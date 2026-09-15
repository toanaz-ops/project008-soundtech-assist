"""The Console page's connect bar: address, Connect/Disconnect, the lamp.

No socket anywhere: every connect here runs against
`FakeDesk().transport()` (spec S9.1), and the tests that need a desk
which never answers replace just that transport callable with a gated
stub, so nothing waits real seconds.

`test_every_lamp_style_has_a_rule_in_the_generated_stylesheet` is the
load-bearing one. `set_style` on a QLabel resolves to nothing unless
`theme.qss` carries a `QLabel[azStyle="..."]` rule, and before this task
it carried `azStyle` rules for QPushButton only -- so the lamp would
have been invisible on the desk with every widget-level assertion green.
"""

import dataclasses
import threading

import pytest

pytest.importorskip("PySide6.QtWidgets")

HOST = "192.168.128.28"


def _identity():
    from wing_parser.net.identity import WingIdentity

    return WingIdentity(
        ip=HOST,
        name="WING-GIAQUY",
        model="wing-rack",
        serial="01009Y90604AAE",
        firmware="3.1-0-g9f314617:release",
    )


def _bar(desk=None, **kwargs):
    """A ConnectBar over a FakeDesk that answers the handshake."""
    from tests.fake_desk import FakeDesk
    from wing_parser.ui.live_connect_bar import ConnectBar

    desk = FakeDesk(identity=_identity()) if desk is None else desk
    return ConnectBar(transport=desk.transport(), **kwargs)


def _stuck_bar(gate, **kwargs):
    """A ConnectBar whose handshake answers nothing until `gate` is set."""
    from tests.fake_desk import FakeDesk
    from wing_parser.ui.live_connect_bar import ConnectBar

    def stuck(host):
        gate.wait(timeout=5.0)
        return _identity()

    transport = dataclasses.replace(FakeDesk().transport(), identity=stuck)
    return ConnectBar(transport=transport, **kwargs)


def test_connect_puts_the_identity_on_the_bar(qt_app, settle):
    bar = _bar()
    bar.address.setCurrentText(HOST)
    seen = []
    bar.connected.connect(seen.append)

    assert bar.connect_now()
    assert settle(lambda: seen), "the connected signal never arrived"
    assert seen == [_identity()]
    assert "WING-GIAQUY" in bar.identity_label.text()
    assert "wing-rack" in bar.identity_label.text()
    assert bar.lamp.property("azStyle") == "ok"
    assert not bar.connect_button.isEnabled()
    assert bar.disconnect_button.isEnabled()


def test_disconnect_clears_the_readout_and_the_lamp(qt_app, settle):
    bar = _bar()
    bar.address.setCurrentText(HOST)
    ended = []
    bar.disconnected.connect(lambda: ended.append(True))
    bar.connect_now()
    assert settle(lambda: bar.lamp.property("azStyle") == "ok")

    bar.disconnect_button.click()
    assert ended == [True]
    assert bar.identity_label.text() == ""
    assert bar.lamp.property("azStyle") == "faded"
    assert bar.connect_button.isEnabled()


def test_disconnect_settles_a_connect_still_in_flight(qt_app, settle):
    """A disconnect mid-handshake must not be undone by the late answer.

    `disconnect_now` cancels the running call; without that the gated
    identity below lands after the bar has said disconnected and drags
    it back to connected.
    """
    gate = threading.Event()
    bar = _stuck_bar(gate)
    bar.address.setCurrentText(HOST)
    seen = []
    bar.connected.connect(seen.append)
    assert bar.connect_now()

    bar.disconnect_now()
    assert bar.lamp.property("azStyle") == "faded"
    gate.set()
    # The worker is free to return now; a call that was NOT settled
    # would deliver during this pump.
    assert not settle(lambda: bool(seen), limit_s=0.3), "the late answer landed"
    assert seen == []
    assert bar.lamp.property("azStyle") == "faded"
    assert bar.identity_label.text() == ""
    assert bar.connect_button.isEnabled(), "and the bar is usable again"


