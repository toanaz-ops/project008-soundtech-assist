import pytest
import yaml

from wing_parser import WingScene
from wing_parser.advisory.loader import load_base_rules


def _show(tmp_path, segments):
    path = tmp_path / "tonight.yaml"
    path.write_text(yaml.safe_dump({"show": "t", "segments": segments}), encoding="utf-8")
    return path


@pytest.fixture
def fire(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")

    def run(segments, rule_id):
        scene = WingScene.load(vu_path, show=_show(tmp_path, segments))
        return [f for f in scene.advisory.run() if f.rule_id == rule_id]

    return run


def test_the_cue_rules_load_with_source_and_rationale():
    """Q1-Q3 only. The all-seven assertion lands in Task 7, once every
    rule exists -- a test that fails for two tasks is a broken gate, not
    a pending one."""
    rules = {r.id: r for r in load_base_rules() if r.id.startswith("Q")}
    assert {"Q1", "Q2", "Q3"} <= set(rules)
    for rule in rules.values():
        assert rule.source.strip() and rule.rationale.strip()


def test_q1_fires_on_a_cue_naming_an_absent_channel(fire):
    # example-Vu.snap is a WING console: channels 1-40 are always present
    # in channel_map() (a fixed strip layout), named or not -- channel 31
    # specifically is present but blank-named, so it fires Q2, not Q1.
    # 41 is the first genuinely absent channel number (Task 3's report
    # already established this same fact for this fixture). Channel 8
    # stays present as the non-firing control.
    found = fire([{"id": "S1", "cues": [
        {"id": "SQ 1", "action": "open", "channels": [8, 41]}]}], "Q1")
    assert [f.target for f in found] == ["cue.S1.SQ1"]
    assert "41" in found[0].message
    assert found[0].severity == "warning"


def test_q1_stays_silent_when_every_channel_is_present(fire):
    assert fire([{"id": "S1", "cues": [
        {"id": "SQ 1", "action": "open", "channels": [8]}]}], "Q1") == []


def test_q3_fires_on_an_absent_dca(fire):
    found = fire([{"id": "S1", "cues": [
        {"id": "SQ 1", "action": "open", "dcas": [99]}]}], "Q3")
    assert [f.target for f in found] == ["cue.S1.SQ1"]
    assert "99" in found[0].message


def test_q4_fires_when_an_expected_kind_has_no_channel(fire):
    found = fire([{"id": "S1", "expects": ["instrument.horns"]}], "Q4")
    assert [f.target for f in found] == ["expects.instrument.horns"]
    assert "instrument.horns" in found[0].message


def test_q4_stays_silent_when_the_kind_is_present(fire):
    assert fire([{"id": "S1", "expects": ["instrument.keys"]}], "Q4") == []


def test_q5_fires_when_the_kind_is_present_but_parked(fire):
    # Every instrument.keys channel on the sample file sits at -inf.
    found = fire([{"id": "S1", "expects": ["instrument.keys"]}], "Q5")
    assert [f.target for f in found] == ["expects.instrument.keys"]
    assert found[0].severity == "info"


def test_q5_does_not_double_report_a_kind_q4_already_flagged(fire):
    assert fire([{"id": "S1", "expects": ["instrument.horns"]}], "Q5") == []


def test_q6_fires_on_a_second_open_of_the_same_channel(fire):
    found = fire([{"id": "S1", "cues": [
        {"id": "SQ 1", "action": "open", "channels": [8]},
        {"id": "SQ 2", "action": "open", "channels": [8]}]}], "Q6")
    assert [f.target for f in found] == ["cue.S1.SQ2"]
    assert found[0].severity == "info"


def test_every_q_rule_now_exists():
    from wing_parser.advisory.loader import load_base_rules
    rules = {r.id for r in load_base_rules() if r.id.startswith("Q")}
    assert rules == {"Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7"}


def test_q7_ships_disabled_and_therefore_never_fires(fire):
    from wing_parser.advisory.loader import load_base_rules
    q7 = next(r for r in load_base_rules() if r.id == "Q7")
    assert q7.enabled is False
    assert "threshold" in q7.rationale.lower()
    # SQ 2's time runs BACKWARDS from SQ 1's on purpose, giving a NEGATIVE
    # gap -- exactly what Q7's predicate ({lt: 0}) matches. With
    # chronological times the gap would be non-negative and fire(...) ==
    # [] would pass regardless of enabled: false, since the predicate
    # would never match either way; that would not prove "disabled" is
    # what keeps Q7 silent. Do not "fix" these times into order.
    assert fire([{"id": "S1", "cues": [
        {"id": "SQ 1", "action": "open", "channels": [8], "time": "T+00:10:00"},
        {"id": "SQ 2", "action": "close", "channels": [8], "time": "T+00:09:59"}]}],
        "Q7") == []
