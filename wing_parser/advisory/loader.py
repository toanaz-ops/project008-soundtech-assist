"""Read rule YAML into Rule records.

`source` and `rationale` are mandatory. Six places in the knowledge base
disagree with each other on thresholds; a rule that cannot say where its
number came from is a rule nobody can re-check later.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from wing_parser.advisory.models import SEVERITIES, Rule

BASE_RULES_DIR = Path(__file__).resolve().parent / "base_rules"


def _rule_from(entry: dict, layer: str, where_from: Path) -> Rule:
    for required in ("id", "title", "severity", "source", "rationale", "message"):
        if not entry.get(required):
            raise ValueError(f"{where_from}: rule is missing required field {required!r}")

    severity = entry["severity"]
    if severity not in SEVERITIES:
        raise ValueError(
            f"{where_from}: rule {entry['id']} has severity {severity!r}; "
            f"expected one of {SEVERITIES}"
        )

    when = entry.get("when") or {}
    if not when.get("for_each"):
        raise ValueError(f"{where_from}: rule {entry['id']} has no when.for_each")

    return Rule(
        id=entry["id"],
        title=entry["title"],
        severity=severity,
        source=entry["source"],
        rationale=entry["rationale"],
        for_each=when["for_each"],
        where=dict(when.get("where") or {}),
        message=entry["message"],
        layer=layer,
        requires_classifier=bool(entry.get("requires_classifier", False)),
        enabled=bool(entry.get("enabled", True)),
        hardness=entry.get("hardness", "hard"),
        applies_when=dict(entry.get("applies_when") or {}),
        supersedes=tuple(entry.get("supersedes") or ()),
    )


def load_rules(path: Path, layer: str) -> list[Rule]:
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    return [_rule_from(entry, layer, Path(path)) for entry in (doc.get("rules") or [])]


def load_base_rules() -> list[Rule]:
    rules: list[Rule] = []
    for path in sorted(BASE_RULES_DIR.glob("*.yaml")):
        rules.extend(load_rules(path, layer="base"))
    return rules
