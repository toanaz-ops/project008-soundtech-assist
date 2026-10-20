"""Wave 5 (spec sections 4 and 9): every settled write and revert reaches the
durable log, at all three apply levels, and a log failure never blocks anything.

Offscreen, `FakeDesk` only -- no socket, no real console.
"""
from __future__ import annotations

import threading

import pytest

pytest.importorskip("PySide6.QtWidgets")

from tests.fake_desk import FakeDesk
from wing_parser import writelog
from wing_parser.net.codec import OscMessage
from wing_parser.net.identity import WingIdentity

HOST = "192.168.128.28"
PATH = "ae_data.ch.1.send.8.mode"
OSC = "/ch/1/send/8/mode"
BECAUSE = "G8:ch.1.send.8"
SHOW = {"code": "AZ-1501", "name": "BIDV Gala", "venue": "GEM Center"}


def _identity():
    return WingIdentity(ip=HOST, name="WING-GIAQUY", model="wing-rack",
                        serial="01009Y90604AAE", firmware="3.1")


@pytest.fixture
def knowledge(tmp_path, monkeypatch):
    from wing_parser import config

    monkeypatch.setattr(config, "knowledge_dir", lambda override=None: tmp_path)
    return tmp_path


class _Page:
    def __init__(self):
        from wing_parser.ui.live_state import LiveState

        self.state = LiveState.CONNECTED

        class _Bar:
            def host(self_inner):
                return HOST

        self.connect_bar = _Bar()


class _Rig:
    """Window stand-in, gate, Changes panel and the sink, wired as in the app."""

    def __init__(self, vu_path, desk, level, transport=None):
        from wing_parser.ui.apply_level import ApplyLevel
        from wing_parser.ui.changes_panel import ChangesPanel
        from wing_parser.ui.live_wiring import WriteGate
        from wing_parser.ui.session import Session
        from wing_parser.ui import write_log_sink

        rig = self

        class _W:
            def __init__(self):
                self.session = Session.open(vu_path)

            def _refresh(self):
                rig.refreshed += 1

        self.refreshed = 0
        self.window = _W()
        self.desk = desk
        self.transport = transport or desk.write_transport()
        self.gate = WriteGate(_Page(), transport=self.transport, timeout=2)
        self.gate.arm.arm(_identity(), SHOW)
        self.gate.arm.level = ApplyLevel[level]
        self.panel = ChangesPanel()
        self.panel.attach_gate(self.gate)
        self.panel.attach_window(self.window)
        self.sink = write_log_sink.install(self.window, self.panel)
        self.patch = self.window.session.record_value(
            PATH, "PRE", label="Set the send to PRE (ch.1.send.8)", because=BECAUSE)
        self.panel.set_changes(self.window.session.changes())

    def send(self, settle):
        """Drive one repair at this rig's level, up to a settled ledger row."""
        from wing_parser.ui import write_router
        from wing_parser.ui.apply_level import ApplyLevel

        level = self.gate.arm.level
        if level is ApplyLevel.MANUAL:
            row = self.panel.list.itemWidget(self.panel.list.item(0))
            opened = []
            row.dialog_opened.connect(opened.append)
            row.send_button.click()
            dialog = opened[0]
        else:
            dialog = write_router.route_repair(
                self.gate, self.patch, 5, transport=self.transport, timeout=2,
                on_sent=self.panel.record_sent, on_error=self.panel.report_write_error)
        if dialog is not None:
            assert settle(lambda: dialog.apply_button.isEnabled())
            dialog.apply_button.click()
        assert settle(lambda: self.panel.has_ledger(), limit_s=4)
        return self


def _desk(**readbacks):
    return FakeDesk(identity=_identity(),
                    leaves={OSC: OscMessage(OSC, "s", ("POST",))},
                    readbacks=readbacks)


def _entries(knowledge):
    entries, skipped = writelog.read_show("AZ-1501", knowledge)
    assert skipped == 0
    return entries


@pytest.mark.parametrize("level", ["MANUAL", "DELAYED", "IMMEDIATE"])
def test_a_settled_repair_writes_one_repair_line(
        qt_app, settle, knowledge, vu_path, level):
    rig = _Rig(vu_path, _desk(), level).send(settle)
    [entry] = _entries(knowledge)

    assert entry.kind == "repair"
    assert entry.finding == BECAUSE
    assert entry.label == "Set the send to PRE (ch.1.send.8)"
    assert entry.address == OSC and entry.path == PATH
    assert (entry.file_before, entry.desk_before) == ("POST", "POST")
    assert (entry.written, entry.readback, entry.outcome) == ("PRE", "PRE", "sent")
    assert entry.show_code == "AZ-1501"
    assert (entry.show, entry.venue) == ("BIDV Gala", "GEM Center")
    assert entry.desk["serial"] == "01009Y90604AAE"
    assert entry.desk["name"] == "WING-GIAQUY"
    assert entry.scene == rig.window.session.path.name
    assert entry.app == __import__("wing_parser").__version__
    assert rig.sink.warning == ""


