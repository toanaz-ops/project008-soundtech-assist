"""Resolve a hand-typed token against a closed vocabulary.

Repairing a near-miss against a closed vocabulary is not the same act as
mapping free text: this one is decidable, and every failure is visible.
The radius is a measurement, not a preference -- see the 2026-08-17
input-pipelines spec §3.1. The channel vocabulary's minimum pairwise
distance is 2, which detects a single error but cannot correct one, so
repair happens at radius 1 and only when exactly one candidate sits
there. A tie is refused, never resolved by picking.
"""

from __future__ import annotations

from dataclasses import dataclass

KNOWN_ACTIONS: tuple[str, ...] = ("open", "close", "up", "down", "recall")

# Below this length a single edit is too large a fraction of the token to
# call a typo. No channel kind is this short (the shortest is
# `drums.pad`, 9), but `fx` in the buses domain is, and so is `up`.
MIN_REPAIR_LENGTH = 4


@dataclass(frozen=True)
class Resolution:
    value: str
    original: str
    repaired: bool


def normalise(token: str) -> str:
    """Case, padding and separator differences are not guesses.

    The result is either a member of the vocabulary or it is not, so
    this collapses without needing to be reported.
    """
    cleaned = token.strip().lower()
    for separator in ("-", "_", " ", "\t"):
        cleaned = cleaned.replace(separator, ".")
    while ".." in cleaned:
        cleaned = cleaned.replace("..", ".")
    return cleaned.strip(".")


def levenshtein(a: str, b: str) -> int:
    """Edit distance, counting an adjacent transposition as one step.

    This is Damerau-Levenshtein (optimal string alignment), not plain
    Levenshtein. Plain insert/delete/substitute distance scores a
    transposition such as 'kyes' for 'keys' as 2 (two substitutions),
    which would refuse to repair one of the most common typing
    mistakes -- swapping two adjacent keys -- even though it is
    unambiguous. Confirmed 2026-08-17: transposition-awareness does not
    change the channel vocabulary's minimum pairwise distance (still 2,
    still speech.lav <-> speech.qa and speech.mc <-> speech.qa), so the
    radius-1 safety argument in this module's docstring holds under
    this metric too.
    """
    la, lb = len(a), len(b)
    distances = [[0] * (lb + 1) for _ in range(la + 1)]
    for i in range(la + 1):
        distances[i][0] = i
    for j in range(lb + 1):
        distances[0][j] = j
    for i in range(1, la + 1):
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            distances[i][j] = min(
                distances[i - 1][j] + 1,
                distances[i][j - 1] + 1,
                distances[i - 1][j - 1] + cost,
            )
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                distances[i][j] = min(distances[i][j], distances[i - 2][j - 2] + 1)
    return distances[la][lb]


def resolve(token: str, vocabulary: tuple[str, ...], *, what: str) -> Resolution:
    cleaned = normalise(token)
    if cleaned in vocabulary:
        return Resolution(value=cleaned, original=token, repaired=False)

    if len(cleaned) >= MIN_REPAIR_LENGTH:
        near = sorted(word for word in vocabulary if levenshtein(cleaned, word) == 1)
        if len(near) == 1:
            return Resolution(value=near[0], original=token, repaired=True)
        if len(near) > 1:
            raise ValueError(
                f"unknown {what} {token!r}: did you mean "
                + " or ".join(repr(word) for word in near)
                + "? One edit away from more than one, so it is not repaired."
            )

    raise ValueError(
        f"unknown {what} {token!r}; expected one of: " + ", ".join(vocabulary)
    )
