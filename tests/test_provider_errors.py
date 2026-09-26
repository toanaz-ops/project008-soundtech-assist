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


def test_a_missing_key_message_classifies_as_no_key():
    """Both adapters' own "no API key" wording (provider_anthropic.py:45-48,
    provider_openai.py:52-55) -- distinct from a key the provider itself
    rejected (BAD_KEY, an HTTP 401/403 round trip actually happened)."""
    exc = RuntimeError("no API key: paste api_key: into provider.yaml or set 'ANTHROPIC_API_KEY'")
    assert pe.classify(exc)[0] == pe.NO_KEY


# -- fix round 1 (a): classify must walk __cause__/__context__ -- provider.py's
# complete_json wraps every raw adapter exception into a bare
# ProviderError(str(exc)) from exc, discarding the original's status_code
# and type at the OUTER level while preserving it as __cause__ -----------


class _WrappedCauseError(Exception):
    """Simulates what a caller of classify() actually receives: the
    OUTER exception is a bare ProviderError with no status_code of its
    own; the real, classifiable exception is its __cause__."""


def _wrap(inner: Exception) -> ProviderError:
    try:
        raise inner
    except Exception as exc:  # noqa: BLE001 - mirrors provider.py's own wrap
        try:
            raise ProviderError(str(exc)) from exc
        except ProviderError as wrapped:
            return wrapped


def test_a_wrapped_401_is_found_through_the_cause_chain():
    assert pe.classify(_wrap(_FakeStatusError(401)))[0] == pe.BAD_KEY


def test_a_wrapped_429_is_found_through_the_cause_chain():
    assert pe.classify(_wrap(_FakeStatusError(429)))[0] == pe.QUOTA


def test_a_wrapped_connection_error_is_found_through_the_cause_chain():
    assert pe.classify(_wrap(_FakeAPIConnectionError("unreachable")))[0] == pe.NO_NETWORK


def test_a_wrapped_import_error_is_found_through_the_cause_chain():
    assert pe.classify(_wrap(ImportError("no module named anthropic")))[0] == pe.SDK_MISSING


def test_a_bare_provider_error_with_no_classifiable_cause_is_bad_reply():
    """The fallback: only when nothing in the chain matches a specific
    class AND something in the chain is a ProviderError."""
    assert pe.classify(ProviderError("reply never matched the schema: x"))[0] == pe.BAD_REPLY


def test_a_cycle_in_the_cause_chain_does_not_hang():
    a = Exception("a")
    b = Exception("b")
    a.__cause__ = b
    b.__cause__ = a  # pathological, must never happen from a real raise, but must not loop
    code, message = pe.classify(a)
    assert code == pe.OTHER  # neither carries anything classifiable
    assert message.strip() != ""


# -- fix round 1 (d): the exception must go through the REAL wrap
# (provider.py's complete_json / the adapters' own except-and-reraise),
# never fed into classify() directly -- this is the refutation of the
# concern task 6's own report raised ----------------------------------


class _FakeAdapter:
    def __init__(self, exc: Exception) -> None:
        self._exc = exc

    def complete_json(self, system, user, schema):
        raise self._exc


_PING_LIKE_SCHEMA = {"type": "object", "properties": {"ok": {"type": "string"}}, "required": ["ok"]}


def _through_the_real_wrap(exc: Exception) -> Exception:
    """What `_failed`/`on_error` actually receives on every real call
    site (llm.py, guess.py, suggest.py, vocab_changes.py): the fake
    adapter's exception after `provider.py`'s own `complete_json` has
    wrapped it -- never `classify()` applied to the raw fake."""
    from wing_parser.classifier.provider import complete_json

    try:
        complete_json(_FakeAdapter(exc), "sys", "user", _PING_LIKE_SCHEMA)
    except Exception as wrapped:  # noqa: BLE001 - capturing it IS the point
        return wrapped
    raise AssertionError("expected the fake adapter's exception to propagate")


def test_a_401_through_the_real_wrap_classifies_as_bad_key():
    assert pe.classify(_through_the_real_wrap(_FakeStatusError(401)))[0] == pe.BAD_KEY


def test_a_429_through_the_real_wrap_classifies_as_quota():
    assert pe.classify(_through_the_real_wrap(_FakeStatusError(429)))[0] == pe.QUOTA


def test_an_sdk_connection_error_through_the_real_wrap_classifies_as_no_network():
    assert pe.classify(_through_the_real_wrap(_FakeAPIConnectionError("gone")))[0] == pe.NO_NETWORK


def test_an_import_error_through_the_real_wrap_classifies_as_sdk_missing():
    assert pe.classify(_through_the_real_wrap(ImportError("no module named anthropic")))[0] == pe.SDK_MISSING


def test_a_no_api_key_error_through_the_real_wrap_classifies_as_no_key():
    exc = RuntimeError("no API key: paste api_key: into provider.yaml or set 'X'")
    assert pe.classify(_through_the_real_wrap(exc))[0] == pe.NO_KEY


class _BadReplyAdapter:
    """Never raises -- always replies with a schema-invalid object, so
    complete_json's own retry loop exhausts and raises a ProviderError
    that wraps nothing else (no useful cause) -- the BAD_REPLY fallback,
    reached through the real wrap rather than constructed by hand."""

    def complete_json(self, system, user, schema):
        return {}


def test_a_schema_failure_through_the_real_wrap_classifies_as_bad_reply():
    from wing_parser.classifier.provider import complete_json

    try:
        complete_json(_BadReplyAdapter(), "sys", "user", _PING_LIKE_SCHEMA)
    except Exception as exc:  # noqa: BLE001 - capturing it IS the point
        assert pe.classify(exc)[0] == pe.BAD_REPLY
    else:
        raise AssertionError("expected a ProviderError")
