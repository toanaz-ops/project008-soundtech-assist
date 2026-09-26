"""classifier.yaml <-> vocabulary dataclass mapping, and the raw writes.

Split out of `vocabulary.py` (ToanAZ's standing preference for short,
single-responsibility files -- see that module's docstring for the
domain rules). This file owns everything that touches raw dict shapes:
the `SetEntry`/`TermEntry` dataclasses, parsing a shipped-default or a
user-written entry into one, the pure validation/diagnostic functions
that don't need a `Vocabulary` instance's own state, and mutating
`classifier.yaml`'s `cuesheet`/`cuesheet_sets` domains through
`cache.read_raw`/`cache.write_raw` -- the same atomic
temp-file-then-rename write `cache.py` already uses for
`channels`/`buses`. `vocabulary.Vocabulary` owns the domain algorithm
that DOES need instance state (nested-set expansion, cycle detection at
write time, merging defaults with a person's edits) and does every
validation check (known kinds, known sets, cycle detection) BEFORE
calling `put_set`/`put_term` here -- the write functions below trust
their caller and do no validation of their own.

W3 (spec, governs over an earlier draft of this module): diacritic/case
folding is for MATCHING identity only -- a stored/displayed key keeps
exactly what the person typed. So `set_from_user`/`term_from_user` do
NOT fold the key they return; `Vocabulary._merge` folds only to decide
IDENTITY (does this override's folded form match an existing default's?
does this write's folded form match an existing raw key's?), and
overwrites `.key` with the default's own authored key when it does (so
display doesn't flip depending on whether a term happens to be a
default's override or a fresh reset back to it).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wing_parser.classifier import cache
from wing_parser.showcontext.ingest import keywords


class UnknownKindError(ValueError):
    pass


class UnknownSetError(ValueError):
    pass


class CycleError(ValueError):
    def __init__(self, path: tuple[str, ...]) -> None:
        super().__init__("cycle: " + " → ".join(path))
        self.path = path


@dataclass(frozen=True)
class SetEntry:
    key: str
    label: str
    kinds: tuple[str, ...] = ()
    sets: tuple[str, ...] = ()
    origin: str = "default"
    shadows_default: bool = False
    deleted: bool = False

    @property
    def display_origin(self) -> str:
        if self.shadows_default and self.origin != "default":
            return "default, edited"
        return self.origin


@dataclass(frozen=True)
class TermEntry:
    key: str
    kinds: tuple[str, ...] = ()
    sets: tuple[str, ...] = ()
    ignore: bool = False
    match: str = "exact"
    origin: str = "default"
    shadows_default: bool = False
    deleted: bool = False

    @property
    def display_origin(self) -> str:
        if self.shadows_default and self.origin != "default":
            return "default, edited"
        return self.origin


# -- raw shape -> dataclass ---------------------------------------------------


def load_defaults(defaults_path: Path) -> tuple[dict, dict]:
    import yaml

    doc = yaml.safe_load(defaults_path.read_text(encoding="utf-8")) or {}
    return doc.get("sets") or {}, doc.get("terms") or {}


def set_from_default(key: str, raw: dict) -> SetEntry:
    # Authored key, unfolded (W3) -- Vocabulary._merge folds separately
    # to build the identity-keyed lookup dict.
    return SetEntry(
        key=key, label=str(raw.get("label", key)),
        kinds=tuple(raw.get("kinds", ())), sets=tuple(raw.get("sets", ())),
        origin="default",
    )


def set_from_user(key: str, raw: dict) -> SetEntry:
    if raw.get("deleted"):
        return SetEntry(key=key, label="", deleted=True, origin="manual")
    return SetEntry(
        key=key, label=str(raw.get("label", key)),
        kinds=tuple(raw.get("kinds", ())), sets=tuple(raw.get("sets", ())),
        origin=str(raw.get("origin", "manual")),
    )


def term_from_default(key: str, raw: dict) -> TermEntry:
    return TermEntry(
        key=key, kinds=tuple(raw.get("kinds", ())),
        sets=tuple(raw.get("sets", ())), ignore=bool(raw.get("ignore", False)),
        match=str(raw.get("match", "exact")), origin="default",
    )


def term_from_user(key: str, raw: dict) -> TermEntry:
    if raw.get("deleted"):
        return TermEntry(key=key, deleted=True, origin="manual")
    if "confidence" in raw:
        # Pre-wave-4 shape (guess.offer_terms -> cache.remember): read as
        # kinds: [x], match: exact (design spec S3.2) so it keeps its
        # meaning with no migration step.
        return TermEntry(
            key=key, kinds=(str(raw["kind"]),), match="exact",
            origin=str(raw.get("origin", "cache")),
        )
    return TermEntry(
        key=key, kinds=tuple(raw.get("kinds", ())),
        sets=tuple(raw.get("sets", ())), ignore=bool(raw.get("ignore", False)),
        match=str(raw.get("match", "exact")), origin=str(raw.get("origin", "manual")),
    )


# -- dataclass -> raw shape, written through cache's atomic path -------------


def _pop_matching(section: dict, key: str) -> None:
    """Remove every raw key in `section` whose folded identity matches
    `key`'s -- a raw key keeps whatever the person typed (W3), so the
    SAME logical entry can be on disk under a different spelling/case/
    diacritics than whatever string a later put/delete/reset call uses.
    Without this, put/delete/reset index the section by the exact string
    passed and silently miss the real entry (fix-round-1 CRITICAL 1)."""
    target = keywords.fold(key)
    for existing in [k for k in section if keywords.fold(k) == target]:
        del section[existing]


def put_set(directory: Path | None, key: str, *, label: str,
            kinds: tuple[str, ...] = (), sets: tuple[str, ...] = (),
            origin: str = "manual") -> None:
    doc = cache.read_raw(directory)
    section = doc.setdefault("cuesheet_sets", {})
    _pop_matching(section, key)
    section[key] = {"label": label, "kinds": list(kinds), "sets": list(sets), "origin": origin}
    cache.write_raw(doc, directory)


def put_term(directory: Path | None, key: str, *, kinds: tuple[str, ...] = (),
             sets: tuple[str, ...] = (), ignore: bool = False,
             match: str = "exact", origin: str = "manual") -> None:
    doc = cache.read_raw(directory)
    section = doc.setdefault("cuesheet", {})
    _pop_matching(section, key)
    entry: dict[str, Any] = {"match": match, "origin": origin}
    if ignore:
        entry["ignore"] = True
    else:
        if kinds:
            entry["kinds"] = list(kinds)
        if sets:
            entry["sets"] = list(sets)
    section[key] = entry
    cache.write_raw(doc, directory)


def delete(directory: Path | None, domain: str, key: str, *, had_default: bool) -> None:
    """Tombstone `key` in `domain` when a default of the same key exists
    (so a later app update cannot silently revive it); otherwise drop the
    entry outright -- there is nothing left for a default to shadow."""
    doc = cache.read_raw(directory)
    section = doc.setdefault(domain, {})
    _pop_matching(section, key)
    if had_default:
        section[key] = {"deleted": True}
    cache.write_raw(doc, directory)


def reset(directory: Path | None, domain: str, key: str) -> None:
    """Remove any override or tombstone for `key`, letting a default (if
    any) show through again."""
    doc = cache.read_raw(directory)
    section = doc.get(domain) or {}
    _pop_matching(section, key)
    cache.write_raw(doc, directory)


# -- write-time validation (pure; Vocabulary supplies the current state) ----


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
    `.sets()` so the Vocabulary window can show and let a person fix it."""
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
