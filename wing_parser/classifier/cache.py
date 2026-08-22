"""Persist classifications so a name is only ever resolved once.

This is what turns the optional Claude fallback from a running cost into
a one-off: whatever resolves a name — pattern, model, or a human editing
the file — the answer lands here and every later run reads it offline.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from wing_parser import config
from wing_parser.classifier.matcher import Classification
from wing_parser.classifier.normalize import clean

FILENAME = "classifier.yaml"
DOMAINS = ("channels", "buses", "cuesheet")

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
# origin: manual | llm | pattern | cache
channels: {}
buses: {}
# cuesheet: terms as they appear on a printed running order, in any
# language, mapped to the same kinds the channels domain uses. A cue
# sheet and a console strip are different naming domains -- nobody
# labels a strip "ca si nu", and no director writes "HS4" -- so a term
# lives here and not in channels.
cuesheet: {}
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
    # This file is documented as hand-editable, so a typo in it is an
    # expected outcome, not a bug. A bare ruamel YAMLError is not a
    # ValueError and no caller catches it; naming the file in a ValueError
    # is the convention showcontext/loader.py and ingest/mapping.py
    # already follow for a hand-edited file.
    try:
        doc = _yaml().load(text)
    except YAMLError as exc:
        raise ValueError(f"{path}: invalid YAML: {exc}") from exc
    if doc is None:
        doc = _yaml().load(_SEED)
    if not hasattr(doc, "get"):
        raise ValueError(
            f"{path}: the top level must be a mapping with "
            + ", ".join(f"{domain}:" for domain in DOMAINS)
            + f" sections, but this file's top level is {type(doc).__name__}."
        )
    for domain in DOMAINS:
        if doc.get(domain) is None:
            doc[domain] = {}
        elif not hasattr(doc[domain], "items"):
            raise ValueError(
                f"{path}: section {domain}: must be a mapping of normalized "
                f"name to entry, but it is {type(doc[domain]).__name__}."
            )
    return doc


def _write(doc: Any, directory: Path | None) -> None:
    """Write via a sibling temp file and one atomic rename.

    This file is the durable record of every classification the tool has
    ever paid a model to make, and Task 17 rewrites it once per unresolved
    name. Truncating it in place means a crash mid-write loses the lot.
    """
    path = _path(directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    )
    try:
        with handle:
            _yaml().dump(doc, handle)
        os.replace(handle.name, path)
    except BaseException:
        Path(handle.name).unlink(missing_ok=True)
        raise


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
