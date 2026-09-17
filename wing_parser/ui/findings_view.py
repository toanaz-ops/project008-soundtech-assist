"""The findings table plus its severity and layer filters.

The layer filter earns its place: a finding's layer says whether a
shipped base rule fired or one of ToanAZ's own principles did, and that
changes how the finding should be read. It is invisible in the CLI's
default output.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QTableView,
    QVBoxLayout,
    QWidget,
)

from wing_parser.advisory.models import LAYERS, SEVERITIES, Finding
from wing_parser.ui.elide import MonoDelegate
from wing_parser.ui.findings_model import FindingsModel
from wing_parser.ui.texts import text

ALL = "all"


class FindingsView(QWidget):
    selected = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._all: list[Finding] = []
        self._model = FindingsModel()

        self._severity = QComboBox()
        self._severity.addItems([ALL, *SEVERITIES])
        self._layer = QComboBox()
        self._layer.addItems([ALL, *LAYERS])
        for box in (self._severity, self._layer):
            box.currentTextChanged.connect(self._apply_filters)

        self._count = QLabel("")

        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.selectionModel().selectionChanged.connect(self._emit_selection)
        self._table.verticalHeader().setVisible(False)
        # targets are identifiers cut in the middle, tail protected; the
        # message is prose, cut with Qt's own middle elision.
        self._table.setItemDelegate(MonoDelegate(prose_columns={3}))
        header = self._table.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)

        bar = QHBoxLayout()
        bar.addWidget(QLabel(text("findings.severity")))
        bar.addWidget(self._severity)
        bar.addWidget(QLabel(text("findings.layer")))
        bar.addWidget(self._layer)
        bar.addStretch()
        bar.addWidget(self._count)

        layout = QVBoxLayout(self)
        layout.addLayout(bar)
        layout.addWidget(self._table)

    def set_findings(self, findings: list[Finding]) -> None:
        self._all = list(findings)
        self._apply_filters()

    def select_first(self) -> None:
        """Programmatic: light row 0 without announcing it as a click."""
        if not self._model.rowCount():
            return
        selection = self._table.selectionModel()
        was_blocked = selection.blockSignals(True)
        self._table.selectRow(0)
        selection.blockSignals(was_blocked)

    def visible_findings(self) -> list[Finding]:
        severity, layer = self._severity.currentText(), self._layer.currentText()
        return [
            finding
            for finding in self._all
            if (severity == ALL or finding.severity == severity)
            and (layer == ALL or finding.layer == layer)
        ]

    def _apply_filters(self) -> None:
        shown = self.visible_findings()
        self._model.set_findings(shown)
        total = len(self._all)
        self._count.setText(
            f"{total} findings" if len(shown) == total
            else f"{len(shown)} of {total} findings"
        )
        self._table.resizeColumnsToContents()

    def _emit_selection(self) -> None:
        rows = self._table.selectionModel().selectedRows()
        self.selected.emit(self._model.finding_at(rows[0].row()) if rows else None)
