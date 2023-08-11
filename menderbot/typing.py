import logging
import os
import re
from typing import Generator

from antlr4.Token import CommonToken  # type: ignore

from menderbot.antlr_generated.PythonParser import PythonParser  # type: ignore
from menderbot.code import PythonLanguageStrategy, node_str
from menderbot.source_file import Insertion, SourceFile

logger = logging.getLogger("typing")


def parse_type_hint_answer(text: str) -> list:
    def line_to_tuple(line: str) -> tuple:
        [ident, new_type] = line.split(":")
        new_type = re.sub(r"\bList\b", "list", new_type)
        # NoReturn has valid uses but is unlikely, assume we mean None
        new_type = re.sub(r"\bNoReturn\b", "None", new_type)
        return (ident.strip(), new_type.strip())

    lines = text.strip().splitlines()
    hints = [line_to_tuple(line) for line in lines if ":" in line]
    return [hint for hint in hints if hint[0] != "self" and hint[1].lower() != "any"]


def add_type_hints(
    tree, function_node: PythonParser.FuncdefContext, hints: list
) -> list:
    function_name_ctx: PythonParser.NameContext = function_node.name()
    function_name = node_str(function_name_ctx)
    def_param_nodes = get_function_param_nodes(function_node)
    return_type_node = function_node.test()
    insertions = []
    py_strat = PythonLanguageStrategy()
    imports = py_strat.get_imports(tree)
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
        for param_node_untyped in def_param_nodes:
            param_node: PythonParser.Def_parameterContext = param_node_untyped
            named_param_node: PythonParser.Named_parameterContext = (
                param_node.named_parameter()
            )

            if named_param_node.name() and node_str(named_param_node.name()) == ident:
                param_name_start: CommonToken = named_param_node.name().start
                line = param_name_start.line
                col = param_name_start.column + 1

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
            line, col = get_arg_list_end_line_col(function_node)
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


def get_arg_list_end_line_col(function_node):
    arg_list_node = function_node.typedargslist()
    arg_list_stop: CommonToken = arg_list_node.stop
    line = arg_list_stop.line
    col = arg_list_stop.column + 2
    return line, col


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
        name = node_str(node.name())
        def_param_nodes = get_function_param_nodes(node)
        args_list_node = node.typedargslist()
        return_type_node = node.test()
        needs_typing_unfiltered = [
            node_str(n.named_parameter()) for n in def_param_nodes
        ]
        needs_typing = [
            ns
            for ns in needs_typing_unfiltered
            if ":" not in ns and ns not in ["self", "cls"]
        ]

        return_type_text = ""
        if return_type_node:
            return_type_text = " -> " + node_str(return_type_node)
        elif name != "__init__":
            needs_typing.append("return")
        params_text = node_str(args_list_node)
        print()
        print(f"def {name}({params_text}){return_type_text}")

        if needs_typing:
            function_text = node_str(node)
            # Should make an object
            yield (tree, node, function_text, needs_typing)


def get_function_param_nodes(
    node: PythonParser.FuncdefContext,
) -> Generator[PythonParser.Def_parameterContext, None, None]:
    args_list_node: PythonParser.TypedargslistContext = node.typedargslist()
    # args_node : Optional[PythonParser.ArgsContext] = params_node.args()
    # def_params_node: Optional[PythonParser.Def_parametersContext] = params_node.def_parameters()
    # kwargs_node: Optional[PythonParser.KwargsContext] = params_node.kwargs()
    def_params_nodes: list[
        PythonParser.Def_parameterContext
    ] = args_list_node.def_parameters()
    for def_params_node_untyped in def_params_nodes:
        def_params_node: PythonParser.Def_parametersContext = def_params_node_untyped
        for def_param_node_untyped in def_params_node.def_parameter():
            def_param_node: PythonParser.Def_parameterContext = def_param_node_untyped
            yield def_param_node
