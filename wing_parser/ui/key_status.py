"""The import page's key line: honest about a missing key, routed to Settings.

The whole assisted path (proposal, guesses) dies without an API key,
and until now it died silently. The line re-checks on every show, so
saving a key in Settings is reflected the moment the page returns --
construction time is too early, because Settings writes the key while
this page is already alive.
"""

from __future__ import annotations

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
    """Cheap and offline: would a model call from this page find a key?

    Deliberately not its own search. `provider.resolve_config` is the
    same function `ImportPage._provider_factory` builds the real provider
    from, so this line cannot drift out of step with the call it is
    describing -- which is exactly how it once warned about a configured
    machine. A placeholder value counts as unconfigured, not as a key,
    and a pin naming a missing file counts as unconfigured too rather
    than as a crash: this line is a hint, not a gate.
    See docs/tech-debt.md#d-30.
    """
    from wing_parser import config
    from wing_parser.classifier import provider

    try:
        loaded = provider.resolve_config(config.knowledge_dir())
    except (OSError, ValueError):
        return False
    return provider.has_usable_key(loaded)
