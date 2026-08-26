"""The Import page: an assisted ingest behind four buttons.

Pick -> Mapping -> Terms -> Preview & Save, stacked in `step_area`.
Wave 1 runs the model calls (`proposal_for`, `guesses_for`)
synchronously under a wait cursor (threads deferred, YAGNI). Every
failure degrades to a status label -- this page never tracebacks.
"""

from __future__ import annotations

import zipfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QPushButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from wing_parser.showcontext.ingest import sheet as sheet_mod
from wing_parser.ui import import_controller as ic
from wing_parser.ui.mapping_step import MappingStep
from wing_parser.ui.pick_step import PickStep
from wing_parser.ui.save_step import SaveStep
from wing_parser.ui.terms_step import TermsStep
from wing_parser.ui.texts import text

FILTER = "Excel workbook (*.xlsx)"


class ImportPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._xlsx: str | None = None
        self._result = None
        self._rows: tuple = ()
        # record_term's write target; tests point this at tmp_path, None = cache default.
        self._directory = None

        self.status = QLabel("")
        self.status.setWordWrap(True)

        self.step_area = QStackedLayout()
        for step in (self._build_pick(), self._build_mapping(),
                     self._build_terms(), self._build_save()):
            self.step_area.addWidget(step)

        layout = QVBoxLayout(self)
        layout.addWidget(self.status)
        layout.addLayout(self.step_area)

    def set_session(self, session) -> None:
        """Accepted but unused: import is scene-independent."""

    @property
    def result(self):
        """Public seam: the BuildResult-shaped object behind step 3."""
        return self._result

    def set_output_directory(self, path) -> None:
        """Public seam: where record_term writes; None restores the default."""
        self._directory = path

    def _provider_factory(self):
        from wing_parser.classifier.provider import load_config, make_provider

        return make_provider(load_config(None))

    def _fail(self, exc: Exception) -> None:
        self.status.setText(text("import.error").format(error=exc))

    def _build_pick(self) -> QWidget:
        self.pick_step = PickStep()
        self.sample_pane = self.pick_step.sample_pane
        self.pick_step.choose_button.clicked.connect(self._choose_file)
        return self.pick_step

    def _choose_file(self) -> None:
        name, _ = QFileDialog.getOpenFileName(
            self, text("import.pick"), "", FILTER
        )
        if name:
            self.pick_file(name)

    def pick_file(self, path: str) -> None:
        """Public seam: what choosing a file does, minus the dialog."""
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            try:
                samples = ic.sample(path)
                proposal = ic.proposal_for(path, self._provider_factory)
            except (OSError, ValueError, zipfile.BadZipFile) as exc:
                self._fail(exc)
                return
        finally:
            QApplication.restoreOverrideCursor()
        self._xlsx = path
        self.pick_step.show_samples(samples)
        self.mapping_step.fill(proposal)
        self.status.setText("")
        self.step_area.setCurrentIndex(1)

    def _build_mapping(self) -> QWidget:
        self.mapping_step = MappingStep()
        for name in ("sheet_edit", "header_row_spin", "badge",
                     "problems_label", "manual_hint", "back_button",
                     "next_button"):
            setattr(self, name, getattr(self.mapping_step, name))

        self.back_button.clicked.connect(
            lambda: self.step_area.setCurrentIndex(0)
        )
        self.next_button.clicked.connect(self._finish_mapping)
        return self.mapping_step

    def letter_edit(self, field: str):
        return self.mapping_step.letter_edit(field)

    header_edit = letter_edit

    def _finish_mapping(self) -> None:
        columns, headers = self.mapping_step.collect()
        name = self.sheet_edit.text().strip() or None
        try:
            read, resolved = ic.read_with(
                self._xlsx, name, self.header_row_spin.value(),
                columns, headers,
            )
            result = ic.build_result(read, resolved)
        except (OSError, ValueError, sheet_mod.MissingExtra) as exc:
            self._fail(exc)
            return
        self._rows = read.rows
        self.show_terms_step(result)

    def _build_terms(self) -> QWidget:
        self.terms_step = TermsStep(self._provider_factory, self._fail)
        self.load_guesses_button = self.terms_step.load_guesses_button
        self.preview_button = QPushButton(text("import.preview"))
        self.preview_button.clicked.connect(self._show_preview)

        step = QWidget()
        layout = QVBoxLayout(step)
        layout.addWidget(self.terms_step)
        layout.addWidget(self.preview_button)
        return step

    def show_terms_step(self, result) -> None:
        """Test seam: rebuild step 3 from any BuildResult-shaped object."""
        self._result = result
        self.terms_step.directory = self._directory
        self.terms_step.set_rows(self._rows)
        self.terms_step.populate(result)
        self.step_area.setCurrentIndex(2)

    def record_button_for(self, term: str) -> QPushButton:
        return self.terms_step.record_button_for(term)

    def skip_button_for(self, term: str) -> QPushButton:
        return self.terms_step.skip_button_for(term)

    def kind_editor_for(self, term: str):
        return self.terms_step.kind_editor_for(term)

    def term_row_state(self, term: str) -> str:
        """pending | recorded | skipped -- recorded means written."""
        return self.terms_step.term_row_state(term)

    def _build_save(self) -> QWidget:
        self.save_step = SaveStep()
        self.preview_pane = self.save_step.preview_pane
        self.save_step.save_button.clicked.connect(self._save_dialog)
        return self.save_step

    def _show_preview(self) -> None:
        try:
            self.preview_pane.setPlainText(
                ic.preview_text(self._xlsx, self._result)
            )
        except (OSError, ValueError) as exc:
            self._fail(exc)
            return
        self.step_area.setCurrentIndex(3)

    def save_as(self, path: str) -> bool:
        """Public seam: write the preview as UTF-8, minus the dialog."""
        try:
            Path(path).write_text(
                ic.preview_text(self._xlsx, self._result), encoding="utf-8"
            )
        except (OSError, ValueError) as exc:
            self._fail(exc)
            return False
        return True

    def _save_dialog(self) -> None:
        name, _ = QFileDialog.getSaveFileName(
            self, text("import.save_as"), "", FILTER
        )
        if name:
            self.save_as(name)
