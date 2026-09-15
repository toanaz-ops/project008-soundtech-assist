"""The Console page's top row: address, Connect/Disconnect, the lamp.

Layout, signals and one state->style table (design spec S6). Every
decision it shows belongs to somebody else: the handshake is
`live_controller.connect` over an injectable `Transport`, the legal
states are `live_state`, and remembering the address is the window's
job -- the bar only hands it `host()` and a `connected` signal. The
runner/state/cancel shell is `live_call_panel.CallPanel`, shared with
`DiscoveryPanel` -- read that module's docstring for why the split runs
where it does.

The lamp is a QLabel wearing an `azStyle`, coloured by four
`QLabel[azStyle="..."]` rules added to `resources/theme.qss` with this
bar: it carried `azStyle` rules for QPushButton only, so without them
the lamp matches no rule and stays the plain text colour while a test
reading the property still passes. `test_ui_console.py` checks the
generated sheet and the polished palette for exactly that reason.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
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

#: Which azStyle the lamp wears in each state -- spec S6's mapping, whole.
#: A table, not an if-chain, so a new LiveState fails a test rather than
#: falling through to a default nobody chose.
LAMP_STYLES: dict[LiveState, str] = {
    LiveState.DISCONNECTED: "faded",
    LiveState.CONNECTING: "warn",
    LiveState.WALKING: "warn",
    LiveState.PULLING: "warn",
    LiveState.CONNECTED: "ok",
    LiveState.WATCHING: "ok",
    LiveState.ERROR: "danger",
    LiveState.LOST: "danger",
}


class ConnectBar(CallPanel):
    """Address, Connect/Disconnect/Cancel, lamp, identity readout."""

    connected = Signal(object)      # the WingIdentity the desk answered
    failed = Signal(object)         # the exception, untranslated
    disconnected = Signal()

    def __init__(self, parent=None, *, transport=None, timeout=None) -> None:
        super().__init__(parent, transport=transport, timeout=timeout)

        self.address = QComboBox()
        self.address.setEditable(True)
        self.address.lineEdit().setPlaceholderText(
            text("console.address_hint"))
        self.connect_button = QPushButton(text("console.connect"))
        self.disconnect_button = QPushButton(text("console.disconnect"))
        self.cancel_button = QPushButton(text("console.cancel"))
        self.cancel_button.setVisible(False)
        self.lamp = QLabel(text("console.lamp"))
        self.identity_label = QLabel("")
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        row = QHBoxLayout()
        row.addWidget(Caption(text("console.address")))
        row.addWidget(self.address, 1)
        row.addWidget(self.connect_button)
        row.addWidget(self.disconnect_button)
        row.addWidget(self.cancel_button)
        row.addWidget(self.lamp)
        row.addWidget(self.identity_label)
        layout = QVBoxLayout(self)
        layout.addLayout(row)
        layout.addWidget(self.status_label)

        self.connect_button.clicked.connect(self.connect_now)
        self.disconnect_button.clicked.connect(self.disconnect_now)
        self.cancel_button.clicked.connect(self.cancel)
        self.set_state(LiveState.DISCONNECTED)

    # -- what the owner drives -------------------------------------------

    def host(self) -> str:
        """The address as typed or chosen, trimmed."""
        return self.address.currentText().strip()

    def set_consoles(self, consoles) -> None:
        """Offer the remembered addresses, most recent first."""
        self.address.clear()
        self.address.addItems(list(consoles))
        if self.address.count():
            self.address.setCurrentIndex(0)

    def set_state(self, state: LiveState) -> None:
        """Wear `state`: the lamp's colour and which buttons are live."""
        super().set_state(state)
        set_style(self.lamp, LAMP_STYLES[state])
        actions = allowed_actions(state)
        self.connect_button.setEnabled("connect" in actions)
        self.disconnect_button.setEnabled("disconnect" in actions)

    # -- connecting -------------------------------------------------------

    def connect_now(self) -> bool:
        """Start the handshake off the GUI thread; False if it never began."""
        host = self.host()
        if not host:
            self.status_label.setText(text("console.no_address"))
            return False
        return self._run_call(
            "connect", live_controller.connect, host, self._transport,
            primary=self.connect_button, cancel_button=self.cancel_button,
            status=self.status_label,
            running=text("console.connecting").format(host=host),
            cancelled=text("console.cancelled"),
            # ButtonRunner formats this with `seconds` alone
            # (call_button.py:85), so the host goes in first.
            timeout_text=text("console.timeout").replace("{host}", host),
            busy_text=text("console.busy"),
            on_success=self._arrived, on_error=self._refused,
            busy_state=LiveState.CONNECTING,
        )

    def disconnect_now(self) -> None:
        """Drop the desk: settle any call in flight, clear the readout.

        The cancel is not optional. A connect still on the wire would
        otherwise land after the bar said disconnected and drag it back
        to connected; `CallRunner.cancel` settles it now and discards
        the late answer (`workers.py:148-154`).
        """
        self._runner.cancel()
        self.identity_label.setText("")
        self.status_label.setText("")
        self.set_state(LiveState.DISCONNECTED)
        self.disconnected.emit()

    def _cancel_fallback(self) -> LiveState | None:
        if self._state is LiveState.CONNECTING:
            return LiveState.DISCONNECTED
        return None

    # -- internals --------------------------------------------------------

    def _arrived(self, identity) -> None:
        self.identity_label.setText(text("console.identity").format(
            name=identity.name, model=identity.model,
            firmware=identity.firmware,
        ))
        self.set_state(LiveState.CONNECTED)
        self.connected.emit(identity)

    def _refused(self, exc) -> None:
        self.status_label.setText(text("console.failed").format(
            host=self.host(), error=exc))
        self._fail(exc)

    def _fail(self, exc) -> None:
        """Both failure paths end here: red lamp, `failed` carrying `exc`.

        `_refused` writes its own line first; a timeout arrives from
        `ButtonRunner.on_timeout` with its line already reported.
        """
        super()._fail(exc)
        self.failed.emit(exc)
