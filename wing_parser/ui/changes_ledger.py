"""Everything written to the desk this session, and the way back (F7).

One row per parameter: address, the desk-live value captured BEFORE the
write, the value written, the read-back result. **Its rows survive an
Undo**, which is a file-side action -- a desk change the UI cannot revert
is worse than a longer panel.

Revert writes that row's captured desk-before value through the CURRENT
apply level: Immediate at once, Delayed and Manual via the countdown.
Revert all walks the rows in REVERSE -- last written, first undone -- and
is still one parameter per transmission (F1): the next starts only after
the previous read-back returns, because `RevertQueue.next()` is called from
the previous one's terminal callback and every write goes through the
gate's single `WriteQueue` underneath that (W10, §7.2).

**Stop ends the run between parameters**; the one already on the wire
completes, because nothing can un-send a packet. In Delayed the way out is
the countdown's own Cancel (W12, W15) -- a Stop button behind a modal
dialog is not reachable at all.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget,
)

from wing_parser.ui import write_router
from wing_parser.ui.apply_level import RevertQueue
from wing_parser.ui.changes_send import badge_text
from wing_parser.ui.texts import text


class LedgerRow(QWidget):
    revert_requested = Signal(object)

    def __init__(self, record, parent=None) -> None:
        super().__init__(parent)
        self.record = record
        self.label = QLabel(text("console.write.ledger_row").format(
            address=record.address, desk=record.desk_before,
            after=record.written))
        self.result_label = QLabel(badge_text(record))
        self.revert_button = QPushButton(text("console.write.revert"))
        self.revert_button.clicked.connect(
            lambda: self.revert_requested.emit(self.record))
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label, 1)
        layout.addWidget(self.result_label)
        layout.addWidget(self.revert_button)


class SentLedger(QWidget):
    run_started = Signal()
    run_finished = Signal()
    reverted = Signal(object, object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._records: list = []
        self._gate = None
        self._window = None
        self._queue: RevertQueue | None = None
        self.list = QListWidget()
        self.progress_label = QLabel("")
        self.revert_all_button = QPushButton(text("console.write.revert_all"))
        self.stop_button = QPushButton(text("console.write.revert_stop"))
        self.stop_button.setEnabled(False)
        self.revert_all_button.clicked.connect(self.revert_all)
        self.stop_button.clicked.connect(self.stop)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(text("console.write.sent_heading")))
        layout.addWidget(self.list)
        layout.addWidget(self.progress_label)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.stop_button)
        buttons.addWidget(self.revert_all_button)
        layout.addLayout(buttons)

    def attach(self, gate, window) -> None:
        self._gate, self._window = gate, window

    # -- the rows ----------------------------------------------------------

    def add(self, record) -> None:
        self._records.append(record)
        row = LedgerRow(record)
        row.revert_requested.connect(self._revert_one)
        item = QListWidgetItem()
        item.setSizeHint(row.sizeHint())
        self.list.addItem(item)
        self.list.setItemWidget(item, row)

    def records(self) -> tuple:
        return tuple(self._records)

    def row_widget(self, index: int) -> LedgerRow:
        return self.list.itemWidget(self.list.item(index))

    # -- reverting -----------------------------------------------------------

    def _revert_one(self, record) -> None:
        write_router.route_revert(
            self._gate, record, getattr(self._window, "_apply_delay", 5),
            self.window(), transport=self._gate.transport,
            on_sent=self._reverted)

    def revert_all(self) -> None:
        """F7: reverse order, sequential, one parameter per transmission."""
        if self._queue is not None:
            return
        self._queue = RevertQueue(self._records)
        self.stop_button.setEnabled(True)
        self.run_started.emit()                      # W14
        self._next()

    def stop(self) -> None:
        """Between parameters. The one already on the wire completes."""
        if self._queue is None:
            return
        self._queue.stop()
        done, total = self._queue.progress
        self.progress_label.setText(text("console.write.revert_stopped").format(
            done=done, total=total))
        self._end_run()

    def _next(self) -> None:
        record = self._queue.next() if self._queue is not None else None
        if record is None:
            if self._queue is not None:
                self._end_run()
            return
        done, total = self._queue.progress
        self.progress_label.setText(text("console.write.reverting").format(
            done=done, total=total, address=record.address))
        write_router.route_revert(
            self._gate, record, getattr(self._window, "_apply_delay", 5),
            self.window(), transport=self._gate.transport,
            on_sent=self._step_done,
            on_error=lambda _exc: self._step_done(None, None),
            on_cancelled=self.stop)                  # W12: Cancel stops the run

    def _step_done(self, _patch, record) -> None:
        if record is not None:
            self._reverted(_patch, record)
        self._next()

    def _reverted(self, patch, record) -> None:
        """W13: the scene goes back too, so the finding reappears."""
        if patch is not None:
            write_router.apply_revert(self._window, record)
        self.reverted.emit(record, record.result)

    def _end_run(self) -> None:
        self._queue = None
        self.stop_button.setEnabled(False)
        self.run_finished.emit()                     # W14
