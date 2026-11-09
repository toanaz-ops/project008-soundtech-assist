"""The Library page (ninth): the mixing knowledge base, browsable and editable.

Left, a search box, a group-by combo and the tree; right, the entry as
Markdown with its Sources. The store is small, so it is read synchronously
every time the page is shown and on any change -- no worker threads.

`confirm_retire` and the two dialog openers are module-level / methods a
test can replace without a real modal dialog.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QSplitter, QVBoxLayout, QWidget,
)

from wing_parser import config
from wing_parser.library import RevisionConflict, ValidationFailed, default_author
from wing_parser.library.store import LibraryStore, LoadedEntry
from wing_parser.ui.library_edit_dialog import EditDialog, remembered_author, warn
from wing_parser.ui.library_entry_view import EntryView
from wing_parser.ui.library_history_dialog import HistoryDialog
from wing_parser.ui.library_support import taxonomy
from wing_parser.ui.library_tree import GROUP_KEYS, LibraryTree
from wing_parser.ui.texts import text


def confirm_retire(parent, title: str, body: str) -> bool:
    answer = QMessageBox.question(parent, title, body)
    return answer == QMessageBox.StandardButton.Yes


class LibraryPage(QWidget):
    def __init__(self, store: LibraryStore | None = None, state_dir=None) -> None:
        super().__init__()
        self.store = store or LibraryStore(config.library_dir(), config.shipped_library_dir())
        self._state_dir = state_dir
        self._entries: list[LoadedEntry] = []
        self._topics: dict = {}

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(text("library.search_placeholder"))
        self.search_box.setClearButtonEnabled(True)
        self.group_box = QComboBox()
        for key in GROUP_KEYS:
            self.group_box.addItem(text(f"library.group.{key}"), key)
        self.retired_check = QCheckBox(text("library.show_retired"))
        self.count_label = QLabel("")
        self.tree = LibraryTree()
        self.view = EntryView(self.store)
        self.new_button = QPushButton(text("library.new"))
        self.edit_button = QPushButton(text("library.edit"))
        self.history_button = QPushButton(text("library.history"))
        self.retire_button = QPushButton(text("library.retire"))

        group_row = QHBoxLayout()
        group_row.addWidget(QLabel(text("library.group_by")))
        group_row.addWidget(self.group_box, stretch=1)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(self.search_box)
        left_layout.addLayout(group_row)
        left_layout.addWidget(self.retired_check)
        left_layout.addWidget(self.tree, stretch=1)
        left_layout.addWidget(self.count_label)
        buttons = QHBoxLayout()
        for button in (self.new_button, self.edit_button, self.history_button, self.retire_button):
            buttons.addWidget(button)
        buttons.addStretch(1)
        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addLayout(buttons)
        right_layout.addWidget(self.view, stretch=1)
        splitter = QSplitter()
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([340, 800])
        layout = QVBoxLayout(self)
        layout.addWidget(splitter)

        self.search_box.textChanged.connect(self._repopulate)
        self.group_box.currentIndexChanged.connect(self._repopulate)
        self.retired_check.toggled.connect(self._repopulate)
        self.tree.entry_selected.connect(self._on_selected)
        self.new_button.clicked.connect(self.new_entry)
        self.edit_button.clicked.connect(self.edit_entry)
        self.history_button.clicked.connect(self.show_history)
        self.retire_button.clicked.connect(self.retire_entry)
        self._sync_buttons()

    # -- loading -----------------------------------------------------
    def showEvent(self, event) -> None:  # noqa: N802 -- Qt override
        super().showEvent(event)
        self.refresh()

    def refresh(self) -> None:
        """Re-read the store (both layers) and rebuild the tree."""
        self._entries = self.store.entries(include_retired=True)
        self._topics, _ = taxonomy(self.store)
        self.view.topics = self._topics
        self._repopulate()
        if not self.tree.current_entry_id():
            self.tree.select_entry(self.tree.first_entry_id())

    def _visible(self) -> list[LoadedEntry]:
        if self.retired_check.isChecked():
            return self._entries
        return [e for e in self._entries if e.entry.get("status") != "retired"]

    def _repopulate(self, *_args) -> None:
        shown = self.tree.populate(self._visible(), self.group_box.currentData(),
                                   self._topics, self.search_box.text())
        self.count_label.setText(text("library.count").format(count=shown))

    # -- selection ---------------------------------------------------
    def selected(self) -> LoadedEntry | None:
        entry_id = self.tree.current_entry_id()
        return next((e for e in self._entries if e.id == entry_id), None)

    def _on_selected(self, _entry_id: str) -> None:
        self.view.show_entry(self.selected())
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        loaded = self.selected()
        for button in (self.edit_button, self.history_button):
            button.setEnabled(loaded is not None)
        retired = loaded is not None and loaded.entry.get("status") == "retired"
        self.retire_button.setEnabled(loaded is not None and not retired)

    # -- actions -----------------------------------------------------
    def _after_change(self, entry_id: str) -> None:
        self.refresh()
        if entry_id:
            self.tree.select_entry(entry_id)

    def new_entry(self) -> None:
        dialog = EditDialog(self.store, None, self, self._state_dir)
        if dialog.exec():
            self._after_change(dialog.saved_id)

    def edit_entry(self) -> None:
        loaded = self.selected()
        if loaded is None:
            return
        dialog = EditDialog(self.store, loaded, self, self._state_dir)
        if dialog.exec():
            self._after_change(dialog.saved_id)

    def show_history(self) -> None:
        loaded = self.selected()
        if loaded is None:
            return
        dialog = HistoryDialog(self.store, loaded.id, self, self._state_dir)
        dialog.exec()
        if dialog.restored:
            self._after_change(loaded.id)

    def retire_entry(self) -> None:
        loaded = self.selected()
        if loaded is None:
            return
        title = str(loaded.entry.get("title") or loaded.id)
        if not confirm_retire(self, text("library.retire.title"),
                              text("library.retire.confirm").format(title=title)):
            return
        author = remembered_author(self._state_dir) or default_author()
        try:
            self.store.retire(loaded.id, author=author, note=text("library.retire.note"),
                              expected_revision=int(loaded.entry.get("revision") or 0))
        except RevisionConflict as exc:
            warn(self, text("library.conflict.title"),
                 text("library.conflict.edit").format(actual=exc.actual, expected=exc.expected))
        except ValidationFailed as exc:
            warn(self, text("library.conflict.title"), text("library.save_failed").format(error=exc))
        self._after_change(loaded.id)
