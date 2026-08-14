"""Append-only verdict log.

There is no machine learning here. The log exists so that, read across
many shows, a pattern becomes visible: seven rejections of G8, all in
scenes with exactly one monitor bus, is the signal that a conditional
principle should be written. A human writes it; Claude only reads the
log and proposes.
"""

from __future__ import annotations

import json
import warnings
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from wing_parser import config
from wing_parser.advisory.models import Finding

FILENAME = "feedback.jsonl"
VERDICTS: tuple[str, ...] = ("correct", "false-positive", "irrelevant")


@dataclass(frozen=True)
class Verdict:
    finding_id: str
    rule_id: str
    layer: str
    verdict: str
    note: str
    scene: str
    target: str
    recorded_at: str


def finding_id(finding: Finding) -> str:
    """Stable across runs for the same rule hitting the same target."""
    return f"{finding.rule_id}:{finding.target}"


def _path(directory: Path | None) -> Path:
    return config.knowledge_dir(directory) / FILENAME


def record(
    finding: Finding,
    verdict: str,
    note: str = "",
    scene: str = "",
    directory: Path | None = None,
    now: datetime | None = None,
) -> Verdict:
    if verdict not in VERDICTS:
        raise ValueError(f"unknown verdict {verdict!r}; expected one of {VERDICTS}")

    entry = Verdict(
        finding_id=finding_id(finding),
        rule_id=finding.rule_id,
        layer=finding.layer,
        verdict=verdict,
        note=note,
        scene=scene,
        target=finding.target,
        recorded_at=(now or datetime.now(timezone.utc)).isoformat(),
    )

    path = _path(directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
    return entry


def read_log(directory: Path | None = None) -> list[Verdict]:
    path = _path(directory)
    if not path.exists():
        return []

    entries: list[Verdict] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(Verdict(**json.loads(line)))
        except (json.JSONDecodeError, TypeError) as unreadable:
            # A hand-edited log should not break the reader, but it must
            # not lose history in silence either. TypeError fires on any
            # well-formed JSON object whose keys no longer match Verdict,
            # so a single schema change would otherwise discard every
            # pre-existing line without a word.
            warnings.warn(
                f"{path}:{number}: skipping unreadable feedback entry ({unreadable})",
                stacklevel=2,
            )
    return entries


def summarise(directory: Path | None = None) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for entry in read_log(directory):
        counts.setdefault(entry.rule_id, {}).setdefault(entry.verdict, 0)
        counts[entry.rule_id][entry.verdict] += 1
    return counts
