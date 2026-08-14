"""Read rule YAML into Rule records.

`source` and `rationale` are mandatory. Six places in the knowledge base
disagree with each other on thresholds; a rule that cannot say where its
number came from is a rule nobody can re-check later.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from wing_parser.advisory.models import SEVERITIES, Rule
from wing_parser.advisory.predicates import OPERATORS

BASE_RULES_DIR = Path(__file__).resolve().parent / "base_rules"


def _load_yaml(path: Path) -> dict:
    """Parse a rule file, turning a YAML syntax error into the same
    ValueError shape every other load-time problem raises, instead of a
    bare `yaml.YAMLError` no caller here is set up to catch."""
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: invalid YAML: {exc}") from exc


def _validate_where(where: dict, path: Path, rule_id: str) -> None:
    """Reject an unknown predicate operator at load time.

    `predicates.matches` raises `ValueError` for this too, but only when
    a target happens to reach that `where` clause mid-run -- a rule that
    is rarely evaluated could ship a typo'd operator for a long time
    before it ever surfaces. Checking every operator key up front means a
    hand-edited rule file fails at load, the same moment every other slip
    in it would.
    """
    for field_path, expected in where.items():
        if not isinstance(expected, dict):
            continue
        for operator in expected:
            if operator not in OPERATORS:
                raise ValueError(
                    f"{path}: rule {rule_id} has an unknown predicate "
                    f"operator {operator!r} on {field_path!r}; expected "
                    f"one of {sorted(OPERATORS)}"
                )


def _optional(entry: dict, key: str, default):
    """Read an optional field, treating an explicit YAML null as unset.

    `.get(key, default)` only defaults when the key is absent. A rule file
    is hand-edited, and `enabled:` with the value left off is a plausible
    slip — under `.get` it would come back None, silently disabling a rule
    its author meant to leave on. The sibling fields (`where`,
    `applies_when`, `supersedes`) already collapse null to their default
    via `or`; this keeps the scalar ones consistent with them.
    """
    value = entry.get(key)
    return default if value is None else value


def _rule_from(entry: dict, layer: str, where_from: Path) -> Rule:
    if not isinstance(entry, dict):
        raise ValueError(
            f"{where_from}: each rule entry must be a mapping, not "
            f"{type(entry).__name__} ({entry!r})"
        )

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
    if not isinstance(when, dict):
        raise ValueError(
            f"{where_from}: rule {entry['id']} has a when: block that must "
            f"be a mapping, not {type(when).__name__} ({when!r})"
        )
    if not when.get("for_each"):
        raise ValueError(f"{where_from}: rule {entry['id']} has no when.for_each")

    where = dict(when.get("where") or {})
    _validate_where(where, where_from, entry["id"])

    return Rule(
        id=entry["id"],
        title=entry["title"],
        severity=severity,
        source=entry["source"],
        rationale=entry["rationale"],
        for_each=when["for_each"],
        where=where,
        message=entry["message"],
        layer=layer,
        requires_classifier=bool(_optional(entry, "requires_classifier", False)),
        enabled=bool(_optional(entry, "enabled", True)),
        hardness=_optional(entry, "hardness", "hard"),
        applies_when=dict(entry.get("applies_when") or {}),
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