def test_a_timeout_shows_one_error_line_naming_the_host(qt_app, settle):
    """The 5 s backstop, run at 0 s so no test waits (workers.py:109-114).

    The brief cites this as workers.py:97-99; re-read on 2026-09-16, the
    `timeout` override lives at :109 (docstring) and :114 (the branch).
    """
    from wing_parser.ui.workers import CallTimedOut

    gate = threading.Event()
    bar = _stuck_bar(gate, timeout=0)
    bar.address.setCurrentText(HOST)
    failures = []
    bar.failed.connect(failures.append)

    assert bar.connect_now()
    try:
        # Not "the host appears": the running line names it too. The
        # backstop firing is what this waits for.
        assert settle(lambda: failures), "the backstop never fired"
        line = bar.status_label.text()
        assert "\n" not in line, f"more than one line: {line!r}"
        assert HOST in line and "0 s" in line
        assert bar.lamp.property("azStyle") == "danger"
        assert isinstance(failures[0], CallTimedOut)
        assert not bar.connect_button.isEnabled(), "error needs a reset first"
    finally:
        gate.set()


def test_a_refused_connect_reddens_the_lamp_and_reports_the_reason(
        qt_app, settle):
    """`query_identity`'s own TimeoutError, passed through untranslated."""
    from tests.fake_desk import FakeDesk
    from wing_parser.ui.live_connect_bar import ConnectBar

    desk = FakeDesk(identity=TimeoutError(f"no console answered at {HOST}"))
    bar = ConnectBar(transport=desk.transport())
    bar.address.setCurrentText(HOST)
    failures = []
    bar.failed.connect(failures.append)

    assert bar.connect_now()
    assert settle(lambda: failures)
    assert isinstance(failures[0], TimeoutError)
    assert HOST in bar.status_label.text()
    assert "no console answered" in bar.status_label.text()
    assert bar.lamp.property("azStyle") == "danger"
    assert bar.identity_label.text() == ""


def test_the_lamp_carries_the_style_for_every_state(qt_app):
    from wing_parser.ui.live_connect_bar import LAMP_STYLES
    from wing_parser.ui.live_state import LiveState

    bar = _bar()
    expected = {
        LiveState.DISCONNECTED: "faded",
        LiveState.CONNECTING: "warn",
        LiveState.WALKING: "warn",
        LiveState.PULLING: "warn",
        LiveState.CONNECTED: "ok",
        LiveState.WATCHING: "ok",
        LiveState.ERROR: "danger",
        LiveState.LOST: "danger",
    }
    assert set(LAMP_STYLES) == set(LiveState), "a state with no lamp style"
    for state, style in expected.items():
        bar.set_state(state)
        assert bar.lamp.property("azStyle") == style, state


def test_every_lamp_style_has_a_rule_in_the_generated_stylesheet():
    """The trap: `set_style` on a QLabel resolves to nothing without one."""
    from wing_parser.ui.live_connect_bar import LAMP_STYLES
    from wing_parser.ui.theme import qss

    sheet = qss.build()
    for style in sorted(set(LAMP_STYLES.values())):
        assert f'QLabel[azStyle="{style}"]' in sheet, style
    assert "$" not in sheet, "an unsubstituted $token reached the lamp rules"


def test_the_lamp_really_takes_its_colour_from_the_stylesheet(qt_app):
    """A selector that exists is not yet a lamp that is coloured.

    The generated sheet is applied to the application (and restored
    afterwards) and the polished palette read back: a rule Qt failed to
    match would leave the lamp on the plain $text colour with the
    selector still present in the string.
    """
    from PySide6.QtGui import QPalette

    from wing_parser.ui.live_connect_bar import LAMP_STYLES
    from wing_parser.ui.theme import qss, tokens

    bar = _bar()
    previous = qt_app.styleSheet()
    qt_app.setStyleSheet(qss.build())
    try:
        for state, style in LAMP_STYLES.items():
            bar.set_state(state)
            shown = bar.lamp.palette().color(QPalette.ColorRole.WindowText)
            assert shown.name() == tokens.hex_str(style), state
    finally:
        qt_app.setStyleSheet(previous)


def test_the_address_combo_offers_the_remembered_consoles(qt_app):
    bar = _bar()
    bar.set_consoles(["192.168.128.28", "10.0.0.9"])

    offered = [bar.address.itemText(i) for i in range(bar.address.count())]
    assert offered == ["192.168.128.28", "10.0.0.9"]
    assert bar.host() == "192.168.128.28", "most recent is the one offered"
    assert bar.address.isEditable(), "a new desk must be typeable"
    bar.address.setCurrentText("  10.0.0.7  ")
    assert bar.host() == "10.0.0.7", "the typed address, trimmed"


