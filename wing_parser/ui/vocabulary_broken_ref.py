"""Terms-tab-only: fixing a term's reference to a set that no longer
exists (fix round 1, S2). Neither action may be silent: both go through
`vocabulary_tab_support.write_or_report` and only ever touch the ONE
broken name the operator picked the row for, leaving every other kind or
set already on the term untouched.

This is also the fix for "today's silent drop-on-Edit must go": the
Terms tab now disables Edit outright for a row with a genuinely broken
reference (see `vocabulary_terms_tab.py`'s `_refresh_buttons`), so the
only way to touch that reference is through one of these two explicit,
named actions -- Edit's own dialog never gets a chance to silently omit
a set name it was never given in its known-sets list.
"""

from __future__ import annotations

from PySide6.QtWidgets import QInputDialog, QMessageBox

from wing_parser.ui import vocabulary_tab_support as support
from wing_parser.ui.texts import text


def _replace_term_sets(vocabulary, entry, new_sets) -> None:
    vocabulary.put_term(entry.key, kinds=entry.kinds, sets=new_sets,
                        ignore=entry.ignore, match=entry.match)


def pick_another_set(parent, vocabulary, entry, broken_name, on_changed) -> None:
    choices = tuple(s.key for s in vocabulary.sets())
    if not choices:
        QMessageBox.warning(parent, text("vocabulary.title"), text("vocabulary.no_sets_to_pick"))
        return
    chosen, ok = QInputDialog.getItem(
        parent, text("vocabulary.title"),
        text("vocabulary.pick_set_prompt").format(name=broken_name),
        choices, 0, False,
    )
    if not ok:
        return
    new_sets = tuple(chosen if s == broken_name else s for s in entry.sets)
    if support.write_or_report(parent, lambda: _replace_term_sets(vocabulary, entry, new_sets)):
        on_changed()


def drop_reference(parent, vocabulary, entry, broken_name, on_changed) -> None:
    new_sets = tuple(s for s in entry.sets if s != broken_name)
    if support.write_or_report(parent, lambda: _replace_term_sets(vocabulary, entry, new_sets)):
        on_changed()
