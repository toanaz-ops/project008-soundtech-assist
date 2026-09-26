"""Editable cue-sheet vocabulary: sets, terms, defaults, overrides.

Two kinds of thing a person teaches this tool about a cue sheet (design
spec §3):

* a **set** -- a named bundle of kinds ("Drum kit" is seven drum kinds),
  which may nest other sets (Band contains Drum kit, F13);
* a **term** -- a word or phrase from a real running order, pointing at
  one or more kinds and/or sets, or at `ignore` (F5).

Defaults ship in `data/cuesheet_defaults.yaml`, never edited at runtime.
A person's own edits live in `classifier.yaml`'s `cuesheet` (terms) and
`cuesheet_sets` (sets) domains. An entry there with the same folded key
as a default REPLACES it; `deleted: true` tombstones a default so a
later app update cannot bring it back; `reset_*` removes the override or
tombstone and lets the default show through again.

Every kind is validated against `matcher.known_kinds("channels")` --
`expects:` refuses anything else (ROADMAP §5 item 7) -- and every named
set must exist among the currently-visible (non-deleted) sets. A set may
nest another; expansion is depth-first, first-seen order, deduplicated,
and a cycle is refused AT WRITE TIME (`CycleError`, naming the path) but
tolerated -- expanded once, never looped -- if one already reached disk
by hand-editing, because `expand_set` also runs at ordinary load time,
where raising would break every fragment behind the cycle, not just the
one entry that is wrong.

The `SetEntry`/`TermEntry` dataclasses, the raw-shape <-> dataclass
parsing, and the raw `classifier.yaml` writes all live in
`vocabulary_store.py` (ToanAZ's standing preference for short,
single-responsibility files) and are re-exported below so a caller only
ever needs `from wing_parser.classifier import vocabulary as vocab`.
This module owns the domain algorithm: merging defaults with a person's
edits, nested-set expansion, cycle detection, and validation -- each of
which needs this instance's own state (`self._sets`, `self.sets()`), so
it stays here rather than in the (stateless) store.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from wing_parser.classifier import cache
from wing_parser.classifier.matcher import known_kinds
from wing_parser.classifier.vocabulary_store import (
    CycleError,
    SetEntry,
    TermEntry,
    UnknownKindError,
    UnknownSetError,
    delete,
    load_defaults,
    put_set,
    put_term,
    reset,
    set_from_default,
    set_from_user,
    term_from_default,
    term_from_user,
)
from wing_parser.showcontext.ingest import keywords

__all__ = [
    "CycleError", "SetEntry", "TermEntry", "UnknownKindError", "UnknownSetError",
    "Vocabulary",
]

_DEFAULTS_PATH = Path(__file__).resolve().parent / "data" / "cuesheet_defaults.yaml"


class Vocabulary:
    """His edits over the shipped defaults, sets expanded on demand."""

    def __init__(self, sets: dict[str, SetEntry], terms: dict[str, TermEntry],
                 directory: Path | None = None) -> None:
        self._sets = sets
        self._terms = terms
        self._directory = directory

    @classmethod
    def load(cls, directory: Path | None = None) -> "Vocabulary":
        sets, terms = cls._merge(directory)
        return cls(sets, terms, directory)

    @staticmethod
    def _merge(directory: Path | None) -> tuple[dict[str, SetEntry], dict[str, TermEntry]]:
        """Shipped defaults + this directory's own edits/tombstones, keyed
        by folded identity so an override lands on the right default
        regardless of the case/diacritics the person typed it in."""
        default_sets, default_terms = load_defaults(_DEFAULTS_PATH)
        sets = {keywords.fold(k): set_from_default(k, v) for k, v in default_sets.items()}
        terms = {keywords.fold(k): term_from_default(k, v) for k, v in default_terms.items()}
        default_set_keys = frozenset(sets)
        default_term_keys = frozenset(terms)

        doc = cache.read_raw(directory)
        for key, raw in (doc.get("cuesheet_sets") or {}).items():
            folded = keywords.fold(key)
            entry = set_from_user(key, raw)
            if not entry.deleted and folded in default_set_keys:
                entry = replace(entry, shadows_default=True)
            sets[folded] = entry
        for key, raw in (doc.get("cuesheet") or {}).items():
            folded = keywords.fold(key)
            entry = term_from_user(key, raw)
            if not entry.deleted and folded in default_term_keys:
                entry = replace(entry, shadows_default=True)
            terms[folded] = entry
        return sets, terms

    def _refresh(self) -> None:
        """Re-merge from disk after a write so a second call on the SAME
        instance (no reload in between) sees it -- e.g. one put_set
        naming another in its own `sets=` right after."""
        self._sets, self._terms = self._merge(self._directory)

    # -- reading --------------------------------------------------------

    def sets(self) -> tuple[SetEntry, ...]:
        return tuple(sorted((s for s in self._sets.values() if not s.deleted),
                            key=lambda s: s.key))

    def terms(self) -> tuple[TermEntry, ...]:
        return tuple(sorted((t for t in self._terms.values() if not t.deleted),
                            key=lambda t: t.key))

    def expand_set(self, key: str, _visiting: frozenset[str] = frozenset()) -> tuple[str, ...]:
        """Depth-first, first-seen order: a nested set's own kinds come
        before the kinds this set adds on top of it."""
        folded = keywords.fold(key)
        entry = self._sets.get(folded)
        if entry is None or entry.deleted or folded in _visiting:
            return ()
        visiting = _visiting | {folded}
        kinds: list[str] = []
        for nested in entry.sets:
            for kind in self.expand_set(nested, visiting):
                if kind not in kinds:
                    kinds.append(kind)
        for kind in entry.kinds:
            if kind not in kinds:
                kinds.append(kind)
        return tuple(kinds)

    def effective(self) -> tuple[keywords.Term, ...]:
        out = []
        for term in self.terms():
            kinds: list[str] = list(term.kinds)
            for set_key in term.sets:
                for kind in self.expand_set(set_key):
                    if kind not in kinds:
                        kinds.append(kind)
            out.append(keywords.Term(key=term.key, kinds=tuple(kinds),
                                     ignored=term.ignore, match=term.match))
        return tuple(out)

    # -- validation (needs this instance's own state) ----------------------

    def _check_kinds(self, kinds) -> None:
        known = set(known_kinds("channels"))
        unknown = [k for k in kinds if k not in known]
        if unknown:
            raise UnknownKindError(f"unknown kind(s) {unknown}")

    def _check_sets(self, set_keys) -> None:
        visible = {s.key for s in self.sets()}
        unknown = [s for s in set_keys if keywords.fold(s) not in visible]
        if unknown:
            raise UnknownSetError(f"no such set(s) {unknown}")

    def _check_cycle(self, key: str, nested_sets: tuple[str, ...]) -> None:
        folded_key = keywords.fold(key)

        def walk(current: str, path: tuple[str, ...]) -> None:
            if current == folded_key:
                raise CycleError(path + (current,))
            entry = self._sets.get(current)
            if entry is None or entry.deleted:
                return
            for nested in entry.sets:
                walk(keywords.fold(nested), path + (current,))

        for nested in nested_sets:
            walk(keywords.fold(nested), (folded_key,))

    # -- writing (validated here, mutated in vocabulary_store.py) -----------

    def put_set(self, key: str, *, label: str, kinds: tuple[str, ...] = (),
                sets: tuple[str, ...] = (), origin: str = "manual") -> None:
        self._check_kinds(kinds)
        self._check_sets(sets)
        self._check_cycle(key, sets)
        put_set(self._directory, key, label=label, kinds=kinds, sets=sets, origin=origin)
        self._refresh()

    def put_term(self, key: str, *, kinds: tuple[str, ...] = (),
                 sets: tuple[str, ...] = (), ignore: bool = False,
                 match: str = "word", origin: str = "manual") -> None:
        if ignore and (kinds or sets):
            raise ValueError("a term is ignore: true OR kinds/sets, not both")
        self._check_kinds(kinds)
        self._check_sets(sets)
        put_term(self._directory, key, kinds=kinds, sets=sets, ignore=ignore,
                  match=match, origin=origin)
        self._refresh()

    def delete_set(self, key: str) -> None:
        delete(self._directory, "cuesheet_sets", key, had_default=self._had_default_set(key))
        self._refresh()

    def delete_term(self, key: str) -> None:
        delete(self._directory, "cuesheet", key, had_default=self._had_default_term(key))
        self._refresh()

    def _had_default_set(self, key: str) -> bool:
        folded = keywords.fold(key)
        entry = self._sets.get(folded)
        return entry is not None and (entry.origin == "default" or entry.shadows_default)

    def _had_default_term(self, key: str) -> bool:
        folded = keywords.fold(key)
        entry = self._terms.get(folded)
        return entry is not None and (entry.origin == "default" or entry.shadows_default)

    def reset_set(self, key: str) -> None:
        reset(self._directory, "cuesheet_sets", key)
        self._refresh()

    def reset_term(self, key: str) -> None:
        reset(self._directory, "cuesheet", key)
        self._refresh()
