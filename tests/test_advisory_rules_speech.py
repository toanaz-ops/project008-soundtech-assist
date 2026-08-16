import pytest

from wing_parser import WingScene
from tests.conftest import _mutated_scene


@pytest.fixture(scope="module")
def vu_scene(vu_path):
    return WingScene.load(vu_path)


def test_s1_fires_on_a_speech_channel_without_hpf(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "LECTERN"
        ae["ch"]["20"]["flt"]["lc"] = False
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    findings = [f for f in scene.advisory.run() if f.rule_id == "S1"]
    assert [(f.target, f.severity) for f in findings] == [("ch.20", "warning")]


def test_s1_respects_the_engaged_hpf(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "LECTERN"
        ae["ch"]["20"]["flt"]["lc"] = True
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    targets = [f.target for f in scene.advisory.run() if f.rule_id == "S1"]
    assert "ch.20" not in targets


def test_s1_on_the_real_file_matches_the_probe(vu_scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    findings = sorted(f.target for f in vu_scene.advisory.run() if f.rule_id == "S1")
    # Probed 2026-08-17: the five speech-classified channels (ch.1/2/3
    # "Mic N VOX IEMn" -> speech.vocal, ch.8 "M8 MC" -> speech.mc, ch.11
    # "HS4" -> speech.headset) all have raw flt.lc True, so S1 is silent
    # on the untouched real file. Re-verify with the Task 2 probe script
    # if this ever goes red.
    assert findings == []


def test_s2_fires_when_playback_sits_in_an_active_automix_group(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "PLAYBACK"
        ae["ch"]["20"]["postins"]["on"] = True
        # ch.20's real postins.mode is "FX" (probed 2026-08-17), not
        # AUTO_X like chs 1-8/11 -- the brief's "AUTO_X mode already
        # present" comment does not hold for channel 20, so the mode is
        # set explicitly here to land the fixture in an active automix
        # group (group name "X", from mode "AUTO_X").
        ae["ch"]["20"]["postins"]["mode"] = "AUTO_X"
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    findings = [f for f in scene.advisory.run() if f.rule_id == "S2"]
    assert [(f.target, f.severity) for f in findings] == [("ch.20", "error")]


def test_s2_ignores_a_configured_but_inactive_automix(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "PLAYBACK"
        ae["ch"]["20"]["postins"]["on"] = False
        ae["ch"]["20"]["postins"]["mode"] = "AUTO_X"
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f for f in scene.advisory.run() if f.rule_id == "S2"] == []


def test_g10_fires_on_every_iem_output_when_no_ambient_channel_exists(vu_scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    findings = sorted(f.target for f in vu_scene.advisory.run() if f.rule_id == "G10")
    assert findings == ["matrix.5", "matrix.6", "matrix.7", "matrix.8"]
    severities = {f.severity for f in vu_scene.advisory.run() if f.rule_id == "G10"}
    assert severities == {"info"}


def test_g11_fires_beyond_five_notches_on_a_monitor(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        eq = ae["bus"]["7"]["eq"]                   # SIDEFILL -> monitor.wedge
        eq["on"] = True
        # Bus EQ parses exactly 6 STD bands: low (lg/lf/lq, shape leq),
        # 1-4 (Ng/Nf/Nq), high (hg/hf/hq, shape heq) -- there are no
        # 5g/6g bands (verified against eq_models.yaml and
        # tests/test_query_bus.py::TestNotchCount). leq/heq must also be
        # moved off the real file's "SHV" (shelf) shape, since a shelf
        # never counts as a notch regardless of gain/Q.
        eq["leq"], eq["heq"] = "PEQ", "PEQ"
        for prefix in ("l", "1", "2", "3", "4", "h"):
            eq[f"{prefix}g"] = -8.0
            eq[f"{prefix}q"] = 10.0
            eq[f"{prefix}f"] = 400.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert scene.bus(7).notch_count == 6
    findings = [f for f in scene.advisory.run() if f.rule_id == "G11"]
    assert [(f.target, f.severity) for f in findings] == [("bus.7", "warning")]


def test_g12_fires_on_a_high_boost_on_the_foh_main(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        eq = ae["main"]["1"]["eq"]
        eq["on"] = True
        eq["1g"], eq["1f"], eq["1q"] = 3.0, 10000.0, 1.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    findings = [f for f in scene.advisory.run() if f.rule_id == "G12"]
    assert [(f.target, f.severity) for f in findings] == [("main.1", "info")]


def test_g11_and_g12_are_silent_on_the_untouched_real_file(vu_scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    found = {f.rule_id for f in vu_scene.advisory.run()}
    # Probed 2026-08-17: no output's real EQ carries more than five
    # q>=8/gain<=-6 bands (every bus.notch_count is 0), and the only
    # main/pa_zone outputs (main.1, matrix.1 FLOWN, matrix.4 CEN) all
    # read max_boost_above_8k None. Matrix 5 (IEM MC) does carry a real
    # +0.3 dB band above 8k, but its role is monitor.iem, outside G12's
    # {in: [main, pa_zone]} where-clause.
    assert found.isdisjoint({"G11", "G12"})


def test_s1_s2_g10_g11_g12_are_silent_on_the_factory_scene(factory_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    scene = WingScene.load(factory_path)
    found = {f.rule_id for f in scene.advisory.run()}
    assert found.isdisjoint({"S1", "S2", "G10", "G11", "G12"})
