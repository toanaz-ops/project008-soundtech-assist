"""Widgets shared by the page registry until real pages replace them."""

from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget

from wing_parser.ui.texts import text


class EmptyState(QWidget):
    """A placeholder for a page that is not built yet.

    It shows the page's name and offers the one action that always makes
    sense on an empty window: opening a scene.
    """

    open_requested = Signal()

    def __init__(self, page_name: str) -> None:
        super().__init__()
        icon = QLabel()
        icon.setPixmap(qta.icon("fa5s.folder-open").pixmap(48, 48))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)

        name = QLabel(page_name)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)

        hint = QLabel(text("empty.open_hint"))
        hint.setAlignment(Qt.AlignmentFlag.AlignCenter)

        open_button = QPushButton(text("empty.open_button"))
        open_button.clicked.connect(self.open_requested)

        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(icon)
        layout.addWidget(name)
        layout.addWidget(hint)
        layout.addWidget(open_button, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addStretch()
