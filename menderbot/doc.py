import itertools
import logging
from pathlib import Path

from dataclasses import dataclass
import tempfile
from typing import Iterable
import tiktoken
from charset_normalizer import from_path
import openai

from tree_sitter import Language, Parser

CPP_LANGUAGE = Language("build/my-languages.so", "cpp")
logger = logging.getLogger("gpt_autodoc")


def init_logging():
    logger.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    logger.addHandler(stream_handler)


class GptClient:
    def __init__(self, model_name, dry_run: bool):
        self.model_name = model_name
        self.encoding = tiktoken.encoding_for_model(self.model_name)
        self.dry_run = dry_run

    def fetch_completion(self, user_prompt):
        logger.debug("### Prompt:\n%s\n###", user_prompt)
        if self.dry_run:
            return "Dummy dry run response"
        response = openai.ChatCompletion.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
        )
        response_content = response["choices"][0]["message"]["content"]
        logger.debug("### Response:\n%s\n###", response_content)
        return response_content

    def is_within_token_limit(self, text, token_limit):
        num_tokens = len(self.encoding.encode(text))
        logger.debug("Num tokens %s", num_tokens)
        return num_tokens <= token_limit


def chunk_text(string, num_chunks):
    chunk_size = len(string) // num_chunks
    return [string[i : i + chunk_size] for i in range(0, len(string), chunk_size)]


class DocGen:
    def __init__(self, gpt_client: GptClient):
        self.gpt_client = gpt_client

    def generate_doc(self, code, token_limit):
        user_prompt = f"Write a detailed Doxygen style comment for this C++ code. Respond with comment only, no code.\nCODE:\n{code}"
        if not self.gpt_client.is_within_token_limit(user_prompt, token_limit):
            # TODO: Increase model size
            return None
        return self.gpt_client.fetch_completion(user_prompt)


@dataclass
class Insertion:
    text: str
    line_number: int


def insert_in_lines(lines: Iterable[str], insertions: Iterable[Insertion]):
    lines = iter(lines)
    last_line = 1
    for insertion in insertions:
        for line in itertools.islice(lines, insertion.line_number - last_line):
            yield line
            last_line += 1
        yield insertion.text
        yield "\n"
    yield from lines


def parse_source_to_tree(source, language):
    parser = Parser()
    parser.set_language(language)

    return parser.parse(source)


block_breaking_node_types = ["function_definition", "method_definition"]


def get_node_declarator_name(node):
    declarator_node = node.child_by_field_name("declarator")
    while declarator_node.child_by_field_name("declarator"):
        declarator_node = declarator_node.child_by_field_name("declarator")
    return str(declarator_node.text, encoding="utf-8")


def function_nodes(tree):
    cursor = tree.walk()
    if cursor.node.type == "translation_unit":
        cursor.goto_first_child()
    has_next = True
    while has_next:
        if cursor.node.type in block_breaking_node_types:
            yield cursor.node
        has_next = cursor.goto_next_sibling()


class SourceFile:
    def __init__(self, path: str):
        self.path = path
        self.encoding = None

    def load_source_as_utf8(self):
        loaded = from_path(self.path)
        best_guess = loaded.best()
        self.encoding = best_guess.encoding
        return best_guess.output(encoding="utf_8")

    def is_unicode(self):
        return self.encoding.startswith("utf")

    def update_file(self, insertions: Iterable[Insertion], suffix):
        source_file = Path(self.path)
        with source_file.open("r", encoding=self.encoding) as filehandle:
            new_lines = list(insert_in_lines(lines=filehandle, insertions=insertions))
            out_file = source_file.with_suffix(f"{source_file.suffix}{suffix}")
            logger.info("Writing updates to %s", out_file)
            self._write_result(new_lines, out_file)

    def _write_result(self, lines, output_file: Path):
        with tempfile.TemporaryDirectory() as tempdir:
            my_tempfile: Path = Path(tempdir) / "output.txt"
            with my_tempfile.open("w") as filehandle:
                for line in lines:
                    filehandle.write(line)
            my_tempfile.replace(output_file)


def document_file(path, dry_run: bool, max_changes, write):
    gpt_client = GptClient(model_name="gpt-3.5-turbo", dry_run=dry_run)
    doc_gen = DocGen(gpt_client=gpt_client)
    source_file = SourceFile(path)
    logger.info('Processing "%s"...', path)
    source = source_file.load_source_as_utf8()
    tree = parse_source_to_tree(source, CPP_LANGUAGE)
    insertions = []
    token_limit = 3300
    for node in function_nodes(tree):
        if len(insertions) >= max_changes:
            break
        name = get_node_declarator_name(node)
        start_line = node.start_point[0] + 1
        comment_node_types = ["comment"]
        has_comment = node.prev_sibling.type in comment_node_types
        if has_comment:
            logger.debug("%s %s has comment, skipping.", name, start_line)
        else:
            code = str(node.text, encoding="utf-8")
            doc = doc_gen.generate_doc(code, token_limit=token_limit)
            if doc:
                # Sometimes GPT will insert the signature after the comment, trim after */
                # TODO: make more robust by invoking the parser
                logger.info("  %s %s autogen doc:\n%s\n", name, start_line, doc)
                if "*/" in doc:
                    doc = doc[0 : doc.rfind("*/") + 2]
                    insertions.append(Insertion(text=doc, line_number=start_line))
                elif not dry_run:
                    logger.warning(
                        "  %s %s produced invalid comment, disgarding\n",
                        name,
                        start_line,
                    )
            else:
                logger.warning("No doc generated for %s %s", name, start_line)
    if len(insertions) > 0 and not dry_run and write:
        if source_file.is_unicode():
            source_file.update_file(insertions)
        else:
            logger.error(
                "Cannot update '%s', please normalize charset to UTF8, e.g.\nnormalizer -r -n '%s'",
                path,
                path,
            )


# if __name__ == "__main__":
#     init_logging()
#     args = create_arg_parser().parse_args()
#     if args.log:
#         fh = logging.FileHandler("gpt_autodoc.log")
#         fh.setLevel(logging.DEBUG)
#         logger.addHandler(fh)
#     if not "OPENAI_API_KEY" in os.environ:
#         logger.warning("OPENAI_API_KEY not found in env, will not be able to connect.")
#     for input_path in args.paths:
#         files = glob.iglob(input_path)
#         for file in files:
#             process_file(file, dry_run=args.dry, max_changes=5, write=args.write, suffix=".autodoc", target_name=args.name)
