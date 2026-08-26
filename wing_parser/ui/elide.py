"""How a table cell's text is cut to fit, and the painter that cuts it.

Two elisions, one place. Identifier-shaped values -- channel names,
target paths, anything an operator scans for its ending -- use the
hand-rolled `elide_middle`, which always protects the last two
characters: "Ana…1" stays readable, "…post-fader to bu" does not.
Prose uses Qt's own middle cut (`elide_prose`), where the tail carries
no information.

`MonoDelegate` is the one cell painter shared by every table: it cuts
text as above, and can set numeric columns in the mono face,
right-aligned so figures compare down the page.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QApplication, QStyle, QStyleOptionViewItem, QStyledItemDelegate

from wing_parser.ui.theme import fonts, tokens

ELLIPSIS = "…"
TAIL = 2


def elide_middle(value: str, metrics: QFontMetrics, width: int) -> str:
    """Cut `value` in the middle, keeping its last two characters.

    Binary search over how much of the head survives; when even
    "…" + tail cannot fit, the widest honest answer is still that
    string, so it is returned regardless.
    """
    if metrics.horizontalAdvance(value) <= width:
        return value
    tail = value[-TAIL:]
    head = value[:-TAIL]
    # A tail that starts with the leftover of a broken word reads worse
    # than one more character: "An… 1" hides which analogue it is, so
    # pull back to the letter before the space -- "An…e 1".
    if tail.startswith(" ") and head:
        tail = head[-1] + tail
        head = head[:-1]
    low, high = 0, len(head)
    while low < high:
        middle = (low + high + 1) // 2
        if metrics.horizontalAdvance(head[:middle] + ELLIPSIS + tail) <= width:
            low = middle
        else:
            high = middle - 1
    return head[:low] + ELLIPSIS + tail


def elide_prose(value: str, metrics: QFontMetrics, width: int) -> str:
    """Qt's own middle cut -- for prose, where the ending is filler."""
    return metrics.elidedText(value, Qt.TextElideMode.ElideMiddle, width)


class MonoDelegate(QStyledItemDelegate):
    """The house cell painter: elision everywhere, mono numerals.

    `numeric_columns` get the mono face AND right alignment;
    `mono_columns` get the face but keep their left edge (a target path
    is technical text, not a figure). `prose_columns` are cut with Qt's
    middle elision instead of the hand-rolled one. The optional bar
    draws a 2px dim-to-accent strip beside one column's cells, gated by
    a zero-argument `bar_enabled` so callers can bind it to a live flag.
    """

    def __init__(
        self,
        numeric_columns: frozenset[int] | set[int] = (),
        mono_columns: frozenset[int] | set[int] = (),
        prose_columns: frozenset[int] | set[int] = (),
        bar_column: int | None = None,
        bar_enabled=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._numeric = frozenset(numeric_columns)
        self._mono = frozenset(mono_columns)
        self._prose = frozenset(prose_columns)
        self._bar_column = bar_column
        self._bar_enabled = bar_enabled
        self._bar_rows = -1
        self._bar_peak = 0.0

    def initStyleOption(self, option: QStyleOptionViewItem, index) -> None:
        super().initStyleOption(option, index)
        column = index.column()
        if column in self._numeric or column in self._mono:
            option.font = fonts.mono_font(tokens.COLUMN_SIZE)
            option.fontMetrics = QFontMetrics(option.font)
        if column in self._numeric:
            option.displayAlignment = (
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
            )

    def paint(self, painter, option: QStyleOptionViewItem, index) -> None:
        self.initStyleOption(option, index)
        metrics = QFontMetrics(option.font)
        width = max(option.rect.width() - tokens.METRICS["unit"] * 2, 0)
        if index.column() in self._prose:
            option.text = elide_prose(option.text, metrics, width)
        else:
            option.text = elide_middle(option.text, metrics, width)
        style = option.widget.style() if option.widget else QApplication.style()
        style.drawControl(QStyle.CE_ItemViewItem, option, painter, option.widget)
        if index.column() == self._bar_column and (
            self._bar_enabled is None or self._bar_enabled()
        ):
            self._paint_bar(painter, option, index)

    # -- the magnitude bar -------------------------------------------------

    def _paint_bar(self, painter, option: QStyleOptionViewItem, index) -> None:
        fraction = self._bar_fraction(index)
        if fraction is None:
            return
        colour = _lerp_colour(fraction)
        band = option.rect.adjusted(0, tokens.METRICS["unit"], 0, -tokens.METRICS["unit"])
        painter.fillRect(band.left(), band.top(), 2, band.height(), colour)

    def _bar_fraction(self, index):
        """|value| against the column's largest, cached per row count."""
        model = index.model()
        rows = model.rowCount()
        if rows != self._bar_rows:
            peak = 0.0
            for row in range(rows):
                try:
                    peak = max(
                        peak,
                        abs(float(model.index(row, self._bar_column).data() or "")),
                    )
                except (TypeError, ValueError):
                    continue
            self._bar_rows, self._bar_peak = rows, peak
        try:
            value = abs(float(index.data()))
        except (TypeError, ValueError):
            return None
        if not self._bar_peak:
            return None
        return min(value / self._bar_peak, 1.0)


def _lerp_colour(fraction: float):
    """dim -> accent, both read from the token table at run time."""
    from PySide6.QtGui import QColor

    low = QColor(tokens.COLOURS["dim"])
    high = QColor(tokens.COLOURS["accent"])
    out = QColor(low)
    out.setRed(round(low.red() + (high.red() - low.red()) * fraction))
    out.setGreen(round(low.green() + (high.green() - low.green()) * fraction))
    out.setBlue(round(low.blue() + (high.blue() - low.blue()) * fraction))
    return out
