import tempfile
from typing import Iterable
from dataclasses import dataclass
import os
import itertools
from pathlib import Path
from charset_normalizer import from_path


@dataclass
class Insertion:
    text: str
    line_number: int
    label: str


def insert_in_lines(lines: Iterable[str], insertions: Iterable[Insertion]):
    lines = iter(lines)
    last_line = 1
    for insertion in insertions:
        for line in itertools.islice(lines, insertion.line_number - last_line):
            yield line
            last_line += 1
        yield insertion.text
        yield "\n"
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

    def update_file(self, insertions: Iterable[Insertion], suffix):
        path_obj = Path(self.path)
        with path_obj.open("r", encoding=self.encoding) as filehandle:
            if self.modified_after_loaded():
                raise Exception(
                    f"File '{self.path}' was externally modified, try again."
                )
            new_lines = list(insert_in_lines(lines=filehandle, insertions=insertions))
            out_file = path_obj.with_suffix(f"{path_obj.suffix}{suffix}")
            self._write_result(new_lines, out_file)

    def _write_result(self, lines, output_file: Path):
        with tempfile.TemporaryDirectory() as tempdir:
            my_tempfile: Path = Path(tempdir) / "output.txt"
            with my_tempfile.open("w") as filehandle:
                for line in lines:
                    filehandle.write(line)
            my_tempfile.replace(output_file)

    def modified_after_loaded(self):
        return os.path.getmtime(self.path) > self._initial_modified_time
