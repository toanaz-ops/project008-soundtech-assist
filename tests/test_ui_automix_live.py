"""Wave 12 phase 2 UI: the Full auto panel against a FakeDesk. No socket."""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")

from tests.fake_desk import FakeDesk
from wing_parser.net.codec import OscMessage
from wing_parser.net.identity import WingIdentity

HOST = "192.168.128.28"
SHOW = {"code": "ADHOC-20261109-0900", "name": "", "venue": ""}


def _identity():
    return WingIdentity(ip=HOST, name="WING-GIAQUY", model="wing-rack",
                        serial="01009Y90604AAE", firmware="3.1-0-g9f314617:release")


def _msg(osc, value):
    if isinstance(value, bool) or isinstance(value, int):
        return OscMessage(osc, "sfi", (str(int(value)), 0.0, int(value)))
    if isinstance(value, float):
        return OscMessage(osc, "sff", (str(value), 0.0, value))
    return OscMessage(osc, "s", (str(value),))


def _writing_transport(desk):
    """The desk's write transport, but a set changes what the desk then reads."""
    from wing_parser.ui import live_write

    base = desk.write_transport()

    def _set(host, osc, value, *, confirm=False, **_kw):
        result = base.set(host, osc, value, confirm=confirm)
        desk.leaves[osc] = _msg(osc, value)
        return result

    return live_write.WriteTransport(identity=base.identity, read=base.read, set=_set)


@pytest.fixture(autouse=True)
def _consent(monkeypatch):
    """The arm dialog is modal: stand in for it by arming the gate; mode = Full auto."""
    from wing_parser.ui import automix_live_consent, settings_automix

    def fake_arm(gate, parent=None, **_kw):
        gate.arm.arm(_identity(), show=SHOW, host=HOST)
        return True

    monkeypatch.setattr(automix_live_consent, "arm_now", fake_arm)
    monkeypatch.setattr(settings_automix, "current_mode", lambda: "full_auto")


class _Env:
    def __init__(self, qt_app, vu_path, simulate, armed=True):
        from wing_parser.automix.live_limits import LiveLimits
        from wing_parser.net.address import osc_address
        from wing_parser.ui.automix_live import AutomixLivePanel
        from wing_parser.ui.live_state import LiveState
        from wing_parser.ui.live_wiring import WriteGate
        from wing_parser.ui.main_window import MainWindow
        from wing_parser.ui.session import Session
        from wing_parser import automix

        class _Bar:
            def host(self):
                return HOST

        class _Page:
            pass

        self.page = _Page()
        self.page.state = LiveState.CONNECTED
        self.page.connect_bar = _Bar()
        self.window = MainWindow(Session.open(vu_path))
        self.desk = FakeDesk(identity=_identity())
        self.gate = WriteGate(self.page, transport=_writing_transport(self.desk), timeout=2)
        if armed:
            self.gate.arm.arm(_identity(), show=SHOW, host=HOST)
        self.panel = AutomixLivePanel(
            self.window, gate=self.gate, client_factory=self.desk.client,
            limits=LiveLimits(tick_s=0.0, max_writes_per_tick=4), timeout=5)
        session = self.window.session
        found = automix.propose(session.scene, session._document(),
                                self.panel.view.options_panel.options())
        assert found.changes
        self.start_values = {}
        for change in found.changes:
            self.start_values[osc_address(change.path)] = change.before
            self.desk.leaves[osc_address(change.path)] = _msg(
                osc_address(change.path), change.before)
        self.panel.view.simulate.setChecked(simulate)
        self.panel.view.ack.setChecked(True)

    def tick(self, settle):
        self.panel._pump()
        assert settle(lambda: not self.panel._runner.busy)

    def desk_values(self):
        from wing_parser.net.codec import leaf_value

        return {osc: leaf_value(self.desk.leaves[osc])[0] for osc in self.start_values}


def test_simulate_writes_nothing_but_lists_would_writes(qt_app, vu_path, settle):
    env = _Env(qt_app, vu_path, simulate=True, armed=False)
    before = dict(env.desk.leaves)
    assert env.panel.start()
    env.tick(settle)
    env.tick(settle)
    assert env.desk.sets == []
    assert env.desk.leaves == before
    model = env.panel.view.writes_model
    assert model.rowCount() > 0
    assert model.item(0, 4).text() == "Would write"
    assert env.window.changes_panel.ledger.records() == ()
    env.panel.stop()


