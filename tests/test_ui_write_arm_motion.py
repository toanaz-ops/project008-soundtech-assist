"""Wave 6 (2026-11-09): soft, non-blocking motion warning in the Arm dialog."""
from __future__ import annotations

import time

import pytest

pytest.importorskip("PySide6.QtWidgets")

from tests.fake_desk import FakeDesk
from wing_parser.net.identity import WingIdentity

HOST = "192.168.128.28"
NAME = "WING-GIAQUY"


class _Page:
    def __init__(self):
        from wing_parser.ui.live_state import LiveState

        self.state = LiveState.CONNECTED

        class _Bar:
            def host(self_inner):
                return HOST

        self.connect_bar = _Bar()


@pytest.fixture
def knowledge(tmp_path, monkeypatch):
    from wing_parser import config

    monkeypatch.setattr(config, "knowledge_dir", lambda override=None: tmp_path)
    return tmp_path


def _dialog(settle, motion):
    from wing_parser.ui.live_wiring import WriteGate
    from wing_parser.ui.write_arm_dialog import ArmWriteDialog

    desk = FakeDesk(identity=WingIdentity(
        ip=HOST, name=NAME, model="wing-rack", serial="01009Y90604AAE",
        firmware="3.1"))
    gate = WriteGate(_Page(), transport=desk.write_transport(), timeout=2)
    for i in range(motion):
        gate.activity.record(f"/ch/{i + 1}/$fdr", time.monotonic())
    dlg = ArmWriteDialog(gate, transport=desk.write_transport(), timeout=2)
    assert settle(lambda: NAME in dlg.status_label.text())
    return dlg, gate


@pytest.mark.parametrize("motion", [0, 4])
def test_warning_follows_motion_and_arming_still_works(
        qt_app, settle, knowledge, motion):
    dlg, gate = _dialog(settle, motion)
    if motion:
        assert not dlg.motion_warning.isHidden()
        assert str(motion) in dlg.motion_warning.text()
        assert dlg.motion_warning.property("azStyle") == "warn"
    else:
        assert dlg.motion_warning.isHidden()
    dlg.latch.setChecked(True)
    dlg.name_edit.setText(NAME)
    dlg.show_fields.code_edit.setText("AZ-1")
    assert dlg.arm_button.isEnabled() is True
    dlg.arm_button.click()
    assert gate.arm.armed()
