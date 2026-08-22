"""A hand-written per-client mapping file, resolved to column letters.

Two blocks, never one. A single block would have to decide whether STT
means "column STT" or "the header cell reading STT", and Vietnamese
running orders head their first column STT often enough that either
answer is silently wrong on real sheets. Ambiguity is refused here, the
way showcontext/vocabulary.py refuses a tie rather than picking a side.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

FIELDS: tuple[str, ...] = ("id", "title", "time", "performers", "note")
REQUIRED: tuple[str, ...] = ("title",)

_LETTERS = re.compile(r"^[A-Z]{1,3}$")
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class RawMapping:
    source: str
    sheet: str | int | None
    header_row: int
    columns: dict[str, str]
    headers: dict[str, str]
    path: Path | None = None


@dataclass(frozen=True)
class SheetMapping:
    source: str
    fields: dict[str, str]


def _normalise(text: str) -> str:
    return _WHITESPACE.sub(" ", (text or "").strip()).casefold()


def _section(doc, name: str, where: str) -> dict[str, str]:
    section = doc.get(name)
    if section is None:
        return {}
    if not isinstance(section, dict):
        raise ValueError(
            f"{where}: {name}: must be a mapping of field name to value, "
            f"but it is {type(section).__name__}."
        )
    return {str(key): str(value) for key, value in section.items()}


def load_mapping(path: str | Path) -> RawMapping:
    """Shape only. Column resolution needs the header row and happens later.

    A YAML syntax error becomes the same ValueError shape every other
    load-time problem here raises, instead of a bare `yaml.YAMLError` the
    CLI is not set up to catch -- the same convention `advisory/loader.py`
    and `showcontext/loader.py` already use for a hand-edited file.
    """
    where_from = Path(path)
    try:
        doc = yaml.safe_load(where_from.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ValueError(f"{where_from}: invalid YAML: {exc}") from exc
    where = str(where_from)

    if not isinstance(doc, dict):
        raise ValueError(
            f"{where}: the top level must be a mapping with header_row: and "
            f"at least one of columns: or headers:, but it is "
            f"{type(doc).__name__}."
        )

    header_row = doc.get("header_row")
    if not isinstance(header_row, int) or isinstance(header_row, bool) or header_row < 1:
        raise ValueError(
            f"{where}: header_row: is required and must be a whole number of "
            f"1 or more, counted the way Excel shows it. Got {header_row!r}."
        )

    sheet = doc.get("sheet")
    if sheet is not None and not isinstance(sheet, (str, int)):
        raise ValueError(
            f"{where}: sheet: must be a name in quotes or a 1-based number, "
            f"not {type(sheet).__name__}."
        )
    if isinstance(sheet, bool):
        raise ValueError(f"{where}: sheet: must be a name or a number, not a boolean.")

    return RawMapping(
        source=str(doc.get("source", "")),
        sheet=sheet,
        header_row=header_row,
        columns=_section(doc, "columns", where),
        headers=_section(doc, "headers", where),
        path=where_from,
    )


def _by_header(name: str, wanted: str, headers: dict[str, str], where: str) -> str:
    target = _normalise(wanted)
    found = sorted(
        letter for letter, text in headers.items() if _normalise(text) == target
    )
    if len(found) == 1:
        return found[0]
    if len(found) > 1:
        raise ValueError(
            f"{where}: headers: {name}: {wanted!r} appears in more than one "
            f"column ({', '.join(found)}). Use columns: with a letter instead."
        )
    raise ValueError(
        f"{where}: headers: {name}: no column on the header row reads "
        f"{wanted!r}. That row reads: "
        + ", ".join(f"{letter}={text!r}" for letter, text in sorted(headers.items()))
        + ". Matching is exact after trimming and case-folding; it is not "
        "repaired, because the distance between real header cells has never "
        "been measured."
    )


def _index(letters: str) -> int:
    """A -> 1, Z -> 26, AA -> 27; nothing -> 0.

    sheet.py reports the sheet's last populated column as a letter, and
    letters do not compare as text: 'AA' sorts before 'B'. Spelled out
    here rather than imported so sheet.py stays the only module that
    knows openpyxl exists.
    """
    value = 0
    for char in letters:
        value = value * 26 + (ord(char) - ord("A") + 1)
    return value


def resolve_columns(raw: RawMapping, headers: dict[str, str],
                    last_column: str = "") -> SheetMapping:
    """`last_column` is how far a letter may reach past the headers.

    A column whose header cell is blank is absent from `headers` -- an
    unlabelled notes or STT column is common on a real running order, and
    is precisely the case `headers:` cannot express. Letters exist as the
    escape hatch for what headers cannot say (design spec section 4.3),
    so one is accepted anywhere inside the sheet's extent and refused
    only past it. A caller that passes no extent gets the furthest header
    instead -- that is all such a caller has said the sheet contains, and
    an error naming it is at least true.
    """
    where = str(raw.path) if raw.path else "<mapping>"
    reach_to = last_column or (max(headers, key=_index) if headers else "")
    reach = _index(reach_to)

    both = sorted(set(raw.columns) & set(raw.headers))
    if both:
        raise ValueError(
            f"{where}: {', '.join(both)} named in both columns: and headers:. "
            "Pick one block; naming a field twice is not resolved by choosing."
        )

    for name in sorted(set(raw.columns) | set(raw.headers)):
        if name not in FIELDS:
            raise ValueError(
                f"{where}: unknown field {name!r}; expected one of: "
                + ", ".join(FIELDS)
            )

    fields: dict[str, str] = {}
    for name, letter in raw.columns.items():
        upper = letter.strip().upper()
        if not _LETTERS.match(upper):
            raise ValueError(
                f"{where}: columns: {name}: {letter!r} is not a column letter. "
                "Use the letter Excel shows above the column, such as C."
            )
        if upper not in headers and _index(upper) > reach:
            raise ValueError(
                f"{where}: columns: {name}: column {upper} is past {reach_to}, "
                "the last column this sheet is known to reach. A column whose "
                "header cell is blank can still be named by its letter, but "
                "not one that is not there at all. Columns with a heading "
                "are: " + ", ".join(sorted(headers))
            )
        fields[name] = upper

    for name, wanted in raw.headers.items():
        fields[name] = _by_header(name, wanted, headers, where)

    missing = [name for name in REQUIRED if name not in fields]
    if missing:
        raise ValueError(
            f"{where}: {', '.join(missing)} must be mapped, in columns: or "
            "headers:. Without it a row has no title and cannot become a "
            "segment."
        )

    return SheetMapping(source=raw.source, fields=fields)
