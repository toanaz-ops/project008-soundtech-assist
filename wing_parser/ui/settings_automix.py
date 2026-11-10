"""The Settings ▸ Automix row: Disabled / Draft only (wave 12, AM-6).

The mode is a string enum persisted in ui-state.json through
`state_store.save_automix_mode` the moment the combo moves, and applies
at once: the Tools ▸ Automix entry shows or hides without a restart.
Phase 2 adds `full_auto` as one more entry in `state_store.AUTOMIX_MODES`
and one more text key.

Nothing here imports `wing_parser.automix`: with the mode Disabled the
engine is never loaded (AM-20).
"""

from __future__ import annotations

from PySide6.QtWidgets import QComboBox, QLabel, QMessageBox, QVBoxLayout, QWidget

from wing_parser import config
from wing_parser.ui import state_store
from wing_parser.ui.texts import text


def current_mode() -> str:
    return state_store.load(config.knowledge_dir())["automix_mode"]


def sync_menu(window) -> None:
    """Show the Tools entry unless the mode is Disabled."""
    window._automix_action.setVisible(current_mode() != "disabled")


class AutomixRow(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.combo = QComboBox()
        self.combo.setObjectName("automix_mode_combo")
        for mode in state_store.AUTOMIX_MODES:
            self.combo.addItem(text(f"settings.automix.{mode}"), mode)
        self.combo.setCurrentIndex(
            state_store.AUTOMIX_MODES.index(current_mode()))
        note = QLabel(text("settings.automix_note"))
        note.setWordWrap(True)
        self.combo.currentIndexChanged.connect(self._changed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.combo)
        layout.addWidget(note)

    def _changed(self, index: int) -> None:
        directory = config.knowledge_dir()
        try:
            state_store.save_automix_mode(directory, self.combo.itemData(index))
        except OSError as exc:
            QMessageBox.critical(
                self.window(), text("settings.title"),
                text("settings.save_failed").format(
                    path=state_store.state_path(directory), error=exc))
            self.combo.blockSignals(True)
            self.combo.setCurrentIndex(
                state_store.AUTOMIX_MODES.index(current_mode()))
            self.combo.blockSignals(False)
            return
        window = self.window().parent()
        if window is not None and hasattr(window, "_automix_action"):
            sync_menu(window)
        live = getattr(window, "_automix_live", None)
        if live is not None:
            live.mode_changed(self.combo.itemData(index))
