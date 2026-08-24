"""Config search order, defaults, and factory dispatch."""
from pathlib import Path

from wing_parser.classifier.provider import (
    DEFAULT_CONFIG,
    load_config,
    make_provider,
    resolve,
)
# The adapter classes live in their own modules (Tasks 2 and 3), so they
# are imported from there, never from provider.py:
from wing_parser.classifier.provider_anthropic import AnthropicProvider
from wing_parser.classifier.provider_openai import OpenAICompatProvider


def _write_openai(tmp_path):
    target = tmp_path / "provider.yaml"
    target.write_text(
        "provider: openai-compat\nmodel: deepseek-v4-flash\n"
        "base_url: https://api.deepseek.com\n", encoding="utf-8"
    )
    return target


def test_defaults_are_anthropic_unchanged():
    cfg = resolve(DEFAULT_CONFIG)
    assert cfg.name == "anthropic"
    assert cfg.model == "claude-opus-5"
    assert cfg.api_key_env == "ANTHROPIC_API_KEY"


def test_yaml_file_wins(tmp_path, monkeypatch):
    target = tmp_path / "provider.yaml"
    target.write_text(
        "provider: openai-compat\nmodel: deepseek-v4-flash\n"
        "base_url: https://api.deepseek.com\n", encoding="utf-8"
    )
    cfg = resolve(load_config(target))
    assert cfg.name == "openai-compat"
    assert cfg.model == "deepseek-v4-flash"
    assert cfg.api_key_env == "DEEPSEEK_API_KEY"  # filled default


def test_env_var_points_at_file(tmp_path, monkeypatch):
    target = tmp_path / "p.yaml"
    target.write_text("provider: openai-compat\n", encoding="utf-8")
    monkeypatch.setenv("WING_PROVIDER_CONFIG", str(target))
    assert load_config(None).name == "openai-compat"


def test_no_file_anywhere_gives_default(monkeypatch, tmp_path):
    monkeypatch.delenv("WING_PROVIDER_CONFIG", raising=False)
    monkeypatch.chdir(tmp_path)
    assert load_config(None) == DEFAULT_CONFIG


def test_unknown_provider_refused(tmp_path):
    target = tmp_path / "p.yaml"
    target.write_text("provider: palm\n", encoding="utf-8")
    try:
        load_config(target)
    except ValueError as exc:
        assert "palm" in str(exc)
    else:
        raise AssertionError("unknown provider accepted")


def test_make_provider_dispatch(tmp_path, monkeypatch):
    monkeypatch.delenv("WING_PROVIDER_CONFIG", raising=False)
    cfg = resolve(load_config(None))
    assert isinstance(make_provider(cfg), AnthropicProvider)
    cfg2 = resolve(load_config(_write_openai(tmp_path)))
    assert isinstance(make_provider(cfg2), OpenAICompatProvider)
