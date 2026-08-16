"""Run rules over a scene and produce findings.

A rule marked requires_classifier is skipped for any target whose
classification is below the usable threshold. Firing a source-dependent
rule against a channel nobody could identify is how an advisory tool
starts producing confident nonsense.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Iterator

from wing_parser.advisory.models import Finding, Rule
from wing_parser.advisory.predicates import all_match, render, resolve_path
from wing_parser.classifier.matcher import LOW


@dataclass(frozen=True)
class Target:
    name: str
    context: dict[str, Any]
    confidence: float


def _channels(scene) -> Iterator[Target]:
    for channel in scene.channels():
        yield Target(
            name=f"ch.{channel.number}",
            context={"channel": channel},
            confidence=channel.source_type.confidence,
        )


def _channel_sends(scene) -> Iterator[Target]:
    """One target per bus or matrix send.

    Both destination families bind under the context key `destination_bus`
    so one rule can range over both; the target name keeps the raw file's
    MX prefix so bus 8 and matrix 8 stay distinct. Mains are a different
    record shape (MainSend) and have their own iterator below.
    """
    buses = {bus.number: bus for bus in scene.buses()}
    matrices = {m.number: m for m in scene.matrices()}
    for channel in scene.channels():
        for send in channel.sends:
            if send.dest_kind == "bus":
                destination, name = buses.get(send.dest), f"ch.{channel.number}.send.{send.dest}"
            elif send.dest_kind == "matrix":
                destination, name = matrices.get(send.dest), f"ch.{channel.number}.send.MX{send.dest}"
            else:
                continue
            yield Target(
                name=name,
                context={"channel": channel, "send": send, "destination_bus": destination},
                confidence=destination.role.confidence if destination else 0.0,
            )


def _buses(scene) -> Iterator[Target]:
    for bus in scene.buses():
        yield Target(
            name=f"bus.{bus.number}",
            context={"bus": bus},
            confidence=bus.role.confidence,
        )


def _outputs(scene) -> Iterator[Target]:
    """Every summing destination: buses, auxes, mains and matrices."""
    for bus in scene.bus_family():
        yield Target(
            name=f"{bus.kind}.{bus.number}",
            context={"bus": bus},
            confidence=bus.role.confidence,
        )


def _channel_main_sends(scene) -> Iterator[Target]:
    mains = scene.family("main")
    for channel in scene.channels():
        for main_send in channel.main_sends:
            destination = mains.get(main_send.dest)
            yield Target(
                name=f"ch.{channel.number}.main.{main_send.dest}",
                context={
                    "channel": channel,
                    "main_send": main_send,
                    "destination_main": destination,
                },
                confidence=destination.role.confidence if destination else 0.0,
            )


def _nothing(scene) -> Iterator[Target]:
    """No targets at all, for a rule that exists only to supersede another."""
    return iter(())


ITERATORS: dict[str, Callable[[Any], Iterator[Target]]] = {
    "channel": _channels,
    "channel.sends": _channel_sends,
    "channel.main_sends": _channel_main_sends,
    "bus": _buses,
    "output": _outputs,
    "none": _nothing,
}


def targets_for(scene, for_each: str) -> Iterator[Target]:
    if for_each not in ITERATORS:
        raise KeyError(f"no target iterator named {for_each!r}")
    return ITERATORS[for_each](scene)


def _matched_clause(context: dict[str, Any], clauses: tuple[dict, ...]) -> int | None:
    """Index of the first `any_of` clause that matches, or None."""
    for index, clause in enumerate(clauses):
        if all_match(context, clause):
            return index
    return None


def evaluate(scene, rule: Rule) -> list[Finding]:
    if not rule.enabled:
        return []

    findings: list[Finding] = []
    for target in targets_for(scene, rule.for_each):
        if rule.requires_classifier and target.confidence < LOW:
            continue
        if not all_match(target.context, rule.where):
            continue

        matched = None
        if rule.any_of:
            matched = _matched_clause(target.context, rule.any_of)
            if matched is None:
                continue

        evidence = {path: resolve_path(target.context, path) for path in rule.where}
        if matched is not None:
            evidence.update(
                {path: resolve_path(target.context, path) for path in rule.any_of[matched]}
            )
            evidence["_any_of"] = matched

        findings.append(
            Finding(
                rule_id=rule.id,
                layer=rule.layer,
                severity=rule.severity,
                target=target.name,
                message=render(rule.message, target.context),
                evidence=evidence,
                confidence=target.confidence if rule.requires_classifier else 1.0,
            )
        )
    return findings


def evaluate_all(scene, rules: Iterable[Rule]) -> list[Finding]:
    findings: list[Finding] = []
    for rule in rules:
        findings.extend(evaluate(scene, rule))
    return findings
