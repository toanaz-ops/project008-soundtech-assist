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


def test_typing_the_name_before_identity_arrives_shows_pending_not_wrong(qt_app, settle):
    """Review fix round 1, #1: the read has not settled yet, so a typed
    name -- even the RIGHT one -- must not be judged wrong for lack of
    anything to compare it against."""
    from wing_parser.ui.texts import text

    dlg, _g, _d = _arm_dialog(qt_app)
    dlg.latch.setChecked(True)
    dlg.name_edit.setText(NAME)
    assert dlg.name_hint.text() == text("console.write.name_pending")
    assert dlg.arm_button.isEnabled() is False

    assert settle(lambda: NAME in dlg.status_label.text())
    assert dlg.name_hint.text() == ""
    assert dlg.arm_button.isEnabled() is True


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


def test_rejecting_mid_read_cancels_the_runner_and_ignores_the_late_reply(
        qt_app, settle):
    """Review fix round 1, #2: Cancel/Esc/X while the pre-flight read is
    still in flight must settle the runner right then, so a reply that was
    already on its way across the thread boundary cannot re-enable
    anything on a dialog the operator just dismissed."""
    dlg, gate, _d = _arm_dialog(qt_app)
    before = dlg.status_label.text()

    dlg.reject()

    # Pump the event loop a while: if the late identity reply were still
    # going to land, this is where it would.
    settle(lambda: False, limit_s=0.3)
    assert dlg.status_label.text() == before
    assert dlg.arm_button.isEnabled() is False
    assert gate.arm.armed() is False


# -- Delayed (F5, §8.4, W11, W12) ---------------------------------------

PATH = "ae_data.ch.1.send.8.mode"
OSC = "/ch/1/send/8/mode"
BOOL_PATH = "ae_data.ch.1.in.set.inv"
BOOL_OSC = "/ch/1/in/set/inv"


def _patch(path=PATH, before="POST", after="PRE"):
    from wing_parser.edit.journal import Patch
    return Patch(path=path, before=before, after=after, because="G8:ch.1.send.8",
                 label="Set the send to PRE (ch.1.send.8)")


def _delay_dialog(qt_app, *, desk=None, seconds=5, patch=None, armed=True, **kwargs):
    from wing_parser.ui.write_delay_dialog import DelayedWriteDialog

    desk = desk or FakeDesk(identity=_identity(),
                            leaves={OSC: OscMessage(OSC, "s", ("POST",))},
                            readbacks={OSC: "PRE"})
    gate = _gate(qt_app, desk)
    if armed:
        gate.arm.arm(_identity())
    dlg = DelayedWriteDialog(gate, patch or _patch(), seconds,
                             transport=desk.write_transport(), timeout=2, **kwargs)
    return dlg, gate, desk


def test_the_countdown_starts_at_the_settings_value(qt_app):
    dlg, _g, _d = _delay_dialog(qt_app, seconds=9)
    assert dlg.remaining == 9
    assert "9" in dlg.countdown_label.text()


def test_plus_five_adds_to_the_remainder_repeatably_with_no_ceiling(qt_app):
    """F5: an operator who needs a minute presses it twelve times, and that
    is a legitimate answer."""
    dlg, _g, _d = _delay_dialog(qt_app, seconds=5)
    for expected in (10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65):
        dlg.extend_button.click()
        assert dlg.remaining == expected


def test_the_dialog_shows_the_desk_value_the_file_value_and_the_new_one(qt_app, settle):
    dlg, _g, _d = _delay_dialog(qt_app)
    assert settle(lambda: "POST" in dlg.desk_label.text())
    assert "POST" in dlg.file_label.text()
    assert "PRE" in dlg.after_label.text()
    assert OSC in dlg.address_label.text()


def test_the_mismatch_line_appears_only_when_the_desk_moved(qt_app, settle):
    quiet, _g, _d = _delay_dialog(qt_app)
    assert settle(lambda: "POST" in quiet.desk_label.text())
    assert quiet.mismatch_label.text() == ""

    desk = FakeDesk(identity=_identity(),
                    leaves={OSC: OscMessage(OSC, "s", ("GRP",))},
                    readbacks={OSC: "PRE"})
    moved, _g2, _d2 = _delay_dialog(qt_app, desk=desk)
    assert settle(lambda: moved.mismatch_label.text())
    assert "GRP" in moved.mismatch_label.text()
    assert "POST" in moved.mismatch_label.text()


