"""Wave 5 (spec section 5): the Arm dialog also asks which show this is."""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")

from tests.fake_desk import FakeDesk
from wing_parser.net.identity import WingIdentity

HOST = "192.168.128.28"
NAME = "WING-GIAQUY"


def _identity():
    return WingIdentity(ip=HOST, name=NAME, model="wing-rack",
                        serial="01009Y90604AAE", firmware="3.1")


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


def _dialog(settle, knowledge):
    from wing_parser.ui.live_wiring import WriteGate
    from wing_parser.ui.write_arm_dialog import ArmWriteDialog

    desk = FakeDesk(identity=_identity())
    gate = WriteGate(_Page(), transport=desk.write_transport(), timeout=2)
    dlg = ArmWriteDialog(gate, transport=desk.write_transport(), timeout=2)
    assert settle(lambda: NAME in dlg.status_label.text())
    dlg.latch.setChecked(True)
    dlg.name_edit.setText(NAME)
    return dlg, gate


def test_arm_stays_disabled_without_a_valid_show_code(qt_app, settle, knowledge):
    dlg, _gate = _dialog(settle, knowledge)
    assert dlg.arm_button.isEnabled() is False


@pytest.mark.parametrize("typed", ["", "AZ-", "ABC-1", "../x", "AZA-1"])
def test_an_invalid_code_keeps_arm_disabled_and_says_why(
        qt_app, settle, knowledge, typed):
    from wing_parser.ui.texts import text

    dlg, _gate = _dialog(settle, knowledge)
    dlg.show_fields.code_edit.setText(typed)
    assert dlg.arm_button.isEnabled() is False
    if typed:
        assert dlg.show_fields.code_hint.text() == text("console.write.arm_code_hint")


def test_a_lowercase_code_is_accepted_and_folded(qt_app, settle, knowledge):
    dlg, gate = _dialog(settle, knowledge)
    dlg.show_fields.code_edit.setText("aza-000123")
    assert dlg.arm_button.isEnabled() is True
    dlg.arm_button.click()
    assert gate.arm.show["code"] == "AZA-000123"


def test_the_adhoc_tick_fills_a_generated_code(qt_app, settle, knowledge):
    from wing_parser.writelog import normalize_code

    dlg, _gate = _dialog(settle, knowledge)
    dlg.show_fields.adhoc.setChecked(True)
    code = dlg.show_fields.code_edit.text()
    assert code.startswith("ADHOC-") and normalize_code(code) == code
    assert dlg.arm_button.isEnabled() is True
    dlg.show_fields.adhoc.setChecked(False)
    assert dlg.show_fields.code_edit.text() == ""
    assert dlg.arm_button.isEnabled() is False


def test_name_and_venue_are_capped_at_eighty(qt_app, settle, knowledge):
    dlg, _gate = _dialog(settle, knowledge)
    dlg.show_fields.name_edit.setText("n" * 200)
    dlg.show_fields.venue_edit.setText("v" * 200)
    assert len(dlg.show_fields.name_edit.text()) == 80
    assert len(dlg.show_fields.venue_edit.text()) == 80


def test_arming_attaches_the_show_and_saves_last_show(qt_app, settle, knowledge):
    from wing_parser.ui import state_store

    dlg, gate = _dialog(settle, knowledge)
    dlg.show_fields.code_edit.setText("AZ-1501")
    dlg.show_fields.name_edit.setText(" BIDV Gala ")
    dlg.show_fields.venue_edit.setText("GEM Center")
    dlg.arm_button.click()

    show = {"code": "AZ-1501", "name": "BIDV Gala", "venue": "GEM Center"}
    assert gate.arm.show == show
    assert state_store.load(knowledge)["last_show"] == show


def test_all_three_fields_are_prefilled_from_last_show(qt_app, settle, knowledge):
    from wing_parser.ui import state_store

    state_store.save_last_show(
        knowledge, {"code": "AZ-1501", "name": "BIDV Gala", "venue": "GEM Center"})
    dlg, _gate = _dialog(settle, knowledge)
    assert dlg.show_fields.code_edit.text() == "AZ-1501"
    assert dlg.show_fields.name_edit.text() == "BIDV Gala"
    assert dlg.show_fields.venue_edit.text() == "GEM Center"
    assert dlg.arm_button.isEnabled() is True


def test_disarm_forgets_the_show(qt_app, settle, knowledge):
    dlg, gate = _dialog(settle, knowledge)
    dlg.show_fields.code_edit.setText("AZ-9")
    dlg.arm_button.click()
    assert gate.arm.show is not None
    gate.close()
    assert gate.arm.show is None
