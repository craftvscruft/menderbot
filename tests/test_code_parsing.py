import pytest
from menderbot.code import (
    CppLanguageStrategy,
    PythonLanguageStrategy,
    parse_source_to_tree,
)
from tree_sitter import Language


PY_LANGUAGE = Language("build/my-languages.so", "python")
CPP_LANGUAGE = Language("build/my-languages.so", "cpp")


def parse_string_to_tree(str, lang):
    source_bytes = bytes(str, "utf-8")
    return parse_source_to_tree(source_bytes, lang)


@pytest.fixture
def sample_python_tree():
    source = """
def foo():
    pass

def bar():
    pass
"""
    return parse_string_to_tree(source, PY_LANGUAGE)


@pytest.fixture
def sample_cpp_tree():
    source = """
#include <stdio.h>
int main() {
   printf("Hello, World!");
   return 0;
}
"""
    source_bytes = bytes(source, "utf-8")
    return parse_source_to_tree(source_bytes, CPP_LANGUAGE)


@pytest.fixture
def py_strat():
    return PythonLanguageStrategy()


@pytest.fixture
def cpp_strat():
    return CppLanguageStrategy()


def test_function_nodes_with_python(sample_python_tree, py_strat):
    result = py_strat.get_function_nodes(sample_python_tree)

    assert len(result) == 2
    assert result[0].type == "function_definition"
    assert result[1].type == "function_definition"


def test_decorated_function_nodes_with_python(py_strat):
    source = """
@cli.command()
@click.argument("q", nargs=-1)
def foo(q):
    pass

def bar(q):
    pass
"""
    tree = parse_string_to_tree(source, PY_LANGUAGE)
    result = list(py_strat.get_function_nodes(tree))

    assert len(result) == 2
    assert result[0].type == "function_definition"
    assert result[1].type == "function_definition"


def test_class_function_nodes_with_python(py_strat):
    source = """
class Cls:
    def __init__(self):
        pass

    def foo():
        pass
"""
    tree = parse_string_to_tree(source, PY_LANGUAGE)
    result = list(py_strat.get_function_nodes(tree))

    assert len(result) == 2
    assert result[0].type == "function_definition"
    assert result[1].type == "function_definition"


def test_python_function_has_comment_false(sample_cpp_tree):
    strat = PythonLanguageStrategy()
    source = """
def foo():
    pass
"""
    tree = parse_string_to_tree(source, PY_LANGUAGE).root_node
    node = strat.get_function_nodes(tree)[0]
    assert not strat.function_has_comment(node)


def test_python_function_has_comment_false(py_strat):
    strat = PythonLanguageStrategy()
    source = """
def foo():
    \"\"\"Doc string\"\"\"
    pass
"""
    tree = parse_string_to_tree(source, PY_LANGUAGE)
    node = py_strat.get_function_nodes(tree)[0]
    assert strat.function_has_comment(node)


def test_python_function_name(py_strat):
    strat = PythonLanguageStrategy()
    source = """
def foo():
    \"\"\"Doc string\"\"\"
    pass
"""
    tree = parse_string_to_tree(source, PY_LANGUAGE)
    node = py_strat.get_function_nodes(tree)[0]
    assert py_strat.get_node_declarator_name(node) == "foo"


def test_cpp_function_name(cpp_strat):
    source = """
#include <stdio.h>
int main() {
   printf("Hello, World!");
   return 0;
}
"""
    tree = parse_string_to_tree(source, CPP_LANGUAGE)
    node = cpp_strat.get_function_nodes(tree)[0]
    assert cpp_strat.get_node_declarator_name(node) == "main"
