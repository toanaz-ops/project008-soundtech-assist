"""Spec §8.1: the Vocabulary window's Sets and Terms tabs, plus fix
round 1's spec gaps (S1 search, S2 broken-reference actions) and
data-safety fixes (I1 reachable Reset for a deleted default, I2 Add
validation, I3 shared dialog-retry helper).

Every test builds a real VocabularyWindow over an isolated tmp_path
directory (no real knowledge/ touched) and drives its real buttons and
tables -- QT_QPA_PLATFORM=offscreen, timeout=2 is not needed here since
nothing in this window makes a network call (that arrives in Task 6).
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QInputDialog, QMessageBox

from wing_parser.classifier import vocabulary as vocab_module
from wing_parser.ui.texts import text


@pytest.fixture
def window(qt_app, tmp_path):
    from wing_parser.ui.vocabulary_window import VocabularyWindow

    return VocabularyWindow(directory=tmp_path)


def _make_broken_term(window) -> None:
    """A term with a kind AND a set reference that then stops existing
    (a manual-only set, so deleting it drops the raw entry outright --
    genuinely unknown afterwards, not a "default, deleted" tombstone)."""
    window.vocabulary.put_set("temp kit", label="Temp kit", kinds=("drums.pad",))
    window.vocabulary.put_term("temp term", kinds=("speech.mc",),
                               sets=("temp kit",), match="word")
    window.vocabulary.delete_set("temp kit")
    window._reload()


def _make_broken_set(window) -> None:
    """Fix round 2, item 3: a set nesting another set that then stops
    existing -- "broken exactly like a term's" (spec §8.1)."""
    window.vocabulary.put_set("temp kit", label="Temp kit", kinds=("drums.pad",))
    window.vocabulary.put_set("host kit", label="Host kit", kinds=("speech.mc",),
                              sets=("temp kit",))
    window.vocabulary.delete_set("temp kit")
    window._reload()


def _stub_confirm(monkeypatch, *, yes: bool) -> list:
    """Stubs QMessageBox.question the same way existing tests stub
    QMessageBox.warning -- returns the list of call-arg tuples so a test
    can assert what was named in the confirmation."""
    calls: list = []

    def _question(*args, **kwargs):
        calls.append(args)
        return QMessageBox.StandardButton.Yes if yes else QMessageBox.StandardButton.No

    monkeypatch.setattr(QMessageBox, "question", _question)
    return calls


def _rows_by_key(table, column=0) -> dict:
    return {table.item(r, column).text(): r for r in range(table.rowCount())}


def _visible_keys(table, column=0) -> set:
    return {table.item(r, column).text() for r in range(table.rowCount())
           if not table.isRowHidden(r)}


# -- brief's original coverage (kept) ----------------------------------------


def test_tools_vocabulary_over_a_broken_classifier_yaml_warns_instead_of_crashing(
        qt_app, tmp_path, monkeypatch):
    """I1: `VocabularyWindow.__init__` calls `Vocabulary.load(directory)`
    unguarded -- `cache._read` raises ValueError for a YAML syntax error
    or a non-mapping domain (unlike a per-entry hand-edit mistake, which
    `vocabulary.py`'s own loader never raises on). Reached from Tools >
    Vocabulary (menus.py), the Terms step's Vocabulary... button, and its
    AI: propose button; this test drives the real menu action, which in
    a console=False release exe would otherwise die silently."""
    from PySide6.QtGui import QAction
    from PySide6.QtWidgets import QMessageBox
    from wing_parser.ui.main_window import MainWindow

    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    (tmp_path / "classifier.yaml").write_text("cuesheet: [unterminated", encoding="utf-8")

    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warnings.append(a) or None)

    main_window = MainWindow(None)
    action = next(
        a for a in main_window.findChildren(QAction) if a.text() == text("menu.vocabulary"))
    action.trigger()   # must not raise

    assert warnings and "invalid YAML" in str(warnings[-1])


def test_the_sets_tab_lists_every_shipped_default(window):
    labels = _visible_keys(window.sets_tab.table)
    assert {"Drum kit", "Band", "Award moment"} <= labels


def test_the_terms_tab_lists_every_shipped_default(window):
    keys = _visible_keys(window.terms_tab.table)
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
    assert "Cajon kit" in _rows_by_key(window.sets_tab.table)


def test_editing_drum_kit_changes_what_band_shows_as_nested(window, monkeypatch):
    """F13: the Sets tab shows each set's fully expanded kinds beside its
    own list, so editing Drum kit's effect on Band is visible without
    opening Band's own row."""
    from wing_parser.ui import vocabulary_sets_tab

    monkeypatch.setattr(
        vocabulary_sets_tab, "VocabularySetDialog",
        lambda *a, **k: _AutoAcceptSetDialog("drum kit", "Drum kit", ("drums.pad",), ()),
    )
    rows = _rows_by_key(window.sets_tab.table)
    window.sets_tab.table.selectRow(rows["Drum kit"])
    window.sets_tab._edit()

    band_row = _rows_by_key(window.sets_tab.table)["Band"]
    nested_cell = window.sets_tab.table.item(band_row, 2).text()
    assert "drums.pad" in nested_cell


def test_a_hand_edited_bad_entry_shows_as_a_non_modal_problem_notice(qt_app, tmp_path):
    """Controller addition 1: `Vocabulary.problems` (loader-side
    diagnostics for a hand-edited classifier.yaml, vocabulary.py S3.2)
    must be visible somewhere in this window -- not swallowed, and not
    a blocking QMessageBox that would fire on every single open. Fix
    round 1: plain text (a hand-edited key can contain markup-looking
    characters), and the header must not tell the operator to fix a row
    that does not exist for a malformed entry."""
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
    assert "fix the entry below" not in win.problems_label.text()
    assert "classifier.yaml" in win.problems_label.text()
    assert win.problems_label.textFormat() == Qt.TextFormat.PlainText
    assert not win.isModal()  # the window itself never blocks on this notice


def test_the_window_opens_from_the_real_main_windows_tools_menu(qt_app, tmp_path, monkeypatch):
    """Fix round 1 minor: trigger the real QAction found by its own
    label, rather than calling the delegating method directly. I1: the
    handler goes through `vocabulary_window.open_vocabulary` now (a
    broken classifier.yaml warns instead of crashing), so the stub is
    patched where that guard actually constructs the dialog."""
    import wing_parser.ui.vocabulary_window as vw_module
    from wing_parser import config
    from wing_parser.ui.main_window import MainWindow

    monkeypatch.setenv(config.ENV_VAR, str(tmp_path))
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    opened = {}

    def _stub_vocabulary_window(parent, *, directory=None, initial_fragments=()):
        opened["parent"] = parent
        return _NullExec()

    monkeypatch.setattr(vw_module, "VocabularyWindow", _stub_vocabulary_window)
    window = MainWindow(None)
    action = _tools_menu_action(window, text("menu.vocabulary"))
    action.trigger()
    assert opened["parent"] is window


def _tools_menu_action(window, label):
    for menu_action in window.menuBar().actions():
        menu = menu_action.menu()
        if menu is None:
            continue
        for action in menu.actions():
            if action.text() == label:
                return action
    raise AssertionError(f"no menu action with text {label!r}")


# -- fix round 1, S1: live search ---------------------------------------------


def test_search_filters_terms_by_folded_diacritic_insensitive_key(window):
    window.terms_tab.search_edit.setText("trong")   # folds from "trống"
    visible = _visible_keys(window.terms_tab.table)
    assert "trống" in visible
    assert "mc" not in visible
    assert "hoa tươi" not in visible


def test_search_filters_sets_by_key_and_label(window):
    window.sets_tab.search_edit.setText("drum")
    assert _visible_keys(window.sets_tab.table) == {"Drum kit"}


def test_search_finds_a_set_by_its_key_when_the_label_does_not_contain_it(window, monkeypatch):
    """Fix round 2, item 1: the Sets-tab haystack used to be built from
    label_text + label + kinds -- label_text equals label for a normal
    row, so the key itself was never actually searchable."""
    from wing_parser.ui import vocabulary_sets_tab

    monkeypatch.setattr(
        vocabulary_sets_tab, "VocabularySetDialog",
        lambda *a, **k: _AutoAcceptSetDialog("cajon kit", "Percussion", ("drums.pad",), ()),
    )
    window.sets_tab.table.clearSelection()
    window.sets_tab._add()

    window.sets_tab.search_edit.setText("cajon")
    assert "Percussion" in _visible_keys(window.sets_tab.table)


def test_search_also_matches_by_kind_not_only_key_or_label(window):
    window.sets_tab.search_edit.setText("vocal")   # only Band's kinds have it
    assert _visible_keys(window.sets_tab.table) == {"Band"}


def test_clearing_the_search_shows_every_row_again(window):
    window.terms_tab.search_edit.setText("trong")
    window.terms_tab.search_edit.setText("")
    visible = _visible_keys(window.terms_tab.table)
    assert {"mc", "trống", "hoa tươi"} <= visible


def test_a_search_hidden_term_cannot_be_deleted_unseen(window, monkeypatch):
    """Fix round 2, item 2: select "mc", type "trong" (hides "mc"'s row),
    click Delete -- "mc" must survive, and the confirmation must never
    even fire, because the selection was cleared when its row vanished
    behind the filter."""
    calls = _stub_confirm(monkeypatch, yes=True)
    rows = _rows_by_key(window.terms_tab.table)
    window.terms_tab.table.selectRow(rows["mc"])
    window.terms_tab.search_edit.setText("trong")
    assert not window.terms_tab.delete_button.isEnabled()
    window.terms_tab.delete_button.click()

    assert not calls
    v = vocab_module.Vocabulary.load(window._directory)
    assert "mc" in {t.key for t in v.terms()}


def test_a_search_hidden_set_cannot_be_deleted_unseen(window, monkeypatch):
    calls = _stub_confirm(monkeypatch, yes=True)
    rows = _rows_by_key(window.sets_tab.table)
    window.sets_tab.table.selectRow(rows["Band"])
    window.sets_tab.search_edit.setText("drum")   # hides "Band", keeps "Drum kit"
    assert not window.sets_tab.delete_button.isEnabled()
    window.sets_tab.delete_button.click()

    assert not calls
    v = vocab_module.Vocabulary.load(window._directory)
    assert "band" in {s.key for s in v.sets()}


# -- fix round 1, S2: fixing a broken set reference ---------------------------


def test_a_broken_reference_disables_edit_and_enables_the_two_fix_actions(window):
    """"today's silent drop-on-Edit must go" -- Edit is disabled outright
    for a row whose set reference is genuinely gone."""
    _make_broken_term(window)
    rows = _rows_by_key(window.terms_tab.table)
    window.terms_tab.table.selectRow(rows["temp term"])
    assert not window.terms_tab.edit_button.isEnabled()
    assert window.terms_tab.pick_set_button.isEnabled()
    assert window.terms_tab.drop_ref_button.isEnabled()


def test_picking_another_set_replaces_the_broken_reference(window, monkeypatch):
    _make_broken_term(window)
    monkeypatch.setattr(QInputDialog, "getItem", lambda *a, **k: ("band", True))
    rows = _rows_by_key(window.terms_tab.table)
    window.terms_tab.table.selectRow(rows["temp term"])
    window.terms_tab._pick_another_set()

    v = vocab_module.Vocabulary.load(window._directory)
    term = {t.key: t for t in v.terms()}["temp term"]
    assert term.sets == ("band",)
    assert term.kinds == ("speech.mc",)   # untouched


def test_dropping_the_reference_removes_it_and_keeps_the_rest(window):
    _make_broken_term(window)
    rows = _rows_by_key(window.terms_tab.table)
    window.terms_tab.table.selectRow(rows["temp term"])
    window.terms_tab._drop_reference()

    v = vocab_module.Vocabulary.load(window._directory)
    term = {t.key: t for t in v.terms()}["temp term"]
    assert term.sets == ()
    assert term.kinds == ("speech.mc",)


# -- fix round 2, item 3: S2 generalised to the Sets tab -----------------------


def test_a_broken_nested_set_shows_the_broken_marker(window):
    _make_broken_set(window)
    rows = _rows_by_key(window.sets_tab.table)
    nested_cell = window.sets_tab.table.item(rows["Host kit"], 2).text()
    assert "temp kit" in nested_cell and "no longer exists" in nested_cell


def test_a_broken_nested_set_disables_edit_and_enables_the_two_fix_actions(window):
    _make_broken_set(window)
    rows = _rows_by_key(window.sets_tab.table)
    window.sets_tab.table.selectRow(rows["Host kit"])
    assert not window.sets_tab.edit_button.isEnabled()
    assert window.sets_tab.pick_set_button.isEnabled()
    assert window.sets_tab.drop_ref_button.isEnabled()


def test_picking_another_set_replaces_a_sets_broken_nested_reference(window, monkeypatch):
    _make_broken_set(window)
    monkeypatch.setattr(QInputDialog, "getItem", lambda *a, **k: ("band", True))
    rows = _rows_by_key(window.sets_tab.table)
    window.sets_tab.table.selectRow(rows["Host kit"])
    window.sets_tab._pick_another_set()

    v = vocab_module.Vocabulary.load(window._directory)
    host = {s.key: s for s in v.sets()}["host kit"]
    assert host.sets == ("band",)
    assert host.kinds == ("speech.mc",)   # untouched


def test_dropping_a_sets_broken_nested_reference_keeps_the_rest(window):
    _make_broken_set(window)
    rows = _rows_by_key(window.sets_tab.table)
    window.sets_tab.table.selectRow(rows["Host kit"])
    window.sets_tab._drop_reference()

    v = vocab_module.Vocabulary.load(window._directory)
    host = {s.key: s for s in v.sets()}["host kit"]
    assert host.sets == ()
    assert host.kinds == ("speech.mc",)


# -- fix round 1, I1: Reset reachable for a deleted default -------------------


def test_deleting_a_default_term_then_resetting_brings_it_back(window, monkeypatch):
    _stub_confirm(monkeypatch, yes=True)
    rows = _rows_by_key(window.terms_tab.table)
    window.terms_tab.table.selectRow(rows["hoa tươi"])
    window.terms_tab.delete_button.click()

    rows_after_delete = _rows_by_key(window.terms_tab.table)
    assert "hoa tươi" in rows_after_delete   # now its own greyed row
    window.terms_tab.table.selectRow(rows_after_delete["hoa tươi"])
    assert not window.terms_tab.edit_button.isEnabled()
    assert not window.terms_tab.delete_button.isEnabled()
    assert window.terms_tab.reset_button.isEnabled()
    window.terms_tab.reset_button.click()

    v = vocab_module.Vocabulary.load(window._directory)
    assert "hoa tươi" in {t.key for t in v.terms()}
    assert "hoa tươi" not in {t.key for t in v.deleted_terms()}


def test_deleting_a_default_set_then_resetting_brings_it_back(window, monkeypatch):
    _stub_confirm(monkeypatch, yes=True)
    rows = _rows_by_key(window.sets_tab.table)
    window.sets_tab.table.selectRow(rows["Award moment"])
    window.sets_tab.delete_button.click()

    rows_after_delete = _rows_by_key(window.sets_tab.table)
    assert "award moment" in rows_after_delete   # deleted rows show their key
    window.sets_tab.table.selectRow(rows_after_delete["award moment"])
    assert not window.sets_tab.edit_button.isEnabled()
    assert not window.sets_tab.delete_button.isEnabled()
    assert window.sets_tab.reset_button.isEnabled()
    window.sets_tab.reset_button.click()

    v = vocab_module.Vocabulary.load(window._directory)
    assert "award moment" in {s.key for s in v.sets()}
    assert "award moment" not in {s.key for s in v.deleted_sets()}


def test_reset_is_disabled_for_a_manual_only_set(window):
    window.vocabulary.put_set("cajon kit", label="Cajon kit", kinds=("drums.pad",))
    window._reload()
    rows = _rows_by_key(window.sets_tab.table)
    window.sets_tab.table.selectRow(rows["Cajon kit"])
    assert not window.sets_tab.reset_button.isEnabled()


def test_reset_is_disabled_for_a_manual_only_term(window):
    window.vocabulary.put_term("cajon", kinds=("drums.pad",), match="word")
    window._reload()
    rows = _rows_by_key(window.terms_tab.table)
    window.terms_tab.table.selectRow(rows["cajon"])
    assert not window.terms_tab.reset_button.isEnabled()


# -- fix round 1, I2: Add validates the name -----------------------------------


def test_add_set_refuses_a_blank_name_and_keeps_the_dialog_open(window, monkeypatch):
    from wing_parser.ui import vocabulary_sets_tab

    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warnings.append(a[-1]))
    dialog = _ScriptedDialog(("   ", "Blank", (), ()))
    monkeypatch.setattr(vocabulary_sets_tab, "VocabularySetDialog", lambda *a, **k: dialog)
    before = _rows_by_key(window.sets_tab.table)
    window.sets_tab.table.clearSelection()
    window.sets_tab._add()

    assert warnings and "empty" in warnings[0].lower()
    assert dialog.calls == 2
    assert _rows_by_key(window.sets_tab.table).keys() == before.keys()


