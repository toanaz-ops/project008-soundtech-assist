"""Async callback handlers for `DelayedWriteDialog`, split out to keep the
dialog itself under the house-style line ceiling (D-50).

Both classes mutate the dialog they are given directly -- each is a named
slice of `DelayedWriteDialog`'s own book-keeping, not an independent
object with its own lifecycle, so reaching into `dlg.<anything>` here is
exactly as coupled (and exactly as safe) as it was inline before the
split. Neither imports `live_wiring`: `write_delay_dialog` must not
either (a cycle bit it once already), and this module keeps that rule by
construction -- it only ever sees the dialog instance it is handed.
"""

from __future__ import annotations

from wing_parser.ui import live_write
from wing_parser.ui.texts import text


class PreflightRead:
    """The dialog's own pre-flight `CallRunner` call (W5). A landed value
    normalises the desk's current reading, enables Apply, and releases an
    expiry that was held at 0 (F5: `_tick` sets `dlg._expired` rather than
    apply blind). A failed read disables Apply for the dialog's life --
    dropping the write silently, or applying blind, is worse than either.
    """

    def __init__(self, dialog) -> None:
        self._dlg = dialog

    def landed(self, value) -> None:
        dlg = self._dlg
        if value is None:
            self.failed()
            return
        dlg.desk_before = value
        dlg.desk_label.setText(text("console.write.desk_value").format(value=value))
        dlg.mismatch_label.setText(
            live_write.mismatch_line(value, dlg._patch.before))
        dlg.apply_button.setEnabled(True)
        if dlg._expired:
            dlg._apply()                  # F5: the countdown was waiting

    def failed(self) -> None:
        dlg = self._dlg
        dlg.desk_label.setText(text("console.write.no_read"))
        dlg.apply_button.setEnabled(False)
        dlg._timer.stop()


class WriteOutcome:
    """The two ways a submitted `WriteJob` (§8.3) can settle. Both clear
    `_sent` first -- a packet that already landed (either way) is no
    longer "on the wire", so `reject()`/`_cancel` stop refusing themselves
    from here on."""

    def __init__(self, dialog) -> None:
        self._dlg = dialog

    def done(self, result) -> None:
        dlg = self._dlg
        dlg._sent = False
        dlg.applied.emit(result)
        dlg.accept()

    def failed(self, exc) -> None:
        dlg = self._dlg
        dlg._sent = False
        dlg.status_label.setText(text("console.write.refused").format(error=exc))
        dlg.failed.emit(exc)
        dlg.reject()


def cancel(dlg) -> None:
    """W12: stops the WHOLE revert run. W15: Delayed's only way out, since
    a Stop button behind a modal dialog is not reachable. Gated on
    `dlg._sent`, NOT `dlg._settled`: a countdown that settled without
    transmitting (gate 4 refused it) must still be closable."""
    if dlg._sent:
        return
    dlg._settled = True
    dlg._timer.stop()
    dlg.status_label.setText(text(
        "console.write.revert_cancelled" if dlg._record
        else "console.write.cancelled"))
    dlg.cancelled.emit()
    dlg.reject()
