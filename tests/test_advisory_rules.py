import json

import pytest

from wing_parser import WingScene
from wing_parser import config
from wing_parser.advisory.loader import load_base_rules

from tests.conftest import _mutated_scene


@pytest.fixture(scope="module")
def scene(vu_path):
    return WingScene.load(vu_path)


def test_the_full_base_rule_set_ships(scene):
    assert {r.id for r in load_base_rules()} == {
        "G8", "G7", "G9", "E6", "R1", "R2", "R3", "R3M",
        "R4", "R5", "R6", "N1", "N2",
        "S1", "S2", "G10", "G11", "G12",
        "Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7",
        "PC1", "PC2", "PC3", "PC4", "PC5", "PC6", "PC7", "PC8",
        "PB1", "PB2", "PB3", "PB4", "PB5", "PB6",
    }


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


def test_g7_is_silent_because_every_iem_matrix_has_dynamics_on(scene, monkeypatch):
    # Split 2026-08-16: G7 now only looks at bus.role == monitor.iem, and
    # for_each is `output` so its domain is the whole bus family. Probed
    # 2026-08-16 against the raw ae_data: matrix 5 (IEM MC), 6 (IEM CA SI
    # 1), 7 (IEM CA SI 2) and 8 (IEM3 BAKUP) -- the only monitor.iem
    # outputs in the file -- all read dyn.on: True, dyn.mdl: "COMP". Bus 7
    # SIDEFILL, the old sole G7 target, is monitor.wedge now and moved to
    # G9 below.
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    assert [f for f in scene.advisory.run() if f.rule_id == "G7"] == []


def test_g9_fires_on_the_sidefill_at_warning(scene, monkeypatch):
    # Probed 2026-08-16: bus 7 SIDEFILL (monitor.wedge) is the only
    # monitor-role output in the file with dyn.on: False. Bus 8/9/10
    # (MON VOX/L/R, plain `monitor`) and matrix 3 SIDE (monitor.wedge) all
    # read dyn.on: True, so they do not join this list.
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    findings = [f for f in scene.advisory.run() if f.rule_id == "G9"]
    assert [(f.target, f.severity) for f in findings] == [("bus.7", "warning")]


def test_g9_states_facts_rather_than_asserting_a_conclusion(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    message = next(f for f in scene.advisory.run() if f.rule_id == "G9").message
    assert "COMP" in message
    assert "not a limiter" not in message


def test_g7_fires_when_an_iem_matrix_bypasses_dynamics(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    scene = _mutated_scene(vu_path, tmp_path,
                           lambda ae: ae["mtx"]["5"]["dyn"].__setitem__("on", False))
    findings = [f for f in scene.advisory.run() if f.rule_id == "G7"]
    assert [(f.target, f.severity) for f in findings] == [("matrix.5", "error")]


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


def test_the_shipped_small_profile_loads_and_suppresses_g8_and_g10(scene, monkeypatch):
    # G7 no longer fires on this file post-split (all IEM matrices have
    # dyn.on True); bus.7 SIDEFILL's finding moved to G9. Probed
    # 2026-08-16 with profile="small": {E6 ch.11, G9 bus.7}, G8 absent.
    # Task 10 (2026-08-17) added G10, which fires on the same four IEM
    # matrices as the untouched-file probe in
    # test_the_sample_scene_finding_counts (no ambient channel exists
    # anywhere in this file) -- re-probed with profile="small":
    # {E6 ch.11, G9 bus.7, G10 x4}, G8 still absent.
    # Task 12 (2026-08-17) added the band presets. The shipped "small"
    # profile sets no `event`, so it does not switch the band family off,
    # and this file's real drum channels fire PB1/PB2/PB4/PB5 the same as
    # the unprofiled run in test_the_sample_scene_finding_counts --
    # re-probed with profile="small": {E6 ch.11, G9 bus.7, G10 x4,
    # PB1/PB2/PB4/PB5 x1 each}, G8 still absent.
    # 2026-08-17: the profile gained a second rule superseding G10, on the
    # probed ground that this rig carries no ambient mic at all (34 named
    # channels, none classifying utility.ambient), so the four G10
    # findings name a microphone that does not exist. Re-probed with
    # profile="small": {E6 ch.11, G9 bus.7, PB1/PB2/PB4/PB5 x1 each} = 6,
    # G8 and G10 both absent. The unprofiled run is unchanged at 22 --
    # test_the_real_file_advisory_contract still pins all four G10 rows.
    monkeypatch.delenv(config.ENV_VAR, raising=False)
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    found = scene.advisory.run(profile="small")
    assert [f.rule_id for f in found if f.rule_id in {"G8", "G10"}] == []
    assert {f.rule_id for f in found} == {"G9", "E6", "PB1", "PB2", "PB4", "PB5"}
    assert len(found) == 6


def test_the_small_profile_records_who_switched_each_rule_off(scene, monkeypatch):
    monkeypatch.delenv(config.ENV_VAR, raising=False)
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    assert scene.advisory.suppressed(profile="small") == {
        "G8": "show.small.post-monitors-are-deliberate",
        "G10": "show.small.no-ambient-mic-is-the-rig",
    }


def test_the_shipped_principles_file_still_loads(scene, monkeypatch):
    """principles.yaml holds no principles now. It must still parse, and
    it must not quietly stop being read.

    `layers._principles` returns [] both when the shipped file parses to
    `principles: []` and when the file is simply absent, so asserting only
    on `.rules()` / `.layer == "toanaz"` would pass identically either way.
    Assert the file's on-disk text directly so this test can only pass
    against the real shipped file, not against its absence.
    """
    monkeypatch.delenv(config.ENV_VAR, raising=False)
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    principles_path = config.knowledge_dir() / "principles.yaml"
    assert principles_path.is_file()
    assert "principles: []" in principles_path.read_text(encoding="utf-8")
    assert scene.advisory.rules()
    assert [r for r in scene.advisory.rules() if r.layer == "toanaz"] == []
