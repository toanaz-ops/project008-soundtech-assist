"""Rows and a vocabulary become Segment records. No I/O happens here.

The vocabulary lookup arrives as a callable rather than an import, which
is what keeps every interpretation decision in this file testable without
a filesystem -- and what keeps the module honest about performing no
reads of its own.

Nothing is ever guessed. A fragment that does not resolve confidently
becomes a verbatim comment, because a weak guess entering `expects:`
would make Q4 stop catching the thing it exists for -- the same argument
Q4's own rationale makes about channel classification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from wing_parser.classifier import matcher
from wing_parser.classifier.normalize import clean
from wing_parser.showcontext.models import Segment

_SPLIT = re.compile(r"[,/;\n]+")


@dataclass(frozen=True)
class BuiltSegment:
    segment: Segment
    comments: tuple[str, ...]


@dataclass(frozen=True)
class BuildResult:
    segments: tuple[BuiltSegment, ...]
    loose_comments: tuple[str, ...]
    data_rows: int
    comment_rows: int
    blank_rows: int


def resolve_fragment(fragment: str, lookup) -> str | None:
    """Vocabulary first, pattern matcher second, nothing third."""
    target = clean(fragment)
    if not target:
        return None

    remembered = lookup(target)
    if remembered is not None and matcher.is_confident(remembered):
        return remembered.kind

    found = matcher.classify(fragment, "channels")
    if matcher.is_confident(found):
        return found.kind

    return None


def _cell(row, mapping, field: str) -> str:
    letter = mapping.fields.get(field)
    if letter is None:
        return ""
    return row.cells.get(letter, "")


def _expectations(text: str, lookup, row_number: int) -> tuple[tuple[str, ...],
                                                               tuple[str, ...]]:
    kinds: list[str] = []
    comments: list[str] = []
    for fragment in _SPLIT.split(text):
        stripped = fragment.strip()
        if not stripped:
            continue
        kind = resolve_fragment(stripped, lookup)
        if kind is None:
            comments.append(
                f"row {row_number}: could not read performer {stripped!r}"
            )
        elif kind not in kinds:
            kinds.append(kind)
    return tuple(kinds), tuple(comments)


def build(rows, mapping, lookup, blank_rows: int = 0) -> BuildResult:
    built: list[BuiltSegment] = []
    loose: list[str] = []
    generated = 0

    for row in rows:
        title = _cell(row, mapping, "title").strip()
        performers = _cell(row, mapping, "performers")
        note = _cell(row, mapping, "note").strip()
        written_time = _cell(row, mapping, "time").strip()

        if not title:
            parts = [
                f"{name}={value!r}"
                for name, value in (
                    ("performers", performers.strip()),
                    ("note", note),
                    ("time", written_time),
                )
                if value
            ]
            loose.append(
                f"row {row.number}: no title, kept as a comment"
                + (" -- " + ", ".join(parts) if parts else "")
            )
            continue

        kinds, comments = _expectations(performers, lookup, row.number)
        notes = list(comments)
        if written_time:
            notes.insert(0, f"row {row.number}: time {written_time!r}")
        if note:
            notes.append(f"row {row.number}: note {note!r}")

        written_id = _cell(row, mapping, "id").strip()
        if not written_id:
            generated += 1
            written_id = f"S{generated}"

        built.append(
            BuiltSegment(
                segment=Segment(id=written_id, title=title, expects=kinds),
                comments=tuple(notes),
            )
        )

    return BuildResult(
        segments=tuple(built),
        loose_comments=tuple(loose),
        data_rows=len(rows),
        comment_rows=len(loose),
        blank_rows=blank_rows,
    )
