"""The Import page's steps: what each one is made of, and what finishing it does.

`import_page` keeps the page -- its layout, its worker, and the two file
dialogs the tests reach for through `import_page.QFileDialog`. Everything
that is about a *step* lives here: building the four of them, publishing
the widgets the page's seams expose, and the two transitions that read
the workbook (`finish_mapping`) and render the YAML (`show_preview`).

Split out under docs/tech-debt.md#d-29 -- the 1b-19 wiring had put
import_page.py 46 lines over the ~200-line ceiling. Behaviour is
byte-preserved and every public seam still answers on the page, so
tests/test_ui_import_page.py passes unchanged.
"""

from __future__ import annotations

from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget

from wing_parser.showcontext.ingest import sheet as sheet_mod
from wing_parser.ui import import_controller as ic
from wing_parser.ui.mapping_step import MappingStep
from wing_parser.ui.pick_step import PickStep
from wing_parser.ui.save_step import SaveStep
from wing_parser.ui.terms_step import TermsStep
from wing_parser.ui.texts import text

# The mapping widgets the page re-exports by name. They are the seams
# tests drive (`page.sheet_edit`, `page.next_button`, ...), so the list
# is data rather than eight setattr lines.
MAPPING_WIDGETS = (
    "sheet_edit", "header_row_spin", "badge", "problems_label",
    "manual_hint", "back_button", "next_button",
)


def build_steps(page) -> tuple[QWidget, ...]:
    """The four step widgets, wired to `page` and published on it.

    Call order matters only in that `page.status`, `page._runner` and
    `page._fail` must already exist: the terms step is handed all three.
    """
    return (_pick(page), _mapping(page), _terms(page), _save(page))


def _pick(page) -> QWidget:
    page.pick_step = PickStep()
    page.sample_pane = page.pick_step.sample_pane
    page.pick_step.choose_button.clicked.connect(page._choose_file)
    return page.pick_step


def _mapping(page) -> QWidget:
    page.mapping_step = MappingStep()
    for name in MAPPING_WIDGETS:
        setattr(page, name, getattr(page.mapping_step, name))

    page.back_button.clicked.connect(
        lambda: page.step_area.setCurrentIndex(0)
    )
    page.next_button.clicked.connect(lambda: finish_mapping(page))
    return page.mapping_step


def _terms(page) -> QWidget:
    page.terms_step = TermsStep(
        page._provider_factory, page._fail,
        runner=page._runner, report=page.status.setText,
    )
    page.load_guesses_button = page.terms_step.load_guesses_button
    page.preview_button = QPushButton(text("import.preview"))
    page.preview_button.clicked.connect(lambda: show_preview(page))

    step = QWidget()
    layout = QVBoxLayout(step)
    layout.addWidget(page.terms_step)
    layout.addWidget(page.preview_button)
    return step


def _save(page) -> QWidget:
    page.save_step = SaveStep()
    page.preview_pane = page.save_step.preview_pane
    page.save_step.save_button.clicked.connect(page._save_dialog)
    return page.save_step


def finish_mapping(page) -> None:
    """Step 2 -> step 3: read the sheet the operator just described.

    Local and synchronous -- no model call -- so a bad sheet name or a
    missing extra lands in the status label without leaving step 2.
    """
    columns, headers = page.mapping_step.collect()
    name = page.sheet_edit.text().strip() or None
    try:
        read, resolved = ic.read_with(
            page._xlsx, name, page.header_row_spin.value(),
            columns, headers,
        )
        result = ic.build_result(read, resolved)
    except (OSError, ValueError, sheet_mod.MissingExtra) as exc:
        page._fail(exc)
        return
    page._rows = read.rows
    page.show_terms_step(result)


def show_preview(page) -> None:
    """Step 3 -> step 4: render the YAML the Save button will write."""
    try:
        page.preview_pane.setPlainText(
            ic.preview_text(page._xlsx, page._result)
        )
    except (OSError, ValueError) as exc:
        page._fail(exc)
        return
    page.step_area.setCurrentIndex(3)
