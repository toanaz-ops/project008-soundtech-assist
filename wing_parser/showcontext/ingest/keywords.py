"""Fold Vietnamese text and match it against a closed set of terms.

Spec §3.4-3.5. `fold()` is the ONE diacritic-stripping function this wave
uses -- `classifier/normalize.py:clean()` is a shallower, pre-existing
function (casefold + whitespace only) used by the "channels"/"buses"
domains and left untouched; conflating the two would silently change how
console-strip names classify.

`match()` implements steps 1-2 of the lookup order (design spec S3.3):
whole-fragment equality against `match="exact"` terms, then whole-word
substring scanning against `match="word"` terms. Step 3 (patterns.yaml)
and step 4 (give up) are `build.resolve_fragment`'s job, not this
module's -- this file does no I/O and knows nothing about a console
strip or a scene.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class Term:
    """One resolved vocabulary entry. `key` is kept as originally typed
    (not folded) so a caller can still show it; every comparison folds
    both sides through `fold()` at match time."""

    key: str
    kinds: tuple[str, ...]
    ignored: bool
    match: str  # "exact" | "word"


@dataclass(frozen=True)
class Resolution:
    kinds: tuple[str, ...]
    ignored: bool


def fold(text: str) -> str:
    """NFC -> casefold -> strip combining marks -> đ/Đ -> d -> punctuation
    to space -> collapse whitespace (design spec S3.4).

    Casefold runs BEFORE the NFD decomposition that exposes combining
    marks, so "BLĐ" and "bld" both end up "bld": casefold already lowers
    "Đ" to "đ", and "đ" (U+0111) has no NFD decomposition of its own --
    it is a distinct Latin letter, not a base letter plus a combining
    stroke -- which is why it needs its own explicit replace after the
    generic combining-mark strip removes tone marks.
    """
    if not text:
        return ""
    normalised = unicodedata.normalize("NFC", text)
    cased = normalised.casefold()
    decomposed = unicodedata.normalize("NFD", cased)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    recomposed = unicodedata.normalize("NFC", stripped).replace("đ", "d")
    despaced = _PUNCTUATION.sub(" ", recomposed)
    return _WHITESPACE.sub(" ", despaced).strip()


def _contains_word(haystack: str, needle: str) -> bool:
    """Is folded `needle` a whole-word (or whole-phrase) hit in `haystack`?

    Both are already folded by the caller. `re.escape` keeps a
    multi-word needle's internal space literal, and the look-around
    bounds match a single word OR a phrase without over-matching inside
    a longer word ("band" must not hit "bandana", spec S3.4).
    """
    if not needle:
        return False
    pattern = r"(?<!\w)" + re.escape(needle) + r"(?!\w)"
    return re.search(pattern, haystack) is not None


def match(text: str, terms: Sequence[Term]) -> Resolution:
    """Steps 1-2 of the lookup order (S3.3). Empty, non-ignored when
    neither step hits -- the caller tries patterns.yaml next."""
    folded_text = fold(text)
    if not folded_text:
        return Resolution((), False)

    for term in terms:
        if term.match == "exact" and fold(term.key) == folded_text:
            return Resolution(term.kinds, term.ignored)

    word_hits = [
        term for term in terms
        if term.match == "word" and _contains_word(folded_text, fold(term.key))
    ]
    if not word_hits:
        return Resolution((), False)

    # Longest-wins containment (S3.5): drop a hit whose folded key is a
    # proper substring of a longer hit's folded key.
    kept = []
    for term in word_hits:
        folded_key = fold(term.key)
        if any(
            folded_key != fold(other.key) and folded_key in fold(other.key)
            for other in word_hits
        ):
            continue
        kept.append(term)

    kinds: list[str] = []
    any_non_ignore = False
    for term in kept:
        if term.ignored:
            continue
        any_non_ignore = True
        for kind in term.kinds:
            if kind not in kinds:
                kinds.append(kind)

    if any_non_ignore:
        return Resolution(tuple(kinds), False)
    if kept:
        return Resolution((), True)  # ignore wins only when nothing else matched
    return Resolution((), False)
