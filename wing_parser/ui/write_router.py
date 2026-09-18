"""What happens to a repair between the click and the ledger row (F3).

Three levels, one entry point. Manual stops here -- the journal row's own
Send button resumes it, and that button opens the countdown too, so Manual
has one control that always means the same thing. Delayed opens the
countdown. Immediate reads the desk once, then writes.

**Immediate still reads first.** The ledger records the desk-live value
captured BEFORE the write (F7), and without it Revert would have nothing to
write back. That read runs on `ImmediateWrite`'s own `CallRunner` (W5), the
same rule the two dialogs follow, because the Console page's runner is
legitimately busy during a watch (`workers.py:112-113`).

A module of its own because nowhere else would take it: `main_window.py`
gets four lines this whole wave, `console_page.py` and `live_controller.py`
may not grow at all (W7), `changes_send.py` is budgeted at 120 for the Send
button and its badges, and `live_wiring.py` already carries the gate.

Imports `WriteJob`/`GateClosed` from `write_gate.py` directly, not from
`live_wiring` (which re-exports them): `live_wiring.install_write_gate`
calls into this module, so importing back from `live_wiring` at module
level would be a cycle waiting to happen.
"""

from __future__ import annotations

from PySide6.QtCore import QObject

from wing_parser.net.address import osc_address
from wing_parser.ui import live_write
from wing_parser.ui.apply_level import ApplyLevel
from wing_parser.ui.write_arm_dialog import arm_now
from wing_parser.ui.write_delay_dialog import DelayedWriteDialog
from wing_parser.ui.write_gate import GateClosed, WriteJob
from wing_parser.ui.workers import CallRunner


def _record(path, desk_before, written, result) -> live_write.SentWrite:
    return live_write.SentWrite(address=osc_address(path), path=path,
                                desk_before=desk_before, written=written,
                                result=result)


class ImmediateWrite(QObject):
    """Read the desk once, then write. No dialog -- that is the trade F3
    buys, and exactly why Immediate cannot be reached without arming and
    why the selector falls back to Manual the moment the connection drops.

    Keeps itself referenced through its `CallRunner` parent chain until the
    write settles; the caller does not have to hold it.
    """

    def __init__(self, gate, patch, after, *, transport=None, timeout=None,
                 on_sent=None, on_error=None, parent=None) -> None:
        super().__init__(parent or gate)
        self._gate = gate
        self._patch = patch
        self._after = after
        self._address = osc_address(patch.path)
        self._on_sent = on_sent or (lambda _p, _r: None)
        self._on_error = on_error or (lambda _e: None)
        self._runner = CallRunner(self)
        self._runner.start(
            "connect", (transport or live_write.REAL).read,
            gate.host(), patch.path,
            on_success=self._write, on_failure=lambda _exc: self._write(None),
            timeout=timeout,
        )

    def _write(self, desk_before) -> None:
        if not self._gate.ready():                          # GATE 4 (§8.4)
            from wing_parser.ui.texts import text
            self._on_error(GateClosed(text("console.write.gate_closed")))
            return
        self._desk_before = desk_before
        self._gate.submit(WriteJob(
            live_write.WriteConfirmation(
                host=self._gate.host(), address=self._address,
                after=self._after, identity=self._gate.arm.identity,
                desk_before=desk_before),
            self._done, self._on_error,
        ))

    def _done(self, result) -> None:
        self._on_sent(self._patch,
                      _record(self._patch.path, self._desk_before,
                              self._after, result))


def route_repair(gate, patch, delay, parent=None, *, transport=None, timeout=None,
                 on_sent=None, on_error=None):
    """Apply `patch` to the desk at the gate's CURRENT level (F3).

    Returns the `DelayedWriteDialog` when one was opened, else `None`.
    """
    level = gate.arm.level
    if level is ApplyLevel.MANUAL:
        return None                    # the journal row's Send resumes it
    if not arm_now(gate, parent, transport=transport, timeout=timeout):
        return None
    if level is ApplyLevel.IMMEDIATE:
        ImmediateWrite(gate, patch, patch.after, transport=transport,
                       timeout=timeout, on_sent=on_sent, on_error=on_error,
                       parent=parent)
        return None
    return _countdown(gate, patch, patch.after, delay, parent,
                      transport=transport, timeout=timeout,
                      on_sent=on_sent, on_error=on_error)


def route_revert(gate, record, delay, parent=None, *, transport=None, timeout=None,
                 on_sent=None, on_error=None, on_cancelled=None):
    """F7: write a ledger row's captured desk-before value back, through the
    CURRENT level -- Immediate at once, Delayed and Manual via the
    countdown. Manual reverts through the countdown too, so a revert is
    never a silent packet."""
    from wing_parser.edit.journal import Patch

    if not arm_now(gate, parent, transport=transport, timeout=timeout):
        return None
    patch = Patch(path=record.path, before=record.result.readback,
                  after=record.desk_before, because="revert", label="Revert")
    if gate.arm.level is ApplyLevel.IMMEDIATE:
        ImmediateWrite(gate, patch, record.desk_before, transport=transport,
                       timeout=timeout, on_sent=on_sent, on_error=on_error,
                       parent=parent)
        return None
    return _countdown(gate, patch, record.desk_before, delay, parent,
                      transport=transport, timeout=timeout, on_sent=on_sent,
                      on_error=on_error, on_cancelled=on_cancelled,
                      revert_record=record)


def _countdown(gate, patch, after, delay, parent, *, transport, timeout,
               on_sent=None, on_error=None, on_cancelled=None,
               revert_record=None):
    dialog = DelayedWriteDialog(gate, patch, delay, parent, transport=transport,
                                timeout=timeout, revert_record=revert_record)
    if on_sent is not None:
        dialog.applied.connect(lambda result: on_sent(
            patch, _record(patch.path, dialog.desk_before, after, result)))
    if on_error is not None:
        dialog.failed.connect(on_error)
    if on_cancelled is not None:
        dialog.cancelled.connect(on_cancelled)
    dialog.open()
    return dialog
