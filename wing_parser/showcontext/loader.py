"""Read a show-context YAML file into records.

Structural problems raise, naming the file and the segment: a duplicate
id or an unresolvable kind means the document says something the tool
cannot act on, and finding that out on show day beats acting on a guess.
A malformed optional field becomes an anomaly instead -- `time:` feeds
only Q7, which ships disabled, and failing the other six rules over one
mistyped clock cell is the wrong trade (spec section 7).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from wing_parser.classifier.matcher import known_kinds
from wing_parser.showcontext import vocabulary
from wing_parser.showcontext.models import Cue, Segment, ShowContext

# "T-12:00" or "T+1:04:30" -- the ROS column-1 format from
# docs/knowledge-base/04-templates-and-matrices/Master-Run-Of-Show-ROS.md.
# Parsed by hand rather than by regex; the repo bans building regexes in
# generated code and this is simple enough not to need one.


def _parse_time(text: str) -> int | None:
    """Show-relative time to signed seconds, or None if unreadable."""
    if not isinstance(text, str) or len(text) < 2 or text[0] not in "Tt":
        return None
    sign = text[1]
    if sign not in "+-":
        return None
    parts = text[2:].split(":")
    if not 2 <= len(parts) <= 3:
        return None
    try:
        numbers = [int(part) for part in parts]
    except ValueError:
        return None
    if any(number < 0 for number in numbers):
        return None
    while len(numbers) < 3:
        numbers.insert(0, 0)
    hours, minutes, seconds = numbers
    total = hours * 3600 + minutes * 60 + seconds
    return -total if sign == "-" else total


def _numbers(raw, where: str, field: str) -> tuple[int, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(f"{where}: {field} must be a list, not {type(raw).__name__}")
    out: list[int] = []
    for item in raw:
        if not isinstance(item, int) or isinstance(item, bool):
            raise ValueError(f"{where}: {field} entry {item!r} is not a whole number")
        out.append(item)
    return tuple(out)


def _list_of(raw, where: str, field: str) -> list:
    """Guard a field that must be a YAML list before iterating it.

    `raw.get(field) or []` only guards falsiness, not type -- a scalar
    like `segments: 5` or `cues: 3` is truthy and not iterable, so it
    would reach a bare `for` loop and raise `TypeError: 'int' object is
    not iterable`, a traceback with no file name in it. And a bare string
    like `expects: instrument.keys` (the brackets left off a one-item
    list, the single most likely slip in this format) is truthy *and*
    iterable -- it would iterate its characters one at a time instead of
    raising here at all. Both cases are caught the same way: only a list
    is accepted, everything else names the file, the field, and what it
    actually got.
    """
    if raw is None:
        return []
    if not isinstance(raw, list):
        hint = ""
        if isinstance(raw, str):
            hint = " (missing the [ ] brackets around a one-item list?)"
        raise ValueError(
            f"{where}: {field} must be a list, not {type(raw).__name__}{hint}"
        )
    return raw


def parse_show_context(doc: dict, where_from: Path) -> ShowContext:
    if not isinstance(doc, dict):
        raise ValueError(f"{where_from}: the file must be a mapping at the top level")

    anomalies: list[str] = []
    kinds = known_kinds("channels")
    segments: list[Segment] = []
    seen_segments: set[str] = set()

    for entry in _list_of(doc.get("segments"), where_from, "segments"):
        if not isinstance(entry, dict):
            raise ValueError(f"{where_from}: each segment must be a mapping")
        segment_id = str(entry.get("id") or "").strip()
        if not segment_id:
            raise ValueError(f"{where_from}: a segment is missing its 'id'")
        if segment_id.lower() in seen_segments:
            raise ValueError(f"{where_from}: duplicate segment id {segment_id!r}")
        seen_segments.add(segment_id.lower())
        where = f"{where_from}: segment {segment_id}"

        expects: list[str] = []
        for written in _list_of(entry.get("expects"), where, "expects"):
            try:
                resolved = vocabulary.resolve(str(written), kinds, what="kind")
            except ValueError as exc:
                raise ValueError(f"{where}: {exc}") from exc
            if resolved.repaired:
                anomalies.append(
                    f"{where}: expects {resolved.original!r} read as {resolved.value!r}"
                )
            expects.append(resolved.value)

        cues: list[Cue] = []
        seen_cues: set[str] = set()
        for raw_cue in _list_of(entry.get("cues"), where, "cues"):
            if not isinstance(raw_cue, dict):
                raise ValueError(f"{where}: each cue must be a mapping")
            cue_id = str(raw_cue.get("id") or "").strip()
            if not cue_id:
                raise ValueError(f"{where}: a cue is missing its 'id'")
            collapsed = "".join(cue_id.split()).lower()
            if collapsed in seen_cues:
                raise ValueError(f"{where}: duplicate cue id {cue_id!r}")
            seen_cues.add(collapsed)

            try:
                action = vocabulary.resolve(
                    str(raw_cue.get("action") or ""), vocabulary.KNOWN_ACTIONS, what="action"
                )
            except ValueError as exc:
                raise ValueError(f"{where}, cue {cue_id}: {exc}") from exc
            if action.repaired:
                anomalies.append(
                    f"{where}, cue {cue_id}: action {action.original!r} "
                    f"read as {action.value!r}"
                )

            written_time = raw_cue.get("time")
            seconds = _parse_time(written_time) if written_time is not None else None
            if written_time is not None and seconds is None:
                anomalies.append(
                    f"{where}, cue {cue_id}: time {written_time!r} is not "
                    "T+H:MM:SS or T-MM:SS and was ignored"
                )

            cues.append(Cue(
                id=cue_id,
                action=action.value,
                channels=_numbers(raw_cue.get("channels"), where, "channels"),
                dcas=_numbers(raw_cue.get("dcas"), where, "dcas"),
                time=written_time if seconds is not None else None,
                note=str(raw_cue.get("note") or ""),
            ))

        segment_time = entry.get("time")
        if segment_time is not None and _parse_time(segment_time) is None:
            anomalies.append(f"{where}: time {segment_time!r} is not readable and was ignored")
            segment_time = None

        segments.append(Segment(
            id=segment_id,
            title=str(entry.get("title") or ""),
            time=segment_time,
            expects=tuple(expects),
            cues=tuple(cues),
        ))

    return ShowContext(
        show=str(doc.get("show") or where_from.stem),
        date=str(doc["date"]) if doc.get("date") else None,
        segments=tuple(segments),
        anomalies=tuple(anomalies),
        path=where_from,
    )


def load_show_context(path: str | Path) -> ShowContext:
    where_from = Path(path)
    if not where_from.is_file():
        raise ValueError(f"no show context file at {where_from}")
    try:
        doc = yaml.safe_load(where_from.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"{where_from}: invalid YAML: {exc}") from exc
    return parse_show_context(doc, where_from)
