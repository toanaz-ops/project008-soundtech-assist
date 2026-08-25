"""Proposing a column mapping -- and refusing to trust the proposal.

check_proposal re-reads the workbook and verifies every claim. The
proposer (Task 9) calls this between the model and the human; nothing
unchecked reaches either.
"""

from __future__ import annotations

from dataclasses import dataclass

REQUIRED_COLUMN = "title"


@dataclass(frozen=True)
class MappingProposal:
    sheet: str
    header_row: int
    columns: dict[str, str]
    headers: dict[str, str]
    problems: tuple[str, ...]


def check_proposal(raw: dict, xlsx_path) -> tuple[str, ...]:
    from wing_parser.showcontext.ingest import sheet as sheet_mod

    name = raw.get("sheet")
    header_row = raw.get("header_row")
    columns = raw.get("columns") or {}
    problems: list[str] = []

    if not isinstance(header_row, int) or isinstance(header_row, bool) or header_row < 1:
        return (f"header_row {header_row!r} is not a row number.",)

    try:
        read = sheet_mod.read_sheet(xlsx_path, name, header_row)
    except ValueError as exc:
        return (f"sheet {name!r}: {exc}",)

    for field, letter in sorted(columns.items()):
        upper = str(letter).strip().upper()
        if upper not in read.headers and upper != read.last_column:
            problems.append(
                f"column {field}:{upper} has no text on the header row and is "
                f"past the sheet's extent ({read.last_column})."
            )
    if REQUIRED_COLUMN not in columns:
        problems.append(f"{REQUIRED_COLUMN!r} must be among the proposed columns.")
    return tuple(problems)
