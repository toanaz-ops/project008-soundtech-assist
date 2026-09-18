"""F8/W13: what a live write means for the scene, and the two record
types `live_write.send`/`revert` pass through gate 4.

`wing_parser.net.write` may be imported from exactly one `ui/` module,
`live_write.py` (the allow-list in `tests/test_ui_live_is_read_only.py`) --
this module is not it, so every `SetResult` this file touches is typed
`Any` and read duck-typed (`.matched` / `.readback`) rather than imported.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any

from wing_parser.net.address import osc_address
from wing_parser.net.identity import WingIdentity
from wing_parser.net.jsontypes import is_boolean_shape


@dataclass(frozen=True)
class WriteConfirmation:
    """Gate 4's token (§8.4). `live_write.send` accepts nothing else."""

    host: str
    address: str            # the OSC address, already mapped
    after: Any
    identity: WingIdentity
    desk_before: Any | None


@dataclass(frozen=True)
class SentWrite:
    """One ledger row (F7). `desk_before` is what the DESK held, read live
    at pre-flight -- not the journal's `before`, which is what the FILE
    held when the operator clicked Repair. Revert writes this one back.

    Both spellings of the leaf are carried: `address` is what the packet
    went to, `path` is the dotted document path it came from. Revert needs
    the path back -- to build a `Patch` and to reach `jsontypes` -- and this
    project has no inverse of `osc_address`; inventing one would be a second
    mapper to keep in step with `_place` (W2). Carrying it cannot drift.

    `result` is a `wing_parser.net.write.SetResult`, typed `Any` here for
    the reason in this module's docstring.
    """

    address: str
    path: str
    desk_before: Any | None
    written: Any
    result: Any


def scene_value(parts: Sequence[str], readback: Any) -> Any:
    """F8's one coercion: what a read-back value looks like in the .snap.

    `parts` is the leaf path with `ae_data.` already stripped, exactly as
    `jsontypes.py:48-59` requires -- `is_boolean_shape(["ae_data", ...])`
    answers False in SILENCE, so the shape is never left to a caller.
    Use `net.address.leaf_parts(path)`; nothing else.
    """
    if readback is None:
        return None
    if is_boolean_shape(parts):
        return bool(readback)
    return readback


class Outcome(str, Enum):
    """§2.4: three, never two.

    `write.py:122` computes `matched = readback is not None and (...)`, so
    `matched=False` with `readback=None` means the desk NEVER ANSWERED the
    read-back -- the packet may or may not have landed -- while
    `matched=False` WITH a readback means it answered a different value: a
    clamp. `net/write.py:5-9` records that the console clamps an
    out-of-range value and still answers `OK`, which is why every write
    there is read back; without this distinction the app would show a
    repaired finding the desk had quietly refused.
    """

    SENT = "sent"
    CLAMPED = "clamped"
    NO_REPLY = "no_reply"


def outcome(result: Any) -> Outcome:
    """`result` is a `wing_parser.net.write.SetResult`, duck-typed
    (`.matched` / `.readback`) for the reason in this module's docstring.
    """
    if result.matched:
        return Outcome.SENT
    return Outcome.CLAMPED if result.readback is not None else Outcome.NO_REPLY


def settle_scene(parts: Sequence[str], after: Any, result: Any) -> Any | None:
    """What the scene leaf must hold now, or `None` to leave it alone (F8).

    Matched -> `after`, the value the journal and the dialog both showed --
    NOT `readback`, which `_values_match` (`write.py:84-90`) will have
    called a match while being a different Python type (`bool(1) == True`)
    or a clamped-to-sentinel number (`-999.0` reads back `-144.0`).
    Clamp -> `scene_value(parts, readback)`, so Doctor re-derives against
    the desk's truth. No reply -> `None`: inventing a value for a silent
    desk is the one thing worse than admitting ignorance.

    `result` is a `wing_parser.net.write.SetResult`, duck-typed for the
    reason in this module's docstring.
    """
    if result.matched:
        return after
    if result.readback is None:
        return None
    return scene_value(parts, result.readback)


def plan_write(patch: Any, revert_record: SentWrite | None) -> tuple[str, Any]:
    """The address and the value a write dialog will send (§2.3, W12/W13):
    `revert_record`'s captured desk-before when reverting, else the
    patch's own `after`. `patch` is a `wing_parser.edit.journal.Patch`,
    typed `Any` for the reason in this module's docstring.
    """
    address = osc_address(patch.path)
    after = revert_record.desk_before if revert_record is not None else patch.after
    return address, after


def confirmation_for(host: str, address: str, after: Any, identity: WingIdentity,
                      desk_before: Any | None) -> WriteConfirmation:
    """One place gate 4's token is assembled, so every caller (the
    countdown, and eventually Manual/Immediate) passes the same five
    names in the same order rather than repeating the dataclass call."""
    return WriteConfirmation(host=host, address=address, after=after,
                              identity=identity, desk_before=desk_before)


def desk_now(record: SentWrite) -> Any:
    """W13: what the desk holds NOW, per the original send's read-back.

    After a clamp that differs from `record.written`; when the send got no
    reply at all (`readback is None`) there is nothing truer to fall back
    on than `record.written`, the best knowledge this app has. ONE rule,
    read from here by everything that needs it -- `write_router.route_revert`
    builds a revert `Patch` whose `before` is this, and a second copy of
    the rule is how the countdown came to show "expected: None".

    `record.result` is a `wing_parser.net.write.SetResult`, duck-typed
    (`.readback`) for the reason in this module's docstring.
    """
    readback = record.result.readback
    return record.written if readback is None else readback