def test_add_set_refuses_a_name_that_already_exists(window, monkeypatch):
    from wing_parser.ui import vocabulary_sets_tab

    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warnings.append(a[-1]))
    dialog = _ScriptedDialog(("Band", "Band", (), ()))   # folds to the existing "band"
    monkeypatch.setattr(vocabulary_sets_tab, "VocabularySetDialog", lambda *a, **k: dialog)
    window.sets_tab.table.clearSelection()
    window.sets_tab._add()

    assert warnings and "already exists" in warnings[0]
    assert dialog.calls == 2


def test_add_term_refuses_a_blank_name(window, monkeypatch):
    from wing_parser.ui import vocabulary_terms_tab

    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warnings.append(a[-1]))
    dialog = _ScriptedDialog(("", (), (), False, "exact"))
    monkeypatch.setattr(vocabulary_terms_tab, "VocabularyTermDialog", lambda *a, **k: dialog)
    window.terms_tab.table.clearSelection()
    window.terms_tab._add()

    assert warnings and "empty" in warnings[0].lower()
    assert dialog.calls == 2


def test_add_term_refuses_a_name_that_already_exists(window, monkeypatch):
    from wing_parser.ui import vocabulary_terms_tab

    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warnings.append(a[-1]))
    dialog = _ScriptedDialog(("MC", ("speech.mc",), (), False, "word"))   # folds to "mc"
    monkeypatch.setattr(vocabulary_terms_tab, "VocabularyTermDialog", lambda *a, **k: dialog)
    window.terms_tab.table.clearSelection()
    window.terms_tab._add()

    assert warnings and "already exists" in warnings[0]
    assert dialog.calls == 2


