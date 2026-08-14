"""Three-layer rule resolution: base, then ToanAZ, then per-show.

Generic rules are written as absolutes because that is how training
material teaches. Real shows have conditions the textbook never states,
so a higher layer can switch a base rule off under stated conditions and
say why. Every finding records which layer decided it, because otherwise
a false positive is undiagnosable.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import yaml

from wing_parser import config
from wing_parser.advisory.evaluator import evaluate_all
from wing_parser.advisory.loader import _optional, load_base_rules, load_rules
from wing_parser.advisory.models import SEVERITIES, Finding, Rule

PRINCIPLES_FILE = "principles.yaml"
SHOWS_DIR = "shows"


def _monitor_bus_count(scene) -> int:
    return sum(1 for bus in scene.buses() if bus.is_monitor)


CONDITIONS: dict[str, Callable[[Any], Any]] = {
    "monitor_bus_count": _monitor_bus_count,
    "channel_count": lambda scene: len(scene.channels()),
}


def condition_holds(scene, applies_when: dict[str, Any]) -> bool:
    for name, expected in (applies_when or {}).items():
        probe = CONDITIONS.get(name)
        if probe is None:
            return False
        if probe(scene) != expected:
            return False
    return True


def _principles(directory: Path | None) -> list[Rule]:
    path = config.knowledge_dir(directory) / PRINCIPLES_FILE
    if not path.exists():
        return []
    return _as_rules(path, layer="toanaz", key="principles")


def _show_rules(directory: Path | None) -> list[Rule]:
    """A show file may be saved `.yaml` or `.yml`.

    Globbing only `*.yaml` makes a `.yml` file silently invisible --
    not loaded, not warned about, indistinguishable from "no overrides
    tonight." Both extensions are gathered into one sorted list so
    load order stays deterministic regardless of which spelling a show
    file used.
    """
    shows = config.knowledge_dir(directory) / SHOWS_DIR
    if not shows.is_dir():
        return []
    paths = sorted(list(shows.glob("*.yaml")) + list(shows.glob("*.yml")))
    rules: list[Rule] = []
    for path in paths:
        rules.extend(load_rules(path, layer="show"))
    return rules


def _as_rules(path: Path, layer: str, key: str) -> list[Rule]:
    """principles.yaml uses `principles:` and may omit the `when` block.

    A principle whose only job is to switch a base rule off needs no
    target of its own, so a missing `when` becomes a rule that matches
    nothing and exists purely for its `supersedes` list. An explicit
    `when` block with no `for_each` is a different, invalid case and is
    rejected the same way `loader.load_rules` rejects it, rather than
    left to raise a bare `KeyError` a few lines down.

    Every optional scalar routes through `loader._optional`, not
    `.get(key, default)`. `.get` only supplies its default when the key
    is absent entirely; a hand-edited principles file can leave a key
    present but blank, which YAML parses as null. A blank `hardness:`
    would resolve to `None` under `.get`, `_is_active` would not
    recognise it as `"flexible"`, and the principle would fall through
    to unconditionally active -- silently switching a base rule off on
    every show from a one-character slip. This is also why this layer
    validates `severity` against `SEVERITIES`: `load_rules` already
    rejects a bad severity for the base layer, and toanaz is the one
    hand-maintained layer, so leaving it unvalidated here would make
    the only human-edited layer the only unchecked one.
    """
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    rules: list[Rule] = []
    for entry in doc.get(key) or []:
        severity = _optional(entry, "severity", "info")
        if severity not in SEVERITIES:
            raise ValueError(
                f"{path}: rule {entry['id']} has severity {severity!r}; "
                f"expected one of {SEVERITIES}"
            )
        when = entry.get("when")
        if when is not None:
            if not when.get("for_each"):
                raise ValueError(f"{path}: rule {entry['id']} has no when.for_each")
        else:
            when = {"for_each": "channel", "where": {"channel.number": -1}}
        rules.append(
            Rule(
                id=entry["id"],
                title=entry.get("principle") or entry.get("title", entry["id"]),
                severity=severity,
                source=entry.get("source", "ToanAZ"),
                rationale=entry.get("rationale", ""),
                for_each=when["for_each"],
                where=dict(when.get("where") or {}),
                message=entry.get("message", entry.get("principle", entry["id"])),
                layer=layer,
                requires_classifier=bool(_optional(entry, "requires_classifier", False)),
                enabled=bool(_optional(entry, "enabled", True)),
                hardness=_optional(entry, "hardness", "hard"),
                applies_when=dict(entry.get("applies_when") or {}),
                supersedes=tuple(entry.get("supersedes") or ()),
            )
        )
    return rules


def _is_active(scene, rule: Rule) -> bool:
    if not rule.enabled:
        return False
    if rule.hardness == "flexible":
        return condition_holds(scene, rule.applies_when)
    return True


def active_rules(scene, directory: Path | None = None) -> list[Rule]:
    higher = [r for r in _principles(directory) + _show_rules(directory) if _is_active(scene, r)]
    base = load_base_rules()

    # A `supersedes` entry naming a rule id that does not exist -- a typo
    # such as `G88` for `G8` -- would otherwise leave the intended base
    # rule firing while its author believes it is off, and would make
    # `suppressed_ids()` (the diagnostic that exists so a false positive
    # is traceable) report a suppression that never happened. Fail loudly
    # instead, against the union of everything that could legitimately be
    # superseded: the base rules plus every other active higher-layer rule.
    known_ids = {r.id for r in base} | {r.id for r in higher}
    for rule in higher:
        for target_id in rule.supersedes:
            if target_id not in known_ids:
                raise ValueError(
                    f"{rule.id} supersedes unknown rule id {target_id!r}"
                )

    suppressed = {rule_id for r in higher for rule_id in r.supersedes}
    return [r for r in base if r.id not in suppressed] + higher


def suppressed_ids(scene, directory: Path | None = None) -> dict[str, str]:
    """Map each switched-off base rule to the higher-layer rule that did it."""
    higher = [r for r in _principles(directory) + _show_rules(directory) if _is_active(scene, r)]
    return {rule_id: r.id for r in higher for rule_id in r.supersedes}


def run(scene, directory: Path | None = None) -> list[Finding]:
    return evaluate_all(scene, active_rules(scene, directory))


class AdvisoryFacade:
    def __init__(self, scene, directory: Path | None = None) -> None:
        self._scene = scene
        self._directory = directory

    def run(self) -> list[Finding]:
        return run(self._scene, self._directory)

    def rules(self) -> list[Rule]:
        return active_rules(self._scene, self._directory)

    def suppressed(self) -> dict[str, str]:
        return suppressed_ids(self._scene, self._directory)
