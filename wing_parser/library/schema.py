"""Constants and taxonomy loaders for the mixing knowledge library.

The format is defined in knowledge/library/SCHEMA.md; change both together.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

ID_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIMESTAMP_RE = re.compile(r"^\d{1,2}:\d{2}(:\d{2})?$")

CONFIDENCE = ("established", "common-practice", "contested")
STATUS = ("draft", "reviewed", "retired")
SOURCE_KINDS = ("article", "book", "paper", "manual", "standard", "video", "course")
MEDIA_KINDS = ("diagram", "image", "video")
IMAGE_LICENSES = ("CC-BY-SA-4.0", "CC-BY-4.0", "CC0-1.0", "public-domain")
TAG_KEYS = ("instrument", "genre", "technique", "event")

# Key order used when writing an entry to disk.
KEY_ORDER = (
    "id", "title", "title_vi", "topic", "tags", "summary", "summary_vi", "body", "body_vi",
    "rule",
    "sources", "media", "confidence", "status", "revision", "updated_at",
    "updated_by",
)
REQUIRED = (
    "id", "title", "topic", "tags", "summary", "body", "sources",
    "confidence", "status", "revision", "updated_at", "updated_by",
)
SOURCE_ORDER = (
    "title", "publisher", "kind", "url", "author", "year", "accessed",
    "locator", "doi", "isbn",
)
MEDIA_ORDER = (
    "kind", "path", "url", "title", "channel", "timestamp", "caption", "caption_vi",
    "license", "attribution", "generated_by",
)


# libyaml-backed loader when available (about 10x faster); same safe semantics.
YAML_LOADER = getattr(yaml, "CSafeLoader", yaml.SafeLoader)


def _load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as handle:
        data = yaml.load(handle, Loader=YAML_LOADER)
    return data if isinstance(data, dict) else {}


def load_topics(root: Path) -> dict[str, dict]:
    """topic id -> {"id", "en", "vi"} from `<root>/topics.yaml`."""
    path = Path(root) / "topics.yaml"
    if not path.is_file():
        return {}
    return {t["id"]: t for t in _load_yaml(path).get("topics", []) if "id" in t}


def load_publishers(root: Path) -> list[dict]:
    """Publisher allow-list from `<root>/sources.yaml`."""
    path = Path(root) / "sources.yaml"
    if not path.is_file():
        return []
    return [p for p in _load_yaml(path).get("publishers", []) if "name" in p]


def publisher_names(publishers: list[dict]) -> set[str]:
    """Case-folded names and aliases of every vetted publisher."""
    names: set[str] = set()
    for item in publishers:
        names.add(str(item["name"]).casefold())
        names.update(str(a).casefold() for a in item.get("aliases", []))
    return names
