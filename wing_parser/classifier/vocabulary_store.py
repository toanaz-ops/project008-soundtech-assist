"""classifier.yaml <-> vocabulary dataclass mapping, and the raw writes.

Split out of `vocabulary.py` (ToanAZ's standing preference for short,
single-responsibility files -- see that module's docstring for the
domain rules). This file owns everything that touches raw dict shapes:
the `SetEntry`/`TermEntry` dataclasses and the exceptions raised over
them, parsing a shipped-default or a user-written entry into one
(raising `MalformedEntryError` -- never `AttributeError`/`KeyError` --
when a hand-edit's shape cannot be parsed at all), and mutating
`classifier.yaml`'s `cuesheet`/`cuesheet_sets` domains through
`cache.read_raw`/`cache.write_raw` -- the same atomic
temp-file-then-rename write `cache.py` already uses for
`channels`/`buses`. The write functions below (`put_set`/`put_term`/
`delete`/`reset`) do no validation of their own -- `vocabulary.Vocabulary`
calls `vocabulary_checks`'s pure functions first and only calls into here
once a write has already passed; `vocabulary_checks.py` (not this file)
owns the actual cycle-detection/kind/set-validation algorithms and the
loader-side diagnostics, since those only need a `sets`/`terms` view,
never this module's I/O.

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
from wing_parser.classifier.matcher import HIGH
from wing_parser.showcontext.ingest import keywords


class UnknownKindError(ValueError):
    pass


class UnknownSetError(ValueError):
    pass


class CycleError(ValueError):
    def __init__(self, path: tuple[str, ...]) -> None:
        super().__init__("cycle: " + " → ".join(path))
        self.path = path


class MalformedEntryError(ValueError):
    """A hand-edited raw entry has a shape `set_from_user`/`term_from_user`
    cannot parse at all (not a mapping; an old-shape entry with
    `confidence:` but no `kind:`; a `kinds:`/`sets:` value that is a
    string instead of a list -- `tuple("speech.mc")` silently splits it
    into single characters otherwise). `Vocabulary._merge` catches this,
    skips the entry, and reports it via `.problems` -- the loader never
    raises (spec S3.2), no matter how a person hand-edited the file."""


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
    if not isinstance(raw, dict):
        raise MalformedEntryError(f"set {key!r}: not a mapping")
    if raw.get("deleted"):
        return SetEntry(key=key, label="", deleted=True, origin="manual")
    kinds, sets = raw.get("kinds", ()), raw.get("sets", ())
    if isinstance(kinds, str) or isinstance(sets, str):
        raise MalformedEntryError(f"set {key!r}: kinds/sets must be a list, not a string")
    return SetEntry(
        key=key, label=str(raw.get("label", key)),
        kinds=tuple(kinds), sets=tuple(sets),
        origin=str(raw.get("origin", "manual")),
    )


def term_from_default(key: str, raw: dict) -> TermEntry:
    return TermEntry(
        key=key, kinds=tuple(raw.get("kinds", ())),
        sets=tuple(raw.get("sets", ())), ignore=bool(raw.get("ignore", False)),
        match=str(raw.get("match", "exact")), origin="default",
    )


def term_from_user(key: str, raw: dict) -> TermEntry:
    if not isinstance(raw, dict):
        raise MalformedEntryError(f"term {key!r}: not a mapping")
    if raw.get("deleted"):
        return TermEntry(key=key, deleted=True, origin="manual")
    if "confidence" in raw:
        # Pre-wave-4 shape (guess.offer_terms -> cache.remember): read as
        # kinds: [x], match: exact (design spec S3.2) so it keeps its
        # meaning with no migration step -- INCLUDING a confidence below
        # matcher.HIGH. Before this module existed, build.py's old
        # resolve_fragment only trusted a remembered Classification when
        # matcher.is_confident() (confidence >= HIGH); a weak model guess
        # stayed a comment, never `expects:` (fix round 1, controller
        # ruling R1). Modelled here as kinds=() rather than dropping the
        # entry outright: it still identity-matches at match="exact" (so
        # it correctly shadows a default of the same key, if any), it
        # just contributes no kind, so keywords.match falls through to
        # the pattern matcher exactly as the pre-wave-4 lookup did.
        if "kind" not in raw:
            raise MalformedEntryError(f"term {key!r}: has confidence but no kind")
        confident = float(raw["confidence"]) >= HIGH
        return TermEntry(
            key=key, kinds=(str(raw["kind"]),) if confident else (), match="exact",
            origin=str(raw.get("origin", "cache")),
        )
    kinds, sets = raw.get("kinds", ()), raw.get("sets", ())
    if isinstance(kinds, str) or isinstance(sets, str):
        raise MalformedEntryError(f"term {key!r}: kinds/sets must be a list, not a string")
    return TermEntry(
        key=key, kinds=tuple(kinds), sets=tuple(sets),
        ignore=bool(raw.get("ignore", False)),
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

