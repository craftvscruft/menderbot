import pytest

from menderbot.antlr_generated.PythonParser import PythonParser
from menderbot.code import PythonLanguageStrategy
from menderbot import python_cst


def parse_string_to_tree(str, lang_strat):
    source_bytes = bytes(str, "utf-8")
    return lang_strat.parse_source_to_tree(source_bytes)


@pytest.fixture
def sample_python_tree(py_strat):
    source = """
def foo():
    pass

def bar():
    pass
"""
    return parse_string_to_tree(source, py_strat)


# @pytest.fixture
# def sample_cpp_tree():
#     source = """
# #include <stdio.h>
# int main() {
#    printf("Hello, World!");
#    return 0;
# }
# """
#     source_bytes = bytes(source, "utf-8")
#     return parse_source_to_tree(source_bytes, CPP_LANGUAGE)


@pytest.fixture
def py_strat():
    return PythonLanguageStrategy()


# @pytest.fixture
# def cpp_strat():
#     return CppLanguageStrategy()


def test_function_nodes_with_python(sample_python_tree, py_strat):
    result = py_strat.get_function_nodes(sample_python_tree)

    assert len(result) == 2
    assert is_function_node(result[0])
    assert is_function_node(result[1])


def is_function_node(result_):
    return result_.getRuleIndex() == PythonParser.RULE_funcdef


def test_decorated_function_nodes_with_python(py_strat):
    source = """
@cli.command()
@click.argument("q", nargs=-1)
def foo(q):
    pass

def bar(q):
    pass
"""
    tree = parse_string_to_tree(source, py_strat)
    result = list(py_strat.get_function_nodes(tree))

    assert len(result) == 2
    assert is_function_node(result[0])
    assert is_function_node(result[1])


def test_class_function_nodes_with_python(py_strat):
    source = """
class Cls:
    def __init__(self):
        pass

    def foo():
        pass
"""
    tree = parse_string_to_tree(source, py_strat)
    result = list(py_strat.get_function_nodes(tree))

    assert len(result) == 2
    assert is_function_node(result[0])
    assert is_function_node(result[1])


def test_python_function_has_comment_false(py_strat):
    source = """
def foo():
    pass
"""
    tree = parse_string_to_tree(source, py_strat)
    node = py_strat.get_function_nodes(tree)[0]
    assert not py_strat.function_has_comment(node)


def test_python_function_has_comment_true(py_strat):
    source = """
def foo():
    \"\"\"Doc string\"\"\"
    pass
"""
    tree = parse_string_to_tree(source, py_strat)
    node = py_strat.get_function_nodes(tree)[0]
    assert py_strat.function_has_comment(node)


def test_python_function_name(py_strat):
    source = """
def foo():
    \"\"\"Doc string\"\"\"
    pass
"""
    tree = parse_string_to_tree(source, py_strat)
    node = py_strat.get_function_nodes(tree)[0]
    assert py_strat.get_function_node_name(node) == "foo"


# def test_cpp_function_name(cpp_strat):
#     source = """
# #include <stdio.h>
# int main() {
#    printf("Hello, World!");
#    return 0;
# }
# """
#     tree = parse_string_to_tree(source, CPP_LANGUAGE)
#     node = cpp_strat.get_function_nodes(tree)[0]
#     assert cpp_strat.get_function_node_name(node) == "main"


def test_python_end_of_params_line_col(py_strat):
    # TODO: Should move into LanguageStrategy probably.
    code = """
#2345678901234
def foo(a, b):
    pass
"""
    fn_ast = python_cst.collect_function_asts(code)[0]
    sig_ast = fn_ast.children_filtered(kind=python_cst.KIND_SIGNATURE)[0]
    sig_end = sig_ast.src_range.end
    assert (sig_end.line, sig_end.col) == (3, 14)
