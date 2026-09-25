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
        # Task-13 ruling: `error` reconnects in one click, like `lost`
        # -- and a backstop that fired is exactly when he wants to try
        # again rather than hunt for a reset.
        assert bar.connect_button.isEnabled(), "error reconnects in one click"
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


def test_a_failed_walk_reports_one_line_and_leaves_discover_dead(qt_app, settle):
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
    # Task-13 ruling: `error` offers Connect, so a retry is one click --
    # but a walk is not what it offers. Discover stays dead until the
    # desk is answering again.
    assert not panel.discover_button.isEnabled(), "Discover is dead in error"


# -- SnapshotPanel: Pull, the two guards, Open Doctor, Export ----------------
#
# The desk here is the real `user-files/example-Vu.snap`, leaf by leaf:
# `tests/test_live_controller.py::_desk_holding` already builds one and this
# module imports it rather than growing a second copy. One pull is taken per
# module and replayed, so no test re-walks the whole file twice.
#
# D16: the window stays on the Console page after a pull. D4: a pulled scene
# joins the recent menu only once it has been exported. D3: Export writes the
# PATCHED document through `Session.save_as`, never the pull-time bytes.


@pytest.fixture(scope="module")
def vu_result(vu_path):
    """One real `SnapshotResult` off the Vu desk, taken once per module."""
    from tests.test_live_controller import _desk_holding

    return _desk_holding(vu_path).transport().snapshot(HOST)


def _replaying(result):
    """A `Transport` whose `snapshot` hands back `result` and nothing else.

    `**_kw` (not just `host`): D-41's `pull` may call this with `schema=`
    when the page it is driving wired a real `SchemaCache` -- a double
    standing in for `Transport.snapshot` has to tolerate exactly the
    keyword the real one does, or `pull` raises `TypeError` instead of
    reaching the outcome this test wants to drive.
    """
    from tests.fake_desk import FakeDesk

    return dataclasses.replace(
        FakeDesk().transport(), snapshot=lambda host, **_kw: result)


def _snapshot_panel(transport, *, identity=None, host=HOST):
    from wing_parser.ui.live_snapshot import SnapshotPanel
    from wing_parser.ui.live_state import LiveState

    panel = SnapshotPanel(transport=transport)
    panel.set_identity(_identity() if identity is None else identity)
    panel.set_host(host)
    panel.set_state(LiveState.CONNECTED)
    return panel


def _wired(monkeypatch, panel):
    """A real MainWindow with `panel` wired the way the app wires it."""
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui import live_wiring
    from wing_parser.ui.main_window import MainWindow

    window = MainWindow(None)
    live_wiring.wire_console(window, panel)
    return window


def _pull_settled(panel, settle):
    """Pump until the pull's running line has been replaced by its outcome."""
    from wing_parser.ui.texts import text

    running = text("console.pulling").format(host=HOST)
    assert panel.pull_now(), "the pull never started"
    return settle(lambda: panel.status_label.text() != running)


def test_an_empty_read_shows_an_error_line_and_no_session_reaches_the_window(
        qt_app, settle, monkeypatch):
    """The `EmptyReadError` guard, at the UI boundary this time.

    A desk that answers nothing produces a valid, empty scene; without
    this guard the window would adopt it and Doctor would truthfully
    report "No findings." for a console it never reached.
    """
    from tests.fake_desk import FakeDesk

    panel = _snapshot_panel(FakeDesk().transport())
    window = _wired(monkeypatch, panel)
    pulled = []
    panel.session_pulled.connect(pulled.append)

    assert _pull_settled(panel, settle), "the failure line never arrived"
    line = panel.status_label.text()
    assert "\n" not in line, f"more than one line: {line!r}"
    assert "no console answered" in line and HOST in line
    assert pulled == [], "a session escaped the guard"
    assert window.session is None, "the window adopted an empty read"
    assert not panel.export_button.isEnabled()
    assert not panel.doctor_button.isEnabled()


def test_a_partial_read_shows_a_persistent_banner_naming_the_counts(
        qt_app, settle, monkeypatch, vu_result):
    partial = dataclasses.replace(
        vu_result,
        unresolved_nodes=("/mtx", "/dca"),
        unresolved_leaves=("/ch/7/$fdr", "/ch/8/$fdr", "/ch/9/$fdr"),
    )
    panel = _snapshot_panel(_replaying(partial))
    window = _wired(monkeypatch, panel)

    assert _pull_settled(panel, settle)
    assert window.session is not None, "a partial read is still usable"
    assert panel.banner.isVisibleTo(panel), "the banner is persistent"
    line = panel.banner.text()
    assert "2 node(s)" in line and "3 leaf" in line, line
    assert "/mtx" in line and "/dca" in line, line


def test_a_clean_pull_reaches_the_window_and_every_page_sees_it(
        qt_app, settle, monkeypatch, vu_result):
    panel = _snapshot_panel(_replaying(vu_result))
    window = _wired(monkeypatch, panel)
    seen = {}
    for key, page in window.pages.items():
        if hasattr(page, "set_session"):
            seen[key] = []
            page.set_session = lambda session, bucket=seen[key]: bucket.append(
                session)
    pulled = []
    panel.session_pulled.connect(pulled.append)

    assert _pull_settled(panel, settle)
    assert pulled, "session_pulled never fired"
    assert window.session is pulled[0]
    assert window.session.findings(), "the Vu scene has findings; this one must too"
    assert set(seen) >= {"doctor", "overview", "channels", "routing", "diff"}
    for key, bucket in seen.items():
        assert bucket and bucket[-1] is window.session, key
    assert not panel.banner.isVisibleTo(panel), "a clean read shows no banner"
    assert str(len(window.session.findings())) in panel.loaded_label.text()


def test_the_view_stays_on_the_console_page_after_a_pull(
        qt_app, settle, monkeypatch, vu_result):
    """D16: the watch may be running and he may want to pull again."""
    panel = _snapshot_panel(_replaying(vu_result))
    window = _wired(monkeypatch, panel)
    window.switch_to("console")

    assert _pull_settled(panel, settle)
    assert window.session is not None
    assert window.stack.currentWidget() is window.pages["console"]


def test_open_doctor_switches_to_the_doctor_page(
        qt_app, settle, monkeypatch, vu_result):
    panel = _snapshot_panel(_replaying(vu_result))
    window = _wired(monkeypatch, panel)
    window.switch_to("console")

    assert _pull_settled(panel, settle)
    assert panel.doctor_button.isEnabled(), "a loaded scene has a Doctor to open"
    panel.doctor_button.click()
    assert window.stack.currentWidget() is window.pages["doctor"]


def test_export_writes_through_save_as_and_remembers_the_exported_path(
        qt_app, settle, monkeypatch, tmp_path, vu_result):
    """D3 + D4 in one: the patched document, and the path remembered after."""
    import json

    from wing_parser.edit import pointer
    from wing_parser.ui import live_export
    from wing_parser.ui.session import Session

    panel = _snapshot_panel(_replaying(vu_result))
    window = _wired(monkeypatch, panel)
    assert _pull_settled(panel, settle)

    target = next(f for f in window.session.findings() if f.rule_id == "G8")
    assert window.session.repair(target) is True
    patch = window.session.changes()[0]

    out = tmp_path / "exported.snap"
    monkeypatch.setattr(live_export.QFileDialog, "getSaveFileName",
                        lambda *args, **kwargs: (str(out), ""))
    assert panel.export_now()

    written = json.loads(out.read_text(encoding="utf-8"))
    assert pointer.read(written, patch.path) == patch.after
    assert not [
        finding
        for finding in Session.open(out).findings()
        if (finding.rule_id, finding.target) == (target.rule_id, target.target)
    ]
    assert window._recent == [str(out)], "the exported path is remembered"


def test_a_pulled_session_is_not_in_the_recent_menu_before_export(
        qt_app, settle, monkeypatch, vu_result):
    """D4: its path names no file, so open_recent would pop 'File is gone'."""
    panel = _snapshot_panel(_replaying(vu_result))
    window = _wired(monkeypatch, panel)

    assert _pull_settled(panel, settle)
    assert window.session is not None
    assert window._recent == []
    assert window._recent_menu.actions() == []


