import tempfile
from typing import Iterable
from dataclasses import dataclass
import os
import itertools
from pathlib import Path
from charset_normalizer import from_path
import rich_click as click


@dataclass
class Insertion:
    text: str
    line_number: int
    label: str
    col: int = -1  # Use with `inline`
    inline: bool = False  # Insert into existing line instead of adding new line


def partition(pred, iterable):
    "Use a predicate to partition entries into false entries and true entries"
    # partition(is_odd, range(10)) --> 0 2 4 6 8   and  1 3 5 7 9
    t1, t2 = itertools.tee(iterable)
    return itertools.filterfalse(pred, t1), filter(pred, t2)


def insert_in_lines(lines: Iterable[str], insertions: Iterable[Insertion]):
    lines = iter(lines)
    last_line = 1
    insertion_groups = itertools.groupby(insertions, key=lambda ins: ins.line_number)
    for line_number, insertion_group in insertion_groups:
        for line in itertools.islice(lines, line_number - last_line):
            yield line
            last_line += 1
        full_insertions, inline_insertions = partition(
            lambda ins: ins.inline, insertion_group
        )
        for insertion in full_insertions:
            yield insertion.text + "\n"

        line_to_edit = None
        col_offset = 0
        for insertion in inline_insertions:
            if not line_to_edit:
                line_to_edit = next(lines, "")
            col = insertion.col + col_offset
            col_offset += len(insertion.text)
            line_to_edit = line_to_edit[:col] + insertion.text + line_to_edit[col:]
        if line_to_edit:
            yield line_to_edit
            last_line += 1
    yield from lines


class SourceFile:
    def __init__(self, path: str):
        self.path = path
        self.encoding = None
        self._initial_modified_time = os.path.getmtime(path)

    def load_source_as_utf8(self):
        loaded = from_path(self.path)
        best_guess = loaded.best()
        self.encoding = best_guess.encoding
        return best_guess.output(encoding="utf_8")

    def is_unicode(self):
        return self.encoding.startswith("utf")

    def update_file(self, insertions: Iterable[Insertion], suffix: str) -> None:
        path_obj = Path(self.path)
        with path_obj.open("r", encoding=self.encoding) as filehandle:
            if self.modified_after_loaded():
                raise click.FileError(
                    self.path, "File was externally modified, try again."
                )
            new_lines = list(insert_in_lines(lines=filehandle, insertions=insertions))
            out_file = path_obj.with_suffix(f"{path_obj.suffix}{suffix}")
            self._write_result(new_lines, out_file)

    def _write_result(self, lines: list, output_file: Path) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            my_tempfile: Path = Path(tempdir) / "output.txt"
            with my_tempfile.open("w") as filehandle:
                for line in lines:
                    filehandle.write(line)
            my_tempfile.replace(output_file)

    def modified_after_loaded(self) -> bool:
        return os.path.getmtime(self.path) > self._initial_modified_time
