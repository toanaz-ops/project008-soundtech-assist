"""Dry-run a draft rule file against scenes without enabling it.

Drafts live in `<knowledge_dir>/drafts/`. The resolver never reads that
directory, so a draft cannot change a real show's findings; it is only
ever evaluated here, as extra toanaz-layer rules. Nothing in this module
writes a file.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from wing_parser import config
from wing_parser.advisory import layers
from wing_parser.advisory.evaluator import evaluate_all
from wing_parser.advisory.loader import load_base_rules
from wing_parser.advisory.models import Finding, Rule
from wing_parser.advisory.resolver import active_rules, suppressed_ids
from wing_parser.advisory.validation import _validate_owner_source

DRAFTS_DIR = "drafts"


@dataclass(frozen=True)
class DraftLoad:
    path: Path
    rules: tuple[Rule, ...] = ()
    error: str | None = None
    promotable: bool = False
    promote_blockers: tuple[str, ...] = ()


@dataclass(frozen=True)
class SceneDelta:
    before: int
    after: int
    added: tuple[Finding, ...] = ()
    removed: tuple[Finding, ...] = ()
    suppressed: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SceneResult:
    path: Path
    delta: SceneDelta | None = None
    error: str | None = None


def list_drafts(directory: Path | None = None) -> list[Path]:
    folder = config.knowledge_dir(directory) / DRAFTS_DIR
    if not folder.is_dir():
        return []
    files = [p for p in folder.iterdir()
             if p.is_file() and p.suffix.lower() in (".yaml", ".yml")]
    return sorted(files, key=lambda p: p.name)


def _check_ids(path: Path, rules: list[Rule], directory: Path | None) -> None:
    base_ids = {r.id for r in load_base_rules()}
    principle_ids = {r.id for r in layers._principles(directory)}
    seen: set[str] = set()
    for rule in rules:
        if rule.id in base_ids:
            raise ValueError(f"{path}: draft rule id {rule.id!r} collides "
                             "with a base rule id")
        if rule.id in principle_ids:
            raise ValueError(f"{path}: draft rule id {rule.id!r} collides "
                             "with a rule already in principles.yaml")
        if rule.id in seen:
            raise ValueError(f"{path}: draft rule id {rule.id!r} appears "
                             "more than once")
        seen.add(rule.id)
    for rule in rules:
        for target in rule.supersedes:
            if target in principle_ids or target in seen:
                raise ValueError(
                    f"{path}: {rule.id} supersedes {target!r}, which is not "
                    "a base rule id; supersedes names only base rules")
            if target not in base_ids:
                raise ValueError(f"{path}: {rule.id} supersedes unknown "
                                 f"rule id {target!r}")


def load_draft(path: Path, directory: Path | None = None) -> DraftLoad:
    path = Path(path)
    try:
        rules = layers._as_rules(path, layer="toanaz", key="principles",
                                 owner_source=False)
        if not rules:
            raise ValueError(f"{path}: the draft contains no rules under "
                             "'principles:'")
        _check_ids(path, rules, directory)
    except (ValueError, OSError) as exc:
        return DraftLoad(path=path, error=str(exc))
    blockers: list[str] = []
    for rule in rules:
        try:
            _validate_owner_source([rule], path)
        except ValueError as exc:
            blockers.append(str(exc))
    return DraftLoad(path=path, rules=tuple(rules),
                     promotable=not blockers,
                     promote_blockers=tuple(blockers))


def _diff(before: list[Finding], after: list[Finding]):
    def key(f: Finding):
        return (f.rule_id, f.target, f.message)

    def surplus(items, other):
        spare = Counter(key(f) for f in items) - Counter(key(f) for f in other)
        out = []
        for f in items:
            if spare[key(f)] > 0:
                spare[key(f)] -= 1
                out.append(f)
        return tuple(out)

    return surplus(after, before), surplus(before, after)


def dry_run(scene, draft_rules, directory: Path | None = None) -> SceneDelta:
    draft_rules = tuple(draft_rules)
    before = evaluate_all(scene, active_rules(scene, directory))
    after = evaluate_all(
        scene, active_rules(scene, directory, extra_rules=draft_rules))
    added, removed = _diff(before, after)
    ids = {r.id for r in draft_rules}
    suppressed = {k: v for k, v in
                  suppressed_ids(scene, directory,
                                 extra_rules=draft_rules).items() if v in ids}
    return SceneDelta(len(before), len(after), added, removed, suppressed)


def dry_run_files(paths, draft_rules,
                  directory: Path | None = None) -> list[SceneResult]:
    from wing_parser import WingScene

    results: list[SceneResult] = []
    for raw in paths:
        path = Path(raw)
        try:
            scene = WingScene.load(path)
            results.append(SceneResult(
                path, delta=dry_run(scene, draft_rules, directory)))
        except Exception as exc:  # one bad file must not stop the rest
            results.append(
                SceneResult(path, error=f"{type(exc).__name__}: {exc}"))
    return results
