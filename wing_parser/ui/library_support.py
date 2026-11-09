"""Small helpers the Library page, view and dialogs share (no widgets).

The store keeps its taxonomy loaders private to a layer lookup; the UI
needs the same topics and publishers for live validation of an unsaved
entry, so the lookup is repeated here over the public `store.root` /
`store.shipped_root` pair.
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from wing_parser.library import Issue, load_publishers, load_topics, validate
from wing_parser.library.store import LibraryStore
from wing_parser.ui.texts import current_language


def layer_roots(store: LibraryStore) -> list[Path]:
    roots = [store.root]
    if store.shipped_root is not None:
        roots.append(store.shipped_root)
    return roots


def taxonomy(store: LibraryStore) -> tuple[dict, list]:
    """(topics, publishers) from the first layer that carries a taxonomy."""
    for root in layer_roots(store):
        if (root / "topics.yaml").is_file():
            return load_topics(root), load_publishers(root)
    return {}, []


def check_entry(store: LibraryStore, entry: dict) -> list[Issue]:
    topics, publishers = taxonomy(store)
    return validate(entry, topics=topics, publishers=publishers,
                    media_root=[r / "media" for r in layer_roots(store)])


def topic_label(topics: dict, topic_id: str) -> str:
    """The topic's label in the UI language; the raw id when unknown."""
    item = topics.get(topic_id)
    if not item:
        return str(topic_id)
    return str(item.get(current_language()) or item.get("en") or topic_id)


def now_stamp() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def today() -> str:
    return dt.date.today().isoformat()


def flag_codes(issues: list[Issue]) -> set[str]:
    return {issue.code for issue in issues}
