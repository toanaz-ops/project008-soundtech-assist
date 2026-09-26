"""Spec §7: Try AI reports provider/model/elapsed/proposal or a
classified failure -- the same classifier Settings' Test connection
uses (Task 4). Most tests fake `propose_mapping` directly so no real
xlsx sampling or model call runs; the per-class classification tests
(below the kill-switch section) instead drive the REAL `propose_mapping`
against a real tests/data workbook with a fake PROVIDER whose
`complete_json` raises or misbehaves -- `test_ui_vocabulary_assistant.
py`'s `_RaisingProvider` pattern (lines 296-338 there).

Fix round 1, controller ruling: the kill switch IS honoured
(mapping_try_ai.py's own module docstring has the full reasoning and
supersedes this file's PREVIOUS docstring, which said the opposite).
Every test below that needs a real call explicitly
`monkeypatch.delenv("WING_DISABLE_LLM", raising=False)` -- defensive
here since this file's own `panel` fixture never sets it, but explicit
per the controller's instruction and future-proof against a real
operator's shell having it set.

One departure from the plan's own draft remains: the provider factory
runs on the worker thread, never the GUI thread, so a bad provider.yaml
is reported like any other failure.
"""
from __future__ import annotations

import re
import threading

import pytest

pytest.importorskip("PySide6.QtWidgets")

XLSX = "tests/data/ingest-fixture.xlsx"


class _Proposal:
    sheet = "Rundown"; header_row = 4
    columns = {"id": "B"}; headers = {"performers": "On stage"}
    problems = ()


@pytest.fixture
def panel(qt_app):
    from wing_parser.ui.mapping_try_ai import MappingTryAi
    from wing_parser.ui.workers import CallRunner

    return MappingTryAi(CallRunner(), lambda: object(), lambda: "some.xlsx")


def test_a_successful_try_shows_provider_model_and_the_proposal(panel, monkeypatch, settle):
    from wing_parser.ui import mapping_try_ai

    monkeypatch.setattr(mapping_try_ai.suggest, "propose_mapping",
                        lambda xlsx, provider: _Proposal())
    panel.try_button.click()
    assert settle(lambda: panel.proposal_view.toPlainText() != "")
    assert "Rundown" in panel.proposal_view.toPlainText()
    # Minor: provider/model and elapsed seconds really reach result_label,
    # in the "{provider}, {seconds}s" shape mapping_try_ai.py's own
    # import.try_ai.result text defines -- not just "some non-empty text".
    assert re.fullmatch(r"[\w.\-]+/[\w.\-]*, \d+(\.\d+)?s", panel.result_label.text())


def test_a_401_shows_the_shared_bad_key_message(panel, monkeypatch, settle):
    from wing_parser.ui import mapping_try_ai

    class _Unauthorized(Exception):
        status_code = 401

    def boom(xlsx, provider):
        raise _Unauthorized("nope")

    monkeypatch.setattr(mapping_try_ai.suggest, "propose_mapping", boom)
    panel.try_button.click()
    # Settled on the target substring directly (test_ui_settings.py's own
    # idiom) rather than "!= ''" then a second assert -- ButtonRunner sets
    # the "Asking the model..." running text synchronously on click, so a
    # bare non-empty check would settle on that and never see the failure.
    assert settle(lambda: "rejected" in panel.result_label.text())


def test_no_xlsx_yet_does_nothing(qt_app):
    from wing_parser.ui.mapping_try_ai import MappingTryAi
    from wing_parser.ui.workers import CallRunner

    panel = MappingTryAi(CallRunner(), lambda: object(), lambda: None)
    assert panel._try() is False


# -- Controller requirements: no-key up-front, a bad factory, real timeout --


def test_no_key_shows_the_message_up_front_and_never_calls_propose(panel, monkeypatch):
    from wing_parser.ui import key_status, mapping_try_ai

    monkeypatch.delenv("WING_DISABLE_LLM", raising=False)
    monkeypatch.setattr(key_status, "key_configured", lambda: False)
    reached = []
    monkeypatch.setattr(
        mapping_try_ai.suggest, "propose_mapping",
        lambda xlsx, provider: reached.append(1) or _Proposal(),
    )

    panel.show()   # the re-check trigger, same idiom as key_status.KeyStatusLine
    assert not panel.try_button.isEnabled()
    assert panel.result_label.text() != ""

    assert panel._try() is False   # the disabled-button path, driven directly
    assert reached == []


