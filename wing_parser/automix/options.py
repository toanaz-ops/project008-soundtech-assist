"""Value types of the automix engine: options in, proposal out.

No logic lives here beyond input validation, so the UI and the tests can
import the shapes without pulling in the knowledge tables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

GENRES = ("pop", "rock", "ballad", "jazz", "edm", "bolero", "speech")
STAGES = ("hpf", "eq", "gate", "comp", "fader", "fx", "sends", "inserts")
VENUES = ("small", "medium", "large")


@dataclass(frozen=True)
class AutomixOptions:
    genre: str
    bpm: float = 120.0
    venue: str = "medium"
    strength: float = 1.0  # 0..1, how far from current toward target
    stages: frozenset = frozenset(STAGES)
    min_confidence: float = 0.8  # classifier HIGH; below -> skipped row
    lead_channels: tuple = ()  # empty -> heuristic (AM-8)

    def __post_init__(self) -> None:
        if self.genre not in GENRES:
            raise ValueError(f"unknown genre {self.genre!r}; expected one of {GENRES}")
        if self.venue not in VENUES:
            raise ValueError(f"unknown venue {self.venue!r}; expected one of {VENUES}")
        if not 0.0 <= self.strength <= 1.0:
            raise ValueError(f"strength {self.strength} outside 0..1")
        if self.bpm <= 0:
            raise ValueError("bpm must be positive")
        unknown = set(self.stages) - set(STAGES)
        if unknown:
            raise ValueError(f"unknown stages {sorted(unknown)}")


@dataclass(frozen=True)
class Change:
    path: str  # full pointer path, "ae_data.ch.5.eq.1g"
    before: Any
    after: Any
    stage: str
    target: str  # "ch.5" / "fx.2"
    label: str  # short English label (the UI translates stage names)
    why: str  # one sentence, English
    sources: tuple = ()
    confidence: str = "eng_default"


@dataclass(frozen=True)
class Suggestion:
    """Cannot be expressed as a Patch (e.g. load PLATE into an empty slot)."""

    stage: str
    target: str
    text: str
    sources: tuple = ()


@dataclass(frozen=True)
class Skipped:
    target: str
    reason: str


@dataclass(frozen=True)
class Proposal:
    options: AutomixOptions
    changes: tuple = ()
    suggestions: tuple = ()
    skipped: tuple = ()
    headroom_trim_db: float = 0.0
    warnings: tuple = field(default=())  # owner-layer entries that were ignored
