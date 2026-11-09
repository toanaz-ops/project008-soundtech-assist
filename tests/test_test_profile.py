"""DEVCAVE_TEST_PROFILE isolates every per-user path under one directory."""

from pathlib import Path

import pytest

from wing_parser import config


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv(config.ENV_VAR, raising=False)
    monkeypatch.delenv(config.LIBRARY_ENV_VAR, raising=False)
    monkeypatch.delenv(config.PROFILE_ENV_VAR, raising=False)


def test_unset_keeps_the_real_paths(monkeypatch):
    monkeypatch.setattr(config, "is_frozen", lambda: True)
    assert config.test_profile() is None
    assert config.user_dir() == config.USER_DEFAULT
    assert config.knowledge_dir() == config.USER_DEFAULT
    assert config.library_dir() == config.USER_DEFAULT / "library"


def test_empty_value_counts_as_unset(monkeypatch):
    monkeypatch.setenv(config.PROFILE_ENV_VAR, "  ")
    assert config.test_profile() is None


@pytest.mark.parametrize("frozen", [True, False])
def test_set_roots_every_path_under_the_profile(monkeypatch, tmp_path, frozen):
    monkeypatch.setattr(config, "is_frozen", lambda: frozen)
    monkeypatch.setenv(config.PROFILE_ENV_VAR, str(tmp_path))
    # Real-path env vars must not leak past the profile.
    monkeypatch.setenv(config.ENV_VAR, str(Path.home() / "real-knowledge"))
    monkeypatch.setenv(config.LIBRARY_ENV_VAR, str(Path.home() / "real-library"))
    for path in (config.user_dir(), config.knowledge_dir(), config.library_dir()):
        assert path.is_relative_to(tmp_path / "home")


def test_relative_profile_is_rejected(monkeypatch):
    monkeypatch.setenv(config.PROFILE_ENV_VAR, "relative/dir")
    with pytest.raises(ValueError):
        config.knowledge_dir()


def test_state_file_lands_in_the_profile(monkeypatch, tmp_path):
    from wing_parser.ui import state_store

    monkeypatch.setenv(config.PROFILE_ENV_VAR, str(tmp_path))
    state_store.save_author(config.knowledge_dir(), "tester")
    assert (tmp_path / "home" / ".config" / "wing-skill" / state_store.STATE_FILE).is_file()


def test_window_title_carries_the_marker(qt_app, monkeypatch, tmp_path, vu_path):
    from wing_parser.ui.main_window import MainWindow
    from wing_parser.ui.session import Session

    monkeypatch.setenv(config.PROFILE_ENV_VAR, str(tmp_path))
    window = MainWindow(Session.open(vu_path))
    assert window.windowTitle().endswith(config.PROFILE_TITLE_MARKER)
    empty = MainWindow(None)
    assert empty.windowTitle().endswith(config.PROFILE_TITLE_MARKER)


def test_window_title_has_no_marker_when_unset(qt_app, vu_path):
    from wing_parser.ui.main_window import MainWindow
    from wing_parser.ui.session import Session

    window = MainWindow(Session.open(vu_path))
    assert config.PROFILE_TITLE_MARKER not in window.windowTitle()
