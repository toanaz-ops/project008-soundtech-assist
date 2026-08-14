import pytest

from wing_parser import WingScene
from wing_parser.advisory.evaluator import evaluate, evaluate_all, targets_for
from wing_parser.advisory.models import Rule


@pytest.fixture(scope="module")
def scene(vu_path):
    return WingScene.load(vu_path)


def rule(**overrides) -> Rule:
    base = dict(
        id="T", title="t", severity="warning", source="test", rationale="test",
        for_each="channel", where={}, message="{channel.number}", layer="base",
    )
    base.update(overrides)
    return Rule(**base)


def test_channel_iterator_yields_every_channel(scene):
    targets = list(targets_for(scene, "channel"))
    assert len(targets) == 40
    assert targets[7].name == "ch.8"
    assert targets[7].context["channel"].name == "M8 MC"


def test_send_iterator_binds_the_destination_bus(scene):
    targets = list(targets_for(scene, "channel.sends"))
    match = next(t for t in targets if t.name == "ch.8.send.8")
    assert match.context["send"].mode == "POST"
    assert match.context["destination_bus"].name == "MON VOX"


def test_bus_iterator_yields_sixteen_buses(scene):
    assert len(list(targets_for(scene, "bus"))) == 16


def test_unknown_iterator_raises(scene):
    with pytest.raises(KeyError, match="cabbage"):
        list(targets_for(scene, "cabbage"))


def test_empty_where_matches_every_target(scene):
    assert len(evaluate(scene, rule())) == 40


def test_scalar_predicate_filters(scene):
    findings = evaluate(scene, rule(where={"channel.number": 8}))
    assert len(findings) == 1
    assert findings[0].target == "ch.8"
    assert findings[0].message == "8"


def test_finding_carries_rule_metadata(scene):
    finding = evaluate(scene, rule(where={"channel.number": 8}))[0]
    assert finding.rule_id == "T"
    assert finding.layer == "base"
    assert finding.severity == "warning"


def test_evidence_records_the_matched_values(scene):
    finding = evaluate(
        scene, rule(where={"channel.number": 8, "channel.muted": False})
    )[0]
    assert finding.evidence["channel.number"] == 8
    assert finding.evidence["channel.muted"] is False


def test_disabled_rule_produces_nothing(scene):
    assert evaluate(scene, rule(enabled=False)) == []


def test_classifier_dependent_rule_carries_the_confidence(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    findings = evaluate(
        scene,
        rule(
            for_each="bus",
            requires_classifier=True,
            where={"bus.role": "monitor"},
            message="{bus.name}",
        ),
    )
    names = {f.message for f in findings}
    assert {"MON VOX", "MON L", "MON R"} <= names
    assert all(f.confidence >= 0.8 for f in findings)


def test_classifier_dependent_rule_skips_unclassifiable_targets(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    findings = evaluate(
        scene,
        rule(requires_classifier=True, where={}, message="{channel.name}"),
    )
    # "My Lap" cannot be classified, so no rule that depends on the
    # classifier may fire against it.
    assert "My Lap" not in {f.message for f in findings}


def test_evaluate_all_concatenates(scene):
    findings = evaluate_all(
        scene,
        [rule(id="A", where={"channel.number": 8}), rule(id="B", where={"channel.number": 9})],
    )
    assert {f.rule_id for f in findings} == {"A", "B"}
