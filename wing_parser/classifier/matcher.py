"""Pattern-based source-type and bus-role classification.

The file records only the name a human typed, so classification is a
guess. Every guess carries a confidence, and the caller decides what to
do with a weak one — the alternative, silently assuming, is how an
advisory tool starts producing confident nonsense.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from wing_parser.classifier.normalize import clean

HIGH = 0.8
LOW = 0.4

_DATA = Path(__file__).resolve().parent / "data" / "patterns.yaml"


@dataclass(frozen=True)
class Classification:
    kind: str
    confidence: float
    origin: str
    matched: str | None = None


UNKNOWN = Classification(kind="unknown", confidence=0.0, origin="none")


@lru_cache(maxsize=None)
def _compiled(domain: str) -> tuple[tuple[re.Pattern[str], str, float], ...]:
    doc = yaml.safe_load(_DATA.read_text(encoding="utf-8"))
    if domain not in doc:
        raise KeyError(f"no pattern set named {domain!r} in {_DATA}")
    return tuple(
        (re.compile(entry["match"]), entry["kind"], float(entry["confidence"]))
        for entry in doc[domain]
    )


def classify(name: str, domain: str) -> Classification:
    """Best match for a name. Ties break toward the longest matched text."""
    target = clean(name)
    if not target:
        return UNKNOWN

    best: Classification | None = None
    for pattern, kind, confidence in _compiled(domain):
        found = pattern.search(target)
        if found is None:
            continue
        candidate = Classification(
            kind=kind,
            confidence=confidence,
            origin="pattern",
            matched=found.group(0),
        )
        if best is None or _rank(candidate) > _rank(best):
            best = candidate

    return best or UNKNOWN


def _rank(c: Classification) -> tuple[float, int]:
    return (c.confidence, len(c.matched or ""))


def is_confident(c: Classification) -> bool:
    return c.confidence >= HIGH


def is_usable(c: Classification) -> bool:
    return c.confidence >= LOW


@lru_cache(maxsize=None)
def known_kinds(domain: str) -> tuple[str, ...]:
    """Every kind a pattern set can produce, sorted and deduplicated.

    `_compiled` returns compiled patterns, which is the wrong shape for a
    caller that wants the vocabulary itself -- show context validates
    `expects:` entries against it (2026-08-17 input-pipelines spec §3).
    """
    doc = yaml.safe_load(_DATA.read_text(encoding="utf-8"))
    if domain not in doc:
        raise KeyError(f"no pattern set named {domain!r} in {_DATA}")
    return tuple(sorted({entry["kind"] for entry in doc[domain]}))
