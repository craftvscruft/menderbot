from typing import Iterable
from unittest.mock import patch

import pytest

from menderbot.__main__ import try_function_type_hints
from menderbot.code import LanguageStrategy, PythonLanguageStrategy, node_str
from menderbot.source_file import Insertion, SourceFile, insert_in_lines
from menderbot.typing import (
    add_type_hints,
    parse_type_hint_answer,
    what_needs_typing,
)
from menderbot import python_cst


@pytest.fixture
def py_strat():
    return PythonLanguageStrategy()


def parse_string_to_tree(str, lang_strat: LanguageStrategy):
    source_bytes = bytes(str, "utf-8")
    return lang_strat.parse_source_to_tree(source_bytes)


def test_add_type_hints(py_strat):
    code = """
def foo(a):
    pass
"""
    code_lines = code.splitlines(True)
    expected_lines = ["\n", "def foo(a: int) -> None:\n", "    pass\n"]
    expected = [
        Insertion(text=": int", line_number=2, col=10, inline=True, label="foo"),
        Insertion(text=" -> None", line_number=2, col=11, inline=True, label="foo"),
    ]
    fn_asts = python_cst.collect_function_asts(code)
    hints = [("a", "int"), ("return", "None")]
    insertions = add_type_hints(fn_asts[0], hints, [])

    sig_ast = fn_asts[0].children_filtered(kind=python_cst.KIND_SIGNATURE)[0]
    # print(code)
    # print(sig_ast.text)
    # print(sig_ast.src_range)
    # print(python_cst.to_json(fn_asts))
    assert sig_ast.src_range.end.col == 11

    assert insertions == expected
    assert list(insert_in_lines(code_lines, insertions)) == expected_lines


def test_add_type_hints_on_first_line(py_strat):
    code = """def foo(a):
    pass
"""
    expected = [
        Insertion(text=": int", line_number=1, col=10, inline=True, label="foo"),
        Insertion(text=" -> None", line_number=1, col=11, inline=True, label="foo"),
    ]
    fn_asts = python_cst.collect_function_asts(code)
    hints = [("a", "int"), ("return", "None")]
    insertions = add_type_hints(fn_asts[0], hints, [])

    assert insertions == expected


def test_parse_type_hint_answer():
    assert parse_type_hint_answer("a : int\nreturn : Any\n") == [("a", "int")]


def test_process_untyped_functions_one_result(py_strat):
    code = """def foo(a):
    pass"""
    fn_asts = python_cst.collect_function_asts(code)
    needs_typing = what_needs_typing(fn_asts[0])
    assert needs_typing == ["a", "return"]


def test_process_untyped_functions_excludes_init(py_strat):
    code = """def __init__(a):
    pass"""
    fn_asts = python_cst.collect_function_asts(code)
    needs_typing = what_needs_typing(fn_asts[0])
    assert needs_typing == ["a"]


class MockSourceFile(SourceFile):
    def __init__(self):
        self.path = ""

    def load_source_as_utf8(self):
        return ""

    def update_file(self, insertions: Iterable[Insertion], suffix: str) -> None:
        pass


def test_try_function_type_hints(py_strat):
    code = """
def foo(a):
    pass
    """
    fn_asts = python_cst.collect_function_asts(code)
    with patch(
        "menderbot.check.run_check",
        side_effect=lambda _: True,
    ):
        source_file = MockSourceFile()
        no_hints = try_function_type_hints(
            "..mypy..", source_file, fn_asts[0], []
        )
        assert no_hints == []
        one_hint_no_results = try_function_type_hints(
            "..mypy..", source_file, fn_asts[0], ["a"]
        )
        assert one_hint_no_results == []


def test_indented_function(py_strat):
    """
    Currently a function too deeply indented will not parse as a function.
    This test documents that, in case we decide to change it.
    """
    code = """\n    def foo(a):\n        pass"""
    tree = parse_string_to_tree(
        code,
        py_strat,
    )

    function_nodes = py_strat.get_function_nodes(tree)

    assert len(function_nodes) == 0


def test_get_from_imports(py_strat):
    code = """
from typing import Foo, Bar
from typing import Baz
from otherlib import Quux
def foo(a):
    pass
"""
    tree = parse_string_to_tree(
        code,
        py_strat,
    )
    assert py_strat.get_imports(tree) == [
        ("typing", "Foo"),
        ("typing", "Bar"),
        ("typing", "Baz"),
        ("otherlib", "Quux"),
    ]


def test_get_non_from_imports(py_strat):
    code = """
import typing
import typing.Foo
import foo.Bar as Baz
def foo(a):
    pass
"""
    tree = parse_string_to_tree(
        code,
        py_strat,
    )
    assert py_strat.get_imports(tree) == [
        ("", "typing"),
        ("", "typing.Foo"),
        ("", "foo.Bar as Baz"),
    ]