def test_editing_keeps_its_replace_semantics_same_key_no_validation(window, monkeypatch):
    """Edit disables the name field, so check_new_key never fires for it
    -- editing Drum kit back onto itself must not be refused as a
    "duplicate"."""
    from wing_parser.ui import vocabulary_sets_tab

    monkeypatch.setattr(
        vocabulary_sets_tab, "VocabularySetDialog",
        lambda *a, **k: _AutoAcceptSetDialog("drum kit", "Drum kit", ("drums.pad",), ()),
    )
    rows = _rows_by_key(window.sets_tab.table)
    window.sets_tab.table.selectRow(rows["Drum kit"])
    window.sets_tab._edit()
    assert "Drum kit" in _rows_by_key(window.sets_tab.table)


# -- fix round 1 minors --------------------------------------------------------


def test_creating_a_set_cycle_shows_the_path_and_keeps_the_dialog_open(window, monkeypatch):
    from wing_parser.ui import vocabulary_sets_tab

    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warnings.append(a[-1]))
    dialog = _ScriptedDialog(("drum kit", "Drum kit", (), ("band",)))
    monkeypatch.setattr(vocabulary_sets_tab, "VocabularySetDialog", lambda *a, **k: dialog)
    rows = _rows_by_key(window.sets_tab.table)
    window.sets_tab.table.selectRow(rows["Drum kit"])
    window.sets_tab._edit()   # band already nests drum kit -> a cycle through it

    assert len(warnings) == 1
    assert "cycle" in warnings[0] and "→" in warnings[0]
    assert dialog.calls == 2
    assert "Drum kit" in _rows_by_key(window.sets_tab.table)


