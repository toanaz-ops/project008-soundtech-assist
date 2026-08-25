"""The routing page: the routing summary table and unclassified channels.

Facts come from `data.routing_view`; this page puts the summary pairs
in a table on top and anything the classifier could not place in a list
underneath. No rule knowledge, no styling.
"""

from __future__ import annotations

from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QGroupBox,
    QListWidget,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from wing_parser.ui import data
from wing_parser.ui.session import Session
from wing_parser.ui.texts import text

COLUMNS = ("label", "value")


class RoutingPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.summary_model = QStandardItemModel(0, len(COLUMNS), self)
        self.summary_model.setHorizontalHeaderLabels(
            [text(f"routing.col.{key}") for key in COLUMNS]
        )
        summary_table = QTableView()
        summary_table.setModel(self.summary_model)
        summary_table.verticalHeader().setVisible(False)
        summary_table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        summary_group = QGroupBox(text("routing.summary"))
        summary_layout = QVBoxLayout(summary_group)
        summary_layout.addWidget(summary_table)

        self.unclassified_list = QListWidget()
        unclassified_group = QGroupBox(text("routing.unclassified"))
        unclassified_layout = QVBoxLayout(unclassified_group)
        unclassified_layout.addWidget(self.unclassified_list)

        body = QSplitter(Qt.Orientation.Vertical)
        body.addWidget(summary_group)
        body.addWidget(unclassified_group)
        body.setStretchFactor(0, 3)
        body.setStretchFactor(1, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(body)

        self.set_session(None)

    def set_session(self, session: Session | None) -> None:
        loaded = session is not None
        pairs, unclassified = data.routing_view(session.scene) if loaded else ([], [])

        self.summary_model.removeRows(0, self.summary_model.rowCount())
        for label, value in pairs:
            self.summary_model.appendRow([
                QStandardItem(label),
                QStandardItem(str(value)),
            ])

        self.unclassified_list.clear()
        for name in unclassified:
            self.unclassified_list.addItem(name)
