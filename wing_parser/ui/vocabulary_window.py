"""The Vocabulary window: Sets and Terms tabs over one shared Vocabulary.

Opened from the Tools menu (menus.py) and from a button on the Terms
step (Task 7). Task 6 adds a third tab, the AI assistant, without
changing anything below -- `_reload()` is written generically enough
that the assistant's Apply can call it too.

`problems_label` surfaces `Vocabulary.problems` (a hand-edited
`classifier.yaml` entry the loader could not fully trust -- an unknown
kind/set or a set cycle already on disk; `vocabulary.py`'s own per-entry
loader never raises, spec S3.2) as a plain in-window notice, not a
`QMessageBox`: it is informational, not a step blocking anything, and a
modal popup on every open would be in the way every single time until
the entry is fixed. That "never raises" claim does NOT extend to
`Vocabulary.load` itself: `cache._read` raises `ValueError` for a YAML
syntax error or a non-mapping domain, which is not a per-entry problem
`.problems` can report. `open_vocabulary()` below is the guarded entry
point every caller (menus.py, terms_step.py) uses instead of
constructing this dialog directly (fix round, I1) -- in a console=False
release exe, an unguarded raise out of a Qt slot is a silent no-op."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTabWidget, QVBoxLayout,
)

from wing_parser.classifier import vocabulary as vocab_module
from wing_parser.ui import key_status
from wing_parser.ui.texts import text
from wing_parser.ui.vocabulary_assistant import VocabularyAssistant
from wing_parser.ui.vocabulary_sets_tab import VocabularySetsTab
from wing_parser.ui.vocabulary_terms_tab import VocabularyTermsTab


class VocabularyWindow(QDialog):
    def __init__(self, parent=None, *, directory=None,
                 initial_fragments: tuple[str, ...] = ()) -> None:
        super().__init__(parent)
        self.setWindowTitle(text("vocabulary.title"))
        self.setMinimumSize(640, 420)
        self._directory = directory
        self.vocabulary = vocab_module.Vocabulary.load(directory)

        self.problems_label = QLabel("")
        self.problems_label.setWordWrap(True)
        self.problems_label.setVisible(False)
        # Plain text (fix round 1 minor): a hand-edited key can contain
        # anything, including characters Qt's rich-text parser would
        # otherwise treat as markup.
        self.problems_label.setTextFormat(Qt.TextFormat.PlainText)

        self.sets_tab = VocabularySetsTab(self.vocabulary, self._reload)
        self.terms_tab = VocabularyTermsTab(self.vocabulary, self._reload)
        self.assistant_tab = VocabularyAssistant(self.vocabulary, self._provider_factory, self._reload)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.sets_tab, text("vocabulary.tab.sets"))
        self.tabs.addTab(self.terms_tab, text("vocabulary.tab.terms"))
        self.tabs.addTab(self.assistant_tab, text("vocabulary.tab.assistant"))

        close_button = QPushButton(text("vocabulary.close"))
        close_button.clicked.connect(self.accept)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.problems_label)
        layout.addWidget(self.tabs)
        layout.addLayout(buttons)
        self._update_problems()

        if initial_fragments:
            # Task 7's Terms-step entry point: open straight into a
            # running proposal for the fragments it could not resolve,
            # with no UI of its own needed on that step.
            self.tabs.setCurrentWidget(self.assistant_tab)
            self.assistant_tab.propose_for_fragments(initial_fragments)

    def _provider_factory(self):
        """Passed to `VocabularyAssistant`, which invokes it on a worker
        thread (fix round 1, I1), never here. Delegates to
        `key_status.provider_factory` (fix round 1 minor -- was
        duplicated with `ImportPage`'s own copy)."""
        return key_status.provider_factory()

    def _reload(self) -> None:
        """Every write on either tab re-reads the vocabulary and refreshes
        all three -- editing Drum kit must be visible in Band's
        nested-kinds cell without closing this window (F13), and an
        Apply in the assistant must be visible on the Sets/Terms tabs
        the same way a manual edit already is."""
        self.vocabulary = vocab_module.Vocabulary.load(self._directory)
        self.sets_tab.set_vocabulary(self.vocabulary)
        self.terms_tab.set_vocabulary(self.vocabulary)
        self.assistant_tab.set_vocabulary(self.vocabulary)
        self._update_problems()

    def _update_problems(self) -> None:
        problems = self.vocabulary.problems
        if problems:
            self.problems_label.setText(
                text("vocabulary.problems_header") + "\n" + "\n".join(problems))
        self.problems_label.setVisible(bool(problems))


def open_vocabulary(parent, directory=None, fragments: tuple[str, ...] = ()) -> None:
    """Construct and run a `VocabularyWindow` without ever letting a
    broken `classifier.yaml` escape a Qt slot (I1) -- every caller uses
    this instead of constructing the dialog directly."""
    try:
        window = VocabularyWindow(parent, directory=directory, initial_fragments=fragments)
    except (OSError, ValueError) as exc:
        QMessageBox.warning(parent, text("vocabulary.title"), str(exc))
        return
    window.exec()