def test_the_export_dialog_suggests_a_sanitised_desk_name(
        qt_app, settle, monkeypatch, vu_result):
    """A desk named `FOH/Monitors` must not propose a path with a directory."""
    from wing_parser.ui import live_export

    identity = dataclasses.replace(_identity(), name="FOH/Monitors")
    panel = _snapshot_panel(_replaying(vu_result), identity=identity)
    _wired(monkeypatch, panel)
    assert _pull_settled(panel, settle)

    suggested = []

    def _capture(parent, caption, directory, selected_filter):
        suggested.append(directory)
        return "", ""

    monkeypatch.setattr(
        live_export.QFileDialog, "getSaveFileName", _capture)
    assert not panel.export_now(), "a cancelled dialog writes nothing"
    assert suggested, "the dialog was never offered a suggestion"
    assert "FOH_Monitors" in suggested[0], suggested[0]
    assert "/" not in suggested[0] and "\\" not in suggested[0], suggested[0]


def test_the_export_dialog_suggests_a_bare_name_for_a_file_opened_scene(
        qt_app, monkeypatch, vu_path):
    """I1: `set_session` gives the panel scenes that came from disk.

    `console_page.set_session` syncs the window's session into
    `SnapshotPanel`, which enables Export on any loaded scene -- so File
    > Open > Console > Export reaches `export_name` with a real path,
    not a pull's bare stem. Sanitising the whole string mangled the
    directory into the filename; only the name is proposed now.
    """
    from wing_parser.ui import live_export
    from wing_parser.ui.session import Session

    panel = _snapshot_panel(None)
    panel.set_session(Session.open(vu_path))

    suggested = []

    def _capture(parent, caption, directory, selected_filter):
        suggested.append(directory)
        return "", ""

    monkeypatch.setattr(
        live_export.QFileDialog, "getSaveFileName", _capture)
    assert not panel.export_now(), "a cancelled dialog writes nothing"
    assert suggested == ["example-Vu.snap"], suggested


# -- the wiring itself, both halves of its contract --------------------------
#
# Review of task 11 (round 1): `wire_console` guards on `session_pulled` and
# then connects three signals, and neither branch was pinned. Both are now.


def test_wiring_a_page_without_the_signals_connects_nothing(
        qt_app, monkeypatch):
    """The no-op branch of the all-or-none contract.

    Task 13 filled the Console slot with a real `ConsolePage`, so the
    page this branch was written for -- task 8's `EmptyState` -- is no
    longer in the window. The branch itself still has to hold: a widget
    with none of the three signals must return quietly rather than raise
    on the first missing one. `EmptyState` is still the widget it is
    checked with, because that is the one this guard was measured
    against.
    """
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui import live_wiring
    from wing_parser.ui.console_page import ConsolePage
    from wing_parser.ui.main_window import MainWindow
    from wing_parser.ui.page_base import EmptyState

    window = MainWindow(None)
    assert isinstance(window.pages["console"], ConsolePage)
    assert live_wiring.wire_console(window, EmptyState("x")) is None
    assert window.session is None


def test_each_console_signal_drives_the_window(
        qt_app, monkeypatch, tmp_path, vu_path):
    """The other half: a page carrying all three, each one firing.

    A stub rather than `SnapshotPanel`, so this pins the wiring and not
    the panel -- task 13's `ConsolePage` has to re-emit exactly these
    three, and this is the test that says what "exactly these" means.
    """
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from PySide6.QtCore import QObject, Signal

    from wing_parser.ui import live_wiring
    from wing_parser.ui.main_window import MainWindow
    from wing_parser.ui.session import Session

    class _ConsoleStub(QObject):
        session_pulled = Signal(object)
        exported = Signal(str)
        doctor_requested = Signal()

    window = MainWindow(None)
    window.switch_to("console")
    page = _ConsoleStub()
    live_wiring.wire_console(window, page)

    session = Session.open(vu_path)
    page.session_pulled.emit(session)
    assert window.session is session
    assert window.stack.currentWidget() is window.pages["console"], "D16"

    page.exported.emit(str(tmp_path / "exported.snap"))
    assert window._recent == [str(tmp_path / "exported.snap")]

    page.doctor_requested.emit()
    assert window.stack.currentWidget() is window.pages["doctor"]


def test_export_and_open_doctor_survive_a_later_failed_pull(
        qt_app, settle, monkeypatch, vu_result):
    """A scene in memory stays exportable when the NEXT pull fails.

    Orchestrator ruling (task 11 review): writing a file is not a desk
    action, so Export is gated on a loaded session alone. Gating it on
    `allowed_actions` instead greyed out Export in `ERROR` -- exactly
    when the operator most wants the scene he already has on disk.
    """
    from tests.fake_desk import FakeDesk
    from wing_parser.ui.live_state import LiveState

    answers = iter([vu_result, FakeDesk().transport().snapshot(HOST)])
    transport = dataclasses.replace(
        FakeDesk().transport(), snapshot=lambda host, **_kw: next(answers))
    panel = _snapshot_panel(transport)
    window = _wired(monkeypatch, panel)

    assert _pull_settled(panel, settle)
    assert window.session is not None
    assert panel.export_button.isEnabled()

    assert _pull_settled(panel, settle), "the second, empty pull never settled"
    assert "no console answered" in panel.status_label.text()
    assert panel._state is LiveState.ERROR
    assert panel.export_button.isEnabled(), "the pulled scene is still in memory"
    assert panel.doctor_button.isEnabled()
    assert not panel.pull_button.isEnabled(), (
        "Pull is dead in error -- Connect is what error offers (task 13)")


def test_a_pull_is_refused_from_a_state_that_does_not_allow_it(
        qt_app, monkeypatch, vu_result):
    """The button is disabled; a programmatic caller must be refused too."""
    from wing_parser.ui.live_state import LiveState, allowed_actions

    panel = _snapshot_panel(_replaying(vu_result))
    panel.set_state(LiveState.WATCHING)
    assert "pull" not in allowed_actions(LiveState.WATCHING)

    assert not panel.pull_now(), "a pull started while the watch was running"
    assert panel._state is LiveState.WATCHING, "and the watch state survived"


# -- the watch: LiveEventsView (task 12) -------------------------------------
#
# Every watch below runs the REAL `poller.watch` over a `FakeDesk` whose
# rounds are scripted (D5, spec S9.1) -- no socket, and no stand-in loop
# written to agree with the widget. The interval is pushed to the spin's
# floor so a bounded `settle` pump covers several rounds; nothing here
# waits a real second.

FAST = 0.05          # the interval spin's floor, in seconds
TIME, STRIP, KEY, CHANGE = 0, 1, 2, 3


def _fader(address, db):
    from wing_parser.net.codec import OscMessage

    return OscMessage(address, "sff", (str(db), 0.5, db))


def _mute(address, on):
    from wing_parser.net.codec import OscMessage

    return OscMessage(address, "sfi", (str(on), float(on), on))


def _watch_desk(rounds):
    """One strip, three leaves, and a scripted round per `get_many`.

    `poller.watch` spends one round on `read_labels` and one on the
    priming sample before its first loop round (`poller.py:84-86`), so
    every script below opens with two no-change entries.
    """
    from tests.fake_desk import FakeDesk

    leaves = {
        "/ch/1/$fdr": _fader("/ch/1/$fdr", -6.0),
        "/ch/1/$mute": _mute("/ch/1/$mute", 0),
        "/ch/1/name": _nameleaf(),
    }
    return FakeDesk(leaves=leaves, rounds=rounds, strips={"ch": 1})


def _nameleaf():
    from wing_parser.net.codec import OscMessage

    return OscMessage("/ch/1/name", "s", ("KICK",))


