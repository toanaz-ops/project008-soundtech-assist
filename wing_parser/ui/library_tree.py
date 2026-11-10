"""The Library tree: group, then its entries, with counts.

Grouping uses `facets` for the groups and `search` for each group's
members, so the tree and the search box can never disagree.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem

from wing_parser.library import facets, search
from wing_parser.library.store import LoadedEntry
from wing_parser.ui.library_support import topic_label
from wing_parser.ui.texts import current_language, text

GROUP_KEYS = ("topic", "instrument", "genre", "technique", "publisher")
ID_ROLE = Qt.ItemDataRole.UserRole


def _group_label(group_by: str, value: str, topics: dict) -> str:
    return topic_label(topics, value) if group_by == "topic" else value


def _title(loaded: LoadedEntry) -> str:
    vi = loaded.entry.get("title_vi") if current_language() == "vi" else None
    title = str(vi or loaded.entry.get("title") or loaded.id)
    return f"{title}  !" if loaded.has_errors else title


class LibraryTree(QTreeWidget):
    entry_selected = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.setHeaderHidden(True)
        self.currentItemChanged.connect(self._on_current)

    def _on_current(self, current, _previous) -> None:
        entry_id = current.data(0, ID_ROLE) if current is not None else None
        self.entry_selected.emit(entry_id or "")

    def current_entry_id(self) -> str:
        item = self.currentItem()
        return (item.data(0, ID_ROLE) or "") if item is not None else ""

    def populate(self, entries: list[LoadedEntry], group_by: str, topics: dict,
                 query: str = "") -> int:
        """Rebuild the tree for `entries` under `query`; returns the match count."""
        keep = self.current_entry_id()
        matches = search(entries, query)
        self.blockSignals(True)
        self.clear()
        counts = facets(matches)[group_by]
        placed: set[str] = set()
        ordered = sorted(counts, key=lambda v: _group_label(group_by, v, topics).casefold())
        bold = QFont(self.font())
        bold.setBold(True)
        for value in ordered:
            members = search(matches, **{group_by: value})
            self._add_group(_group_label(group_by, value, topics), members, bold)
            placed.update(m.id for m in members)
        rest = [m for m in matches if m.id not in placed]
        if rest:
            self._add_group(text("library.untagged"), rest, bold)
        self.expandAll()
        self.blockSignals(False)
        found = self.select_entry(keep)
        if not found:
            self.entry_selected.emit("")
        return len(matches)

    def _add_group(self, label: str, members: list[LoadedEntry], font: QFont) -> None:
        group = QTreeWidgetItem(self, [f"{label} ({len(members)})"])
        group.setFont(0, font)
        group.setFlags(Qt.ItemFlag.ItemIsEnabled)
        for loaded in members:
            child = QTreeWidgetItem(group, [_title(loaded)])
            child.setData(0, ID_ROLE, loaded.id)

    def select_entry(self, entry_id: str) -> bool:
        """Select the first row carrying `entry_id`; False when there is none."""
        for index in range(self.topLevelItemCount()):
            group = self.topLevelItem(index)
            for row in range(group.childCount()):
                child = group.child(row)
                if entry_id and child.data(0, ID_ROLE) == entry_id:
                    self.setCurrentItem(child)
                    return True
        return False

    def first_entry_id(self) -> str:
        for index in range(self.topLevelItemCount()):
            group = self.topLevelItem(index)
            if group.childCount():
                return group.child(0).data(0, ID_ROLE)
        return ""
