"""The Import page: an assisted ingest behind four buttons.

Pick -> Mapping -> Terms -> Scene -> Save, stacked in `step_area`;
each step is built and advanced by `import_steps` (docs/tech-debt.md#d-29).
Model calls (`proposal_for`, `guesses_for`) run on cancellable workers
with ruled timeouts (task C, wave 1b) -- the page never blocks on the
network. Every failure degrades to a status label -- no tracebacks.
"""

from __future__ import annotations

import zipfile

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFileDialog,
    QLabel,
    QPushButton,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

from wing_parser.ui import import_controller as ic
from wing_parser.ui import import_steps
from wing_parser.ui import key_status
from wing_parser.ui.call_button import ButtonRunner
from wing_parser.ui.key_status import KeyStatusLine
from wing_parser.ui.step_rail import StepRail
from wing_parser.ui.texts import text
from wing_parser.ui.workers import CallRunner

STEPS = ("pick", "mapping", "vocabulary", "scene", "save")


class ImportPage(QWidget):
    open_settings_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._xlsx: str | None = None
        self._result = None
        self._rows: tuple = ()
        # the sheet read and resolved mapping; import_steps.refresh_result
        # rebuilds _result from these against the current vocabulary (R1).
        self._read = None
        self._resolved = None
        # record_term's write target; tests point this at tmp_path, None = cache default.
        self._directory = None
        # the window's session -- Doctor's scene, offered to the Scene step.
        self._session = None

        self.status = QLabel("")
        self.status.setWordWrap(True)
        self.key_status = KeyStatusLine()
        self.key_status.open_settings_requested.connect(
            self.open_settings_requested)
        self._runner = CallRunner(self)
        self.cancel_button = QPushButton(text("import.cancel"))
        self.cancel_button.setVisible(False)
        self.cancel_button.clicked.connect(self._runner.cancel)
        self.step_rail = StepRail(
            tuple((s, text(f"import.step.{s}")) for s in STEPS))

        self.step_area = QStackedLayout()
        for step in import_steps.build_steps(self):
            self.step_area.addWidget(step)
        self.step_area.currentChanged.connect(self.step_rail.set_step)

        self._proposal_call = ButtonRunner(
            runner=self._runner, primary=self.pick_step.choose_button,
            cancel=self.cancel_button, report=self.status.setText,
            running=text("import.proposing"),
            cancelled=text("import.cancelled"),
            timeout_text=text("import.timeout"),
            busy_text=text("import.busy"), on_error=self._fail,
        )

        layout = QVBoxLayout(self)
        layout.addWidget(self.step_rail)
        layout.addWidget(self.status)
        layout.addWidget(self.key_status)
        layout.addWidget(self.cancel_button)
        layout.addLayout(self.step_area)

    def set_session(self, session) -> None:
        """The window's session -- Doctor's scene, the Scene step's default."""
        self._session = session

    @property
    def result(self):
        """Public seam: the BuildResult-shaped object behind step 3."""
        return self._result

    def set_output_directory(self, path) -> None:
        """Public seam: where record_term writes; None restores the default."""
        self._directory = path

    def _provider_factory(self):
        return key_status.provider_factory()

    def _fail(self, exc: Exception) -> None:
        self.status.setText(text("import.error").format(error=exc))

    def _choose_file(self) -> None:
        name, _ = QFileDialog.getOpenFileName(
            self, text("import.pick"), "", text("import.xlsx_filter")
        )
        if name:
            self.pick_file(name)

    def pick_file(self, path: str) -> None:
        """Public seam: what choosing a file does, minus the dialog.

        Sampling is local and stays synchronous; the model proposal
        runs on a worker with its ruled timeout -- the continuation
        lands in `_proposal_done` when the wire answers.
        """
        try:
            samples = ic.sample(path)
        except (OSError, ValueError, zipfile.BadZipFile) as exc:
            self._fail(exc)
            return
        self.pick_step.show_samples(samples)
        self._proposal_call.run(
            "proposal", ic.proposal_for, path, self._provider_factory,
            on_success=lambda proposal: self._proposal_done(
                path, samples, proposal),
        )

    def _proposal_done(self, path, samples, proposal) -> None:
        """The exact success continuation `pick_file` always had."""
        self._xlsx = path
        self.mapping_step.fill(proposal)
        self.status.setText("")
        self.step_area.setCurrentIndex(1)

    def letter_edit(self, field: str):
        return self.mapping_step.letter_edit(field)

    header_edit = letter_edit

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

    def save_as(self, path: str) -> bool:
        """Public seam: write the preview as UTF-8, minus the dialog."""
        return import_steps.write_output(self, path)

    def _save_dialog(self) -> None:
        name, _ = QFileDialog.getSaveFileName(
            self, text("import.save_as"), "", text("import.yaml_filter")
        )
        if name:
            self.save_as(name)
