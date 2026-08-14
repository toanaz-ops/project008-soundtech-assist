"""Persist classifications so a name is only ever resolved once.

This is what turns the optional Claude fallback from a running cost into
a one-off: whatever resolves a name — pattern, model, or a human editing
the file — the answer lands here and every later run reads it offline.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from wing_parser import config
from wing_parser.classifier.matcher import Classification
from wing_parser.classifier.normalize import clean

FILENAME = "classifier.yaml"
DOMAINS = ("channels", "buses")

_SEED = """\
# Cached and manually declared classifications.
#
# Keys are normalized names (trimmed, whitespace-collapsed, casefolded).
# Anything written here is read before the pattern matcher runs, so a
# manual entry always wins and a name only ever costs one classification
# in its lifetime.
#
# Comments you add here survive every rewrite -- annotate freely.
#
# origin: manual | llm | pattern
channels: {}
buses: {}
"""


def _yaml() -> YAML:
    """Round-trip mode. safe_dump would erase every comment in the file."""
    engine = YAML()
    engine.preserve_quotes = True
    return engine


def _path(directory: Path | None) -> Path:
    return config.knowledge_dir(directory) / FILENAME


def _read(directory: Path | None) -> Any:
    """The live document, comments and all. Mutate and hand back to _write."""
    path = _path(directory)
    text = path.read_text(encoding="utf-8") if path.exists() else _SEED
    doc = _yaml().load(text)
    if doc is None:
        doc = _yaml().load(_SEED)
    for domain in DOMAINS:
        if doc.get(domain) is None:
            doc[domain] = {}
    return doc


def _write(doc: Any, directory: Path | None) -> None:
    path = _path(directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        _yaml().dump(doc, handle)


def _one(domain: str, key: str, entry: Any, path: Path) -> Classification:
    for required in ("kind", "confidence"):
        if required not in entry:
            raise ValueError(
                f"{path}: entry {domain}.{key!r} is missing required key "
                f"{required!r}. Each entry needs at least kind: and "
                f"confidence:, plus an optional origin: and matched:."
            )
    return Classification(
        kind=str(entry["kind"]),
        confidence=float(entry["confidence"]),
        origin=str(entry.get("origin", "cache")),
        matched=entry.get("matched"),
    )


def load(directory: Path | None = None) -> dict[str, dict[str, Classification]]:
    doc = _read(directory)
    path = _path(directory)
    return {
        domain: {
            key: _one(domain, key, entry, path)
            for key, entry in (doc.get(domain) or {}).items()
        }
        for domain in DOMAINS
    }


def lookup(name: str, domain: str, directory: Path | None = None) -> Classification | None:
    return load(directory).get(domain, {}).get(clean(name))


def remember(
    name: str,
    domain: str,
    classification: Classification,
    directory: Path | None = None,
) -> None:
    doc = _read(directory)
    if doc.get(domain) is None:
        doc[domain] = {}
    doc[domain][clean(name)] = {
        "kind": classification.kind,
        "confidence": round(float(classification.confidence), 3),
        "origin": classification.origin,
        "matched": classification.matched,
    }
    _write(doc, directory)
