"""The watch's control row: Start, Stop, Reconnect, interval, rate.

Everything the operator can touch while a watch runs, and nothing that
knows a watch is running: no transport, no worker, no state of its own.
`set_actions` is handed the page's state and answers the only question
this row asks of it -- which of these three buttons are live -- off the
one table `live_state.py` exhausts (`allowed_actions`), so no
`setEnabled` is scattered anywhere else.

Reconnect lives here rather than beside the connect bar because it is
offered in `lost`, and `lost` is the state this row's own watch reached
-- the table above it still holds the events that desk really sent
(spec S7.3). It only asks: `LiveEventsView` re-emits it, and the page
gives it to `ConnectBar`, which owns the handshake.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from wing_parser.ui import live_guard
from wing_parser.ui.live_guard import (
    DEFAULT_INTERVAL,
    MAX_INTERVAL,
    MIN_INTERVAL,
)
from wing_parser.ui.live_state import LiveState, allowed_actions
from wing_parser.ui.texts import text
from wing_parser.ui.theme.widgets import Caption

class WatchBar(QWidget):
    """Start/Stop/Reconnect, the interval spin, and the rate line."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.start_button = QPushButton(text("console.start"))
        self.stop_button = QPushButton(text("console.stop"))
        self.reconnect_button = QPushButton(text("console.reconnect"))
        self.reconnect_button.setVisible(False)
        self.interval = QDoubleSpinBox()
        self.interval.setDecimals(2)
        self.interval.setRange(MIN_INTERVAL, MAX_INTERVAL)
        self.interval.setSingleStep(MIN_INTERVAL)
        self.interval.setValue(DEFAULT_INTERVAL)
        self.interval.setSuffix(text("console.interval_suffix"))
        self.rate_label = QLabel("")

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(Caption(text("console.watch")))
        row.addWidget(self.start_button)
        row.addWidget(self.stop_button)
        row.addWidget(self.reconnect_button)
        row.addWidget(QLabel(text("console.interval")))
        row.addWidget(self.interval)
        row.addWidget(self.rate_label, 1)

    def show_rate(self, events: int, seconds: float) -> None:
        """The rate line. **No arithmetic here**: both numbers come back
        from `live_guard.watch_rate`, its zero-second case included --
        that is the one with a bug to have, because this renders the
        moment Start is pressed, before any time has passed."""
        rate, elapsed = live_guard.watch_rate(events, seconds)
        self.rate_label.setText(
            text("console.watch_rate").format(rate=rate, elapsed=elapsed))

    def set_actions(self, state: LiveState, watchable: bool) -> None:
        """Wear `state`. `watchable` is "discovery has been run" -- a
        state that allows a watch still has nothing to watch without it."""
        actions = allowed_actions(state)
        self.start_button.setEnabled("watch" in actions and watchable)
        self.stop_button.setEnabled("stop" in actions)
        self.stop_button.setVisible(state is LiveState.WATCHING)
        self.reconnect_button.setVisible(state is LiveState.LOST)
        self.reconnect_button.setEnabled("connect" in actions)
        # The interval is the loop's own pacing: changing it mid-watch
        # would say something the running poller cannot hear.
        self.interval.setEnabled(state is not LiveState.WATCHING)
