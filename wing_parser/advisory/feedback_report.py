"""Per-rule roll-up of the verdict log (wave 7).

Pure: no Qt, no file access. `build_report` only reads what `feedback.read_log`
returned and counts it. `candidate` marks a rule worth asking the human about
(write a principle or `supersedes`); nothing here changes a rule.
"""

from __future__ import annotations

from dataclasses import dataclass

from wing_parser.advisory.feedback import Verdict

CANDIDATE_MIN_REJECTIONS = 3


@dataclass(frozen=True)
class RuleVerdicts:
    rule_id: str
    layer: str
    correct: int
    false_positive: int
    irrelevant: int
    last: str
    notes: tuple[str, ...]
    candidate: bool


def build_report(entries: list[Verdict]) -> list[RuleVerdicts]:
    by_rule: dict[str, list[Verdict]] = {}
    for entry in entries:
        by_rule.setdefault(entry.rule_id, []).append(entry)

    rows: list[RuleVerdicts] = []
    for rule_id, group in by_rule.items():
        count = {v: sum(1 for e in group if e.verdict == v)
                 for v in ("correct", "false-positive", "irrelevant")}
        rejected = count["false-positive"] + count["irrelevant"]
        newest_first = sorted(group, key=lambda e: e.recorded_at, reverse=True)
        rows.append(RuleVerdicts(
            rule_id=rule_id,
            layer=newest_first[0].layer,
            correct=count["correct"],
            false_positive=count["false-positive"],
            irrelevant=count["irrelevant"],
            last=newest_first[0].recorded_at,
            notes=tuple(e.note for e in newest_first if e.note.strip()),
            candidate=rejected >= CANDIDATE_MIN_REJECTIONS
            and rejected > count["correct"],
        ))
    rows.sort(key=lambda r: (-(r.false_positive + r.irrelevant), r.rule_id))
    return rows