def test_connecting_remembers_the_address(qt_app, settle):
    """The bar does not persist -- it hands the owner the address it used.

    Persisting is the window's job (tasks 11/13); what the bar owes it is
    `host()` at the moment the connect lands, which is what an owner
    feeds to `state_store.remember_console`.
    """
    from wing_parser.ui import state_store

    bar = _bar()
    bar.set_consoles(["10.0.0.9"])
    bar.address.setCurrentText(HOST)
    used = []
    bar.connected.connect(lambda identity: used.append(bar.host()))

    assert bar.connect_now()
    assert settle(lambda: used)
    assert used == [HOST]
    assert state_store.remember_console(["10.0.0.9"], used[0]) == [
        HOST, "10.0.0.9"]


def test_cancel_chrome_appears_while_the_connect_runs(qt_app):
    from wing_parser.ui.texts import text

    gate = threading.Event()
    bar = _stuck_bar(gate)
    bar.address.setCurrentText(HOST)
    try:
        assert bar.connect_now()
        assert bar.cancel_button.isVisibleTo(bar)
        assert not bar.connect_button.isEnabled()
        assert bar.lamp.property("azStyle") == "warn"
        assert HOST in bar.status_label.text()
        bar.cancel_button.click()
    finally:
        gate.set()

    assert not bar.cancel_button.isVisibleTo(bar)
    assert bar.status_label.text() == text("console.cancelled")
    assert bar.lamp.property("azStyle") == "faded"
    assert bar.connect_button.isEnabled()


def test_a_second_connect_is_refused_while_one_runs(qt_app):
    from wing_parser.ui.texts import text

    gate = threading.Event()
    bar = _stuck_bar(gate)
    bar.address.setCurrentText(HOST)
    try:
        assert bar.connect_now()
        assert not bar.connect_now()
        assert bar.status_label.text() == text("console.busy")
    finally:
        gate.set()
        bar.cancel()


def test_an_empty_address_starts_no_call(qt_app):
    from wing_parser.ui.texts import text

    bar = _bar()
    bar.address.setCurrentText("   ")
    assert not bar.connect_now()
    assert bar.status_label.text() == text("console.no_address")
    assert bar.lamp.property("azStyle") == "faded"


# -- DiscoveryPanel: inventory, and the unresolved banner --------------------
#
# The 2026-08-23 incident this banner exists for: a walk opened a watch on
# 16 leaves with seven top-level families unresolved
# (docs/handoff/2026-08-23-live-watch-acceptance-complete.md); an immediate
# rerun resolved all 220. `WatchList.addresses` here is a bag of dummy leaf
# addresses -- FakeDesk._walk takes its leaf TOTAL from `leaves` and its
# per-family breakdown from `strips` independently (fake_desk.py:150-161),
# so the two are set separately to pin exactly the numbers this task names.

UNRESOLVED = ("/io", "/ch", "/aux", "/bus", "/main", "/mtx", "/$ctl")


def _leaves(n):
    from wing_parser.net.codec import OscMessage

    return {f"/probe/{i}": OscMessage(f"/probe/{i}", "i", (0,)) for i in range(n)}


def _panel(desk=None, *, transport=None, **kwargs):
    from tests.fake_desk import FakeDesk
    from wing_parser.ui.live_discovery import DiscoveryPanel

    if transport is None:
        desk = FakeDesk() if desk is None else desk
        transport = desk.transport()
    return DiscoveryPanel(transport=transport, **kwargs)


def test_a_clean_walk_shows_the_leaf_total_and_the_family_counts(qt_app, settle):
    from tests.fake_desk import FakeDesk
    from wing_parser.ui.live_state import LiveState

    desk = FakeDesk(
        leaves=_leaves(220),
        strips={"ch": 40, "bus": 16, "main": 4, "mtx": 8, "dca": 16},
    )
    panel = _panel(desk)
    panel.set_state(LiveState.CONNECTED)
    panel.set_host(HOST)
    results = []
    panel.discovered.connect(results.append)

    assert panel.discover_now()
    assert settle(lambda: results), "discovered never arrived"
    assert len(results[0].addresses) == 220
    assert results[0].strips == {
        "ch": 40, "bus": 16, "main": 4, "mtx": 8, "dca": 16,
    }
    summary = panel.inventory_label.text()
    assert "220" in summary
    for piece in ("40 ch", "16 bus", "4 main", "8 mtx", "16 dca"):
        assert piece in summary, summary


