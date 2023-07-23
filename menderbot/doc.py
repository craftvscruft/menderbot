import os
import abc
import logging
from pathlib import Path

from typing import Iterable
import tiktoken
import openai

from tree_sitter import Language, Parser

from menderbot.source_file import SourceFile, Insertion

CPP_LANGUAGE = Language("build/my-languages.so", "cpp")
PY_LANGUAGE = Language("build/my-languages.so", "python")

logger = logging.getLogger("doc")


def init_logging():
    logger.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    logger.addHandler(stream_handler)


init_logging()


def parse_source_to_tree(source, language):
    parser = Parser()
    parser.set_language(language)

    return parser.parse(source)


class LanguageStrategy(abc.ABC):
    @abc.abstractclassmethod
    def function_has_comment(self, node):
        pass

    @abc.abstractclassmethod
    def parse_source_to_tree(self, source):
        pass

    @abc.abstractclassmethod
    def get_node_declarator_name(self, node):
        pass

    @abc.abstractclassmethod
    def get_function_nodes(self, tree):
        pass


class PythonLanguageStrategy(LanguageStrategy):
    def function_has_comment(self, node):
        """Checks if function has a docstring. Example node:
        (function_definition name: (identifier) parameters: (parameters)
           body: (block (expression_statement
             (string string_content: (string_content))) (pass_statement)))
        """
        body_node = node.child_by_field_name("body")
        if body_node and body_node.type == "block":
            if (
                body_node.child_count > 0
                and body_node.children[0].type == "expression_statement"
            ):
                expression_statement_node = body_node.children[0]
                if expression_statement_node.child_count > 0:
                    return expression_statement_node.children[0].type == "string"
        return False

    def parse_source_to_tree(self, source):
        return parse_source_to_tree(source, PY_LANGUAGE)

    def get_node_declarator_name(self, node):
        name_node = node.child_by_field_name("name")
        return str(name_node.text, encoding="utf-8")

    def get_function_nodes(self, tree):
        query = PY_LANGUAGE.query(
            """
        (function_definition name: (identifier)) @function
        """
        )
        captures = query.captures(tree.root_node)
        return [capture[0] for capture in captures]

    function_doc_line_offset = 1


class CppLanguageStrategy(LanguageStrategy):
    def function_has_comment(self, node):
        return node.prev_sibling.type in ["comment"]

    def parse_source_to_tree(self, source):
        return parse_source_to_tree(source, CPP_LANGUAGE)

    def get_node_declarator_name(self, node):
        declarator_node = node.child_by_field_name("declarator")
        while declarator_node.child_by_field_name("declarator"):
            declarator_node = declarator_node.child_by_field_name("declarator")
        return str(declarator_node.text, encoding="utf-8")

    def get_function_nodes(self, tree):
        query = CPP_LANGUAGE.query(
            """
        [
            (function_definition) @function
        ]
        """
        )
        captures = query.captures(tree.root_node)
        return [capture[0] for capture in captures]

    function_doc_line_offset = 0


LANGUAGE_STRATEGIES = {
    ".py": PythonLanguageStrategy(),
    ".c": CppLanguageStrategy(),
    ".cpp": CppLanguageStrategy(),
}


def document_file(source_file: SourceFile, doc_gen):
    path = source_file.path
    logger.info('Processing "%s"...', path)
    _, file_extension = os.path.splitext(path)
    language_strategy = LANGUAGE_STRATEGIES.get(file_extension)
    if not language_strategy:
        logger.info('Unrecognized extension "%s", skipping.', file_extension)
        return

    source = source_file.load_source_as_utf8()
    tree = language_strategy.parse_source_to_tree(source)
    insertions = []
    for node in language_strategy.get_function_nodes(tree):
        if not language_strategy.function_has_comment(node):
            name = language_strategy.get_node_declarator_name(node)
            logger.info('Found undocumented function "%s"', name)
            code = str(node.text, encoding="utf-8")
            comment = doc_gen(code, file_extension)
            function_start_line = node.start_point[0] + 1
            doc_start_line = (
                function_start_line + language_strategy.function_doc_line_offset
            )
            if comment:
                logger.info("Documenting with: %s", comment)
                logger.info("For code: %s", code)
                insertions.append(
                    Insertion(text=comment, line_number=doc_start_line, label=name)
                )
    return insertions
