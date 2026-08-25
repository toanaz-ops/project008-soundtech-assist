"""OpenAI-compatible endpoint as a Provider -- DeepSeek's doorway.

DeepSeek documents an OpenAI-SDK-shaped API (base_url api.deepseek.com)
whose chat-completions accept response_format {"type": "json_object"}.
That mode enforces valid JSON but not a shape, so the schema rides in the
prompt as an example and `complete_json` in provider.py does the
enforcement. Docs re-checked 2026-08-24.
"""

from __future__ import annotations

import json
import os

from wing_parser.classifier.provider import ProviderError

EXTRA_HINT = (
    "talking to an OpenAI-compatible model needs the openai package, "
    "which is not installed. Install it with:  pip install -e .[llm-openai]"
)


class MissingExtra(RuntimeError):
    pass


def _example(schema: dict) -> str:
    parts = ", ".join(
        f'"{name}": <{spec.get("type", "string")}>'
        for name, spec in schema.get("properties", {}).items()
    )
    return "{" + parts + "}"


class OpenAICompatProvider:
    """`base_url` is what makes this cover DeepSeek, OpenAI, or a local box."""

    def __init__(self, model: str, api_key_env: str, base_url: str = "",
                 api_key: str = ""):
        self.model = model
        self.api_key_env = api_key_env
        self.base_url = base_url
        # A key pasted into provider.yaml beats the env var: the file was
        # edited deliberately, most recently, by the person running this.
        self.api_key = api_key

    def _client(self):
        key = self.api_key or os.environ.get(self.api_key_env, "")
        if not key:
            raise ProviderError(
                f"no API key: paste api_key: into provider.yaml or set "
                f"environment variable {self.api_key_env!r}"
            )
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise MissingExtra(EXTRA_HINT) from exc
        kwargs = {"api_key": key}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        return OpenAI(**kwargs)

    def complete_json(self, system: str, user: str, schema: dict) -> dict:
        client = self._client()
        system_prompt = (
            f"{system}\n\nReply with json exactly in this shape:\n{_example(schema)}"
        )
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        try:
            return json.loads(content)
        except (TypeError, ValueError) as exc:
            raise ProviderError(
                f"model replied with unparseable content: {exc}"
            ) from exc
