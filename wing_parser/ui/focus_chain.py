"""The explicit Tab chain inside one page (task 18's focus ring).

Extracted from main_window in the task-C split; `_tab_stops` stays
importable from main_window for the keyboard tests.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QScrollArea, QWidget


def _tab_stops(parent: QWidget) -> list[QWidget]:
    """The widgets of one page a Tab press can actually land on.

    Scroll-area internals (viewport, bars) and combo-popup machinery
    take focus but only ever forward it, so they are not stops; the
    scroll *container* itself is skipped the same way. QTableView stays:
    it is a real stop that merely happens to own scrollbars.
    """
    stops: list[QWidget] = []
    for child in parent.findChildren(QWidget):
        policy = child.focusPolicy()
        if not policy & Qt.FocusPolicy.TabFocus and not policy & Qt.FocusPolicy.StrongFocus:
            continue
        ancestor = child.parentWidget()
        while ancestor is not None and ancestor is not parent:
            if isinstance(ancestor, QComboBox):
                break  # popup list of a combo: focus lands via the combo
            ancestor = ancestor.parentWidget()
        else:
            name = child.objectName()
            forwards = name.startswith("qt_scrollarea") or isinstance(child, QScrollArea)
            if not forwards:
                # Views route focus through their viewport (focusProxy),
                # so the chain speaks in proxies — normalise to it.
                effective = child.focusProxy() or child
                if effective not in stops:
                    stops.append(effective)
    return stops


def _chain_tab_order(parent: QWidget) -> None:
    """Link the page's own focus stops into one explicit Tab chain.

    Without this Qt invents a chain across the whole window in creation
    order, and Tab wanders out of the visible page. The Task 18 focus
    ring makes the resulting order visible.
    """
    for current, following in zip(_tab_stops(parent), _tab_stops(parent)[1:]):
        QWidget.setTabOrder(current, following)
