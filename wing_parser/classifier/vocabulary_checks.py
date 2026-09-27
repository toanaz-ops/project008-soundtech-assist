"""Pure validation and loader-side diagnostics for the cue-sheet vocabulary.

No I/O -- every function here takes the state it needs as a plain
argument (a `sets`/`terms` dict, a `known_kinds` frozenset) and either
raises one of `vocabulary_store`'s exceptions (write-time checks, called
by `Vocabulary` before it writes) or returns data (loader-side
diagnostics, called by `Vocabulary.load()`/`_refresh()` -- these never
raise; spec S3.2 says the loader never raises, no matter how a person
hand-edited `classifier.yaml`).

Split out of `vocabulary_store.py` once that file grew past its own
short-file budget: that module owns raw-shape parsing and the raw
writes; this one owns everything that only READS a merged
`sets`/`terms` view to validate or diagnose it.
"""

from __future__ import annotations

from wing_parser.classifier.vocabulary_store import (
    CycleError,
    SetEntry,
    TermEntry,
    UnknownKindError,
    UnknownSetError,
)
from wing_parser.showcontext.ingest import keywords

# -- write-time validation (Vocabulary calls these before it writes) --------


def check_kinds(key: str, kinds, known_kinds: frozenset[str]) -> None:
    unknown = [k for k in kinds if k not in known_kinds]
    if unknown:
        raise UnknownKindError(f"{key!r}: unknown kind(s) {unknown}")


def check_sets(key: str, set_keys, visible_set_identities: frozenset[str]) -> None:
    # `visible_set_identities` is folded dict keys of non-deleted sets,
    # NOT their (possibly unfolded, W3) display key -- fix-round-1
    # IMPORTANT 3.
    unknown = [s for s in set_keys if keywords.fold(s) not in visible_set_identities]
    if unknown:
        raise UnknownSetError(f"{key!r}: no such set(s) {unknown}")


def check_cycle(sets: dict[str, SetEntry], key: str, nested_sets: tuple[str, ...]) -> None:
    """Refuse a cycle THROUGH `key` (naming the path); tolerate -- not
    raise -- a cycle already on disk that this write does not join
    (fix-round-1 IMPORTANT 1): `seen` stops `walk` from looping forever
    on that pre-existing cycle instead of ever reaching `key` again."""
    folded_key = keywords.fold(key)

    def display(folded: str) -> str:
        if folded == folded_key:
            return key
        entry = sets.get(folded)
        return entry.key if entry is not None else folded

    def walk(current: str, path: tuple[str, ...], seen: frozenset[str]) -> None:
        if current == folded_key:
            raise CycleError(tuple(display(p) for p in path) + (display(current),))
        if current in seen:
            return
        seen = seen | {current}
        entry = sets.get(current)
        if entry is None or entry.deleted:
            return
        for nested in entry.sets:
            walk(keywords.fold(nested), path + (current,), seen)

    for nested in nested_sets:
        walk(keywords.fold(nested), (folded_key,), frozenset())


# -- loader-side diagnostics (spec S3.2: never raise on load, report) -------


def find_set_cycles(sets: dict[str, SetEntry]) -> list[tuple[str, ...]]:
    """Every distinct cycle among non-deleted sets, one entry per cycle
    regardless of which node the scan happens to start from (deduped by
    the frozenset of nodes on the cycle). `sets` is keyed by folded
    identity; a returned path is folded-identity strings, tolerant of
    the cycle whether or not it is the one a caller is about to join."""
    found: list[tuple[str, ...]] = []
    seen_identities: set[frozenset[str]] = set()

    def walk(current: str, path: tuple[str, ...]) -> None:
        if current in path:
            idx = path.index(current)
            cycle_path = path[idx:] + (current,)
            identity = frozenset(path[idx:])
            if identity not in seen_identities:
                seen_identities.add(identity)
                found.append(cycle_path)
            return
        entry = sets.get(current)
        if entry is None or entry.deleted:
            return
        for nested in entry.sets:
            walk(keywords.fold(nested), path + (current,))

    for start in sorted(sets):
        walk(start, ())
    return found


def compute_problems(sets: dict[str, SetEntry], terms: dict[str, TermEntry],
                      known_kinds: frozenset[str]) -> tuple[str, ...]:
    """Diagnostics for a hand-edited `classifier.yaml`: an unknown kind or
    an unknown/missing set, naming the entry's own display key, plus one
    message per distinct set cycle. Never raised -- `Vocabulary.load()`
    always succeeds; a broken term still resolves to its remaining kinds
    (spec S3.2) and a broken term/set is still visible via `.terms()`/
    `.sets()` so the Vocabulary window can show and let a person fix it.
    (Malformed-shape entries that could not even be parsed into a
    `SetEntry`/`TermEntry` at all are reported separately by
    `Vocabulary._merge`, since by the time they would reach here they no
    longer exist to inspect.)"""
    visible_sets = {k for k, s in sets.items() if not s.deleted}
    problems: list[str] = []

    for term in terms.values():
        if term.deleted:
            continue
        unknown_kinds = [k for k in term.kinds if k not in known_kinds]
        if unknown_kinds:
            problems.append(f"term {term.key!r}: unknown kind(s) {unknown_kinds}")
        unknown_sets = [s for s in term.sets if keywords.fold(s) not in visible_sets]
        if unknown_sets:
            problems.append(f"term {term.key!r}: unknown set(s) {unknown_sets}")

    for entry in sets.values():
        if entry.deleted:
            continue
        unknown_kinds = [k for k in entry.kinds if k not in known_kinds]
        if unknown_kinds:
            problems.append(f"set {entry.key!r}: unknown kind(s) {unknown_kinds}")
        unknown_sets = [s for s in entry.sets if keywords.fold(s) not in visible_sets]
        if unknown_sets:
            problems.append(f"set {entry.key!r}: unknown set(s) {unknown_sets}")

    for cycle in find_set_cycles(sets):
        problems.append("set cycle: " + " → ".join(sets[node].key for node in cycle))

    return tuple(problems)
