"""The things QSS cannot reach, drawn from the style instead.

Qt paints the focus rectangle from the style, not the stylesheet, so
Fusion's dotted OS rect survives every QSS rule and reads as a
rendering fault on graphite. A QProxyStyle intercepts the primitive
and draws the house ring instead. The same proxy answers
SH_ItemView_ShowDecorationSelected so an item-view selection covers
the whole row, decoration included -- QSS has no selector for that
hint, only this one.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPen
from PySide6.QtWidgets import QProxyStyle, QStyle

from wing_parser.ui.theme import tokens


class HouseStyle(QProxyStyle):
    """Fusion, with the focus ring and row-selection hint re-homed."""

    def __init__(self) -> None:
        super().__init__("Fusion")

    def drawPrimitive(self, element, option, painter, widget=None):
        if element == QStyle.PrimitiveElement.PE_FrameFocusRect:
            painter.save()
            ring = QPen(QColor(tokens.hex_str("accent")))
            ring.setWidth(1)
            painter.setPen(ring)
            painter.drawRect(option.rect.adjusted(0, 0, -1, -1))
            painter.restore()
            return
        super().drawPrimitive(element, option, painter, widget)

    def styleHint(self, hint, option=None, widget=None, returnData=None):
        if hint == QStyle.StyleHint.SH_ItemView_ShowDecorationSelected:
            return 1
        return super().styleHint(hint, option, widget, returnData)
