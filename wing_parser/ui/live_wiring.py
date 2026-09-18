"""What the Console page's signals do to the window.

`window_state.py`'s job, for the one scene that arrives from a desk
rather than from a file -- kept out of `main_window.py`, which is at
190 lines and would not survive a fourth responsibility, and out of
`live_snapshot.py`, which must not import the window it talks to.

The adopt path here is deliberately **not** `window_state.adopt_session`
(`window_state.py:94-98`): it opens with `switch_to("doctor")`, and D16 says a
pull leaves the view where it is. The operator is mid-console-workflow
-- start a watch, rerun a short discovery, export what he just pulled --
and all of that is on this page; yanking the view away costs him the
place he was working in, where staying costs one click on Open Doctor.
"""

from __future__ import annotations

from wing_parser.ui import window_state
from wing_parser.ui.write_gate import GateClosed, WriteGate, WriteJob  # noqa: F401 -- re-export (Task 11 escape hatch)


def adopt_pulled_session(window, session) -> None:
    """Everything a freshly *pulled* scene needs, minus the page switch.

    `window_state.adopt_session` without its `switch_to("doctor")` (D16),
    and without `remember_recent` (D4): the session's path is a bare
    suggested filename naming nothing on disk, so a recent-menu entry
    would later pop "File is gone" and self-heal itself away
    (`window_state.py:76-89`). `SnapshotPanel.exported` is what puts a
    real path in that menu, once one exists.
    """
    window.session = session
    window._show_finding(None)
    window._refresh()


def wire_console(window, page) -> None:
    """Connect the Console page to the window, if the page is built yet.

    **The contract is all three signals or none of them.** A Console
    page offers `session_pulled`, `exported` and `doctor_requested`, or
    it offers nothing and this is a no-op -- task 13's `ConsolePage`
    re-emits all three from its `SnapshotPanel`, and this function is
    also handed that panel directly by several tests. The `hasattr` is
    the same idiom `MainWindow._refresh` uses for `set_session`
    (`main_window.py:176-178`), and existed for the same reason: the
    Console page arrived over several tasks, and until task 13 the slot
    held task 8's `EmptyState`, which has none of the three. The branch
    is still live and still pinned -- any widget without them reaches
    here. Deliberately only the first signal is guarded: a page carrying
    `session_pulled` but missing one of the other two is a half-built
    contract and raises `AttributeError` here, at construction, rather
    than silently dropping Export or Open Doctor at a venue. Both
    branches are pinned in `tests/test_ui_console.py`.
    """
    if not hasattr(page, "session_pulled"):
        return
    page.session_pulled.connect(
        lambda session: adopt_pulled_session(window, session))
    page.exported.connect(
        lambda path: window_state.remember_recent(window, path))
    page.doctor_requested.connect(lambda: window.switch_to("doctor"))
    # The fourth is outside that contract and carries its own guard: it
    # is a whole-page signal (the address a handshake landed on, for
    # `window_state` to remember), and `SnapshotPanel` -- which this
    # function is handed directly by several tests, and which owns the
    # three above -- does not have it.
    if hasattr(page, "host_connected"):
        page.host_connected.connect(
            lambda host: window_state.remember_console(window, host))


def install_write_gate(window, page, *, transport=None, timeout=None) -> WriteGate:
    """Build the gate, publish it on the window, wire every dropout to it.

    The three sources are the page's EXISTING signals: `console_page.py` is
    at 199 of the 200-line ceiling and may not grow a state signal (W7),
    and these are exactly the transitions into DISCONNECTED, ERROR and LOST
    (`console_page.py:117-138`).
    """
    gate = WriteGate(page, transport=transport, timeout=timeout, parent=window)
    window.write_gate = gate
    page.connect_bar.disconnected.connect(gate.close)
    page.events.lost.connect(lambda _exc: gate.close())
    for panel in (page.connect_bar, page.discovery, page.snapshot):
        panel.failed.connect(lambda _exc: gate.close())
    changes = getattr(window, "changes_panel", None)
    if changes is not None:
        changes.attach_gate(gate)          # task 12 gives ChangesPanel this
    return gate
