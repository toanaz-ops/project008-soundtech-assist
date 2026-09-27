"""Unit tests for the provider protocol and the reply validator."""
import pytest

from wing_parser.classifier.provider import (
    ProviderError,
    complete_json,
    validate_reply,
)

SCHEMA = {
    "type": "object",
    "properties": {"kind": {"type": "string"}, "confidence": {"type": "number"}},
    "required": ["kind"],
}


class FakeProvider:
    """Returns queued replies, records prompts."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []

    def complete_json(self, system, user, schema):
        self.calls.append((system, user, schema))
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply


def test_valid_reply_has_no_problems():
    assert validate_reply({"kind": "speech.vocal"}, SCHEMA) == []


def test_missing_required_field_is_a_problem():
    problems = validate_reply({"confidence": 0.9}, SCHEMA)
    assert problems == ["missing required field 'kind'"]


def test_wrong_type_and_extra_keys():
    problems = validate_reply({"kind": 7}, SCHEMA)
    assert any("kind" in p for p in problems)


def test_non_mapping_reply_is_one_problem():
    assert validate_reply("nope", SCHEMA) == ["reply is not a JSON object"]


def test_retry_once_then_raise():
    fake = FakeProvider([{"confidence": 0.9}, {"kind": "instrument.bass"}])
    result = complete_json(fake, "sys", "user", SCHEMA)
    assert result == {"kind": "instrument.bass"}
    assert len(fake.calls) == 2


def test_two_bad_replies_raise_provider_error():
    fake = FakeProvider([{}, {}])
    with pytest.raises(ProviderError):
        complete_json(fake, "sys", "user", SCHEMA)
    assert len(fake.calls) == 2


def test_adapter_exception_is_not_retried():
    fake = FakeProvider([ProviderError("dead uplink")])
    with pytest.raises(ProviderError):
        complete_json(fake, "sys", "user", SCHEMA)
    assert len(fake.calls) == 1


# -- fix round 1 (c): Settings' Test connection must use classify() in
# production, not only when a test injects a raising probe. `ping()`
# catches everything and used to return the raw `str(exc)` -- the ONE
# production caller (`SettingsDialog._probe = probe or provider.ping`)
# never raises, so `provider_errors.classify` was unreachable through it.
# `ping()` now sources its failure message from the same classifier,
# keeping its (ok, message) contract unchanged for that caller. --------


def test_ping_failure_message_comes_from_classify(monkeypatch):
    from wing_parser.classifier import provider, provider_errors

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # No package import needed to reach this: AnthropicProvider checks
    # for a usable key before ever touching the `anthropic` SDK.
    ok, message = provider.ping(provider.ProviderConfig())
    assert ok is False
    assert message == provider_errors._MESSAGES[provider_errors.NO_KEY]


def test_ping_still_reports_success_as_before(monkeypatch):
    from wing_parser.classifier import provider

    class _FakeProvider:
        def complete_json(self, system, user, schema):
            return {"ok": "yes"}

    monkeypatch.setattr(provider, "make_provider", lambda cfg: _FakeProvider())
    ok, message = provider.ping(provider.ProviderConfig(name="anthropic"))
    assert ok is True
    assert "anthropic" in message