def _events_view(desk, fast=True, **kwargs):
    """A `LiveEventsView` over `desk`, discovered and ready to watch."""
    from wing_parser.ui.live_events_view import LiveEventsView
    from wing_parser.ui.live_state import LiveState

    transport = desk.transport()
    view = LiveEventsView(transport=transport, **kwargs)
    view.set_host(HOST)
    view.set_watch_list(transport.walk(HOST))
    view.set_state(LiveState.CONNECTED)
    if fast:
        view.bar.interval.setValue(FAST)
    return view


def _quiet(view, settle):
    """Stop the watch and wait for its thread -- no test leaves one running."""
    view.stop_watch()
    assert settle(lambda: not view.is_watching()), "the watch thread never ended"


def _two_events():
    """$fdr moves on round 1, $mute on round 2, then steady state."""
    return [
        {"/ch/1/$fdr": _fader("/ch/1/$fdr", -6.0)},          # read_labels
        {"/ch/1/$fdr": _fader("/ch/1/$fdr", -6.0)},          # priming sample
        {"/ch/1/$fdr": _fader("/ch/1/$fdr", -3.0)},          # round 1
        {"/ch/1/$fdr": _fader("/ch/1/$fdr", -3.0),           # round 2, and
         "/ch/1/$mute": _mute("/ch/1/$mute", 1)},            # every round after
    ]


def test_the_interval_spin_starts_at_the_pollers_default(qt_app):
    """0.25 s, and the floor is not zero: an unpaced loop is a flood."""
    from wing_parser.ui.live_guard import DEFAULT_INTERVAL

    view = _events_view(_watch_desk([]), fast=False)
    assert view.bar.interval.value() == DEFAULT_INTERVAL == 0.25
    assert view.bar.interval.minimum() == FAST


def test_scripted_changes_land_in_the_table_in_order(qt_app, settle):
    view = _events_view(_watch_desk(_two_events()))
    started = []
    view.started.connect(lambda: started.append(True))

    assert view.start_watch(), "the watch never began"
    assert started == [True]
    assert settle(lambda: view.model.rowCount() >= 2), "only one round landed"

    keys = [view.model.item(row, KEY).text() for row in range(2)]
    assert keys == ["$fdr", "$mute"], "the poller's order is the table's order"
    _quiet(view, settle)


def test_the_row_shows_the_strip_label_the_key_and_before_to_after(
        qt_app, settle):
    view = _events_view(_watch_desk(_two_events()))
    assert view.start_watch()
    assert settle(lambda: view.model.rowCount() >= 1)

    assert view.model.item(0, STRIP).text() == "KICK", "the strip's own name"
    assert view.model.item(0, KEY).text() == "$fdr"
    cell = view.model.item(0, CHANGE).text()
    assert "-6.0" in cell and "-3.0" in cell and "→" in cell, cell
    float(view.model.item(0, TIME).text())     # the poller's own elapsed
    _quiet(view, settle)


def test_stop_settles_the_worker_and_restores_the_buttons(qt_app, settle):
    from wing_parser.ui.live_state import LiveState

    view = _events_view(_watch_desk(_two_events()))
    ended = []
    view.stopped.connect(lambda: ended.append(True))

    assert view.start_watch()
    assert view._state is LiveState.WATCHING
    assert not view.bar.start_button.isEnabled()
    assert settle(lambda: view.model.rowCount() >= 1)

    assert view.stop_watch(), "Stop was refused while the watch was running"
    assert settle(lambda: bool(ended)), "stopped never arrived"
    assert settle(lambda: not view.is_watching()), "the thread outlived Stop"
    assert view._state is LiveState.CONNECTED
    assert view.bar.start_button.isEnabled()
    assert not view.bar.stop_button.isEnabled()
    assert view.model.rowCount() >= 1, "Stop keeps what the watch collected"


def test_desk_lost_leaves_the_events_on_screen_and_offers_reconnect(
        qt_app, settle):
    """D6 + the spec's `lost` state: the events above the banner were real."""
    from wing_parser.ui.live_guard import DeskLost
    from wing_parser.ui.live_state import LiveState

    desk = _watch_desk([
        {"/ch/1/$fdr": _fader("/ch/1/$fdr", -6.0)},      # read_labels
        {"/ch/1/$fdr": _fader("/ch/1/$fdr", -6.0)},      # priming sample
        {"/ch/1/$fdr": _fader("/ch/1/$fdr", -3.0)},      # round 1: one event
        {}, {}, {},                                      # three silent rounds
    ])
    view = _events_view(desk)
    gone = []
    view.lost.connect(gone.append)

    assert view.start_watch()
    assert settle(lambda: bool(gone)), "the desk was never declared lost"
    assert isinstance(gone[0], DeskLost) and gone[0].rounds == 3
    assert view._state is LiveState.LOST
    assert view.model.rowCount() == 1, "the event it did see stays on screen"
    assert view.bar.reconnect_button.isVisibleTo(view.bar), "Reconnect is offered"
    assert view.bar.reconnect_button.isEnabled()
    assert settle(lambda: not view.is_watching())

    asked = []
    view.reconnect_requested.connect(lambda: asked.append(True))
    view.bar.reconnect_button.click()
    assert asked == [True]


def test_the_rate_line_comes_from_watch_rate_not_from_the_widget(
        qt_app, settle, monkeypatch):
    """No arithmetic in the widget: the line follows `watch_rate` exactly."""
    from wing_parser.ui import live_guard

    monkeypatch.setattr(live_guard, "watch_rate", lambda events, seconds: (42.0, 7.0))
    view = _events_view(_watch_desk([]))

    assert view.start_watch()
    assert "42.00" in view.bar.rate_label.text(), view.bar.rate_label.text()
    assert "7.0" in view.bar.rate_label.text(), view.bar.rate_label.text()
    _quiet(view, settle)


def test_a_watch_is_refused_without_a_leaf_list_or_from_the_wrong_state(
        qt_app):
    """Both guards, and neither may start a thread."""
    from wing_parser.ui.live_state import LiveState

    view = _events_view(_watch_desk([]))
    view.set_watch_list(None)
    assert not view.start_watch(), "a watch began with nothing to watch"
    assert view.status_label.text()
    assert not view.is_watching()

    view.set_watch_list(view._transport.walk(HOST))
    view.set_state(LiveState.PULLING)
    assert not view.start_watch(), "a watch began while a pull was running"
    assert view._state is LiveState.PULLING
    assert not view.is_watching()


# -- task 12, review round 1: the two ways a session was orphaned ------------


def test_leaving_the_watching_state_cancels_the_orphaned_session(
        qt_app, settle):
    """`set_state` is not only the page's paint call -- it can end a watch.

    `allowed_actions(WATCHING)` contains `disconnect`, and
    `ConnectBar.disconnect_now` sets its state directly
    (`live_connect_bar.py:150`), so task 13 fanning that out reaches this
    view as a bare `set_state(DISCONNECTED)`. Without the cancel the
    worker polls that desk forever: Stop is hidden in DISCONNECTED and
    `stop_watch` refuses, because `stop` is not in that state's actions.
    """
    from wing_parser.ui.live_state import LiveState

    view = _events_view(_watch_desk(_two_events()))
    ended, gone = [], []
    view.stopped.connect(lambda: ended.append(True))
    view.lost.connect(gone.append)
    assert view.start_watch()
    assert settle(lambda: view.model.rowCount() >= 1)

    view.set_state(LiveState.DISCONNECTED)
    assert settle(lambda: not view.is_watching()), "the worker outlived the page"
    # Pump past the end: the terminal signal is delivered in here, and it
    # must not drag the page back out of the state it was just put in.
    assert not settle(lambda: bool(ended or gone), limit_s=0.3)
    assert view._state is LiveState.DISCONNECTED
    assert not view.stop_watch(), "there is nothing left to stop"
    assert view.model.rowCount() >= 1, "and what it collected stays on screen"


