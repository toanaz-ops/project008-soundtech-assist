"""Spec §9.2: the journal row's Send button, its badges, and what a result
does to the scene. Offscreen, no socket -- `FakeDesk` throughout.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")

from tests.fake_desk import FakeDesk
from wing_parser.net.codec import OscMessage
from wing_parser.net.identity import WingIdentity

HOST = "192.168.128.28"
PATH = "ae_data.ch.1.send.8.mode"
OSC = "/ch/1/send/8/mode"


def _identity():
    return WingIdentity(ip=HOST, name="WING-GIAQUY", model="wing-rack",
                        serial="01009Y90604AAE", firmware="3.1-0-g9f314617:release")


def _patch(before="POST", after="PRE", path=PATH):
    from wing_parser.edit.journal import Patch
    return Patch(path=path, before=before, after=after, because="G8:ch.1.send.8",
                 label="Set the send to PRE (ch.1.send.8)")


def _gate(qt_app, desk, state=None):
    from wing_parser.ui.live_state import LiveState
    from wing_parser.ui.live_wiring import WriteGate

    class _Bar:
        def host(self):
            return HOST

    class _Page:
        pass

    page = _Page()
    page.state = state or LiveState.CONNECTED
    page.connect_bar = _Bar()
    return WriteGate(page, transport=desk.write_transport(), timeout=2)


def _row(qt_app, gate, patch=None):
    from wing_parser.ui.changes_send import SendRow
    return SendRow(patch or _patch(), gate)


# -- the button's one meaning (§2.2) ------------------------------------


def test_send_is_disabled_only_by_a_closed_gate(qt_app):
    from wing_parser.ui.live_state import LiveState
    from wing_parser.ui.texts import text

    desk = FakeDesk(identity=_identity())
    gate = _gate(qt_app, desk, state=LiveState.DISCONNECTED)
    row = _row(qt_app, gate)
    assert row.send_button.isEnabled() is False
    assert row.send_button.toolTip() == text("console.write.blocked")


def test_send_stays_enabled_while_unarmed(qt_app):
    """§2.2: being unarmed does NOT disable it -- clicking while unarmed
    opens ArmWriteDialog first, so the button always means one thing."""
    desk = FakeDesk(identity=_identity())
    gate = _gate(qt_app, desk)
    row = _row(qt_app, gate)
    assert gate.arm.armed() is False
    assert row.send_button.isEnabled() is True


def test_clicking_send_while_unarmed_arms_before_it_counts_down(qt_app, monkeypatch):
    from wing_parser.ui import write_router

    desk = FakeDesk(identity=_identity(),
                    leaves={OSC: OscMessage(OSC, "s", ("POST",))})
    gate = _gate(qt_app, desk)
    calls = []
    monkeypatch.setattr(write_router, "arm_now",
                        lambda g, parent=None, **kw: calls.append(g) or False)
    row = _row(qt_app, gate)
    row.send_button.click()
    assert calls == [gate] and desk.sets == []


def test_manuals_send_opens_the_countdown_not_a_bare_confirm(qt_app):
    """§2.2: Manual exists so the operator SEES the numbers, and that screen
    is where the numbers are."""
    from wing_parser.ui.write_delay_dialog import DelayedWriteDialog

    desk = FakeDesk(identity=_identity(),
                    leaves={OSC: OscMessage(OSC, "s", ("POST",))},
                    readbacks={OSC: "PRE"})
    gate = _gate(qt_app, desk)
    gate.arm.arm(_identity())
    row = _row(qt_app, gate)
    opened = []
    row.dialog_opened.connect(opened.append)
    row.send_button.click()
    assert opened and isinstance(opened[0], DelayedWriteDialog)
    opened[0].reject()


# -- the three badges (§2.4) --------------------------------------------


def _record(readback, matched, written="PRE", desk_before="POST"):
    from wing_parser.net.write import SetResult
    from wing_parser.ui.live_write import SentWrite

    return SentWrite(address=OSC, path=PATH, desk_before=desk_before,
                     written=written,
                     result=SetResult(OSC, written, str(written), False,
                                      readback, matched))


@pytest.mark.parametrize("readback,matched,key", [
    ("PRE", True, "console.write.sent"),
    ("GRP", False, "console.write.clamped"),
    (None, False, "console.write.no_reply"),
])
def test_each_outcome_puts_its_own_badge_on_the_row(qt_app, readback, matched, key):
    from wing_parser.ui.texts import text

    desk = FakeDesk(identity=_identity())
    row = _row(qt_app, _gate(qt_app, desk))
    row.set_badge(_record(readback, matched))
    assert text(key).split("{")[0].strip() in row.badge.text()


# -- what a result does to the scene (F8) -------------------------------


def _window(qt_app, vu_path):
    from wing_parser.ui.session import Session

    class _W:
        def __init__(self):
            self.session = Session.open(vu_path)
            self.refreshed = 0

        def _refresh(self):
            self.refreshed += 1

    return _W()


def test_a_matched_write_leaves_the_scene_where_repair_put_it(qt_app, vu_path):
    from wing_parser.ui import write_router

    window = _window(qt_app, vu_path)
    patch = window.session.record_value(PATH, "PRE", label="x", because="G8")
    before_len = len(window.session.changes())

    write_router.apply_result(window, patch, _record("PRE", True))

    assert len(window.session.changes()) == before_len, (
        "matched -> the leaf already holds `after`; no second patch")


def test_a_clamp_rewrites_the_scene_so_the_finding_reflects_the_desk(qt_app, vu_path):
    from wing_parser.edit import pointer
    from wing_parser.ui import write_router

    window = _window(qt_app, vu_path)
    patch = window.session.record_value(PATH, "PRE", label="x", because="G8")

    write_router.apply_result(window, patch, _record("GRP", False))

    assert pointer.read(window.session._document(), PATH) == "GRP"
    assert window.refreshed >= 1


def test_a_silent_desk_leaves_the_scene_exactly_as_repair_set_it(qt_app, vu_path):
    from wing_parser.edit import pointer
    from wing_parser.ui import write_router

    window = _window(qt_app, vu_path)
    patch = window.session.record_value(PATH, "PRE", label="x", because="G8")
    before_len = len(window.session.changes())

    write_router.apply_result(window, patch, _record(None, False))

    assert pointer.read(window.session._document(), PATH) == "PRE"
    assert len(window.session.changes()) == before_len


# -- the dock, the panel, and Undo (§9.2) -------------------------------


def _panel(qt_app, gate, window):
    from wing_parser.ui.changes_panel import ChangesPanel

    panel = ChangesPanel()
    panel.attach_gate(gate)
    panel.attach_window(window)
    return panel


def test_a_successful_send_appends_exactly_one_ledger_row(qt_app, vu_path):
    desk = FakeDesk(identity=_identity())
    window = _window(qt_app, vu_path)
    panel = _panel(qt_app, _gate(qt_app, desk), window)
    patch = window.session.record_value(PATH, "PRE", label="x", because="G8")

    panel.record_sent(patch, _record("PRE", True))

    assert len(panel.ledger.records()) == 1
    assert panel.has_ledger() is True


def test_undo_removes_the_journal_row_and_leaves_the_ledger_row(qt_app, vu_path):
    """F7: its rows survive an Undo, which is a FILE-side action -- a desk
    change the UI cannot revert is worse than a longer panel."""
    desk = FakeDesk(identity=_identity())
    window = _window(qt_app, vu_path)
    panel = _panel(qt_app, _gate(qt_app, desk), window)
    patch = window.session.record_value(PATH, "PRE", label="x", because="G8")
    panel.record_sent(patch, _record("PRE", True))

    window.session.undo()
    panel.set_changes(window.session.changes())

    assert panel.list.count() == 0
    assert len(panel.ledger.records()) == 1
    assert panel.ledger.row_widget(0).revert_button.isEnabled() is True


def test_clicking_send_end_to_end_reaches_the_ledger_and_the_scene(qt_app, settle, vu_path):
    """Driven through the button, not by calling `record_sent` directly:
    armed gate, click Send, the countdown opens, click Apply now, and the
    result reaches `ChangesPanel.record_sent` -- the ledger, the badge and
    F8's scene correction all follow from the click alone."""
    from wing_parser.edit import pointer
    from wing_parser.ui.texts import text

    desk = FakeDesk(identity=_identity(),
                    leaves={OSC: OscMessage(OSC, "s", ("POST",))})
    window = _window(qt_app, vu_path)
    gate = _gate(qt_app, desk)
    gate.arm.arm(_identity())
    panel = _panel(qt_app, gate, window)
    window.session.record_value(PATH, "PRE", label="x", because="G8")
    panel.set_changes(window.session.changes())

    row = panel.list.itemWidget(panel.list.item(0))
    opened = []
    row.dialog_opened.connect(opened.append)
    row.send_button.click()

    assert opened
    dialog = opened[0]
    assert settle(lambda: dialog.apply_button.isEnabled())
    dialog.apply_button.click()

    assert settle(lambda: panel.has_ledger())
    assert len(panel.ledger.records()) == 1
    assert text("console.write.sent").split("{")[0].strip() in row.badge.text()
    assert pointer.read(window.session._document(), PATH) == "PRE", (
        "F8 matched -> the leaf already holds `after`; no second patch needed")


def test_every_journal_row_carries_its_own_send_button(qt_app, vu_path):
    from wing_parser.ui.changes_send import SendRow

    desk = FakeDesk(identity=_identity())
    window = _window(qt_app, vu_path)
    panel = _panel(qt_app, _gate(qt_app, desk), window)
    window.session.record_value(PATH, "PRE", label="x", because="G8")
    window.session.record_value("ae_data.ch.2.send.8.mode", "PRE",
                                label="y", because="G8")
    panel.set_changes(window.session.changes())

    assert panel.list.count() == 2
    for index in range(2):
        widget = panel.list.itemWidget(panel.list.item(index))
        assert isinstance(widget, SendRow)
