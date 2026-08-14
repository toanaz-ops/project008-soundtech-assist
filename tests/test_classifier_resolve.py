import pytest
import yaml

from wing_parser import WingScene
from wing_parser.classifier.matcher import HIGH, Classification
from wing_parser.classifier.resolve import Classifier


@pytest.fixture
def knowledge(tmp_path):
    directory = tmp_path / "knowledge"
    directory.mkdir()
    (directory / "classifier.yaml").write_text(
        yaml.safe_dump({"channels": {}, "buses": {}}), encoding="utf-8"
    )
    return directory


def test_pattern_hit_is_returned(knowledge):
    result = Classifier(directory=knowledge, use_llm=False).resolve("Kick In ", "channels")
    assert result.kind == "drums.kick.in"
    assert result.origin == "pattern"


def test_cache_entry_beats_the_pattern_matcher(knowledge):
    from wing_parser.classifier import cache

    cache.remember(
        "Kick In ", "channels",
        Classification("drums.kick.trigger", 1.0, "manual"),
        directory=knowledge,
    )
    result = Classifier(directory=knowledge, use_llm=False).resolve("Kick In", "channels")
    assert result.kind == "drums.kick.trigger"
    assert result.origin == "manual"


def test_unresolvable_name_is_unknown_with_llm_off(knowledge):
    classifier = Classifier(directory=knowledge, use_llm=False)
    assert classifier.resolve("My Lap", "channels").kind == "unknown"
    assert "My Lap" in classifier.unresolved


def test_weak_match_is_recorded_as_low_confidence(knowledge):
    classifier = Classifier(directory=knowledge, use_llm=False)
    result = classifier.resolve("Mic 4", "channels")
    assert result.confidence < HIGH
    assert "Mic 4" in classifier.low_confidence


def test_llm_is_consulted_only_below_the_gate(knowledge, monkeypatch):
    calls: list[str] = []

    def fake(name, domain, context=""):
        calls.append(name)
        return Classification("utility.playback", 0.82, "llm")

    monkeypatch.setattr("wing_parser.classifier.resolve.llm.available", lambda: True)
    monkeypatch.setattr("wing_parser.classifier.resolve.llm.classify", fake)

    classifier = Classifier(directory=knowledge, use_llm=True)
    classifier.resolve("Kick In", "channels")      # confident pattern hit
    classifier.resolve("My Lap", "channels")       # nothing matches

    assert calls == ["My Lap"]


def test_llm_answer_is_flushed_to_the_cache(knowledge, monkeypatch):
    monkeypatch.setattr("wing_parser.classifier.resolve.llm.available", lambda: True)
    monkeypatch.setattr(
        "wing_parser.classifier.resolve.llm.classify",
        lambda name, domain, context="": Classification("utility.playback", 0.82, "llm"),
    )

    classifier = Classifier(directory=knowledge, use_llm=True)
    classifier.resolve("My Lap", "channels")
    classifier.flush()

    doc = yaml.safe_load((knowledge / "classifier.yaml").read_text(encoding="utf-8"))
    assert doc["channels"]["my lap"]["origin"] == "llm"


def test_resolution_is_memoised_within_one_classifier(knowledge, monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr("wing_parser.classifier.resolve.llm.available", lambda: True)
    monkeypatch.setattr(
        "wing_parser.classifier.resolve.llm.classify",
        lambda name, domain, context="": (calls.append(name), Classification("x", 0.9, "llm"))[1],
    )

    classifier = Classifier(directory=knowledge, use_llm=True)
    classifier.resolve("My Lap", "channels")
    classifier.resolve("My Lap", "channels")
    assert len(calls) == 1


def test_scene_exposes_source_type_and_bus_role(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    scene = WingScene.load(vu_path)

    assert scene.channel(8).source_type.kind == "speech.mc"
    assert scene.channel(13).source_type.kind == "drums.kick.in"
    assert scene.bus(8).role.kind == "monitor"
    assert scene.bus(8).is_monitor is True
    assert scene.bus(12).is_monitor is False        # HALL is an fx bus


def test_monitor_buses_in_the_real_file(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    scene = WingScene.load(vu_path)
    monitors = {bus.number for bus in scene.buses() if bus.is_monitor}
    assert {8, 9, 10} <= monitors


def test_unclassified_channels_are_listed_not_dropped(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    scene = WingScene.load(vu_path)
    names = {view.name for view in scene.unclassified()}
    assert "My Lap" in names
    assert "Kick In " not in names


def test_offline_run_still_classifies_by_pattern(vu_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    scene = WingScene.load(vu_path)
    assert scene.bus(8).is_monitor is True          # MON VOX resolves offline


def test_a_blank_name_costs_nothing_and_is_not_a_naming_problem(knowledge, monkeypatch):
    # Six channels in the real file are unnamed. An empty slot is not a
    # name that needs improving, and it must never reach the model.
    called: list[str] = []
    monkeypatch.setattr("wing_parser.classifier.resolve.llm.available", lambda: True)
    monkeypatch.setattr(
        "wing_parser.classifier.resolve.llm.classify",
        lambda name, domain, context="": called.append(name) or Classification("x", 0.9, "llm"),
    )

    classifier = Classifier(directory=knowledge, use_llm=True)
    for blank in ("", "   ", "\t"):
        assert classifier.resolve(blank, "channels").kind == "unknown"

    assert called == []
    assert classifier.unresolved == ()
    assert classifier.low_confidence == ()


def test_the_knowledge_file_is_read_once_not_once_per_name(knowledge, monkeypatch):
    # cache.lookup() re-parses the whole file per call, and since Task 15
    # that parse is a ruamel round-trip. Measured on a 200-entry cache:
    # 50 per-name lookups took 3.4 s against 65 ms for one load. The file
    # grows one entry per name ever seen, so per-name reads get slower
    # exactly as the tool gets used.
    from wing_parser.classifier import resolve as resolve_module

    loads: list[object] = []
    real_load = resolve_module.cache.load

    def counted(directory=None):
        loads.append(directory)
        return real_load(directory)

    monkeypatch.setattr(resolve_module.cache, "load", counted)

    classifier = Classifier(directory=knowledge, use_llm=False)
    for name in ("Kick In", "Snare Top", "My Lap", "HS4", "MON VOX"):
        classifier.resolve(name, "channels")

    assert len(loads) == 1


def test_a_classifier_nobody_asks_touches_no_disk(monkeypatch):
    # WingScene builds one unconditionally, including for scenes the
    # caller only wants routing or levels from.
    from wing_parser.classifier import resolve as resolve_module

    def explode(directory=None):
        raise AssertionError("the knowledge file was read on construction")

    monkeypatch.setattr(resolve_module.cache, "load", explode)
    Classifier(directory=None, use_llm=False)       # must not raise
