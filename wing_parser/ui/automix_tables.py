"""Result tables and the detail text of the Automix dialog (wave 12).

Display only: nothing here writes a scene or a desk. The engine's
English labels stay English in the cells (parameter names are mixer
nouns); stage names go through `text()`.
"""

from __future__ import annotations

from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QTableView

from wing_parser.ui.elide import MonoDelegate
from wing_parser.ui.texts import text

CHANGE_COLS = ("channel", "source", "stage", "parameter", "before", "after",
               "confidence")
SUGGESTION_COLS = ("channel", "stage", "text")
SKIPPED_COLS = ("channel", "reason")
NEWLINE = chr(10)


def make_table(keys, numeric=(), mono=()):
    model = QStandardItemModel(0, len(keys))
    model.setHorizontalHeaderLabels([text(f"automix.col.{k}") for k in keys])
    table = QTableView()
    table.setModel(model)
    table.setItemDelegate(MonoDelegate(
        numeric_columns=set(numeric), mono_columns=set(mono)))
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
    return table, model


def _rows(model, rows) -> None:
    model.removeRows(0, model.rowCount())
    for cells in rows:
        model.appendRow([QStandardItem(str(c)) for c in cells])


def _stage(stage: str) -> str:
    return text(f"automix.stage.{stage}")


def fill_changes(model, changes, names) -> None:
    """`names` maps a target ("ch.5") to (display name, classifier kind)."""
    _rows(model, ((names.get(c.target, (c.target, ""))[0],
                   names.get(c.target, ("", ""))[1], _stage(c.stage), c.label,
                   c.before, c.after, c.confidence) for c in changes))


def fill_suggestions(model, suggestions) -> None:
    _rows(model, ((s.target, _stage(s.stage), s.text) for s in suggestions))


def fill_skipped(model, skipped) -> None:
    _rows(model, ((s.target, s.reason) for s in skipped))


def detail_text(change, sources: dict) -> str:
    """The why-sentence and one cite + url line per source id."""
    lines = [change.why, "", text("automix.detail.sources")]
    for ident in change.sources:
        info = sources.get(ident, {})
        lines.append(f"{ident}: {info.get('cite', '?')} {info.get('url', '')}".rstrip())
    if not change.sources:
        lines.append(text("automix.detail.no_sources"))
    return NEWLINE.join(lines)
