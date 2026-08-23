"""Where a packaged build keeps the user's knowledge directory.

The bug these guard against is silent and total: inside a PyInstaller
bundle `__file__` resolves into a temporary extraction directory that
is deleted on exit, so a knowledge directory resolved from it would
swallow every verdict the operator recorded and report nothing wrong.
"""

import json

import pytest

from wing_parser import config


@pytest.fixture(autouse=True)
def _no_env_override(monkeypatch):
    # conftest points the whole suite at a throwaway directory via the
    # environment variable, which would short-circuit every case here.
    monkeypatch.delenv(config.ENV_VAR, raising=False)


def test_an_unfrozen_run_still_prefers_the_in_repo_directory(monkeypatch):
    monkeypatch.setattr(config, "is_frozen", lambda: False)
    assert config.knowledge_dir() == config._REPO_DEFAULT


def test_a_frozen_run_never_resolves_inside_the_bundle(monkeypatch):
    monkeypatch.setattr(config, "is_frozen", lambda: True)
    resolved = config.knowledge_dir()

    assert resolved == config.USER_DEFAULT
    assert resolved != config._REPO_DEFAULT
    # The bundle's own copy is SEARCH_ORDER[0] and does exist inside a
    # frozen build, so a plain first-existing-wins walk would pick it.
    assert config.SEARCH_ORDER[0] == config._REPO_DEFAULT


def test_the_explicit_override_still_wins_when_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "is_frozen", lambda: True)
    assert config.knowledge_dir(tmp_path) == tmp_path


def test_the_environment_variable_still_wins_when_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "is_frozen", lambda: True)
    monkeypatch.setenv(config.ENV_VAR, str(tmp_path))
    assert config.knowledge_dir() == tmp_path


def test_is_frozen_is_false_in_a_normal_interpreter():
    assert config.is_frozen() is False


def test_seed_copies_the_starting_set_into_an_empty_target(tmp_path):
    source = tmp_path / "bundled"
    (source / "shows").mkdir(parents=True)
    (source / "principles.yaml").write_text("principles: []", encoding="utf-8")
    (source / "shows" / "small.yaml").write_text("event: universal", encoding="utf-8")

    target = tmp_path / "user"
    assert config.seed_user_dir(target, source) is True
    assert (target / "principles.yaml").read_text(encoding="utf-8") == "principles: []"
    assert (target / "shows" / "small.yaml").exists()


def test_seed_never_overwrites_what_the_user_has_edited(tmp_path):
    source = tmp_path / "bundled"
    source.mkdir()
    (source / "principles.yaml").write_text("principles: []", encoding="utf-8")

    target = tmp_path / "user"
    target.mkdir()
    edited = target / "principles.yaml"
    edited.write_text("principles: [his own work]", encoding="utf-8")

    assert config.seed_user_dir(target, source) is False
    assert edited.read_text(encoding="utf-8") == "principles: [his own work]"


def test_seed_does_not_truncate_an_existing_feedback_log(tmp_path):
    """The failure that would hurt most, asserted directly."""
    source = tmp_path / "bundled"
    source.mkdir()
    (source / "feedback.jsonl").write_text("", encoding="utf-8")

    target = tmp_path / "user"
    target.mkdir()
    log = target / "feedback.jsonl"
    log.write_text(json.dumps({"rule_id": "G8", "verdict": "false-positive"}) + "\n",
                   encoding="utf-8")

    config.seed_user_dir(target, source)
    assert "G8" in log.read_text(encoding="utf-8")


def test_seed_is_a_no_op_when_there_is_nothing_to_copy(tmp_path):
    assert config.seed_user_dir(tmp_path / "user", tmp_path / "missing") is False


def test_seeding_a_directory_onto_itself_is_refused(tmp_path):
    tmp_path.joinpath("principles.yaml").write_text("principles: []", encoding="utf-8")
    assert config.seed_user_dir(tmp_path, tmp_path) is False


def test_a_frozen_app_keeps_verdicts_across_two_sessions(monkeypatch, tmp_path):
    """End to end: record, throw the process away, read it back.

    Simulates the real failure by pointing the "bundle" at a directory
    the test then deletes, exactly as PyInstaller deletes _MEIPASS.
    """
    from wing_parser.advisory import feedback
    from wing_parser.advisory.models import Finding

    bundle = tmp_path / "meipass" / "knowledge" / "toanaz"
    bundle.mkdir(parents=True)
    (bundle / "principles.yaml").write_text("principles: []", encoding="utf-8")

    user_dir = tmp_path / "home" / ".config" / "wing-skill"
    monkeypatch.setattr(config, "is_frozen", lambda: True)
    monkeypatch.setattr(config, "USER_DEFAULT", user_dir)
    monkeypatch.setattr(config, "bundled_dir", lambda: bundle)

    assert config.seed_user_dir() is True

    finding = Finding(rule_id="G8", layer="base", severity="warning",
                      target="ch.1.send.8", message="x")
    feedback.record(finding, "false-positive", scene="s.snap")

    # The bundle goes away when the process exits.
    import shutil
    shutil.rmtree(tmp_path / "meipass")

    entries = feedback.read_log()
    assert len(entries) == 1
    assert entries[0].verdict == "false-positive"
