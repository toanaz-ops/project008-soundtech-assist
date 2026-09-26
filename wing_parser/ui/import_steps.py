"""The Import page's steps: what each one is made of, and what finishing it does.

`import_page` keeps the page -- its layout, its worker, and the two file
dialogs the tests reach for through `import_page.QFileDialog`. Everything
that is about a *step* lives here: building the four of them, publishing
the widgets the page's seams expose, and the transitions that read the
workbook (`finish_mapping`), rebuild against a freshly taught vocabulary
(`refresh_result`), render the YAML (`show_preview`) and write it
(`write_output`).

Split out under docs/tech-debt.md#d-29 -- the 1b-19 wiring had put
import_page.py 46 lines over the ~200-line ceiling. Behaviour is
byte-preserved and every public seam still answers on the page, so
tests/test_ui_import_page.py passes unchanged. Fix round 2 moved
`refresh_result` (and the write half of `save_as`, `write_output`) here
from `import_page.py` for the same reason -- Task 9 needs the headroom
`_refresh_result`'s 13 lines and `save_as`'s write logic were using up.
"""

from __future__ import annotations

from pathlib import Path

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
    page.terms_step = TermsStep()
    page.terms_step.fail = page._fail
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
        result = ic.build_result(read, resolved, page._directory)
    except (OSError, ValueError, sheet_mod.MissingExtra) as exc:
        page._fail(exc)
        return
    page._rows = read.rows
    page._read, page._resolved = read, resolved
    page.show_terms_step(result)


def refresh_result(page) -> bool:
    """R1: Preview and Save must reflect what Record/Ignore just taught
    in the Terms step, not the mapping-time snapshot -- rebuild from the
    stored read/resolved mapping against the freshly loaded vocabulary at
    this wizard's own directory.

    Returns False, having already reported through `page._fail`, when the
    rebuild itself fails -- fix round 2: the caller must then stop rather
    than show or write the stale `page._result` it never touches on
    failure. Returns True when there is nothing to rebuild (a test that
    hands `show_terms_step` a bare result directly, never having gone
    through `finish_mapping`) or when the rebuild succeeds.
    """
    if page._read is None or page._resolved is None:
        return True
    try:
        page._result = ic.build_result(page._read, page._resolved, page._directory)
    except (OSError, ValueError) as exc:
        page._fail(exc)
        return False
    return True


def show_preview(page) -> None:
    """Step 3 -> step 4: render the YAML the Save button will write.

    A failed `refresh_result` has already reported itself; stop here
    without advancing past step 3 or rendering the now-stale result
    (fix round 2)."""
    if not refresh_result(page):
        return
    try:
        page.preview_pane.setPlainText(
            ic.preview_text(page._xlsx, page._result)
        )
    except (OSError, ValueError) as exc:
        page._fail(exc)
        return
    page.step_area.setCurrentIndex(3)


def write_output(page, path: str) -> bool:
    """Step 4's Save, minus the dialog -- `import_page.save_as` delegates
    here. Refreshed first, same as Preview; a failed refresh must not be
    followed by writing the stale mapping-time result (fix round 2)."""
    if not refresh_result(page):
        return False
    try:
        Path(path).write_text(
            ic.preview_text(page._xlsx, page._result), encoding="utf-8"
        )
    except (OSError, ValueError) as exc:
        page._fail(exc)
        return False
    return True
