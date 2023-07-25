from menderbot.code import function_indent, line_indent, reindent


def test_line_indent_spaces():
    source = """    def foo():
        pass"""
    expected = "    "

    assert line_indent(source) == expected


def test_line_indent_spaces():
    source = """\tdef foo():\n\t\tpass"""
    expected = "\t"

    assert line_indent(source) == expected


def test_function_indent_single_line():
    source = """  def foo():\n    pass"""
    expected = "    "

    assert function_indent(source) == expected


def test_function_indent_multiline():
    source = """  def foo():\n    a=1\n    return a"""
    expected = "    "

    assert function_indent(source) == expected


def test_reindent():
    source = """ a\n b\n c"""
    expected = """  a\n  b\n  c"""

    assert reindent(source, "  ") == expected
