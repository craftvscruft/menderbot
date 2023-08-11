import logging
import os
from typing import Callable

from menderbot.code import LANGUAGE_STRATEGIES
from menderbot.source_file import Insertion, SourceFile

logger = logging.getLogger("doc")


def init_logging() -> None:
    logger.setLevel(logging.DEBUG)
    # create console handler with a higher log level
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    logger.addHandler(stream_handler)


init_logging()


def document_file(source_file: SourceFile, doc_gen: Callable) -> list[Insertion]:
    path = source_file.path
    logger.info('Processing "%s"...', path)
    _, file_extension = os.path.splitext(path)
    language_strategy = LANGUAGE_STRATEGIES.get(file_extension)
    if not language_strategy:
        logger.info('Unrecognized extension "%s", skipping.', file_extension)
        return []

    source = source_file.load_source_as_utf8()
    tree = language_strategy.parse_source_to_tree(source)
    insertions = []
    for node in language_strategy.get_function_nodes(tree):
        if not language_strategy.function_has_comment(node):
            name = language_strategy.get_function_node_name(node)
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
