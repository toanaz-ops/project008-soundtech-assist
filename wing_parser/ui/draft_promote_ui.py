"""Promote button for the draft dry-run dialog (wave 9).

Confirm -> `draft_promote.promote` -> result box -> reload the draft list
-> `on_promoted`. Strings are looked up at call time.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QMessageBox, QPushButton

from wing_parser.advisory import draft_dry_run as dd
from wing_parser.advisory import draft_promote
from wing_parser.ui.texts import text


def make_button(dialog) -> QPushButton:
    button = QPushButton(text("dryrun.promote"))
    button.setEnabled(False)
    button.clicked.connect(lambda: promote_clicked(dialog))
    return button


def can_promote(load) -> bool:
    return load is not None and not load.error and load.promotable


def reload_drafts(dialog) -> None:
    dialog.combo.blockSignals(True)
    dialog.combo.clear()
    for path in dd.list_drafts(dialog._directory):
        dialog.combo.addItem(path.name, str(path))
    dialog.combo.blockSignals(False)
    dialog._draft_changed()


def promote_clicked(dialog) -> None:
    load = dialog._load
    if not can_promote(load):
        return
    yes = QMessageBox.StandardButton.Yes
    answer = QMessageBox.question(
        dialog, text("dryrun.promote_title"),
        text("dryrun.promote_confirm").format(name=Path(load.path).name))
    if answer != yes:
        return
    result = draft_promote.promote(load.path, dialog._directory)
    if not result.ok:
        QMessageBox.warning(
            dialog, text("dryrun.promote_title"),
            text("dryrun.promote_failed").format(error=result.error))
        return
    note = (text("dryrun.promote_warn").format(error=result.error)
            if result.error else "")
    QMessageBox.information(
        dialog, text("dryrun.promote_title"),
        text("dryrun.promote_done").format(
            ids=", ".join(result.rule_ids), backup=result.backup) + note)
    reload_drafts(dialog)
    callback = getattr(dialog, "_on_promoted", None)
    if callback is not None:
        try:
            callback()
        except Exception as exc:  # the write already succeeded
            QMessageBox.critical(dialog, text("dryrun.promote_title"), str(exc))