def test_a_bool_leaf_reads_true_and_false_never_one_and_zero(qt_app, settle):
    """§4's normalisation, seen where it actually misleads an operator: an
    unnormalised read shows "the desk holds 0, the scene file expected
    False" and a mismatch warning that is not one."""
    desk = FakeDesk(identity=_identity(),
                    leaves={BOOL_OSC: OscMessage(BOOL_OSC, "sfi", ("1", 0.0, 1))},
                    readbacks={BOOL_OSC: 0})
    dlg, _g, _d = _delay_dialog(
        qt_app, desk=desk,
        patch=_patch(path=BOOL_PATH, before=True, after=False))
    assert settle(lambda: dlg.desk_label.text() != "")
    assert "True" in dlg.desk_label.text()
    assert dlg.mismatch_label.text() == "", "True == True is not a mismatch"


def test_a_desk_that_lacks_the_address_says_so_instead_of_guessing(qt_app, settle):
    from wing_parser.ui.texts import text

    desk = FakeDesk(identity=_identity(), leaves={})
    dlg, _g, _d = _delay_dialog(qt_app, desk=desk)
    assert settle(lambda: dlg.desk_label.text() == text("console.write.no_read"))


def test_apply_now_sends_at_once(qt_app, settle):
    dlg, _g, desk = _delay_dialog(qt_app)
    settle(lambda: dlg.desk_label.text() != "")
    results = []
    dlg.applied.connect(results.append)
    dlg.apply_button.click()
    assert settle(lambda: results)
    assert [c[0:2] for c in desk.sets] == [(OSC, "PRE")]


def test_expiry_is_an_apply(qt_app, settle):
    """F5, stated flatly: a dialog that quietly dropped the write on timeout
    would leave the desk and the scene disagreeing with nobody told."""
    dlg, _g, desk = _delay_dialog(qt_app, seconds=3)
    settle(lambda: dlg.desk_label.text() != "")
    results = []
    dlg.applied.connect(results.append)
    for _ in range(3):
        dlg._tick()
    assert settle(lambda: results)
    assert [c[0:2] for c in desk.sets] == [(OSC, "PRE")]


def test_cancel_sends_nothing_and_leaves_the_journal_patch_alone(qt_app, settle):
    from wing_parser.ui.texts import text

    dlg, _g, desk = _delay_dialog(qt_app)
    settle(lambda: dlg.desk_label.text() != "")
    heard = []
    dlg.cancelled.connect(lambda: heard.append(True))
    dlg.cancel_button.click()
    assert desk.sets == []
    assert heard
    assert dlg.status_label.text() == text("console.write.cancelled")
    assert "Undo" in text("console.write.cancelled")


def test_gate_four_refuses_a_countdown_that_outlived_its_connection(qt_app, settle):
    """§8.4: a countdown can run a minute and the desk can go LOST under it."""
    from wing_parser.ui.live_state import LiveState
    from wing_parser.ui.texts import text

    dlg, gate, desk = _delay_dialog(qt_app, seconds=1)
    settle(lambda: dlg.desk_label.text() != "")
    failures = []
    dlg.failed.connect(failures.append)
    gate._page.state = LiveState.LOST          # the desk went away underneath
    dlg._tick()
    assert settle(lambda: failures)
    assert desk.sets == []
    assert dlg.status_label.text() == text("console.write.gate_closed")


def test_disarming_under_a_countdown_refuses_it_too(qt_app, settle):
    dlg, gate, desk = _delay_dialog(qt_app, seconds=1)
    settle(lambda: dlg.desk_label.text() != "")
    failures = []
    dlg.failed.connect(failures.append)
    gate.arm.disarm()
    dlg._tick()
    assert settle(lambda: failures)
    assert desk.sets == []


def test_the_delay_dialog_is_application_modal(qt_app):
    from PySide6.QtCore import Qt

    dlg, _g, _d = _delay_dialog(qt_app)
    assert dlg.windowModality() == Qt.WindowModality.ApplicationModal


def _record(desk_before="POST"):
    from wing_parser.net.write import SetResult
    from wing_parser.ui.live_write import SentWrite

    return SentWrite(address=OSC, path=PATH, desk_before=desk_before,
                     written="PRE",
                     result=SetResult(OSC, "PRE", "PRE", False, "PRE", True))


def test_a_revert_countdowns_cancel_stops_the_whole_run(qt_app, settle):
    """W12: not "skip this one" -- a seven-row revert would need seven
    deliberate cancels to abandon, the opposite of what Cancel promises."""
    from wing_parser.ui.texts import text

    dlg, _g, desk = _delay_dialog(qt_app, revert_record=_record())
    settle(lambda: dlg.desk_label.text() != "")
    heard = []
    dlg.cancelled.connect(lambda: heard.append(True))
    dlg.cancel_button.click()
    assert heard and desk.sets == []
    assert dlg.status_label.text() == text("console.write.revert_cancelled")


