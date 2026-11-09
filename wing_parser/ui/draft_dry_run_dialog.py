"""Tools > Draft rule dry-run (wave 8): what would this draft change?

Read-only. Runs a draft rule file over chosen scenes, synchronously (no
worker thread, D-58), and lists the findings it would add or remove. It
never writes principles.yaml, a scene or the desk.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QHBoxLayout, QLabel,
    QListWidget, QPushButton, QVBoxLayout,
)

from wing_parser import config
from wing_parser.advisory import draft_dry_run as dd
from wing_parser.ui import draft_dry_run_tables as tables
from wing_parser.ui.texts import text

NEWLINE = chr(10)


def default_scenes(window) -> list[str]:
    """The open scene, then recent `.snap` files that still exist."""
    session = getattr(window, "session", None)
    candidates = [str(session.path)] if session is not None else []
    candidates += [e for e in getattr(window, "_recent", [])
                   if str(e).lower().endswith(".snap")]
    found: list[str] = []
    for entry in candidates:
        if Path(entry).is_file() and entry not in found:
            found.append(entry)
    return found


class DraftDryRunDialog(QDialog):
    def __init__(self, parent=None, scenes=(), directory=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(text("dryrun.title"))
        self.resize(980, 640)
        self._directory = directory
        self._folder = config.knowledge_dir(directory) / dd.DRAFTS_DIR
        self._load = None
        self._results: list = []

        self.guidance = QLabel(
            text("dryrun.no_drafts").format(path=self._folder))
        self.guidance.setWordWrap(True)
        self.open_folder = QPushButton(text("dryrun.open_folder"))
        self.open_folder.clicked.connect(self._open_folder)
        self.combo = QComboBox()
        self.browse = QPushButton(text("dryrun.browse"))
        self.browse.clicked.connect(self._browse)
        self.status = QLabel()
        self.status.setWordWrap(True)
        self.scene_list = QListWidget()
        self.scene_list.setSelectionMode(
            QListWidget.SelectionMode.ExtendedSelection)
        self.scene_list.setMaximumHeight(110)
        self.add_btn = QPushButton(text("dryrun.add"))
        self.add_btn.clicked.connect(self._add)
        self.remove_btn = QPushButton(text("dryrun.remove"))
        self.remove_btn.clicked.connect(self._remove)
        self.run_btn = QPushButton(text("dryrun.run"))
        self.run_btn.clicked.connect(self.run)
        self.no_change = QLabel(text("dryrun.no_change"))
        self.no_change.setVisible(False)
        self.summary, self.summary_model = tables.make_table(
            tables.SUMMARY_COLS, {1, 2, 3, 4}, {0}, single=True)
        self.detail, self.detail_model = tables.make_table(
            tables.DETAIL_COLS, set(), {0, 2, 3})

        row = QHBoxLayout()
        row.addWidget(QLabel(text("dryrun.draft_label")))
        row.addWidget(self.combo, 1)
        row.addWidget(self.browse)
        side = QVBoxLayout()
        for w in (self.add_btn, self.remove_btn, self.run_btn):
            side.addWidget(w)
        side.addStretch()
        scenes_row = QHBoxLayout()
        scenes_row.addWidget(self.scene_list, 1)
        scenes_row.addLayout(side)
        layout = QVBoxLayout(self)
        layout.addWidget(self.guidance)
        layout.addWidget(self.open_folder, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(row)
        layout.addWidget(self.status)
        layout.addWidget(QLabel(text("dryrun.scenes_heading")))
        layout.addLayout(scenes_row)
        layout.addWidget(self.no_change)
        layout.addWidget(self.summary, 2)
        layout.addWidget(self.detail, 3)

        for scene in scenes:
            self._add_scene(str(scene))
        drafts = dd.list_drafts(directory)
        for path in drafts:
            self.combo.addItem(path.name, str(path))
        self.guidance.setVisible(not drafts)
        self.open_folder.setVisible(not drafts)
        self.combo.currentIndexChanged.connect(self._draft_changed)
        self.summary.selectionModel().selectionChanged.connect(self._filter)
        self._draft_changed()

    def _add_scene(self, path: str) -> None:
        listed = [self.scene_list.item(i).text()
                  for i in range(self.scene_list.count())]
        if path not in listed:
            self.scene_list.addItem(path)

    def _draft_changed(self, *_args) -> None:
        data = self.combo.currentData()
        load = dd.load_draft(Path(data), self._directory) if data else None
        self._load = load
        if load is None:
            self.status.setText("")
        elif load.error:
            self.status.setText(load.error)
        else:
            lines = [text("dryrun.rules").format(count=len(load.rules))]
            lines += ([text("dryrun.ready")] if load.promotable else
                      [text("dryrun.not_ready"), *load.promote_blockers])
            self.status.setText(NEWLINE.join(lines))
        self._update_run()

    def _update_run(self) -> None:
        ok = self._load is not None and not self._load.error
        self.run_btn.setEnabled(ok and self.scene_list.count() > 0)

    def _browse(self) -> None:
        name, _ = QFileDialog.getOpenFileName(
            self, text("dryrun.browse_title"), str(self._folder),
            text("dryrun.yaml_filter"))
        if name:
            self.combo.addItem(Path(name).name, name)
            self.combo.setCurrentIndex(self.combo.count() - 1)

    def _add(self) -> None:
        names, _ = QFileDialog.getOpenFileNames(
            self, text("dryrun.add_title"), "", text("dryrun.snap_filter"))
        for name in names:
            self._add_scene(name)
        self._update_run()

    def _remove(self) -> None:
        for item in self.scene_list.selectedItems():
            self.scene_list.takeItem(self.scene_list.row(item))
        self._update_run()

    def _open_folder(self) -> None:
        self._folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._folder)))

    def run(self) -> None:
        if not self.run_btn.isEnabled():
            return
        paths = [self.scene_list.item(i).text()
                 for i in range(self.scene_list.count())]
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self._results = dd.dry_run_files(
                paths, self._load.rules, self._directory)
        finally:
            QApplication.restoreOverrideCursor()
        tables.fill_summary(self.summary_model, self._results)
        tables.fill_detail(self.detail_model, self._results, None)
        self.no_change.setVisible(tables.changes_nothing(self._results))

    def _filter(self, *_args) -> None:
        rows = self.summary.selectionModel().selectedRows()
        tables.fill_detail(self.detail_model, self._results,
                           rows[0].row() if rows else None)


def open_draft_dry_run(window) -> None:
    DraftDryRunDialog(window, default_scenes(window)).exec()