def test_real_mode_writes_through_the_gate_and_fills_the_ledger(qt_app, vu_path, settle):
    env = _Env(qt_app, vu_path, simulate=False)
    assert env.panel.start()
    env.tick(settle)
    env.tick(settle)
    sets = env.desk.sets
    assert sets and all(confirm is True for _osc, _value, confirm in sets)
    records = env.window.changes_panel.ledger.records()
    assert len(records) == len(sets)
    assert all(r.show == SHOW and r.identity.serial == _identity().serial for r in records)
    assert env.panel.view.writes_model.item(0, 4).text() == "Sent"
    env.panel.stop()


def test_gate_going_not_ready_stops_the_loop(qt_app, vu_path, settle):
    from wing_parser.ui.live_state import LiveState

    env = _Env(qt_app, vu_path, simulate=False)
    assert env.panel.start()
    env.tick(settle)
    written = len(env.desk.sets)
    env.page.state = LiveState.DISCONNECTED
    env.gate.close()
    assert env.panel._ctx.stop.is_set() and env.panel._ctx.abort.is_set()
    assert env.panel._loop.state.value == "stopped"
    env.panel._pump()
    assert not env.panel._runner.busy and len(env.desk.sets) == written
    assert env.panel.view.start_btn.isEnabled()


def test_revert_automix_restores_the_desk_values(qt_app, vu_path, settle):
    env = _Env(qt_app, vu_path, simulate=False)
    assert env.panel.start()
    env.tick(settle)
    env.tick(settle)
    assert env.desk_values() != env.start_values
    env.panel.stop()
    assert env.panel.view.revert_btn.isEnabled()
    reverted = []
    env.window.changes_panel.ledger.reverted.connect(
        lambda record, _result: reverted.append(record.path))
    assert env.panel.revert()
    assert settle(lambda: not env.panel._runner.busy)
    now = env.desk_values()
    for osc, value in env.start_values.items():
        assert now[osc] == (pytest.approx(value) if isinstance(value, float) else value), osc
    assert reverted
    assert not env.panel.view.revert_btn.isEnabled()


def test_simulate_with_an_armed_gate_still_writes_nothing(qt_app, vu_path, settle):
    env = _Env(qt_app, vu_path, simulate=True, armed=True)
    assert env.gate.arm.armed()
    assert env.panel.start()
    env.tick(settle)
    env.tick(settle)
    assert env.desk.sets == [] and env.panel.view.writes_model.rowCount() > 0
    env.panel.stop()
    assert env.gate.arm.armed()                      # an arm that was not ours stays


def test_real_start_needs_a_fresh_arm_and_stop_disarms(qt_app, vu_path, settle):
    env = _Env(qt_app, vu_path, simulate=False, armed=True)
    calls = []
    original = env.gate.arm.disarm

    def spy():
        calls.append(1)
        original()

    env.gate.arm.disarm = spy
    assert env.panel.start()
    assert calls and env.gate.arm.armed()            # disarmed first, then re-armed
    env.panel.stop()
    assert not env.gate.arm.armed()


def test_start_refusals(qt_app, vu_path, monkeypatch):
    from wing_parser.ui import settings_automix

    env = _Env(qt_app, vu_path, simulate=False)
    env.panel.view.ack.setChecked(False)
    assert not env.panel.start() and "FULL AUTO" in env.panel.view.status.text()
    env.panel.view.ack.setChecked(True)
    monkeypatch.setattr(settings_automix, "current_mode", lambda: "draft")
    assert not env.panel.start() and "Full auto" in env.panel.view.status.text()
    monkeypatch.setattr(settings_automix, "current_mode", lambda: "full_auto")
    env.gate._queue._in_flight = object()            # a Repair / Revert still on the wire
    assert not env.panel.start() and "queued" in env.panel.view.status.text()
    env.gate._queue._in_flight = None
    assert env.panel.start()
    env.panel.stop()


