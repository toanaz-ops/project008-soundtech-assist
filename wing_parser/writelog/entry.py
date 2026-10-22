"""One settled write or revert, as stored on one JSONL line."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import datetime
from typing import Any

ENTRY_VERSION = 1


def now_ts() -> str:
    """Local time with UTC offset, millisecond precision."""
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


def ts_key(ts: str) -> tuple[int, float, str]:
    """Sort key for stored timestamps: chronological, not lexical.

    ``2026-10-20T23:00+07:00`` and ``2026-10-20T20:00+00:00`` are different
    instants whose strings order the other way round. A stamp that does not
    parse sorts before every parseable one, by its raw text.
    """
    try:
        return (1, datetime.fromisoformat(ts).astimezone().timestamp(), "")
    except (TypeError, ValueError, OverflowError, OSError):
        return (0, 0.0, str(ts))


@dataclass(frozen=True)
class LogEntry:
    v: int
    ts: str
    show_code: str
    show: str | None
    venue: str | None
    desk: dict | None
    kind: str  # "repair" | "revert"
    finding: str | None
    label: str
    address: str
    path: str
    file_before: Any
    desk_before: Any
    written: Any
    readback: Any
    outcome: str  # "sent" | "clamped" | "no_reply"
    scene: str | None
    app: str

    def to_json(self) -> dict:
        return asdict(self)

    @classmethod
    def from_json(cls, data: dict) -> "LogEntry":
        names = {f.name for f in fields(cls)}
        if not isinstance(data, dict) or set(data) != names:
            raise TypeError("log entry keys do not match LogEntry")
        for key in ("ts", "show_code", "kind", "outcome"):
            if not isinstance(data[key], str):
                raise TypeError(f"log entry field {key!r} must be a string")
        if data["desk"] is not None and not isinstance(data["desk"], dict):
            raise TypeError("log entry field 'desk' must be an object or null")
        return cls(**data)
