import json

import pytest

from wing_parser import WingScene
from wing_parser import config
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


def test_g7_fires_only_where_the_dynamics_are_bypassed(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    findings = [f for f in scene.advisory.run() if f.rule_id == "G7"]
    # Bus 7 SIDEFILL has dyn.on False; buses 8, 9 and 10 have it True.
    # The model half of G7 is held back until a real limiter token is
    # known, so a bus carrying COMP switched on is no longer reported.
    assert [f.target for f in findings] == ["bus.7"]
    assert findings[0].severity == "error"


def test_g7_states_facts_rather_than_asserting_a_conclusion(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    message = next(f for f in scene.advisory.run() if f.rule_id == "G7").message
    assert "COMP" in message
    assert "not a limiter" not in message


def test_the_sample_scene_reports_fourteen_findings(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    found = scene.advisory.run()
    counts = {rule_id: sum(1 for f in found if f.rule_id == rule_id)
              for rule_id in ("G8", "G7", "E6")}
    assert counts == {"G8": 12, "G7": 1, "E6": 1}
    assert len(found) == 14


def test_e6_still_fires_only_on_the_headset_channel(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    findings = [f for f in scene.advisory.run() if f.rule_id == "E6"]
    assert [f.target for f in findings] == ["ch.11"]


def test_e6_fires_on_a_short_hold_even_when_the_range_is_acceptable(
    vu_path, tmp_path, monkeypatch
):
    """The real file cannot discriminate E6's two clauses -- channel 11 is
    the only channel meeting the preconditions and it fails both -- so the
    hold clause needs a synthesised case."""
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    gate = doc["ae_data"]["ch"]["11"]["gate"]
    gate["range"] = 4      # the raw key is "range"; the view exposes range_dB
    gate["hld"] = 30       # the raw key is "hld"; the view exposes hold_ms
    live = tmp_path / "short_hold.snap"
    live.write_text(json.dumps(doc), encoding="utf-8")

    findings = [f for f in WingScene.load(live).advisory.run() if f.rule_id == "E6"]
    assert [f.target for f in findings] == ["ch.11"]
    assert findings[0].evidence["_any_of"] == 1


def test_e6_message_names_both_range_and_hold(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    message = next(f for f in scene.advisory.run() if f.rule_id == "E6").message
    assert "40.0" in message
    assert "10.0" in message


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
    findings = scene.advisory.run()
    # all(...) over an empty list is vacuously True, so an empty findings
    # list would pass this assertion without actually exercising anything.
    assert findings
    assert all(f.layer in {"base", "toanaz", "show"} for f in findings)


def test_the_shipped_small_profile_loads_and_suppresses_g8(scene, monkeypatch):
    monkeypatch.delenv(config.ENV_VAR, raising=False)
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    found = scene.advisory.run(profile="small")
    assert [f.rule_id for f in found if f.rule_id == "G8"] == []
    assert {f.rule_id for f in found} == {"G7", "E6"}
    assert len(found) == 2


def test_the_small_profile_records_who_switched_g8_off(scene, monkeypatch):
    monkeypatch.delenv(config.ENV_VAR, raising=False)
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    assert scene.advisory.suppressed(profile="small") == {
        "G8": "show.small.post-monitors-are-deliberate"
    }


def test_the_shipped_principles_file_still_loads(scene, monkeypatch):
    """principles.yaml holds no principles now. It must still parse, and
    it must not quietly stop being read."""
    monkeypatch.delenv(config.ENV_VAR, raising=False)
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    assert scene.advisory.rules()
    assert [r for r in scene.advisory.rules() if r.layer == "toanaz"] == []