def test_a_clamped_write_is_logged_as_clamped(qt_app, settle, knowledge, vu_path):
    _Rig(vu_path, _desk(**{OSC: "GRP"}), "IMMEDIATE").send(settle)
    [entry] = _entries(knowledge)
    assert (entry.outcome, entry.readback) == ("clamped", "GRP")


def test_a_revert_writes_a_revert_line_with_the_repairs_finding(
        qt_app, settle, knowledge, vu_path):
    rig = _Rig(vu_path, _desk(), "IMMEDIATE").send(settle)
    [record] = rig.panel.ledger.records()

    rig.panel.ledger._revert_one(record)
    assert settle(lambda: len(rig.panel.ledger.records()) >= 0
                  and len(writelog.read_show("AZ-1501", knowledge)[0]) == 2)

    repair, revert = _entries(knowledge)
    assert repair.kind == "repair" and revert.kind == "revert"
    assert revert.finding == BECAUSE, "W14: the last repair on that path"
    assert revert.path == PATH and revert.written == "POST"
    assert revert.desk["serial"] == "01009Y90604AAE"
    assert revert.show_code == "AZ-1501"
    assert revert.outcome == "sent"


def test_a_revert_of_an_unknown_path_has_a_null_finding(
        qt_app, settle, knowledge, vu_path):
    from wing_parser.net.write import SetResult
    from wing_parser.ui.live_write import SentWrite

    rig = _Rig(vu_path, _desk(), "IMMEDIATE")
    record = SentWrite(address=OSC, path=PATH, desk_before="POST", written="PRE",
                       result=SetResult(OSC, "PRE", "PRE", False, "PRE", True),
                       identity=_identity(), show=SHOW)
    rig.panel.ledger.reverted.emit(record, record.result)
    [entry] = _entries(knowledge)
    assert entry.kind == "revert" and entry.finding is None


def test_a_log_failure_never_blocks_the_write_or_anything_after_it(
        qt_app, settle, knowledge, vu_path, monkeypatch):
    """W3: ANY Exception from the append -- not just OSError."""
    from wing_parser.ui.texts import text

    def boom(entry, directory=None):
        raise RuntimeError("disk on fire")

    monkeypatch.setattr(writelog, "append", boom)
    rig = _Rig(vu_path, _desk(**{OSC: "GRP"}), "MANUAL").send(settle)
    row = rig.panel.list.itemWidget(rig.panel.list.item(0))

    assert len(rig.panel.ledger.records()) == 1, "the ledger row still landed"
    assert text("console.write.clamped").split("{")[0].strip() in row.badge.text()
    from wing_parser.edit import pointer
    assert pointer.read(rig.window.session._document(), PATH) == "GRP", (
        "the scene correction still happened")
    assert "disk on fire" in rig.sink.warning
    assert str(knowledge) in rig.sink.warning, "the warning names the folder"
    assert rig.panel.log_warning_label.text() == rig.sink.warning
    assert not rig.panel.log_warning_label.isHidden()


def test_a_write_without_a_show_warns_instead_of_crashing(
        qt_app, settle, knowledge, vu_path):
    rig = _Rig(vu_path, _desk(), "IMMEDIATE")
    rig.gate.arm.show = None
    rig.send(settle)
    assert rig.sink.warning != ""
    assert writelog.list_shows(knowledge) == []


@pytest.mark.parametrize("level", ["IMMEDIATE", "DELAYED"])
def test_a_write_that_settles_after_gate_close_still_logs_its_desk(
        qt_app, settle, knowledge, vu_path, level):
    """W13: close() disarms (identity and show -> None) while the write is
    still on the wire; the line must still name the desk and the show."""
    from wing_parser.ui import live_write, write_router

    desk = _desk()
    inner = desk.write_transport()
    started, release = threading.Event(), threading.Event()

    def slow_set(host, osc, value, **kw):
        started.set()
        release.wait(3)
        return inner.set(host, osc, value, **kw)

    transport = live_write.WriteTransport(
        identity=inner.identity, read=inner.read, set=slow_set)
    rig = _Rig(vu_path, desk, level, transport=transport)
    dialog = write_router.route_repair(
        rig.gate, rig.patch, 5, transport=transport, timeout=5,
        on_sent=rig.panel.record_sent)
    if dialog is not None:
        assert settle(lambda: dialog.apply_button.isEnabled())
        dialog.apply_button.click()
    assert settle(started.is_set)

    rig.gate.close()
    release.set()
    assert settle(lambda: rig.panel.has_ledger(), limit_s=4)

    [entry] = _entries(knowledge)
    assert entry.desk["serial"] == "01009Y90604AAE"
    assert entry.show_code == "AZ-1501"


def test_the_sink_does_not_import_the_net_write_module():
    """The AST allow-list stays exactly one module, `live_write.py`."""
    import inspect

    from wing_parser.ui import write_log_sink

    source = inspect.getsource(write_log_sink)
    assert "net.write" not in source and "net import write" not in source
