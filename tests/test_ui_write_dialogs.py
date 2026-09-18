"""Spec §9.2: both write dialogs, offscreen, against `FakeDesk`.

No socket: every identity and every read comes from
`FakeDesk.write_transport()` (task 3), and every runner is constructed with
a small positive `timeout` (not `0`, which `CallRunner` reads as a
zero-second budget and fires `CallTimedOut` on the very next event-loop
pass -- Task 8 measured it) so no test waits real seconds (`workers.py:114`).
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")

from tests.fake_desk import FakeDesk
from wing_parser.net.codec import OscMessage
from wing_parser.net.identity import WingIdentity

HOST = "192.168.128.28"
NAME = "WING-GIAQUY"


def _identity():
    return WingIdentity(ip=HOST, name=NAME, model="wing-rack",
                        serial="01009Y90604AAE", firmware="3.1-0-g9f314617:release")


class _Page:
    """The two things `WriteGate` reads off a Console page: state and host."""

    def __init__(self, state):
        self.state = state

        class _Bar:
            def host(self_inner):
                return HOST

        self.connect_bar = _Bar()


def _gate(qt_app, desk, state=None):
    from wing_parser.ui.live_state import LiveState
    from wing_parser.ui.live_wiring import WriteGate

    page = _Page(state or LiveState.CONNECTED)
    return WriteGate(page, transport=desk.write_transport(), timeout=2)


def _arm_dialog(qt_app, desk=None):
    from wing_parser.ui.write_arm_dialog import ArmWriteDialog

    desk = FakeDesk(identity=_identity()) if desk is None else desk
    gate = _gate(qt_app, desk)
    dlg = ArmWriteDialog(gate, transport=desk.write_transport(), timeout=2)
    return dlg, gate, desk


# -- Arm (F4, §8.2) -----------------------------------------------------


def test_arm_is_disabled_when_the_dialog_opens(qt_app, settle):
    dlg, _g, _d = _arm_dialog(qt_app)
    assert settle(lambda: NAME in dlg.status_label.text())
    assert dlg.arm_button.isEnabled() is False


def test_the_latch_alone_does_not_enable_arm(qt_app, settle):
    dlg, _g, _d = _arm_dialog(qt_app)
    settle(lambda: NAME in dlg.status_label.text())
    dlg.latch.setChecked(True)
    assert dlg.arm_button.isEnabled() is False


def test_the_name_alone_does_not_enable_arm(qt_app, settle):
    dlg, _g, _d = _arm_dialog(qt_app)
    settle(lambda: NAME in dlg.status_label.text())
    dlg.name_edit.setText(NAME)
    assert dlg.arm_button.isEnabled() is False


def test_both_together_enable_arm(qt_app, settle):
    dlg, _g, _d = _arm_dialog(qt_app)
    settle(lambda: NAME in dlg.status_label.text())
    dlg.latch.setChecked(True)
    dlg.name_edit.setText(NAME)
    assert dlg.arm_button.isEnabled() is True


@pytest.mark.parametrize("typed", ["WING-GIAQUI", "wing-giaquy", " WING-GIAQUY"])
def test_a_near_miss_name_is_refused_and_said_so(qt_app, settle, typed):
    """Exact, not case-folded and not stripped: §2.1 says "the typed name
    equals `identity.name` exactly"."""
    from wing_parser.ui.texts import text

    dlg, _g, _d = _arm_dialog(qt_app)
    settle(lambda: NAME in dlg.status_label.text())
    dlg.latch.setChecked(True)
    dlg.name_edit.setText(typed)
    assert dlg.arm_button.isEnabled() is False
    assert dlg.name_hint.text() == text("console.write.name_wrong")


def test_the_dialog_shows_the_serial_it_just_re_queried(qt_app, settle):
    dlg, _g, _d = _arm_dialog(qt_app)
    assert settle(lambda: "01009Y90604AAE" in dlg.status_label.text())


def test_an_identity_failure_leaves_arm_dead_for_this_dialogs_life(qt_app, settle):
    desk = FakeDesk(identity=TimeoutError("no reply"))
    dlg, _g, _d = _arm_dialog(qt_app, desk)
    assert settle(lambda: "Cannot identify" in dlg.status_label.text())
    assert "not armed" in dlg.status_label.text()
    dlg.latch.setChecked(True)
    dlg.name_edit.setText(NAME)
    assert dlg.arm_button.isEnabled() is False


def test_arming_arms_the_gate_and_announces_the_identity(qt_app, settle):
    dlg, gate, _d = _arm_dialog(qt_app)
    settle(lambda: NAME in dlg.status_label.text())
    seen = []
    dlg.armed.connect(seen.append)
    gate.changed.connect(lambda: seen.append("changed"))
    dlg.latch.setChecked(True)
    dlg.name_edit.setText(NAME)
    dlg.arm_button.click()

    assert gate.arm.armed() is True
    assert gate.arm.identity.serial == "01009Y90604AAE"
    assert any(getattr(item, "name", None) == NAME for item in seen)
    assert "changed" in seen, "the selector has to hear that the levels opened"


def test_arm_now_is_a_no_op_on_an_already_armed_gate(qt_app):
    from wing_parser.ui.write_arm_dialog import arm_now

    desk = FakeDesk(identity=_identity())
    gate = _gate(qt_app, desk)
    gate.arm.arm(_identity())
    assert arm_now(gate) is True, "no second dialog for an armed connection"


def test_the_arm_dialog_is_application_modal(qt_app):
    from PySide6.QtCore import Qt

    dlg, _g, _d = _arm_dialog(qt_app)
    assert dlg.windowModality() == Qt.WindowModality.ApplicationModal
