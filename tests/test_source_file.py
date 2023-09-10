from menderbot.source_file import Insertion, insert_in_lines


def test_insert_in_lines_empty():
    expected = []
    lines = []
    insertions = []
    assert list(insert_in_lines(lines, insertions)) == expected


def test_insert_in_lines_insert_first():
    expected = ["aaa\n", "bbb\n", "ccc\n"]
    lines = ["bbb\n", "ccc\n"]
    insertions = [Insertion(text="aaa", line_number=1, label="...")]
    assert list(insert_in_lines(lines, insertions)) == expected


def test_insert_in_lines_insert_middle():
    expected = ["aaa\n", "bbb\n", "ccc\n"]
    lines = ["aaa\n", "ccc\n"]
    insertions = [Insertion(text="bbb", line_number=2, label="...")]
    assert list(insert_in_lines(lines, insertions)) == expected


def test_insert_in_lines_insert_last():
    expected = ["aaa\n", "bbb\n", "ccc\n"]
    lines = ["aaa\n", "bbb\n"]
    insertions = [Insertion(text="ccc", line_number=3, label="...")]
    assert list(insert_in_lines(lines, insertions)) == expected


def test_insert_in_lines_insert_inline():
    expected = ["aaa\n", "_b_\n", "ccc\n"]
    lines = ["aaa\n", "__\n", "ccc\n"]
    insertions = [Insertion(text="b", line_number=2, label="...", inline=True, col=2)]
    assert list(insert_in_lines(lines, insertions)) == expected


def test_insert_in_lines_insert_inline_muliple_in_one_line():
    expected = ["aaa\n", "_1a_2b_\n", "ccc\n"]
    lines = ["aaa\n", "_1_2_\n", "ccc\n"]
    insertions = [
        Insertion(text="a", line_number=2, label="...", inline=True, col=3),
        Insertion(text="b", line_number=2, label="...", inline=True, col=5),
    ]
    assert list(insert_in_lines(lines, insertions)) == expected


def test_insert_in_lines_insert_inline_muliple_in_one_line_regression():
    expected = ["def foo(i: int, j: int) -> int:\n", "    return i+j\n"]
    lines = ["def foo(i: int, j):\n", "    return i+j\n"]
    insertions = [
        Insertion(text=": int", line_number=1, label="...", inline=True, col=18),
        Insertion(text=" -> int", line_number=1, label="...", inline=True, col=19),
    ]
    assert list(insert_in_lines(lines, insertions)) == expected


def test_insert_in_lines_insert_inline_muliple_line():
    expected = ["aaa\n", "_1a_\n", "_2b_\n"]
    lines = ["aaa\n", "_1_\n", "_2_\n"]
    insertions = [
        Insertion(text="a", line_number=2, label="...", inline=True, col=3),
        Insertion(text="b", line_number=3, label="...", inline=True, col=3),
    ]
    assert list(insert_in_lines(lines, insertions)) == expected


def test_insert_in_lines_insert_inline_muliple_line():
    expected = ["aaa\n", "_1a_\n", "_2b_\n"]
    lines = ["aaa\n", "_1_\n", "_2_\n"]
    insertions = [
        Insertion(text="a", line_number=2, label="...", inline=True, col=3),
        Insertion(text="b", line_number=3, label="...", inline=True, col=3),
    ]
    assert list(insert_in_lines(lines, insertions)) == expected

def test_insert_in_lines_regression():
    code = """
def foo(a):
    pass
    """
    expected_code = """
def foo(a: int) -> None:
    pass
    """
    lines = code.splitlines(True)
    expected = expected_code.splitlines(True)
    insertions = [
        Insertion(text=": int", line_number=2, col=10, inline=True, label="foo"),
        Insertion(text=" -> None", line_number=2, col=11, inline=True, label="foo"),
    ]
    assert list(insert_in_lines(lines, insertions)) == expected
