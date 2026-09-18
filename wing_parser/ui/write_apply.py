"""F8/W13: what a write result does to the scene, split out of
`write_router.py` (review round 1, item 3) -- that module was routing
plus applying at 182 of its ruled 160-line budget (task 11's brief),
and these two functions are the "after the result comes back" half:
routing decides WHEN/HOW a packet goes out, this decides what the
SCENE looks like once one has. Deliberately non-Qt: neither function
builds a widget, and `changes_send.badge_text` (a Qt module) is
imported locally inside `apply_result`, exactly as `write_router.py`
already deferred it, so importing this module costs nothing Qt-shaped.
"""

from __future__ import annotations

from wing_parser.net.address import leaf_parts
from wing_parser.ui import live_write
from wing_parser.ui.texts import text


def apply_result(window, patch, record) -> None:
    """F8: matched -> nothing (leaf already holds `after`). Clamp -> a
    second patch to `scene_value(parts, readback)`. No reply -> nothing."""
    from wing_parser.ui.changes_send import badge_text

    value = live_write.settle_scene(
        leaf_parts(patch.path), patch.after, record.result)
    if value is None or value == patch.after:
        return
    window.session.record_value(
        patch.path, value,
        label=badge_text(record), because=patch.because)
    window._refresh()


def apply_revert(window, record) -> None:
    """W13: move the leaf back to what the desk now holds, coerced through
    `scene_value` exactly as F8 does -- so Doctor re-derives and the finding
    REAPPEARS. The honest outcome: the desk really is back in the state the
    rule objects to. `record.written` is this revert's OWN target (the
    original ledger row's `desk_before`, captured at send time) -- not
    `record.desk_before`, which is what the desk held right before THIS
    write went out and plays the same role `patch.after` plays in
    `apply_result` above. The original `Patch` is left alone; Undo is still
    the file-side door, and silently dropping a patch because a desk write
    was reverted would conflate the two."""
    value = live_write.settle_scene(
        leaf_parts(record.path), record.written, record.result)
    if value is None:
        return
    window.session.record_value(
        record.path, value,
        label=text("console.write.reverted").format(
            readback=record.result.readback),
        because="revert")
    window._refresh()
