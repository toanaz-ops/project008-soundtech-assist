"""Wave 5, W13: desk identity and the show travel WITH each write.

They are copied at submit time. They are never read from the gate when the
write settles, because `WriteGate.close()` disarms (clearing both) while an
in-flight write can still settle afterwards.
"""
from __future__ import annotations

import threading

import pytest

pytest.importorskip("PySide6.QtWidgets")

from tests.fake_desk import FakeDesk
from wing_parser.net.codec import OscMessage
from wing_parser.net.identity import WingIdentity

HOST = "192.168.128.28"
PATH = "ae_data.ch.1.send.8.mode"
OSC = "/ch/1/send/8/mode"
SHOW = {"code": "AZ-1501", "name": "BIDV Gala", "venue": "GEM Center"}


def _identity():
    return WingIdentity(ip=HOST, name="WING-GIAQUY", model="wing-rack",
                        serial="01009Y90604AAE", firmware="3.1")


class _Page:
    def __init__(self):
        from wing_parser.ui.live_state import LiveState

        self.state = LiveState.CONNECTED

        class _Bar:
            def host(self_inner):
                return HOST

        self.connect_bar = _Bar()


def _patch():
    from wing_parser.edit.journal import Patch

    return Patch(path=PATH, before="POST", after="PRE", because="G8:ch.1.send.8",
                 label="Set the send to PRE (ch.1.send.8)")


def _desk():
    return FakeDesk(identity=_identity(),
                    leaves={OSC: OscMessage(OSC, "s", ("POST",))},
                    readbacks={OSC: "PRE"})


def _gate(transport, level):
    from wing_parser.ui.live_wiring import WriteGate

    gate = WriteGate(_Page(), transport=transport, timeout=2)
    gate.arm.arm(_identity(), SHOW)
    gate.arm.level = level
    return gate


def test_the_record_carries_identity_and_show_when_immediate(qt_app, settle):
    from wing_parser.ui import write_router
    from wing_parser.ui.apply_level import ApplyLevel

    desk = _desk()
    gate = _gate(desk.write_transport(), ApplyLevel.IMMEDIATE)
    sent = []
    write_router.route_repair(gate, _patch(), 5, transport=desk.write_transport(),
                              timeout=2, on_sent=lambda p, r: sent.append(r))
    assert settle(lambda: sent)
    assert sent[0].identity.serial == "01009Y90604AAE"
    assert sent[0].show == SHOW


def test_the_record_carries_identity_and_show_when_delayed(qt_app, settle):
    from wing_parser.ui import write_router
    from wing_parser.ui.apply_level import ApplyLevel

    desk = _desk()
    gate = _gate(desk.write_transport(), ApplyLevel.DELAYED)
    sent = []
    dialog = write_router.route_repair(
        gate, _patch(), 5, transport=desk.write_transport(), timeout=2,
        on_sent=lambda p, r: sent.append(r))
    assert settle(lambda: dialog.apply_button.isEnabled())
    dialog.apply_button.click()
    assert settle(lambda: sent)
    assert sent[0].identity.serial == "01009Y90604AAE"
    assert sent[0].show == SHOW


def test_the_show_is_a_copy_not_the_gates_live_dict(qt_app, settle):
    from wing_parser.ui import write_router
    from wing_parser.ui.apply_level import ApplyLevel

    desk = _desk()
    gate = _gate(desk.write_transport(), ApplyLevel.IMMEDIATE)
    sent = []
    write_router.route_repair(gate, _patch(), 5, transport=desk.write_transport(),
                              timeout=2, on_sent=lambda p, r: sent.append(r))
    assert settle(lambda: sent)
    assert sent[0].show is not gate.arm.show


@pytest.mark.parametrize("level_name", ["IMMEDIATE", "DELAYED"])
def test_a_write_that_settles_after_gate_close_still_has_its_desk(
        qt_app, settle, level_name):
    """The exact W13 trap: close() disarms, the in-flight write settles after."""
    from wing_parser.ui import live_write, write_router
    from wing_parser.ui.apply_level import ApplyLevel

    desk = _desk()
    inner = desk.write_transport()
    started, release = threading.Event(), threading.Event()

    def slow_set(host, osc, value, **kw):
        started.set()
        release.wait(3)
        return inner.set(host, osc, value, **kw)

    transport = live_write.WriteTransport(
        identity=inner.identity, read=inner.read, set=slow_set)
    level = ApplyLevel[level_name]
    gate = _gate(transport, level)
    sent = []
    dialog = write_router.route_repair(
        gate, _patch(), 5, transport=transport, timeout=5,
        on_sent=lambda p, r: sent.append(r))
    if level is ApplyLevel.DELAYED:
        assert settle(lambda: dialog.apply_button.isEnabled())
        dialog.apply_button.click()
    assert settle(started.is_set)

    gate.close()                                   # disarms: identity -> None
    assert gate.arm.identity is None and gate.arm.show is None
    release.set()

    assert settle(lambda: sent, limit_s=4)
    assert sent[0].identity.serial == "01009Y90604AAE"
    assert sent[0].show == SHOW
