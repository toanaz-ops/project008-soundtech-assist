"""Widget construction, live search, and broken-reference display shared
by the Vocabulary window's Sets and Terms tabs (split out of
`vocabulary_tab_support.py` in fix round 2 to stay under the 200-line
house-style ceiling -- that module keeps the write/confirm plumbing;
this one keeps everything about building and filtering the table
itself)."""

from __future__ import annotations

from PySide6.QtWidgets import QHBoxLayout, QLineEdit, QPushButton, QTableWidget

from wing_parser.showcontext.ingest import keywords
from wing_parser.ui.texts import text


def build_search_edit(on_text_changed) -> QLineEdit:
    """S1's search box -- identical construction on both tabs."""
    edit = QLineEdit()
    edit.setPlaceholderText(text("vocabulary.search_placeholder"))
    edit.textChanged.connect(on_text_changed)
    return edit


def build_table(columns: tuple[str, ...], on_selection_changed) -> QTableWidget:
    table = QTableWidget(0, len(columns))
    table.setHorizontalHeaderLabels([text(key) for key in columns])
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    table.itemSelectionChanged.connect(on_selection_changed)
    return table


def build_toolbar(*button_specs: tuple[str, object]):
    """`button_specs` is (text key, click handler) pairs. Returns
    `(layout, [buttons])` in the same order, so a tab can unpack straight
    into its own named button attributes."""
    layout = QHBoxLayout()
    buttons = []
    for key, handler in button_specs:
        button = QPushButton(text(key))
        button.clicked.connect(handler)
        layout.addWidget(button)
        buttons.append(button)
    layout.addStretch(1)
    return layout, buttons


def selected_row(table, row_entries):
    row = table.currentRow()
    if row < 0 or row >= len(row_entries):
        return None
    return row_entries[row]


def clear_selection(table) -> None:
    """Clear both the current index and the row selection, in the order
    that actually notifies a listener on `itemSelectionChanged`:
    `setCurrentCell(-1, -1)` FIRST -- fires that signal with
    `currentRow()` already -1 -- then `clearSelection()` as a redundant,
    harmless no-op. The reverse order is a real bug this fixes: alone,
    `clearSelection()` fires the signal while `currentRow()` is still
    the stale row about to become invalid, so a listener reading
    `currentRow()` right then sees the OLD selection, and
    `setCurrentCell(-1, -1)` afterward does not fire the signal again
    once nothing is selected."""
    table.setCurrentCell(-1, -1)
    table.clearSelection()


def apply_search_filter(table, haystacks: list[str], query: str) -> None:
    """S1: live, case-insensitive, diacritic-folded row filtering. Rows
    are hidden, not removed, so table indices stay stable for every
    other lookup this tab does. Fix round 2: if the current row becomes
    hidden, the selection is cleared too -- otherwise it stays
    "selected" invisibly, and Delete (or any other button) still acts on
    it."""
    folded_query = keywords.fold(query)
    for row, haystack in enumerate(haystacks):
        table.setRowHidden(row, bool(folded_query) and folded_query not in haystack)
    current = table.currentRow()
    if current >= 0 and table.isRowHidden(current):
        clear_selection(table)


def folded_haystack(*parts: str) -> str:
    return keywords.fold(" ".join(parts))


def set_identities(vocabulary) -> set[str]:
    """Folded identity of every currently visible set -- the same notion
    of "exists" `vocabulary_checks.check_sets`/`Vocabulary.expand_set`
    use, so a case/diacritic-variant reference is never wrongly flagged
    broken."""
    return {keywords.fold(s.key) for s in vocabulary.sets()}


def broken_set_names(entry_sets, identities: set[str]) -> tuple[str, ...]:
    """Which of `entry_sets` (a term's `sets`, or a set's own nested
    `sets`) name something no longer in `identities`."""
    return tuple(s for s in entry_sets if keywords.fold(s) not in identities)


def render_nested_sets(entry_sets, identities: set[str]) -> str:
    """A comma-joined display of `entry_sets`, marking each broken name
    (fix round 2, S2 generalised to the Sets tab: "broken exactly like a
    term's")."""
    return ", ".join(
        s if keywords.fold(s) in identities else text("vocabulary.broken").format(names=s)
        for s in entry_sets
    )