def test_an_empty_term_write_shows_an_error_and_keeps_the_dialog_open(window, monkeypatch):
    from wing_parser.ui import vocabulary_terms_tab

    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warnings.append(a[-1]))
    dialog = _ScriptedDialog(("brand new term", (), (), False, "word"))
    monkeypatch.setattr(vocabulary_terms_tab, "VocabularyTermDialog", lambda *a, **k: dialog)
    window.terms_tab.table.clearSelection()
    window.terms_tab._add()

    assert len(warnings) == 1
    assert dialog.calls == 2
    assert "brand new term" not in _rows_by_key(window.terms_tab.table)


def test_editing_keeps_a_case_variant_set_reference_via_folded_preselect(window):
    """Adapted from the plan's draft (fix round 1 minor): a reference
    that only differs in case/diacritics from a real set's own key is
    valid by folded identity, not broken, and the dialog's own
    pre-select must not silently drop it on an untouched OK."""
    from wing_parser.ui.vocabulary_term_dialog import VocabularyTermDialog

    window.vocabulary.put_term("case variant term", sets=("Drum Kit",), match="word")
    window._reload()
    entry = next(t for t in window.vocabulary.terms() if t.key == "case variant term")

    rows = _rows_by_key(window.terms_tab.table)
    window.terms_tab.table.selectRow(rows["case variant term"])
    assert window.terms_tab.edit_button.isEnabled()   # not treated as broken

    dialog = VocabularyTermDialog(window.terms_tab, known_kinds=(),
                                  known_sets=("drum kit",), initial=entry)
    _key, _kinds, sets_, _ignore, _match = dialog.values()
    assert sets_ == ("drum kit",)   # preserved, normalised to the real key


