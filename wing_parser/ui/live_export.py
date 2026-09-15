"""What to call a pulled scene on disk. No Qt, four lines of rule.

Split out of `live_snapshot.py` at that file's 200-line ceiling, and
worth its own module rather than a lump in the panel: `menus.save_as`
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

#: Everything a proposed filename may NOT keep. `\w` covers the digits,
#: letters and underscore; the class adds the dot and the dash a
#: timestamped `.snap` name needs. A separator on either platform ("/",
#: "\\") is outside it, which is the point.
_UNSAFE = re.compile(r"[^\w.\-]")


def export_name(path) -> str:
    """A pulled scene's suggested filename, safe to hand a file dialog."""
    return _UNSAFE.sub("_", str(path))
