"""The library store: one YAML file per entry plus an append-only history.

Writes go through `save`/`retire`/`restore` only: they validate, bump the
revision, stamp author and time, write atomically and log a snapshot.
Hand-written files are still loaded (and flagged), never dropped.
"""

from __future__ import annotations

import datetime as dt
import difflib
import getpass
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from wing_parser.library import schema
from wing_parser.library.serialize import _normalise, _plain, dump_entry
from wing_parser.library.validate import Issue, errors, validate


class ValidationFailed(Exception):
    def __init__(self, issues: list[Issue]):
        self.issues = issues
        super().__init__("; ".join(i.format() for i in errors(issues)))


class RevisionConflict(Exception):
    def __init__(self, entry_id: str, expected: int, actual: int):
        self.entry_id, self.expected, self.actual = entry_id, expected, actual
        super().__init__(f"{entry_id}: expected revision {expected}, file is at {actual}")


@dataclass(frozen=True)
class Revision:
    rev: int
    at: str
    author: str
    action: str  # create | edit | retire | restore | shipped
    note: str
    snapshot: dict


@dataclass
class LoadedEntry:
    entry: dict
    issues: list[Issue] = field(default_factory=list)
    path: Path | None = None
    layer: str = "user"  # "shipped" | "user"

    @property
    def id(self) -> str:
        return str(self.entry.get("id", ""))

    @property
    def has_errors(self) -> bool:
        return bool(errors(self.issues))


def default_author() -> str:
    try:
        return getpass.getuser() or "unknown"
    except Exception:  # no usable login name in this environment
        return "unknown"


def _now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


