"""An add/remove-row table of mappings: the Sources and Media editors.

Cells are text, except the columns named in `choices`, which are combo
boxes. `rows()` drops blank cells and turns an all-digit `year` back into
the integer the YAML files carry, so an untouched row round-trips.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from wing_parser.ui.texts import text


class DictTable(QWidget):
    changed = Signal()

    def __init__(self, columns: tuple[str, ...], choices: dict[str, tuple[str, ...]] | None = None,
                 defaults: dict | None = None) -> None:
        super().__init__()
        self.columns = columns
        self.choices = choices or {}
        self.defaults = defaults or {}
        self.table = QTableWidget(0, len(columns))
        self.table.setHorizontalHeaderLabels([text(f"library.col.{c}") for c in columns])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemChanged.connect(lambda _item: self.changed.emit())
        self.add_button = QPushButton(text("library.add_row"))
        self.remove_button = QPushButton(text("library.remove_row"))
        self.add_button.clicked.connect(lambda: self.add_row())
        self.remove_button.clicked.connect(self.remove_selected)
        buttons = QHBoxLayout()
        buttons.addWidget(self.add_button)
        buttons.addWidget(self.remove_button)
        buttons.addStretch(1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.table, stretch=1)
        layout.addLayout(buttons)

    def add_row(self, values: dict | None = None) -> int:
        values = {**self.defaults, **(values or {})}
        row = self.table.rowCount()
        self.table.blockSignals(True)
        self.table.insertRow(row)
        for col, name in enumerate(self.columns):
            value = "" if values.get(name) is None else str(values[name])
            if name in self.choices:
                combo = QComboBox()
                combo.addItems(self.choices[name])
                if value in self.choices[name]:
                    combo.setCurrentText(value)
                combo.currentTextChanged.connect(lambda _t: self.changed.emit())
                self.table.setCellWidget(row, col, combo)
            else:
                self.table.setItem(row, col, QTableWidgetItem(value))
        self.table.blockSignals(False)
        self.changed.emit()
        return row

    def remove_selected(self) -> None:
        rows = sorted({i.row() for i in self.table.selectedIndexes()}, reverse=True)
        for row in rows:
            self.table.removeRow(row)
        self.changed.emit()

    def set_cell(self, row: int, name: str, value: str) -> None:
        col = self.columns.index(name)
        widget = self.table.cellWidget(row, col)
        if isinstance(widget, QComboBox):
            widget.setCurrentText(value)
        else:
            self.table.setItem(row, col, QTableWidgetItem(value))

    def set_rows(self, rows: list[dict]) -> None:
        self.table.setRowCount(0)
        for row in rows:
            self.add_row({**{c: "" for c in self.defaults}, **row})

    def _cell(self, row: int, col: int) -> str:
        widget = self.table.cellWidget(row, col)
        if isinstance(widget, QComboBox):
            return widget.currentText().strip()
        item = self.table.item(row, col)
        return item.text().strip() if item is not None else ""

    def rows(self) -> list[dict]:
        out = []
        for row in range(self.table.rowCount()):
            data = {name: self._cell(row, col) for col, name in enumerate(self.columns)}
            data = {k: v for k, v in data.items() if v}
            if data.get("year", "").isdigit():
                data["year"] = int(data["year"])
            out.append(data)
        return out
