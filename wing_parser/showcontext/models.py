"""Frozen records for one show's context.

Deliberately dumb. Everything derived lives in view.py, resolved against
a scene; a record here states only what the file said.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Cue:
    id: str
    action: str
    channels: tuple[int, ...] = ()
    dcas: tuple[int, ...] = ()
    time: str | None = None
    note: str = ""


@dataclass(frozen=True)
class Segment:
    id: str
    title: str = ""
    time: str | None = None
    expects: tuple[str, ...] = ()
    cues: tuple[Cue, ...] = ()
    sound: str = ""
    lighting: str = ""
    led: str = ""


@dataclass(frozen=True)
class ShowContext:
    show: str
    date: str | None = None
    segments: tuple[Segment, ...] = ()
    anomalies: tuple[str, ...] = field(default_factory=tuple)
    path: Path | None = None