def test_shutdown_ends_a_running_watch_and_is_wired_to_the_quit(qt_app):
    """No thread outlives the app: `QThread: Destroyed while running`.

    `MainWindow.closeEvent` only saves window state
    (`main_window.py:163-165`), and nothing else in the app stops a
    watch, so the view hooks `aboutToQuit` itself and blocks there.
    """
    from wing_parser.ui.live_state import LiveState

    view = _events_view(_watch_desk(_two_events()))
    assert view.start_watch()
    assert view.is_watching()
    view.shutdown()
    assert not view.is_watching(), "shutdown returned with the thread alive"

    # And the hook itself, driven rather than counted: PySide6's
    # `QObject.receivers` takes no SignalInstance, so the signal is
    # emitted instead. Only this view is alive to hear it -- Qt drops a
    # connection when either end is destroyed.
    # `shutdown` ends the thread and leaves the state alone -- the app is
    # quitting, so there is nothing to leave it in. A page that wanted to
    # go on would put it back itself, which is what this does.
    view.set_state(LiveState.CONNECTED)
    assert view.start_watch()
    qt_app.aboutToQuit.emit()
    assert not view.is_watching(), "aboutToQuit did not reach shutdown"


def test_a_failure_that_is_not_a_lost_desk_says_so(qt_app, settle):
    """A code bug mid-watch must not be misdiagnosed as a quiet desk.

    The state is still `lost` -- `live_state.py` gives `watching` no
    third exit -- but the sentence is the other one.
    """
    from wing_parser.ui.live_events_view import LiveEventsView
    from wing_parser.ui.live_state import LiveState

    def boom(client, watch_list, **kwargs):
        raise ValueError("the watch list went stale")

    transport = dataclasses.replace(_watch_desk([]).transport(), watch=boom)
    view = LiveEventsView(transport=transport)
    view.set_host(HOST)
    view.set_watch_list(transport.walk(HOST))
    view.set_state(LiveState.CONNECTED)
    seen = []
    view.lost.connect(seen.append)

    assert view.start_watch()
    assert settle(lambda: bool(seen)), "the failure never reached the page"
    assert isinstance(seen[0], ValueError)
    assert view._state is LiveState.LOST
    line = view.status_label.text()
    assert "went stale" in line, line
    assert "not the desk going quiet" in line, line
    assert settle(lambda: not view.is_watching())


# -- task 12, review round 2 -------------------------------------------------


def test_an_abandoned_sessions_late_end_cannot_touch_the_next_one(
        qt_app, settle):
    """Each session answers for ITSELF, not for whichever is current.

    Reproduced in review: abandon A by disconnecting, reconnect, Start B,
    and A's terminal signal then arrives while `_session` is B. Judged
    against B's flag it passes, emits `stopped`, drags the page to
    CONNECTED -- and the disconnect guard, seeing WATCHING -> CONNECTED
    with a live session, abandons B as well. Two sessions lost to one
    late signal.
    """
    from wing_parser.ui.live_state import LiveState

    view = _events_view(_watch_desk(_two_events()))
    ended, gone = [], []
    view.stopped.connect(lambda: ended.append(True))
    view.lost.connect(gone.append)

    assert view.start_watch()
    first = view._session
    assert settle(lambda: view.model.rowCount() >= 1)
    view.set_state(LiveState.DISCONNECTED)          # abandons A
    assert settle(lambda: not first.is_running())

    view.set_state(LiveState.CONNECTED)
    assert view.start_watch()
    second = view._session
    assert second is not first

    # A's terminal signal, delivered late. Emitted by hand because the
    # real one already arrived while A was still `_session`, which is
    # exactly the case the bug did NOT cover.
    first.worker.finished_cancelled.emit()

    assert view._state is LiveState.WATCHING, "A's late end moved the page"
    assert ended == [] and gone == []
    assert view.is_watching() and view._session is second, "B was abandoned too"
    _quiet(view, settle)


def test_the_shutdown_wait_outlasts_the_slowest_interval_the_spin_offers():
    """`poller.watch` sleeps `remaining` without consulting the cancel
    event (`poller.py:121-123`), so a watch at `MAX_INTERVAL` still owes
    a whole interval after Stop. A wait shorter than that returns False
    with the thread alive, and `aboutToQuit` has nothing left to do with
    a False -- `QThread.terminate` is unsafe and `net/` is out of scope
    this wave.

    The derivation is asserted, not the wall clock: proving it for real
    means running one watch at 5 s, and one number is not worth five
    seconds on every suite run.
    """
    from wing_parser.ui.live_guard import MAX_INTERVAL
    from wing_parser.ui.live_watch_session import WAIT_MS

    assert WAIT_MS > MAX_INTERVAL * 1000, "shutdown gives up mid-sleep"
    assert WAIT_MS >= (MAX_INTERVAL + 1.0) * 1000, "and one round beyond it"


# -- ConsolePage: the assembly, and one table driving every button ----------
#
# Task 13. The page owns exactly ONE `LiveState`; the four panels never
# carry a state the page did not put there through `set_state`, and the
# page contains no `setEnabled` of its own at all. That is the property
# `test_every_button_matches_allowed_actions_in_every_state` exhausts --
# eight states against every QPushButton the page really contains (the
# set is read off `findChildren`, so a button added later and left out
# of the map below fails this test rather than escaping it).
#
# Two of those buttons are NOT table-driven and are asserted against the
# loaded scene instead: Export and Open Doctor, per the task-11
# orchestrator ruling -- writing a file and switching page are not desk
# actions, and gating them on `allowed_actions` greyed out Export in
# `ERROR`, exactly when the scene in memory is the one thing worth
# saving (`live_snapshot.py:101-118`).


def _console_desk(**kwargs):
    """A desk that answers the handshake, a walk and a pull.

    `unresolved` is on by default so the Rerun button's OWN precondition
    (`_has_unresolved`, `live_discovery.py:159`) is met and the state
    table is then the only thing left deciding it.
    """
    from tests.fake_desk import FakeDesk

    fields = dict(identity=_identity(), leaves=_leaves(3),
                  strips={"ch": 1}, unresolved=UNRESOLVED)
    fields.update(kwargs)
    return FakeDesk(**fields)


def _page(desk=None, *, transport=None, **kwargs):
    from wing_parser.ui.console_page import ConsolePage

    if transport is None:
        transport = (_console_desk() if desk is None else desk).transport()
    return ConsolePage(transport=transport, **kwargs)


def _armed_page(session=None):
    """A page whose every non-state precondition is already satisfied.

    Start needs a watch list and Rerun needs unresolved families; with
    both handed over, `allowed_actions` is the ONLY thing left that can
    move either button, which is what the exhaustive test measures.
    """
    desk = _console_desk()
    page = _page(desk)
    watch_list = desk.transport().walk(HOST)
    page.discovery.set_result(watch_list)
    page.events.set_watch_list(watch_list)
    page.set_session(session)
    return page


def _table_driven(page):
    """Every button whose enabled-ness is one `allowed_actions` name."""
    return {
        "connect": [page.connect_bar.connect_button,
                    page.events.bar.reconnect_button],
        "disconnect": [page.connect_bar.disconnect_button],
        "discover": [page.discovery.discover_button],
        "rerun": [page.discovery.rerun_button],
        "pull": [page.snapshot.pull_button],
        "watch": [page.events.bar.start_button],
        "stop": [page.events.bar.stop_button],
        # All three, deliberately: `cancel` is allowed in each busy
        # state, so in `walking` the connect bar's and the snapshot's
        # Cancel are enabled too. They are also HIDDEN -- `ButtonRunner`
        # shows one only while that panel's own call runs
        # (`call_button.py:59-60,70-73`) -- so an enabled Cancel on a
        # panel with nothing running is unreachable, and
        # `ConsolePage._cancelled` keys off the page's state rather than
        # off which button was pressed.
        "cancel": [page.connect_bar.cancel_button,
                   page.discovery.cancel_button,
                   page.snapshot.cancel_button],
    }


def test_the_page_builds_with_no_desk_and_no_session(qt_app):
    """No transport, no scene, no network: construction alone.

    `live_controller.REAL` is the default transport and touches nothing
    until a call is actually started, so this builds the page exactly as
    `MainWindow` does.
    """
    from wing_parser.ui.console_page import ConsolePage
    from wing_parser.ui.live_state import LiveState

    page = ConsolePage()
    assert page.state is LiveState.DISCONNECTED
    assert page.connect_bar.connect_button.isEnabled()
    assert not page.snapshot.pull_button.isEnabled()
    assert not page.snapshot.export_button.isEnabled()
    page.set_session(None)
    assert page.snapshot.loaded_label.text() == ""


