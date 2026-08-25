"""Proposing a column mapping -- and refusing to trust the proposal.

check_proposal re-reads the workbook and verifies every claim.
propose_mapping sits between the model and the human; nothing unchecked
reaches either.
"""

from __future__ import annotations

import json
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
    problems: list[str] = []

    if not isinstance(header_row, int) or isinstance(header_row, bool) or header_row < 1:
        return (f"header_row {header_row!r} is not a row number.",)

    blocks: dict[str, dict] = {}
    for key in ("columns", "headers"):
        value = raw.get(key)
        if value is None:
            blocks[key] = {}
        elif isinstance(value, dict):
            blocks[key] = value
        else:
            return (f"{key} must be an object, got {type(value).__name__}.",)

    try:
        read = sheet_mod.read_sheet(xlsx_path, name, header_row)
    except ValueError as exc:
        return (f"sheet {name!r}: {exc}",)

    for field, letter in sorted(blocks["columns"].items()):
        upper = str(letter).strip().upper()
        if upper not in read.headers and upper != read.last_column:
            problems.append(
                f"column {field}:{upper} has no text on the header row and is "
                f"past the sheet's extent ({read.last_column})."
            )
    if REQUIRED_COLUMN not in blocks["columns"]:
        problems.append(f"{REQUIRED_COLUMN!r} must be among the proposed columns.")
    return tuple(problems)


SYSTEM_PROMPT = (
    "You are proposing how to read a producer's event-running-order "
    "spreadsheet as structured rows. You see each sheet's name and its "
    "first rows rendered as LETTER+ROW='text'. Pick the sheet that is the "
    "actual rundown, find the header row, and map columns. Map id/time/"
    "title by letter; map performers/note/sound/lighting/led by exact "
    "header text. Leave a field out rather than guess wrong. Reply with "
    "json in the requested shape only."
)

PROPOSAL_SCHEMA = {
    "type": "object",
    "properties": {
        "sheet": {"type": "string"},
        "header_row": {"type": "number"},
        "columns": {"type": "string"},   # JSON-encoded dict; see _decode
        "headers": {"type": "string"},   # dialect has no object values
    },
    "required": ["sheet", "header_row", "columns"],
}


class _Encoded:
    """A Provider whose nested-object replies travel as JSON strings.

    The schema dialect is flat, so `columns`/`headers` are declared
    string-typed -- but an adapter that parses raw JSON (the OpenAI-
    compatible one does) can hand back native dicts. Flattening them
    here lets one validation path serve both shapes instead of letting
    a good proposal die as schema-invalid.
    """

    def __init__(self, inner):
        self.inner = inner

    def complete_json(self, system: str, user: str, schema: dict) -> dict:
        reply = self.inner.complete_json(system, user, schema)
        return {
            key: json.dumps(value, ensure_ascii=False)
            if isinstance(value, dict)
            else value
            for key, value in reply.items()
        }


def _decode(reply: dict) -> dict:
    """The dialect is flat, so nested dicts travel as JSON-encoded strings."""
    decoded = {
        "sheet": str(reply["sheet"]),
        "header_row": int(float(reply["header_row"])),
    }
    for key in ("columns", "headers"):
        value = reply.get(key)
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                pass  # left as the raw string; the checker reports it
        if value is not None:
            decoded[key] = value
    return decoded


def _resolve_problems(raw: dict, xlsx_path) -> tuple[str, ...]:
    """Header-text claims are consumed the way the import pipeline will.

    check_proposal trusts letters only after seeing text on them;
    resolve_columns goes further and re-finds every header-text claim on
    the real row -- the same consumption the build step performs later.
    """
    from wing_parser.showcontext.ingest import mapping, sheet as sheet_mod

    try:
        read = sheet_mod.read_sheet(xlsx_path, raw["sheet"], raw["header_row"])
    except ValueError as exc:
        return (f"sheet {raw['sheet']!r}: {exc}",)
    try:
        mapping.resolve_columns(
            mapping.RawMapping(
                source="<proposal>",
                sheet=raw["sheet"],
                header_row=raw["header_row"],
                columns=raw.get("columns") or {},
                headers=raw.get("headers") or {},
            ),
            read.headers,
            read.last_column,
        )
    except ValueError as exc:
        return (str(exc),)
    return ()


def propose_mapping(xlsx_path, provider):
    from wing_parser.classifier.provider import complete_json
    from wing_parser.showcontext.ingest.sample import sample_workbook

    samples = sample_workbook(xlsx_path)
    rendered = "\n\n".join(
        f"SHEET {s.name!r}:\n" + "\n".join(s.lines) for s in samples
    )
    user = f"Sheets:\n{rendered}\n\nPropose the mapping."
    problems: tuple[str, ...] = ()
    reply: dict = {}
    for _attempt in range(2):
        sent = user if not problems else (
            f"{user}\n\nYour previous reply was rejected: {'; '.join(problems)}"
        )
        reply = complete_json(_Encoded(provider), SYSTEM_PROMPT, sent, PROPOSAL_SCHEMA)
        decoded = _decode(reply)
        problems = check_proposal(decoded, xlsx_path)
        if not problems:
            problems = _resolve_problems(decoded, xlsx_path)
        if not problems:
            break
    decoded = _decode(reply)
    return MappingProposal(
        sheet=decoded["sheet"],
        header_row=decoded["header_row"],
        columns=decoded.get("columns", {}),
        headers=decoded.get("headers", {}),
        problems=tuple(problems),
    )