def test_an_oserror_from_delete_is_reported_not_raised(window, monkeypatch):
    def _boom(key):
        raise OSError("disk full")

    monkeypatch.setattr(window.vocabulary, "delete_set", _boom)
    _stub_confirm(monkeypatch, yes=True)
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warnings.append(a[-1]))
    rows = _rows_by_key(window.sets_tab.table)
    window.sets_tab.table.selectRow(rows["Band"])
    window.sets_tab.delete_button.click()

    assert warnings and "disk full" in warnings[0]
    assert "Band" in _rows_by_key(window.sets_tab.table)


def test_an_oserror_from_a_dialog_save_is_reported_and_keeps_the_dialog_open(window, monkeypatch):
    from wing_parser.ui import vocabulary_sets_tab

    def _boom(key, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(window.vocabulary, "put_set", _boom)
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning", lambda *a, **k: warnings.append(a[-1]))
    dialog = _ScriptedDialog(("cajon kit", "Cajon kit", ("drums.pad",), ()))
    monkeypatch.setattr(vocabulary_sets_tab, "VocabularySetDialog", lambda *a, **k: dialog)
    window.sets_tab.table.clearSelection()
    window.sets_tab._add()

    assert warnings and "disk full" in warnings[0]
    assert dialog.calls == 2


# -- fix round 2, item 4: confirm before dropping a hand-edited kind ----------


def _inject_weird_set(window) -> None:
    from wing_parser.classifier import cache

    doc = cache.read_raw(window._directory)
    doc.setdefault("cuesheet_sets", {})["weird kit"] = {
        "label": "Weird kit", "kinds": ["drums.pad", "no.such.kind"], "origin": "manual",
    }
    cache.write_raw(doc, window._directory)
    window._reload()


def _inject_weird_term(window) -> None:
    from wing_parser.classifier import cache

    doc = cache.read_raw(window._directory)
    doc.setdefault("cuesheet", {})["weird term"] = {
        "kinds": ["speech.mc", "no.such.kind"], "match": "word", "origin": "manual",
    }
    cache.write_raw(doc, window._directory)
    window._reload()


def test_editing_a_set_confirms_before_dropping_an_unknown_kind(window, monkeypatch):
    from wing_parser.ui import vocabulary_sets_tab

    _inject_weird_set(window)
    calls = _stub_confirm(monkeypatch, yes=False)
    dialog = _ScriptedDialog(("weird kit", "Weird kit", ("drums.pad",), ()))
    monkeypatch.setattr(vocabulary_sets_tab, "VocabularySetDialog", lambda *a, **k: dialog)

    rows = _rows_by_key(window.sets_tab.table)
    window.sets_tab.table.selectRow(rows["Weird kit"])
    window.sets_tab._edit()

    assert len(calls) == 1 and "no.such.kind" in str(calls[0])
    assert dialog.calls == 2   # declined -- reshown, not just abandoned
    v = vocab_module.Vocabulary.load(window._directory)
    assert "no.such.kind" in {s.key: s for s in v.sets()}["weird kit"].kinds


def test_confirming_the_kind_drop_saves_without_the_unknown_kind(window, monkeypatch):
    from wing_parser.ui import vocabulary_sets_tab

    _inject_weird_set(window)
    _stub_confirm(monkeypatch, yes=True)
    dialog = _ScriptedDialog(("weird kit", "Weird kit", ("drums.pad",), ()))
    monkeypatch.setattr(vocabulary_sets_tab, "VocabularySetDialog", lambda *a, **k: dialog)

    rows = _rows_by_key(window.sets_tab.table)
    window.sets_tab.table.selectRow(rows["Weird kit"])
    window.sets_tab._edit()

    assert dialog.calls == 1
    v = vocab_module.Vocabulary.load(window._directory)
    assert {s.key: s for s in v.sets()}["weird kit"].kinds == ("drums.pad",)


def test_editing_a_term_confirms_before_dropping_an_unknown_kind(window, monkeypatch):
    from wing_parser.ui import vocabulary_terms_tab

    _inject_weird_term(window)
    calls = _stub_confirm(monkeypatch, yes=False)
    dialog = _ScriptedDialog(("weird term", ("speech.mc",), (), False, "word"))
    monkeypatch.setattr(vocabulary_terms_tab, "VocabularyTermDialog", lambda *a, **k: dialog)

    rows = _rows_by_key(window.terms_tab.table)
    window.terms_tab.table.selectRow(rows["weird term"])
    window.terms_tab._edit()

    assert len(calls) == 1 and "no.such.kind" in str(calls[0])
    assert dialog.calls == 2
    v = vocab_module.Vocabulary.load(window._directory)
    assert "no.such.kind" in {t.key: t for t in v.terms()}["weird term"].kinds


# -- fix round 2, item 5: Delete confirms by name, defaults to No -------------


def test_delete_asks_for_confirmation_naming_the_entry_and_defaults_to_no(window, monkeypatch):
    calls = _stub_confirm(monkeypatch, yes=False)
    rows = _rows_by_key(window.terms_tab.table)
    window.terms_tab.table.selectRow(rows["mc"])
    window.terms_tab.delete_button.click()

    assert len(calls) == 1
    *_, message, buttons, default = calls[0]
    assert "mc" in message
    assert default == QMessageBox.StandardButton.No
    v = vocab_module.Vocabulary.load(window._directory)
    assert "mc" in {t.key for t in v.terms()}   # declined -- nothing deleted


def test_delete_proceeds_once_confirmed(window, monkeypatch):
    _stub_confirm(monkeypatch, yes=True)
    rows = _rows_by_key(window.terms_tab.table)
    window.terms_tab.table.selectRow(rows["mc"])
    window.terms_tab.delete_button.click()

    v = vocab_module.Vocabulary.load(window._directory)
    assert "mc" not in {t.key for t in v.terms()}


def test_selection_is_cleared_after_a_successful_delete(window, monkeypatch):
    _stub_confirm(monkeypatch, yes=True)
    rows = _rows_by_key(window.terms_tab.table)
    window.terms_tab.table.selectRow(rows["mc"])
    window.terms_tab.delete_button.click()

    assert window.terms_tab.table.currentRow() == -1
    assert not window.terms_tab.edit_button.isEnabled()


def test_the_window_has_an_assistant_tab_and_it_shares_the_reload(qt_app, tmp_path):
    from wing_parser.ui.vocabulary_window import VocabularyWindow

    window = VocabularyWindow(directory=tmp_path)
    assert window.tabs.indexOf(window.assistant_tab) >= 0
    assert window.assistant_tab._vocabulary is window.vocabulary


# -- fix round 1, I1: a broken provider factory must not abort __init__ ---


def test_a_broken_provider_factory_does_not_abort_window_construction(
        qt_app, monkeypatch, tmp_path, settle):
    from wing_parser import config as config_module
    from wing_parser.classifier import provider as provider_module
    from wing_parser.ui import vocabulary_window

    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "provider.yaml").write_text("api_key: sk-test\n", encoding="utf-8")
    monkeypatch.setenv(config_module.ENV_VAR, str(knowledge))
    monkeypatch.delenv(provider_module.ENV_VAR, raising=False)

    def _raising_factory(self):
        raise ValueError("boom: bad provider.yaml")

    monkeypatch.setattr(
        vocabulary_window.VocabularyWindow, "_provider_factory", _raising_factory)

    # Must not raise -- the old, eager `self._provider_factory()` call in
    # _start would have propagated straight out of this constructor.
    window = vocabulary_window.VocabularyWindow(
        directory=tmp_path / "vocab", initial_fragments=("x",))
    assert window.tabs.currentWidget() is window.assistant_tab
    assert settle(lambda: "boom" in window.assistant_tab.status_label.text())


