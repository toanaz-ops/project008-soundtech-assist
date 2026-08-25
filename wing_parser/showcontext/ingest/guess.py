"""Offer a kind for a term the cuesheet vocabulary lacks.

The model proposes; only an explicit y from ToanAZ writes anything, and
the write goes through cache.remember -- the same atomic, round-trip
path every other classification has ever taken -- stamped
origin 'g2b-assisted'.
"""

from __future__ import annotations

import re

SYSTEM_PROMPT = (
    "You are labelling terms from Vietnamese event running orders for a "
    "live-sound tool. Given a term and its row context, name the dotted "
    "kind it behaves as on a mixing console (e.g. speech.vocal, "
    "instrument.guitar.electric, utility.playback). If genuinely "
    "unknowable, kind 'unknown', confidence 0. Do not guess to be helpful."
)

TERM_SCHEMA = {
    "type": "object",
    "properties": {"kind": {"type": "string"}, "confidence": {"type": "number"}},
    "required": ["kind", "confidence"],
}

# build._expectations records a fragment it cannot read as
# `row N: could not read performer '<fragment>'`; 'term' is kept in the
# alternation so older or future comment spellings parse too.
_UNRESOLVED = re.compile(r"(?:performer|term) '(.+?)'")


def unresolved_terms(result) -> tuple[str, ...]:
    """Terms whose lookup returned None, deduplicated, first-seen order.

    build.build reports them through BuiltSegment.comments lines shaped
    `row N: could not read performer '...'` -- parse those, do not
    re-run the lookups.
    """
    found: list[str] = []
    for built in result.segments:
        for comment in built.comments:
            match = _UNRESOLVED.search(comment)
            if match:
                term = match.group(1)
                if term not in found:
                    found.append(term)
    return tuple(found)


def propose_term(term, context_lines, provider):
    from wing_parser.classifier.matcher import Classification
    from wing_parser.classifier.provider import complete_json

    user = f"Term: {term!r}\nContext rows:\n" + "\n".join(context_lines)
    reply = complete_json(provider, SYSTEM_PROMPT, user, TERM_SCHEMA)
    kind = str(reply["kind"]).strip().casefold()
    score = min(1.0, max(0.0, float(reply["confidence"])))
    if not kind or kind == "unknown":
        return None
    return Classification(kind=kind, confidence=score, origin="g2b-assisted")


def offer_terms(terms, context_by_term, *, provider_factory, input_fn=input,
                print_fn=print, directory=None) -> int:
    from wing_parser.classifier import cache

    recorded = 0
    for term in terms:
        try:
            guess = propose_term(term, context_by_term.get(term, []), provider_factory())
        except Exception as exc:  # noqa: BLE001 - degrade like every model path
            print_fn(f"(term guessing unavailable: {exc})")
            return recorded
        if guess is None:
            continue
        answer = input_fn(f"Record '{term}' as {guess.kind}? [y/N]: ").strip().lower()
        if answer == "y":
            cache.remember(term, "cuesheet", guess, directory=directory)
            recorded += 1
    return recorded
