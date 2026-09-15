"""What the Console page's three signals do to the window.

`window_state.py`'s job, for the one scene that arrives from a desk
rather than from a file -- kept out of `main_window.py`, which is at
189 lines and would not survive a fourth responsibility, and out of
`live_snapshot.py`, which must not import the window it talks to.

The adopt path here is deliberately **not** `window_state.adopt_session`
(`:68-72`): that one opens with `switch_to("doctor")`, and D16 says a
pull leaves the view where it is. A watch may be running and the
operator may want to pull again; yanking the page away mid-session costs
more than the one click `Open Doctor` asks for.
"""

from __future__ import annotations

from wing_parser.ui import window_state


def adopt_pulled_session(window, session) -> None:
    """Everything a freshly *pulled* scene needs, minus the page switch.

    `window_state.adopt_session` without its `switch_to("doctor")` (D16),
    and without `remember_recent` (D4): the session's path is a bare
    suggested filename naming nothing on disk, so a recent-menu entry
    would later pop "File is gone" and self-heal itself away
    (`window_state.py:50-66`). `SnapshotPanel.exported` is what puts a
    real path in that menu, once one exists.
    """
    window.session = session
    window._show_finding(None)
    window._refresh()


def wire_console(window, page) -> None:
    """Connect the Console page to the window, if the page is built yet.

    The `hasattr` guard is the same idiom `MainWindow._refresh` uses for
    `set_session` (`main_window.py:174-176`) and exists for the same
    reason: the Console page arrives over several tasks, and until task
    13 replaces it the slot still holds task 8's `EmptyState`, which has
    none of these signals. A page that has `session_pulled` is expected
    to carry all three -- they are one contract, not three optional
    ones, so a page missing the other two should fail loudly here rather
    than silently drop Export or Open Doctor.
    """
    if not hasattr(page, "session_pulled"):
        return
    page.session_pulled.connect(
        lambda session: adopt_pulled_session(window, session))
    page.exported.connect(
        lambda path: window_state.remember_recent(window, path))
    page.doctor_requested.connect(lambda: window.switch_to("doctor"))
