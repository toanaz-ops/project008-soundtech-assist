"""The option controls of the Automix dialog (wave 12).

The genre / venue / stage tuples are repeated here on purpose: importing
them from `wing_parser.automix` would load the engine when the menu is
built, which AM-20 forbids. `test_ui_automix` pins them to the engine's.
The lead-vocal picker is left out of phase 1 (AM-32): the engine's
heuristic picks the lead.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QLabel,
    QSlider, QWidget,
)

from wing_parser.ui.texts import text

GENRES = ("pop", "rock", "ballad", "jazz", "edm", "bolero", "speech")
VENUES = ("small", "medium", "large")
STAGES = ("hpf", "eq", "gate", "comp", "fader", "fx", "sends", "inserts")


class OptionsPanel(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.genre = QComboBox()
        for code in GENRES:
            self.genre.addItem(text(f"automix.genre.{code}"), code)
        self.bpm = QDoubleSpinBox()
        self.bpm.setRange(40, 240)
        self.bpm.setDecimals(0)
        self.bpm.setValue(120)
        self.venue = QComboBox()
        for code in VENUES:
            self.venue.addItem(text(f"automix.venue.{code}"), code)
        self.venue.setCurrentIndex(VENUES.index("medium"))
        self.strength = QSlider(Qt.Orientation.Horizontal)
        self.strength.setRange(0, 100)
        self.strength.setValue(100)
        self.strength_label = QLabel(text("automix.percent").format(value=100))
        self.strength.valueChanged.connect(
            lambda v: self.strength_label.setText(
                text("automix.percent").format(value=v)))
        self.stage_boxes = {}
        stages = QHBoxLayout()
        for code in STAGES:
            box = QCheckBox(text(f"automix.stage.{code}"))
            box.setChecked(True)
            self.stage_boxes[code] = box
            stages.addWidget(box)
        strength_row = QHBoxLayout()
        strength_row.addWidget(self.strength, 1)
        strength_row.addWidget(self.strength_label)
        form = QFormLayout(self)
        form.addRow(text("automix.genre"), self.genre)
        form.addRow(text("automix.bpm"), self.bpm)
        form.addRow(text("automix.venue"), self.venue)
        form.addRow(text("automix.strength"), strength_row)
        form.addRow(text("automix.stages"), stages)

    def options(self):
        """Build the engine's options; the engine is loaded only here."""
        from wing_parser.automix import AutomixOptions

        return AutomixOptions(
            genre=self.genre.currentData(), bpm=self.bpm.value(),
            venue=self.venue.currentData(),
            strength=self.strength.value() / 100.0,
            stages=frozenset(c for c, b in self.stage_boxes.items()
                             if b.isChecked()))
