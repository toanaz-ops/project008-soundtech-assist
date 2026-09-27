"""The Scene cross-check step: a segment's `expects` against a scene,
from one of three sources (design spec §5, F6). Read-only. `chosen_scene`
is this widget's own record of the last Skip/Continue -- `import_finish.
finish_scene` reads it from here to render the preview; Save (I2) writes
exactly that rendered text back out, with no re-render of its own.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from wing_parser import WingScene
from wing_parser.showcontext.ingest import propose
from wing_parser.showcontext.view import channels_of
from wing_parser.ui.texts import text
from wing_parser.ui.theme import tokens

DOCTOR = "doctor"
FILE = "file"
PULL = "pull"


def _load_error_text(path: str, exc: Exception) -> str:
    """Name the file once -- parse_raw's own message may already start
    with the path (loader.py); a bare JSON syntax error does not. M8:
    the dialog can hand back a forward-slash path on Windows while the
    loader names the file with a native (backslash) Path string --
    `Path(path)` normalises before comparing so both spellings match."""
    message = str(exc)
    if str(Path(path)) in message:
        return text("import.scene.file_error_named").format(error=message)
    return text("import.scene.file_error").format(path=path, error=message)


class SceneStep(QWidget):
    continue_requested = Signal(object)
    skip_requested = Signal()

    def __init__(self, *, doctor_scene_provider: Callable[[], object | None]) -> None:
        super().__init__()
        self._doctor_scene_provider = doctor_scene_provider
        self._pulled_session = None
        self._file_scene = None
        self._result = None
        self.chosen_scene = None

        self.source_box = QComboBox()
        self.source_box.addItem(text("import.scene.source.doctor"), DOCTOR)
        self.source_box.addItem(text("import.scene.source.file"), FILE)
        self.source_box.addItem(text("import.scene.source.pull"), PULL)
        self._set_pull_enabled(False)
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
        self.skip_button.clicked.connect(self._skip)
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
        """Entered every time the step is shown: re-picks the default
        source (spec §5 -- Doctor, else whichever of Pull/File has one)."""
        self._result = result
        self._preselect_source()
        self._refresh_table()

    def set_pulled_session(self, session) -> None:
        """The Console page's last Pull this run (W4, in-memory only)."""
        self._pulled_session = session
        self._set_pull_enabled(session is not None)
        self._refresh_table()

    def _set_pull_enabled(self, enabled: bool) -> None:
        item = self.source_box.model().item(self.source_box.findData(PULL))
        if item is not None:
            item.setEnabled(enabled)

    def _preselect_source(self) -> None:
        if self._doctor_scene_provider() is not None:
            target = DOCTOR
        elif self._pulled_session is not None:
            target = PULL
        elif self._file_scene is not None:
            target = FILE
        else:
            target = DOCTOR
        self.source_box.setCurrentIndex(self.source_box.findData(target))

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
            self._file_scene = None   # do not keep a stale earlier success
            self.table.setRowCount(0)
            self.continue_button.setEnabled(False)
            self.status_label.setText(_load_error_text(path, exc))
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
        scene = None
        if self._result is None:
            pass
        elif self.source_box.currentData() == PULL and self._pulled_session is None:
            self.status_label.setText(text("import.scene.no_pull_yet"))
        else:
            scene = self._current_scene()
            if scene is None:
                self.status_label.setText(text("import.scene.no_scene"))
            else:
                self.status_label.setText("")
                self._populate_table(scene)
        self.continue_button.setEnabled(scene is not None)

    def _populate_table(self, scene) -> None:
        """One row per segment (spec §5), even one with no `expects`."""
        missing = propose.missing_for_segments(self._result, scene)
        segments = self._result.segments
        self.table.setRowCount(len(segments))
        warn = QColor(tokens.COLOURS["warn"])
        for r, built in enumerate(segments):
            gaps = missing.get(built.segment.id, ())
            found_kinds = tuple(k for k in built.segment.expects if k not in gaps)
            found = ", ".join(
                f"{channel.data.number} {channel.data.name}"
                for kind in found_kinds for channel in channels_of(scene, kind)
            )
            self.table.setItem(r, 0, QTableWidgetItem(built.segment.id))
            self.table.setItem(r, 1, QTableWidgetItem(", ".join(built.segment.expects)))
            self.table.setItem(r, 2, QTableWidgetItem(found))
            missing_item = QTableWidgetItem(", ".join(gaps))
            if gaps:
                missing_item.setForeground(warn)
            self.table.setItem(r, 3, missing_item)

    def _skip(self) -> None:
        self.chosen_scene = None
        self.skip_requested.emit()

    def _continue(self) -> None:
        self._refresh_table()   # the table must match what is about to be emitted
        self.chosen_scene = self._current_scene()
        self.continue_requested.emit(self.chosen_scene)
