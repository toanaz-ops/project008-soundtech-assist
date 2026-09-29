"""Show an AI failure in the UI language.

`provider_errors.classify` returns `(code, english_message)`; the CLI
keeps that English. The UI asks here instead: a classed failure reads
from the `ai_error.<code>` key, while OTHER (no key, by design) keeps
the provider's own message -- it is the SDK's sentence, not ours.
"""

from __future__ import annotations

from wing_parser.ui.texts import TEXTS, text


def ai_message(code: str, message: str) -> str:
    key = f"ai_error.{code}"
    return text(key) if key in TEXTS else message
