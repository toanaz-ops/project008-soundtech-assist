"""One settled write or revert, as stored on one JSONL line."""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields
from datetime import datetime
from typing import Any

ENTRY_VERSION = 1


def now_ts() -> str:
    """Local time with UTC offset, millisecond precision."""
    return datetime.now().astimezone().isoformat(timespec="milliseconds")


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
        return cls(**data)
