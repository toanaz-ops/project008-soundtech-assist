"""The Console page's inventory row: Discover, leaf counts, the banner.

Mirrors `live_connect_bar.py` in shape -- both now build on the shared
`live_call_panel.CallPanel` (runner, transport, timeout, state, Cancel,
the ButtonRunner dance) rather than repeating it; read that module's
docstring for why the split runs where it does. What this widget owns
that the bar does not is a *result*: `set_result` renders the leaf
total, the per-family inventory, and -- the load-bearing part of this
page (spec S6) -- the unresolved banner. It needs no `_fail` override of
its own (unlike `ConnectBar`, which has a `failed` signal to emit) --
the base's "state -> error" is the whole story here.

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

from functools import partial

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from wing_parser.ui import live_controller
from wing_parser.ui.live_call_panel import CallPanel
from wing_parser.ui.live_state import LiveState, allowed_actions
from wing_parser.ui.texts import text
from wing_parser.ui.theme.widgets import Caption, set_style


class DiscoveryPanel(CallPanel):
    """Discover, the per-family inventory, and the unresolved banner."""

    discovered = Signal(object)     # the WatchList the walk returned
    rerun_requested = Signal()      # Rerun clicked, ahead of the retry

    def __init__(self, parent=None, *, transport=None, timeout=None,
                 schema_cache=None) -> None:
        super().__init__(parent, transport=transport, timeout=timeout)
        self._host = ""
        self._has_unresolved = False
        #: D-41: shared with the page's SnapshotPanel when the page hands
        #: one in -- `None` (the default) walks exactly as before.
        self._schema_cache = schema_cache

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
        # The trailing stretch is what keeps the button beside its own
        # caption: without it the row's spare width goes INTO the button
        # (measured on the task-13 page grab -- a 226 px "Discover"
        # floating in the middle of the panel, half a screen from the
        # word it belongs to). It costs nothing when the panel is narrow.
        top.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.inventory_label)
        layout.addWidget(self.banner)
        layout.addWidget(self.status_label)

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
        super().set_state(state)
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

    def _cancel_fallback(self) -> LiveState | None:
        if self._state is LiveState.WALKING:
            return LiveState.CONNECTED
        return None

    # -- internals --------------------------------------------------------

    def _rerun(self) -> None:
        """C1 (D-41 fix round): force a fresh walk. `_schema_for` already
        refuses to CACHE an incomplete schema, so `rerun_button` (only
        enabled while `_has_unresolved`) should never find one waiting --
        this clears it anyway, defensively, and bumps the generation so a
        walk still in flight from an earlier click cannot land late."""
        if self._schema_cache is not None:
            self._schema_cache.clear()
        self.rerun_requested.emit()
        self._start()

    def _start(self) -> bool:
        if not self._host:
            self.status_label.setText(text("console.no_address"))
            return False
        return self._run_call(
            "walk",
            partial(live_controller.discover, cache=self._schema_cache),
            self._host, self._transport,
            primary=self.discover_button, cancel_button=self.cancel_button,
            status=self.status_label,
            running=text("console.discovering"),
            cancelled=text("console.walk_cancelled"),
            # ButtonRunner formats this with `seconds` alone
            # (call_button.py:85), so the host goes in first.
            timeout_text=text("console.walk_timeout").replace(
                "{host}", self._host),
            busy_text=text("console.walk_busy"),
            on_success=self._arrived, on_error=self._refused,
            busy_state=LiveState.WALKING,
        )

    def _refresh_buttons(self) -> None:
        actions = allowed_actions(self._state)
        self.discover_button.setEnabled("discover" in actions)
        self.rerun_button.setEnabled("rerun" in actions and self._has_unresolved)
        self.cancel_button.setEnabled("cancel" in actions)

    def _arrived(self, watch_list) -> None:
        self.set_state(LiveState.CONNECTED)
        self.set_result(watch_list)
        self.discovered.emit(watch_list)

    def _refused(self, exc) -> None:
        self.status_label.setText(text("console.walk_failed").format(
            host=self._host, error=exc))
        self._fail(exc)
