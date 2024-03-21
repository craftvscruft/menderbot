from abc import ABC, abstractmethod

from antlr4 import InputStream  # type: ignore
from antlr4 import CommonTokenStream, ParserRuleContext, ParseTreeWalker
from antlr4.Token import CommonToken  # type: ignore

from menderbot.antlr_generated.PythonLexer import PythonLexer  # type: ignore
from menderbot.antlr_generated.PythonParser import PythonParser  # type: ignore
from menderbot.antlr_generated.PythonParserListener import (  # type: ignore
    PythonParserListener,
)


def node_str(node) -> str:
    return get_text_including_whitespace(node)


def node_start_line(node: ParserRuleContext) -> int:
    node_start: CommonToken = node.start
    return node_start.line


def node_stop_line(node: ParserRuleContext) -> int:
    node_stop: CommonToken = node.stop
    return node_stop.line


def node_start_column(node: ParserRuleContext) -> int:
    node_start: CommonToken = node.start
    return node_start.column


def node_stop_column(node: ParserRuleContext) -> int:
    node_start: CommonToken = node.stop
    return node_start.column


def get_text_including_whitespace(ctx: ParserRuleContext):
    if not ctx:
        return ""
    start: CommonToken = ctx.start
    stop: CommonToken = ctx.stop
    start_idx: int = start.start
    stop_idx: int = stop.stop
    stream: InputStream = start.getInputStream()
    return stream.getText(start_idx, stop_idx)


def line_indent(line: str) -> str:
    count = len(line) - len(line.lstrip())
    return line[:count]


def function_indent(code: str) -> str:
    second_line_start = code.find("\n") + 1
    no_first_line = code[second_line_start:]
    if no_first_line.find("\n") > -1:
        second_line_end = second_line_start + no_first_line.find("\n")
        second_line = code[second_line_start:second_line_end]
    else:
        second_line = no_first_line
    return line_indent(second_line)


def reindent(text: str, indent: str) -> str:
    lines = text.split("\n")
    indented_lines = [indent + line.lstrip() for line in lines]
    return "\n".join(indented_lines)


class LanguageStrategy(ABC):
    @abstractmethod
    def function_has_comment(self, node) -> bool:
        pass

    @abstractmethod
    def parse_source_to_tree(self, source: bytes) -> None:
        pass

    @abstractmethod
    def get_function_nodes(self, tree) -> list:
        pass

    def get_imports(self, tree) -> list:
        del tree
        return []

    @property
    @abstractmethod
    def function_doc_line_offset(self) -> int:
        pass


class PythonLanguageStrategy(LanguageStrategy):
    def function_has_comment(self, node: PythonParser.FuncdefContext) -> bool:
        """Checks if function has a docstring."""
        body_node: PythonParser.SuiteContext = node.suite()
        if body_node:
            # https://peps.python.org/pep-0257/
            first_stmt_node: PythonParser.StmtContext = body_node.stmt(0)
            first_stmt_text = first_stmt_node.getText().strip()
            has_doc_prefix = (
                first_stmt_text.startswith('"""')
                or first_stmt_text.startswith('r"""')
                or first_stmt_text.startswith('u"""')
            )

            has_doc_suffix = first_stmt_text.endswith('"""')
            return has_doc_prefix and has_doc_suffix
        return False

    def parse_source_to_tree(self, source: bytes):
        input_stream = InputStream(str(source, encoding="utf-8") + "\n")
        lexer = PythonLexer(input_stream)
        token_stream = CommonTokenStream(lexer)
        parser = PythonParser(token_stream)
        return parser.file_input()

    def get_function_nodes(self, tree) -> list[PythonParser.FuncdefContext]:
        function_nodes: list[PythonParser.FuncdefContext] = []

        class MyListener(PythonParserListener):
            def enterFuncdef(self, ctx: PythonParser.FuncdefContext):
                function_nodes.append(ctx)
                # print(ctx.toStringTree(recog=parser))

        walker = ParseTreeWalker()
        walker.walk(MyListener(), tree)
        return function_nodes

    def get_function_node_name(self, node):
        name_node: PythonParser.NameContext = node.name()
        name = name_node.getText()
        return name

    def get_imports(self, tree) -> list[tuple[str, str]]:
        results: list[tuple[str, str]] = []

        class MyListener(PythonParserListener):
            def enterFrom_stmt(self, ctx: PythonParser.From_stmtContext):
                dotted_name_ctx: PythonParser.Dotted_nameContext = ctx.dotted_name()
                import_as_names_ctx: PythonParser.Import_as_namesContext = (
                    ctx.import_as_names()
                )
                import_as_name_ctxs: list[PythonParser.Import_as_nameContext] = (
                    import_as_names_ctx.import_as_name()
                )
                # print(type(import_as_name_ctxs))
                for import_as_name_ctx in import_as_name_ctxs:
                    results.append(
                        (dotted_name_ctx.getText(), node_str(import_as_name_ctx))
                    )
                # print(ctx.toStringTree(recog=parser))

            def enterImport_stmt(self, ctx: PythonParser.Import_stmtContext):
                dotted_as_names_ctx: PythonParser.Dotted_as_namesContext = (
                    ctx.dotted_as_names()
                )
                dotted_as_name_ctxs: list[PythonParser.Dotted_nameContext] = (
                    dotted_as_names_ctx.dotted_as_name()
                )
                for dottedAsNameCtx in dotted_as_name_ctxs:
                    results.append(("", node_str(dottedAsNameCtx)))

        walker = ParseTreeWalker()
        walker.walk(MyListener(), tree)
        return results

    function_doc_line_offset = 1


# class CppLanguageStrategy(LanguageStrategy):
#     def function_has_comment(self, node) -> bool:
#         return node.prev_sibling.type in ["comment"]
#
#     def parse_source_to_tree(self, source: bytes):
#         return parse_source_to_tree(source, CPP_LANGUAGE)
#
#     def get_function_nodes(self, tree) -> list:
#         query = CPP_LANGUAGE.query(
#             """
#         [
#             (function_definition) @function
#         ]
#         """
#         )
#         captures = query.captures(tree.root_node)
#         return [capture[0] for capture in captures]
#
#     function_doc_line_offset = 0


LANGUAGE_STRATEGIES = {
    ".py": PythonLanguageStrategy(),
    # ".c": CppLanguageStrategy(),
    # ".cpp": CppLanguageStrategy(),
}
