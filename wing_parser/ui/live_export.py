"""Writing a pulled scene to disk: what to call it, and the writing.

Split out of `live_snapshot.py` at that file's 200-line ceiling -- the
name rule at task 11, the Export action itself at task 13, when
`set_session` arrived and the panel crossed the line again. Two halves
of one responsibility; the panel keeps only the signal it emits when a
file really was written.

**Export writes `Session.save_as`** (D3) -- the *patched* document
(`session.py:92-96` -> `_document()` at `:43-44`). The pull-time JSON
`SnapshotPanel.original` holds is Diff's "as pulled" baseline and is
deliberately NOT what this writes: that would drop every repair made
since the pull.

The name rule is worth a function of its own rather than a lump in the
panel: `menus.save_as`
proposes a filename from the same `Session.path` (`menus.py:87-93`) and
needs the same sanitising once `live_controller.suggested_name` has a
seam to split (deferred minor, task 11 review). A pure function over a
path is testable with no desk, no window and no QApplication.

The rule: `suggested_name` (`live_controller.py:159-173`) builds its
stem from `WingIdentity.name` -- whatever somebody typed into the desk
-- so the perfectly ordinary console name "FOH/Monitors" would reach a
Save dialog as a *directory* that does not exist, and the operator would
be shown a path he cannot save to for a reason nothing on screen
explains.
"""

from __future__ import annotations

import re

from PySide6.QtWidgets import QFileDialog

from wing_parser.ui.texts import text

#: Everything a proposed filename may NOT keep. `\w` covers the digits,
#: letters and underscore; the class adds the dot and the dash a
#: timestamped `.snap` name needs. A separator on either platform ("/",
#: "\\") is outside it, which is the point.
_UNSAFE = re.compile(r"[^\w.\-]")


def export_name(path) -> str:
    """A pulled scene's suggested filename, safe to hand a file dialog."""
    return _UNSAFE.sub("_", str(path))


def ask_and_save(parent, session) -> tuple[str | None, str]:
    """Ask where, write there, answer `(path written, line to show)`.

    `path` is None whenever nothing was written -- no scene, a cancelled
    dialog, or a refused write -- so the caller emits its `exported`
    signal on exactly the case that produced a file. A failed write
    leaves `session` untouched and still exportable somewhere else,
    which is why the OSError becomes a line rather than a raise.
    """
    if session is None:
        return None, ""
    name, _ = QFileDialog.getSaveFileName(
        parent, text("console.export_title"),
        export_name(session.path), text("menu.scene_filter"),
    )
    if not name:
        return None, ""
    try:
        session.save_as(name)
    except OSError as exc:
        return None, text("console.export_failed").format(
            file=name, error=exc)
    return name, text("console.exported").format(file=name)
