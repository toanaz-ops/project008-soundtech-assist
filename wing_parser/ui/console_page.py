"""The Console page: four panels, one state, and no rule of its own.

Spec S6's assembly. Everything on this page already knows how to do its
own job -- the handshake, the walk, the pull, the watch -- so what is
left here is the one thing none of them can own alone: **which state the
console connection is in**. Every button's enabled-ness comes from
`live_state.allowed_actions`; there is no `setEnabled` in this file at
all, and `test_every_button_matches_allowed_actions_in_every_state`
exhausts that -- eight states against every QPushButton the page
contains, `findChildren` deciding what "every" means.

**Panel signals in, `set_state` out.** A panel reports what happened
(`connected`, `failed`, `discovered`, `session_pulled`, `started`,
`stopped`, `lost`) and the page answers with `transition(state, event)`,
then fans the result to all four -- the page's `_state` is the only one
that decides anything. A panel does still move its OWN copy first, when
its call starts (`live_call_panel.py:125-126`); the page reads that
through `CallPanel.state` for one question -- did the call actually
begin? -- and then overwrites it with the fanned value. `transition`
raises on a pair S6 does not document rather than leaving a stale page,
so a wiring mistake here fails loudly in a test instead of quietly at a
venue.

**Three `CallRunner`s, not one.** The design named a single runner on
this page; the three one-shot panels were built owning one each
(`live_call_panel.py:56`) -- the watch is not one of them, it runs a
`GeneratorWorker` (`live_watch_session.py:102`) -- and that is what
shipped. Mutual exclusion of `connecting`/`walking`/`pulling` does not
depend on the difference: the state table disables every other button
while one of them runs, and each panel's own runner refuses a second
call while one is in flight (`workers.py:112-113`). What one shared
runner would add is a further refusal path for something the table
already forbids.

**Layout** (S6): connect bar across the top, discovery and snapshot side
by side under it, the events view below with all the stretch. Both
middle panels are short and narrow -- a caption, a few buttons, two or
three lines -- while the event table is the one thing here worth more
rows. Measured on a 1366x768 window (2026-09-16): the middle band is
100 px side by side and would be ~206 px stacked, so stacking would take
roughly a quarter of the table's 435 px and give it to whitespace.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QVBoxLayout, QWidget

from wing_parser.ui.live_connect_bar import ConnectBar
from wing_parser.ui.live_discovery import DiscoveryPanel
from wing_parser.ui.live_events_view import LiveEventsView
from wing_parser.ui.live_snapshot import SnapshotPanel
from wing_parser.ui.live_state import LiveState, allowed_actions, transition


class ConsolePage(QWidget):
    """Connect bar, discovery, snapshot and watch, over one state."""

    #: The three `live_wiring.wire_console` connects, re-emitted whole
    #: from `SnapshotPanel`: its contract is all three or none of them
    #: (`live_wiring.py:37-54`).
    session_pulled = Signal(object)
    exported = Signal(str)
    doctor_requested = Signal()
    #: The address a handshake actually landed on, for the window to
    #: remember -- persisting is `window_state`'s job, not a widget's.
    host_connected = Signal(str)

    def __init__(self, parent=None, *, transport=None, timeout=None) -> None:
        super().__init__(parent)
        self._state = LiveState.DISCONNECTED
        self.connect_bar = ConnectBar(transport=transport, timeout=timeout)
        self.discovery = DiscoveryPanel(transport=transport, timeout=timeout)
        self.snapshot = SnapshotPanel(transport=transport, timeout=timeout)
        self.events = LiveEventsView(transport=transport)

        middle = QHBoxLayout()
        middle.addWidget(self.discovery, 1)
        middle.addWidget(self.snapshot, 1)
        layout = QVBoxLayout(self)
        layout.addWidget(self.connect_bar)
        layout.addLayout(middle)
        layout.addWidget(self.events, 1)

        self._wire()
        self._apply_state(LiveState.DISCONNECTED)

    # -- what the window drives -------------------------------------------

    @property
    def state(self) -> LiveState:
        """The one state this page and its four panels are wearing."""
        return self._state

    def set_session(self, session) -> None:
        """`MainWindow._refresh`'s fan-out (`main_window.py:176-178`).

        A sync, and nothing else: the Console page is not the session's
        consumer, but `SnapshotPanel` shows a scene-loaded line and gates
        Export and Open Doctor on one, and a panel still describing a
        scene the window has replaced is worse than the coupling
        (orchestrator ruling, task 13).
        """
        self.snapshot.set_session(session)

    def set_consoles(self, consoles) -> None:
        """Offer the remembered addresses, most recent first."""
        self.connect_bar.set_consoles(consoles)

    # -- the wiring, whole -------------------------------------------------

    def _wire(self) -> None:
        bar, walk = self.connect_bar, self.discovery
        pull, watch = self.snapshot, self.events

        bar.connect_button.clicked.connect(lambda: self._begun("connect", bar))
        bar.connected.connect(self._connected)
        bar.disconnected.connect(lambda: self._fire("disconnect"))

        walk.discover_button.clicked.connect(lambda: self._begun("walk", walk))
        walk.rerun_button.clicked.connect(lambda: self._begun("walk", walk))
        walk.discovered.connect(self._discovered)

        pull.pull_button.clicked.connect(lambda: self._begun("pull", pull))
        pull.session_pulled.connect(self._pulled)
        pull.exported.connect(self.exported)
        pull.doctor_requested.connect(self.doctor_requested)

        watch.started.connect(lambda: self._fire("watch"))
        watch.stopped.connect(lambda: self._fire("stop"))
        watch.lost.connect(lambda _exc: self._fire("lost"))
        # Reconnect is offered in `lost` but the handshake is the bar's
        # (`live_watch_bar.py:10-14`); unconnected it is a dead button.
        watch.reconnect_requested.connect(self._reconnect)

        for panel in (bar, walk, pull):
            panel.failed.connect(lambda _exc: self._fire("fail"))
            panel.cancel_button.clicked.connect(self._cancelled)

    # -- the one state -----------------------------------------------------

    def _apply_state(self, state: LiveState) -> None:
        """Wear `state`, and put every panel in it. The only writer."""
        self._state = state
        for panel in (self.connect_bar, self.discovery,
                      self.snapshot, self.events):
            panel.set_state(state)

    def _fire(self, event: str) -> None:
        """Move by the table; `transition` raises on an illegal pair."""
        self._apply_state(transition(self._state, event))

    def _begun(self, event: str, panel) -> None:
        """Adopt `event` only if `panel`'s call really started.

        A refused start -- no address typed, a call of that kind already
        running -- leaves the panel in its idle state and reports its own
        line. Firing anyway would park the page in a busy state whose
        only action is a Cancel with nothing to cancel.
        """
        if panel.state is transition(self._state, event):
            self._apply_state(panel.state)

    def _cancelled(self) -> None:
        """Whichever Cancel was pressed, the page leaves the busy state.

        Each panel has already reverted itself to the state this
        transition names (`live_call_panel.py:75-80`); the guard covers a
        Cancel pressed with no call running, which the table refuses.
        """
        if "cancel" in allowed_actions(self._state):
            self._fire("cancel")

    def _reconnect(self) -> None:
        """Reconnect: the bar's handshake, started from the watch's row.

        Called rather than connected straight to `connect_now`, so the
        page hears the start it would otherwise only see on a click.
        """
        self.connect_bar.connect_now()
        self._begun("connect", self.connect_bar)

    # -- what the panels report --------------------------------------------

    def _connected(self, identity) -> None:
        host = self.connect_bar.host()
        self.snapshot.set_identity(identity)
        for panel in (self.discovery, self.snapshot, self.events):
            panel.set_host(host)
        self._fire("ok")
        self.host_connected.emit(host)

    def _discovered(self, watch_list) -> None:
        self.events.set_watch_list(watch_list)
        self._fire("ok")

    def _pulled(self, session) -> None:
        self._fire("ok")
        self.session_pulled.emit(session)
