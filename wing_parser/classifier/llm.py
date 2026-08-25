"""Optional Claude fallback for names the pattern matcher cannot resolve.

This is the only place in the system where a model participates. The
parser and the rule engine stay deterministic; a model here only turns
one ambiguous human-typed string into a typed guess, and the answer is
cached so it is asked at most once per name.

Every failure path returns None. This tool is used in venues where the
network is unreliable or absent, so an unreachable API must degrade to
"unknown", never to an exception. That covers a safety refusal too:
claude-opus-5 can answer with stop_reason "refusal" and no parsed
output, which surfaces here as an exception and lands on the same
"unknown" path as a dead uplink.
"""

from __future__ import annotations

import os

from wing_parser.classifier.matcher import Classification

_MODEL = "claude-opus-5"
DISABLE_VAR = "WING_DISABLE_LLM"

_PROMPT = """You are labelling a mixing-console scene file.

A {domain_word} on a Behringer WING is named: {name!r}
{context}
Reply with the source type and how confident you are.

Use one of these kinds where it fits, or coin a similar dotted kind:
  drums.kick, drums.snare.top, drums.snare.bottom, drums.tom,
  drums.hihat, drums.overhead, instrument.bass, instrument.guitar.acoustic,
  instrument.guitar.electric, instrument.keys, speech.vocal, speech.mc,
  speech.lectern, speech.lav, speech.headset, speech.handheld,
  utility.click, utility.playback, utility.talkback, utility.ambient,
  utility.spare, utility.fx_return
For a bus, use one of: monitor, fx, subgroup, record, stream, matrix_fill.

Engineers abbreviate heavily and sometimes write in languages other than
English. If the name is genuinely uninformative, answer "unknown" with a
confidence of 0. Do not guess to be helpful.
"""

_DOMAIN_WORD = {"channels": "channel", "buses": "bus"}


_OFF = {"", "0", "false", "no", "off"}


def kill_switch_on() -> bool:
    """True unless the variable is unset or set to something meaning "no".

    Bare truthiness would make WING_DISABLE_LLM=0 disable the fallback,
    which is the opposite of what anyone typing that expects.

    Public because every path that would construct a provider must ask
    it first, not just this module's own fallback: the wizard's mapping
    proposal and term guessing call make_provider() directly. The check
    lives here rather than in provider.py because DISABLE_VAR and the
    _OFF table are model policy -- provider.py is a transport layer and
    does not decide whether models are used at all.
    """
    return os.environ.get(DISABLE_VAR, "").strip().casefold() not in _OFF


# Internal callers predate the rename.
_kill_switch_thrown = kill_switch_on


def available() -> bool:
    if kill_switch_on():
        return False
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def _ask(name: str, domain: str, context: str) -> tuple[str, float]:
    """Single API call through the provider layer. Tests replace _ask itself."""
    from wing_parser.classifier.provider import complete_json
    from wing_parser.classifier.provider_anthropic import AnthropicProvider

    schema = {
        "type": "object",
        "properties": {"kind": {"type": "string"}, "confidence": {"type": "number"}},
        "required": ["kind", "confidence"],
    }
    reply = complete_json(
        AnthropicProvider(model=_MODEL),
        "You are labelling a mixing-console scene file.",
        _PROMPT.format(domain_word=_DOMAIN_WORD.get(domain, "channel"),
                       name=name,
                       context=f"{context}\n" if context else ""),
        schema,
    )
    return reply["kind"], reply["confidence"]


def classify(name: str, domain: str, context: str = "") -> Classification | None:
    if not available():
        return None
    try:
        kind, confidence = _ask(name, domain, context)
        # Coercion belongs inside the guard. A model that answers with a
        # confidence of "high" instead of 0.9 must land on the same
        # "unknown" path as a dead uplink -- float() would otherwise raise
        # straight through the promise this module makes.
        kind = str(kind).strip().casefold()
        score = min(1.0, max(0.0, float(confidence)))
    except Exception:            # noqa: BLE001 - offline must never raise
        return None
    # casefold above is what makes this catch "Unknown" and "UNKNOWN" too.
    # Without it a capitalised refusal became a Classification, and Task 17
    # would have written it into the knowledge file as a real answer.
    if not kind or kind == "unknown":
        return None
    return Classification(kind=kind, confidence=score, origin="llm")
