"""The one doorway every model call goes through.

A Provider turns (system prompt, user prompt, schema) into a validated
JSON dict. The schema dialect is deliberately tiny -- flat objects whose
values are strings or numbers -- because that covers every judgement job
in this project and is what both adapters can honour natively: Anthropic
through `messages.parse`, OpenAI-compatible endpoints through
`response_format={"type": "json_object"}` plus our own validation.

Every failure raises ProviderError. Callers degrade on it; nothing here
returns half an answer.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


class ProviderError(RuntimeError):
    """A model call failed, or its answer never matched the schema."""


def _check(value: object, spec: dict, where: str, problems: list[str]) -> None:
    expected = spec.get("type")
    if expected == "string":
        if not isinstance(value, str):
            problems.append(f"{where} must be a string, got {type(value).__name__}")
    elif expected == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            problems.append(f"{where} must be a number, got {type(value).__name__}")
    else:  # unknown dialect member -- refused loudly, not guessed around
        problems.append(f"{where}: unsupported schema type {expected!r}")


def validate_reply(reply: object, schema: dict) -> list[str]:
    """Problems with a reply against the dialect, empty list when clean."""
    if not isinstance(reply, dict):
        return ["reply is not a JSON object"]
    problems: list[str] = []
    properties = schema.get("properties", {})
    for name in schema.get("required", []):
        if name not in reply:
            problems.append(f"missing required field {name!r}")
    for name, value in reply.items():
        if name in properties:
            _check(value, properties[name], repr(name), problems)
    return problems


@runtime_checkable
class Provider(Protocol):
    def complete_json(self, system: str, user: str, schema: dict) -> dict: ...


def complete_json(
    provider: Provider, system: str, user: str, schema: dict
) -> dict:
    """One retry on a schema-invalid reply; adapter errors are not retried."""
    for attempt in range(2):
        try:
            reply = provider.complete_json(system, user, schema)
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001 - normalise adapter failures
            raise ProviderError(str(exc)) from exc
        problems = validate_reply(reply, schema)
        if not problems:
            return reply
        user = f"{user}\n\nYour previous reply was rejected: {'; '.join(problems)}. Reply again."
    raise ProviderError(f"reply never matched the schema: {'; '.join(problems)}")


# --- appended: config loading and the adapter factory ---
import os
from dataclasses import dataclass, replace
from pathlib import Path

import yaml


@dataclass(frozen=True)
class ProviderConfig:
    name: str = "anthropic"
    model: str = ""
    api_key_env: str = ""
    base_url: str = ""


DEFAULT_CONFIG = ProviderConfig()

_NAME_DEFAULTS = {
    "anthropic": ProviderConfig(
        name="anthropic", model="claude-opus-5", api_key_env="ANTHROPIC_API_KEY"
    ),
    "openai-compat": ProviderConfig(
        name="openai-compat", model="deepseek-chat", api_key_env="DEEPSEEK_API_KEY"
    ),
}

ENV_VAR = "WING_PROVIDER_CONFIG"

_KNOWN_KEYS = {"provider", "model", "api_key_env", "base_url", "name"} | set(
    _NAME_DEFAULTS
)


def _load_named_file(path: Path) -> ProviderConfig:
    if not path.exists():
        raise ValueError(f"{path}: named provider config does not exist.")
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(doc, dict):
        raise ValueError(f"{path}: top level must be a mapping.")
    unknown = set(doc) - _KNOWN_KEYS
    if unknown:
        raise ValueError(
            f"{path}: unknown keys {sorted(unknown)}; known keys are "
            + ", ".join(sorted(_KNOWN_KEYS - {"name", "provider"}))
        )
    name = str(doc.get("name", doc.get("provider", DEFAULT_CONFIG.name)))
    if name not in _NAME_DEFAULTS:
        raise ValueError(
            f"{path}: provider {name!r} is not one of: "
            + ", ".join(sorted(_NAME_DEFAULTS))
        )
    return ProviderConfig(
        name=name,
        model=str(doc.get("model", "")),
        api_key_env=str(doc.get("api_key_env", "")),
        base_url=str(doc.get("base_url", "")),
    )


def load_config(explicit: str | Path | None = None) -> ProviderConfig:
    """explicit beats $WING_PROVIDER_CONFIG beats ./provider.yaml beats default.

    A file named by the argument or $WING_PROVIDER_CONFIG must exist: a
    missing one raises ValueError naming the path. Only when nothing is
    named do we fall through ./provider.yaml to the defaults.
    """
    if explicit is not None:
        return _load_named_file(Path(explicit))
    if os.environ.get(ENV_VAR):
        return _load_named_file(Path(os.environ[ENV_VAR]))
    fallback = Path("provider.yaml")
    if fallback.exists():
        return _load_named_file(fallback)
    return DEFAULT_CONFIG


def resolve(config: ProviderConfig) -> ProviderConfig:
    base = _NAME_DEFAULTS[config.name]
    return replace(
        config,
        model=config.model or base.model,
        api_key_env=config.api_key_env or base.api_key_env,
    )


def make_provider(config: ProviderConfig):
    resolved = resolve(config)
    if resolved.name == "anthropic":
        from wing_parser.classifier.provider_anthropic import AnthropicProvider

        return AnthropicProvider(model=resolved.model, api_key_env=resolved.api_key_env)
    from wing_parser.classifier.provider_openai import OpenAICompatProvider

    return OpenAICompatProvider(
        model=resolved.model,
        api_key_env=resolved.api_key_env,
        base_url=resolved.base_url,
    )
