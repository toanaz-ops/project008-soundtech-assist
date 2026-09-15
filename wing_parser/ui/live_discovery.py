"""The Console page's inventory row: Discover, leaf counts, the banner.

Mirrors `live_connect_bar.py` in shape: a `transport`-injected widget that
runs one call through `CallRunner` + `ButtonRunner` under a named kind
(here `"walk"`, `live_controller.discover` -> `WatchList`), and maps
`LiveState` -> enabled buttons through `live_state.allowed_actions`
rather than a scattered `setEnabled`. What it owns that the bar does not
is a *result*: `set_result` renders the leaf total, the per-family
inventory, and -- the load-bearing part of this page (spec S6) -- the
unresolved banner.

The banner exists because of one measured incident (2026-08-23): a walk
opened a watch on 16 leaves with seven top-level families unresolved,
and an immediate rerun resolved all 220. `WatchList.unresolved` carries
those family node names (`net/watch/list.py:39-48`, sourced from
`SchemaResult.unresolved_nodes`, `net/schema.py:109`) precisely so a
short list is never silently mistaken for a complete one. No progress
bar while a walk runs (D7): `walk_schema` (`schema.py:68`) is a
breadth-first loop with no callback seam, and this wave does not touch
`net/`.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from wing_parser.ui import live_controller
from wing_parser.ui.call_button import ButtonRunner
from wing_parser.ui.live_state import LiveState, allowed_actions
from wing_parser.ui.texts import text
from wing_parser.ui.theme.widgets import Caption, set_style
from wing_parser.ui.workers import CallRunner


class DiscoveryPanel(QWidget):
    """Discover, the per-family inventory, and the unresolved banner."""

    discovered = Signal(object)     # the WatchList the walk returned
    rerun_requested = Signal()      # Rerun clicked, ahead of the retry

    def __init__(self, parent=None, *, transport=None, timeout=None) -> None:
        super().__init__(parent)
        self._transport = transport or live_controller.REAL
        self._timeout = timeout
        self._state = LiveState.DISCONNECTED
        self._host = ""
        self._has_unresolved = False

        self.discover_button = QPushButton(text("console.discover"))
        self.cancel_button = QPushButton(text("console.cancel"))
        self.cancel_button.setVisible(False)
        self.inventory_label = QLabel("")
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        self.banner_label = QLabel("")
        self.banner_label.setWordWrap(True)
        set_style(self.banner_label, "warn")
        self.rerun_button = QPushButton(text("console.rerun"))
        self.banner = QWidget()
        self.banner.setVisible(False)
        banner_row = QHBoxLayout(self.banner)
        banner_row.setContentsMargins(0, 0, 0, 0)
        banner_row.addWidget(self.banner_label, 1)
        banner_row.addWidget(self.rerun_button)

        top = QHBoxLayout()
        top.addWidget(Caption(text("console.discovery")))
        top.addWidget(self.discover_button)
        top.addWidget(self.cancel_button)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.inventory_label)
        layout.addWidget(self.banner)
        layout.addWidget(self.status_label)

        self._runner = CallRunner(self)
        self.discover_button.clicked.connect(self.discover_now)
        self.rerun_button.clicked.connect(self._rerun)
        self.cancel_button.clicked.connect(self.cancel)
        self.set_state(LiveState.DISCONNECTED)

    # -- what the owner drives -------------------------------------------

    def set_host(self, host: str) -> None:
        """The console address to walk -- the page reads it off ConnectBar."""
        self._host = host

    def set_state(self, state: LiveState) -> None:
        """Wear `state`: which of Discover/Rerun are live right now."""
        self._state = state
        self._refresh_buttons()

    def set_result(self, watch_list) -> None:
        """Render a `WatchList`: leaf total, inventory, unresolved banner."""
        total = len(watch_list.addresses)
        breakdown = ", ".join(
            f"{count} {family}" for family, count in watch_list.strips.items()
        )
        self.inventory_label.setText(
            text("console.inventory").format(total=total, breakdown=breakdown)
        )
        self._has_unresolved = bool(watch_list.unresolved)
        self.banner.setVisible(self._has_unresolved)
        if self._has_unresolved:
            self.banner_label.setText(text("console.unresolved_banner").format(
                families=", ".join(watch_list.unresolved), total=total))
        self._refresh_buttons()

    # -- discovering --------------------------------------------------------

    def discover_now(self) -> bool:
        """Start the walk off the GUI thread; False if it never began."""
        return self._start()

    def cancel(self) -> None:
        """Settle a running walk now; its late answer is discarded."""
        self._runner.cancel()
        if self._state is LiveState.WALKING:
            self.set_state(LiveState.CONNECTED)

    # -- internals --------------------------------------------------------

    def _rerun(self) -> None:
        self.rerun_requested.emit()
        self._start()

    def _start(self) -> bool:
        if not self._host:
            self.status_label.setText(text("console.no_address"))
            return False
        call = ButtonRunner(
            runner=self._runner, primary=self.discover_button,
            cancel=self.cancel_button, report=self.status_label.setText,
            running=text("console.discovering"),
            cancelled=text("console.walk_cancelled"),
            # ButtonRunner formats this with `seconds` alone
            # (call_button.py:85), so the host goes in first.
            timeout_text=text("console.walk_timeout").replace(
                "{host}", self._host),
            busy_text=text("console.walk_busy"),
            on_error=self._refused, on_timeout=self._fail, parent=self,
        )
        started = call.run(
            "walk", live_controller.discover, self._host, self._transport,
            on_success=self._arrived, timeout=self._timeout,
        )
        if started:
            self.set_state(LiveState.WALKING)
        return started

    def _refresh_buttons(self) -> None:
        actions = allowed_actions(self._state)
        self.discover_button.setEnabled("discover" in actions)
        self.rerun_button.setEnabled("rerun" in actions and self._has_unresolved)

    def _arrived(self, watch_list) -> None:
        self.set_state(LiveState.CONNECTED)
        self.set_result(watch_list)
        self.discovered.emit(watch_list)

    def _refused(self, exc) -> None:
        self.status_label.setText(text("console.walk_failed").format(
            host=self._host, error=exc))
        self._fail(exc)

    def _fail(self, exc) -> None:
        """Both failure paths end here: state -> error, no reset needed.

        `_refused` writes its own line first; a timeout arrives from
        `ButtonRunner.on_timeout` with its line already reported.
        """
        self.set_state(LiveState.ERROR)
