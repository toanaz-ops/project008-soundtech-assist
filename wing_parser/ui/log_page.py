"""The Log page (wave 5): what was written to a desk, per show.

Read-only (W5): no revert from a past session, because the desk's present
state is unknown. Left, one row per show code, newest first; right, that
show's writes in time order, with the same columns as the HTML report.
**Export report...** renders `writelog.render_html` in the UI language.

The save dialog and the folder opener are module-level functions so a test
can replace them (`choose_save_path`, `open_folder`) without a real dialog.
The page re-reads the folder every time it is shown and on **Refresh** --
a button, not F5, which is bound app-wide to reanalyse.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QStandardItemModel
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QLabel, QListWidget, QPushButton, QSplitter,
    QTableView, QVBoxLayout, QWidget,
)

from wing_parser import writelog
from wing_parser.ui import log_rows
from wing_parser.ui.elide import MonoDelegate
from wing_parser.ui.log_rows import COLUMNS, MONO, NUMERIC
from wing_parser.ui.texts import text
from wing_parser.ui.theme.widgets import Caption


def choose_save_path(parent, title, suggested, file_filter) -> str:
    name, _ = QFileDialog.getSaveFileName(parent, title, suggested, file_filter)
    return name


def open_folder(path) -> None:
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))


class LogPage(QWidget):
    def __init__(self, directory: Path | None = None) -> None:
        super().__init__()
        self._directory = directory
        self._sink = None
        self._sink_warning = ""
        self._skip_warning = ""

        self.shows_list = QListWidget()
        self.entries_model = QStandardItemModel(0, len(COLUMNS), self)
        self.entries_table = QTableView()
        self.entries_table.setModel(self.entries_model)
        self.entries_table.setItemDelegate(
            MonoDelegate(numeric_columns=NUMERIC, mono_columns=MONO))
        self.entries_table.verticalHeader().setVisible(False)
        self.entries_table.setEditTriggers(QTableView.EditTrigger.NoEditTriggers)
        self.export_button = QPushButton(text("log.export"))
        self.folder_button = QPushButton(text("log.open_folder"))
        self.refresh_button = QPushButton(text("log.refresh"))
        self.warning_label = QLabel("")
        self.warning_label.setWordWrap(True)
        self.warning_label.setVisible(False)
        self.empty_label = QLabel(text("log.empty"))
        self.empty_label.setWordWrap(True)
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        for button in (self.refresh_button, self.folder_button, self.export_button):
            buttons.addWidget(button)
        left, right = QVBoxLayout(), QVBoxLayout()
        left.addWidget(Caption(text("log.shows_heading")))
        left.addWidget(self.shows_list)
        right.addWidget(Caption(text("log.entries_heading")))
        right.addWidget(self.entries_table)
        splitter = QSplitter()
        for side, stretch in ((left, 1), (right, 3)):
            holder = QWidget()
            holder.setLayout(side)
            splitter.addWidget(holder)
            splitter.setStretchFactor(splitter.count() - 1, stretch)
        layout = QVBoxLayout(self)
        layout.addLayout(buttons)
        layout.addWidget(self.warning_label)
        layout.addWidget(self.empty_label)
        layout.addWidget(splitter, stretch=1)
        layout.addWidget(self.status_label)
        self.entries_model.setHorizontalHeaderLabels(
            [text(f"log.report.col.{key}") for key in COLUMNS])

        self.refresh_button.clicked.connect(self.refresh)
        self.folder_button.clicked.connect(self.open_log_folder)
        self.export_button.clicked.connect(self.export_report)
        self.shows_list.currentRowChanged.connect(self._row_changed)
        self.export_button.setEnabled(False)

    # -- the sink's failure warning (W3) ------------------------------------

    def attach_sink(self, sink) -> None:
        self._sink = sink
        sink.warning_changed.connect(self._set_sink_warning)
        self._set_sink_warning(sink.warning)

    def _set_sink_warning(self, message: str) -> None:
        self._sink_warning = message
        self._show_warnings()

    def _show_warnings(self) -> None:
        joined = " ".join(m for m in (self._sink_warning, self._skip_warning) if m)
        self.warning_label.setText(joined)
        self.warning_label.setVisible(bool(joined))

    # -- reading the folder ---------------------------------------------------

    def showEvent(self, event) -> None:
        super().showEvent(event)
        self.refresh()

    def current_code(self) -> str | None:
        item = self.shows_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def refresh(self) -> None:
        keep = self.current_code()
        shows = writelog.list_shows(self._directory)
        self.shows_list.blockSignals(True)
        self.shows_list.clear()
        for show in shows:
            self.shows_list.addItem(log_rows.show_item(show))
        self.shows_list.blockSignals(False)
        self.empty_label.setVisible(not shows)
        for row, show in enumerate(shows):
            if show.code == keep:
                self.shows_list.setCurrentRow(row)
                break
        else:
            self.shows_list.setCurrentRow(-1)
        self._load(self.current_code())

    def _row_changed(self, _row: int) -> None:
        self._load(self.current_code())

    def _load(self, code: str | None) -> None:
        self.entries_model.removeRows(0, self.entries_model.rowCount())
        self.export_button.setEnabled(code is not None)
        self._skip_warning = ""
        if code is not None:
            entries, skipped = writelog.read_show(code, self._directory)
            for entry in sorted(entries, key=lambda e: e.ts):
                self.entries_model.appendRow(log_rows.entry_row(entry))
            if skipped:
                self._skip_warning = text("log.warning.skipped").format(
                    count=skipped, code=code)
        self._show_warnings()

    # -- the buttons -----------------------------------------------------------

    def open_log_folder(self) -> None:
        folder = writelog.log_dir(self._directory)
        folder.mkdir(parents=True, exist_ok=True)
        open_folder(folder)

    def export_report(self) -> None:
        code = self.current_code()
        if code is None:
            return
        target = choose_save_path(self, text("log.save_title"),
                                  f"{code}-report.html", text("log.save_filter"))
        if not target:
            return
        summary = next((s for s in writelog.list_shows(self._directory)
                        if s.code == code), None)
        entries, _ = writelog.read_show(code, self._directory)
        if summary is None:
            return
        labels = {key: text(key) for key in writelog.REPORT_LABEL_KEYS}
        html = writelog.render_html(summary, entries, labels, writelog.now_ts())
        try:
            Path(target).write_text(html, encoding="utf-8")
        except OSError as exc:
            self.status_label.setText(text("log.export_failed").format(error=exc))
            return
        self.status_label.setText(text("log.export_done").format(path=target))
