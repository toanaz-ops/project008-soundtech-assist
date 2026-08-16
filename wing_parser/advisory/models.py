"""Rule and Finding records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SEVERITIES: tuple[str, ...] = ("info", "warning", "error")
LAYERS: tuple[str, ...] = ("base", "toanaz", "show")


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    severity: str
    source: str
    rationale: str
    for_each: str
    where: dict[str, Any]
    message: str
    layer: str
    requires_classifier: bool = False
    enabled: bool = True
    hardness: str = "hard"
    applies_when: dict[str, Any] = field(default_factory=dict)
    any_of: tuple[dict[str, Any], ...] = ()
    supersedes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Finding:
    rule_id: str
    layer: str
    severity: str
    target: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