def test_every_button_matches_allowed_actions_in_every_state(qt_app, vu_path):
    from PySide6.QtWidgets import QPushButton

    from wing_parser.ui.live_state import LiveState, allowed_actions
    from wing_parser.ui.session import Session

    for session in (None, Session.open(vu_path)):
        page = _armed_page(session)
        driven = _table_driven(page)
        gated = [page.snapshot.export_button, page.snapshot.doctor_button]

        covered = {id(button) for row in driven.values() for button in row}
        covered |= {id(button) for button in gated}
        missed = [button.text() for button in page.findChildren(QPushButton)
                  if id(button) not in covered]
        assert missed == [], "a button nothing in this test accounts for"

        for state in LiveState:
            page._apply_state(state)
            actions = allowed_actions(state)
            for action, row in driven.items():
                for button in row:
                    assert button.isEnabled() is (action in actions), (
                        f"{button.text()!r} in {state.value} "
                        f"(actions: {sorted(actions)})")
            for button in gated:
                assert button.isEnabled() is (session is not None), (
                    f"{button.text()!r} is gated on the scene, not on "
                    f"{state.value}")


def test_an_illegal_transition_raises_rather_than_leaving_a_stale_page(qt_app):
    """`transition` raises, and the page is untouched when it does.

    A page that swallowed the error would sit in a state its own buttons
    disagree with; one that half-applied it would be worse.
    """
    from wing_parser.ui.live_state import LiveState

    page = _page()
    with pytest.raises(ValueError) as excinfo:
        page._fire("watch")
    assert "disconnected" in str(excinfo.value)
    assert "watch" in str(excinfo.value)
    assert page.state is LiveState.DISCONNECTED
    assert page.connect_bar.connect_button.isEnabled()
    assert not page.snapshot.pull_button.isEnabled()


def test_cancel_restores_the_buttons(qt_app, settle):
    """Cancel is the only way out of a busy state, for the whole page.

    The three busy states enable nothing else, so a Cancel the page did
    not hear would strand every panel greyed out.
    """
    from wing_parser.ui.live_state import LiveState

    gate = threading.Event()

    def stuck(host):
        gate.wait(timeout=5.0)
        return _identity()

    transport = dataclasses.replace(
        _console_desk().transport(), identity=stuck)
    page = _page(transport=transport)
    page.connect_bar.address.setCurrentText(HOST)

    page.connect_bar.connect_button.click()
    assert page.state is LiveState.CONNECTING
    assert not page.discovery.discover_button.isEnabled()
    assert page.connect_bar.cancel_button.isEnabled()

    page.connect_bar.cancel_button.click()
    assert page.state is LiveState.DISCONNECTED
    assert page.connect_bar.connect_button.isEnabled()
    assert not page.connect_bar.cancel_button.isEnabled()
    gate.set()
    settle(lambda: False, limit_s=0.2)   # let the worker return and die


def test_a_refused_start_leaves_the_page_where_it_was(qt_app):
    """An empty address starts no call -- and moves no state.

    Firing `connect` anyway would put the page in `connecting`, whose
    action set is Cancel alone, with no call running for Cancel to end.
    """
    from wing_parser.ui.live_state import LiveState
    from wing_parser.ui.texts import text

    page = _page()
    page.connect_bar.address.setCurrentText("   ")
    page.connect_bar.connect_button.click()
    assert page.state is LiveState.DISCONNECTED
    assert page.connect_bar.status_label.text() == text("console.no_address")


def test_a_connect_carries_the_host_to_every_panel(qt_app, settle):
    from wing_parser.ui.live_state import LiveState

    page = _page()
    page.connect_bar.address.setCurrentText(HOST)
    remembered = []
    page.host_connected.connect(remembered.append)

    page.connect_bar.connect_button.click()
    assert settle(lambda: page.state is LiveState.CONNECTED)
    assert remembered == [HOST]
    assert page.discovery._host == HOST
    assert page.snapshot._host == HOST
    assert page.events._host == HOST
    assert page.snapshot._identity == _identity()


def test_a_walk_arms_the_watch_and_a_failed_one_reddens_the_page(
        qt_app, settle):
    """Discovery's two outcomes, both reaching the page's one state."""
    from wing_parser.ui.live_state import LiveState

    page = _page()
    page.connect_bar.address.setCurrentText(HOST)
    page.connect_bar.connect_button.click()
    assert settle(lambda: page.state is LiveState.CONNECTED)

    page.discovery.discover_button.click()
    assert settle(lambda: page.state is LiveState.CONNECTED
                  and page.events._watch_list is not None)
    assert page.events.bar.start_button.isEnabled()

    def refuse(host, **_kw):
        raise OSError("no route to host")

    page.discovery._transport = dataclasses.replace(
        _console_desk().transport(), walk=refuse)
    page.discovery.discover_button.click()
    assert settle(lambda: page.state is LiveState.ERROR)
    assert page.connect_bar.lamp.property("azStyle") == "danger"
    assert page.connect_bar.connect_button.isEnabled(), (
        "error reconnects in one click, like lost")


def _schema_share_desk():
    """A desk small enough to read fast, and shaped for BOTH Discover
    (any leaf works) and Pull (`/ch/1/name` is a real `ae_data` leaf, so
    the read is non-empty and never raises `EmptyReadError`)."""
    from tests.fake_desk import FakeDesk
    from wing_parser.net.codec import OscMessage

    return FakeDesk(
        identity=_identity(), strips={"ch": 1},
        leaves={"/ch/1/name": OscMessage("/ch/1/name", "s", ("KICK",))},
    )


def test_a_round_trip_through_discover_and_pull_walks_the_schema_once(
        qt_app, settle):
    """D-41: the `net/` seam (`schema=`) already existed; this proves the
    Console page actually uses it. Discover then Pull -- and the reverse
    order -- must cost the desk ONE walk for the whole round trip, not
    one inside each call, driven through the real buttons against
    `FakeDesk` (`desk.walks`, D-41's own counter)."""
    from wing_parser.ui.live_state import LiveState

    desk = _schema_share_desk()
    page = _page(desk)
    page.connect_bar.address.setCurrentText(HOST)
    page.connect_bar.connect_button.click()
    assert settle(lambda: page.state is LiveState.CONNECTED)

    page.discovery.discover_button.click()
    assert settle(lambda: page.events._watch_list is not None)
    page.snapshot.pull_button.click()
    assert settle(lambda: page.snapshot._session is not None)
    assert desk.walks == [HOST], "Discover then Pull must share one walk"

    # The reverse order, on its own fresh connection: Pull walks first,
    # Discover must reuse it.
    desk2 = _schema_share_desk()
    page2 = _page(desk2)
    page2.connect_bar.address.setCurrentText(HOST)
    page2.connect_bar.connect_button.click()
    assert settle(lambda: page2.state is LiveState.CONNECTED)

    page2.snapshot.pull_button.click()
    assert settle(lambda: page2.snapshot._session is not None)
    page2.discovery.discover_button.click()
    assert settle(lambda: page2.events._watch_list is not None)
    assert desk2.walks == [HOST], "Pull then Discover must share it too"


