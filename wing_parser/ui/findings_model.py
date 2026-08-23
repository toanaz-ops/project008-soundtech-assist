"""A table model over the advisory findings.

Sorted severity-first and then by rule and target, deterministically.
The list is rebuilt from scratch after every repair, and one that
reshuffled under the cursor each time would be unusable.
"""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from wing_parser.advisory.models import Finding

COLUMNS: tuple[str, ...] = ("Severity", "Rule", "Target", "Message", "Layer")

# Errors first: an error is a routing mistake that will be audible.
_RANK = {"error": 0, "warning": 1, "info": 2}


def sort_key(finding: Finding) -> tuple:
    return (_RANK.get(finding.severity, 9), finding.rule_id, finding.target)


class FindingsModel(QAbstractTableModel):
    def __init__(self) -> None:
        super().__init__()
        self._rows: list[Finding] = []

    def set_findings(self, findings: list[Finding]) -> None:
        self.beginResetModel()
        self._rows = sorted(findings, key=sort_key)
        self.endResetModel()

    def finding_at(self, row: int) -> Finding:
        return self._rows[row]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        finding = self._rows[index.row()]
        return (
            finding.severity,
            finding.rule_id,
            finding.target,
            finding.message,
            finding.layer,
        )[index.column()]

    def headerData(
        self,
        section: int,
        orientation: Qt.Orientation,
        role: int = Qt.ItemDataRole.DisplayRole,
    ):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation != Qt.Orientation.Horizontal:
            return None
        return COLUMNS[section]
