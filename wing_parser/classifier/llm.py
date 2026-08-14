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

MODEL = "claude-opus-5"
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


def _kill_switch_thrown() -> bool:
    """True unless the variable is unset or set to something meaning "no".

    Bare truthiness would make WING_DISABLE_LLM=0 disable the fallback,
    which is the opposite of what anyone typing that expects.
    """
    return os.environ.get(DISABLE_VAR, "").strip().casefold() not in _OFF


def available() -> bool:
    if _kill_switch_thrown():
        return False
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def _ask(name: str, domain: str, context: str) -> tuple[str, float]:
    """Single API call. Split out so tests can replace it."""
    import anthropic
    from pydantic import BaseModel, Field

    class SourceGuess(BaseModel):
        kind: str = Field(description="dotted source type, or 'unknown'")
        confidence: float = Field(description="0.0 to 1.0")

    client = anthropic.Anthropic()
    response = client.messages.parse(
        model=MODEL,
        # Headroom, not appetite. On claude-opus-5 thinking is ON by default
        # -- unlike opus-4-8, where omitting the parameter meant no thinking
        # -- and max_tokens caps thinking PLUS the reply. The answer here is
        # two short fields, but 1024 would truncate the moment the model
        # thinks first, and classify() swallows the resulting exception into
        # a silent None. Overshooting costs nothing: billing is per token
        # emitted, not per token allowed.
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": _PROMPT.format(
                    domain_word=_DOMAIN_WORD.get(domain, "channel"),
                    name=name,
                    context=f"{context}\n" if context else "",
                ),
            }
        ],
        output_format=SourceGuess,
    )
    guess = response.parsed_output
    return guess.kind, guess.confidence


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
