from pathlib import Path

import pytest
import yaml

from wing_parser import config
from wing_parser.classifier import cache
from wing_parser.classifier.matcher import Classification


@pytest.fixture
def knowledge(tmp_path: Path) -> Path:
    directory = tmp_path / "knowledge"
    directory.mkdir()
    (directory / "classifier.yaml").write_text(
        yaml.safe_dump({"channels": {}, "buses": {}}), encoding="utf-8"
    )
    return directory


def test_env_var_wins_over_every_other_location(tmp_path, monkeypatch):
    override = tmp_path / "elsewhere"
    override.mkdir()
    monkeypatch.setenv(config.ENV_VAR, str(override))
    assert config.knowledge_dir() == override


def test_repo_default_is_used_when_the_env_var_is_unset(monkeypatch):
    monkeypatch.delenv(config.ENV_VAR, raising=False)
    assert config.knowledge_dir().name == "toanaz"


def test_explicit_override_beats_the_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv(config.ENV_VAR, str(tmp_path / "ignored"))
    explicit = tmp_path / "explicit"
    explicit.mkdir()
    assert config.knowledge_dir(override=explicit) == explicit


def test_lookup_misses_on_an_empty_cache(knowledge):
    assert cache.lookup("Kick In", "channels", directory=knowledge) is None


def test_remember_then_lookup_round_trips(knowledge):
    entry = Classification(kind="utility.playback", confidence=0.8, origin="llm")
    cache.remember("My Lap", "channels", entry, directory=knowledge)

    found = cache.lookup("My Lap", "channels", directory=knowledge)
    assert found is not None
    assert found.kind == "utility.playback"
    assert found.confidence == pytest.approx(0.8)
    assert found.origin == "llm"


def test_lookup_is_insensitive_to_case_and_trailing_space(knowledge):
    cache.remember("Kick In ", "channels", Classification("drums.kick.in", 0.95, "manual"), directory=knowledge)
    assert cache.lookup("KICK IN", "channels", directory=knowledge) is not None
    assert cache.lookup("  kick in  ", "channels", directory=knowledge) is not None


def test_domains_do_not_collide(knowledge):
    cache.remember("MON VOX", "buses", Classification("monitor", 0.9, "manual"), directory=knowledge)
    assert cache.lookup("MON VOX", "channels", directory=knowledge) is None
    assert cache.lookup("MON VOX", "buses", directory=knowledge) is not None


def test_remember_persists_to_disk_in_readable_yaml(knowledge):
    cache.remember("My Lap", "channels", Classification("utility.playback", 0.8, "llm"), directory=knowledge)

    doc = yaml.safe_load((knowledge / "classifier.yaml").read_text(encoding="utf-8"))
    assert doc["channels"]["my lap"]["kind"] == "utility.playback"
    assert doc["channels"]["my lap"]["origin"] == "llm"


def test_missing_cache_file_is_created_on_first_write(tmp_path):
    empty = tmp_path / "fresh"
    empty.mkdir()
    cache.remember("Bass", "channels", Classification("instrument.bass", 0.9, "pattern"), directory=empty)
    assert (empty / "classifier.yaml").exists()


ANNOTATED = """\
# ToanAZ's own header. This must survive every write.
channels:
  kick in:            # judged by ear at the Hanoi show, do not re-guess
    kind: drums.kick.in
    confidence: 1.0
    origin: manual
buses: {}
"""


def test_writes_preserve_comments_the_human_wrote(tmp_path):
    directory = tmp_path / "annotated"
    directory.mkdir()
    target = directory / "classifier.yaml"
    target.write_text(ANNOTATED, encoding="utf-8")

    cache.remember("My Lap", "channels", Classification("utility.playback", 0.8, "llm"), directory=directory)
    after_one = target.read_text(encoding="utf-8")
    assert "ToanAZ's own header" in after_one
    assert "do not re-guess" in after_one

    # A second write must not erode what the first one preserved.
    cache.remember("MON VOX", "buses", Classification("monitor", 0.9, "pattern"), directory=directory)
    after_two = target.read_text(encoding="utf-8")
    assert "ToanAZ's own header" in after_two
    assert "do not re-guess" in after_two
    assert cache.lookup("Kick In", "channels", directory=directory).origin == "manual"
    assert cache.lookup("My Lap", "channels", directory=directory) is not None
    assert cache.lookup("MON VOX", "buses", directory=directory) is not None


def test_the_shipped_seed_file_matches_the_module_fallback():
    # cache.py falls back to _SEED when the file is absent; if the two
    # drift, a fresh checkout and a fresh install disagree on the format.
    shipped = (config.knowledge_dir() / "classifier.yaml").read_text(encoding="utf-8")
    assert shipped == cache._SEED


def test_a_hand_edited_entry_missing_a_key_names_the_file_and_the_key(tmp_path):
    directory = tmp_path / "broken"
    directory.mkdir()
    (directory / "classifier.yaml").write_text(
        "channels:\n  kick in:\n    origin: manual\nbuses: {}\n", encoding="utf-8"
    )
    with pytest.raises(ValueError) as excinfo:
        cache.load(directory=directory)

    message = str(excinfo.value)
    assert "classifier.yaml" in message
    assert "kick in" in message
    assert "kind" in message
