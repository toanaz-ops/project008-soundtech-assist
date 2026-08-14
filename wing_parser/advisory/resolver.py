"""Three-layer rule resolution: base, then ToanAZ, then per-show.

Generic rules are written as absolutes because that is how training
material teaches. Real shows have conditions the textbook never states,
so a higher layer can switch a base rule off under stated conditions and
say why. Every finding records which layer decided it, because otherwise
a false positive is undiagnosable.

Reading and validating the hand-edited YAML for the toanaz and show
layers lives in `layers.py`; this module is the resolution and
precedence logic -- which rules end up active, and why -- and does not
parse a rule file itself.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from wing_parser.advisory.evaluator import evaluate_all
from wing_parser.advisory.layers import _principles, _show_rules
from wing_parser.advisory.loader import load_base_rules
from wing_parser.advisory.models import Finding, Rule


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


def _is_active(scene, rule: Rule) -> bool:
    if not rule.enabled:
        return False
    if rule.hardness == "flexible":
        return condition_holds(scene, rule.applies_when)
    return True


def active_rules(scene, directory: Path | None = None) -> list[Rule]:
    higher = [r for r in _principles(directory) + _show_rules(directory) if _is_active(scene, r)]
    base = load_base_rules()
    base_ids = {r.id for r in base}
    higher_ids = {r.id for r in higher}

    # Design spec section 6.3 (line 270): "`supersedes` names the base
    # rules it switches off while active." shows/ is documented (§6.2) as
    # one-off exceptions, not a layer with authority over principles --
    # there is no cross-layer precedence mechanism, and this resolver does
    # not add one. `active_rules` only ever filters the *base* layer by
    # `suppressed`, so a `supersedes` entry naming a higher-layer rule id
    # would pass a base-or-higher validity check and then silently do
    # nothing. Reject it, and tell the two failure shapes apart: an id in
    # neither layer is a typo (e.g. `G88` for `G8`); an id that names a
    # real higher-layer rule is a misuse of a field the spec defines as
    # base-only.
    for rule in higher:
        for target_id in rule.supersedes:
            if target_id in base_ids:
                continue
            if target_id in higher_ids:
                raise ValueError(
                    f"{rule.id} supersedes {target_id!r}, which is a "
                    "higher-layer rule id, not a base rule id. Per design "
                    "spec section 6.3 (line 270), supersedes names only "
                    "the base rules a rule switches off; naming another "
                    "principle or show rule has no effect and is rejected."
                )
            raise ValueError(f"{rule.id} supersedes unknown rule id {target_id!r}")

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
