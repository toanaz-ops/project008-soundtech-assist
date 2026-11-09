"""Search and facets over loaded entries (Vietnamese-tone-insensitive)."""

from __future__ import annotations

from collections import Counter

from wing_parser.library.store import LoadedEntry
from wing_parser.showcontext.ingest.keywords import fold

FACET_KEYS = ("topic", "instrument", "genre", "technique", "publisher")


def _data(item) -> dict:
    return item.entry if isinstance(item, LoadedEntry) else item


def _tag_values(entry: dict, group: str) -> list[str]:
    tags = entry.get("tags") or {}
    values = tags.get(group) if isinstance(tags, dict) else None
    return [str(v) for v in values] if isinstance(values, list) else []


def _publishers(entry: dict) -> list[str]:
    return [str(s.get("publisher", "")) for s in entry.get("sources") or []
            if isinstance(s, dict)]


def _title_text(entry: dict) -> str:
    return fold(f"{entry.get('title', '')} {entry.get('title_vi', '')}")


def _full_text(entry: dict) -> str:
    parts = [entry.get("title", ""), entry.get("title_vi", ""), entry.get("summary", ""),
             entry.get("body", "")]
    for group in ("instrument", "genre", "technique", "event"):
        parts.extend(_tag_values(entry, group))
    for src in entry.get("sources") or []:
        if isinstance(src, dict):
            parts.extend((src.get("title", ""), src.get("publisher", "")))
    return fold(" ".join(str(p) for p in parts if p))


def search(entries: list, query: str = "", *, topic: str | None = None,
           instrument: str | None = None, genre: str | None = None,
           technique: str | None = None, publisher: str | None = None) -> list:
    """Entries matching every filter and every folded query token.

    Ranking: more tokens in the title first, then title order. With an
    empty query the order is title order.
    """
    tokens = fold(query).split()
    wanted_publisher = publisher.casefold() if publisher else None
    scored: list[tuple[int, str, object]] = []
    for item in entries:
        entry = _data(item)
        if topic and entry.get("topic") != topic:
            continue
        if instrument and instrument not in _tag_values(entry, "instrument"):
            continue
        if genre and genre not in _tag_values(entry, "genre"):
            continue
        if technique and technique not in _tag_values(entry, "technique"):
            continue
        if wanted_publisher and wanted_publisher not in (p.casefold() for p in _publishers(entry)):
            continue
        full, title = _full_text(entry), _title_text(entry)
        if not all(t in full for t in tokens):
            continue
        score = sum(1 for t in tokens if t in title)
        scored.append((-score, str(entry.get("title", "")).casefold(), item))
    scored.sort(key=lambda row: (row[0], row[1]))
    return [row[2] for row in scored]


def facets(entries: list) -> dict[str, Counter]:
    """Counts per topic / instrument / genre / technique / publisher."""
    out: dict[str, Counter] = {key: Counter() for key in FACET_KEYS}
    for item in entries:
        entry = _data(item)
        if entry.get("topic"):
            out["topic"][entry["topic"]] += 1
        for group in ("instrument", "genre", "technique"):
            out[group].update(set(_tag_values(entry, group)))
        out["publisher"].update(set(_publishers(entry)))
    return out
