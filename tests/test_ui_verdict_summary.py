"""Tools > Verdict summary: read-only table per rule, notes on select."""

import pytest

pytest.importorskip("PySide6.QtWidgets")


def _log(tmp_path, monkeypatch, entries):
    from wing_parser.advisory import feedback
    from wing_parser.advisory.models import Finding

    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    for rule, verdict, note in entries:
        finding = Finding(rule_id=rule, layer="L1", severity="warning",
                          target="t", message="m")
        feedback.record(finding, verdict, note, directory=tmp_path)


def test_dialog_rows_and_notes(qt_app, tmp_path, monkeypatch):
    from wing_parser.ui.verdict_summary import VerdictSummaryDialog

    _log(tmp_path, monkeypatch, [("G1", "false-positive", "too loud"),
                                 ("G1", "irrelevant", ""),
                                 ("G2", "correct", "")])
    dialog = VerdictSummaryDialog(None)
    assert dialog.table.model().rowCount() == 2
    dialog.table.selectRow(0)
    assert "too loud" in dialog.notes_view.toPlainText()
    assert dialog.empty_label.isHidden()


def test_dialog_empty_log_shows_guidance(qt_app, tmp_path, monkeypatch):
    from wing_parser.ui.verdict_summary import VerdictSummaryDialog

    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    dialog = VerdictSummaryDialog(None)
    assert dialog.table.model().rowCount() == 0
    assert not dialog.empty_label.isHidden()
    assert dialog.empty_label.text()
