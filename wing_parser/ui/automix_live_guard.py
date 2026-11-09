"""Start preconditions of Full auto (wave 12 phase 2, AM-57)."""

from __future__ import annotations

from wing_parser.ui import settings_automix


def refusal(panel) -> str | None:
    """The text key of the first reason Start must refuse, or None."""
    if getattr(panel._window, "session", None) is None:
        return "automix.live.need_scene"
    gate = panel._gate
    if not gate.can_write():
        return "automix.live.need_connection"
    if panel._runner.busy or panel._worker_busy():
        return "automix.live.busy"
    if not gate.idle():                      # one writer on the wire (W10)
        return "automix.live.gate_busy"
    if not panel.view.simulate.isChecked():
        if not panel.view.ack.isChecked():
            return "automix.live.need_ack"
        if settings_automix.current_mode() != "full_auto":
            return "automix.live.need_mode"
    return None
