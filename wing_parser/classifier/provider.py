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
