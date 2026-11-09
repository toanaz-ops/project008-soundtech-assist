"""Revert automix, panel side (wave 12 phase 2): a mixin of `AutomixLivePanel`."""

from __future__ import annotations

from wing_parser.ui import automix_live_records as records
from wing_parser.ui.texts import text


class RevertMixin:
    def _can_revert(self) -> bool:
        return bool(self._worker and self._worker.originals
                    and not self._worker_busy() and self._gate.can_write())

    def revert(self) -> bool:
        if not self._can_revert():
            self._say(text("automix.live.nothing_to_revert"))
            return False
        if self._runner.busy or not self._gate.idle():
            self._say(text("automix.live.busy"))
            return False
        if not self._fresh_arm():                    # consent per revert (AM-57)
            return False
        self._ctx.abort.clear()
        self._worker.begin()
        started = self._runner.start(
            "tick", self._worker.revert, self._loop.locked_paths,
            on_success=self._reverted, on_failure=self._failed,
            timeout=self._timeout or max(60, 6 * len(self._worker.originals)))
        if not started:
            self._worker.busy.clear()
            return False
        records.lock_other_writers(self._window, True)
        self.view.set_running(True, False)
        return True

    def _reverted(self, result) -> None:
        skipped, error = result
        count = self._drain()
        key = "automix.live.reverted" if not skipped else "automix.live.reverted_skipped"
        message = text(key).format(count=count, skipped=len(skipped))
        self._settle()
        self._release_arm()
        self._say(message if not error else text("automix.live.error").format(error=error))
