"""The right-hand side of the Library page: badges over a Markdown view.

Badges are coloured labels (the theme's `azStyle` states), the entry
itself is Markdown in a `QTextBrowser`. Links open in the system browser.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QImage, QTextDocument
from PySide6.QtWidgets import QHBoxLayout, QLabel, QTextBrowser, QVBoxLayout, QWidget

from wing_parser.library.store import LibraryStore, LoadedEntry
from wing_parser.ui.library_markdown import entry_markdown
from wing_parser.ui.library_support import flag_codes
from wing_parser.ui.texts import text
from wing_parser.ui.theme.widgets import set_style

_CONFIDENCE_STYLE = {"established": "ok", "common-practice": None, "contested": "warn"}
_STATUS_STYLE = {"draft": "warn", "reviewed": "ok", "retired": "faded"}


def badges_for(loaded: LoadedEntry) -> list[tuple[str, str, str | None]]:
    """(key, label, azStyle) for every badge the entry earns."""
    entry, codes = loaded.entry, flag_codes(loaded.issues)
    badges: list[tuple[str, str, str | None]] = []
    confidence, status = entry.get("confidence"), entry.get("status")
    if confidence in _CONFIDENCE_STYLE:
        badges.append((confidence, text(f"library.badge.{confidence}"), _CONFIDENCE_STYLE[confidence]))
    if status in _STATUS_STYLE:
        badges.append((status, text(f"library.badge.{status}"), _STATUS_STYLE[status]))
    badges.append((loaded.layer, text(f"library.badge.{loaded.layer}"), "faded"))
    if "unsourced" in codes:
        badges.append(("unsourced", text("library.badge.unsourced"), "danger"))
    if "unvetted-source" in codes:
        badges.append(("unvetted", text("library.badge.unvetted"), "warn"))
    other = [i for i in loaded.issues if i.level == "error" and i.code != "unsourced"]
    if other:
        badges.append(("invalid", text("library.badge.invalid"), "danger"))
    return badges


class FitBrowser(QTextBrowser):
    """A Markdown view whose local images never outgrow the viewport."""

    def loadResource(self, kind, url):  # noqa: N802 -- Qt override
        if kind == QTextDocument.ResourceType.ImageResource.value and url.isLocalFile():
            image = QImage(url.toLocalFile())
            limit = max(self.viewport().width() - 24, 240)
            if not image.isNull():
                if image.width() > limit:
                    return image.scaledToWidth(limit, Qt.TransformationMode.SmoothTransformation)
                return image
        return super().loadResource(kind, url)


class EntryView(QWidget):
    def __init__(self, store: LibraryStore, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._store = store
        self.topics: dict = {}
        self.badge_row = QHBoxLayout()
        self.badge_row.setSpacing(14)
        self.browser = FitBrowser()
        self._loaded: LoadedEntry | None = None
        self._rendered_width = 0
        self._refit = QTimer(self)
        self._refit.setSingleShot(True)
        self._refit.setInterval(200)
        self._refit.timeout.connect(self._refit_images)
        self.browser.setOpenExternalLinks(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(self.badge_row)
        layout.addWidget(self.browser, stretch=1)
        self.badge_keys: list[str] = []
        self.show_entry(None)

    def _clear_badges(self) -> None:
        while self.badge_row.count():
            item = self.badge_row.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self.badge_keys = []

    def show_entry(self, loaded: LoadedEntry | None) -> None:
        self._clear_badges()
        self._loaded = loaded
        self._rendered_width = self.browser.viewport().width()
        if loaded is None:
            self.browser.setMarkdown(f"*{text('library.empty')}*")
            return
        for key, label, style in badges_for(loaded):
            badge = QLabel(label.upper())
            set_style(badge, style)
            self.badge_row.addWidget(badge)
            self.badge_keys.append(key)
        self.badge_row.addStretch(1)
        self.browser.setMarkdown(entry_markdown(loaded, self._store, self.topics))

    def resizeEvent(self, event) -> None:  # noqa: N802 -- Qt override
        super().resizeEvent(event)
        if self._loaded is not None and abs(self.browser.viewport().width() - self._rendered_width) > 40:
            self._refit.start()

    def _refit_images(self) -> None:
        """Re-render at the new width, keeping the reader's place."""
        bar = self.browser.verticalScrollBar()
        place = bar.value()
        self.show_entry(self._loaded)
        bar.setValue(place)
