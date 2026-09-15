"""The watch, as it happens: one session, its events, and how it ended.

The three parts each carry their own reasons, and this binds them: the
controls are `live_watch_bar.py`, the table `live_events_table.py`
(D8 -- why this is not `ChangesPanel`), and the thread and its cancel
`live_watch_session.py` (D5 -- one `GeneratorWorker` per watch, never a
GUI-thread `QTimer`). Not a `CallPanel` (`live_call_panel.py`): that
shell is one call, one result, one numeric budget, and a watch is a
stream that runs for a whole show with no deadline at all (spec S7.2).
Its conventions still hold here -- an injected transport, `set_state`
driving every button off `allowed_actions`, every string from
`texts_console.py`.

**No arithmetic here.** Rate and elapsed both come back from
`live_guard.watch_rate`, its zero-second case included: that is the one
with a bug to have, because the line renders the moment Start is
pressed, before any time has passed. The single clock subtraction below
reads how long the session has run; it is not the readout.

Two ways out of a running watch, exactly the two `live_state.py`
documents: `stop` -> `connected`, and `lost` -> `lost`, which **keeps
the table on screen** -- those events were real -- and offers Reconnect
(spec S7.3). Any other failure mid-watch ends in `lost` too, carrying
its own sentence: `DeskLost` is only the *silent* way for a desk to go
away, and the state table has no third exit to offer the rest.
"""

from __future__ import annotations

import time

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from wing_parser.ui import live_controller, live_guard
from wing_parser.ui.live_events_table import EventTable
from wing_parser.ui.live_state import LiveState, allowed_actions, transition
from wing_parser.ui.live_watch_bar import WatchBar
from wing_parser.ui.live_watch_session import WatchSession
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
        self._events = 0
        self._started_at = 0.0

        self.bar = WatchBar()
        self.table = EventTable()
        #: The table's model: the page and its tests read rows off it.
        self.model = self.table.model
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

    # -- what the owner drives ---------------------------------------------

    def set_host(self, host: str) -> None:
        """The console address to watch -- read off `ConnectBar`."""
        self._host = host

    def set_watch_list(self, watch_list) -> None:
        """What discovery found. Without one there is nothing to watch."""
        self._watch_list = watch_list
        self._refresh_buttons()

    def set_state(self, state: LiveState) -> None:
        """Wear `state`: which of Start/Stop/Reconnect are live now."""
        self._state = state
        self._refresh_buttons()

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
        self._events = 0
        self._started_at = self._clock()
        session = WatchSession(self._transport, self._host,
                               self._watch_list, self.bar.interval.value())
        session.worker.produced.connect(self._append)
        session.worker.progress.connect(self._round)
        session.worker.finished.connect(self._ended)
        session.worker.finished_cancelled.connect(self._ended)
        session.worker.failed.connect(self._failed)
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
        self._events += 1
        self._render_rate()

    def _round(self, _answered: int, _total: int) -> None:
        """Every guarded round re-renders the rate line -- no QTimer (D5).
        The counts themselves are the page's to show (task 13)."""
        self._render_rate()

    def _ended(self, summary=None) -> None:
        """`finished` (with a summary) and `finished_cancelled` (without)."""
        self.status_label.setText(
            text("console.watch_cancelled") if summary is None
            else text("console.watch_stopped").format(
                events=summary.events, rounds=summary.rounds))
        self._leave("stop")
        self.stopped.emit()

    def _failed(self, exc) -> None:
        """`DeskLost`, or any other OSError/ValueError the stream raised."""
        self.status_label.setText(text("console.watch_lost").format(
            host=self._host, error=exc))
        self._leave("lost")
        self.lost.emit(exc)

    # -- internals ---------------------------------------------------------

    def _leave(self, event: str) -> None:
        """Fire `event`, but only if the page is still watching.

        `transition` raises on a pair S6 does not document, and a last
        round can land after the page has already been moved on -- a
        disconnect while it was in flight. The session itself is kept
        referenced either way: a `QThread` whose last reference goes
        while it still runs is destroyed mid-run.
        """
        if self._state is LiveState.WATCHING:
            self.set_state(transition(self._state, event))
        else:
            self._refresh_buttons()

    def _render_rate(self) -> None:
        rate, elapsed = live_guard.watch_rate(
            self._events, self._clock() - self._started_at)
        self.bar.rate_label.setText(
            text("console.watch_rate").format(rate=rate, elapsed=elapsed))

    def _refresh_buttons(self) -> None:
        self.bar.set_actions(self._state, self._watch_list is not None)
