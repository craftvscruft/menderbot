import os
from typing import Iterable

from approvaltests.approvals import verify

from menderbot.code import LANGUAGE_STRATEGIES, function_indent, reindent
from menderbot.doc import document_file
from menderbot.source_file import Insertion, SourceFile, insert_in_lines


class FakeSourceFile(SourceFile):
    def __init__(self, path: str, text: str):
        self.path = path
        self.encoding = None
        self._initial_modified_time = None
        self.text = text
        self.original_text = text

    def update_file(self, insertions: Iterable[Insertion], suffix: str) -> None:
        del suffix
        if len(insertions) == 0:
            return
        # Split keeping delimiter, so each line will have a "\n"
        old_lines = self.text.splitlines(True)
        new_lines = list(insert_in_lines(lines=old_lines, insertions=insertions))
        self.text = "".join(new_lines)

    def load_source_as_utf8(self):
        return bytes(self.text, "utf-8")

    def is_unicode(self):
        return True

    def modified_after_loaded(self):
        return False


def test_parse_with_fake_source_file():
    source_file = FakeSourceFile(
        "my/path.py",
        """
def foo():
    print('Hello World')
    
def foo():
    \"\"\"Hello\"\"\"
    print('Hello World')
""",
    )

    path = source_file.path
    _, file_extension = os.path.splitext(path)
    language_strategy = LANGUAGE_STRATEGIES.get(file_extension)
    assert language_strategy

    source = source_file.load_source_as_utf8()
    tree = language_strategy.parse_source_to_tree(source)
    function_nodes = language_strategy.get_function_nodes(tree)
    assert len(function_nodes) == 2
    assert not language_strategy.function_has_comment(function_nodes[0])
    assert language_strategy.function_has_comment(function_nodes[1])


def test_do_nothing_for_unknown_extension():
    def generate_fake_doc(code, file_extension):
        del code
        del file_extension
        raise AssertionError("Should not be called")

    source_file = FakeSourceFile(
        "my/path.unknown",
        """
def foo():
    print('Hello World')
""",
    )

    insertions = document_file(source_file, generate_fake_doc)
    source_file.update_file(insertions, suffix="")
    assert source_file.text == source_file.original_text


def test_adds_python_doc():
    def generate_fake_doc(code, file_extension):
        assert file_extension == ".py"
        indent = function_indent(code)
        return reindent('"""Hi!"""', indent)

    source_file = FakeSourceFile(
        "my/path.py",
        """
def foo():
    print('Hello World')
""",
    )

    insertions = document_file(source_file, generate_fake_doc)
    source_file.update_file(insertions, suffix="")
    verify(source_file.text)


def test_passes_in_code_to_generator():
    code_received = None

    def generate_fake_doc(code, file_extension):
        nonlocal code_received
        assert file_extension == ".py"
        code_received = code
        return '  """Hi!"""'

    source_file = FakeSourceFile(
        "my/path.py",
        """
def foo():
    print('Hello World')
""",
    )

    document_file(source_file, generate_fake_doc)
    assert code_received == "def foo():\n    print('Hello World')\n\n"
