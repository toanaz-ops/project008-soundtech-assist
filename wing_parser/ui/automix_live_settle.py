"""Settling of Full auto (wave 12 phase 2, AM-52): a mixin of `AutomixLivePanel`.

Controls come back only once the last worker thread has ended; rows a
thread left behind are recorded even when the CallRunner abandoned it."""

from __future__ import annotations

from wing_parser.ui import automix_live_records as records


class SettleMixin:
    def _worker_busy(self) -> bool:
        """A thread of ours may still run after the CallRunner gave up on it."""
        return self._worker is not None and self._worker.busy.is_set()

    def _active(self) -> bool:
        return self._timer.isActive() or self._worker_busy()

    def _lock_ui(self, running: bool) -> None:
        self.view.set_running(running, self._can_revert())
        records.lock_other_writers(self._window, running, self._gate)    # one writer (W10)

    def _finish_run(self) -> None:
        was_running = self._timer.isActive()
        self._timer.stop()
        self._settle()
        if was_running:
            self._refresh_status()

    def _settle(self) -> None:
        """Controls come back only once the last worker thread has ended."""
        if self._worker_busy():
            if not self._settle_timer.isActive():
                self._settle_timer.start()
            self.view.set_running(True, False)
            return
        self._settle_timer.stop()
        self._drain()
        self._lock_ui(False)

    def _drain(self) -> int:
        """Record every row a thread left, even one the runner abandoned (AM-52)."""
        if self._worker is None:
            return 0
        rows = self._worker.take_rows()
        if rows:
            self._add_rows(rows)
        reverts = self._worker.take_revert_rows()
        if reverts:
            self.view.add_rows(records.record_reverts(self._window, self._ctx, reverts))
        return len(reverts)