def test_ledger_and_other_writers_are_dead_while_running(qt_app, vu_path, settle):
    env = _Env(qt_app, vu_path, simulate=False)
    ledger = env.window.changes_panel.ledger
    assert env.panel.start()
    assert not ledger.isEnabled() and not env.window.changes_panel.list.isEnabled()
    env.tick(settle)
    env.panel.stop()
    assert ledger.isEnabled()


class _Blocking:
    """A write transport whose first set lands on the desk, then hangs."""

    def __init__(self, desk):
        import threading

        from wing_parser.ui import live_write

        self.release, self.entered = threading.Event(), threading.Event()
        base = _writing_transport(desk)

        def _set(host, osc, value, **kw):
            result = base.set(host, osc, value, **kw)
            self.entered.set()
            self.release.wait(5)
            return result

        self.transport = live_write.WriteTransport(
            identity=base.identity, read=base.read, set=_set)


def test_tick_timeout_stops_the_loop_and_every_write_is_recorded(qt_app, vu_path, settle):
    env = _Env(qt_app, vu_path, simulate=False)
    block = _Blocking(env.desk)
    env.gate._transport = block.transport
    env.panel._timeout = 0.3
    assert env.panel.start()
    env.panel._pump()
    assert settle(lambda: env.panel._loop.state.value == "stopped", 5)
    panel = env.panel
    assert panel._worker_busy() and panel._ctx.stop.is_set() and panel._ctx.abort.is_set()
    assert not panel.view.start_btn.isEnabled()               # still locked: a thread runs
    assert not env.window.changes_panel.ledger.isEnabled()
    panel._pump()
    assert not panel._runner.busy                              # no second tick
    assert not panel.start() and "already running" in panel.view.status.text()
    block.release.set()
    assert settle(lambda: not panel._worker_busy() and panel.view.start_btn.isEnabled(), 5)
    sets = env.desk.sets
    assert len(sets) == 1                                      # the stopped loop wrote no more
    assert len(env.window.changes_panel.ledger.records()) == len(sets)
    assert env.window.changes_panel.ledger.isEnabled()


def test_revert_leaves_an_operator_moved_leaf_alone(qt_app, vu_path, settle):
    env = _Env(qt_app, vu_path, simulate=False)
    assert env.panel.start()
    env.tick(settle)
    env.tick(settle)
    osc = env.desk.sets[0][0]
    env.desk.leaves[osc] = _msg(osc, 3.0)                      # the operator grabs it
    env.panel.stop()
    assert env.panel.revert()
    assert settle(lambda: not env.panel._runner.busy and not env.panel._worker_busy())
    assert env.desk_values()[osc] == 3.0
    others = [o for o in env.start_values if o != osc and o in {s[0] for s in env.desk.sets}]
    assert others
    for other in others:
        value = env.start_values[other]
        assert env.desk_values()[other] == (pytest.approx(value) if isinstance(value, float) else value)
    assert "left" in env.panel.view.status.text()
    assert not env.gate.arm.armed()                            # the revert's arm is released


def test_leaving_full_auto_in_settings_stops_a_live_run(qt_app, vu_path, settle):
    env = _Env(qt_app, vu_path, simulate=False)
    assert env.panel.start()
    env.panel.mode_changed("draft")
    assert env.panel._loop.state.value == "stopped" and not env.gate.arm.armed()


def test_second_open_reuses_the_panel(qt_app, vu_path):
    from wing_parser.ui.automix_live import open_live
    from wing_parser.ui.main_window import MainWindow
    from wing_parser.ui.session import Session

    window = MainWindow(Session.open(vu_path))
    open_live(window)
    first = window._automix_live
    open_live(window)
    assert window._automix_live is first
    first.close()


def test_rearm_after_a_gate_drop_refreshes_revert(qt_app, vu_path, settle):
    from wing_parser.ui.live_state import LiveState

    env = _Env(qt_app, vu_path, simulate=False)
    assert env.panel.start()
    env.tick(settle)
    env.page.state = LiveState.DISCONNECTED
    env.gate.close()
    assert not env.panel.view.revert_btn.isEnabled()
    env.page.state = LiveState.CONNECTED
    env.gate.changed.emit()
    assert env.panel.view.revert_btn.isEnabled()
