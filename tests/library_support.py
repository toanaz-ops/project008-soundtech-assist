"""Shared builders for the library tests (not a test module)."""

from __future__ import annotations

import copy
from pathlib import Path

import yaml

TOPICS = {"topics": [{"id": "eq", "en": "EQ", "vi": "EQ"},
                     {"id": "vocals", "en": "Vocals", "vi": "Giọng hát"}]}
PUBLISHERS = {"publishers": [{"name": "Sound On Sound", "aliases": ["SOS"], "why": "test"}]}

SOURCE = {"title": "Choosing a high-pass filter", "publisher": "Sound On Sound",
          "kind": "article", "url": "https://example.org/hpf", "accessed": "2026-11-09"}


def make_root(path: Path) -> Path:
    """A library root with taxonomy files and empty entries/."""
    path.mkdir(parents=True, exist_ok=True)
    (path / "entries").mkdir(exist_ok=True)
    for name, data in (("topics.yaml", TOPICS), ("sources.yaml", PUBLISHERS)):
        with open(path / name, "w", encoding="utf-8", newline="\n") as handle:
            yaml.safe_dump(data, handle, allow_unicode=True)
    return path


def entry(entry_id: str = "hpf-basics", **overrides) -> dict:
    data = {
        "id": entry_id, "title": "High-pass filter basics", "title_vi": "Lọc thông cao",
        "topic": "eq",
        "tags": {"instrument": ["vocal"], "genre": [], "technique": ["hpf"], "event": []},
        "summary": "Why and where to set a high-pass filter.",
        "body": "Set the filter below the lowest useful note.\n\nSecond paragraph.\n",
        "sources": [copy.deepcopy(SOURCE)],
        "confidence": "common-practice", "status": "draft",
    }
    data.update(overrides)
    return data


def write_raw(root: Path, data: dict) -> Path:
    """Write an entry file by hand (as a person editing a file would)."""
    full = {"revision": 1, "updated_at": "2026-11-09T10:00:00+07:00", "updated_by": "tester"}
    full.update(data)
    path = root / "entries" / f"{full['id']}.yaml"
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        yaml.safe_dump(full, handle, allow_unicode=True, sort_keys=False)
    return path
