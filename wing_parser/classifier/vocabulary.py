"""Editable cue-sheet vocabulary: sets, terms, defaults, overrides.

Two kinds of thing a person teaches this tool about a cue sheet (design
spec §3): a **set** (a named bundle of kinds, may nest other sets, F13)
and a **term** (a word/phrase pointing at kinds and/or sets, or at
`ignore`, F5). Defaults ship in `data/cuesheet_defaults.yaml`, never
edited at runtime; a person's own edits live in `classifier.yaml`'s
`cuesheet`/`cuesheet_sets` domains. An entry with the same folded key as
a default REPLACES it; `deleted: true` tombstones a default; `reset_*`
removes the override/tombstone and lets the default show through again.

Every kind is validated against `matcher.known_kinds("channels")`; every
named set must exist among the currently-visible (non-deleted) sets. Set
expansion is depth-first, first-seen, deduplicated; a cycle is refused
AT WRITE TIME (`CycleError`, naming the path) but tolerated -- expanded
once, never looped -- if one already reached disk by hand-editing
(`.problems` reports it instead; `.load()` never raises).

`SetEntry`/`TermEntry`, raw-shape parsing, and the raw `classifier.yaml`
writes live in `vocabulary_store.py`; the pure kind/set/cycle validation
and loader-side diagnostics live in `vocabulary_checks.py` (short,
single-responsibility files -- ToanAZ's standing preference). Both are
re-exported below where their names are part of this module's public
surface. This module holds the `Vocabulary` class itself: the state a
caller needs an instance for (merging defaults with a directory's
edits, nested-set expansion, supplying that state to the pure checks).
"""

from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from pathlib import Path

from wing_parser.classifier import cache
from wing_parser.classifier import vocabulary_checks as checks
from wing_parser.classifier import vocabulary_store as store
from wing_parser.classifier.matcher import known_kinds
from wing_parser.classifier.vocabulary_store import (
    CycleError,
    MalformedEntryError,
    SetEntry,
    TermEntry,
    UnknownKindError,
    UnknownSetError,
)
from wing_parser.showcontext.ingest import keywords

__all__ = [
    "CycleError", "MalformedEntryError", "SetEntry", "TermEntry",
    "UnknownKindError", "UnknownSetError", "Vocabulary",
]

_DEFAULTS_PATH = Path(__file__).resolve().parent / "data" / "cuesheet_defaults.yaml"


@lru_cache(maxsize=1)
def _shipped_defaults() -> tuple[dict, dict]:
    """Parsed once per process -- the shipped file never changes at
    runtime, so re-parsing it on every `Vocabulary._refresh()` (one per
    write) is pure waste."""
    return store.load_defaults(_DEFAULTS_PATH)


