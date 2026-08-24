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
