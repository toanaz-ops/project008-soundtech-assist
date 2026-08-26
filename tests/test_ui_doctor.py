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

    page.findings_view._table.selectRow(0)   # the real click path, offscreen

    assert len(emitted) == 1
    assert emitted[0] is not None
