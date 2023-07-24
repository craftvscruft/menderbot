import pytest
from menderbot.__main__ import parse_type_hint_answer
from menderbot.source_file import Insertion, insert_in_lines
from tree_sitter import Language
from menderbot.code import PythonLanguageStrategy, parse_source_to_tree
from menderbot.typing import add_type_hints, process_untyped_functions_in_tree


PY_LANGUAGE = Language("build/my-languages.so", "python")


@pytest.fixture
def py_strat():
    return PythonLanguageStrategy()


def parse_string_to_tree(str, lang):
    source_bytes = bytes(str, "utf-8")
    return parse_source_to_tree(source_bytes, lang)


def test_add_type_hints(py_strat):
    code = """
def foo(a):
    pass
"""
    code_lines = code.splitlines(True)
    expected_lines = ["\n", "def foo(a: int) -> None:\n", "    pass\n"]
    tree = parse_string_to_tree(
        code,
        PY_LANGUAGE,
    )
    expected = [
        Insertion(text=": int", line_number=2, col=9, inline=True, label="foo"),
        Insertion(text=" -> None", line_number=2, col=10, inline=True, label="foo"),
    ]
    function_nodes = py_strat.get_function_nodes(tree)
    hints = [("a", "int"), ("return", "None")]
    insertions = add_type_hints(function_nodes[0], hints)

    assert insertions == expected
    assert list(insert_in_lines(code_lines, insertions)) == expected_lines


def test_add_type_hints_on_first_line(py_strat):
    tree = parse_string_to_tree(
        """def foo(a):
    pass
""",
        PY_LANGUAGE,
    )
    expected = [
        Insertion(text=": int", line_number=1, col=9, inline=True, label="foo"),
        Insertion(text=" -> None", line_number=1, col=10, inline=True, label="foo"),
    ]
    function_nodes = py_strat.get_function_nodes(tree)
    hints = [("a", "int"), ("return", "None")]
    insertions = add_type_hints(function_nodes[0], hints)

    assert insertions == expected


def test_parse_type_hint_answer():
    assert parse_type_hint_answer("a : int\nreturn : Any\n") == [("a", "int")]


def test_process_untyped_functions_one_result(py_strat):
    tree = parse_string_to_tree(
        """def foo(a):
    pass""",
        PY_LANGUAGE,
    )
    results = list(process_untyped_functions_in_tree(tree, py_strat))
    assert len(results) == 1
    (_, _, needs_typing) = results[0]
    assert needs_typing == ["a", "return"]


def test_process_untyped_functions_excludes_init(py_strat):
    tree = parse_string_to_tree(
        """def __init__(a):
    pass""",
        PY_LANGUAGE,
    )
    results = list(process_untyped_functions_in_tree(tree, py_strat))
    assert len(results) == 1
    (_, _, needs_typing) = results[0]
    assert needs_typing == ["a"]
