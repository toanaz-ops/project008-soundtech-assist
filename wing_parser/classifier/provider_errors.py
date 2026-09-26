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

Fix round 1 (a): `classify` walks `__cause__`/`__context__`, not just the
exception it was handed. `provider.py`'s shared `complete_json` does
`except Exception as exc: raise ProviderError(str(exc)) from exc` for
ANY raw exception an adapter raises -- discarding that exception's
`.status_code`/type at the OUTER level while `raise ... from exc` (and
Python's own implicit `__context__`) keeps it reachable one level down.
Without walking the chain, a real bad key / no-network / missing-SDK
failure from any of the three model-call sites (`llm.py`, `guess.py`,
`suggest.py`) or `vocab_changes.py` always fell through to BAD_REPLY,
hiding the real cause from every surface that shows this line. A
`visited` guard stops a pathological `__cause__` cycle (never produced
by a real `raise ... from`, but not something a duck-typed walk should
trust blindly either).

A `CallTimedOut` is never classified here -- `ui/workers.py`'s
`CallRunner` and `ui/call_button.py`'s `ButtonRunner` already intercept
it before any `on_error` callback runs, and every existing call site
already shows one ruled sentence for it. See this file's own docstring
in the plan for why that stays true after this task.
"""

from __future__ import annotations

from typing import Iterator

from wing_parser.classifier.provider import ProviderError

BAD_KEY = "bad_key"
QUOTA = "quota"
NO_KEY = "no_key"
NO_NETWORK = "no_network"
SDK_MISSING = "sdk_missing"
BAD_REPLY = "bad_reply"
OTHER = "other"

_MESSAGES = {
    BAD_KEY: "That key was rejected by the provider. Check it in Settings.",
    QUOTA: "The provider reported no quota or a rate limit. Try again later.",
    NO_KEY: "No API key is configured. Add one in Settings.",
    NO_NETWORK: "Could not reach the provider -- check the network.",
    SDK_MISSING: "The model SDK for this provider is not installed in this build.",
    BAD_REPLY: "The model's reply could not be read as the expected answer.",
}


def _chain(exc: BaseException) -> Iterator[BaseException]:
    """`exc`, then its `__cause__`/`__context__`, then THEIR cause/context,
    stopping the moment something has already been seen -- a real
    `raise ... from` sets both to the same exception, so this is
    naturally short in practice."""
    visited: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in visited:
        visited.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def _classify_one(exc: BaseException) -> str | None:
    """A single exception's own class, or None -- never BAD_REPLY/OTHER,
    which are `classify`'s own fallback once the whole chain is
    exhausted, not a property of any one link in it."""
    status = getattr(exc, "status_code", None)
    if status in (401, 403):
        return BAD_KEY
    if status in (402, 429):
        return QUOTA
    message = str(exc)
    if "no API key" in message:
        return NO_KEY
    type_name = type(exc).__name__
    if isinstance(exc, ConnectionError) or "Connection" in type_name:
        return NO_NETWORK
    if isinstance(exc, ImportError) or "pip install -e ." in message:
        return SDK_MISSING
    return None


def classify(exc: Exception) -> tuple[str, str]:
    """(code, human-readable text)."""
    saw_provider_error = False
    for link in _chain(exc):
        if isinstance(link, ProviderError):
            saw_provider_error = True
        code = _classify_one(link)
        if code is not None:
            return code, _MESSAGES[code]
    if saw_provider_error:
        return BAD_REPLY, _MESSAGES[BAD_REPLY]
    return OTHER, str(exc)
