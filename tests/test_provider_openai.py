"""Request shaping for the OpenAI-compatible adapter, tested through fakes.

No test here touches the network: the openai module is faked wholesale,
because CI does not install it (global constraint: offline first).
"""
import json
import sys
import types

import pytest

from wing_parser.classifier.provider import ProviderError
from wing_parser.classifier.provider_openai import MissingExtra, OpenAICompatProvider

SCHEMA = {
    "type": "object",
    "properties": {"kind": {"type": "string"}},
    "required": ["kind"],
}


class FakeCompletions:
    def __init__(self, payload):
        self.payload = payload
        self.last_kwargs = None

    def create(self, **kwargs):
        self.last_kwargs = kwargs
        content = json.dumps(self.payload)
        message = types.SimpleNamespace(content=content)
        choice = types.SimpleNamespace(message=message)
        return types.SimpleNamespace(choices=[choice])


@pytest.fixture()
def fake_sdk(monkeypatch):
    """Install a stand-in `openai` module before the adapter imports it."""
    completions = FakeCompletions({"kind": "speech.mc"})
    mod = types.ModuleType("openai")

    class FakeOpenAI:
        def __init__(self, api_key=None, base_url=None):
            self.api_key = api_key
            self.base_url = base_url
            self.chat = types.SimpleNamespace(completions=completions)

    mod.OpenAI = FakeOpenAI
    monkeypatch.setitem(sys.modules, "openai", mod)
    return completions


def test_request_shape(fake_sdk, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_KEY", "k-test")
    provider = OpenAICompatProvider(
        model="deepseek-chat", api_key_env="DEEPSEEK_KEY",
        base_url="https://api.deepseek.com",
    )
    result = provider.complete_json("be terse", "name a channel", SCHEMA)
    assert result == {"kind": "speech.mc"}
    kwargs = fake_sdk.last_kwargs
    # DeepSeek's json_object mode refuses a prompt without the word json
    # and an example -- docs verified 2026-08-24 -- so both must be there.
    assert kwargs["response_format"] == {"type": "json_object"}
    assert "json" in kwargs["messages"][0]["content"].lower()
    assert '"kind"' in kwargs["messages"][0]["content"]
    assert kwargs["model"] == "deepseek-chat"


def test_invalid_json_content_raises_provider_error(fake_sdk, monkeypatch):
    monkeypatch.setenv("DEEPSEEK_KEY", "k-test")

    def create(**kwargs):
        return types.SimpleNamespace(
            choices=[
                types.SimpleNamespace(
                    message=types.SimpleNamespace(content="not json at all")
                )
            ]
        )

    fake_sdk.create = create
    provider = OpenAICompatProvider(
        model="m", api_key_env="DEEPSEEK_KEY", base_url=""
    )
    with pytest.raises(ProviderError):
        provider.complete_json("s", "u", SCHEMA)


def test_missing_sdk_raises_named_extra(monkeypatch):
    monkeypatch.setitem(sys.modules, "openai", None)  # import guard trips
    monkeypatch.delenv("NOPE_KEY", raising=False)
    provider = OpenAICompatProvider(model="m", api_key_env="NOPE_KEY")
    with pytest.raises((MissingExtra, ProviderError)):
        provider.complete_json("s", "u", SCHEMA)
