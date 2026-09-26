"""Spec §8.2: propose -> validate -> tick -> Apply, never a write before
Apply (F11). A fake Provider stands in for the model -- no network, no
key, ever."""
from __future__ import annotations

import json

import pytest

pytest.importorskip("PySide6.QtWidgets")


class _FakeProvider:
    def __init__(self, reply):
        self._reply = reply

    def complete_json(self, system, user, schema):
        return self._reply


def _mixed_reply():
    return {"changes_json": json.dumps([
        {"op": "add", "target": "term", "key": "cajon", "before": None,
         "after": {"kinds": ["drums.pad"]}, "reason": "a hand drum"},
        {"op": "add", "target": "term", "key": "x", "before": None,
         "after": {"kinds": ["nonsense.kind"]}, "reason": "bad kind"},
    ])}


@pytest.fixture
def assistant(qt_app, tmp_path):
    from wing_parser.classifier import vocabulary as vocab_module
    from wing_parser.ui.vocabulary_assistant import VocabularyAssistant

    vocabulary = vocab_module.Vocabulary.load(tmp_path)
    applied = []
    widget = VocabularyAssistant(
        vocabulary, lambda: _FakeProvider(_mixed_reply()), lambda: applied.append(True))
    # I0's real-environment key check has its own dedicated tests below;
    # every other test here is about propose/validate/apply and must not
    # depend on whether THIS machine happens to export a real API key.
    widget._key_ok = True
    widget.propose_button.setEnabled(True)
    widget.instruction_edit.setEnabled(True)
    widget._tmp_path = tmp_path  # test-only stash, not a public seam
    widget._applied_log = applied
    return widget


def _classifier_path(directory):
    return directory / "classifier.yaml"


def test_a_mixed_valid_invalid_proposal_only_lets_the_valid_one_be_ticked(assistant):
    assistant._call.run = lambda kind, fn, *a, on_success: on_success(fn(*a)) or True
    assistant._propose()
    assert assistant.table.rowCount() == 2
    assert assistant._checks[0].isEnabled() and assistant._checks[0].isChecked()
    assert not assistant._checks[1].isEnabled()


def test_apply_writes_only_the_ticked_valid_change_and_nothing_before(assistant):
    from wing_parser.classifier import vocabulary as vocab_module

    classifier_path = _classifier_path(assistant._tmp_path)
    assert not classifier_path.exists()   # nothing on disk at all yet

    assistant._call.run = lambda kind, fn, *a, on_success: on_success(fn(*a)) or True
    assistant._propose()
    # Byte-identical, not just "the loaded keys look the same" (fix round
    # 1 minor): Propose must not have touched the file at all.
    assert not classifier_path.exists()

    assistant._checks[1].setEnabled(True)   # tampering with a disabled box, proving it's ignored anyway
    assistant._checks[1].setChecked(True)
    assistant._apply()

    after = vocab_module.Vocabulary.load(assistant._tmp_path).terms()
    keys = {t.key: t for t in after}
    assert keys["cajon"].origin == "ai-approved"
    assert "x" not in keys   # the invalid one, even force-ticked, is never applied
    assert assistant._applied_log == [True]


def test_propose_for_fragments_is_the_terms_steps_entry_point(assistant):
    assistant._call.run = lambda kind, fn, *a, on_success: on_success(fn(*a)) or True
    assistant.propose_for_fragments(("tốp múa",))
    assert assistant.table.rowCount() == 2   # the fake provider always returns the same fixed reply


# -- fix round 1 minors: clear-after-Apply, tally, no re-write on a second
# click with nothing left ticked -------------------------------------------


