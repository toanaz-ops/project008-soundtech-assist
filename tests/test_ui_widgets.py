"""The widget layer.

Kept thin deliberately. The safety net for this application is that no
decision lives inside a widget -- those are tested in
test_ui_session.py and test_edit_*.py. What these tests pin is the
handful of places where a widget could still lie: offering a repair
that does not exist, hiding the rationale, or writing the wrong thing
to the verdict log.
"""

import pytest

from wing_parser.ui.session import Session


@pytest.fixture
def session(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    return Session.open(vu_path)


def a_finding(session, rule_id):
    return next(f for f in session.findings() if f.rule_id == rule_id)


# -- findings model -----------------------------------------------------


def test_the_model_holds_every_finding(qt_app, session):
    from wing_parser.ui.findings_model import FindingsModel

    model = FindingsModel()
    model.set_findings(session.findings())
    assert model.rowCount() == 22
    assert model.columnCount() == 5


def test_rows_are_sorted_errors_first_then_warnings_then_info(qt_app, session):
    from wing_parser.ui.findings_model import FindingsModel

    model = FindingsModel()
    model.set_findings(session.findings())
    rank = {"error": 0, "warning": 1, "info": 2}
    ranks = [rank[model.finding_at(row).severity] for row in range(model.rowCount())]
    assert ranks == sorted(ranks)


def test_the_order_is_stable_across_two_identical_loads(qt_app, vu_path, monkeypatch):
    # The table is rebuilt after every repair. One that reshuffled under
    # the cursor each time would be unusable.
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.findings_model import FindingsModel

    def keys():
        model = FindingsModel()
        model.set_findings(Session.open(vu_path).findings())
        return [
            (model.finding_at(row).rule_id, model.finding_at(row).target)
            for row in range(model.rowCount())
        ]

    assert keys() == keys()


def test_the_message_column_shows_the_finding_message(qt_app, session):
    from PySide6.QtCore import Qt

    from wing_parser.ui.findings_model import FindingsModel

    model = FindingsModel()
    model.set_findings(session.findings())
    index = model.index(0, 3)
    assert model.data(index, Qt.ItemDataRole.DisplayRole) == model.finding_at(0).message


# -- findings view ------------------------------------------------------


def test_the_severity_filter_narrows_the_list(qt_app, session):
    from wing_parser.ui.findings_view import FindingsView

    view = FindingsView()
    view.set_findings(session.findings())
    assert len(view.visible_findings()) == 22

    view._severity.setCurrentText("warning")
    shown = view.visible_findings()
    assert shown and all(f.severity == "warning" for f in shown)
    assert len(shown) < 22


def test_the_layer_filter_narrows_the_list(qt_app, session):
    from wing_parser.ui.findings_view import FindingsView

    view = FindingsView()
    view.set_findings(session.findings())
    view._layer.setCurrentText("base")
    # Every rule shipped in base_rules is base-layer, so this is all of
    # them on an unprofiled run -- the assertion that matters is that
    # the filter reaches the layer field at all.
    assert all(f.layer == "base" for f in view.visible_findings())


# -- detail panel -------------------------------------------------------


def test_a_repairable_finding_offers_a_button_with_the_descriptor_label(qt_app, session):
    from wing_parser.ui.detail_panel import DetailPanel

    panel = DetailPanel()
    panel.show_finding(a_finding(session, "G8"), session)
    assert panel.repair_button.isEnabled() is True
    assert panel.repair_button.text() == "Set the send to PRE"
    assert panel.no_repair_label.text() == ""


def test_a_finding_with_no_descriptor_offers_no_button_and_says_why(qt_app, session):
    from wing_parser.ui.detail_panel import DetailPanel

    panel = DetailPanel()
    panel.show_finding(a_finding(session, "G10"), session)
    assert panel.repair_button.isEnabled() is False
    assert "by hand" in panel.no_repair_label.text()


def test_the_panel_shows_the_rule_rationale_and_source(qt_app, session):
    from wing_parser.ui.detail_panel import DetailPanel

    panel = DetailPanel()
    panel.show_finding(a_finding(session, "G8"), session)
    rule = session.rule("G8")
    assert rule.rationale.strip()[:40] in panel.rationale_label.text()
    assert rule.source.strip()[:30] in panel.source_label.text()


def test_pressing_repair_clears_the_finding_from_the_session(qt_app, session):
    from wing_parser.ui.detail_panel import DetailPanel

    panel = DetailPanel()
    target = a_finding(session, "G8")
    panel.show_finding(target, session)
    panel.repair_button.click()

    assert len(session.findings()) == 21
    assert session.dirty is True


def test_pressing_a_disabled_repair_changes_nothing(qt_app, session):
    from wing_parser.ui.detail_panel import DetailPanel

    panel = DetailPanel()
    panel.show_finding(a_finding(session, "G10"), session)
    panel.repair_button.click()

    assert len(session.findings()) == 22
    assert session.dirty is False


# -- verdict bar --------------------------------------------------------


def test_the_verdict_bar_writes_one_line_to_the_log(qt_app, session, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    from wing_parser.advisory import feedback
    from wing_parser.ui.verdict_bar import VerdictBar

    bar = VerdictBar()
    bar.show_finding(a_finding(session, "G8"), session)
    bar.note.setText("mixer feeds this one from the desk")
    bar.buttons["false-positive"].click()

    entries = feedback.read_log(tmp_path)
    assert len(entries) == 1
    assert entries[0].rule_id == "G8"
    assert entries[0].verdict == "false-positive"
    assert entries[0].scene == str(session.path)
    assert entries[0].note == "mixer feeds this one from the desk"


def test_the_tally_reports_verdicts_already_recorded(qt_app, session, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    from wing_parser.ui.verdict_bar import VerdictBar

    bar = VerdictBar()
    finding = a_finding(session, "G8")
    bar.show_finding(finding, session)
    assert "no verdict recorded yet" in bar.tally.text()

    bar.buttons["correct"].click()
    assert "1 correct" in bar.tally.text()


def test_the_verdict_buttons_are_dead_with_nothing_selected(qt_app):
    from wing_parser.ui.verdict_bar import VerdictBar

    bar = VerdictBar()
    bar.show_finding(None, None)
    assert all(not button.isEnabled() for button in bar.buttons.values())


def test_the_whole_verdict_bar_wakes_only_with_a_selection(qt_app, session):
    from wing_parser.ui.verdict_bar import VerdictBar

    bar = VerdictBar()
    assert all(not button.isEnabled() for button in bar.buttons.values())
    assert not bar.note.isEnabled()

    bar.show_finding(a_finding(session, "G8"), session)
    assert all(button.isEnabled() for button in bar.buttons.values())
    assert bar.note.isEnabled()


# -- changes panel ------------------------------------------------------


def test_the_changes_panel_lists_one_row_per_patch(qt_app, session):
    """Wave 3 (S2.2): each row is a `SendRow` widget with its own Send
    button, not plain item text -- `test_ui_changes_send.py` covers that
    row in depth; this only pins the count and what it names."""
    from wing_parser.ui.changes_panel import ChangesPanel

    session.repair(a_finding(session, "G8"))
    panel = ChangesPanel()
    panel.set_changes(session.changes())

    assert panel.list.count() == 1
    row = panel.list.itemWidget(panel.list.item(0)).label.text()
    assert "POST" in row and "PRE" in row


def test_an_empty_journal_leaves_the_changes_list_empty(qt_app, session):
    from wing_parser.ui.changes_panel import ChangesPanel

    panel = ChangesPanel()
    panel.set_changes(session.changes())
    assert panel.list.count() == 0
    assert panel.undo_button.isEnabled() is False


# -- window -------------------------------------------------------------


def test_the_window_title_marks_an_unsaved_change(qt_app, session):
    from wing_parser.ui.main_window import MainWindow

    window = MainWindow(session)
    assert window.windowTitle().endswith("example-Vu.snap")

    session.repair(a_finding(session, "G8"))
    window._refresh()
    assert window.windowTitle().endswith("*")


def test_the_window_opens_with_no_session_at_all(qt_app):
    from wing_parser.ui.main_window import MainWindow

    window = MainWindow(None)
    assert window.windowTitle() == "wing"
    assert window._save_action.isEnabled() is False
    assert window._undo_action.isEnabled() is False


def test_undo_from_the_window_restores_the_finding_count(qt_app, session):
    from wing_parser.ui.main_window import MainWindow

    window = MainWindow(session)
    session.repair(a_finding(session, "G8"))
    window._refresh()
    assert len(window.session.findings()) == 21

    window.undo()
    assert len(window.session.findings()) == 22
    assert window.windowTitle().endswith("example-Vu.snap")
