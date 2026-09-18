"""The doctor page: findings shown, verdicts taken, clears kept silent."""

import pytest

pytest.importorskip("PySide6.QtWidgets")

from wing_parser.ui.apply_level import ApplyLevel


@pytest.fixture
def page(qt_app, vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.doctor_page import DoctorPage
    from wing_parser.ui.session import Session

    doctor = DoctorPage()
    doctor.set_session(Session.open(vu_path))
    return doctor


def _identity():
    from wing_parser.net.identity import WingIdentity

    return WingIdentity(ip="192.168.128.28", name="WING-GIAQUY",
                        model="wing-rack", serial="01009Y90604AAE",
                        firmware="3.1-0-g9f314617:release")


def _has_repair(finding) -> bool:
    from wing_parser.edit import repairs

    return finding.rule_id in repairs.load_repairs()


def _doctor(qt_app, desk=None, state=None):
    from tests.fake_desk import FakeDesk
    from wing_parser.ui.doctor_page import DoctorPage
    from wing_parser.ui.live_state import LiveState
    from wing_parser.ui.live_wiring import WriteGate

    desk = desk or FakeDesk(identity=_identity())

    class _Bar:
        def host(self):
            return "192.168.128.28"

    class _Page:
        pass

    page = _Page()
    page.state = state or LiveState.CONNECTED
    page.connect_bar = _Bar()
    gate = WriteGate(page, transport=desk.write_transport(), timeout=2)
    doctor = DoctorPage()
    doctor.attach_gate(gate)
    return doctor, gate, desk


def test_programmatic_clear_does_not_emit_selected(page):
    emitted = []
    page.selected.connect(emitted.append)

    page.show_finding(None)                  # MainWindow/set_session path
    page.set_session(None)                   # the other internal clear path

    assert emitted == []


def test_a_user_row_click_emits_selected_exactly_once(page):
    emitted = []
    page.selected.connect(emitted.append)

    page.findings_view._table.selectRow(1)   # the real click path, offscreen;
    # row 0 is already taken by set_session's own first-row selection.

    assert len(emitted) == 1
    assert emitted[0] is not None


def test_set_session_selects_the_first_row_and_wakes_the_verdict_bar(page):
    selection = page.findings_view._table.selectionModel().selectedRows()
    assert len(selection) == 1
    assert all(b.isEnabled() for b in page.verdict_bar.buttons.values())
    assert page.verdict_bar.note.isEnabled()


def test_the_first_row_selection_is_silent(qt_app, vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.doctor_page import DoctorPage
    from wing_parser.ui.session import Session

    doctor = DoctorPage()
    emitted = []
    doctor.selected.connect(emitted.append)
    doctor.set_session(Session.open(vu_path))

    assert emitted == []


# -- the apply-level selector and Arm (F3, F4, W14) ---------------------


def test_the_selector_offers_delayed_and_immediate_only_when_armed(qt_app):
    doctor, gate, _d = _doctor(qt_app)
    assert doctor.level_box.currentData() is ApplyLevel.MANUAL
    for index in range(doctor.level_box.count()):
        enabled = doctor.level_box.model().item(index).isEnabled()
        assert enabled == (doctor.level_box.itemData(index) is ApplyLevel.MANUAL)

    gate.arm.arm(_identity())
    gate.changed.emit()
    for index in range(doctor.level_box.count()):
        assert doctor.level_box.model().item(index).isEnabled()


def test_the_selector_falls_back_to_manual_on_disarm(qt_app):
    doctor, gate, _d = _doctor(qt_app)
    gate.arm.arm(_identity())
    gate.changed.emit()
    doctor.level_box.setCurrentIndex(
        doctor.level_box.findData(ApplyLevel.IMMEDIATE))
    assert gate.arm.level is ApplyLevel.IMMEDIATE

    gate.close()                                  # a dropout
    assert doctor.level_box.currentData() is ApplyLevel.MANUAL
    assert gate.arm.level is ApplyLevel.MANUAL


def test_the_arm_button_becomes_the_armed_label(qt_app):
    from wing_parser.ui.texts import text

    doctor, gate, _d = _doctor(qt_app)
    assert doctor.arm_button.text() == text("console.write.arm")
    gate.arm.arm(_identity())
    gate.changed.emit()
    assert doctor.arm_button.text() == text("console.write.armed").format(
        name="WING-GIAQUY")


def test_the_selector_and_arm_go_dead_for_a_revert_run_and_come_back(qt_app):
    """W14: a run that changed level halfway would send some parameters
    through a countdown and others instantly, from one click."""
    doctor, _g, _d = _doctor(qt_app)
    doctor.set_controls_enabled(False)
    assert doctor.level_box.isEnabled() is False
    assert doctor.arm_button.isEnabled() is False
    doctor.set_controls_enabled(True)
    assert doctor.level_box.isEnabled() is True
    assert doctor.arm_button.isEnabled() is True


def test_repair_announces_the_patch_it_appended(qt_app, vu_path):
    """The routing hook: DetailPanel emits the journal's newest Patch."""
    from wing_parser.ui.session import Session

    doctor, _g, _d = _doctor(qt_app)
    session = Session.open(vu_path)
    finding = next(f for f in session.findings()
                   if session.rule(f.rule_id) and _has_repair(f))
    doctor.set_session(session)
    doctor.show_finding(finding)
    seen = []
    doctor.send_requested.connect(seen.append)

    doctor.detail_panel.repair_button.click()

    assert seen, "a successful repair must announce its patch"
    assert seen[0] is session.changes()[-1]


def test_a_repair_that_does_nothing_announces_nothing(qt_app):
    doctor, _g, _d = _doctor(qt_app)
    seen = []
    doctor.send_requested.connect(seen.append)
    doctor.detail_panel._repair()          # no finding, no session
    assert seen == []


def test_arm_from_the_doctor_page_uses_the_gates_own_transport(qt_app, monkeypatch):
    """MINOR 7: this was the one `arm_now` call site in the app that passed
    no `transport=`, so `ArmWriteDialog` fell back to `live_write.REAL` and
    a fake gate's Arm button would have opened a real socket."""
    from wing_parser.ui import doctor_page

    doctor, gate, _desk = _doctor(qt_app)
    seen = {}
    monkeypatch.setattr(doctor_page, "arm_now",
                        lambda g, parent=None, **kw: seen.update(gate=g, **kw) or True)

    doctor.arm_button.click()

    assert seen["gate"] is gate
    assert seen["transport"] is gate.transport
    assert gate.transport is not None
