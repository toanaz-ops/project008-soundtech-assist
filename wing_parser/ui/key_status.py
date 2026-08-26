"""The import page's key line: honest about a missing key, routed to Settings.

The whole assisted path (proposal, guesses) dies without an API key,
and until now it died silently. The line re-checks on every show, so
saving a key in Settings is reflected the moment the page returns --
construction time is too early, because Settings writes the key while
this page is already alive.
"""

from __future__ import annotations

import os

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QWidget

from wing_parser.ui.texts import text


class KeyStatusLine(QLabel):
    open_settings_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("", parent)
        self.setWordWrap(True)
        self.linkActivated.connect(
            lambda _link: self.open_settings_requested.emit())
        self._check()

    def showEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().showEvent(event)
        self._check()

    def _check(self) -> None:
        if _key_configured():
            self.setText("")
        else:
            self.setText(
                text("import.no_key")
                + ' <a href="settings">' + text("import.open_settings") + "</a>"
            )


def _key_configured() -> bool:
    """Cheap and offline: does the effective provider config carry a key?

    A pasted api_key in provider.yaml wins, else its api_key_env. A
    WING_PROVIDER_CONFIG naming a missing file counts as unconfigured,
    not as a crash -- this line is a hint, not a gate.
    """
    from wing_parser.classifier import provider

    try:
        loaded = provider.load_config(None)
    except ValueError:
        return False
    resolved = provider.resolve(loaded)
    return bool(loaded.api_key) or bool(os.environ.get(resolved.api_key_env))
