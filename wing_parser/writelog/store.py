"""Append-only per-show JSONL store under ``<knowledge_dir>/write-log/``."""

from __future__ import annotations

import json
import warnings
from dataclasses import dataclass
from pathlib import Path

from wing_parser import config

from .codes import normalize_code
from .entry import ENTRY_VERSION, LogEntry, ts_key


@dataclass
class ShowSummary:
    code: str
    show: str | None
    venue: str | None
    first_ts: str
    last_ts: str
    writes: int
    sent: int
    clamped: int
    no_reply: int
    reverts: int
    skipped: int


def log_dir(directory: Path | None = None) -> Path:
    return config.knowledge_dir(directory) / "write-log"


def _file(code: str, directory: Path | None) -> Path:
    safe = normalize_code(code)
    if safe is None or safe != code:
        raise ValueError(f"invalid show code: {code!r}")
    return log_dir(directory) / f"{safe}.jsonl"


def append(entry: LogEntry, directory: Path | None = None) -> None:
    """Append one line. Raises on failure; the caller decides what to do."""
    path = _file(entry.show_code, directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry.to_json(), ensure_ascii=False) + "\n")
        handle.flush()


def read_show(code: str, directory: Path | None = None) -> tuple[list[LogEntry], int]:
    """Return ``(entries, skipped_line_count)`` for one show."""
    path = _file(code, directory)
    if not path.exists():
        return [], 0
    entries: list[LogEntry] = []
    skipped = 0
    text = path.read_text(encoding="utf-8")
    for number, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            if not isinstance(data, dict) or data.get("v") != ENTRY_VERSION:
                raise ValueError(f"unknown entry version {data.get('v') if isinstance(data, dict) else None!r}")
            entries.append(LogEntry.from_json(data))
        except (ValueError, TypeError) as unreadable:
            skipped += 1
            warnings.warn(
                f"{path}:{number}: skipping unreadable write-log entry ({unreadable})",
                stacklevel=2,
            )
    return entries, skipped


def list_shows(directory: Path | None = None) -> list[ShowSummary]:
    """One summary per show file, newest ``last_ts`` first."""
    root = log_dir(directory)
    if not root.is_dir():
        return []
    shows: list[ShowSummary] = []
    for path in sorted(root.glob("*.jsonl")):
        code = path.stem
        if normalize_code(code) != code:
            continue
        entries, skipped = read_show(code, directory)
        if not entries and not skipped:
            continue
        stamps = sorted((e.ts for e in entries), key=ts_key)
        named = next((e for e in reversed(entries) if e.show or e.venue), None)
        shows.append(ShowSummary(
            code=code,
            show=named.show if named else None,
            venue=named.venue if named else None,
            first_ts=stamps[0] if stamps else "",
            last_ts=stamps[-1] if stamps else "",
            writes=len(entries),
            sent=sum(e.outcome == "sent" for e in entries),
            clamped=sum(e.outcome == "clamped" for e in entries),
            no_reply=sum(e.outcome == "no_reply" for e in entries),
            reverts=sum(e.kind == "revert" for e in entries),
            skipped=skipped,
        ))
    shows.sort(key=lambda s: ts_key(s.last_ts), reverse=True)
    return shows
