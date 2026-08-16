"""Read rule YAML into Rule records.

`source` and `rationale` are mandatory. Six places in the knowledge base
disagree with each other on thresholds; a rule that cannot say where its
number came from is a rule nobody can re-check later.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from wing_parser.advisory.models import SEVERITIES, Rule
from wing_parser.advisory.validation import _optional, _validate_any_of, _validate_where

BASE_RULES_DIR = Path(__file__).resolve().parent / "base_rules"


def _load_yaml(path: Path) -> dict:
    """Parse a rule file, turning a YAML syntax error into the same
    ValueError shape every other load-time problem raises, instead of a
    bare `yaml.YAMLError` no caller here is set up to catch."""
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: invalid YAML: {exc}") from exc


def _rule_from(entry: dict, layer: str, where_from: Path) -> Rule:
    if not isinstance(entry, dict):
        raise ValueError(
            f"{where_from}: each rule entry must be a mapping, not "
            f"{type(entry).__name__} ({entry!r})"
        )

    if not entry.get("id"):
        raise ValueError(f"{where_from}: rule is missing required field 'id'")

    when = entry.get("when")
    supersede_only = when is None

    required = ["title", "severity", "source", "rationale"]
    if not supersede_only:
        required.append("message")
    for field in required:
        if not entry.get(field):
            raise ValueError(
                f"{where_from}: rule {entry['id']} is missing required field {field!r}"
            )

    severity = entry["severity"]
    if severity not in SEVERITIES:
        raise ValueError(
            f"{where_from}: rule {entry['id']} has severity {severity!r}; "
            f"expected one of {SEVERITIES}"
        )

    if supersede_only:
        when = {"for_each": "none", "where": {}}
    if not isinstance(when, dict):
        raise ValueError(
            f"{where_from}: rule {entry['id']} has a when: block that must "
            f"be a mapping, not {type(when).__name__} ({when!r})"
        )
    if not when.get("for_each"):
        raise ValueError(f"{where_from}: rule {entry['id']} has no when.for_each")

    where = dict(when.get("where") or {})
    _validate_where(where, where_from, entry["id"])
    any_of = (
        _validate_any_of(when["any_of"], where_from, entry["id"])
        if "any_of" in when
        else ()
    )

    return Rule(
        id=entry["id"],
        title=entry["title"],
        severity=severity,
        source=entry["source"],
        rationale=entry["rationale"],
        for_each=when["for_each"],
        where=where,
        message=entry.get("message") or entry["title"],
        layer=layer,
        requires_classifier=bool(_optional(entry, "requires_classifier", False)),
        enabled=bool(_optional(entry, "enabled", True)),
        hardness=_optional(entry, "hardness", "hard"),
        applies_when=dict(entry.get("applies_when") or {}),
        any_of=any_of,
        supersedes=tuple(entry.get("supersedes") or ()),
    )


def load_rules(path: Path, layer: str) -> list[Rule]:
    path = Path(path)
    doc = _load_yaml(path)
    return [_rule_from(entry, layer, path) for entry in (doc.get("rules") or [])]


def load_base_rules() -> list[Rule]:
    rules: list[Rule] = []
    for path in sorted(BASE_RULES_DIR.glob("*.yaml")):
        rules.extend(load_rules(path, layer="base"))
    return rules
