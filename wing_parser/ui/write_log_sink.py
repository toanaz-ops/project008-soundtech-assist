"""Adapts settled writes and reverts into durable write-log lines (wave 5).

Subscribes to `ChangesPanel.sent` (every repair, at every apply level -- it
is emitted at the END of `record_sent`, after the badge, the ledger row and
the scene correction) and `SentLedger.reverted`. Everything it needs about
the desk and the show comes off the `SentWrite` itself, copied at submit
time (W13); nothing is read from the gate here, because `WriteGate.close()`
disarms while an in-flight write can still settle.

**A log failure never blocks anything (W3).** `_log` catches `Exception`,
never re-raises, and leaves a warning that the Log page and the Changes dock
show. Runs on the GUI thread (settle callbacks arrive there); a local file
is fine, a network-share knowledge dir would stall the UI -- accepted.

Names nothing under `wing_parser.net`: the result is read duck-typed through
`write_records.outcome`, as `write_records.py` itself does, so the AST
allow-list in `tests/test_ui_live_is_read_only.py` stays at one module.
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal

import wing_parser
from wing_parser import writelog
from wing_parser.ui import write_records
from wing_parser.ui.texts import text


def install(window, changes) -> "WriteLogSink":
    """Build the sink, publish it as `window.write_log_sink`, wire the dock
    and the Log page (if the window has built one yet)."""
    sink = WriteLogSink(window)
    sink.attach(changes)
    window.write_log_sink = sink
    sink.warning_changed.connect(changes.set_log_warning)
    page = getattr(window, "pages", {}).get("log")
    if page is not None and hasattr(page, "attach_sink"):
        page.attach_sink(sink)
    return sink


class WriteLogSink(QObject):
    warning_changed = Signal(str)       # "" never fires: a warning persists

    def __init__(self, window, directory: Path | None = None) -> None:
        super().__init__()
        self._window = window
        self._directory = directory
        self._findings: dict[str, str] = {}     # W14: path -> last repair finding
        self._labels: dict[str, str] = {}
        self.warning = ""

    def attach(self, changes) -> None:
        changes.sent.connect(self.on_sent)
        changes.ledger.reverted.connect(self.on_reverted)

    # -- the two sources -----------------------------------------------------

    def on_sent(self, patch, record) -> None:
        self._findings[record.path] = patch.because
        self._labels[record.path] = patch.label
        self._log("repair", record, patch.because, patch.label, patch.before)

    def on_reverted(self, record, _result) -> None:
        original = self._labels.get(record.path)
        label = f"Revert: {original}" if original else "Revert"
        self._log("revert", record, self._findings.get(record.path), label, None)

    # -- the one write, fenced (W3) ----------------------------------------

    def _log(self, kind, record, finding, label, file_before) -> None:
        try:
            writelog.append(
                self._entry(kind, record, finding, label, file_before),
                self._directory)
        except Exception as exc:        # noqa: BLE001 -- W3: ANY failure
            self.warning = text("log.warning.append_failed").format(
                folder=writelog.log_dir(self._directory), error=exc)
            self.warning_changed.emit(self.warning)

    def _entry(self, kind, record, finding, label, file_before):
        show = record.show
        if not show or not show.get("code"):
            raise ValueError("no show code was attached to this write")
        session = getattr(self._window, "session", None)
        identity = record.identity
        return writelog.LogEntry(
            v=writelog.ENTRY_VERSION, ts=writelog.now_ts(),
            show_code=show["code"], show=show.get("name") or None,
            venue=show.get("venue") or None,
            desk=asdict(identity) if is_dataclass(identity) else None,
            kind=kind, finding=finding, label=label,
            address=record.address, path=record.path,
            file_before=file_before, desk_before=record.desk_before,
            written=record.written, readback=record.result.readback,
            outcome=write_records.outcome(record.result).value,
            scene=Path(session.path).name if session is not None else None,
            app=wing_parser.__version__,
        )
