"""Spec §7: Try AI reports provider/model/elapsed/proposal or a
classified failure -- the same classifier Settings' Test connection
uses (Task 4). A fake provider stands in for the model; propose_mapping
is monkeypatched directly so no real xlsx sampling or model call runs.

Two deliberate departures from the plan's own draft, both load-bearing
and explained in mapping_try_ai.py's module docstring:

- WING_DISABLE_LLM (the kill switch) is never checked here, the same
  way Settings' own "Test connection" never checks it -- both are an
  explicit, one-off diagnostic action, not the wizard's silent
  auto-assist the switch exists to silence. `page`'s own fixture in
  test_ui_import_page.py sets this switch for every wizard test, and
  the Try AI panel must still reach the fake provider under it.
- The provider factory runs on the worker thread, never the GUI
  thread, so a bad provider.yaml is reported like any other failure.
"""
from __future__ import annotations

import threading

import pytest

pytest.importorskip("PySide6.QtWidgets")


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
    def bad_factory():
        raise ValueError("bad provider.yaml")

    panel._provider_factory = bad_factory
    started = panel._try()
    assert started
    assert settle(lambda: "bad provider.yaml" in panel.result_label.text())


def test_a_real_timeout_is_reported_through_the_real_call_runner(panel, monkeypatch, settle):
    from wing_parser.ui import mapping_try_ai

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
