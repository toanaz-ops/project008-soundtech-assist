"""Shared plumbing for the Vocabulary window's Sets and Terms tabs (fix
round 1, I3 -- the two tabs had near-identical copies of this before).

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


def run_dialog_loop(parent, dialog, apply) -> bool:
    """Re-show `dialog` (same instance, its input kept) until `apply`
    succeeds or the operator cancels -- a QDialog's widgets keep their
    state across repeated `exec()` calls, only its own accept/reject
    result resets."""
    while dialog.exec():
        try:
            apply(dialog.result())
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


def folded_haystack(*parts: str) -> str:
    return keywords.fold(" ".join(parts))


def apply_search_filter(table, haystacks: list[str], query: str) -> None:
    """S1: live, case-insensitive, diacritic-folded row filtering. Rows
    are hidden, not removed, so table indices stay stable for every
    other lookup this tab does."""
    folded_query = keywords.fold(query)
    for row, haystack in enumerate(haystacks):
        table.setRowHidden(row, bool(folded_query) and folded_query not in haystack)
