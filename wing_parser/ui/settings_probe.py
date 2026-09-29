"""Settings ▸ Test connection's default probe, in the UI language.

`provider.ping` returns the CLI's English `(ok, message)`, so a failure
caught inside it could never reach `ai_message`. This probe runs
`provider.ping_raw` (which raises) and classifies the failure here, with
its code in hand -- the CLI's `ping` and `provider_errors` are untouched.
It runs on the dialog's worker thread; `text()` only reads a global.
"""

from __future__ import annotations

from wing_parser.classifier import provider, provider_errors
from wing_parser.ui.ai_error_text import ai_message
from wing_parser.ui.texts import text


def probe(cfg: provider.ProviderConfig) -> tuple[bool, str]:
    try:
        provider.ping_raw(cfg)
    except Exception as exc:  # noqa: BLE001 - every failure becomes a message
        return False, ai_message(*provider_errors.classify(exc))
    return True, text("settings.probe_replied").format(name=cfg.name)
