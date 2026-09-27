"""Write-path plumbing shared by the Vocabulary window's Sets and Terms
tabs (fix round 1, I3). Widget construction, search, and broken-set
display live in `vocabulary_tab_widgets.py` (split out in fix round 2 to
stay under the 200-line house-style ceiling).

`run_dialog_loop`/`write_or_report` both treat `ValueError` and `OSError`
the same way: `UnknownKindError`/`UnknownSetError`/`CycleError` are all
`ValueError` subclasses (vocabulary_store.py), `put_term`'s own
empty-term check is a plain `ValueError`, and `check_new_key` below
raises a plain `ValueError` too -- one `except` in each helper covers
every save-time failure a tab can produce. `OSError` is the write
hitting disk trouble, reported the same way `SettingsDialog.save()`
already does for `provider.yaml`.
"""

from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from wing_parser.showcontext.ingest import keywords
from wing_parser.ui.texts import text


class UserDeclined(Exception):
    """Raised by an `apply` callback passed to `run_dialog_loop` to
    reshow the same dialog with NO additional message box -- for when
    the operator already answered an inline confirmation (fix round 2:
    declining to drop an unknown kind). Distinct from `ValueError`/
    `OSError` so `run_dialog_loop` does not also pop a redundant warning
    on top of the confirmation the operator just answered."""


def run_dialog_loop(parent, dialog, apply) -> bool:
    """Re-show `dialog` (same instance, its input kept) until `apply`
    succeeds or the operator cancels -- a QDialog's widgets keep their
    state across repeated `exec()` calls, only its own accept/reject
    result resets."""
    while dialog.exec():
        try:
            apply(dialog.values())
        except UserDeclined:
            continue
        except (ValueError, OSError) as exc:
            QMessageBox.warning(parent, text("vocabulary.title"), _message(exc))
            continue
        return True
    return False


def write_or_report(parent, action) -> bool:
    """Same failure handling as `run_dialog_loop`, for an action with no
    dialog to re-show (Delete, Reset, a broken-reference fix)."""
    try:
        action()
    except (ValueError, OSError) as exc:
        QMessageBox.warning(parent, text("vocabulary.title"), _message(exc))
        return False
    return True


def _message(exc: Exception) -> str:
    if isinstance(exc, OSError):
        return text("vocabulary.write_failed").format(error=exc)
    return str(exc)


def check_new_key(key: str, existing_identities) -> None:
    """Add-only validation (fix round 1, I2). Edit disables the name
    field, so it never calls this -- its replace semantics (a save under
    the same key overwrites) are unchanged."""
    folded = keywords.fold(key)
    if not folded:
        raise ValueError(text("vocabulary.name_required"))
    if folded in existing_identities:
        raise ValueError(text("vocabulary.name_exists"))


def confirm_kind_drop(parent, dropped: tuple[str, ...]) -> None:
    """Fix round 2, item 4: an edit that would silently drop a
    hand-edited kind the dialog cannot even display (it only lists
    `known_kinds`) must be confirmed first, naming what would be
    dropped. Raises `UserDeclined` on No/Esc/close -- the caller (a
    `run_dialog_loop` `apply`) then reshows the SAME dialog, nothing
    written, "Cancel keeps the entry unchanged"."""
    if not dropped:
        return
    answer = QMessageBox.question(
        parent, text("vocabulary.title"),
        text("vocabulary.kind_drop_confirm").format(kinds=", ".join(dropped)),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    if answer != QMessageBox.StandardButton.Yes:
        raise UserDeclined()


def confirm_overwrite(parent, name: str) -> bool:
    """M3: Record/Ignore on the Terms step writes through `put_term`,
    which replaces any existing entry under the same folded key with no
    warning of its own -- a shortened key can silently collide with an
    already-taught term (default or manual). Same default-to-No idiom as
    `confirm_delete`, naming the entry that would be overwritten."""
    answer = QMessageBox.question(
        parent, text("vocabulary.title"), text("vocabulary.overwrite_confirm").format(name=name),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return answer == QMessageBox.StandardButton.Yes


def confirm_delete(parent, name: str) -> bool:
    """Fix round 2, item 5: Delete must name the entry and default to
    No."""
    answer = QMessageBox.question(
        parent, text("vocabulary.title"), text("vocabulary.delete_confirm").format(name=name),
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        QMessageBox.StandardButton.No,
    )
    return answer == QMessageBox.StandardButton.Yes
