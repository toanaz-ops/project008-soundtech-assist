"""Spec §8.1: the Vocabulary window's Sets and Terms tabs.

Every test builds a real VocabularyWindow over an isolated tmp_path
directory (no real knowledge/ touched) and drives its real buttons and
tables -- QT_QPA_PLATFORM=offscreen, timeout=2 is not needed here since
nothing in this window makes a network call (that arrives in Task 6).
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtWidgets import QMessageBox


@pytest.fixture
def window(qt_app, tmp_path):
    from wing_parser.ui.vocabulary_window import VocabularyWindow

    return VocabularyWindow(directory=tmp_path)


def test_the_sets_tab_lists_every_shipped_default(window):
    labels = {window.sets_tab.table.item(r, 0).text()
             for r in range(window.sets_tab.table.rowCount())}
    assert {"Drum kit", "Band", "Award moment"} <= labels


def test_the_terms_tab_lists_every_shipped_default(window):
    keys = {window.terms_tab.table.item(r, 0).text()
           for r in range(window.terms_tab.table.rowCount())}
    assert {"mc", "trống", "hoa tươi"} <= keys


def test_adding_a_set_through_the_dialog_shows_up_after_accept(window, monkeypatch):
    from wing_parser.ui import vocabulary_sets_tab

    monkeypatch.setattr(
        vocabulary_sets_tab, "VocabularySetDialog",
        lambda *a, **k: _AutoAcceptSetDialog("cajon kit", "Cajon kit",
                                             ("drums.pad",), ()),
    )
    window.sets_tab.table.clearSelection()
    window.sets_tab._add()
    labels = {window.sets_tab.table.item(r, 0).text()
             for r in range(window.sets_tab.table.rowCount())}
    assert "Cajon kit" in labels


def test_editing_drum_kit_changes_what_band_shows_as_nested(window, monkeypatch):
    """F13: the Sets tab shows each set's fully expanded kinds beside its
    own list, so editing Drum kit's effect on Band is visible without
    opening Band's own row."""
    from wing_parser.ui import vocabulary_sets_tab

    monkeypatch.setattr(
        vocabulary_sets_tab, "VocabularySetDialog",
        lambda *a, **k: _AutoAcceptSetDialog("drum kit", "Drum kit", ("drums.pad",), ()),
    )
    rows = {window.sets_tab.table.item(r, 0).text(): r
           for r in range(window.sets_tab.table.rowCount())}
    window.sets_tab.table.selectRow(rows["Drum kit"])
    window.sets_tab._edit()

    band_row = {window.sets_tab.table.item(r, 0).text(): r
               for r in range(window.sets_tab.table.rowCount())}["Band"]
    nested_cell = window.sets_tab.table.item(band_row, 2).text()
    assert "drums.pad" in nested_cell


def test_deleting_a_default_term_then_resetting_brings_it_back(window):
    rows = {window.terms_tab.table.item(r, 0).text(): r
           for r in range(window.terms_tab.table.rowCount())}
    window.terms_tab.table.selectRow(rows["hoa tươi"])
    window.terms_tab._delete()
    keys_after_delete = {window.terms_tab.table.item(r, 0).text()
                         for r in range(window.terms_tab.table.rowCount())}
    assert "hoa tươi" not in keys_after_delete

    # Reset needs a fresh vocabulary reload to see the tombstone go away --
    # exactly what _on_changed()/_reload() already does on every write.
    window._reload()
    from wing_parser.classifier import vocabulary as vocab_module
    v = vocab_module.Vocabulary.load(window._directory)
    v.reset_term("hoa tươi")
    window._reload()
    keys_after_reset = {window.terms_tab.table.item(r, 0).text()
                        for r in range(window.terms_tab.table.rowCount())}
    assert "hoa tươi" in keys_after_reset


def test_the_window_opens_from_the_real_main_windows_tools_menu(qt_app, tmp_path, monkeypatch):
    from wing_parser import config
    from wing_parser.ui.main_window import MainWindow
    from wing_parser.ui import menus

    monkeypatch.setenv(config.ENV_VAR, str(tmp_path))
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    opened = {}

    def _stub_vocabulary_window(parent):
        opened["parent"] = parent
        return _NullExec()

    monkeypatch.setattr(menus, "VocabularyWindow", _stub_vocabulary_window)
    window = MainWindow(None)
    window.open_vocabulary()
    assert opened["parent"] is window


