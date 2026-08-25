"""The channels page: the full channel list and a read-only detail pane.

Selecting a row fills the pane from `data.channel_detail_rows`. The
pane never edits anything -- repairs belong to the doctor page -- so it
has no signals at all: selection is internal to this widget.
"""

from __future__ import annotations

from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QScrollArea,
    QSplitter,
    QTableView,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtCore import Qt

from wing_parser.cli.render import level
from wing_parser.ui import data
from wing_parser.ui.session import Session
from wing_parser.ui.texts import text

COLUMNS = ("number", "name", "kind", "confidence", "fader", "muted")


class ChannelsPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.rows: tuple[data.ChannelRow, ...] = ()
        self._channels_by_number: dict[int, object] = {}

        self._table_group = QGroupBox(text("channels.table"))
        self.channels_model = QStandardItemModel(0, len(COLUMNS), self)
        self.channels_model.setHorizontalHeaderLabels(
            [text(f"channels.col.{key}") for key in COLUMNS]
        )
        self.table = QTableView()
        self.table.setModel(self.channels_model)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        table_layout = QVBoxLayout(self._table_group)
        table_layout.addWidget(self.table)

        self.detail_title = QLabel(text("channels.detail_empty"))
        self.detail_title.setWordWrap(True)
        self._detail_body = QWidget()
        self._detail_grid = QGridLayout(self._detail_body)
        self._detail_grid.setColumnStretch(1, 1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._detail_body)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(self.detail_title)
        right_layout.addWidget(scroll, stretch=1)

        body = QSplitter(Qt.Orientation.Horizontal)
        body.addWidget(self._table_group)
        body.addWidget(right)
        body.setStretchFactor(0, 3)
        body.setStretchFactor(1, 2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(body)

        self.table.selectionModel().selectionChanged.connect(self._show_detail)
        self.set_session(None)

    def set_session(self, session: Session | None) -> None:
        loaded = session is not None
        self.channels_model.removeRows(0, self.channels_model.rowCount())
        self.rows = data.channel_rows(session.scene) if loaded else ()
        self._channels_by_number = (
            {ch.number: ch for ch in sorted(
                session.scene.channels(), key=lambda c: c.number)}
            if loaded else {}
        )
        for row in self.rows:
            self.channels_model.appendRow([
                QStandardItem(str(row.number)),
                QStandardItem(row.name),
                QStandardItem(row.kind),
                QStandardItem(f"{row.confidence:.2f}"),
                QStandardItem(level(row.fader_dB)),
                QStandardItem(str(row.muted)),
            ])
        if not loaded:
            self.detail_title.setText(text("channels.detail_empty"))
            self._clear_rows()

    def _clear_rows(self) -> None:
        while self._detail_grid.count():
            item = self._detail_grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _show_detail(self) -> None:
        index = self.table.currentIndex()
        row_index = index.row() if index.isValid() else -1
        if not 0 <= row_index < len(self.rows):
            return
        summary_row = self.rows[row_index]
        channel = self._channels_by_number[summary_row.number]
        self.detail_title.setText(
            text("channels.title").format(
                number=channel.number, name=channel.name
            )
        )
        self._clear_rows()
        for grid_row, (label, value) in enumerate(data.channel_detail_rows(channel)):
            name_label = QLabel(label)
            value_label = QLabel(value)
            value_label.setWordWrap(True)
            value_label.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse
            )
            self._detail_grid.addWidget(name_label, grid_row, 0)
            self._detail_grid.addWidget(value_label, grid_row, 1)
