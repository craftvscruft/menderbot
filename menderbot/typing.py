import os
import logging
from typing import Any, Callable
from menderbot.code import PythonLanguageStrategy
from menderbot.source_file import SourceFile

logger = logging.getLogger("typing")


def node_str(node):
    return str(node.text, encoding="utf-8")


def process_untyped_functions(
    source_file: SourceFile, handler: Callable[[str, list], Any]
):
    path = source_file.path
    logger.info('Processing "%s"...', path)
    _, file_extension = os.path.splitext(path)
    if not file_extension == ".py":
        logger.info('"%s" is not a Python file, skipping.', path)
        return
    language_strategy = PythonLanguageStrategy()
    source = source_file.load_source_as_utf8()
    tree = language_strategy.parse_source_to_tree(source)
    for node in language_strategy.get_function_nodes(tree):
        name = str(node.child_by_field_name("name").text, encoding="utf-8")
        params_node = node.child_by_field_name("parameters")
        return_type_node = node.child_by_field_name("return_type")
        needs_typing = [
            node_str(n)
            for n in params_node.children
            if n.type in ["identifier", "default_parameter"]
        ]
        return_type_text = ""
        if return_type_node:
            return_type_text = " -> " + node_str(return_type_node)
        else:
            needs_typing.append("return")
        params = node_str(params_node)
        print(f"def {name}{params}{return_type_text}")

        if needs_typing:
            function_text = node_str(node)
            handler(function_text, needs_typing)
        # https://github.com/tree-sitter/tree-sitter-python/blob/master/grammar.js
        # print(node.sexp())
