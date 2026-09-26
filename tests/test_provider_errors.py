"""Spec §7: one shared failure vocabulary for Settings' Test connection,
the Mapping step's Try AI, and the Vocabulary window's assistant.

Every exception here is a plain fake -- never a real anthropic/openai
import -- so this module (and this test) work in a build with neither
SDK installed. `status_code` duck-typing mirrors both SDKs' own
`APIStatusError` shape (checked by opening provider_anthropic.py /
provider_openai.py, listed as Task 4's own file reads above).
"""
from __future__ import annotations

from wing_parser.classifier import provider_errors as pe
from wing_parser.classifier.provider import ProviderError


class _FakeStatusError(Exception):
    def __init__(self, status_code, message="boom"):
        super().__init__(message)
        self.status_code = status_code


def test_401_and_403_classify_as_bad_key():
    assert pe.classify(_FakeStatusError(401))[0] == pe.BAD_KEY
    assert pe.classify(_FakeStatusError(403))[0] == pe.BAD_KEY


def test_402_and_429_classify_as_quota():
    assert pe.classify(_FakeStatusError(402))[0] == pe.QUOTA
    assert pe.classify(_FakeStatusError(429))[0] == pe.QUOTA


def test_a_connection_error_classifies_as_no_network():
    assert pe.classify(ConnectionError("no route to host"))[0] == pe.NO_NETWORK


class _FakeAPIConnectionError(Exception):
    """Stands in for anthropic.APIConnectionError / openai.APIConnectionError
    -- both name-match "Connection", neither is a builtin ConnectionError."""


def test_an_sdk_named_connection_error_also_classifies_as_no_network():
    assert pe.classify(_FakeAPIConnectionError("unreachable"))[0] == pe.NO_NETWORK


def test_an_import_error_classifies_as_sdk_missing():
    assert pe.classify(ImportError("no module named anthropic"))[0] == pe.SDK_MISSING


def test_the_lazy_import_runtime_error_text_also_classifies_as_sdk_missing():
    """provider_anthropic.py/provider_openai.py wrap a missing SDK's
    ImportError in RuntimeError/MissingExtra carrying this exact phrase
    (EXTRA_HINT in both modules) -- classify() must recognise it even
    though it is no longer an ImportError by the time it gets here."""
    exc = RuntimeError("talking to Claude needs the anthropic package. "
                       "Install it with:  pip install -e .[llm]")
    assert pe.classify(exc)[0] == pe.SDK_MISSING


def test_a_provider_error_classifies_as_bad_reply():
    assert pe.classify(ProviderError("reply never matched the schema: x"))[0] == pe.BAD_REPLY


def test_anything_else_classifies_as_other_and_keeps_the_original_text():
    code, text = pe.classify(ValueError("something unexpected"))
    assert code == pe.OTHER
    assert "something unexpected" in text


def test_every_code_has_non_empty_human_text():
    for exc in (_FakeStatusError(401), _FakeStatusError(429), ConnectionError("x"),
               ImportError("x"), ProviderError("x"), ValueError("x")):
        code, text = pe.classify(exc)
        assert text.strip() != ""
