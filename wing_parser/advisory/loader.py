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


def _validate_any_of(raw, path: Path, rule_id: str) -> tuple[dict, ...]:
    """Read and check an `any_of` block. One level, never empty.

    `when.get("any_of")` returns None both when the key is absent and
    when it is present with the value left off, so the caller tests
    membership and only reaches here in the second case. That distinction
    is the whole point: an absent `any_of` means "this rule has no OR",
    while a blank one that slipped through would leave `Rule.any_of` at
    `()` -- the same present-but-null hazard `_optional` exists for. There
    is no unconditional `any(...)` in this path: `evaluate()` only
    consults `any_of` when it is truthy (`if rule.any_of:`), so an empty
    tuple would not be read as "nothing matched" and skipped -- it would
    be read as "no OR was written" and the rule would fire on every
    target that satisfies `where`, wider than its author intended, not
    silent.

    Of the two guards below, `if raw is None:` is not the one carrying the
    safety burden -- `isinstance(raw, list)` rejects `None` on its own,
    since `None` is not a `list`. The `None` branch exists only to give a
    better message ("remove the key or give it at least one clause")
    than the generic "must be a list, not NoneType" the `isinstance`
    check would otherwise produce. `if not raw:` is the guard that
    actually matters: `any_of: []` is a syntactically valid empty list,
    passes `isinstance(raw, list)` cleanly, and has nothing else standing
    between it and the over-firing described above.
    """
    if raw is None:
        raise ValueError(
            f"{path}: rule {rule_id} has an empty any_of; remove the key "
            "or give it at least one clause"
        )
    if not isinstance(raw, list):
        raise ValueError(
            f"{path}: rule {rule_id} has an any_of that must be a list, not "
            f"{type(raw).__name__} ({raw!r})"
        )
    if not raw:
        raise ValueError(
            f"{path}: rule {rule_id} has an empty any_of; remove the key "
            "or give it at least one clause"
        )

    clauses: list[dict] = []
    for clause in raw:
        if not isinstance(clause, dict):
            raise ValueError(
                f"{path}: rule {rule_id} has an any_of clause that must be a "
                f"mapping, not {type(clause).__name__} ({clause!r})"
            )
        if "any_of" in clause:
            raise ValueError(
                f"{path}: rule {rule_id} nests any_of inside an any_of clause; "
                "one level of OR only"
            )
        _validate_where(clause, path, rule_id)
        clauses.append(dict(clause))
    return tuple(clauses)


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
        message=entry["message"],
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
