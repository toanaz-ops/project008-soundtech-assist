"""The Scene cross-check step: what a segment's expects: needs against a
scene, from one of three sources (design spec §5, F6). Read-only --
nothing here writes to a live console. Skip leaves the emitted file
exactly as it is today (no proposals); Continue passes the chosen scene
through to import_steps.finish_scene, which threads it into
ic.preview_text exactly as the CLI's --scene does.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from wing_parser import WingScene
from wing_parser.showcontext.ingest import propose
from wing_parser.ui.texts import text
from wing_parser.ui.theme import tokens

DOCTOR = "doctor"
FILE = "file"
PULL = "pull"


class SceneStep(QWidget):
    continue_requested = Signal(object)
    skip_requested = Signal()

    def __init__(self, *, doctor_scene_provider: Callable[[], object | None]) -> None:
        super().__init__()
        self._doctor_scene_provider = doctor_scene_provider
        self._pulled_session = None
        self._file_scene = None
        self._result = None

        self.source_box = QComboBox()
        self.source_box.addItem(text("import.scene.source.doctor"), DOCTOR)
        self.source_box.addItem(text("import.scene.source.file"), FILE)
        self.source_box.addItem(text("import.scene.source.pull"), PULL)
        self.source_box.currentIndexChanged.connect(self._source_changed)

        self.open_file_button = QPushButton(text("import.scene.open_file"))
        self.open_file_button.clicked.connect(self._open_file)
        self.open_file_button.setVisible(False)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([
            text("import.scene.col.segment"), text("import.scene.col.needed"),
            text("import.scene.col.found"), text("import.scene.col.missing"),
        ])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.skip_button = QPushButton(text("import.scene.skip"))
        self.skip_button.clicked.connect(lambda: self.skip_requested.emit())
        self.continue_button = QPushButton(text("import.scene.continue"))
        self.continue_button.clicked.connect(self._continue)

        top = QHBoxLayout()
        top.addWidget(QLabel(text("import.scene.source")))
        top.addWidget(self.source_box)
        top.addWidget(self.open_file_button)

        buttons = QHBoxLayout()
        buttons.addWidget(self.skip_button)
        buttons.addWidget(self.continue_button)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, 1)
        layout.addLayout(buttons)
        self._source_changed()

    def set_result(self, result) -> None:
        self._result = result
        self._refresh_table()

    def set_pulled_session(self, session) -> None:
        """The Console page's last successful Pull this app run (W4:
        in-memory only). Read only when the 'Console's last Pull' source
        is actually selected -- see _refresh_table's own message when
        it is selected but nothing has been pulled yet."""
        self._pulled_session = session
        self._refresh_table()

    def _source_changed(self) -> None:
        self.open_file_button.setVisible(self.source_box.currentData() == FILE)
        self._refresh_table()

    def _open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, text("import.scene.open_file"), "", text("menu.scene_filter"))
        if not path:
            return
        try:
            self._file_scene = WingScene.load(path)
        except (OSError, ValueError) as exc:
            self.status_label.setText(
                text("import.scene.file_error").format(path=path, error=exc))
            return
        self._refresh_table()

    def _current_scene(self):
        source = self.source_box.currentData()
        if source == DOCTOR:
            return self._doctor_scene_provider()
        if source == FILE:
            return self._file_scene
        if source == PULL:
            return self._pulled_session.scene if self._pulled_session else None
        return None

    def _refresh_table(self) -> None:
        self.table.setRowCount(0)
        if self._result is None:
            return
        if self.source_box.currentData() == PULL and self._pulled_session is None:
            self.status_label.setText(text("import.scene.no_pull_yet"))
            return
        scene = self._current_scene()
        if scene is None:
            self.status_label.setText(text("import.scene.no_scene"))
            return
        self.status_label.setText("")
        missing = propose.missing_for_segments(self._result, scene)
        rows = [built for built in self._result.segments if built.segment.expects]
        self.table.setRowCount(len(rows))
        warn = QColor(tokens.COLOURS["warn"])
        for r, built in enumerate(rows):
            gaps = missing.get(built.segment.id, ())
            found = tuple(kind for kind in built.segment.expects if kind not in gaps)
            self.table.setItem(r, 0, QTableWidgetItem(built.segment.id))
            self.table.setItem(r, 1, QTableWidgetItem(", ".join(built.segment.expects)))
            self.table.setItem(r, 2, QTableWidgetItem(", ".join(found)))
            missing_item = QTableWidgetItem(", ".join(gaps))
            if gaps:
                missing_item.setForeground(warn)
            self.table.setItem(r, 3, missing_item)

    def _continue(self) -> None:
        self.continue_requested.emit(self._current_scene())
