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
    """Cheap and offline: does the effective config carry a *real* key?

    $WING_PROVIDER_CONFIG wins outright -- it is the pin the Settings
    dialog drops after a save, and a pin naming a missing file counts as
    unconfigured, not as a crash: this line is a hint, not a gate. With
    no pin the knowledge-dir copy is read, which is where the dialog
    writes and what a first run that never saved from here would miss;
    ./provider.yaml and the defaults stay behind it, walked by
    `load_config(None)`. A placeholder value ("PASTE_KEY..." and
    friends) counts as unconfigured, not as a key -- see
    `provider.is_placeholder_key` and docs/tech-debt.md#d-30.
    """
    from wing_parser import config
    from wing_parser.classifier import provider

    pinned = bool(os.environ.get(provider.ENV_VAR))
    saved = config.knowledge_dir() / "provider.yaml"
    try:
        loaded = provider.load_config(
            None if pinned or not saved.exists() else saved
        )
    except (OSError, ValueError):
        return False
    return provider.has_usable_key(loaded)
