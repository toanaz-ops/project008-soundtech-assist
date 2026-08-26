"""The one stylesheet/palette application point.

Order matters and is not negotiable:

- fonts.load() before setFont: the base face must be registered before
  anything asks for it.
- setPalette before any icon is built: qtawesome resolves an icon's
  colour from the application palette at construction time, and
  MainWindow.__init__ builds six sidebar icons -- so apply() must stay
  called BEFORE MainWindow is constructed (wired in __main__.py).

Idempotent via an app property, because the test suite shares one
QApplication across many tests.
"""

from __future__ import annotations

from PySide6.QtWidgets import QApplication

from wing_parser.ui.theme import fonts, palette, qss, tokens
from wing_parser.ui.theme.proxy_style import HouseStyle

_GUARD = "_wing_theme_applied"


def apply(app: QApplication) -> None:
    if getattr(app, _GUARD, False):
        return
    setattr(app, _GUARD, True)

    app.setStyle(HouseStyle())
    fonts.load()
    app.setFont(fonts.base_font(tokens.BASE_SIZE))
    app.setPalette(palette.build())
    try:
        import qtawesome

        qtawesome.set_global_defaults(color=tokens.hex_str("dim"))
    except ImportError:
        pass
    app.setStyleSheet(qss.build())
