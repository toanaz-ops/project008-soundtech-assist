"""Build the application QPalette from the token table.

qtawesome resolves an icon's colour from the application palette at
icon-construction time, so this must be installed before MainWindow is
constructed -- install.apply() owns that ordering.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette

from wing_parser.ui.theme import tokens


def build() -> QPalette:
    p = QPalette()
    c = tokens.COLOURS

    def role(role_name: QPalette.ColorRole, token: str) -> None:
        p.setColor(role_name, QColor(tokens.hex_str(token)))

    role(QPalette.ColorRole.Window, "background")
    role(QPalette.ColorRole.WindowText, "text")
    role(QPalette.ColorRole.Base, "well")
    role(QPalette.ColorRole.AlternateBase, "panel")
    role(QPalette.ColorRole.Text, "text")
    role(QPalette.ColorRole.Button, "panel")
    role(QPalette.ColorRole.ButtonText, "text")
    role(QPalette.ColorRole.PlaceholderText, "faded")
    role(QPalette.ColorRole.ToolTipBase, "panel")
    role(QPalette.ColorRole.ToolTipText, "text")
    role(QPalette.ColorRole.BrightText, "peak")
    role(QPalette.ColorRole.Light, "raise_")
    role(QPalette.ColorRole.Midlight, "border")
    role(QPalette.ColorRole.Mid, "grid")
    role(QPalette.ColorRole.Dark, "shade")
    role(QPalette.ColorRole.Shadow, "shade")
    role(QPalette.ColorRole.Highlight, "accent")
    role(QPalette.ColorRole.HighlightedText, "shade")
    role(QPalette.ColorRole.Link, "settled")
    return p
