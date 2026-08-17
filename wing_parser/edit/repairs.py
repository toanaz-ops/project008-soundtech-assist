"""How to repair a finding -- declared in YAML, never inferred.

The dangerous version of this feature is a button that guesses. A rule
with no descriptor shows no button, which is a complete and honest
answer: most rules state a window or a count, so no single value
follows from them. Same line the advisory layer already takes with Q7,
which ships disabled rather than carrying a threshold nobody can cite.

A finding's `target` is very nearly the raw JSON path -- `ch.1.send.8`
against `ae_data.ch.1.send.8` -- because both mirror how the WING
organises a scene. "Very nearly" is not "exactly", which is why the
path is declared per rule rather than derived at run time, and why
every descriptor carries a test proving it clears its own finding.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from wing_parser.advisory.feedback import finding_id
from wing_parser.advisory.models import Finding
from wing_parser.edit import pointer
from wing_parser.edit.journal import Patch

KINDS: tuple[str, ...] = ("set", "toggle")
_DATA = Path(__file__).resolve().parent / "data" / "repairs.yaml"


@dataclass(frozen=True)
class Repair:
    rule: str
    kind: str
    path: str
    label: str
    rationale: str
    to: Any = None


def parse_repairs(doc: dict) -> dict[str, Repair]:
    out: dict[str, Repair] = {}
    for entry in doc.get("repairs") or []:
        rule = str(entry.get("rule") or "").strip()
        if not rule:
            raise ValueError("a repair descriptor is missing its 'rule'")
        if not str(entry.get("rationale") or "").strip():
            raise ValueError(f"repair {rule} has no rationale")
        kind = str(entry.get("kind") or "")
        if kind not in KINDS:
            raise ValueError(
                f"repair {rule} has unknown kind {kind!r}; expected one of {KINDS}"
            )
        if not str(entry.get("path") or "").strip():
            raise ValueError(f"repair {rule} has no path")
        if kind == "set" and "to" not in entry:
            raise ValueError(f"repair {rule} is a 'set' with no 'to' value")
        out[rule] = Repair(
            rule=rule,
            kind=kind,
            path=str(entry["path"]),
            label=str(entry.get("label") or rule),
            rationale=str(entry["rationale"]),
            to=entry.get("to"),
        )
    return out


@lru_cache(maxsize=1)
def load_repairs() -> dict[str, Repair]:
    return parse_repairs(yaml.safe_load(_DATA.read_text(encoding="utf-8")) or {})


def parts_of(target: str) -> dict[str, str]:
    """`"ch.1.send.8"` -> `{"ch": "1", "send": "8"}`.

    A finding's target alternates name and number, which is what makes
    a declared path template fillable at all. A placeholder the target
    does not supply raises KeyError from `str.format`, which is
    correct: it means the descriptor does not fit the finding it was
    matched to, and a silent empty substitution would build a path
    pointing at nothing.
    """
    segments = target.split(".")
    return dict(zip(segments[::2], segments[1::2]))


def patch_for(finding: Finding, document: dict) -> Patch | None:
    """The patch that clears this finding, or None if none is declared."""
    repair = load_repairs().get(finding.rule_id)
    if repair is None:
        return None

    path = repair.path.format(**parts_of(finding.target))
    before = pointer.read(document, path)
    after = (not before) if repair.kind == "toggle" else repair.to
    return Patch(
        path=path,
        before=before,
        after=after,
        because=finding_id(finding),
        label=f"{repair.label} ({finding.target})",
    )
