"""The Console page's snapshot row: Pull, the two guards, Export.

The third `live_call_panel.CallPanel` subclass, after `ConnectBar` and
`DiscoveryPanel` -- read that module for what the shared shell owns.
What this one adds is the only thing on the page producing a `Session`:

* **Both of `_load()`'s guards, shown.** `EmptyReadError` reports the
  ported CLI sentence and **no session leaves this widget** -- the whole
  reason that error exists (`live_controller.py:44-64`). A partial read
  is usable, so it loads, and `incomplete_report` becomes a *persistent*
  banner: a scene that is not the whole desk must never look complete.
* **Export writes `Session.save_as`** (D3) -- the *patched* document
  (`session.py:92-96` -> `_document()` at `:43-44`). The pull-time JSON
  is kept beside it as `original`, Diff's "as pulled" baseline, and is
  deliberately not what Export writes: that would drop every repair.
* **No `set_session`.** `MainWindow._refresh` fans the session out to
  every page defining one (`main_window.py:174-176`); this panel
  produces sessions rather than consuming them.

The window is reached by signal only (`live_wiring.py`) -- this module
must not import `main_window` -- so those three signals are the contract.
"""

from __future__ import annotations

import re

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from wing_parser.ui import live_controller
from wing_parser.ui.live_call_panel import CallPanel
from wing_parser.ui.live_state import LiveState, allowed_actions
from wing_parser.ui.texts import text
from wing_parser.ui.theme.widgets import Caption, set_style

#: Everything a proposed filename may NOT keep: `suggested_name` takes
#: its stem from `WingIdentity.name`, so the ordinary desk name
#: "FOH/Monitors" would reach the Save dialog as a *directory* that does
#: not exist. Task 4's deferred minor, closed where the path is proposed.
_UNSAFE = re.compile(r"[^\w.\-]")


def export_name(path) -> str:
    """The pulled scene's suggested filename, safe to hand a file dialog."""
    return _UNSAFE.sub("_", str(path))


class SnapshotPanel(CallPanel):
    """Pull, the empty/partial guards, the scene-loaded line, Export."""

    session_pulled = Signal(object)     # the Session a clean pull built
    exported = Signal(str)              # the path Export actually wrote
    doctor_requested = Signal()         # Open Doctor clicked (D16)

    def __init__(self, parent=None, *, transport=None, timeout=None) -> None:
        super().__init__(parent, transport=transport, timeout=timeout)
        self._host = ""
        self._identity = None
        self._session = None
        #: The pull-time JSON text (D3): Diff's baseline, never Export's.
        self.original = ""

        self.pull_button = QPushButton(text("console.pull"))
        self.cancel_button = QPushButton(text("console.cancel"))
        self.cancel_button.setVisible(False)
        self.doctor_button = QPushButton(text("console.open_doctor"))
        self.export_button = QPushButton(text("console.export"))
        self.loaded_label = QLabel("")
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        # One label, not DiscoveryPanel's label-plus-Rerun row: a
        # partial pull already loaded, so there is no action to offer.
        self.banner = QLabel("")
        self.banner.setWordWrap(True)
        self.banner.setVisible(False)
        set_style(self.banner, "warn")

        top = QHBoxLayout()
        top.addWidget(Caption(text("console.snapshot")))
        for button in (self.pull_button, self.cancel_button,
                       self.doctor_button, self.export_button):
            top.addWidget(button)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.banner)
        layout.addWidget(self.loaded_label)
        layout.addWidget(self.status_label)

        self.pull_button.clicked.connect(self.pull_now)
        self.cancel_button.clicked.connect(self.cancel)
        self.doctor_button.clicked.connect(self.doctor_requested)
        self.export_button.clicked.connect(self.export_now)
        self.set_state(LiveState.DISCONNECTED)

    # -- what the owner drives -------------------------------------------

    def set_host(self, host: str) -> None:
        """The console address to pull -- the page reads it off ConnectBar."""
        self._host = host

    def set_identity(self, identity) -> None:
        """The desk that answered, or `None`: the suggested filename's stem."""
        self._identity = identity

    def set_state(self, state: LiveState) -> None:
        """Wear `state`: which of Pull/Export/Open Doctor are live.

        Both scene-bound buttons also need a scene: `allowed_actions`
        answers about the *desk*, not about what has been pulled.
        """
        super().set_state(state)
        loaded = self._session is not None
        self.pull_button.setEnabled("pull" in allowed_actions(state))
        self.export_button.setEnabled(
            "export" in allowed_actions(state) and loaded)
        self.doctor_button.setEnabled(loaded)

    # -- pulling ----------------------------------------------------------

    def pull_now(self) -> bool:
        """Read the whole desk off the GUI thread; False if it never began."""
        if not self._host:
            self.status_label.setText(text("console.no_address"))
            return False
        return self._run_call(
            "snapshot", live_controller.pull, self._host, self._transport,
            primary=self.pull_button, cancel_button=self.cancel_button,
            status=self.status_label,
            running=text("console.pulling").format(host=self._host),
            cancelled=text("console.pull_cancelled"),
            # ButtonRunner formats this with `seconds` alone
            # (call_button.py:85), so the host goes in first.
            timeout_text=text("console.pull_timeout").replace(
                "{host}", self._host),
            busy_text=text("console.pull_busy"),
            on_success=self._arrived, on_error=self._refused,
            busy_state=LiveState.PULLING,
        )

    def export_now(self) -> bool:
        """Write the patched scene where he chooses; False if nothing was."""
        if self._session is None:
            return False
        name, _ = QFileDialog.getSaveFileName(
            self, text("console.export_title"),
            export_name(self._session.path), text("menu.scene_filter"),
        )
        if not name:
            return False
        try:
            self._session.save_as(name)
        except OSError as exc:
            # The session is untouched and still exportable elsewhere.
            self.status_label.setText(
                text("console.export_failed").format(file=name, error=exc))
            return False
        self.status_label.setText(text("console.exported").format(file=name))
        self.exported.emit(name)
        return True

    def _cancel_fallback(self) -> LiveState | None:
        if self._state is LiveState.PULLING:
            return LiveState.CONNECTED
        return None

    # -- internals --------------------------------------------------------

    def _arrived(self, result) -> None:
        report = live_controller.incomplete_report(result)
        self.banner.setVisible(report is not None)
        if report is not None:
            self.banner.setText(
                text("console.incomplete_banner").format(report=report))
        session, original = live_controller.session_from_snapshot(
            result, self._identity)
        self._session = session
        self.original = original
        self.loaded_label.setText(text("console.scene_loaded").format(
            findings=len(session.findings())))
        self.set_state(LiveState.CONNECTED)
        self.session_pulled.emit(session)

    def _refused(self, exc) -> None:
        if isinstance(exc, live_controller.EmptyReadError):
            # Its own sentence, ported whole from `cli/commands.py:47-62`
            # -- it already names the host and both counts.
            self.status_label.setText(str(exc))
        else:
            self.status_label.setText(text("console.pull_failed").format(
                host=self._host, error=exc))
        self._fail(exc)
