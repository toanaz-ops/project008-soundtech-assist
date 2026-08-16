import json

import pytest

from wing_parser import WingScene
from wing_parser.advisory.evaluator import evaluate, evaluate_all, targets_for
from wing_parser.advisory.loader import load_base_rules
from wing_parser.advisory.models import Rule


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    # Same guarantee test_cli.py's "offline" fixture gives the CLI suite:
    # no test in this module can reach a model even if `anthropic` is
    # installed, rather than relying on the subset of tests below that
    # happened to set this per-test.
    monkeypatch.setenv("WING_DISABLE_LLM", "1")


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


def test_classifier_dependent_rule_carries_the_confidence(scene):
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
    # The exact value, not a floor. All four monitor buses classify at 0.9,
    # so `>= 0.8` would still pass if evaluate()'s
    # `target.confidence if rule.requires_classifier else 1.0` were dropped
    # and every finding came out at a hardcoded 1.0.
    assert all(f.confidence == pytest.approx(0.9) for f in findings)


def test_classifier_dependent_rule_skips_unclassifiable_targets(scene):
    findings = evaluate(
        scene,
        rule(requires_classifier=True, where={}, message="{channel.name}"),
    )
    names = {f.message for f in findings}
    # Pin the positive case first: a gate that wrongly excluded every
    # target would satisfy the absence check below trivially.
    assert findings
    # "My Lap" cannot be classified, so no rule that depends on the
    # classifier may fire against it.
    assert "My Lap" not in names
    # HS4 classifies speech.headset at 0.7, inside the 0.4-0.8 band. It is
    # the only thing in this file that tells a LOW gate apart from a HIGH
    # one -- "My Lap" sits at 0.0 and is excluded either way, so without
    # this line the test would pass even if the gate skipped at HIGH.
    assert "HS4" in names


def _g8_rule() -> Rule:
    return next(r for r in load_base_rules() if r.id == "G8")


def test_dest_kind_guard_prevents_a_phantom_monitor_finding_on_a_matrix_send(
    vu_path, tmp_path
):
    """Channel 39 (BOH Talk) and channel 40 (FOH Tak) both carry a POST
    send to MX8 -- a matrix, not bus 8 -- in the sample file, and matrix
    number 8 collides exactly with bus 8 (MON VOX): monitor buses are 7,
    8, 9 and 10. `_channel_sends` in evaluator.py tells the two apart
    only by `send.dest_kind != "bus": continue`; the sample file's own
    `on: false` on both sends is the only other thing standing between
    this and a phantom "talkback mic feeding a monitor bus" finding. Flip
    channel 39's MX8 send on -- an entirely ordinary thing, a talkback
    send switched on mid-show -- and confirm G8 still does not fire. This
    is real data, not a synthetic fixture: it is the near-miss the review
    found when it removed the guard and still got 343 passed, 1 skipped.
    """
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"]["39"]["send"]["MX8"]["on"] = True
    live = tmp_path / "talkback_on.snap"
    live.write_text(json.dumps(doc), encoding="utf-8")

    findings = evaluate(WingScene.load(live), _g8_rule())
    assert all(not f.target.startswith("ch.39.") for f in findings)
    assert all(f.target != "ch.39.send.8" for f in findings)


def test_any_of_fires_when_either_clause_matches(scene):
    findings = evaluate(
        scene,
        rule(where={"channel.number": 8},
             any_of=({"channel.name": "nothing"}, {"channel.muted": False})),
    )
    assert [f.target for f in findings] == ["ch.8"]


def test_any_of_does_not_fire_when_no_clause_matches(scene):
    assert evaluate(
        scene,
        rule(where={"channel.number": 8},
             any_of=({"channel.name": "nothing"}, {"channel.muted": True})),
    ) == []


def test_where_still_gates_a_rule_that_has_any_of(scene):
    """`where` is AND with the whole any_of block, not an alternative to it."""
    assert evaluate(
        scene,
        rule(where={"channel.number": 999}, any_of=({"channel.muted": False},)),
    ) == []


def test_evidence_records_which_clause_matched(scene):
    finding = evaluate(
        scene,
        rule(where={"channel.number": 8},
             any_of=({"channel.name": "nothing"}, {"channel.muted": False})),
    )[0]
    assert finding.evidence["_any_of"] == 1
    assert finding.evidence["channel.muted"] is False
    assert finding.evidence["channel.number"] == 8


def test_evidence_records_the_first_clause_when_more_than_one_matches(scene):
    """`_matched_clause` must return the first match, not merely a match --
    the finding order this advisory tool produces has to be stable, and a
    test built from one non-matching clause and one matching clause (as
    above) cannot distinguish "first" from "last" from "any". Both clauses
    below match channel 8, so only checking for index 0 pins the guarantee."""
    finding = evaluate(
        scene,
        rule(where={"channel.number": 8},
             any_of=({"channel.muted": False}, {"channel.name": "M8 MC"})),
    )[0]
    assert finding.evidence["_any_of"] == 0


def test_a_rule_without_any_of_carries_no_marker(scene):
    finding = evaluate(scene, rule(where={"channel.number": 8}))[0]
    assert "_any_of" not in finding.evidence


def test_evaluate_all_concatenates(scene):
    findings = evaluate_all(
        scene,
        [rule(id="A", where={"channel.number": 8}), rule(id="B", where={"channel.number": 9})],
    )
    assert {f.rule_id for f in findings} == {"A", "B"}


def test_the_none_iterator_yields_no_targets(scene):
    assert list(targets_for(scene, "none")) == []
    assert evaluate(scene, rule(for_each="none", where={})) == []
