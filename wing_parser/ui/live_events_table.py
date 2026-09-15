"""The watch's own table: time, strip, key, before -> after.

**Not `ChangesPanel` (D8).** Reusing it was the obvious move and is
ruled out: `ChangesPanel.set_changes` takes `edit.journal.Patch` tuples
(`changes_panel.py:13,30-36`), and its dock's visibility is bound to
`session.dirty` (`main_window.py:179-180` -- the spec and the task
brief both say :175-176, which is where that pair sat before task 11
added three lines above it; re-read 2026-09-16). A watch event is not an
unsaved edit -- nobody made it, and saving the scene does not clear it
-- so feeding one into that dock would make the dock mean two things at
once. This table is the other meaning, and owns nothing else: it holds
no transport, no state and no worker, which is why it fits beside
`LiveEventsView` rather than inside it.

Its one judgement is the fallback in `append`: a blank `Change.label` is
ordinary -- `factory-scene.snap` names no channel at all -- so an
unnamed strip shows its address rather than a gap, which is the same
call `net/watch/events.py:30-33` makes for the CLI's own line.
"""

from __future__ import annotations

from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QTableView

from wing_parser.ui.elide import MonoDelegate
from wing_parser.ui.texts import text

COLUMNS = ("time", "strip", "key", "change")


class EventTable(QTableView):
    """One row per `Change`, in the order the poller yielded them."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.model = QStandardItemModel(0, len(COLUMNS), self)
        self.model.setHorizontalHeaderLabels(
            [text(f"console.col.{column}") for column in COLUMNS]
        )
        self.setModel(self.model)
        # time: mono and right-aligned, so figures compare down the
        # page. key and change carry technical text -- the face, but
        # their left edge.
        self.setItemDelegate(MonoDelegate(numeric_columns={0},
                                          mono_columns={2, 3}))
        self.verticalHeader().setVisible(False)
        self.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)

    def append(self, change) -> None:
        """One `Change` -> one row. See this module's docstring for the
        blank-label fallback."""
        self.model.appendRow([
            QStandardItem(
                text("console.event_time").format(seconds=change.elapsed)),
            QStandardItem(change.label or change.strip),
            QStandardItem(change.key),
            QStandardItem(text("console.event_change").format(
                before=change.before, after=change.after)),
        ])

    def clear_events(self) -> None:
        """Empty the table for a new session. Only Start calls this: a
        watch that ended keeps what it collected on screen."""
        self.model.removeRows(0, self.model.rowCount())
