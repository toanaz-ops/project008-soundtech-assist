"""The Diff page: the live scene against any other scene file.

The left side is always the current session's live scene, so unsaved
journal edits show up here the moment a comparison runs — that is the
point of the page. The right side is whatever file the operator picks.
"""

from __future__ import annotations

import qtawesome as qta
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableView,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QStandardItem, QStandardItemModel

from wing_parser import WingScene
from wing_parser.cli.diffcore import diff_rows
from wing_parser.ui.session import Session
from wing_parser.ui.texts import text

COLUMNS = ("path", "before", "after", "magnitude")

FILTER = "WING scene (*.snap);;All files (*)"


class DiffPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._session: Session | None = None

        self.compare_button = QPushButton(text("diff.compare"))
        self.compare_button.setIcon(qta.icon("fa5s.exchange-alt"))
        self.compare_button.clicked.connect(self._choose_other)
        self.clear_button = QPushButton(text("diff.clear"))
        self.clear_button.setIcon(qta.icon("fa5s.eraser"))
        self.clear_button.clicked.connect(self._clear)

        controls = QHBoxLayout()
        controls.addWidget(self.compare_button)
        controls.addWidget(self.clear_button)
        controls.addStretch()

        self.model = QStandardItemModel(0, len(COLUMNS), self)
        self.model.setHorizontalHeaderLabels(
            [text(f"diff.col.{key}") for key in COLUMNS]
        )
        table = QTableView()
        table.setModel(self.model)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)

        group = QGroupBox(text("diff.table"))
        group_layout = QVBoxLayout(group)
        group_layout.addWidget(table)

        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(controls)
        layout.addWidget(self.error_label)
        layout.addWidget(group, stretch=1)

        self.set_session(None)

    # -- state -----------------------------------------------------------

    def set_session(self, session: Session | None) -> None:
        self._session = session
        self.compare_button.setEnabled(session is not None)
        self._clear()

    def compare_with(self, path: str) -> None:
        """Diff the live scene against `path`.

        A public seam so tests (and future callers) skip the dialog. An
        unreadable file is an error label, never a traceback: the
        operator picks the wrong file sometimes and must stay in the app.
        """
        if self._session is None:
            self.error_label.setText(text("diff.no_session"))
            return
        try:
            other = WingScene.load(path)
        except (OSError, ValueError) as exc:
            self.error_label.setText(text("diff.error").format(error=exc))
            return
        self.error_label.setText("")
        rows = sorted(
            diff_rows(self._session.scene, other),
            key=lambda row: (row.magnitude is None, -(row.magnitude or 0)),
        )
        for row in rows:
            self.model.appendRow([
                QStandardItem(row.path),
                QStandardItem(row.before),
                QStandardItem(row.after),
                QStandardItem(
                    "" if row.magnitude is None else f"{row.magnitude:.2f}"
                ),
            ])

    # -- actions ---------------------------------------------------------

    def _choose_other(self) -> None:
        name, _ = QFileDialog.getOpenFileName(
            self, text("diff.compare"), "", FILTER
        )
        if name:
            self.compare_with(name)

    def _clear(self) -> None:
        self.model.removeRows(0, self.model.rowCount())
        self.error_label.setText("")