def test_initial_fragments_switches_tab_and_really_starts_a_proposal(
        qt_app, monkeypatch, tmp_path, settle):
    from wing_parser import config as config_module
    from wing_parser.classifier import provider as provider_module
    from wing_parser.ui import vocabulary_window

    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "provider.yaml").write_text("api_key: sk-test\n", encoding="utf-8")
    monkeypatch.setenv(config_module.ENV_VAR, str(knowledge))
    monkeypatch.delenv(provider_module.ENV_VAR, raising=False)

    class _FakeProvider:
        def complete_json(self, system, user, schema):
            import json

            return {"changes_json": json.dumps([
                {"op": "add", "target": "term", "key": "cajon", "before": None,
                 "after": {"kinds": ["drums.pad"]}, "reason": "a hand drum"},
            ])}

    monkeypatch.setattr(
        vocabulary_window.VocabularyWindow, "_provider_factory", lambda self: _FakeProvider())

    window = vocabulary_window.VocabularyWindow(
        directory=tmp_path / "vocab", initial_fragments=("tốp múa",))
    assert window.tabs.currentWidget() is window.assistant_tab
    # Proof the pipeline really ran end to end (worker -> propose_changes
    # -> validate -> _show_proposal), not merely that the tab was
    # selected: the fake provider's one change populates exactly one row.
    assert settle(lambda: window.assistant_tab.table.rowCount() == 1)


