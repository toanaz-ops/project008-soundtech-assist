"""Rows and a vocabulary become Segment records. This module opens no file
of its own -- it takes no path, no scene, and no knowledge directory. The
pattern matcher it calls into (`wing_parser.classifier.matcher.classify`)
does read `patterns.yaml` from disk on first use, cached for the rest of
the process; that read is the matcher's business, not this module's.

The vocabulary lookup arrives as a callable rather than an import, which
is what keeps every interpretation decision in this file testable without
a filesystem -- and what keeps this module's own tests free of fixtures
on disk.

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
    unreadable_performers: int = 0

    @property
    def expectations(self) -> int:
        """How many `expects:` entries the segments carry in total.

        Counted from the segments rather than stored beside them, so it
        cannot drift from what was actually built. It is reported because
        `performers:` is optional (design spec section 4): a mapping that
        omits it gives every segment an empty `expects:`, and without
        this number that file is indistinguishable -- at the summary, the
        trailer and a `doctor --show` run alike -- from having imported
        no show context at all.
        """
        return sum(len(built.segment.expects) for built in self.segments)


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


def _fold(segment_id: str) -> str:
    """The loader's own collision rule, borrowed so the two cannot disagree.

    `wing_parser/showcontext/loader.py:104` refuses a file whose segment
    ids collide after `.lower()`. Folding any other way here would let
    this module emit a file the project's own loader then rejects.
    """
    return segment_id.lower()


def _unique(wanted: str, used: set[str]) -> str:
    """`S1` again becomes `S1-2`, then `S1-3`. Never silently."""
    suffix = 2
    while _fold(f"{wanted}-{suffix}") in used:
        suffix += 1
    return f"{wanted}-{suffix}"


def build(rows, mapping, lookup, blank_rows: int = 0,
          *, headers: dict[str, str] | None = None) -> BuildResult:
    """Segment ids are unique here, and every consumer downstream needs that.

    `propose.for_segments` returns a dict keyed by segment id and
    `emit.render` looks each segment's proposal up by the same key, so a
    repeated id would hand one segment's channel numbers to another --
    printing `# --scene: ch 25 'Bass' is instrument.bass` above a segment
    expecting a guitar. That is a statement the sheet does not make, in
    the one place it is meant to be read literally.
    """
    built: list[BuiltSegment] = []
    loose: list[str] = []
    unreadable = 0
    generated = 0
    used: set[str] = set()

    for row in rows:
        title = _cell(row, mapping, "title").strip()
        performers = _cell(row, mapping, "performers")
        note = _cell(row, mapping, "note").strip()
        sound = _cell(row, mapping, "sound").strip()
        lighting = _cell(row, mapping, "lighting").strip()
        led = _cell(row, mapping, "led").strip()
        written_time = _cell(row, mapping, "time").strip()
        written_id = _cell(row, mapping, "id").strip()

        if not title:
            parts = [
                f"{name}={value!r}"
                for name, value in (
                    ("id", written_id),
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
        unreadable += len(comments)
        notes = list(comments)
        if written_time:
            notes.insert(0, f"row {row.number}: time {written_time!r}")
        if note:
            notes.append(f"row {row.number}: note {note!r}")
        if headers is not None:
            consumed = set(mapping.fields.values())
            for letter in sorted(headers):
                if letter in consumed:
                    continue
                cell = row.cells.get(letter, "").strip()
                if cell:
                    notes.append(f"[{headers[letter]}] {cell}")

        if not written_id:
            # A generated id steps over one the sheet already spent: a
            # sheet reading S1, <blank> must not produce S1 twice.
            generated += 1
            while _fold(f"S{generated}") in used:
                generated += 1
            written_id = f"S{generated}"
        elif _fold(written_id) in used:
            taken = written_id
            written_id = _unique(taken, used)
            notes.append(
                f"row {row.number}: id {taken!r} was already used above, so "
                f"this segment was written as {written_id!r}"
            )
        used.add(_fold(written_id))

        built.append(
            BuiltSegment(
                segment=Segment(
                    id=written_id,
                    title=title,
                    expects=kinds,
                    sound=sound,
                    lighting=lighting,
                    led=led,
                ),
                comments=tuple(notes),
            )
        )

    return BuildResult(
        segments=tuple(built),
        loose_comments=tuple(loose),
        data_rows=len(rows),
        comment_rows=len(loose),
        blank_rows=blank_rows,
        unreadable_performers=unreadable,
    )