def test_rerun_after_an_incomplete_discover_actually_walks_again(qt_app, settle):
    """C1 (D-41 fix round, CRITICAL): an incomplete first walk must never
    be cached. Rerun exists precisely to try again -- a `_schema_for`
    that cached the incomplete `SchemaResult` anyway would make Rerun
    (and a later Pull) replay the SAME unresolved families forever,
    exactly the failure the banner's own comment (2026-08-23) describes
    D-41 must not reintroduce."""
    from tests.fake_desk import FakeDesk
    from wing_parser.net.codec import OscMessage
    from wing_parser.ui.live_state import LiveState

    desk = FakeDesk(
        identity=_identity(), strips={"ch": 1}, unresolved=("/mtx",),
        leaves={"/ch/1/name": OscMessage("/ch/1/name", "s", ("KICK",))},
    )
    page = _page(desk)
    page.connect_bar.address.setCurrentText(HOST)
    page.connect_bar.connect_button.click()
    assert settle(lambda: page.state is LiveState.CONNECTED)

    page.discovery.discover_button.click()
    assert settle(lambda: page.events._watch_list is not None)
    assert desk.walks == [HOST]
    assert page.discovery.banner.isVisibleTo(page.discovery)
    assert page.events._watch_list.unresolved == ("/mtx",)

    # The desk resolves /mtx by the time Rerun is clicked.
    desk.unresolved = ()
    desk.leaves["/mtx/1/name"] = OscMessage("/mtx/1/name", "s", ("MTX1",))

    page.discovery.rerun_button.click()
    assert settle(lambda: not page.discovery.banner.isVisibleTo(page.discovery))
    assert desk.walks == [HOST, HOST], "Rerun must walk again, not replay the cached one"
    assert page.events._watch_list.unresolved == ()
    assert "/mtx/1/name" in page.events._watch_list.addresses


def test_pull_after_an_incomplete_discover_walks_fresh_not_the_stale_schema(
        qt_app, settle):
    """C1's other half: before D-41, Pull always walked fresh. A cache
    populated by an INCOMPLETE Discover must not change that -- Pull
    must never inherit the same partial leaf list."""
    from tests.fake_desk import FakeDesk
    from wing_parser.net.codec import OscMessage
    from wing_parser.ui.live_state import LiveState

    desk = FakeDesk(
        identity=_identity(), strips={"ch": 1}, unresolved=("/mtx",),
        leaves={"/ch/1/name": OscMessage("/ch/1/name", "s", ("KICK",))},
    )
    page = _page(desk)
    page.connect_bar.address.setCurrentText(HOST)
    page.connect_bar.connect_button.click()
    assert settle(lambda: page.state is LiveState.CONNECTED)

    page.discovery.discover_button.click()
    assert settle(lambda: page.events._watch_list is not None)
    assert desk.walks == [HOST]

    page.snapshot.pull_button.click()
    assert settle(lambda: page.snapshot._session is not None)
    assert desk.walks == [HOST, HOST], (
        "Pull must walk fresh, not reuse the incomplete schema")


def test_the_schema_cache_is_dropped_on_disconnect_and_on_reconnect(
        qt_app, settle):
    """D-41: a schema must never outlive its own connection. Disconnect
    drops it, and so does the NEXT connect, even to the same address --
    the tree's shape is live (S2.10), so a stale walk carried into a new
    connection is worse than paying for one more."""
    from wing_parser.ui.live_state import LiveState

    desk = _schema_share_desk()
    page = _page(desk)
    page.connect_bar.address.setCurrentText(HOST)
    page.connect_bar.connect_button.click()
    assert settle(lambda: page.state is LiveState.CONNECTED)

    page.discovery.discover_button.click()
    assert settle(lambda: page.events._watch_list is not None)
    assert desk.walks == [HOST]
    assert page._schema_cache.get() is not None

    page.connect_bar.disconnect_button.click()
    assert page._schema_cache.get() is None, "disconnect must drop the cache"

    page.connect_bar.connect_button.click()
    assert settle(lambda: page.state is LiveState.CONNECTED)
    assert page._schema_cache.get() is None, "a fresh connect must drop it too"

    page.snapshot.pull_button.click()
    assert settle(lambda: page.snapshot._session is not None)
    assert desk.walks == [HOST, HOST], "the second connection walked fresh"


def test_the_page_re_emits_all_three_window_signals(
        qt_app, settle, monkeypatch, tmp_path, vu_result):
    """`wire_console`'s all-or-none contract, against the real page."""
    from wing_parser.ui.live_state import LiveState

    page = _page(transport=_replaying(vu_result))
    window = _wired(monkeypatch, page)
    window.switch_to("console")
    page.snapshot.set_host(HOST)
    page._apply_state(LiveState.CONNECTED)

    page.snapshot.pull_button.click()
    assert settle(lambda: window.session is not None), "no session arrived"
    assert window.stack.currentWidget() is window.pages["console"], "D16"
    assert page.state is LiveState.CONNECTED

    exported = tmp_path / "pulled.snap"
    page.snapshot.exported.emit(str(exported))
    assert window._recent == [str(exported)]

    page.snapshot.doctor_requested.emit()
    assert window.stack.currentWidget() is window.pages["doctor"]


def test_set_session_syncs_the_snapshot_panel(qt_app, vu_path):
    """Orchestrator ruling: the page is a `set_session` consumer after all.

    Not because the Console page needs the scene, but because a stale
    one is worse: without this, Export on this page would write the
    scene a pull left behind long after the window opened another file.
    """
    from wing_parser.ui.session import Session

    page = _page()
    session = Session.open(vu_path)
    page.set_session(session)
    assert page.snapshot._session is session
    assert page.snapshot.export_button.isEnabled()
    assert page.snapshot.doctor_button.isEnabled()
    assert page.snapshot.loaded_label.text() != ""

    page.set_session(None)
    assert page.snapshot._session is None
    assert not page.snapshot.export_button.isEnabled()
    assert not page.snapshot.doctor_button.isEnabled()
    assert page.snapshot.loaded_label.text() == ""


def test_reconnect_from_lost_starts_a_new_handshake(qt_app, settle):
    """Reconnect is a dead button unless the page hands it to the bar."""
    from wing_parser.ui.live_state import LiveState

    page = _page()
    page.connect_bar.address.setCurrentText(HOST)
    page._apply_state(LiveState.LOST)
    assert page.events.bar.reconnect_button.isVisibleTo(page.events.bar)

    page.events.bar.reconnect_button.click()
    assert page.state is LiveState.CONNECTING
    assert settle(lambda: page.state is LiveState.CONNECTED)


def test_disconnecting_out_of_a_watch_returns_the_page_to_disconnected(
        qt_app):
    """`watching` offers Disconnect, so the table has to accept it.

    `_ACTIONS[WATCHING]` carried `disconnect` from task 1 while `_TABLE`
    had no row for it: the button was live and the page's own
    `transition` would have raised on the click.
    """
    from wing_parser.ui.live_state import LiveState

    page = _page()
    page._apply_state(LiveState.WATCHING)
    assert page.connect_bar.disconnect_button.isEnabled()

    page.connect_bar.disconnect_button.click()
    assert page.state is LiveState.DISCONNECTED
    assert page.connect_bar.connect_button.isEnabled()


def test_the_window_offers_and_remembers_the_console_addresses(
        qt_app, monkeypatch, tmp_path):
    """Persisting is the window's job; the page only asks and answers.

    Mirrors how `recent` is persisted (`window_state.py:62-64` and `:116-128`) --
    restored before first paint, remembered on a successful connect,
    written back on close.
    """
    from wing_parser import config
    from wing_parser.ui import state_store, window_state
    from wing_parser.ui.console_page import ConsolePage
    from wing_parser.ui.main_window import MainWindow

    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    monkeypatch.setenv(config.ENV_VAR, str(tmp_path))
    state_store.save(tmp_path, {"consoles": ["10.0.0.9"]})

    window = MainWindow(None)
    page = window.pages["console"]
    assert isinstance(page, ConsolePage)
    assert page.connect_bar.host() == "10.0.0.9", "most recent, offered"

    page.host_connected.emit(HOST)
    assert window._consoles == [HOST, "10.0.0.9"]
    window_state.save_on_close(window)
    assert state_store.load(tmp_path)["consoles"] == [HOST, "10.0.0.9"]


# -- the watch branch, end to end over the real panels ---------------------
#
# Review round 1 of task 13: every test above that reaches `watching` or
# `lost` injects the state with `_apply_state`, so deleting any of the
# three `events.*` connects in `ConsolePage._wire` left all 67 green. The
# two tests below are the ones that would notice -- they drive a real
# watch off a real `WatchSession` thread and let the real signals arrive.


