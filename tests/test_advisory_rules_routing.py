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
