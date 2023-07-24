import os
import logging
from typing import Any, Callable
from menderbot.code import PythonLanguageStrategy
from menderbot.source_file import Insertion, SourceFile

logger = logging.getLogger("typing")


def node_str(node):
    return str(node.text, encoding="utf-8")


def add_type_hints(function_node, hints):
    function_name = node_str(function_node.child_by_field_name("name"))
    params_node = function_node.child_by_field_name("parameters")
    return_type_node = function_node.child_by_field_name("return_type")
    insertions = []

    for ident, new_type in hints:
        for param_node in params_node.children:
            if param_node.type in ["identifier"] and node_str(param_node) == ident:
                line = param_node.end_point[0] + 1
                col = param_node.end_point[1]

                insertions.append(
                    Insertion(
                        text=f" : {new_type}",
                        line_number=line,
                        col=col,
                        inline=True,
                        label=function_name,
                    )
                )
        if ident == "return" and not return_type_node:
            line = params_node.end_point[0] + 1
            col = params_node.end_point[1]
            insertions.append(
                Insertion(
                    text=f" -> {new_type}",
                    line_number=line,
                    col=col,
                    inline=True,
                    label=function_name,
                )
            )
    return insertions


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
    insertions = []
    for node in language_strategy.get_function_nodes(tree):
        name = node_str(node.child_by_field_name("name"))
        params_node = node.child_by_field_name("parameters")
        return_type_node = node.child_by_field_name("return_type")
        needs_typing = [
            node_str(n) for n in params_node.children if n.type in ["identifier"]
        ]
        # Add "default_parameter" later probably.
        return_type_text = ""
        if return_type_node:
            return_type_text = " -> " + node_str(return_type_node)
        else:
            needs_typing.append("return")
        params = node_str(params_node)
        print(f"def {name}{params}{return_type_text}")

        if needs_typing:
            function_text = node_str(node)
            hints = handler(function_text, needs_typing)
            insertions += add_type_hints(node, hints)
        # https://github.com/tree-sitter/tree-sitter-python/blob/master/grammar.js
        # print(node.sexp())
    return insertions
