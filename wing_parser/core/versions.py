"""Version registry for WING snapshot schemas.

The ae_data/ce_data payload is identical across all observed versions;
only the outer envelope differs. This module owns that delta.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import yaml

_DATA = Path(__file__).resolve().parent.parent / "descriptors" / "data" / "versions.yaml"


@dataclass(frozen=True)
class SceneVersion:
    type_id: str
    label: str
    meta_keys: tuple[str, ...]
    has_globals: bool
    cards: tuple[str, ...]
    known: bool = True


def load_registry(path: Path | None = None) -> dict[str, SceneVersion]:
    doc = yaml.safe_load((path or _DATA).read_text(encoding="utf-8"))
    return {
        type_id: SceneVersion(
            type_id=type_id,
            label=entry["label"],
            meta_keys=tuple(entry["meta_keys"]),
            has_globals=bool(entry["has_globals"]),
            cards=tuple(entry["cards"]),
        )
        for type_id, entry in doc["versions"].items()
    }


def newest_id(path: Path | None = None) -> str:
    doc = yaml.safe_load((path or _DATA).read_text(encoding="utf-8"))
    return doc["newest"]


def resolve(type_id: str, registry: dict[str, SceneVersion]) -> SceneVersion:
    """Return the version entry for type_id.

    An unrecognised type_id yields the newest known schema with known=False,
    so the caller can warn and still attempt a parse rather than refusing
    the file outright.
    """
    if type_id in registry:
        return registry[type_id]
    fallback = registry[newest_id()]
    return replace(fallback, type_id=type_id, known=False)
