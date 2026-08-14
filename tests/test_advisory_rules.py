import json

import pytest

from wing_parser import WingScene
from wing_parser.advisory.loader import load_base_rules


@pytest.fixture(scope="module")
def scene(vu_path):
    return WingScene.load(vu_path)


def test_three_base_rules_ship(scene):
    assert {r.id for r in load_base_rules()} == {"G8", "G7", "E6"}


def test_every_base_rule_cites_a_source_and_a_rationale():
    for rule in load_base_rules():
        assert "docs/knowledge-base/" in rule.source, rule.id
        assert len(rule.rationale) > 40, rule.id


def test_g8_fires_on_channel_eight_into_bus_eight(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    findings = [f for f in scene.advisory.run() if f.rule_id == "G8"]
    match = next(f for f in findings if f.target == "ch.8.send.8")

    assert match.severity == "warning"
    assert match.layer == "base"
    assert "MON VOX" in match.message
    assert match.confidence >= 0.8


def test_g7_fires_on_bus_eight(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    match = next(f for f in scene.advisory.run() if f.rule_id == "G7" and f.target == "bus.8")

    assert match.severity == "error"
    assert "COMP" in match.message


def test_e6_fires_on_the_headset_channel_and_nothing_else(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    findings = [f for f in scene.advisory.run() if f.rule_id == "E6"]
    # Channel 11 (HS4) is the only channel in this file carrying both an
    # active gate over 6 dB and an active automix insert: gate range 40 dB,
    # hold 10 ms, automix group X. This is a real finding on a real show
    # file, not a fixture -- do not "fix" it by weakening the rule.
    assert [f.target for f in findings] == ["ch.11"]
    assert "HS4" in findings[0].message


def test_e6_ignores_an_automix_group_configured_but_switched_off(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    # Channels 1, 2, 3, 5, 6, 7 and 8 all carry automix group X with the
    # post insert switched OFF, and a gate over 6 dB. They are exactly the
    # false positives E6's `channel.post_insert.on` check exists to
    # prevent, so none of them may appear. Drop that check and this test
    # goes red with seven extra targets.
    flagged = {f.target for f in scene.advisory.run() if f.rule_id == "E6"}
    assert flagged.isdisjoint({f"ch.{n}" for n in (1, 2, 3, 5, 6, 7, 8)})


def test_e6_fires_once_the_automix_insert_is_switched_on(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"]["8"]["postins"]["on"] = True
    live = tmp_path / "automix_on.snap"
    live.write_text(json.dumps(doc), encoding="utf-8")

    findings = [f for f in WingScene.load(live).advisory.run() if f.rule_id == "E6"]
    # ch.11 already fires on the unmodified file; switching channel 8's
    # insert on adds it, and targets come out in channel order.
    assert [f.target for f in findings] == ["ch.8", "ch.11"]
    assert "X" in findings[0].message


def test_every_finding_records_its_layer(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    assert all(f.layer in {"base", "toanaz", "show"} for f in scene.advisory.run())