class Vocabulary:
    """His edits over the shipped defaults, sets expanded on demand."""

    def __init__(self, sets: dict[str, SetEntry], terms: dict[str, TermEntry],
                 default_set_keys: frozenset[str], default_term_keys: frozenset[str],
                 problems: tuple[str, ...], directory: Path | None = None) -> None:
        self._sets = sets
        self._terms = terms
        self._default_set_keys = default_set_keys
        self._default_term_keys = default_term_keys
        self._problems = problems
        self._directory = directory

    @classmethod
    def load(cls, directory: Path | None = None) -> "Vocabulary":
        sets, terms, default_set_keys, default_term_keys, problems = cls._merge(directory)
        return cls(sets, terms, default_set_keys, default_term_keys, problems, directory)

    @staticmethod
    def _merge(directory: Path | None):
        """Shipped defaults + this directory's own edits/tombstones, keyed
        by folded identity so an override lands on the right default
        regardless of the case/diacritics the person typed it in. An
        entry that shadows a default takes the DEFAULT's own authored key
        (W3: a stored/displayed key never folds) so display is stable
        whether the person is looking at the override or, later, at the
        reverted default -- only the identity check folds.

        A raw entry `set_from_user`/`term_from_user` cannot parse at all
        (`MalformedEntryError`) is skipped, not raised -- the loader
        never raises (spec S3.2) -- and reported in `.problems` naming
        the key, same as a parsed-but-otherwise-broken entry."""
        default_sets_raw, default_terms_raw = _shipped_defaults()
        sets = {keywords.fold(k): store.set_from_default(k, v) for k, v in default_sets_raw.items()}
        terms = {keywords.fold(k): store.term_from_default(k, v) for k, v in default_terms_raw.items()}
        default_set_keys = frozenset(sets)
        default_term_keys = frozenset(terms)

        load_problems: list[str] = []
        doc = cache.read_raw(directory)
        for key, raw in (doc.get("cuesheet_sets") or {}).items():
            folded = keywords.fold(key)
            try:
                entry = store.set_from_user(key, raw)
            except MalformedEntryError as exc:
                load_problems.append(str(exc))
                continue
            if not entry.deleted and folded in default_set_keys:
                entry = replace(entry, key=sets[folded].key, shadows_default=True)
            sets[folded] = entry
        for key, raw in (doc.get("cuesheet") or {}).items():
            folded = keywords.fold(key)
            try:
                entry = store.term_from_user(key, raw)
            except MalformedEntryError as exc:
                load_problems.append(str(exc))
                continue
            if not entry.deleted and folded in default_term_keys:
                entry = replace(entry, key=terms[folded].key, shadows_default=True)
            terms[folded] = entry

        known = frozenset(known_kinds("channels"))
        problems = tuple(load_problems) + checks.compute_problems(sets, terms, known)
        return sets, terms, default_set_keys, default_term_keys, problems

    def _refresh(self) -> None:
        """Re-merge from disk after a write so a second call on the SAME
        instance (no reload in between) sees it -- e.g. one put_set
        naming another in its own `sets=` right after."""
        sets, terms, default_set_keys, default_term_keys, problems = self._merge(self._directory)
        self._sets = sets
        self._terms = terms
        self._default_set_keys = default_set_keys
        self._default_term_keys = default_term_keys
        self._problems = problems

    # -- reading --------------------------------------------------------

    @property
    def problems(self) -> tuple[str, ...]:
        """Loader-side diagnostics (spec S3.2): a malformed raw entry, an
        unknown kind, an unknown/missing set, or a set cycle found on
        disk -- never raised, so a hand-edit mistake never breaks every
        caller of `.load()`. See `vocabulary_checks.compute_problems`."""
        return self._problems

    def sets(self) -> tuple[SetEntry, ...]:
        return tuple(sorted((s for s in self._sets.values() if not s.deleted),
                            key=lambda s: s.key))

    def terms(self) -> tuple[TermEntry, ...]:
        return tuple(sorted((t for t in self._terms.values() if not t.deleted),
                            key=lambda t: t.key))

    def deleted_sets(self) -> tuple[SetEntry, ...]:
        """Tombstoned defaults (fix round 1, I1): the Vocabulary window
        shows these as their own greyed rows so Reset is reachable
        without going around the UI. `store.delete()` only ever writes a
        tombstone when a default existed under that key -- a manual-only
        delete drops the raw entry outright (nothing left to revert to),
        so every entry returned here is a deleted default, never a
        deleted manual-only entry."""
        return tuple(sorted((s for s in self._sets.values() if s.deleted),
                            key=lambda s: s.key))

    def deleted_terms(self) -> tuple[TermEntry, ...]:
        return tuple(sorted((t for t in self._terms.values() if t.deleted),
                            key=lambda t: t.key))

    def has_default_set(self, key: str) -> bool:
        """Whether `key` has a shipped default underneath -- Reset only
        makes sense when this is true (fix round 1: reset_set on a
        manual-only entry has nothing to fall back to and just deletes it
        outright, which a "Reset to default" button must never do
        silently)."""
        return self._had_default_set(key)

    def has_default_term(self, key: str) -> bool:
        return self._had_default_term(key)

    def expand_set(self, key: str, _visiting: frozenset[str] = frozenset(),
                   _known: frozenset[str] | None = None) -> tuple[str, ...]:
        """Depth-first, first-seen order: a nested set's own kinds come
        before the kinds this set adds on top of it. A hand-edited set's
        kind that `patterns.yaml` cannot produce is dropped here (fix
        round 2) rather than passed through to every term naming this
        set -- `.problems` still names the set so it can be fixed."""
        if _known is None:
            _known = frozenset(known_kinds("channels"))
        folded = keywords.fold(key)
        entry = self._sets.get(folded)
        if entry is None or entry.deleted or folded in _visiting:
            return ()
        visiting = _visiting | {folded}
        kinds: list[str] = []
        for nested in entry.sets:
            for kind in self.expand_set(nested, visiting, _known):
                if kind not in kinds:
                    kinds.append(kind)
        for kind in entry.kinds:
            if kind in _known and kind not in kinds:
                kinds.append(kind)
        return tuple(kinds)

    def effective(self) -> tuple[keywords.Term, ...]:
        """Every visible term, sets expanded -- except a term whose OWN
        kinds include one `patterns.yaml` cannot produce, which is
        excluded here (and named in `.problems`) rather than handed to
        the matcher with a kind it will never recognise. A set-borrowed
        unknown kind is already dropped inside `expand_set`."""
        known = frozenset(known_kinds("channels"))
        out = []
        for term in self.terms():
            if any(k not in known for k in term.kinds):
                continue
            kinds: list[str] = list(term.kinds)
            for set_key in term.sets:
                for kind in self.expand_set(set_key, _known=known):
                    if kind not in kinds:
                        kinds.append(kind)
            out.append(keywords.Term(key=term.key, kinds=tuple(kinds),
                                     ignored=term.ignore, match=term.match))
        return tuple(out)

    # -- validation (thin: supplies this instance's state to the pure
    # checks in vocabulary_checks.py) -----------------------------------

    def _check_kinds(self, key: str, kinds) -> None:
        checks.check_kinds(key, kinds, frozenset(known_kinds("channels")))

    def _check_sets(self, key: str, set_keys) -> None:
        visible = frozenset(k for k, s in self._sets.items() if not s.deleted)
        checks.check_sets(key, set_keys, visible)

    def _check_cycle(self, key: str, nested_sets: tuple[str, ...]) -> None:
        checks.check_cycle(self._sets, key, nested_sets)

    def dry_run_set(self, key: str, *, kinds: tuple[str, ...] = (),
                    sets: tuple[str, ...] = ()) -> tuple[str, ...]:
        """Every problem `put_set(key, ...)` would raise, without writing --
        vocab_changes.validate calls this to decide whether an AI-proposed
        set change could be written. Same order as put_set: an unknown
        kind/set is worth reporting even when a cycle is ALSO present, but
        a cycle check only makes sense once kinds/sets are themselves
        known-good (check_cycle walks `sets`, which an unknown-set problem
        already flagged as untrustworthy)."""
        problems: list[str] = []
        try:
            self._check_kinds(key, kinds)
        except UnknownKindError as exc:
            problems.append(str(exc))
        try:
            self._check_sets(key, sets)
        except UnknownSetError as exc:
            problems.append(str(exc))
        if not problems:
            try:
                self._check_cycle(key, sets)
            except CycleError as exc:
                problems.append(str(exc))
        return tuple(problems)

    def dry_run_term(self, key: str, *, kinds: tuple[str, ...] = (),
                     sets: tuple[str, ...] = (), ignore: bool = False) -> tuple[str, ...]:
        """Every problem `put_term(key, ...)` would raise, without writing.
        The two `put_term` shape rules (ignore XOR kinds/sets; at least one
        of them) are reported as their own single problem, same wording
        `put_term` itself raises, before the per-kind/per-set checks run."""
        if ignore and (kinds or sets):
            return (f"term {key!r}: ignore: true OR kinds/sets, not both",)
        if not ignore and not kinds and not sets:
            return (f"term {key!r}: needs kinds and/or sets, or ignore: true",)
        problems: list[str] = []
        try:
            self._check_kinds(key, kinds)
        except UnknownKindError as exc:
            problems.append(str(exc))
        try:
            self._check_sets(key, sets)
        except UnknownSetError as exc:
            problems.append(str(exc))
        return tuple(problems)

    # -- writing (validated here, mutated in vocabulary_store.py) -----------

    def put_set(self, key: str, *, label: str, kinds: tuple[str, ...] = (),
                sets: tuple[str, ...] = (), origin: str = "manual") -> None:
        self._check_kinds(key, kinds)
        self._check_sets(key, sets)
        self._check_cycle(key, sets)
        store.put_set(self._directory, key, label=label, kinds=kinds, sets=sets, origin=origin)
        self._refresh()

    def put_term(self, key: str, *, kinds: tuple[str, ...] = (),
                 sets: tuple[str, ...] = (), ignore: bool = False,
                 match: str = "exact", origin: str = "manual") -> None:
        if ignore and (kinds or sets):
            raise ValueError(f"term {key!r}: ignore: true OR kinds/sets, not both")
        if not ignore and not kinds and not sets:
            raise ValueError(f"term {key!r}: needs kinds and/or sets, or ignore: true")
        self._check_kinds(key, kinds)
        self._check_sets(key, sets)
        store.put_term(self._directory, key, kinds=kinds, sets=sets, ignore=ignore,
                        match=match, origin=origin)
        self._refresh()

    def delete_set(self, key: str) -> None:
        store.delete(self._directory, "cuesheet_sets", key, had_default=self._had_default_set(key))
        self._refresh()

    def delete_term(self, key: str) -> None:
        store.delete(self._directory, "cuesheet", key, had_default=self._had_default_term(key))
        self._refresh()

    def _had_default_set(self, key: str) -> bool:
        # From the shipped defaults' own (static) key set, NOT from the
        # currently-merged entry -- once deleted, that entry IS the
        # tombstone, so deciding from it would resurrect the default on a
        # second delete (fix-round-1 IMPORTANT 2).
        return keywords.fold(key) in self._default_set_keys

    def _had_default_term(self, key: str) -> bool:
        return keywords.fold(key) in self._default_term_keys

    def reset_set(self, key: str) -> None:
        store.reset(self._directory, "cuesheet_sets", key)
        self._refresh()

    def reset_term(self, key: str) -> None:
        store.reset(self._directory, "cuesheet", key)
        self._refresh()
