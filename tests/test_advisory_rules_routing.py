import pytest

from wing_parser import WingScene
from tests.conftest import _mutated_scene


@pytest.fixture(scope="module")
def vu_scene(vu_path):
    return WingScene.load(vu_path)


def _findings(scene, rule_id):
    return [f for f in scene.advisory.run() if f.rule_id == rule_id]


def test_r1_fires_when_a_click_reaches_the_foh_main(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "CLICK"
        for k, s in ae["ch"]["20"]["send"].items():
            s["on"] = False
        for m in ae["ch"]["20"]["main"].values():
            m["on"] = False
        ae["ch"]["20"]["main"]["1"]["on"] = True   # main 1 = MAIN FOH
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    findings = _findings(scene, "R1")
    assert [(f.target, f.severity) for f in findings] == [("ch.20.main.1", "error")]


def test_r1_stays_silent_when_the_click_feeds_only_monitors(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "CLICK"
        for k, s in ae["ch"]["20"]["send"].items():
            s["on"] = False
        for m in ae["ch"]["20"]["main"].values():
            m["on"] = False
        ae["ch"]["20"]["send"]["MX5"]["on"] = True   # IEM matrix is fine
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert _findings(scene, "R1") == []


def test_r2_fires_when_talkback_reaches_the_foh_main(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "TB"
        for k, s in ae["ch"]["20"]["send"].items():
            s["on"] = False
        for m in ae["ch"]["20"]["main"].values():
            m["on"] = False
        ae["ch"]["20"]["main"]["1"]["on"] = True
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _findings(scene, "R2")] == ["ch.20.main.1"]


def test_r2_allows_talkback_into_the_tb_out_main(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "TB"
        for k, s in ae["ch"]["20"]["send"].items():
            s["on"] = False
        for m in ae["ch"]["20"]["main"].values():
            m["on"] = False
        ae["ch"]["20"]["main"]["4"]["on"] = True   # main 4 'TB OUT' -> role talkback
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert _findings(scene, "R2") == []


def test_r3_and_r3m_fire_on_any_routed_timecode(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "LTC"
        for k, s in ae["ch"]["20"]["send"].items():
            s["on"] = False
        for m in ae["ch"]["20"]["main"].values():
            m["on"] = False
        ae["ch"]["20"]["send"]["9"]["on"] = True       # bus 9, mode whatever it was
        ae["ch"]["20"]["main"]["2"]["on"] = True
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _findings(scene, "R3")] == ["ch.20.send.9"]
    assert [f.target for f in _findings(scene, "R3M")] == ["ch.20.main.2"]


def test_routing_rules_are_silent_on_the_untouched_real_file(vu_scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    found = {f.rule_id for f in vu_scene.advisory.run()}
    assert found.isdisjoint({"R1", "R2", "R3", "R3M"})


def test_r4_fires_on_a_post_fader_send_to_a_record_bus(vu_path, tmp_path, monkeypatch):
    # Bus 12 (HALL) is not exclusive to ch.1 in the real file: chs 1-4
    # and 7 all already send to it POST and on (probed 2026-08-17), so
    # renaming it to RECORD legitimately makes R4 fire on all five, not
    # just ch.1 -- correct behaviour, since the rule is "any post-fader
    # send to a record destination", not "ch.1's send only". The
    # assertion below checks membership rather than the plan's original
    # exact-list equality for that reason.
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["bus"]["12"]["name"] = "RECORD"
        ae["ch"]["1"]["send"]["12"]["on"] = True
        ae["ch"]["1"]["send"]["12"]["mode"] = "POST"
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    findings = [f for f in scene.advisory.run() if f.rule_id == "R4"]
    assert ("ch.1.send.12", "warning") in [(f.target, f.severity) for f in findings]


def test_r4_is_silent_when_the_record_send_is_pre(vu_path, tmp_path, monkeypatch):
    # Same bus-12-is-shared caveat as the fires-test above: chs 2, 3, 4
    # and 7 stay POST and on, so they correctly keep firing R4 on their
    # own targets. Only ch.1's own send is under test here, so the
    # assertion checks that specific target is absent rather than that
    # the rule produced no findings at all.
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["bus"]["12"]["name"] = "RECORD"
        ae["ch"]["1"]["send"]["12"]["on"] = True
        ae["ch"]["1"]["send"]["12"]["mode"] = "PRE"
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    findings = [f for f in scene.advisory.run() if f.rule_id == "R4"]
    assert "ch.1.send.12" not in [f.target for f in findings]


def test_r5_fires_on_a_post_fader_main_send_to_a_record_main(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["main"]["3"]["name"] = "RECORD"       # was RECODING (typo, unclassified)
        # ch 1 already has main 3 on with pre False in the real file
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    findings = [f for f in scene.advisory.run() if f.rule_id == "R5"]
    assert ("ch.1.main.3", "warning") in [(f.target, f.severity) for f in findings]


def test_r6_fires_when_the_caller_feeds_its_own_mix_minus(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "ZOOM"
        ae["bus"]["12"]["name"] = "MIX MINUS"
        ae["ch"]["20"]["send"]["12"]["on"] = True
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    findings = [f for f in scene.advisory.run() if f.rule_id == "R6"]
    assert [(f.target, f.severity) for f in findings] == [("ch.20.send.12", "error")]


def test_n1_fires_on_an_unnamed_channel_that_is_actually_in_use(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ch = ae["ch"]["20"]
        ch["name"] = ""
        ch["fdr"] = 0
        ch["mute"] = False
        ch["main"]["1"]["on"] = True
        ch["in"]["conn"]["grp"] = "A"
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in scene.advisory.run() if f.rule_id == "N1"] == ["ch.20"]


def test_n2_ships_disabled_because_factory_bus_faders_are_not_all_floored(
    vu_path, tmp_path, monkeypatch
):
    """Step 2's probe of user-files/factory-scene.snap found bus faders in
    {-144, 0} -- buses 9-16 sit at raw fdr 0 (unity), not the -144 "off"
    sentinel main/mtx/aux all use. N2 as designed (bus.receives_any AND
    bus.fader_dB > -90) cannot rely on the fader condition to keep the
    factory scene finding-free the way N1 relies on it for channels, so
    it ships with `enabled: false` (see naming.yaml) instead of silently
    narrowing its own semantics. This mutation recreates the exact shape
    N2's `where` clause targets -- unnamed bus, floored fader raised,
    a live send landing on it -- to prove the rule would otherwise have
    matched; `run()` must still report nothing for it because it never
    evaluates a disabled rule at all (see evaluator.evaluate).
    """
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["bus"]["12"]["name"] = ""
        ae["bus"]["12"]["fdr"] = 0
        ae["ch"]["1"]["send"]["12"]["on"] = True
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    rule = next(r for r in scene.advisory.rules() if r.id == "N2")
    assert rule.enabled is False
    assert [f.target for f in scene.advisory.run() if f.rule_id == "N2"] == []