def test_a_provider_factory_error_reaches_the_panel_without_crashing(panel, monkeypatch, settle):
    """Also this file's OTHER-class coverage (see the per-class section
    below): a factory error never reaches `provider.complete_json`'s own
    `raise ProviderError(...) from exc` wrap, so `classify()` never sees
    a ProviderError in the chain and falls all the way to its own OTHER
    fallback -- `str(exc)` verbatim, which is exactly "bad provider.yaml"
    here."""
    monkeypatch.delenv("WING_DISABLE_LLM", raising=False)

    def bad_factory():
        raise ValueError("bad provider.yaml")

    panel._provider_factory = bad_factory
    started = panel._try()
    assert started
    assert settle(lambda: "bad provider.yaml" in panel.result_label.text())


def test_a_real_timeout_is_reported_through_the_real_call_runner(panel, monkeypatch, settle):
    from wing_parser.ui import mapping_try_ai

    monkeypatch.delenv("WING_DISABLE_LLM", raising=False)
    gate = threading.Event()

    def hang(xlsx, provider):
        gate.wait(timeout=5.0)
        return _Proposal()

    monkeypatch.setattr(mapping_try_ai.suggest, "propose_mapping", hang)
    try:
        started = panel._call.run(
            "proposal", mapping_try_ai._call_provider, panel._provider_factory,
            "some.xlsx", on_success=lambda r: None, timeout=0)
        assert started
        assert settle(lambda: "0 s" in panel.result_label.text())
    finally:
        gate.set()
        assert settle(lambda: not panel._runner.busy)


def test_cancel_through_the_real_button_runner_settles_the_call(panel, monkeypatch, settle):
    from wing_parser.ui import mapping_try_ai

    monkeypatch.delenv("WING_DISABLE_LLM", raising=False)
    gate = threading.Event()

    def hang(xlsx, provider):
        gate.wait(timeout=5.0)
        return _Proposal()

    monkeypatch.setattr(mapping_try_ai.suggest, "propose_mapping", hang)
    try:
        started = panel._try()
        assert started
        assert not panel.try_button.isEnabled()   # ButtonRunner's own running state
        panel.cancel_button.click()
        assert settle(lambda: panel.result_label.text() == "Cancelled.")
        assert not panel._runner.busy
        assert panel.try_button.isEnabled()
    finally:
        gate.set()
        assert settle(lambda: not panel._runner.busy)


def test_a_recheck_does_not_re_enable_while_a_call_is_running(panel, monkeypatch, settle):
    """Copies test_ui_vocabulary_assistant.py:255-290's own pattern for
    MappingTryAi: a showEvent-driven recheck (the window reopening, or a
    tab switch away and back mid-call) must never undo ButtonRunner's
    own disabled-while-running state."""
    from wing_parser.ui import key_status, mapping_try_ai

    monkeypatch.delenv("WING_DISABLE_LLM", raising=False)
    monkeypatch.setattr(key_status, "key_configured", lambda: True)
    gate = threading.Event()

    def hang(xlsx, provider):
        gate.wait(timeout=5.0)
        return _Proposal()

    monkeypatch.setattr(mapping_try_ai.suggest, "propose_mapping", hang)
    try:
        started = panel._try()
        assert started
        running_text = panel.result_label.text()
        assert running_text != ""

        panel.show()   # VocabularyWindow reopening, or a tab switch back
        assert not panel.try_button.isEnabled()
        assert panel.result_label.text() == running_text
    finally:
        gate.set()
        assert settle(lambda: not panel._runner.busy)


# -- Fix round 1, controller ruling: the kill switch is honoured -----------


