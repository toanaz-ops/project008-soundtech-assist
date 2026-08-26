"""The wizard's step rail: four read-only legends, one lit.

A four-step flow with no indicator reads as a pile of buttons; the rail
names the road and lights the current stop. It takes no clicks -- the
wizard's own Back/Next buttons own the movement -- so the labels ahead
simply render dimmed.
"""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLabel, QWidget

from wing_parser.ui.theme.widgets import caption_font


class StepRail(QWidget):
    def __init__(self, steps: tuple[tuple[str, str], ...],
                 parent: QWidget | None = None) -> None:
        """`steps` pairs a slug with its display string from texts.py."""
        super().__init__(parent)
        self.names = tuple(slug for slug, _ in steps)
        self.step = 0

        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        self.labels: list[QLabel] = []
        for _, display in steps:
            label = QLabel(display.upper())
            label.setFont(caption_font())
            row.addWidget(label)
            self.labels.append(label)
        row.addStretch()
        self.set_step(0)

    def set_step(self, index: int) -> None:
        self.step = index
        for position, label in enumerate(self.labels):
            label.setEnabled(position == index)
