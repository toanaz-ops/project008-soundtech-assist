"""The overview page: scene counts and the whole channel list at a glance.

Facts come from `data.summarize` / `data.channel_rows`; this page only
shapes them into cards and a table. No rule knowledge, no styling.
"""

from __future__ import annotations

from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from wing_parser.cli.render import level
from wing_parser.ui import data
from wing_parser.ui.session import Session
from wing_parser.ui.texts import text
from wing_parser.ui.theme import fonts, tokens
from wing_parser.ui.theme.widgets import Caption

COUNT_KEYS = ("channels", "buses", "mains", "matrices", "live", "named", "anomalies")
COLUMNS = ("number", "name", "fader", "kind")


class OverviewPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.count_labels: dict[str, QLabel] = {}
        self.count_legends: dict[str, Caption] = {}
        self._build_count_cards()
        self.channels_model = self._build_channels_table()
        layout = QVBoxLayout(self)
        layout.addWidget(self._counts_box)
        layout.addWidget(self._table_group, stretch=1)
        self.set_session(None)

    def _build_count_cards(self) -> None:
        self._counts_box = QGroupBox(text("overview.counts"))
        grid = QGridLayout(self._counts_box)
        for index, key in enumerate(COUNT_KEYS):
            card = QGroupBox(text(f"overview.{key}"))
            legend = Caption(text(f"overview.{key}"))
            value = QLabel("0")
            value.setFont(fonts.mono_font(tokens.SWITCH_SIZE, medium=True))
            card_layout = QVBoxLayout(card)
            card_layout.addWidget(legend)
            card_layout.addWidget(value)
            grid.addWidget(card, index // 4, index % 4)
            self.count_labels[key] = value
            self.count_legends[key] = legend

    def _build_channels_table(self) -> QStandardItemModel:
        self._table_group = QGroupBox(text("overview.table"))
        model = QStandardItemModel(0, len(COLUMNS), self)
        model.setHorizontalHeaderLabels(
            [text(f"overview.col.{key}") for key in COLUMNS]
        )
        table = QTableView()
        table.setModel(model)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        group_layout = QVBoxLayout(self._table_group)
        group_layout.addWidget(table)
        return model

    def set_session(self, session: Session | None) -> None:
        loaded = session is not None
        summary = data.summarize(session.scene) if loaded else None
        for key in COUNT_KEYS:
            if summary is None:
                value: object = 0
            elif key in summary["counts"]:
                value = summary["counts"][key]
            else:
                value = summary[key]
            self.count_labels[key].setText(str(value))

        self.channels_model.removeRows(0, self.channels_model.rowCount())
        if loaded:
            for row in data.channel_rows(session.scene):
                self.channels_model.appendRow([
                    QStandardItem(str(row.number)),
                    QStandardItem(row.name),
                    QStandardItem(level(row.fader_dB)),
                    QStandardItem(row.kind),
                ])
