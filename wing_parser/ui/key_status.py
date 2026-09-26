"""The shared key check + provider factory every AI-backed surface uses.

The import page's key line, honest about a missing key and routed to
Settings, lives here, plus two small functions fix round 1 pulled out
to stop them drifting apart between callers:

- `key_configured()` (was `_key_configured`, private to this file, now
  shared with the Vocabulary window's assistant -- I0) says whether a
  model call would find a key, without making one.
- `provider_factory()` is the exact `resolve_config` -> `make_provider`
  chain both `ImportPage._provider_factory` and
  `VocabularyWindow._provider_factory` had duplicated; both now delegate
  here (fix round 1 minor) so the one chain can't drift out of step with
  itself the way `key_configured`'s own docstring already warns about.

The whole assisted path (proposal, guesses) dies without an API key,
and until now it died silently. `KeyStatusLine` re-checks on every show,
so saving a key in Settings is reflected the moment the page returns --
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
        if key_configured():
            self.setText("")
        else:
            self.setText(
                text("import.no_key")
                + ' <a href="settings">' + text("import.open_settings") + "</a>"
            )


def key_configured() -> bool:
    """Cheap and offline: would a model call find a key?

    Deliberately not its own search. `provider.resolve_config` is the
    same function `provider_factory` (below) builds the real provider
    from, so this check cannot drift out of step with the call it is
    describing -- which is exactly how it once warned about a configured
    machine. A placeholder value counts as unconfigured, not as a key,
    and a pin naming a missing file counts as unconfigured too rather
    than as a crash: this is a hint (or, for the Vocabulary window's
    assistant, a grey-out gate -- I0), not a network probe.
    See docs/tech-debt.md#d-30.
    """
    from wing_parser import config
    from wing_parser.classifier import provider

    try:
        loaded = provider.resolve_config(config.knowledge_dir())
    except (OSError, ValueError):
        return False
    return provider.has_usable_key(loaded)


def provider_factory():
    """The provider a real call uses -- `key_configured` reads the same
    resolver, and the two must never disagree (tech-debt.md#d-30). This
    itself can raise (a malformed provider.yaml, a missing named pin);
    every caller must invoke it on a worker thread, never the GUI thread
    (fix round 1, I1) -- see `ImportPage.pick_file`'s
    `self._provider_factory` argument to `ic.proposal_for`, and
    `VocabularyAssistant._propose_via_factory`, for the pattern."""
    from wing_parser import config
    from wing_parser.classifier.provider import make_provider, resolve_config

    return make_provider(resolve_config(config.knowledge_dir()))
