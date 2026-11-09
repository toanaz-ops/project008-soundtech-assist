"""Result tables of the draft-rule dry-run dialog (wave 8): the per-scene
summary and the per-finding detail. Display only; nothing is written."""

from __future__ import annotations

from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QTableView

from wing_parser.ui.elide import MonoDelegate
from wing_parser.ui.texts import text

SUMMARY_COLS = ("scene", "before", "after", "added", "removed", "error")
DETAIL_COLS = ("scene", "change", "rule", "target", "message")
PLUS, MINUS = "+", "-"


def make_table(keys, numeric, mono, single=False):
    model = QStandardItemModel(0, len(keys))
    model.setHorizontalHeaderLabels([text(f"dryrun.col.{k}") for k in keys])
    table = QTableView()
    table.setModel(model)
    table.setItemDelegate(
        MonoDelegate(numeric_columns=numeric, mono_columns=mono))
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
    if single:
        table.setSelectionMode(QTableView.SelectionMode.SingleSelection)
    return table, model


def fill_summary(model: QStandardItemModel, results) -> None:
    model.removeRows(0, model.rowCount())
    for res in results:
        d = res.delta
        cells = [res.path.name,
                 str(d.before) if d else "", str(d.after) if d else "",
                 PLUS + str(len(d.added)) if d else "",
                 MINUS + str(len(d.removed)) if d else "",
                 res.error or ""]
        model.appendRow([QStandardItem(c) for c in cells])


def fill_detail(model: QStandardItemModel, results, only) -> None:
    model.removeRows(0, model.rowCount())
    for i, res in enumerate(results):
        if res.delta is None or (only is not None and i != only):
            continue
        for sign, found in ((PLUS, res.delta.added),
                            (MINUS, res.delta.removed)):
            for f in found:
                model.appendRow([QStandardItem(v) for v in (
                    res.path.name, sign, f.rule_id, f.target, f.message)])


def changes_nothing(results) -> bool:
    ran = [r for r in results if r.delta is not None]
    return bool(ran) and all(
        not r.delta.added and not r.delta.removed for r in ran)
