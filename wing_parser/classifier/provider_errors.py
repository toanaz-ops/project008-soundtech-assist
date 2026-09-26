"""Classify a provider-call exception into one shared failure vocabulary.

Settings' Test connection, the Mapping step's Try AI (Task 9) and the
Vocabulary window's assistant (Task 6) all call `classify()` and show
its text -- so the same failure reads the same way everywhere, which is
the whole point (design spec §7).

Duck-typed on purpose: `provider_anthropic.py` and `provider_openai.py`
both import their SDK lazily, so this module classifies a real
`anthropic.APIStatusError`/`openai.APIStatusError` without ever
importing either package -- doing so would force an extra onto a
`.[ui]`-only build. Both SDKs' status errors carry a `.status_code` int
(confirmed by reading both provider adapters, 2026-09-26); that duck
type is the entire contract this module leans on.

A `CallTimedOut` is never classified here -- `ui/workers.py`'s
`CallRunner` and `ui/call_button.py`'s `ButtonRunner` already intercept
it before any `on_error` callback runs, and every existing call site
already shows one ruled sentence for it. See this file's own docstring
in the plan for why that stays true after this task.
"""

from __future__ import annotations

from wing_parser.classifier.provider import ProviderError

BAD_KEY = "bad_key"
QUOTA = "quota"
NO_NETWORK = "no_network"
SDK_MISSING = "sdk_missing"
BAD_REPLY = "bad_reply"
OTHER = "other"

_MESSAGES = {
    BAD_KEY: "That key was rejected by the provider. Check it in Settings.",
    QUOTA: "The provider reported no quota or a rate limit. Try again later.",
    NO_NETWORK: "Could not reach the provider -- check the network.",
    SDK_MISSING: "The model SDK for this provider is not installed in this build.",
    BAD_REPLY: "The model's reply could not be read as the expected answer.",
}


def classify(exc: Exception) -> tuple[str, str]:
    """(code, human-readable text)."""
    status = getattr(exc, "status_code", None)
    if status in (401, 403):
        return BAD_KEY, _MESSAGES[BAD_KEY]
    if status in (402, 429):
        return QUOTA, _MESSAGES[QUOTA]

    type_name = type(exc).__name__
    if isinstance(exc, ConnectionError) or "Connection" in type_name:
        return NO_NETWORK, _MESSAGES[NO_NETWORK]
    if isinstance(exc, ImportError) or "pip install -e ." in str(exc):
        return SDK_MISSING, _MESSAGES[SDK_MISSING]
    if isinstance(exc, ProviderError):
        return BAD_REPLY, _MESSAGES[BAD_REPLY]

    return OTHER, str(exc)
