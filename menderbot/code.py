def line_indent(line):
    count = len(line)-len(line.lstrip())
    return line[:count]

def function_indent(code):
    second_line_start = code.find('\n') + 1
    no_first_line = code[second_line_start:]
    if no_first_line.find('\n') > -1:
        second_line_end = second_line_start + no_first_line.find('\n')
        second_line = code[second_line_start:second_line_end]
    else:
        second_line = no_first_line
    return line_indent(second_line)

def reindent(text, indent):
    lines = text.split('\n')
    indented_lines = [indent + line.lstrip() for line in lines]
    return '\n'.join(indented_lines)