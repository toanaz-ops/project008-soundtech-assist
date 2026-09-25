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

**A row the desk never described cannot be put back**: `desk_before is
None` (a pre-flight read that failed or went unanswered) disables that
row's button and leaves it out of a run, counted and reported.

**Stop ends the run between parameters**; the one already on the wire
completes, because nothing can un-send a packet. An error ends it too
(`_step_failed`) rather than advancing into it. In Delayed the way out is
the countdown's own Cancel (W12, W15) -- a Stop button behind a modal
dialog is not reachable at all.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget,
)

from wing_parser.ui import write_apply, write_router
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
        if record.desk_before is None:          # a failed/unanswered pre-flight
            self.revert_button.setEnabled(False)
            self.revert_button.setToolTip(text("console.write.revert_unknown"))
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
        self._skipped = 0
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

    def _route(self, record, **callbacks) -> None:
        write_router.route_revert(
            self._gate, record, getattr(self._window, "_apply_delay", 5),
            self.window(), transport=self._gate.transport, **callbacks)

    def _revert_one(self, record) -> None:
        self._route(record, on_sent=self._reverted)

    def revert_all(self) -> None:
        """F7: reverse order, sequential, one parameter per transmission.

        A row the desk never described (`desk_before is None`) is left OUT
        of the run and counted: `route_revert` refuses one outright."""
        if self._queue is not None:
            return
        can = [r for r in self._records if r.desk_before is not None]
        self._skipped = len(self._records) - len(can)
        self._queue = RevertQueue(can)
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
        self._route(record, on_sent=self._step_done, on_error=self._step_failed,
                    on_cancelled=self.stop)           # W12: Cancel stops the run

    def _step_done(self, _patch, record) -> None:
        if record is not None:
            self._reverted(_patch, record)
        self._next()

    def _step_failed(self, exc) -> None:
        """A `GateClosed` (or anything else) ENDS the run, it does not
        advance it: the connection is the same one every remaining row
        needs, so carrying on stacks one modal countdown per row against a
        desk that is already gone. `run_finished` is emitted exactly once,
        by `_end_run`, and the line names what stopped it."""
        if self._queue is None:
            return
        self._queue.stop()
        self.progress_label.setText(
            text("console.write.revert_failed").format(error=exc))
        self._end_run()

    def _reverted(self, _patch, record) -> None:
        """W13: the scene goes back too, so the finding reappears.

        `_patch` (the internal revert `Patch` `route_revert` built) is
        unused: `on_sent` fires only on a COMPLETED write, never with a
        `None` patch, and the error path is `_step_failed`, which never
        comes through here at all."""
        write_apply.apply_revert(self._window, record)
        self.reverted.emit(record, record.result)

    def _end_run(self) -> None:
        if self._skipped:
            skipped_line = text("console.write.revert_skipped").format(
                skipped=self._skipped,
                plural="" if self._skipped == 1 else "s")
            self.progress_label.setText(
                " ".join((self.progress_label.text(), skipped_line)).strip())
        self._queue = None
        self.stop_button.setEnabled(False)
        self.run_finished.emit()                     # W14
