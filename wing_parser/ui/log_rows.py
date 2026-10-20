"""How the Log page shapes a show or a write into list and table cells.

Split out of `log_page.py` by responsibility: that module wires widgets and
buttons; this one only turns `writelog` records into display text. Every
string is looked up at use time, so a language set before the page is built
(or a test switching language) is honoured.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QStandardItem
from PySide6.QtWidgets import QListWidgetItem

from wing_parser.ui.texts import text
from wing_parser.writelog import COLUMNS, OUTCOME_BADGE

NUMERIC = {5, 6, 7, 8}
MONO = {0, 2, 4}


def show_item(show) -> QListWidgetItem:
    """One left-pane row: code, name, venue, then dates and counts."""
    head = text("log.show_row").format(
        code=show.code, name=show.show or "", venue=show.venue or "")
    counts = text("log.show_counts").format(
        first=show.first_ts[:10], last=show.last_ts[:10], writes=show.writes,
        sent=show.sent, clamped=show.clamped, no_reply=show.no_reply)
    item = QListWidgetItem(f"{head}\n{counts}")
    item.setData(Qt.ItemDataRole.UserRole, show.code)
    return item


def _cell(value) -> QStandardItem:
    return QStandardItem("" if value is None else str(value))


def entry_row(entry) -> list[QStandardItem]:
    """One right-pane row, in `COLUMNS` order."""
    desk = entry.desk or {}
    kind = (text(f"log.report.kind.{entry.kind}")
            if entry.kind in ("repair", "revert") else entry.kind)
    outcome = (text(f"log.outcome.{entry.outcome}")
               if entry.outcome in OUTCOME_BADGE
               else entry.outcome)
    return [_cell(v) for v in (
        entry.ts, desk.get("name") or desk.get("serial"), entry.address,
        entry.label, entry.finding, entry.file_before, entry.desk_before,
        entry.written, entry.readback, outcome, kind)]