class LibraryStore:
    """Two-layer store: `root` (user, writable) over `shipped_root` (read-only).

    An entry id present in both layers resolves to the user copy. With
    `shipped_root` None or equal to `root` there is a single layer.
    """

    def __init__(self, root: Path, shipped_root: Path | None = None):
        self.root = Path(root)
        shipped = Path(shipped_root) if shipped_root is not None else None
        self.shipped_root = None if shipped is None or shipped == self.root else shipped

    def _layers(self) -> list[tuple[str, Path]]:
        layers = [("user", self.root)]
        if self.shipped_root is not None:
            layers.append(("shipped", self.shipped_root))
        return layers

    @property
    def taxonomy_root(self) -> Path:
        """Folder holding topics.yaml / publishers.yaml (user layer first, then shipped)."""
        for _, root in self._layers():
            if (root / "topics.yaml").is_file():
                return root
        return self.root

    # -- paths -----------------------------------------------------------
    @property
    def entries_dir(self) -> Path:
        return self.root / "entries"

    @property
    def media_dir(self) -> Path:
        return self.root / "media"

    def _entry_path(self, entry_id: str) -> Path:
        return self.entries_dir / f"{entry_id}.yaml"

    def _history_path(self, entry_id: str) -> Path:
        return self.root / "history" / f"{entry_id}.jsonl"

    def media_file(self, entry_id: str, rel: str) -> Path:
        """User layer first, then shipped; the user path when neither has it."""
        first: Path | None = None
        for _, root in self._layers():
            base = (root / "media" / entry_id).resolve()
            target = (base / rel).resolve()
            if base != target and base not in target.parents:
                raise ValueError(f"media path escapes its folder: {rel!r}")
            first = first or target
            if target.is_file():
                return target
        return first

    # -- reading ---------------------------------------------------------
    def _check(self, entry: dict) -> list[Issue]:
        tax = self.taxonomy_root
        return validate(entry, topics=schema.load_topics(tax),
                        publishers=schema.load_publishers(tax),
                        media_root=[r / "media" for _, r in self._layers()])

    def _load_file(self, path: Path, layer: str = "user") -> LoadedEntry:
        try:
            with open(path, encoding="utf-8") as handle:
                data = yaml.safe_load(handle)
        except (OSError, yaml.YAMLError, UnicodeDecodeError) as exc:
            return LoadedEntry({"id": path.stem}, [Issue("error", "bad-yaml", "", str(exc))], path, layer)
        if not isinstance(data, dict):
            return LoadedEntry({"id": path.stem},
                               [Issue("error", "bad-yaml", "", "file is not a mapping")], path, layer)
        entry = _plain(data)
        issues = self._check(entry)
        if entry.get("id") != path.stem:
            issues.append(Issue("error", "bad-id", "id",
                                f"id {entry.get('id')!r} does not match file name {path.stem!r}"))
        return LoadedEntry(entry, issues, path, layer)

    def entries(self, include_retired: bool = False) -> list[LoadedEntry]:
        found: dict[str, LoadedEntry] = {}
        for layer, root in self._layers():
            for path in sorted((root / "entries").glob("*.yaml")):
                found.setdefault(path.stem, self._load_file(path, layer))
        loaded = [found[k] for k in sorted(found)]
        if include_retired:
            return loaded
        return [e for e in loaded if e.entry.get("status") != "retired"]

    def get(self, entry_id: str) -> LoadedEntry:
        """The entry (retired included). Raises KeyError when it does not exist."""
        for layer, root in self._layers():
            path = root / "entries" / f"{entry_id}.yaml"
            if path.is_file():
                return self._load_file(path, layer)
        raise KeyError(entry_id)

    # -- history ---------------------------------------------------------
    def history(self, entry_id: str) -> list[Revision]:
        path = self._history_path(entry_id)
        if not path.is_file():
            return []
        out: list[Revision] = []
        with open(path, encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    row = json.loads(line)
                    out.append(Revision(row["rev"], row["at"], row["author"],
                                        row["action"], row.get("note", ""), row["snapshot"]))
        return out

    def _revision(self, entry_id: str, rev: int) -> Revision:
        for item in reversed(self.history(entry_id)):
            if item.rev == rev:
                return item
        raise KeyError(f"{entry_id} revision {rev}")

    def diff(self, entry_id: str, rev_a: int, rev_b: int) -> str:
        """Unified diff of the YAML dumps of two revisions."""
        a, b = self._revision(entry_id, rev_a), self._revision(entry_id, rev_b)
        return "".join(difflib.unified_diff(
            dump_entry(a.snapshot).splitlines(keepends=True),
            dump_entry(b.snapshot).splitlines(keepends=True),
            fromfile=f"{entry_id} rev {rev_a}", tofile=f"{entry_id} rev {rev_b}"))

    def _append_history(self, entry_id: str, rows: list[dict]) -> None:
        path = self._history_path(entry_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    # -- writing ---------------------------------------------------------
    def _write_atomic(self, path: Path, text: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(tmp, path)

    def _commit(self, entry: dict, *, author: str, note: str, action: str,
                expected_revision: int | None) -> dict:
        entry_id = str(entry.get("id", ""))
        path = self._entry_path(entry_id) if schema.ID_RE.match(entry_id) else None
        current = None
        if path is not None:
            try:
                current = self.get(entry_id)
            except KeyError:
                pass
        current_rev = int(current.entry.get("revision", 0) or 0) if current else 0
        if expected_revision is not None and current_rev != expected_revision:
            raise RevisionConflict(entry_id, expected_revision, current_rev)

        data = _plain(dict(entry))
        data["revision"] = current_rev + 1
        data["updated_at"] = _now()
        data["updated_by"] = author or default_author()
        issues = self._check(data)
        if errors(issues):
            raise ValidationFailed(issues)

        rows: list[dict] = []
        if current is not None and not any(r.rev == current_rev for r in self.history(entry_id)) \
                and not current.has_errors:
            shipped = current.layer == "shipped"
            rows.append({"rev": current_rev, "at": str(current.entry.get("updated_at", "")),
                         "author": str(current.entry.get("updated_by", "")),
                         "action": "shipped" if shipped else "create",
                         "note": "shipped version" if shipped else "baseline (existing file)",
                         "snapshot": current.entry})
        data = _normalise(data)
        self._write_atomic(path, dump_entry(data))
        rows.append({"rev": data["revision"], "at": data["updated_at"], "author": data["updated_by"],
                     "action": action if current is not None or action != "edit" else "create",
                     "note": note, "snapshot": data})
        self._append_history(entry_id, rows)
        return data

    def save(self, entry: dict, *, author: str, note: str = "",
             expected_revision: int | None = None) -> dict:
        """Create or update an entry. Returns the entry as written.

        Raises ValidationFailed (nothing written) on any error and
        RevisionConflict when the file is not at `expected_revision`.
        """
        return self._commit(entry, author=author, note=note, action="edit",
                            expected_revision=expected_revision)

    def retire(self, entry_id: str, *, author: str, note: str = "") -> dict:
        entry = dict(self.get(entry_id).entry)
        entry["status"] = "retired"
        return self._commit(entry, author=author, note=note, action="retire",
                            expected_revision=None)

    def restore(self, entry_id: str, rev: int, *, author: str, note: str = "") -> dict:
        """Write an earlier snapshot back as a NEW revision (history is never rewritten)."""
        snapshot = dict(self._revision(entry_id, rev).snapshot)
        return self._commit(snapshot, author=author, note=note or f"restore rev {rev}",
                            action="restore", expected_revision=None)
