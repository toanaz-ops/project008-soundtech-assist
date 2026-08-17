"""Read a .snap file and split it into payload and envelope."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wing_parser.core.versions import SceneVersion, load_registry, resolve


@dataclass(frozen=True)
class RawScene:
    version: SceneVersion
    ae: dict[str, Any]
    ce: dict[str, Any]
    meta: dict[str, Any]
    path: Path


def parse_raw(doc: Any, file_path: Path) -> RawScene:
    """Split an already-parsed document. Separated from reading a file so
    a caller holding an edited copy in memory -- the desktop app, after
    every repair -- can rebuild a scene without writing a temporary file.
    Same shape as showcontext's parse/load pair."""
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


def load_raw(path: str | Path) -> RawScene:
    file_path = Path(path)
    return parse_raw(json.loads(file_path.read_text(encoding="utf-8")), file_path)
