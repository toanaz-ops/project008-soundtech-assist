"""Load, validate and layer the automix knowledge tables.

Two layers, same idea as the advisory rules: the shipped base tables in
`data/` (textbook and engineering defaults, every number carrying `src`
ids or the literal `confidence: eng_default`), and ToanAZ's own
overrides in `<knowledge_dir>/automix.yaml`. An override is honoured only
if its `source:` names ToanAZ and an ISO date; anything else is ignored
and reported in `Knowledge.warnings`, never silently applied.
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from wing_parser import config

DATA_DIR = Path(__file__).resolve().parent / "data"
TABLES = ("eq_targets", "masking", "dynamics", "balance", "fx", "genres", "bounds")
CONFIDENCES = ("high", "medium", "low", "eng_default")
OWNER_FILE = "automix.yaml"
_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_ALIASES = {"eq": "eq_targets"}


def provenance_errors(name: str, node, ids, covered: bool = False, where: str = "") -> list:
    """Every numeric leaf must sit under a record with `src` ids that
    resolve, or `confidence: eng_default`. Provenance is inherited by the
    record's children, so a table row can state it once."""
    errors: list[str] = []
    if isinstance(node, dict):
        here = covered
        if "src" in node or "confidence" in node:
            here = True
            conf, src = node.get("confidence"), node.get("src") or []
            if conf not in CONFIDENCES:
                errors.append(f"{name}:{where}: confidence {conf!r} not in {CONFIDENCES}")
            elif conf != "eng_default" and not src:
                errors.append(f"{name}:{where}: no src and confidence is not eng_default")
            for ident in src:
                if ident not in ids:
                    errors.append(f"{name}:{where}: unknown source id {ident!r}")
        for key, value in node.items():
            if key.endswith("_confidence") and value not in CONFIDENCES:
                errors.append(f"{name}:{where}: {key} {value!r} not in {CONFIDENCES}")
            if key in ("src", "confidence") or (key == "version" and not where):
                continue
            sub = f"{where}.{key}" if where else str(key)
            errors += provenance_errors(name, value, ids, here, sub)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            errors += provenance_errors(name, value, ids, covered, f"{where}[{index}]")
    elif isinstance(node, (int, float)) and not isinstance(node, bool) and not covered:
        errors.append(f"{name}:{where}: numeric value {node} has no src or eng_default")
    return errors


def _read(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


@lru_cache(maxsize=1)
def _base() -> tuple:
    sources = _read(DATA_DIR / "sources.yaml")["sources"]
    tables = {name: _read(DATA_DIR / f"{name}.yaml") for name in TABLES}
    errors = [e for name, table in tables.items()
              for e in provenance_errors(name, table, sources)]
    if errors:
        raise ValueError("automix knowledge tables are invalid:\n" + "\n".join(errors))
    return sources, tables


@dataclass(frozen=True)
class Knowledge:
    tables: dict
    sources: dict
    warnings: tuple = field(default=())

    def __getattr__(self, name: str):
        try:
            return self.tables[_ALIASES.get(name, name)]
        except KeyError:
            raise AttributeError(name) from None


def _apply(tables: dict, sources: dict, index: int, entry) -> None:
    """Apply one override to `tables`/`sources` in place; raise ValueError if unusable."""
    if not isinstance(entry, dict):
        raise ValueError("not a mapping")
    source = " ".join(str(entry.get("source") or "").split())
    if not ("ToanAZ" in source and _ISO_DATE.search(source)):
        raise ValueError(f"source {source!r} must contain 'ToanAZ' and an ISO date (YYYY-MM-DD)")
    name, path, value = entry.get("file"), entry.get("path"), entry.get("value")
    if name not in TABLES:
        raise ValueError(f"file {name!r} is not one of {TABLES}")
    if not (isinstance(path, list) and path and all(isinstance(p, str) for p in path)):
        raise ValueError("path must be a non-empty list of keys")
    if not isinstance(value, dict):
        raise ValueError("value must be a mapping (the record fields to set)")
    ident = f"toanaz_{index}"
    trial = copy.deepcopy(tables[name])
    node = trial
    for hop, key in enumerate(path):
        if not isinstance(node, dict):
            raise ValueError(f"path crosses a value, not a record, before {key!r}")
        node = node.setdefault(key, {})
        if hop < len(path) - 1 and not isinstance(node, dict):
            raise ValueError(f"path crosses {key!r}, which is a {type(node).__name__}, not a record")
    record = node
    if not isinstance(record, dict):
        raise ValueError("path ends on a value, not a record")
    for stale in [k for k in record if str(k).endswith("_confidence")]:
        del record[stale]  # the owner vouches for the whole record
    record.update(copy.deepcopy(value))
    record["src"], record["confidence"] = [ident], "high"
    trial_sources = {**sources, ident: {"cite": f"ToanAZ override: {source}", "kind": "owner", "opened": True}}
    errors = provenance_errors(name, trial, trial_sources)
    if errors:
        raise ValueError("; ".join(errors[:3]))
    tables[name] = trial
    sources[ident] = trial_sources[ident]


def load(knowledge_dir: Path | None = None) -> Knowledge:
    base_sources, base_tables = _base()
    sources, tables = copy.deepcopy(base_sources), copy.deepcopy(base_tables)
    warnings: list[str] = []
    path = config.knowledge_dir(knowledge_dir) / OWNER_FILE
    if path.is_file():
        try:
            entries = _read(path).get("overrides") or []
            if not isinstance(entries, list):
                entries, warnings = [], [f"{path.name}: overrides must be a list"]
        except (yaml.YAMLError, OSError, AttributeError) as exc:
            entries, warnings = [], [f"{path.name}: unreadable ({exc})"]
        for index, entry in enumerate(entries, start=1):
            try:
                _apply(tables, sources, index, entry)
            except (ValueError, TypeError, AttributeError, KeyError) as exc:
                warnings.append(f"{path.name} entry {index} ignored: {exc}")
    return Knowledge(tables, sources, tuple(warnings))
