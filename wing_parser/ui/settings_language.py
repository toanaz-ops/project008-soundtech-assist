"""The Settings ▸ Language row: a combo and the notes under it.

The choice is written to ui-state.json the moment it changes (through
`state_store.save_language`, so no other field is touched) but only takes
effect on the next start: pages build their labels once, and a language
picked once per install is not worth a retranslate hook in every widget
(spec B1). The note under the combo says so, in both languages.

A run started with `--lang` shows a language other than the saved one;
the row says so, so the combo (which shows the SAVED choice) is not
mistaken for what is on screen.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QLabel,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from wing_parser import config
from wing_parser.ui import state_store
from wing_parser.ui.texts import LANGUAGES, current_language, text


def _note(name: str, message: str) -> QLabel:
    label = QLabel(message)
    label.setObjectName(name)
    label.setWordWrap(True)
    return label


class LanguageRow(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.combo = QComboBox()
        self.combo.setObjectName("language_combo")
        for code in LANGUAGES:
            self.combo.addItem(text(f"lang.{code}"), code)
        saved = self._saved()
        self.combo.setCurrentIndex(LANGUAGES.index(saved))
        self.note = _note("language_note", text("settings.language_note"))
        # Nothing to announce until he actually changes the choice.
        self.note.setVisible(False)
        self.run_hint = _note("language_run_hint", text(
            "settings.language_run_hint").format(
                language=text(f"lang.{current_language()}")))
        self.run_hint.setVisible(current_language() != saved)
        self.combo.currentIndexChanged.connect(self._changed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        for widget in (self.combo, self.note, self.run_hint):
            layout.addWidget(widget)

    @staticmethod
    def _saved() -> str:
        return state_store.load(config.knowledge_dir())["language"]

    def _changed(self, index: int) -> None:
        directory = config.knowledge_dir()
        try:
            state_store.save_language(directory, self.combo.itemData(index))
        except OSError as exc:
            QMessageBox.critical(
                self.window(), text("settings.title"),
                text("settings.save_failed").format(
                    path=state_store.state_path(directory), error=exc))
            # Show what is really saved, without saving it again.
            self.combo.blockSignals(True)
            self.combo.setCurrentIndex(LANGUAGES.index(self._saved()))
            self.combo.blockSignals(False)
            return
        self.note.setVisible(True)