def test_the_unresolved_banner_names_every_family_that_did_not_resolve(
        qt_app, settle):
    from tests.fake_desk import FakeDesk
    from wing_parser.ui.live_state import LiveState

    desk = FakeDesk(leaves=_leaves(16), unresolved=UNRESOLVED)
    panel = _panel(desk)
    panel.set_state(LiveState.CONNECTED)
    panel.set_host(HOST)

    assert panel.discover_now()
    assert settle(lambda: panel.banner.isVisibleTo(panel))
    line = panel.banner_label.text()
    for family in UNRESOLVED:
        assert family in line, line
    assert "16" in line, "the leaf count it would watch"
    assert panel.rerun_button.isEnabled()


def test_the_banner_carries_the_rerun_sentence(qt_app, settle):
    from tests.fake_desk import FakeDesk
    from wing_parser.ui.live_state import LiveState

    desk = FakeDesk(leaves=_leaves(16), unresolved=UNRESOLVED)
    panel = _panel(desk)
    panel.set_state(LiveState.CONNECTED)
    panel.set_host(HOST)

    assert panel.discover_now()
    assert settle(lambda: panel.banner.isVisibleTo(panel))
    assert "rerun before believing the list is small" in panel.banner_label.text()


def test_the_banner_is_absent_after_a_clean_walk(qt_app, settle):
    from tests.fake_desk import FakeDesk
    from wing_parser.ui.live_state import LiveState

    desk = FakeDesk(
        leaves=_leaves(220),
        strips={"ch": 40, "bus": 16, "main": 4, "mtx": 8, "dca": 16},
    )
    panel = _panel(desk)
    panel.set_state(LiveState.CONNECTED)
    panel.set_host(HOST)

    assert panel.discover_now()
    assert settle(lambda: panel.inventory_label.text())
    assert not panel.banner.isVisibleTo(panel)


def test_rerun_walks_again_and_clears_the_banner(qt_app, settle):
    import dataclasses

    from tests.fake_desk import FakeDesk
    from wing_parser.net.watch.list import WatchList
    from wing_parser.ui.live_state import LiveState

    responses = iter([
        WatchList(addresses=tuple(_leaves(16)), unresolved=UNRESOLVED, strips={}),
        WatchList(
            addresses=tuple(_leaves(220)), unresolved=(),
            strips={"ch": 40, "bus": 16, "main": 4, "mtx": 8, "dca": 16},
        ),
    ])

    def walk(host):
        return next(responses)

    transport = dataclasses.replace(FakeDesk().transport(), walk=walk)
    panel = _panel(transport=transport)
    panel.set_state(LiveState.CONNECTED)
    panel.set_host(HOST)
    seen = []
    panel.discovered.connect(seen.append)
    reruns = []
    panel.rerun_requested.connect(lambda: reruns.append(True))

    assert panel.discover_now()
    assert settle(lambda: len(seen) == 1)
    assert panel.banner.isVisibleTo(panel)
    assert panel.rerun_button.isEnabled()

    panel.rerun_button.click()
    assert settle(lambda: len(seen) == 2)
    assert reruns == [True]
    assert not panel.banner.isVisibleTo(panel)


def test_a_failed_walk_reports_one_line_and_needs_a_reset(qt_app, settle):
    import dataclasses

    from tests.fake_desk import FakeDesk
    from wing_parser.ui.live_state import LiveState

    from wing_parser.ui.texts import text

    def raising(host):
        raise OSError(f"no console answered at {host}")

    transport = dataclasses.replace(FakeDesk().transport(), walk=raising)
    panel = _panel(transport=transport)
    panel.set_state(LiveState.CONNECTED)
    panel.set_host(HOST)
    running = text("console.discovering")

    assert panel.discover_now()
    assert settle(lambda: panel.status_label.text() != running), (
        "the failure line never arrived")
    line = panel.status_label.text()
    assert "\n" not in line
    assert HOST in line
    assert not panel.discover_button.isEnabled(), "error needs a reset first"
