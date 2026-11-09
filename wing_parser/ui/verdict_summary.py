"""Tools > Verdict summary (wave 7): the verdict log rolled up per rule.

Read-only. One row per rule; selecting a row shows that rule's notes. A
rule flagged Candidate has drawn enough rejections that the operator may
want to write a principle or `supersedes` for it -- the dialog never edits
a rule itself.
"""

from __future__ import annotations

from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QDialog, QLabel, QPlainTextEdit, QTableView, QVBoxLayout,
)

from wing_parser.advisory.feedback import read_log
from wing_parser.advisory.feedback_report import build_report
from wing_parser.ui.elide import MonoDelegate
from wing_parser.ui.texts import text

COLUMNS = ("rule", "layer", "correct", "false_positive", "irrelevant",
           "last", "candidate")
NUMERIC = {2, 3, 4}
MONO = {0, 5}


class VerdictSummaryDialog(QDialog):
    def __init__(self, parent=None, directory=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(text("verdicts.title"))
        self.resize(900, 520)
        self._rows = build_report(read_log(directory))

        self.empty_label = QLabel(text("verdicts.empty"))
        self.empty_label.setWordWrap(True)
        self.model = QStandardItemModel(0, len(COLUMNS), self)
        self.model.setHorizontalHeaderLabels(
            [text(f"verdicts.col.{key}") for key in COLUMNS])
        self.table = QTableView()
        self.table.setModel(self.model)
        self.table.setItemDelegate(
            MonoDelegate(numeric_columns=NUMERIC, mono_columns=MONO))
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.notes_view = QPlainTextEdit()
        self.notes_view.setReadOnly(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.empty_label)
        layout.addWidget(self.table, stretch=3)
        layout.addWidget(QLabel(text("verdicts.notes_heading")))
        layout.addWidget(self.notes_view, stretch=2)

        for row in self._rows:
            self.model.appendRow([QStandardItem(v) for v in (
                row.rule_id, row.layer, str(row.correct),
                str(row.false_positive), str(row.irrelevant), row.last[:16],
                text("verdicts.candidate_yes") if row.candidate else "")])
        self.empty_label.setVisible(not self._rows)
        self.table.setVisible(bool(self._rows))
        self.table.selectionModel().currentRowChanged.connect(self._row_changed)

    def _row_changed(self, current, _previous) -> None:
        index = current.row()
        if not 0 <= index < len(self._rows):
            self.notes_view.setPlainText("")
            return
        notes = self._rows[index].notes
        self.notes_view.setPlainText(
            "\n".join(f"- {note}" for note in notes) if notes
            else text("verdicts.no_notes"))


def open_verdict_summary(parent, directory=None) -> None:
    VerdictSummaryDialog(parent, directory).exec()
