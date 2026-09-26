"""classifier.yaml <-> vocabulary dataclass mapping, and the raw writes.

Split out of `vocabulary.py` (ToanAZ's standing preference for short,
single-responsibility files -- see that module's docstring for the
domain rules). This file owns everything that touches raw dict shapes:
the `SetEntry`/`TermEntry` dataclasses, parsing a shipped-default or a
user-written entry into one, and mutating `classifier.yaml`'s
`cuesheet`/`cuesheet_sets` domains through `cache.read_raw`/
`cache.write_raw` -- the same atomic temp-file-then-rename write
`cache.py` already uses for `channels`/`buses`. `vocabulary.Vocabulary`
owns the domain algorithm (nested-set expansion, cycle detection,
merging defaults with a person's edits) and does every validation check
(known kinds, known sets, cycle detection) BEFORE calling `put_set`/
`put_term` here -- the write functions below trust their caller and do
no validation of their own.
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
        super().__init__("cycle: " + " -> ".join(path))
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
    match: str = "word"
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
    # Key kept exactly as ToanAZ typed it in cuesheet_defaults.yaml (not
    # folded) so the Vocabulary window can show it with its real
    # diacritics/case -- the caller that builds the lookup dict keyed by
    # identity folds separately (Vocabulary.load). A *user* entry (below)
    # folds instead: arbitrary input needs normalizing onto the same
    # identity a default already occupies (S3.2's "same folded key").
    return SetEntry(
        key=key, label=str(raw.get("label", key)),
        kinds=tuple(raw.get("kinds", ())), sets=tuple(raw.get("sets", ())),
        origin="default",
    )


def set_from_user(key: str, raw: dict) -> SetEntry:
    if raw.get("deleted"):
        return SetEntry(key=keywords.fold(key), label="", deleted=True, origin="manual")
    return SetEntry(
        key=keywords.fold(key), label=str(raw.get("label", key)),
        kinds=tuple(raw.get("kinds", ())), sets=tuple(raw.get("sets", ())),
        origin=str(raw.get("origin", "manual")),
    )


def term_from_default(key: str, raw: dict) -> TermEntry:
    # Unfolded, same reasoning as set_from_default above.
    return TermEntry(
        key=key, kinds=tuple(raw.get("kinds", ())),
        sets=tuple(raw.get("sets", ())), ignore=bool(raw.get("ignore", False)),
        match=str(raw.get("match", "word")), origin="default",
    )


def term_from_user(key: str, raw: dict) -> TermEntry:
    if raw.get("deleted"):
        return TermEntry(key=keywords.fold(key), deleted=True, origin="manual")
    if "confidence" in raw:
        # Pre-wave-4 shape (guess.offer_terms -> cache.remember): read as
        # kinds: [x], match: exact (design spec S3.2) so it keeps its
        # meaning with no migration step.
        return TermEntry(
            key=keywords.fold(key), kinds=(str(raw["kind"]),), match="exact",
            origin=str(raw.get("origin", "cache")),
        )
    return TermEntry(
        key=keywords.fold(key), kinds=tuple(raw.get("kinds", ())),
        sets=tuple(raw.get("sets", ())), ignore=bool(raw.get("ignore", False)),
        match=str(raw.get("match", "word")), origin=str(raw.get("origin", "manual")),
    )


# -- dataclass -> raw shape, written through cache's atomic path -------------


def put_set(directory: Path | None, key: str, *, label: str,
            kinds: tuple[str, ...] = (), sets: tuple[str, ...] = (),
            origin: str = "manual") -> None:
    doc = cache.read_raw(directory)
    doc.setdefault("cuesheet_sets", {})[key] = {
        "label": label, "kinds": list(kinds), "sets": list(sets), "origin": origin,
    }
    cache.write_raw(doc, directory)


def put_term(directory: Path | None, key: str, *, kinds: tuple[str, ...] = (),
             sets: tuple[str, ...] = (), ignore: bool = False,
             match: str = "word", origin: str = "manual") -> None:
    doc = cache.read_raw(directory)
    entry: dict[str, Any] = {"match": match, "origin": origin}
    if ignore:
        entry["ignore"] = True
    else:
        if kinds:
            entry["kinds"] = list(kinds)
        if sets:
            entry["sets"] = list(sets)
    doc.setdefault("cuesheet", {})[key] = entry
    cache.write_raw(doc, directory)


def delete(directory: Path | None, domain: str, key: str, *, had_default: bool) -> None:
    """Tombstone `key` in `domain` when a default of the same key exists
    (so a later app update cannot silently revive it); otherwise drop the
    entry outright -- there is nothing left for a default to shadow."""
    doc = cache.read_raw(directory)
    section = doc.setdefault(domain, {})
    if had_default:
        section[key] = {"deleted": True}
    else:
        section.pop(key, None)
    cache.write_raw(doc, directory)


def reset(directory: Path | None, domain: str, key: str) -> None:
    """Remove any override or tombstone for `key`, letting a default (if
    any) show through again."""
    doc = cache.read_raw(directory)
    section = doc.get(domain) or {}
    section.pop(key, None)
    cache.write_raw(doc, directory)
