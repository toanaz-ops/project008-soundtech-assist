"""Widgets and idioms the stylesheet cannot express.

Qt resolves an ``[azStyle="..."]`` selector once, at polish, so a
``setProperty`` on a live widget is invisible without the
unpolish/polish pair in set_style(). Caption is the tracked uppercase
legend face: Qt QSS has neither text-transform nor letter-spacing, so
the tracking lives in the QFont and the case in the string.
"""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QWidget

from wing_parser.ui.theme import fonts, tokens


def set_style(widget: QWidget, style: str | None) -> None:
    """Re-resolve azStyle on a live widget (the polish pair)."""
    widget.setProperty("azStyle", style)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()


class Caption(QLabel):
    """A tracked, uppercase legend line -- a section label."""

    def __init__(self, text_value: str, parent: QWidget | None = None) -> None:
        super().__init__(text_value.upper(), parent)
        self.setFont(fonts.legend_font(
            tokens.CAPTION_SIZE, bold=True, tracking=tokens.TRACK_CAPTION))
