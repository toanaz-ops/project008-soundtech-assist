"""The ruled chrome around one model call: button, Cancel, status line.

Task C (wave 1b): a model call must disable its primary button while
running, offer a visible Cancel only while running, and report
running / timeout / cancelled / failure on a status label. This class
is that dance, once, so the three call sites stay thin.
"""

from __future__ import annotations

from PySide6.QtCore import QObject

from wing_parser.ui.workers import CallTimedOut


class ButtonRunner(QObject):
    """Wire one CallRunner call to a primary button + Cancel + status.

    `on_error` is deliberately not told about a timeout: a `CallTimedOut`
    has its own ruled sentence and no provider message to show, so it is
    reported and stops there. A caller whose STATE must change on one --
    `live_connect_bar`, whose lamp would otherwise sit amber under an
    error line -- passes `on_timeout` as well and receives the
    `CallTimedOut` itself, after the line is reported. Optional: the
    three model-call sites pass neither and are unaffected.
    """

    def __init__(self, *, runner, primary, cancel=None, report=None,
                 running="", cancelled="", timeout_text="", busy_text="",
                 on_error=None, on_timeout=None, parent=None) -> None:
        super().__init__(parent)
        self._runner = runner
        self._primary = primary
        self._cancel = cancel
        self._report = report or (lambda message: None)
        self._running = running
        self._cancelled_text = cancelled
        self._timeout_text = timeout_text
        self._busy_text = busy_text
        self._on_error = on_error
        self._on_timeout = on_timeout
        self._success = None

    def run(self, kind, function, *args, on_success, timeout=None) -> bool:
        """Start the call; False (with the busy message shown) if busy."""
        started = self._runner.start(
            kind, function, *args,
            on_success=self._delivered,
            on_failure=self._failed,
            on_cancel=self._cancelled,
            timeout=timeout,
        )
        if not started:
            if self._busy_text:
                self._report(self._busy_text)
            return False
        self._success = on_success
        self._primary.setEnabled(False)
        if self._cancel is not None:
            self._cancel.setVisible(True)
        if self._running:
            self._report(self._running)
        return True

    def cancel(self) -> None:
        self._runner.cancel()

    # -- internals ------------------------------------------------------

    def _restore(self) -> None:
        self._primary.setEnabled(True)
        if self._cancel is not None:
            self._cancel.setVisible(False)

    def _delivered(self, result) -> None:
        self._restore()
        self._report("")
        callback, self._success = self._success, None
        if callback is not None:
            callback(result)

    def _failed(self, exc) -> None:
        self._restore()
        if isinstance(exc, CallTimedOut):
            self._report(self._timeout_text.format(seconds=exc.seconds))
            if self._on_timeout is not None:
                self._on_timeout(exc)
        elif self._on_error is not None:
            self._on_error(exc)

    def _cancelled(self) -> None:
        self._restore()
        if self._cancelled_text:
            self._report(self._cancelled_text)