# -- fix round 1, I0: the rest of the window keeps working while the
# assistant is greyed out --------------------------------------------------


def test_sets_and_terms_tabs_still_edit_while_the_assistant_is_greyed(
        qt_app, monkeypatch, tmp_path):
    from wing_parser import config as config_module
    from wing_parser.classifier import provider as provider_module
    from wing_parser.ui import vocabulary_sets_tab
    from wing_parser.ui.vocabulary_window import VocabularyWindow

    monkeypatch.setenv(config_module.ENV_VAR, str(tmp_path / "knowledge"))
    monkeypatch.delenv(provider_module.ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    for env in ("ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY"):
        monkeypatch.delenv(env, raising=False)

    window = VocabularyWindow(directory=tmp_path / "vocab")
    assert not window.assistant_tab.propose_button.isEnabled()   # greyed: no key

    monkeypatch.setattr(
        vocabulary_sets_tab, "VocabularySetDialog",
        lambda *a, **k: _AutoAcceptSetDialog("brand new set", "New Set", ("speech.mc",), ()),
    )
    window.sets_tab.table.clearSelection()
    window.sets_tab._add()
    assert "brand new set" in {s.key for s in window.vocabulary.sets()}


class _NullExec:
    def exec(self):
        return 0


class _AutoAcceptSetDialog:
    """Stands in for VocabularySetDialog -- exec() always accepts, values()
    hands back whatever this test wants written."""

    def __init__(self, key, label, kinds, sets_):
        self._payload = (key, label, kinds, sets_)

    def exec(self):
        return 1

    def values(self):
        return self._payload


class _ScriptedDialog:
    """Feeds one `values()` payload per `exec()` call, in the order
    given; once every payload has been consumed, `exec()` returns 0 (as
    if the operator gave up) -- so a tab's retry-on-failure loop cannot
    spin forever waiting for a payload that will never come."""

    def __init__(self, *payloads):
        self._payloads = list(payloads)
        self.calls = 0

    def exec(self):
        self.calls += 1
        return 1 if self._payloads else 0

    def values(self):
        return self._payloads.pop(0)


def test_both_tables_stretch_their_text_heavy_columns(window):
    """D-57: Kinds / Nested sets share the width; the rest fit contents."""
    from PySide6.QtWidgets import QHeaderView

    from wing_parser.ui.vocabulary_tab_widgets import STRETCH_COLUMNS

    stretch = QHeaderView.ResizeMode.Stretch
    contents = QHeaderView.ResizeMode.ResizeToContents
    heavy_headings = {text(key) for key in STRETCH_COLUMNS}
    for tab in (window.sets_tab, window.terms_tab):
        header = tab.table.horizontalHeader()
        seen = 0
        for column in range(tab.table.columnCount()):
            heading = tab.table.horizontalHeaderItem(column).text()
            heavy = heading in heavy_headings
            seen += heavy
            assert header.sectionResizeMode(column) == (
                stretch if heavy else contents), heading
        assert seen == len(STRETCH_COLUMNS)