def test_a_revert_countdown_writes_the_desk_before_value(qt_app, settle):
    dlg, _g, desk = _delay_dialog(qt_app, revert_record=_record(desk_before="GRP"))
    settle(lambda: dlg.desk_label.text() != "")
    dlg.apply_button.click()
    assert settle(lambda: desk.sets)
    assert desk.sets[0][0:2] == (OSC, "GRP")


def test_rejecting_mid_read_cancels_the_delay_runner_and_stops_the_countdown(
        qt_app, settle):
    """Mirrors the arm dialog's own guard: Esc/X while the pre-flight read
    is still in flight must settle the runner AND stop the QTimer right
    then, so neither a late reply nor a late tick can touch a dismissed
    dialog."""
    dlg, gate, _d = _delay_dialog(qt_app)
    before = dlg.desk_label.text()

    dlg.reject()

    settle(lambda: False, limit_s=0.3)
    assert dlg.desk_label.text() == before
    assert dlg._timer.isActive() is False
    assert gate.arm.armed() is True, "reject() must not touch the gate itself"


# -- Fix round 1: Apply gated on the pre-flight read, dismissal locked --

def test_apply_is_disabled_and_inert_before_the_read_lands(qt_app):
    """CRITICAL: a click before the pre-flight read has landed must send
    nothing -- Apply has no real desk value to build a confirmation from
    yet."""
    dlg, _g, desk = _delay_dialog(qt_app)
    assert dlg.apply_button.isEnabled() is False
    dlg.apply_button.click()
    assert desk.sets == []


def test_expiry_holds_at_zero_until_a_pending_read_lands(qt_app, settle):
    """CRITICAL: the countdown can beat the read to zero -- expiry must
    hold, not apply blind, and fire the moment the read actually lands."""
    dlg, _g, desk = _delay_dialog(qt_app, seconds=1)
    results = []
    dlg.applied.connect(results.append)
    dlg._tick()                       # reaches 0 before the read lands
    assert desk.sets == []
    assert dlg.apply_button.isEnabled() is False
    assert settle(lambda: results)
    assert [c[0:2] for c in desk.sets] == [(OSC, "PRE")]


def test_a_failed_pre_flight_read_never_applies(qt_app, settle):
    """CRITICAL: a desk that never answers the pre-flight read must leave
    Apply dead for this dialog's life -- expiry included."""
    from wing_parser.ui.texts import text

    desk = FakeDesk(identity=_identity(), leaves={})   # no answer for OSC
    dlg, _g, _d = _delay_dialog(qt_app, desk=desk, seconds=1)
    assert settle(lambda: dlg.desk_label.text() == text("console.write.no_read"))
    assert dlg.apply_button.isEnabled() is False
    results = []
    dlg.applied.connect(results.append)
    dlg._tick()                       # expiry after a failed read
    settle(lambda: False, limit_s=0.3)
    assert results == []
    assert desk.sets == []
    assert dlg.apply_button.isEnabled() is False


def test_a_submitted_write_cannot_be_dismissed_until_the_result_lands(qt_app, settle):
    """IMPORTANT: a packet on the wire cannot be un-sent -- Escape/X while
    the result is outstanding must be a no-op, not a silent abandon."""
    dlg, _g, desk = _delay_dialog(qt_app)
    settle(lambda: dlg.apply_button.isEnabled())
    applied = []
    dlg.applied.connect(applied.append)
    rejected = []
    dlg.rejected.connect(lambda: rejected.append(True))

    dlg.apply_button.click()
    dlg.reject()                      # Escape while the write is outstanding

    assert rejected == [], "a packet on the wire cannot be un-sent"
    assert settle(lambda: applied)
    assert len(applied) == 1


# -- routing, one test per level (F3) -----------------------------------


def test_manual_sends_nothing_and_opens_nothing(qt_app):
    from wing_parser.ui import write_router
    from wing_parser.ui.apply_level import ApplyLevel

    desk = FakeDesk(identity=_identity(),
                    leaves={OSC: OscMessage(OSC, "s", ("POST",))})
    gate = _gate(qt_app, desk)
    gate.arm.arm(_identity())
    gate.arm.level = ApplyLevel.MANUAL

    dialog = write_router.route_repair(
        gate, _patch(), 5, transport=desk.write_transport(), timeout=2)
    assert dialog is None
    assert desk.sets == []


