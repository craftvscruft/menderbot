import logging
import os
import re

from menderbot import python_cst
from menderbot.source_file import Insertion, SourceFile

logger = logging.getLogger("typing")


def process_untyped_functions(source_file: SourceFile):
    path = source_file.path
    logger.info('Processing "%s"...', path)
    _, file_extension = os.path.splitext(path)
    if not file_extension == ".py":
        logger.info('"%s" is not a Python file, skipping.', path)
        return
    source = source_file.load_source_as_utf8()

    for fn_ast in python_cst.collect_function_asts(source):
        yield (fn_ast, what_needs_typing(fn_ast))


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
    function_ast: python_cst.AstNode,
    hints: list[tuple[str, str]],
    imports: list[tuple[str, str]],
) -> list:
    print("function_node", function_ast.props)
    function_name = function_ast.props["name"]
    sig_ast = function_ast.children_filtered(kind=python_cst.KIND_SIGNATURE)[0]
    def_param_nodes = sig_ast.children_filtered(kind=python_cst.KIND_PARAM)
    return_type = function_ast.props.get(python_cst.PROP_RETURN_TYPE)
    insertions = []
    common_typing_import_names = ["Optional", "Callable", "NamedTuple", "Any", "Type"]

    def add_needed_imports(new_type: str):
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
        for param_node in def_param_nodes:
            if param_node.props.get("name") == ident:
                insertions.append(
                    Insertion(
                        text=f": {new_type}",
                        line_number=param_node.src_range.end.line,
                        col=param_node.src_range.end.col,
                        inline=True,
                        label=function_name,
                    )
                )
        if ident == "return" and not return_type:
            signature_ast = function_ast.children_filtered(
                kind=python_cst.KIND_SIGNATURE
            )[0]
            insertions.append(
                Insertion(
                    text=f" -> {new_type}",
                    line_number=signature_ast.src_range.end.line,
                    col=signature_ast.src_range.end.col,
                    inline=True,
                    label=function_name,
                )
            )

    return insertions


def what_needs_typing(fn_ast: python_cst.AstNode) -> list[str]:
    name = fn_ast.props["name"]
    sig_ast = fn_ast.children_filtered(kind=python_cst.KIND_SIGNATURE)[0]
    param_asts = sig_ast.children_filtered(kind=python_cst.KIND_PARAM)
    return_type = fn_ast.props.get(python_cst.PROP_RETURN_TYPE)
    needs_typing = [
        param_ast.props["name"]
        for param_ast in param_asts
        if "type" not in param_ast.props
        and param_ast.props["name"] not in ["self", "cls"]
    ]
    if not return_type and name != "__init__":
        needs_typing.append("return")
    return needs_typing


# def get_function_param_nodes(
#     node: PythonParser.FuncdefContext,
# ) -> Generator[PythonParser.Def_parameterContext, None, None]:
#     args_list_node: PythonParser.TypedargslistContext = node.typedargslist()
#     # args_node : Optional[PythonParser.ArgsContext] = params_node.args()
#     # def_params_node: Optional[PythonParser.Def_parametersContext] = params_node.def_parameters()
#     # kwargs_node: Optional[PythonParser.KwargsContext] = params_node.kwargs()
#     if args_list_node:
#         def_params_nodes: list[
#             PythonParser.Def_parameterContext
#         ] = args_list_node.def_parameters()
#         for def_params_node_untyped in def_params_nodes:
#             def_params_node: PythonParser.Def_parametersContext = def_params_node_untyped
#             for def_param_node_untyped in def_params_node.def_parameter():
#                 def_param_node: PythonParser.Def_parameterContext = def_param_node_untyped
#                 yield def_param_node
