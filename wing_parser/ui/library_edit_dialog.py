"""Create or edit one library entry.

Save stays disabled while `validate` reports any error -- an entry needs at
least one complete source -- and, when editing, until there is a change
note. Warnings (an unvetted publisher) are listed but never block.
A save goes through `LibraryStore.save`; a `RevisionConflict` reloads the
entry rather than overwriting someone else's change.
"""

from __future__ import annotations

from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from wing_parser import config
from wing_parser.library import EntryExists, Issue, RevisionConflict, ValidationFailed, errors
from wing_parser.library.store import LibraryStore, LoadedEntry, default_author
from wing_parser.ui import state_store
from wing_parser.ui.library_edit_form import EntryForm
from wing_parser.ui.library_support import check_entry, now_stamp, taxonomy
from wing_parser.ui.texts import text
from wing_parser.ui.theme import tokens


def warn(parent, title: str, body: str) -> None:
    QMessageBox.warning(parent, title, body)


def remembered_author(directory=None) -> str:
    saved = state_store.load(directory or config.knowledge_dir()).get("author", "")
    return saved or default_author()


class EditDialog(QDialog):
    def __init__(self, store: LibraryStore, loaded: LoadedEntry | None = None,
                 parent: QWidget | None = None, state_dir=None) -> None:
        super().__init__(parent)
        self._store, self._state_dir = store, state_dir
        self._loaded, self.saved_id = loaded, ""
        self.editing = loaded is not None
        self.setWindowTitle(text("library.edit.title_edit").format(id=loaded.id) if loaded
                            else text("library.edit.title_new"))
        self.resize(980, 720)
        topics, _ = taxonomy(store)
        self.form = EntryForm(topics, self.editing)
        self.form.load(loaded.entry if loaded else {"status": "draft", "confidence": "common-practice"})
        self.author_edit = QLineEdit(remembered_author(state_dir))
        self.note_edit = QLineEdit()
        self.note_edit.setPlaceholderText(text("library.note_hint"))
        self.issue_list = QListWidget()
        self.issue_list.setMaximumHeight(120)
        self.save_button = QPushButton(text("library.save"))
        self.cancel_button = QPushButton(text("library.cancel"))
        self.save_button.setDefault(True)
        self.save_button.clicked.connect(self.save)
        self.cancel_button.clicked.connect(self.reject)

        meta = QFormLayout()
        meta.addRow(text("library.author"), self.author_edit)
        meta.addRow(text("library.note"), self.note_edit)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.save_button)
        layout = QVBoxLayout(self)
        layout.addWidget(self.form, stretch=1)
        layout.addWidget(QLabel(text("library.issues")))
        layout.addWidget(self.issue_list)
        layout.addLayout(meta)
        layout.addLayout(buttons)
        for signal in (self.form.changed, self.author_edit.textChanged, self.note_edit.textChanged):
            signal.connect(self.revalidate)
        self.revalidate()

    def current_issues(self) -> list[Issue]:
        entry = self.form.to_entry()
        entry["revision"] = int(entry.get("revision") or 0) + 1
        entry["updated_at"], entry["updated_by"] = now_stamp(), self.author_edit.text().strip() or "-"
        issues = check_entry(self._store, entry)
        if self.form.rule_error:
            issues.append(Issue("error", "bad-rule", "rule",
                                text("library.rule_bad").format(error=self.form.rule_error)))
        if self.editing and not self.note_edit.text().strip():
            issues.append(Issue("error", "note-required", "note", text("library.note_required")))
        return issues

    def revalidate(self) -> None:
        issues = self.current_issues()
        self.issue_list.clear()
        for issue in sorted(issues, key=lambda i: i.level != "error"):
            label = text(f"library.issue.{issue.level}")
            item = QListWidgetItem(f"{label}: {issue.field} - {issue.message}")
            colour = "danger" if issue.level == "error" else "warn"
            item.setForeground(QBrush(QColor(tokens.hex_str(colour))))
            self.issue_list.addItem(item)
        self.save_button.setEnabled(not errors(issues))

    def save(self) -> None:
        entry = self.form.to_entry()
        author = self.author_edit.text().strip() or default_author()
        creating = self._loaded is None
        expected = None if creating else int(self._loaded.entry.get("revision") or 0)
        try:
            written = self._store.save(entry, author=author, note=self.note_edit.text().strip(),
                                       expected_revision=expected, create=creating)
        except EntryExists:
            warn(self, text("library.conflict.title"), text("library.conflict.new"))
            return
        except RevisionConflict as exc:
            self._on_conflict(exc)
            return
        except ValidationFailed as exc:
            warn(self, text("library.conflict.title"), text("library.save_failed").format(error=exc))
            return
        state_store.save_author(self._state_dir or config.knowledge_dir(), author)
        self.saved_id = str(written["id"])
        self.accept()

    def _on_conflict(self, exc: RevisionConflict) -> None:
        if not self.editing:
            warn(self, text("library.conflict.title"), text("library.conflict.new"))
            return
        warn(self, text("library.conflict.title"),
             text("library.conflict.edit").format(actual=exc.actual, expected=exc.expected))
        self._loaded = self._store.get(self._loaded.id)
        self.form.load(self._loaded.entry)
        self.revalidate()
