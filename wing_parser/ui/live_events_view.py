"""The watch, as it happens: one session, its events, and how it ended.

Three parts, each with its own reasons, bound here: `live_watch_bar.py`
(the controls, and the rate line, whose arithmetic is
`live_guard.watch_rate`'s -- the one subtraction left here reads the
clock the session started on, and is not the readout),
`live_events_table.py` (D8 -- not `ChangesPanel`) and
`live_watch_session.py` (D5 -- one `GeneratorWorker` per watch, never a
GUI-thread `QTimer`). Not a `CallPanel` either: that shell is one call
with one numeric budget; a watch is a stream with no deadline (S7.2).

**Three things end a watch, not one.** Stop; a `set_state` that walks
out of `watching` (`disconnect` is allowed there, so the page's own
Disconnect arrives as one); and `shutdown()` at `aboutToQuit`, hooked in
the constructor. The last two abandon the session, and the terminal
signal that follows is dropped rather than left to drag the page back
out of the state it was just put in.

Two ways out of a *running* watch, exactly the two `live_state.py`
documents: `stop` -> `connected`, and `lost` -> `lost`, which **keeps
the table on screen** -- those events were real -- and offers Reconnect
(S7.3). Any other failure ends in `lost` too, in its own sentence:
`DeskLost` is only the *silent* way for a desk to go away.
"""
from __future__ import annotations

import time

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from wing_parser.ui import live_controller
from wing_parser.ui.live_events_table import EventTable
from wing_parser.ui.live_guard import DeskLost
from wing_parser.ui.live_state import LiveState, allowed_actions, transition
from wing_parser.ui.live_watch_bar import WatchBar
from wing_parser.ui.live_watch_session import WAIT_MS, WatchSession, on_quit
from wing_parser.ui.texts import text


class LiveEventsView(QWidget):
    """The Console page's watch section, `bar` + `table` + a status line."""

    started = Signal()              # a watch session actually began
    stopped = Signal()              # it ended on Stop, or ran itself out
    lost = Signal(object)           # the DeskLost (or OSError) that ended it
    reconnect_requested = Signal()  # Reconnect, offered only in `lost`

    def __init__(self, parent=None, *, transport=None, clock=time.monotonic):
        super().__init__(parent)
        self._transport = transport or live_controller.REAL
        self._clock = clock
        self._state = LiveState.DISCONNECTED
        self._host = ""
        self._watch_list = None
        self._session = None
        self._started_at = 0.0

        self.bar = WatchBar()
        self.table = EventTable()
        self.model = self.table.model   # what the page reads rows off
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(self.bar)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.status_label)

        self.bar.start_button.clicked.connect(self.start_watch)
        self.bar.stop_button.clicked.connect(self.stop_watch)
        self.bar.reconnect_button.clicked.connect(
            self.reconnect_requested.emit)
        self.set_state(LiveState.DISCONNECTED)
        on_quit(self.shutdown)

    # -- what the owner drives ---------------------------------------------

    def set_host(self, host: str) -> None:
        """The console address to watch -- read off `ConnectBar`."""
        self._host = host

    def set_watch_list(self, watch_list) -> None:
        """What discovery found. Without one there is nothing to watch."""
        self._watch_list = watch_list
        self._refresh_buttons()

    def set_state(self, state: LiveState) -> None:
        """Wear `state` -- and abandon the watch if it is not `watching`.

        Not only a repaint: `disconnect` is allowed in `watching` and
        `ConnectBar.disconnect_now` sets state directly
        (`live_connect_bar.py:150`), so that arrives here as a bare
        `set_state`. Uncancelled, the worker polls on forever with Stop
        hidden and `stop_watch` refusing."""
        if (self._state is LiveState.WATCHING
                and state is not LiveState.WATCHING and self.is_watching()):
            self._session.abandon()
        self._state = state
        self._refresh_buttons()

    def shutdown(self, wait_ms: int = WAIT_MS) -> bool:
        """End a live watch and wait for its thread. True if it ended.

        Hooked to `aboutToQuit` -- nothing else would, `closeEvent` only
        saves window state. Safe on a view that never watched."""
        return self._session is None or self._session.finish(wait_ms)

    def is_watching(self) -> bool:
        """True while this session's thread is still running."""
        return self._session is not None and self._session.is_running()

    # -- the session --------------------------------------------------------

    def start_watch(self) -> bool:
        """Open a watch on its own thread; False if it never began."""
        if "watch" not in allowed_actions(self._state):
            return False
        if not self._host:
            self.status_label.setText(text("console.no_address"))
            return False
        if self._watch_list is None:
            self.status_label.setText(text("console.no_watch_list"))
            return False

        self.table.clear_events()
        self._started_at = self._clock()
        session = WatchSession(self._transport, self._host,
                               self._watch_list, self.bar.interval.value())
        session.bind(self._append, self._round, self._ended, self._failed)
        self._session = session

        self.set_state(transition(self._state, "watch"))
        self.status_label.setText(text("console.watching").format(
            host=self._host, total=len(self._watch_list.addresses)))
        self._render_rate()
        session.start()
        self.started.emit()
        return True

    def stop_watch(self) -> bool:
        """Ask the guard to stop; it raises before its next round."""
        if self._session is None or "stop" not in allowed_actions(self._state):
            return False
        self._session.stop()
        self.bar.stop_button.setEnabled(False)
        self.status_label.setText(text("console.stopping"))
        return True

    # -- what the worker reports -------------------------------------------

    def _append(self, change) -> None:
        self.table.append(change)
        self._render_rate()

    def _round(self, _answered: int, _total: int) -> None:
        self._render_rate()             # every round, no QTimer (D5)

    def _ended(self, summary=None) -> None:
        """Either terminal signal, for a session the gate did not drop."""
        self.status_label.setText(
            text("console.watch_cancelled") if summary is None
            else text("console.watch_stopped").format(
                events=summary.events, rounds=summary.rounds))
        self._leave("stop", self.stopped)

    def _failed(self, exc) -> None:
        """`DeskLost`, or any other OSError/ValueError the stream raised.

        Both end in `lost` -- `watching` has no third exit -- but not in
        the same sentence: a stale watch list is not a quiet desk, and
        reading one as the other sends him to check cables."""
        self.status_label.setText(text(
            "console.watch_lost" if isinstance(exc, DeskLost)
            else "console.watch_failed").format(host=self._host, error=exc))
        self._leave("lost", self.lost, exc)

    # -- internals ---------------------------------------------------------

    def _leave(self, event: str, signal, *payload) -> None:
        """Leave `watching` by `event` and say so -- or do neither.

        The signal is INSIDE the guard (task 13 review): it is the
        page's cue to fire the same event on its own table, so a view
        that did not move must not ask the page to -- both tables raise
        on `stop`/`lost` from a state S6 does not document, which is
        also why the check comes first. The session stays referenced
        either way: a `QThread` losing its last reference is deleted."""
        if self._state is not LiveState.WATCHING:
            self._refresh_buttons()
            return
        self.set_state(transition(self._state, event))
        signal.emit(*payload)

    def _render_rate(self) -> None:
        self.bar.show_rate(
            self.table.count(), self._clock() - self._started_at)

    def _refresh_buttons(self) -> None:
        self.bar.set_actions(self._state, self._watch_list is not None)
