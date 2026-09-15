"""The Console page's top row: address, Connect/Disconnect, the lamp.

Layout, signals and one state->style table (design spec S6). Every
decision it shows belongs to somebody else: the handshake is
`live_controller.connect` over an injectable `Transport`, the legal
states are `live_state`, and remembering the address is the window's
job -- the bar only hands it `host()` and a `connected` signal.

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
    QWidget,
)

from wing_parser.ui import live_controller
from wing_parser.ui.call_button import ButtonRunner
from wing_parser.ui.live_state import LiveState, allowed_actions
from wing_parser.ui.texts import text
from wing_parser.ui.theme.widgets import Caption, set_style
from wing_parser.ui.workers import TIMEOUTS, CallRunner, CallTimedOut

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


class ConnectBar(QWidget):
    """Address, Connect/Disconnect/Cancel, lamp, identity readout."""

    connected = Signal(object)      # the WingIdentity the desk answered
    failed = Signal(object)         # the exception, untranslated
    disconnected = Signal()

    def __init__(self, parent=None, *, transport=None, timeout=None) -> None:
        super().__init__(parent)
        self._transport = transport or live_controller.REAL
        self._timeout = timeout
        self._seconds = 0
        self._timeout_line: str | None = None
        self._state = LiveState.DISCONNECTED

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

        self._runner = CallRunner(self)
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
        self._state = state
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
        self._seconds = (
            TIMEOUTS["connect"] if self._timeout is None else self._timeout
        )
        # ButtonRunner formats its timeout text with `seconds` alone
        # (call_button.py:75), so the host goes in before the call starts.
        template = text("console.timeout").replace("{host}", host)
        self._timeout_line = template.format(seconds=self._seconds)
        call = ButtonRunner(
            runner=self._runner, primary=self.connect_button,
            cancel=self.cancel_button, report=self._report,
            running=text("console.connecting").format(host=host),
            cancelled=text("console.cancelled"),
            timeout_text=template,
            busy_text=text("console.busy"),
            on_error=self._refused, parent=self,
        )
        started = call.run(
            "connect", live_controller.connect, host, self._transport,
            on_success=self._arrived, timeout=self._timeout,
        )
        if started:
            self.set_state(LiveState.CONNECTING)
        return started

    def disconnect_now(self) -> None:
        """Drop the desk: clear the readout, tell the owner."""
        self.identity_label.setText("")
        self.status_label.setText("")
        self.set_state(LiveState.DISCONNECTED)
        self.disconnected.emit()

    def cancel(self) -> None:
        """Settle a running connect now; its late answer is discarded."""
        self._runner.cancel()
        if self._state is LiveState.CONNECTING:
            self.set_state(LiveState.DISCONNECTED)

    # -- internals --------------------------------------------------------

    def _report(self, message: str) -> None:
        """Every line ButtonRunner writes lands here.

        The timeout is the one outcome it does not route to `on_error`:
        it reports the line and stops (`call_button.py:74-77`). So the
        line is recognised here -- against the exact string this call
        handed it -- and the bar ends red and emits `failed` like any
        other refused connect, instead of leaving an amber lamp under an
        error message. The `CallTimedOut` re-made here carries the kind
        and seconds `CallRunner` used (`workers.py:138`).
        """
        self.status_label.setText(message)
        if message and message == self._timeout_line:
            self._fail(CallTimedOut("connect", self._seconds))

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
        self.set_state(LiveState.ERROR)
        self.failed.emit(exc)
