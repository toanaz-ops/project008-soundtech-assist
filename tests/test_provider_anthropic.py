"""AnthropicAdapter request shaping through a fake SDK (offline)."""
import sys
import types

import pytest

from wing_parser.classifier.provider_anthropic import AnthropicProvider

SCHEMA = {
    "type": "object",
    "properties": {"kind": {"type": "string"}, "confidence": {"type": "number"}},
    "required": ["kind"],
}


@pytest.fixture()
def fake_sdk(monkeypatch):
    captured = {}

    def _parse(**kwargs):
        captured.update(kwargs)
        guess = types.SimpleNamespace(kind="utility.playback", confidence=0.8)
        return types.SimpleNamespace(parsed_output=guess)

    mod = types.ModuleType("anthropic")

    class FakeMessages:
        parse = staticmethod(_parse)

    class FakeAnthropic:
        def __init__(self, **kwargs):
            self.messages = FakeMessages()

    mod.Anthropic = FakeAnthropic
    monkeypatch.setitem(sys.modules, "anthropic", mod)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k-test")
    return captured


def test_parse_call_carries_flat_model(fake_sdk):
    provider = AnthropicProvider(model="claude-opus-5")
    result = provider.complete_json("sys", "user", SCHEMA)
    assert result == {"kind": "utility.playback", "confidence": 0.8}
    output_format = fake_sdk["output_format"]
    fields = output_format.model_fields
    assert set(fields) == {"kind", "confidence"}
    assert fake_sdk["max_tokens"] >= 4096  # thinking headroom, per llm.py:84-91
