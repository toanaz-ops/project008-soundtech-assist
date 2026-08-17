import pytest
import yaml

from wing_parser import WingScene
from wing_parser.advisory.evaluator import ITERATORS, targets_for


@pytest.fixture
def show_file(tmp_path):
    path = tmp_path / "tonight.yaml"
    path.write_text(yaml.safe_dump({
        "show": "t",
        "segments": [{"id": "S1", "expects": ["speech.mc"],
                      "cues": [{"id": "SQ 1", "action": "open", "channels": [8]}]}],
    }), encoding="utf-8")
    return path


def test_both_iterators_are_registered():
    assert "cue" in ITERATORS and "segment" in ITERATORS


def test_without_a_context_both_iterators_yield_nothing(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    scene = WingScene.load(vu_path)
    assert scene.show is None
    assert list(targets_for(scene, "cue")) == []
    assert list(targets_for(scene, "segment")) == []


def test_with_a_context_targets_carry_the_expected_names(vu_path, show_file, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    scene = WingScene.load(vu_path, show=show_file)
    assert [t.name for t in targets_for(scene, "cue")] == ["cue.S1.SQ1"]
    assert [t.name for t in targets_for(scene, "segment")] == ["segment.S1"]
    cue_target = next(iter(targets_for(scene, "cue")))
    assert set(cue_target.context) == {"cue", "segment"}
    assert cue_target.confidence == 1.0


def test_the_unprofiled_real_file_contract_is_untouched(vu_path, monkeypatch):
    """The load-bearing test: adding show context must not move a
    single existing finding. 22 rows are pinned in
    tests/test_advisory_realfile.py; assert the count here so a
    regression in this subsystem is caught in this subsystem's file."""
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    assert len(WingScene.load(vu_path).advisory.run()) == 22