def test_delayed_opens_the_countdown_and_sends_nothing_yet(qt_app):
    from wing_parser.ui import write_router
    from wing_parser.ui.apply_level import ApplyLevel
    from wing_parser.ui.write_delay_dialog import DelayedWriteDialog

    desk = FakeDesk(identity=_identity(),
                    leaves={OSC: OscMessage(OSC, "s", ("POST",))},
                    readbacks={OSC: "PRE"})
    gate = _gate(qt_app, desk)
    gate.arm.arm(_identity())
    gate.arm.level = ApplyLevel.DELAYED

    dialog = write_router.route_repair(
        gate, _patch(), 9, transport=desk.write_transport(), timeout=2)
    assert isinstance(dialog, DelayedWriteDialog)
    assert dialog.remaining == 9
    assert desk.sets == []
    dialog.reject()


def test_immediate_produces_exactly_one_set_and_no_dialog(qt_app, settle):
    from wing_parser.ui import write_router
    from wing_parser.ui.apply_level import ApplyLevel

    desk = FakeDesk(identity=_identity(),
                    leaves={OSC: OscMessage(OSC, "s", ("POST",))},
                    readbacks={OSC: "PRE"})
    gate = _gate(qt_app, desk)
    gate.arm.arm(_identity())
    gate.arm.level = ApplyLevel.IMMEDIATE
    sent = []

    dialog = write_router.route_repair(
        gate, _patch(), 5, transport=desk.write_transport(), timeout=2,
        on_sent=lambda patch, record: sent.append(record))

    assert dialog is None
    assert settle(lambda: sent)
    assert [c[0:2] for c in desk.sets] == [(OSC, "PRE")]
    assert sent[0].desk_before == "POST", "the ledger records what the desk held"
    assert sent[0].written == "PRE"


def test_an_unarmed_route_opens_the_arm_dialog_first(qt_app, monkeypatch):
    """§2.2: Manual's Send and a Delayed repair both enter through arm_now."""
    from wing_parser.ui import write_router
    from wing_parser.ui.apply_level import ApplyLevel

    desk = FakeDesk(identity=_identity(),
                    leaves={OSC: OscMessage(OSC, "s", ("POST",))})
    gate = _gate(qt_app, desk)
    gate.arm.level = ApplyLevel.DELAYED         # selected but NOT armed
    calls = []
    monkeypatch.setattr(write_router, "arm_now",
                        lambda g, parent=None, **kw: calls.append(g) or False)

    assert write_router.route_repair(
        gate, _patch(), 5, transport=desk.write_transport(), timeout=2) is None
    assert calls == [gate], "no write path may skip gate 2"
    assert desk.sets == []


# -- review round 2, CRITICAL 1 / IMPORTANT 5: reverting a no-answer row --


def _ledger_record(desk_before="POST", readback="PRE", written="PRE"):
    from wing_parser.net.write import SetResult
    from wing_parser.ui.live_write import SentWrite

    return SentWrite(address=OSC, path=PATH, desk_before=desk_before,
                     written=written,
                     result=SetResult(OSC, written, str(written), False,
                                      readback, readback == written))


def test_route_revert_refuses_a_record_the_desk_never_described(qt_app):
    """Belt and braces behind the disabled button: `after=None` would be
    re-expressed as the literal string "None" by `write.set`'s default
    typetag, so routing refuses before gate 2 is even asked."""
    from wing_parser.ui import write_router
    from wing_parser.ui.apply_level import ApplyLevel

    desk = FakeDesk(identity=_identity())
    gate = _gate(qt_app, desk)
    gate.arm.arm(_identity())
    gate.arm.level = ApplyLevel.IMMEDIATE

    with pytest.raises(ValueError):
        write_router.route_revert(gate, _ledger_record(desk_before=None), 5,
                                  transport=desk.write_transport(), timeout=2)
    assert desk.sets == []


def test_a_revert_countdown_shows_what_the_desk_holds_now_not_none(qt_app, settle):
    """IMPORTANT 5: `route_revert` used to build its own `Patch` with
    `before=record.result.readback` and no fallback, so a clamped-or-silent
    send made the countdown read "The scene file expected: None". The
    fallback `write_records.desk_now` states is the one rule now."""
    from wing_parser.ui import write_router
    from wing_parser.ui.apply_level import ApplyLevel

    desk = FakeDesk(identity=_identity(),
                    leaves={OSC: OscMessage(OSC, "s", ("PRE",))},
                    readbacks={OSC: "POST"})
    gate = _gate(qt_app, desk)
    gate.arm.arm(_identity())
    gate.arm.level = ApplyLevel.DELAYED

    dialog = write_router.route_revert(
        gate, _ledger_record(desk_before="POST", readback=None), 5,
        transport=desk.write_transport(), timeout=2)
    assert "None" not in dialog.file_label.text()
    assert "PRE" in dialog.file_label.text(), "the value this app last sent"
    dialog.reject()
