"""Consent of Full auto (wave 12 phase 2, AM-57): a mixin of `AutomixLivePanel`."""

from __future__ import annotations

from wing_parser.ui.texts import text
from wing_parser.ui.write_arm_dialog import arm_now


class ConsentMixin:
    def _arm(self) -> bool:
        return arm_now(self._gate, self)

    def _fresh_arm(self) -> bool:
        """Never ride an arm another writer left behind: disarm, then arm."""
        self._drop_arm()
        if not self._arm():
            return False
        self._armed_by_me = True
        return True

    def _drop_arm(self) -> None:
        self._silent = True
        try:
            if self._gate.arm.armed():
                self._gate.arm.disarm()
                self._gate.changed.emit()
        finally:
            self._silent = False

    def _release_arm(self) -> None:
        if self._armed_by_me:
            self._armed_by_me = False
            self._drop_arm()

    def mode_changed(self, mode: str) -> None:
        """Settings moved the Automix mode: leaving Full auto stops a live run."""
        live = self._ctx is not None and not self._ctx.simulate
        if mode != "full_auto" and live and (self._active() or self._armed_by_me):
            self.stop()
            self._say(text("automix.live.mode_off"))
