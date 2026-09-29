"""A journal list whose rows are as tall as their wrapped text needs.

A `SendRow` carries a badge that can run to a full sentence (a clamped or
unanswered write is the conclusion of a live write and must be readable
whole). A `QListWidget` item keeps whatever size hint it was given, so the
hint has to be recomputed for the row's *current* width -- after a badge
arrives and whenever the list is resized.
"""

from __future__ import annotations

from PySide6.QtCore import QSize
from PySide6.QtWidgets import QListWidget


class FitList(QListWidget):
    def fit_all(self) -> None:
        width = max(self.viewport().width(), 1)
        for index in range(self.count()):
            item = self.item(index)
            row = self.itemWidget(item)
            if row is None:
                continue
            height = row.layout().totalHeightForWidth(width)
            if height < 0:
                height = row.sizeHint().height()
            item.setSizeHint(QSize(width, height))

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.fit_all()
