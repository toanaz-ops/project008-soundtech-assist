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
from wing_parser.ui import token_labels
from wing_parser.ui.texts import text
from wing_parser.ui.theme import tokens

ALL = "all"


class FindingsView(QWidget):
    selected = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._all: list[Finding] = []
        self._model = FindingsModel()

        # Display text is translated; the raw token is the itemData and
        # the only thing filtering ever compares.
        self._severity = self._token_box("severity", SEVERITIES)
        self._layer = self._token_box("layer", LAYERS)
        for box in (self._severity, self._layer):
            box.currentIndexChanged.connect(self._apply_filters)

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

    @staticmethod
    def _token_box(kind: str, tokens) -> QComboBox:
        box = QComboBox()
        box.addItem(token_labels.all_label(), ALL)
        for token in tokens:
            box.addItem(token_labels.label(kind, token), token)
        return box

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
        severity, layer = self._severity.currentData(), self._layer.currentData()
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
            text("findings.count_all").format(total=total)
            if len(shown) == total
            else text("findings.count_some").format(
                shown=len(shown), total=total)
        )
        self._table.resizeColumnsToContents()
        # `MonoDelegate` paints inside `width - 2 * unit`, but the default
        # size hint knows nothing of that pad: a translated cell ("cơ bản")
        # wider than its header was elided. Give every fixed column the pad.
        pad = tokens.METRICS["unit"] * 2
        for column in range(self._model.columnCount()):
            if column != 3:                 # the stretch (message) column
                self._table.setColumnWidth(
                    column, self._table.columnWidth(column) + pad)

    def _emit_selection(self) -> None:
        rows = self._table.selectionModel().selectedRows()
        self.selected.emit(self._model.finding_at(rows[0].row()) if rows else None)
