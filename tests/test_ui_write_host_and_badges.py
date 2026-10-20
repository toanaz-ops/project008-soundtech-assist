"""Audit 2026-10-21, findings 5 and 6: journal badges survive `set_changes`,
and an armed gate keeps the host it was armed for. Offscreen, `FakeDesk` only."""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")

from tests.fake_desk import FakeDesk
from tests.test_ui_changes_send import (
    PATH, _gate, _identity, _panel, _patch, _record, _window,
)

ARMED_HOST = "192.168.128.28"
NAME = "WING-GIAQUY"


# -- finding 5: badges ---------------------------------------------------


def test_a_sent_badge_survives_a_rebuild_of_the_journal_list(qt_app, vu_path):
    desk = FakeDesk(identity=_identity())
    window = _window(qt_app, vu_path)
    panel = _panel(qt_app, _gate(qt_app, desk), window)
    patch = window.session.record_value(PATH, "PRE", label="x", because="G8")
    panel.set_changes(window.session.changes())
    panel.record_sent(patch, _record("PRE", True))
    shown = panel.list.itemWidget(panel.list.item(0)).badge

    assert shown.text()

    # what every Repair / Undo / clamp / revert does next (`MainWindow._refresh`)
    panel.set_changes(window.session.changes())

    row = panel.list.itemWidget(panel.list.item(0))
    assert row.badge.text() == shown.text()
    assert row.badge.isVisibleTo(row) is True


def test_a_badge_does_not_come_back_on_a_re_repaired_patch_after_undo(qt_app, vu_path):
    desk = FakeDesk(identity=_identity())
    window = _window(qt_app, vu_path)
    panel = _panel(qt_app, _gate(qt_app, desk), window)
    patch = window.session.record_value(PATH, "PRE", label="x", because="G8")
    panel.set_changes(window.session.changes())
    panel.record_sent(patch, _record("PRE", True))

    window.session.undo()
    panel.set_changes(window.session.changes())
    patch_again = window.session.record_value(PATH, "PRE", label="x", because="G8")
    panel.set_changes(window.session.changes())

    assert patch_again == patch, "an equal Patch, but one that was NOT sent"
    assert panel.list.itemWidget(panel.list.item(0)).badge.text() == ""


# -- finding 6: host captured at arm time --------------------------------


class _MovableBar:
    def __init__(self, host):
        self.current = host

    def host(self):
        return self.current


def _gate_with_bar(qt_app, desk, bar):
    from wing_parser.ui.live_state import LiveState
    from wing_parser.ui.live_wiring import WriteGate

    class _Page:
        state = LiveState.CONNECTED
        connect_bar = bar

    return WriteGate(_Page(), transport=desk.write_transport(), timeout=2)


def test_an_armed_gate_keeps_the_host_it_was_armed_for(qt_app):
    desk = FakeDesk(identity=_identity())
    bar = _MovableBar(ARMED_HOST)
    gate = _gate_with_bar(qt_app, desk, bar)
    gate.arm.arm(_identity(), host=bar.host())

    bar.current = "10.9.9.9"                      # the operator edits the box

    assert gate.host() == ARMED_HOST
    gate.arm.disarm()
    assert gate.host() == "10.9.9.9", "disarmed: the box is the truth again"


def test_arming_through_the_dialog_captures_the_host_it_identified(qt_app, settle):
    from wing_parser.ui.write_arm_dialog import ArmWriteDialog

    desk = FakeDesk(identity=_identity())
    bar = _MovableBar(ARMED_HOST)
    gate = _gate_with_bar(qt_app, desk, bar)
    dlg = ArmWriteDialog(gate, transport=desk.write_transport(), timeout=2)
    assert settle(lambda: NAME in dlg.status_label.text())

    bar.current = "10.9.9.9"                      # edited while the dialog is open
    dlg.latch.setChecked(True)
    dlg.name_edit.setText(NAME)
    dlg.show_fields.code_edit.setText("AZ-1")
    dlg.arm_button.click()

    assert gate.arm.armed()
    assert gate.host() == ARMED_HOST