def _watch_page(rounds):
    """A `ConsolePage` over a desk that answers a handshake AND a watch.

    `FakeDesk._walk` and `._identity` deliberately do not go through
    `client()` (`fake_desk.py:150-161`), so neither the connect nor the
    discovery below eats a scripted round: the script is the watch's
    alone, and its rounds land where the comments say they do.
    """
    desk = _watch_desk(rounds)
    desk.identity = _identity()
    page = _page(desk)
    page.connect_bar.address.setCurrentText(HOST)
    page.events.bar.interval.setValue(FAST)
    return page


def _connected_and_walked(page, settle):
    """Click through the two steps a watch needs, as the operator does."""
    from wing_parser.ui.live_state import LiveState

    page.connect_bar.connect_button.click()
    assert settle(lambda: page.state is LiveState.CONNECTED), "no handshake"
    page.discovery.discover_button.click()
    assert settle(lambda: page.events._watch_list is not None), "no walk"
    assert page.state is LiveState.CONNECTED


def test_a_watch_runs_on_the_page_and_a_lost_desk_reconnects(qt_app, settle):
    """connect -> discover -> watch -> an event -> lost -> reconnect.

    The whole watch branch of the wiring in one pass, with nothing
    injected: `started`, `lost` and `reconnect_requested` all arrive from
    the widgets that really emit them.
    """
    from wing_parser.ui.live_state import LiveState

    page = _watch_page([
        {"/ch/1/$fdr": _fader("/ch/1/$fdr", -6.0)},      # read_labels
        {"/ch/1/$fdr": _fader("/ch/1/$fdr", -6.0)},      # priming sample
        {"/ch/1/$fdr": _fader("/ch/1/$fdr", -3.0)},      # round 1: one event
        {}, {}, {},                                      # three silent rounds
    ])
    _connected_and_walked(page, settle)

    page.events.bar.start_button.click()
    assert page.state is LiveState.WATCHING, "the page never heard `started`"
    assert not page.snapshot.pull_button.isEnabled(), "a watch refuses a pull"
    assert settle(lambda: page.events.model.rowCount() >= 1), "no event landed"

    assert settle(lambda: page.state is LiveState.LOST), (
        "the page never heard `lost`")
    assert page.events.model.rowCount() >= 1, "the events stay on screen"
    assert page.connect_bar.lamp.property("azStyle") == "danger"
    assert settle(lambda: not page.events.is_watching()), "the thread lived on"

    assert page.events.bar.reconnect_button.isEnabled()
    page.events.bar.reconnect_button.click()
    assert page.state is LiveState.CONNECTING, "Reconnect is a dead button"
    assert settle(lambda: page.state is LiveState.CONNECTED)


def test_disconnecting_a_running_watch_abandons_its_thread(qt_app, settle):
    """Disconnect out of a real watch, not an injected one.

    `ConnectBar.disconnect_now` sets its own state and emits; the page
    fires `disconnect` and fans `set_state`, and it is that fan that
    reaches `LiveEventsView.set_state` and abandons the session. Every
    part of that was covered alone; the composition was only inferred.
    """
    from wing_parser.ui.live_state import LiveState

    page = _watch_page(_two_events())       # never goes silent: no DeskLost
    _connected_and_walked(page, settle)

    page.events.bar.start_button.click()
    assert page.state is LiveState.WATCHING
    assert settle(lambda: page.events.is_watching()), "the thread never ran"

    page.connect_bar.disconnect_button.click()
    assert page.state is LiveState.DISCONNECTED
    assert settle(lambda: not page.events.is_watching()), (
        "the thread outlived Disconnect")
    assert not page.events.bar.start_button.isEnabled()
    assert page.connect_bar.connect_button.isEnabled()


def test_stopping_a_watch_from_the_page_returns_it_to_connected(
        qt_app, settle):
    """The third `events.*` connect: `stopped` -> the page, not just the row.

    Split from the two above because neither reaches it -- one ends in
    `lost`, and the other abandons its session, whose terminal signal
    the gate drops on purpose (`live_watch_session.py:123-135`).
    """
    from wing_parser.ui.live_state import LiveState

    page = _watch_page(_two_events())       # never goes silent: no DeskLost
    _connected_and_walked(page, settle)

    page.events.bar.start_button.click()
    assert page.state is LiveState.WATCHING
    assert settle(lambda: page.events.model.rowCount() >= 1), "no event landed"

    page.events.bar.stop_button.click()
    assert settle(lambda: page.state is LiveState.CONNECTED), (
        "the page never heard `stopped`")
    assert settle(lambda: not page.events.is_watching())
    assert page.events.model.rowCount() >= 1, "Stop keeps what it collected"
    assert page.events.bar.start_button.isEnabled(), "and another watch is offered"
    assert page.snapshot.pull_button.isEnabled(), "the desk is free again"


def test_the_windows_refresh_cannot_clear_the_banner_the_pull_just_raised(
        qt_app, settle, monkeypatch, vu_result):
    """`SnapshotPanel.set_session`'s identity guard, composed.

    A pulled session travels panel -> page -> window -> `_refresh` ->
    `set_session` and lands back on the panel that produced it. Without
    the `session is self._session` guard that round trip clears
    `original` and hides the incomplete banner the same pull raised one
    moment earlier -- a partial scene would then look like a whole desk,
    which is the one thing that banner exists to prevent.

    The page under test is **the window's own**, with the transport
    swapped underneath it. `_wired` above hands `wire_console` a
    standalone panel that is not in `window.pages`, so `_refresh` never
    reaches it -- and a first draft of this test built that way passed
    with the guard deleted, which is how the difference was found.
    """
    from wing_parser.ui.live_state import LiveState
    from wing_parser.ui.main_window import MainWindow

    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    partial = dataclasses.replace(
        vu_result,
        unresolved_nodes=("/mtx", "/dca"),
        unresolved_leaves=("/ch/7/$fdr",),
    )
    window = MainWindow(None)
    page = window.pages["console"]
    page.snapshot._transport = _replaying(partial)
    page.snapshot.set_host(HOST)
    page._apply_state(LiveState.CONNECTED)

    page.snapshot.pull_button.click()
    assert settle(lambda: window.session is not None), "no session arrived"
    assert page.snapshot._session is window.session, "two different scenes"
    assert page.snapshot.banner.isVisibleTo(page.snapshot), (
        "the window's own _refresh hid the incomplete banner")
    assert "/mtx" in page.snapshot.banner.text()


def test_the_panel_does_not_keep_the_as_pulled_json(qt_app, settle, vu_result):
    """Nothing read it, and it was a second copy of the whole scene.

    `SnapshotPanel.original` was documented as "Diff's as-pulled
    baseline", but Diff never reached for it and neither did anything
    else under `wing_parser/ui/` -- one test assertion was its only
    reader. Holding it cost a megabyte-scale string per pull for a
    consumer that does not exist; export goes through
    `Session.save_as`, which is the point D3 was really making.
    """
    panel = _snapshot_panel(_replaying(vu_result))
    assert _pull_settled(panel, settle)
    assert panel._session is not None, "the pull produced no scene"
    assert not hasattr(panel, "original"), (
        "the panel is holding a second copy of the scene nothing reads")


def test_a_terminal_signal_from_a_view_that_already_left_watching_is_silent(
        qt_app):
    """`LiveEventsView._leave`'s guard -- an invariant, not a fixed bug.

    Reaching this through the UI is not possible today: `set_state`
    abandons a running session on the way out of `watching`, and
    `WatchSession._gate` drops an abandoned session's terminal signal
    (`live_watch_session.py:123-135`). The guard keeps the view's
    contract -- *it announces only a transition it actually made* --
    true by construction, rather than by two other modules staying
    correct; without it the page fires `stop`/`lost` from a state whose
    table refuses the pair, i.e. a `ValueError` out of a Qt slot. Called
    directly, because no public path produces it.
    """
    from wing_parser.ui.live_state import LiveState

    view = _events_view(_watch_desk([]))        # CONNECTED, never started
    heard = []
    view.stopped.connect(lambda: heard.append("stopped"))
    view.lost.connect(heard.append)

    view._ended()
    view._failed(OSError("a late answer from a watch nobody is running"))

    assert heard == [], "a view that did not move asked its page to move"
    assert view._state is LiveState.CONNECTED
    assert not view.is_watching()