def test_apply_reports_the_tally_clears_the_table_and_a_second_click_is_a_no_op(assistant):
    assistant._call.run = lambda kind, fn, *a, on_success: on_success(fn(*a)) or True
    assistant._propose()
    assistant._apply()

    assert "1" in assistant.status_label.text()   # 1 applied
    assert assistant.table.rowCount() == 0
    assert assistant._checks == [] and assistant._validated == []

    logged = list(assistant._applied_log)
    assistant._apply()   # nothing ticked (nothing left) -- must not re-write or re-notify
    assert assistant._applied_log == logged


# -- fix round 1, I3: the Before column is the real stored entry ----------


def test_before_column_shows_the_real_entry_not_the_models_claim(assistant):
    reply = {"changes_json": json.dumps([
        {"op": "edit", "target": "term", "key": "mc", "before": {"kinds": ["bogus.claim"]},
         "after": {"kinds": ["speech.mc"]}, "reason": "tweak"},
    ])}
    assistant._provider_factory = lambda: _FakeProvider(reply)
    assistant._call.run = lambda kind, fn, *a, on_success: on_success(fn(*a)) or True
    assistant._propose()

    before_text = assistant.table.item(0, 1).text()
    assert "bogus" not in before_text
    assert "speech.mc" in before_text


# -- fix round 1, I1: the provider factory runs on the worker, not the GUI
# thread -- its own error must reach _failed, never crash a Qt slot -------


def test_a_provider_factory_error_reaches_the_assistant_without_crashing(
        qt_app, tmp_path, monkeypatch, settle):
    from wing_parser import config as config_module
    from wing_parser.classifier import provider as provider_module
    from wing_parser.classifier import vocabulary as vocab_module
    from wing_parser.ui.vocabulary_assistant import VocabularyAssistant

    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "provider.yaml").write_text("api_key: sk-test\n", encoding="utf-8")
    monkeypatch.setenv(config_module.ENV_VAR, str(knowledge))
    monkeypatch.delenv(provider_module.ENV_VAR, raising=False)

    vocabulary = vocab_module.Vocabulary.load(tmp_path / "vocab")

    def bad_factory():
        raise ValueError("bad provider.yaml")

    widget = VocabularyAssistant(vocabulary, bad_factory, lambda: None)
    assert widget.propose_button.isEnabled()   # a real (if fake) key IS configured

    started = widget.propose_for_fragments(("x",))
    assert started
    assert settle(lambda: "bad provider.yaml" in widget.status_label.text())


# -- fix round 1 minor: drive the REAL ButtonRunner/CallRunner path (not a
# patched _call.run), with a fake provider and timeout=0 ------------------


def test_a_real_timeout_is_reported_through_the_real_call_runner(qt_app, tmp_path, settle):
    import threading
    from functools import partial

    from wing_parser.classifier import vocabulary as vocab_module
    from wing_parser.classifier.matcher import known_kinds
    from wing_parser.ui import vocabulary_assistant_support as support
    from wing_parser.ui.vocabulary_assistant import VocabularyAssistant

    gate = threading.Event()

    class _HangingProvider:
        def complete_json(self, system, user, schema):
            gate.wait(timeout=5.0)
            return {"changes_json": "[]"}

    vocabulary = vocab_module.Vocabulary.load(tmp_path)
    widget = VocabularyAssistant(vocabulary, lambda: _HangingProvider(), lambda: None)
    widget._key_ok = True
    widget.propose_button.setEnabled(True)

    try:
        call = partial(support.propose_via_factory, instruction="", fragments=(),
                       vocabulary=vocabulary, known_kinds=known_kinds("channels"))
        started = widget._call.run(
            "guesses", call, widget._provider_factory, on_success=lambda r: None, timeout=0)
        assert started
        assert settle(lambda: "0 s" in widget.status_label.text())
    finally:
        gate.set()


# -- fix round 1, I0: no-key grey-out before any call, and recovery -------


