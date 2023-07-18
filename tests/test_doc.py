import pytest
from tree_sitter import Node
from menderbot.doc import function_nodes

@pytest.fixture
def sample_tree():
    # Create a sample syntax tree
    # This is just a placeholder, replace with a real syntax tree for testing
    return Node()

def test_function_nodes(sample_tree):
    # Call function_nodes with the sample_tree
    result = list(function_nodes(sample_tree))

    # Assert the result
    # This is just a placeholder, replace with real assertions based on the expected output
    assert result == []
