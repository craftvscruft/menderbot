from abc import ABC, abstractmethod

from tree_sitter import Language, Parser

CPP_LANGUAGE = Language("build/my-languages.so", "cpp")
PY_LANGUAGE = Language("build/my-languages.so", "python")


def node_str(node) -> str:
    return str(node.text, encoding="utf-8")


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


def parse_source_to_tree(source: bytes, language: Language):
    parser = Parser()
    parser.set_language(language)

    return parser.parse(source)


class LanguageStrategy(ABC):
    @abstractmethod
    def function_has_comment(self, node) -> bool:
        pass

    @abstractmethod
    def parse_source_to_tree(self, source: bytes) -> None:
        pass

    @abstractmethod
    def get_node_declarator_name(self, node) -> str:
        pass

    @abstractmethod
    def get_function_nodes(self, tree) -> list:
        pass

    @property
    @abstractmethod
    def function_doc_line_offset(self) -> int:
        pass


class PythonLanguageStrategy(LanguageStrategy):
    def function_has_comment(self, node) -> bool:
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

    def parse_source_to_tree(self, source: bytes):
        return parse_source_to_tree(source, PY_LANGUAGE)

    def get_node_declarator_name(self, node) -> str:
        name_node = node.child_by_field_name("name")
        return str(name_node.text, encoding="utf-8")

    def get_function_nodes(self, tree) -> list:
        query = PY_LANGUAGE.query(
            """
        (function_definition name: (identifier)) @function
        """
        )
        captures = query.captures(tree.root_node)
        return [capture[0] for capture in captures]

    function_doc_line_offset = 1


class CppLanguageStrategy(LanguageStrategy):
    def function_has_comment(self, node) -> bool:
        return node.prev_sibling.type in ["comment"]

    def parse_source_to_tree(self, source: bytes):
        return parse_source_to_tree(source, CPP_LANGUAGE)

    def get_node_declarator_name(self, node) -> str:
        declarator_node = node.child_by_field_name("declarator")
        while declarator_node.child_by_field_name("declarator"):
            declarator_node = declarator_node.child_by_field_name("declarator")
        return str(declarator_node.text, encoding="utf-8")

    def get_function_nodes(self, tree) -> list:
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
