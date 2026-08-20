"""Read a .snap file and split it into payload and envelope."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wing_parser.core.versions import SceneVersion, load_registry, resolve


@dataclass(frozen=True)
class RawScene:
    """A decoded scene and where it came from.

    `path` is None for a scene read from a console rather than a file, so
    everything that only wants something to print uses `source` instead --
    a filename for a file, `wing://<ip>` for a live desk. Deriving `source`
    from `path` when it is not given keeps every existing caller working
    and keeps the two from drifting apart.
    """

    version: SceneVersion
    ae: dict[str, Any]
    ce: dict[str, Any]
    meta: dict[str, Any]
    path: Path | None = None
    source: str = ""

    def __post_init__(self) -> None:
        if not self.source:
            derived = self.path.name if self.path is not None else "<unknown>"
            object.__setattr__(self, "source", derived)


def load_raw(path: str | Path) -> RawScene:
    file_path = Path(path)
    doc = json.loads(file_path.read_text(encoding="utf-8"))

    if not isinstance(doc, dict):
        raise ValueError(
            f"{file_path}: expected a JSON object at the top level, "
            f"found {type(doc).__name__}; not a WING snapshot"
        )

    type_id = doc.get("type")
    if not type_id:
        raise ValueError(f"{file_path}: missing top-level 'type' field; not a WING snapshot")

    version = resolve(type_id, load_registry())
    meta = {k: v for k, v in doc.items() if k not in {"ae_data", "ce_data"}}

    return RawScene(
        version=version,
        # `or {}` rather than a .get default: a corrupt file can carry
        # "ae_data": null, where the key is present and the default never
        # fires. Downstream code must never receive None here.
        ae=doc.get("ae_data") or {},
        ce=doc.get("ce_data") or {},
        meta=meta,
        path=file_path,
    )
