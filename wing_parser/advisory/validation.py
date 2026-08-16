"""Checks applied to hand-edited rule YAML, kept apart from loading so
the failure modes they document stay findable.
"""

from __future__ import annotations

from pathlib import Path

from wing_parser.advisory.predicates import OPERATORS


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
