"""Config search order, defaults, and factory dispatch."""
from pathlib import Path

from wing_parser.classifier.provider import (
    DEFAULT_CONFIG,
    ENV_VAR,
    has_usable_key,
    is_placeholder_key,
    load_config,
    make_provider,
    resolve,
    resolve_config,
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


# -- placeholder keys are not keys (docs/tech-debt.md#d-30) --------------
#
# The repo ships fill-me-in markers in two places: `provider.yaml` at the
# root (`api_key: PASTE_KEY_DEEPSEEK_VAO_DAY`) and
# `docs/user-manual/04-cau-hinh-model.md` (`api_key: sk-xxxxxxxx...`).
# Both are non-empty, so a bare truthiness test calls them configured and
# the operator only learns otherwise when the first model call fails.


def test_the_repos_own_provider_yaml_placeholder_is_not_a_key(tmp_path,
                                                              monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    target = tmp_path / "provider.yaml"
    target.write_text(
        "provider: openai-compat\napi_key: PASTE_KEY_DEEPSEEK_VAO_DAY\n",
        encoding="utf-8",
    )
    assert is_placeholder_key("PASTE_KEY_DEEPSEEK_VAO_DAY") is True
    assert has_usable_key(load_config(target)) is False


def test_the_user_manuals_placeholder_is_not_a_key(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    target = tmp_path / "provider.yaml"
    target.write_text(
        "api_key: sk-xxxxxxxxxxxxxxxxxxxxxxxx\n", encoding="utf-8"
    )
    assert has_usable_key(load_config(target)) is False


def test_a_real_looking_pasted_key_is_usable(tmp_path):
    target = tmp_path / "provider.yaml"
    target.write_text('api_key: "sk-9f3ad2e1"\n', encoding="utf-8")
    assert is_placeholder_key("sk-9f3ad2e1") is False
    assert has_usable_key(load_config(target)) is True


def test_an_env_key_rescues_a_placeholder_file(tmp_path, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-from-env")
    target = tmp_path / "provider.yaml"
    target.write_text(
        "provider: openai-compat\napi_key: PASTE_KEY_DEEPSEEK_VAO_DAY\n",
        encoding="utf-8",
    )
    assert has_usable_key(load_config(target)) is True


def test_no_key_anywhere_is_not_usable(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert has_usable_key(DEFAULT_CONFIG) is False


# -- one resolver for the hint and the call (docs/tech-debt.md#d-30) -----
#
# `resolve_config` is what both the import page's key line and its model
# calls read. A second, nearly-identical chain is how the line came to say
# "no model key configured" about a machine whose next model call would
# have succeeded, so these pin the order rather than the outcome.


def test_a_keyless_saved_config_falls_through_to_the_cwd_file(tmp_path,
                                                              monkeypatch):
    """Settings saved with an empty key field is a half-filled form.

    It must not stop the search: `load_config(None)` would have found the
    ./provider.yaml key, and a hint that disagrees with the call is worse
    than no hint.
    """
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "provider.yaml").write_text(
        'provider: openai-compat\napi_key: ""\napi_key_env: ""\n',
        encoding="utf-8",
    )
    (tmp_path / "provider.yaml").write_text(
        'provider: openai-compat\napi_key: "sk-real-9f3a"\n', encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)

    assert resolve_config(knowledge).api_key == "sk-real-9f3a"
    assert has_usable_key(resolve_config(knowledge)) is True


def test_a_placeholder_saved_config_falls_through_too(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "provider.yaml").write_text(
        "provider: openai-compat\napi_key: PASTE_KEY_DEEPSEEK_VAO_DAY\n",
        encoding="utf-8",
    )
    (tmp_path / "provider.yaml").write_text(
        'provider: openai-compat\napi_key: "sk-real-9f3a"\n', encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)

    assert resolve_config(knowledge).api_key == "sk-real-9f3a"


def test_a_usable_saved_key_wins_over_the_cwd_file(tmp_path, monkeypatch):
    monkeypatch.delenv(ENV_VAR, raising=False)
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "provider.yaml").write_text(
        'provider: openai-compat\napi_key: "sk-saved"\n', encoding="utf-8"
    )
    (tmp_path / "provider.yaml").write_text(
        'provider: openai-compat\napi_key: "sk-cwd"\n', encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)

    assert resolve_config(knowledge).api_key == "sk-saved"


def test_the_pin_beats_the_saved_copy(tmp_path, monkeypatch):
    """$WING_PROVIDER_CONFIG names a file on purpose, so it is not stepped over."""
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "provider.yaml").write_text(
        'provider: openai-compat\napi_key: "sk-saved"\n', encoding="utf-8"
    )
    pinned = tmp_path / "pinned.yaml"
    pinned.write_text(
        'provider: openai-compat\napi_key: "sk-pinned"\n', encoding="utf-8"
    )
    monkeypatch.setenv(ENV_VAR, str(pinned))

    assert resolve_config(knowledge).api_key == "sk-pinned"


def test_resolve_config_without_a_knowledge_dir_is_load_config(tmp_path,
                                                               monkeypatch):
    """No knowledge dir named -> byte-for-byte the old chain."""
    monkeypatch.delenv(ENV_VAR, raising=False)
    (tmp_path / "provider.yaml").write_text(
        'provider: openai-compat\napi_key: "sk-cwd"\n', encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)

    assert resolve_config(None) == load_config(None)
