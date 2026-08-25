"""A workbook reduced to what a model can judge layout from.

Only the first `sample_rows` rows of up to `max_sheets` sheets are
rendered, as letter=row=text triples truncated to 40 chars. This is the
~20-line header sample the design spec promises the proposer: enough to
find a header row and name columns, not enough to leak a client's whole
running order into a prompt.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from wing_parser.showcontext.ingest.sheet import worksheet_for, _text

MAX_CELL = 40


@dataclass(frozen=True)
class SheetSample:
    name: str
    lines: tuple[str, ...]


def _line(letter: str, row_number: int, value: str) -> str:
    clipped = value[:MAX_CELL]
    return f"{letter}{row_number}='{clipped}'"


def sample_workbook(path, *, max_sheets=6, sample_rows=20):
    from openpyxl import load_workbook
    from openpyxl.utils import get_column_letter

    book = load_workbook(Path(path), data_only=True, read_only=True)
    try:
        samples = []
        for worksheet in book.worksheets[:max_sheets]:
            lines: list[str] = []
            for row_number, row in enumerate(worksheet.iter_rows(values_only=True), 1):
                if row_number > sample_rows:
                    break
                for index, cell in enumerate(row, start=1):
                    text = _text(cell)
                    if text:
                        lines.append(_line(get_column_letter(index), row_number, text))
            samples.append(SheetSample(name=worksheet.title, lines=tuple(lines)))
        return tuple(samples)
    finally:
        book.close()