def test_kill_switch_on_shows_the_message_and_never_calls_the_factory(panel, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    reached = []
    panel._provider_factory = lambda: reached.append(1) or object()

    assert panel._try() is False
    assert reached == []
    assert "WING_DISABLE_LLM" in panel.result_label.text()


def test_kill_switch_on_greys_the_button_when_shown(panel, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    panel.show()
    assert not panel.try_button.isEnabled()
    assert "WING_DISABLE_LLM" in panel.result_label.text()


# -- Fix round 1, item 3: one test per provider_errors class, driven -------
# through the REAL suggest.propose_mapping (real xlsx sampling, real
# provider.complete_json retry/wrap logic) with a fake PROVIDER that
# misbehaves -- test_ui_vocabulary_assistant.py's _RaisingProvider idiom.


class _RaisingProvider:
    def __init__(self, exc):
        self._exc = exc

    def complete_json(self, system, user, schema):
        raise self._exc


class _NeverValidProvider:
    """Every reply is missing every required field -- provider.py's own
    complete_json retries once, then raises ProviderError("reply never
    matched the schema...") with no further cause: the real "malformed
    reply" shape, not a monkeypatched stand-in for it."""

    def complete_json(self, system, user, schema):
        return {}


class _StatusError(Exception):
    def __init__(self, status_code, message="boom"):
        super().__init__(message)
        self.status_code = status_code


def _try_with(panel, monkeypatch, provider):
    monkeypatch.delenv("WING_DISABLE_LLM", raising=False)
    panel._provider_factory = lambda: provider
    panel._xlsx_provider = lambda: XLSX
    assert panel._try() is True


def test_a_401_status_is_classified_as_the_rejected_key_message(panel, monkeypatch, settle):
    _try_with(panel, monkeypatch, _RaisingProvider(_StatusError(401)))
    assert settle(lambda: "rejected" in panel.result_label.text())


def test_a_429_status_is_classified_as_the_quota_message(panel, monkeypatch, settle):
    _try_with(panel, monkeypatch, _RaisingProvider(_StatusError(429)))
    assert settle(lambda: "quota" in panel.result_label.text())


def test_a_connection_error_is_classified_as_the_no_network_message(panel, monkeypatch, settle):
    _try_with(panel, monkeypatch, _RaisingProvider(ConnectionError("no route to host")))
    assert settle(lambda: "network" in panel.result_label.text())


def test_a_missing_sdk_message_is_classified_as_sdk_missing(panel, monkeypatch, settle):
    exc = RuntimeError(
        "talking to Claude needs the anthropic package. Install it with:  pip install -e .[llm]"
    )
    _try_with(panel, monkeypatch, _RaisingProvider(exc))
    assert settle(lambda: "SDK" in panel.result_label.text())


def test_a_no_api_key_message_is_classified_as_no_key(panel, monkeypatch, settle):
    exc = RuntimeError("no API key: paste api_key: into provider.yaml or set 'ANTHROPIC_API_KEY'")
    _try_with(panel, monkeypatch, _RaisingProvider(exc))
    assert settle(lambda: "No API key" in panel.result_label.text())


def test_a_reply_that_never_matches_the_schema_is_classified_as_bad_reply(panel, monkeypatch, settle):
    _try_with(panel, monkeypatch, _NeverValidProvider())
    assert settle(lambda: "reply" in panel.result_label.text())


def test_an_unmatched_exception_still_falls_back_to_bad_reply_not_other(panel, monkeypatch, settle):
    """NOT the OTHER class (that's covered by
    test_a_provider_factory_error_reaches_the_panel_without_crashing,
    above): `provider.py`'s own `complete_json` wraps ANY adapter
    exception into a `ProviderError` before `_failed` ever sees it
    (`raise ProviderError(str(exc)) from exc`), and `classify()`'s own
    fallback for "saw a ProviderError but no pattern matched" is
    BAD_REPLY, never OTHER -- OTHER is reserved for a failure that
    never went through `complete_json` at all."""
    _try_with(panel, monkeypatch, _RaisingProvider(RuntimeError("weird failure")))
    assert settle(lambda: "reply" in panel.result_label.text())
