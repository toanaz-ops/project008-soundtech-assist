"""The small predicate language rule YAML is written in.

Deliberately small. A rule file should read like a statement about the
console, not like code, and anything that needs real logic belongs in a
Python rule rather than a bigger DSL.
"""

from __future__ import annotations

from string import Formatter
from typing import Any

from wing_parser.classifier.matcher import Classification

_MISSING = object()

# Every operator key `matches()` understands inside a `where` value's
# dict form, e.g. `{"gt": 6.0}`. The loader validates a rule's `where`
# against this set at load time, so an unknown operator is a clean error
# naming the file rather than a `ValueError` raised from mid-run.
OPERATORS: frozenset[str] = frozenset({"not", "in", "not_in", "gt", "lt", "is_null"})


def resolve_path(context: dict[str, Any], path: str) -> Any:
    """Walk a dotted path. A Classification unwraps to its kind."""
    current: Any = context
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part, _MISSING)
        else:
            current = getattr(current, part, _MISSING)
        if current is _MISSING:
            return None
    if isinstance(current, Classification):
        return current.kind
    return current


def matches(value: Any, expected: Any) -> bool:
    if not isinstance(expected, dict):
        return value == expected

    for operator, operand in expected.items():
        if operator == "not":
            if value == operand:
                return False
        elif operator == "in":
            if value not in operand:
                return False
        elif operator == "not_in":
            if value in operand:
                return False
        elif operator == "gt":
            if not isinstance(value, (int, float)) or not value > operand:
                return False
        elif operator == "lt":
            if not isinstance(value, (int, float)) or not value < operand:
                return False
        elif operator == "is_null":
            if (value is None) is not bool(operand):
                return False
        else:
            raise ValueError(
                f"unknown predicate operator {operator!r}; expected one of "
                f"{sorted(OPERATORS)}"
            )
    return True


def all_match(context: dict[str, Any], where: dict[str, Any]) -> bool:
    return all(matches(resolve_path(context, path), expected) for path, expected in where.items())


def render(template: str, context: dict[str, Any]) -> str:
    """Fill {dotted.path} tokens. An unresolvable token is left visible."""
    out: list[str] = []
    for literal, field_name, _spec, _conv in Formatter().parse(template):
        out.append(literal)
        if field_name is None:
            continue
        value = resolve_path(context, field_name)
        out.append(f"{{{field_name}}}" if value is None else str(value))
    return "".join(out).strip()