# -- the write gate (spec §8.1, §8.4, W1, W10) --------------------------


def _job(gate, address, after, on_result, on_error=None):
    from wing_parser.ui import live_wiring
    from wing_parser.ui.live_write import WriteConfirmation

    return live_wiring.WriteJob(
        confirmation=WriteConfirmation(
            host=HOST, address=address, after=after,
            identity=_identity(), desk_before=None),
        on_result=on_result,
        on_error=on_error or (lambda exc: None),
    )


def _gate_page(qt_app, desk=None):
    """A real ConsolePage over a FakeDesk, plus the gate live_wiring builds.

    Two deliberate departures from the task brief's draft of this helper,
    both forced by code the brief predates:

    * the gate's `timeout` is **2**, not 0. `CallRunner.start` reads
      `timeout` as the budget itself (`workers.py:112-117`), so 0 means
      "time out on the next event-loop pass" -- which is exactly what
      `test_a_timeout_shows_one_error_line_naming_the_host` uses it for.
      At 0 no write here could ever succeed. The timer is stopped by the
      first terminal path (`workers.py:167`), so 2 is a ceiling nothing
      waits for, not a delay.
    * the window is a real `QWidget`, not a plain Python class: the gate
      is parented to it and `QObject` rejects a non-`QObject` parent.
      Same ruling as `test_saving_the_dialog_puts_the_delay_on_the_window`
      (commit 0584548) -- production must not bend to a test double, and
      PySide6 widgets accept arbitrary instance attributes.
    """
    from PySide6.QtWidgets import QWidget

    from tests.fake_desk import FakeDesk
    from wing_parser.ui import live_wiring
    from wing_parser.ui.console_page import ConsolePage

    desk = FakeDesk(identity=_identity()) if desk is None else desk
    page = ConsolePage(transport=desk.transport(), timeout=0)

    window = QWidget()
    gate = live_wiring.install_write_gate(
        window, page, transport=desk.write_transport(), timeout=2)
    return window, page, gate, desk


def test_the_write_gate_starts_closed(qt_app):
    _w, _p, gate, _d = _gate_page(qt_app)
    assert gate.can_write() is False and gate.ready() is False


def test_the_gate_opens_in_connected_and_watching_and_in_no_other_state(qt_app):
    from wing_parser.ui.live_state import LiveState

    _w, page, gate, _d = _gate_page(qt_app)
    open_in = set()
    for state in LiveState:
        page._apply_state(state)
        if gate.can_write():
            open_in.add(state)
    assert open_in == {LiveState.CONNECTED, LiveState.WATCHING}


def test_ready_needs_the_gate_open_and_the_arm_state_armed(qt_app):
    from wing_parser.ui.live_state import LiveState

    _w, page, gate, _d = _gate_page(qt_app)
    page._apply_state(LiveState.CONNECTED)
    assert gate.ready() is False, "open but unarmed is not ready"
    gate.arm.arm(_identity())
    assert gate.ready() is True


#: Every dropout the gate listens for, with the state its event is LEGAL in
#: (`live_state._TABLE`) and the state the page lands in. Fired from anywhere
#: else, `ConsolePage._fire` raises inside its own Qt slot: PySide6 prints the
#: traceback, carries on to the next slot and `emit()` returns normally, so the
#: gate's assertions would still hold -- on two tracebacks of stderr noise per
#: run, and with the page left in a state the app could never be in. Code
#: review, round 1. `fail` is legal only in the three busy states, which is
#: exactly where each panel's own call runs, and all three are reachable while
#: armed: arm in CONNECTED, then click Connect/Discover/Pull.
_DROPOUTS = {
    # name:          (emitter attr,   payload,  fired from,    lands in)
    "disconnected":  ("connect_bar",  None,     "CONNECTED",   "DISCONNECTED"),
    "connect_failed": ("connect_bar", "gone",   "CONNECTING",  "ERROR"),
    "walk_failed":   ("discovery",    "gone",   "WALKING",     "ERROR"),
    "pull_failed":   ("snapshot",     "gone",   "PULLING",     "ERROR"),
    "lost":          ("events",       "desk lost", "WATCHING", "LOST"),
}


@pytest.mark.parametrize("dropout", sorted(_DROPOUTS))
def test_every_dropout_disarms_and_announces(qt_app, dropout):
    """W1/F4: `CallPanel.failed` is shared, so all three panels are driven.

    `test_the_gate_publishes_itself_on_the_window` proves the gate is on the
    window; this proves the gate's three dropout sources are all wired, which
    is what the Immediate level rests on -- the selector must fall back to
    Manual the moment the connection goes, or it names a level that is gone.
    """
    from wing_parser.ui.apply_level import ApplyLevel
    from wing_parser.ui.live_state import LiveState

    panel_name, payload, fired_from, lands_in = _DROPOUTS[dropout]
    _w, page, gate, _d = _gate_page(qt_app)
    page._apply_state(LiveState.CONNECTED)      # the gate is open here
    gate.arm.arm(_identity())
    gate.arm.level = ApplyLevel.IMMEDIATE
    page._apply_state(LiveState[fired_from])    # ...and the call is running
    heard = []
    gate.changed.connect(lambda: heard.append(True))

    panel = getattr(page, panel_name)
    signal = panel.disconnected if payload is None else (
        panel.lost if dropout == "lost" else panel.failed)
    signal.emit() if payload is None else signal.emit(OSError(payload))

    assert gate.arm.armed() is False
    assert gate.arm.level is ApplyLevel.MANUAL
    assert heard, "the selector must be told, or it shows a level that is gone"
    assert page.state is LiveState[lands_in], (
        "the page refused the transition, so this fired from a state "
        "`live_state._TABLE` does not document")


def test_two_immediate_submissions_never_overlap_on_the_wire(qt_app, settle):
    from wing_parser.ui.live_state import LiveState

    _w, page, gate, desk = _gate_page(qt_app)
    page._apply_state(LiveState.CONNECTED)
    gate.arm.arm(_identity())
    results = []
    for value in ("PRE", "POST"):
        gate.submit(_job(gate, "/ch/1/send/8/mode", value, results.append))

    assert settle(lambda: len(results) == 2)
    assert [call[0:2] for call in desk.sets] == [
        ("/ch/1/send/8/mode", "PRE"), ("/ch/1/send/8/mode", "POST")]


def test_a_closed_gate_never_reaches_the_transport(qt_app, settle):
    """Gate 4's late re-check: the state can go LOST under a countdown."""
    from wing_parser.ui import live_wiring
    from wing_parser.ui.live_state import LiveState

    _w, page, gate, desk = _gate_page(qt_app)
    page._apply_state(LiveState.CONNECTED)
    gate.arm.arm(_identity())
    page._apply_state(LiveState.LOST)
    errors = []
    gate.submit(_job(gate, "/ch/1/fdr", -6.0, lambda r: None, errors.append))

    assert settle(lambda: errors)
    assert desk.sets == []
    assert isinstance(errors[0], live_wiring.GateClosed)


def test_an_unarmed_gate_never_reaches_the_transport(qt_app, settle):
    from wing_parser.ui.live_state import LiveState

    _w, page, gate, desk = _gate_page(qt_app)
    page._apply_state(LiveState.CONNECTED)
    errors = []
    gate.submit(_job(gate, "/ch/1/fdr", -6.0, lambda r: None, errors.append))
    assert settle(lambda: errors)
    assert desk.sets == []


def test_the_gate_publishes_itself_on_the_window(qt_app):
    window, _p, gate, _d = _gate_page(qt_app)
    assert window.write_gate is gate


def test_the_console_page_gained_no_signal_for_this(qt_app):
    """W7: `console_page.py` is at 199 of the 200-line ceiling. The gate
    reads `page.state` and listens to the panels' OWN signals."""
    from wing_parser.ui.console_page import ConsolePage

    assert not hasattr(ConsolePage, "state_changed")
