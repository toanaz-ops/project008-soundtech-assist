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


def test_yaml_file_wins(tmp_path):
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


def test_unknown_key_refused(tmp_path):
    target = tmp_path / "p.yaml"
    target.write_text("provider: anthropic\ntimeout: 30\n", encoding="utf-8")
    try:
        load_config(target)
    except ValueError as exc:
        assert "timeout" in str(exc)
    else:
        raise AssertionError("unknown config key accepted")


def test_missing_explicit_path_raises(tmp_path, monkeypatch):
    monkeypatch.delenv("WING_PROVIDER_CONFIG", raising=False)
    missing = str(tmp_path / "nope.yaml")
    try:
        load_config(missing)
    except ValueError as exc:
        assert "nope.yaml" in str(exc)
    else:
        raise AssertionError("missing named file silently fell through")


def test_env_var_points_at_missing_file_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("WING_PROVIDER_CONFIG", str(tmp_path / "gone.yaml"))
    try:
        load_config(None)
    except ValueError as exc:
        assert "gone.yaml" in str(exc)
    else:
        raise AssertionError("missing env-named file silently fell through")


def test_make_provider_dispatch(tmp_path, monkeypatch):
    monkeypatch.delenv("WING_PROVIDER_CONFIG", raising=False)
    monkeypatch.chdir(tmp_path)
    cfg = resolve(load_config(None))
    assert isinstance(make_provider(cfg), AnthropicProvider)
    cfg2 = resolve(load_config(_write_openai(tmp_path)))
    assert isinstance(make_provider(cfg2), OpenAICompatProvider)


def test_pasted_api_key_reaches_the_adapter(tmp_path):
    """ToanAZ pastes the key straight into provider.yaml; no env var needed."""
    target = tmp_path / "provider.yaml"
    target.write_text(
        "provider: openai-compat\nbase_url: https://api.deepseek.com\n"
        'api_key: "sk-pasted-key"\n', encoding="utf-8"
    )
    provider = make_provider(load_config(target))
    assert isinstance(provider, OpenAICompatProvider)
    assert provider.api_key == "sk-pasted-key"


def test_pasted_key_beats_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "from-env")
    target = tmp_path / "provider.yaml"
    target.write_text('api_key: "sk-pasted"\n', encoding="utf-8")
    provider = make_provider(load_config(target))
    assert provider.api_key == "sk-pasted"


def test_anthropic_adapter_takes_a_pasted_key_too(tmp_path):
    target = tmp_path / "provider.yaml"
    target.write_text('api_key: "sk-ant-pasted"\n', encoding="utf-8")
    provider = make_provider(load_config(target))
    assert isinstance(provider, AnthropicProvider)
    assert provider.api_key == "sk-ant-pasted"