def test_no_key_greys_out_before_any_call_and_the_factory_is_never_reached(
        qt_app, monkeypatch, tmp_path):
    from wing_parser import config as config_module
    from wing_parser.classifier import provider as provider_module
    from wing_parser.classifier import vocabulary as vocab_module
    from wing_parser.ui.vocabulary_assistant import VocabularyAssistant

    monkeypatch.setenv(config_module.ENV_VAR, str(tmp_path / "knowledge"))
    monkeypatch.delenv(provider_module.ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    for env in ("ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY"):
        monkeypatch.delenv(env, raising=False)

    vocabulary = vocab_module.Vocabulary.load(tmp_path / "vocab")
    reached = []
    widget = VocabularyAssistant(
        vocabulary, lambda: reached.append(1) or _FakeProvider(_mixed_reply()), lambda: None)

    assert not widget.propose_button.isEnabled()
    assert not widget.instruction_edit.isEnabled()
    assert widget.status_label.text() != ""

    assert widget.propose_for_fragments(("x",)) is False
    assert reached == []   # the factory was never even invoked

    widget._propose()      # the button click path refuses the same way
    assert reached == []


def test_the_key_status_rechecks_when_the_tab_is_shown(qt_app, monkeypatch, tmp_path):
    from wing_parser import config as config_module
    from wing_parser.classifier import provider as provider_module
    from wing_parser.classifier import vocabulary as vocab_module
    from wing_parser.ui.vocabulary_assistant import VocabularyAssistant

    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    monkeypatch.setenv(config_module.ENV_VAR, str(knowledge))
    monkeypatch.delenv(provider_module.ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    for env in ("ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY"):
        monkeypatch.delenv(env, raising=False)

    vocabulary = vocab_module.Vocabulary.load(tmp_path / "vocab")
    widget = VocabularyAssistant(vocabulary, lambda: _FakeProvider(_mixed_reply()), lambda: None)
    assert not widget.propose_button.isEnabled()

    # Settings just saved a key while this window stayed open.
    (knowledge / "provider.yaml").write_text("api_key: sk-test\n", encoding="utf-8")
    widget.show()   # the re-check trigger, same idiom as key_status.KeyStatusLine
    assert widget.propose_button.isEnabled()
    assert widget.instruction_edit.isEnabled()
    assert widget.status_label.text() == ""


# -- greying out on an unrecoverable call failure (design spec §8.1) -------


class _RaisingProvider:
    def __init__(self, exc):
        self._exc = exc

    def complete_json(self, system, user, schema):
        raise self._exc


def test_a_missing_sdk_failure_greys_the_tab_out_and_says_why(qt_app, tmp_path):
    """Fix round 1 (a) made classify() walk the __cause__ chain, so
    BAD_KEY/QUOTA/NO_NETWORK/SDK_MISSING are all genuinely reachable
    through this call path now (an earlier version of this test's own
    docstring said only SDK_MISSING was). SDK_MISSING is exercised here
    because it is the easiest to raise offline: the exact text
    provider_anthropic.py's own ImportError handler raises, with no need
    to fake a status_code."""
    from wing_parser.classifier import vocabulary as vocab_module
    from wing_parser.ui.vocabulary_assistant import VocabularyAssistant

    vocabulary = vocab_module.Vocabulary.load(tmp_path)
    exc = RuntimeError(
        "talking to Claude needs the anthropic package. Install it with:  pip install -e .[llm]"
    )
    widget = VocabularyAssistant(vocabulary, lambda: _RaisingProvider(exc), lambda: None)
    widget._key_ok = True
    widget.propose_button.setEnabled(True)
    widget.instruction_edit.setEnabled(True)

    def fake_run(kind, fn, *a, on_success):
        try:
            result = fn(*a)
        except Exception as caught:  # mirrors ButtonRunner routing a failure to on_error
            widget._failed(caught)
        else:
            on_success(result)
        return True

    widget._call.run = fake_run
    widget._propose()

    assert not widget.propose_button.isEnabled()
    assert not widget.instruction_edit.isEnabled()
    assert "SDK" in widget.status_label.text() or "installed" in widget.status_label.text()
