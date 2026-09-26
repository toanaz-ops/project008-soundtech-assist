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
    widget._tmp_path = tmp_path  # test-only stash, not a public seam
    widget._applied_log = applied
    return widget


def test_a_mixed_valid_invalid_proposal_only_lets_the_valid_one_be_ticked(assistant, settle):
    assistant._call.run = lambda kind, fn, *a, on_success: on_success(fn(*a)) or True
    assistant._propose()
    assert assistant.table.rowCount() == 2
    assert assistant._checks[0].isEnabled() and assistant._checks[0].isChecked()
    assert not assistant._checks[1].isEnabled()


def test_apply_writes_only_the_ticked_valid_change_and_nothing_before(assistant):
    from wing_parser.classifier import vocabulary as vocab_module

    assistant._call.run = lambda kind, fn, *a, on_success: on_success(fn(*a)) or True
    assistant._propose()
    assert assistant._tmp_path is not None
    before = vocab_module.Vocabulary.load(assistant._tmp_path).terms()
    assert "cajon" not in {t.key for t in before}   # nothing written before Apply

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


# -- greying out on an unrecoverable failure (design spec §8.1) -------------


class _RaisingProvider:
    def __init__(self, exc):
        self._exc = exc

    def complete_json(self, system, user, schema):
        raise self._exc


def test_a_missing_sdk_failure_greys_the_tab_out_and_says_why(qt_app, tmp_path):
    """The one provider_errors class genuinely reachable through this call
    path: `provider.py`'s shared `complete_json` wraps every raw adapter
    exception into a bare `ProviderError(str(exc))` before it reaches
    `_failed` -- stripping a real SDK error's `.status_code` and type, so
    BAD_KEY/QUOTA/NO_NETWORK cannot be told apart from a schema failure
    here (see the module docstring in vocabulary_assistant.py). SDK_MISSING
    survives because provider_errors.classify matches it on the wrapped
    message text, not the exception's type -- exactly the text
    provider_anthropic.py's own ImportError handler raises."""
    from wing_parser.classifier import vocabulary as vocab_module
    from wing_parser.ui.vocabulary_assistant import VocabularyAssistant

    vocabulary = vocab_module.Vocabulary.load(tmp_path)
    exc = RuntimeError(
        "talking to Claude needs the anthropic package. Install it with:  pip install -e .[llm]"
    )
    widget = VocabularyAssistant(vocabulary, lambda: _RaisingProvider(exc), lambda: None)

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