def test_a_hand_edited_bad_entry_shows_as_a_non_modal_problem_notice(qt_app, tmp_path):
    """Controller addition 1: `Vocabulary.problems` (loader-side
    diagnostics for a hand-edited classifier.yaml, vocabulary.py S3.2)
    must be visible somewhere in this window -- not swallowed, and not
    a blocking QMessageBox that would fire on every single open."""
    from wing_parser.classifier import cache
    from wing_parser.ui.vocabulary_window import VocabularyWindow

    doc = cache.read_raw(tmp_path)
    doc.setdefault("cuesheet", {})["broken term"] = {
        "kinds": ["no.such.kind"], "match": "word",
    }
    cache.write_raw(doc, tmp_path)

    win = VocabularyWindow(directory=tmp_path)
    win.show()  # isVisible() reflects real on-screen state, not just the flag
    assert win.problems_label.isVisible()
    assert "broken term" in win.problems_label.text()
    assert not win.isModal()  # the window itself never blocks on this notice


def test_creating_a_set_cycle_shows_the_path_and_keeps_the_dialog_open(window, monkeypatch):
    """Controller addition 2: CycleError must be shown naming the path,
    the write must not happen, and nothing may crash."""
    from wing_parser.ui import vocabulary_sets_tab

    warnings = []
    monkeypatch.setattr(QMessageBox, "warning",
                        lambda *a, **k: warnings.append(a[-1]))
    monkeypatch.setattr(
        vocabulary_sets_tab, "VocabularySetDialog",
        lambda *a, **k: _FailOnceDialog(("drum kit", "Drum kit", (), ("band",))),
    )
    rows = {window.sets_tab.table.item(r, 0).text(): r
           for r in range(window.sets_tab.table.rowCount())}
    window.sets_tab.table.selectRow(rows["Drum kit"])
    window.sets_tab._edit()  # band already nests drum kit -> a cycle through it

    assert len(warnings) == 1
    assert "cycle" in warnings[0] and "→" in warnings[0]
    # the failed write never landed: Drum kit is still there, unmoved.
    rows_after = {window.sets_tab.table.item(r, 0).text(): r
                 for r in range(window.sets_tab.table.rowCount())}
    assert "Drum kit" in rows_after


def test_an_empty_term_write_shows_an_error_and_keeps_the_dialog_open(window, monkeypatch):
    """put_term raises a plain ValueError (not ignore, no kinds, no sets)
    -- must be caught the same way as the named vocabulary exceptions."""
    from wing_parser.ui import vocabulary_terms_tab

    warnings = []
    monkeypatch.setattr(QMessageBox, "warning",
                        lambda *a, **k: warnings.append(a[-1]))
    monkeypatch.setattr(
        vocabulary_terms_tab, "VocabularyTermDialog",
        lambda *a, **k: _FailOnceDialog(("brand new term", (), (), False, "word")),
    )
    window.terms_tab.table.clearSelection()
    window.terms_tab._add()

    assert len(warnings) == 1
    keys_after = {window.terms_tab.table.item(r, 0).text()
                 for r in range(window.terms_tab.table.rowCount())}
    assert "brand new term" not in keys_after


class _NullExec:
    def exec(self):
        return 0


class _AutoAcceptSetDialog:
    """Stands in for VocabularySetDialog -- exec() always accepts, result()
    hands back whatever this test wants written."""

    def __init__(self, key, label, kinds, sets_):
        self._payload = (key, label, kinds, sets_)

    def exec(self):
        return 1

    def result(self):
        return self._payload


class _FailOnceDialog:
    """A stand-in dialog whose write is expected to fail: exec() accepts
    once (as if the operator clicked OK), and the tab's own retry loop
    calls exec() on it again after the write raises -- this second call
    returns 0, as if the operator saw the error and gave up, so the test
    does not hang in the tab's re-show loop."""

    def __init__(self, payload):
        self._payload = payload
        self._calls = 0

    def exec(self):
        self._calls += 1
        return 1 if self._calls == 1 else 0

    def result(self):
        return self._payload
