"""library_dir resolution and the shipped layer path."""

import pytest

from wing_parser import config


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv(config.LIBRARY_ENV_VAR, raising=False)


def test_unfrozen_default_is_the_repo_copy(monkeypatch):
    monkeypatch.setattr(config, "is_frozen", lambda: False)
    assert config.library_dir() == config.shipped_library_dir()
    assert config.library_dir().parts[-2:] == ("knowledge", "library")


def test_frozen_never_resolves_into_the_bundle(monkeypatch):
    monkeypatch.setattr(config, "is_frozen", lambda: True)
    assert config.library_dir() == config.USER_DEFAULT / "library"
    assert config.library_dir() != config.shipped_library_dir()


def test_env_var_and_override_win(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "is_frozen", lambda: True)
    monkeypatch.setenv(config.LIBRARY_ENV_VAR, str(tmp_path / "env"))
    assert config.library_dir() == tmp_path / "env"
    assert config.library_dir(tmp_path / "x") == tmp_path / "x"


def test_resolving_does_not_create_anything(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "is_frozen", lambda: True)
    monkeypatch.setenv(config.LIBRARY_ENV_VAR, str(tmp_path / "nope"))
    config.library_dir()
    assert not (tmp_path / "nope").exists()
