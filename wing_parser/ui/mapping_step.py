"""The mapping step widget: an editable grid a proposal may prefill.

With no model proposal the grid starts empty under a manual-fill hint.
A proposal prefills sheet, header row and columns and wears a verified
badge only when `problems` is empty; otherwise its problems are shown.
The Next click belongs to the page -- this widget only presents.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from wing_parser.ui.texts import text

LETTER_FIELDS = ("id", "time", "title")
TEXT_FIELDS = ("performers", "note", "sound", "lighting", "led")


class MappingStep(QWidget):
    def __init__(self) -> None:
        super().__init__()
        grid = QGridLayout()
        grid.addWidget(QLabel(text("import.sheet")), 0, 0)
        self.sheet_edit = QLineEdit()
        grid.addWidget(self.sheet_edit, 0, 1)
        grid.addWidget(QLabel(text("import.header_row")), 1, 0)
        self.header_row_spin = QSpinBox()
        self.header_row_spin.setRange(1, 9999)
        grid.addWidget(self.header_row_spin, 1, 1)

        self.badge = QLabel("")
        grid.addWidget(self.badge, 0, 2)
        self.problems_label = QLabel("")
        self.problems_label.setWordWrap(True)
        grid.addWidget(self.problems_label, 2, 0, 1, 3)

        row = 3
        for field in LETTER_FIELDS:
            grid.addWidget(QLabel(field), row, 0)
            edit = QLineEdit()
            edit.setMaxLength(3)
            grid.addWidget(edit, row, 1)
            setattr(self, f"_{field}_edit", edit)
            row += 1
        for field in TEXT_FIELDS:
            grid.addWidget(QLabel(field), row, 0)
            edit = QLineEdit()
            grid.addWidget(edit, row, 1)
            setattr(self, f"_{field}_edit", edit)
            row += 1

        self.manual_hint = QLabel(text("import.manual_hint"))
        self.manual_hint.setWordWrap(True)
        grid.addWidget(self.manual_hint, row, 0, 1, 3)

        self.back_button = QPushButton(text("import.back"))
        self.next_button = QPushButton(text("import.next"))
        buttons = QHBoxLayout()
        buttons.addWidget(self.back_button)
        buttons.addWidget(self.next_button)
        buttons.addStretch()

        layout = QVBoxLayout(self)
        layout.addLayout(grid)
        layout.addLayout(buttons)

    # -- fields ------------------------------------------------------------

    def letter_edit(self, field: str) -> QLineEdit:
        return getattr(self, f"_{field}_edit")

    def header_edit(self, field: str) -> QLineEdit:
        return getattr(self, f"_{field}_edit")

    def collect(self) -> tuple[dict[str, str], dict[str, str]]:
        """Filled entries as (columns by letter, headers by text)."""
        columns = {
            field: self.letter_edit(field).text().strip().upper()
            for field in LETTER_FIELDS if self.letter_edit(field).text().strip()
        }
        headers = {
            field: self.header_edit(field).text().strip()
            for field in TEXT_FIELDS if self.header_edit(field).text().strip()
        }
        return columns, headers

    # -- state ---------------------------------------------------------------

    def clear(self) -> None:
        self.sheet_edit.clear()
        self.header_row_spin.setValue(1)
        for field in LETTER_FIELDS + TEXT_FIELDS:
            self.header_edit(field).clear()
        self.badge.setText("")
        self.problems_label.setText("")
        self.manual_hint.setVisible(True)

    def fill(self, proposal) -> None:
        """Prefill from a MappingProposal (or reset for None)."""
        if proposal is None:
            self.clear()
            return
        self.clear()
        self.manual_hint.setVisible(False)
        self.sheet_edit.setText(str(proposal.sheet))
        self.header_row_spin.setValue(int(proposal.header_row))
        for field, letter in proposal.columns.items():
            self.letter_edit(field).setText(str(letter))
        for field, header in proposal.headers.items():
            self.header_edit(field).setText(str(header))
        key = "import.verified" if not proposal.problems else "import.unverified"
        self.badge.setText(text(key))
        self.problems_label.setText("; ".join(proposal.problems))
