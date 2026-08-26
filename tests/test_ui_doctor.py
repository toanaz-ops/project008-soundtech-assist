"""The doctor page: findings shown, verdicts taken, clears kept silent."""

import pytest

pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture
def page(qt_app, vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.doctor_page import DoctorPage
    from wing_parser.ui.session import Session

    doctor = DoctorPage()
    doctor.set_session(Session.open(vu_path))
    return doctor


def test_programmatic_clear_does_not_emit_selected(page):
    emitted = []
    page.selected.connect(emitted.append)

    page.show_finding(None)                  # MainWindow/set_session path
    page.set_session(None)                   # the other internal clear path

    assert emitted == []


def test_a_user_row_click_emits_selected_exactly_once(page):
    emitted = []
    page.selected.connect(emitted.append)

    page.findings_view._table.selectRow(1)   # the real click path, offscreen;
    # row 0 is already taken by set_session's own first-row selection.

    assert len(emitted) == 1
    assert emitted[0] is not None


def test_set_session_selects_the_first_row_and_wakes_the_verdict_bar(page):
    selection = page.findings_view._table.selectionModel().selectedRows()
    assert len(selection) == 1
    assert all(b.isEnabled() for b in page.verdict_bar.buttons.values())
    assert page.verdict_bar.note.isEnabled()


def test_the_first_row_selection_is_silent(qt_app, vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.doctor_page import DoctorPage
    from wing_parser.ui.session import Session

    doctor = DoctorPage()
    emitted = []
    doctor.selected.connect(emitted.append)
    doctor.set_session(Session.open(vu_path))

    assert emitted == []
