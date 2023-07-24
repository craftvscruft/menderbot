from menderbot.source_file import Insertion, insert_in_lines


def test_insert_in_lines_empty():
    expected = []
    lines = []
    insertions = []
    assert list(insert_in_lines(lines, insertions)) == expected


def test_insert_in_lines_insert_middle():
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
    insertions = [Insertion(text="b", line_number=2, label="...", inline=True, col=1)]
    assert list(insert_in_lines(lines, insertions)) == expected


def test_insert_in_lines_insert_inline_muliple_in_one_line():
    expected = ["aaa\n", "_1a_2b_\n", "ccc\n"]
    lines = ["aaa\n", "_1_2_\n", "ccc\n"]
    insertions = [
        Insertion(text="a", line_number=2, label="...", inline=True, col=2),
        Insertion(text="b", line_number=2, label="...", inline=True, col=4),
    ]
    assert list(insert_in_lines(lines, insertions)) == expected


def test_insert_in_lines_insert_inline_muliple_line():
    expected = ["aaa\n", "_1a_\n", "_2b_\n"]
    lines = ["aaa\n", "_1_\n", "_2_\n"]
    insertions = [
        Insertion(text="a", line_number=2, label="...", inline=True, col=2),
        Insertion(text="b", line_number=3, label="...", inline=True, col=2),
    ]
    assert list(insert_in_lines(lines, insertions)) == expected
