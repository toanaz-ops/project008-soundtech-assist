"""Anthropic as a Provider -- the shape llm.py used inline, extracted.

The schema dialect is flat string/number fields, which maps one-to-one
onto a dynamically built pydantic model for messages.parse. max_tokens
keeps the 4096 headroom llm.py:84-91 measured: thinking counts against
it and a truncated reply dies as an exception downstream.
"""

from __future__ import annotations

import os

EXTRA_HINT = (
    "talking to Claude needs the anthropic package. "
    "Install it with:  pip install -e .[llm]"
)

_TYPE_MAP = {"string": (str, ...), "number": (float, ...)}


class AnthropicProvider:
    def __init__(self, model: str, api_key_env: str = "ANTHROPIC_API_KEY"):
        self.model = model
        self.api_key_env = api_key_env

    def _parse_model(self, schema: dict):
        import pydantic

        fields = {
            name: _TYPE_MAP[spec["type"]]
            for name, spec in schema["properties"].items()
        }
        return pydantic.create_model("Reply", **fields)

    def complete_json(self, system: str, user: str, schema: dict) -> dict:
        key = os.environ.get(self.api_key_env, "")
        if not key:
            raise RuntimeError(f"{self.api_key_env!r} is not set")
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError(EXTRA_HINT) from exc
        client = anthropic.Anthropic(api_key=key)
        response = client.messages.parse(
            model=self.model,
            max_tokens=4096,
            messages=[{"role": "user", "content": f"{system}\n\n{user}"}],
            output_format=self._parse_model(schema),
        )
        guess = response.parsed_output
        return {
            name: getattr(guess, name) for name in schema.get("properties", {})
        }
