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
