import logging
import os
import re

from menderbot.code import PythonLanguageStrategy
from menderbot.source_file import Insertion, SourceFile

logger = logging.getLogger("typing")


def node_str(node) -> str:
    return str(node.text, encoding="utf-8")


def parse_type_hint_answer(text: str) -> list:
    def line_to_tuple(line: str) -> tuple:
        [ident, new_type] = line.split(":")
        new_type = re.sub(r"\bList\b", "list", new_type)
        return (ident.strip(), new_type.strip())

    lines = text.strip().splitlines()
    hints = [line_to_tuple(line) for line in lines if ":" in line]
    return [hint for hint in hints if hint[0] != "self" and hint[1].lower() != "any"]


def add_type_hints(tree, function_node, hints: list) -> list:
    function_name = node_str(function_node.child_by_field_name("name"))
    params_node = function_node.child_by_field_name("parameters")
    return_type_node = function_node.child_by_field_name("return_type")
    insertions = []
    py_strat = PythonLanguageStrategy()
    imports = py_strat.get_type_imports(tree)
    common_typing_import_names = ["Optional", "Callable", "NamedTuple", "Any", "Type"]

    def add_needed_imports(new_type):
        new_type_symbols = re.findall(r"\b\w+\b", new_type)
        for new_type_symbol in new_type_symbols:
            if (
                new_type_symbol in common_typing_import_names
                and ("typing", new_type_symbol) not in imports
            ):
                imports.append(("typing", new_type_symbol))
                insertions.append(
                    Insertion(
                        text=f"from typing import {new_type_symbol}",
                        line_number=1,
                        label="type_import",
                    )
                )

    for ident, new_type in hints:
        add_needed_imports(new_type)
        for param_node in params_node.children:
            if param_node.type in ["identifier"] and node_str(param_node) == ident:
                line = param_node.end_point[0] + 1
                col = param_node.end_point[1]

                insertions.append(
                    Insertion(
                        text=f": {new_type}",
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


def process_untyped_functions(source_file: SourceFile):
    path = source_file.path
    logger.info('Processing "%s"...', path)
    _, file_extension = os.path.splitext(path)
    if not file_extension == ".py":
        logger.info('"%s" is not a Python file, skipping.', path)
        return
    language_strategy = PythonLanguageStrategy()
    source = source_file.load_source_as_utf8()
    tree = language_strategy.parse_source_to_tree(source)
    return process_untyped_functions_in_tree(tree, language_strategy)


def process_untyped_functions_in_tree(tree, language_strategy):
    for node in language_strategy.get_function_nodes(tree):
        name = node_str(node.child_by_field_name("name"))
        params_node = node.child_by_field_name("parameters")
        return_type_node = node.child_by_field_name("return_type")
        needs_typing = [
            node_str(n) for n in params_node.children if n.type in ["identifier"]
        ]
        needs_typing = [n for n in needs_typing if n not in ["self", "cls"]]
        # Add "default_parameter" later probably.
        return_type_text = ""
        if return_type_node:
            return_type_text = " -> " + node_str(return_type_node)
        elif name != "__init__":
            needs_typing.append("return")
        params = node_str(params_node)
        print()
        print(f"def {name}{params}{return_type_text}")

        if needs_typing:
            function_text = node_str(node)
            # Should make an object
            yield (tree, node, function_text, needs_typing)

        # https://github.com/tree-sitter/tree-sitter-python/blob/master/grammar.js
        # print(node.sexp())
