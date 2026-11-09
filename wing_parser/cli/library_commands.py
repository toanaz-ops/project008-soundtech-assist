"""`wing library ...` commands. Each returns a process exit code."""

from __future__ import annotations

import json
import sys

import yaml

from wing_parser import config
from wing_parser.library import (
    LibraryStore,
    RevisionConflict,
    ValidationFailed,
    dump_entry,
    search,
)


def _store() -> LibraryStore:
    return LibraryStore(config.library_dir(), config.shipped_library_dir())


def _filters(args) -> dict:
    return {"topic": args.topic, "instrument": args.instrument, "genre": args.genre,
            "technique": args.technique, "publisher": args.source}


def _print_rows(rows: list, as_json: bool) -> None:
    if as_json:
        print(json.dumps([{**r.entry, "layer": r.layer,
                           "issues": [i.__dict__ for i in r.issues]} for r in rows],
                         ensure_ascii=False, indent=2, default=str))
        return
    for r in rows:
        e = r.entry
        flag = "  [!]" if r.issues else ""
        print(f"{r.id}  {e.get('topic', '')}  r{e.get('revision', '?')}  "
              f"{e.get('status', '')}  {e.get('title', '')}{flag}")
    print(f"{len(rows)} entr{'y' if len(rows) == 1 else 'ies'}")


def list_(args) -> int:
    rows = search(_store().entries(include_retired=getattr(args, "retired", False)),
                  **_filters(args))
    _print_rows(rows, args.json)
    return 0


def search_(args) -> int:
    rows = search(_store().entries(), args.query, **_filters(args))
    _print_rows(rows, args.json)
    return 0


def show(args) -> int:
    try:
        loaded = _store().get(args.id)
    except KeyError:
        print(f"error: no entry {args.id!r}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps({**loaded.entry, "layer": loaded.layer,
                          "issues": [i.__dict__ for i in loaded.issues]},
                         ensure_ascii=False, indent=2, default=str))
    else:
        print(dump_entry(loaded.entry), end="")
        for issue in loaded.issues:
            print(issue.format(loaded.id), file=sys.stderr)
    return 0


def validate_(args) -> int:
    store = _store()
    bad = 0
    loaded = store.entries(include_retired=True)
    for item in loaded:
        for issue in item.issues:
            print(issue.format(item.id))
            if issue.level == "error" or args.strict:
                bad += 1
    print(f"{len(loaded)} entries checked, {bad} blocking issue(s)")
    return 1 if bad else 0


def _read_entry(path: str) -> dict | None:
    try:
        with open(path, encoding="utf-8") as handle:
            data = yaml.safe_load(handle)
    except (OSError, yaml.YAMLError, UnicodeDecodeError) as exc:
        print(f"error: cannot read {path}: {exc}", file=sys.stderr)
        return None
    if not isinstance(data, dict):
        print(f"error: {path} is not a YAML mapping", file=sys.stderr)
        return None
    return data


def _save(entry: dict, args, expected: int | None) -> int:
    try:
        written = _store().save(entry, author=args.author, note=args.note or "",
                                expected_revision=expected)
    except ValidationFailed as exc:
        for issue in exc.issues:
            print(issue.format(str(entry.get("id", ""))), file=sys.stderr)
        return 1
    except RevisionConflict as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"saved {written['id']} at revision {written['revision']}")
    return 0


def add(args) -> int:
    entry = _read_entry(args.file)
    if entry is None:
        return 1
    entry.pop("revision", None)
    try:
        _store().get(str(entry.get("id", "")))
    except KeyError:
        return _save(entry, args, None)
    print(f"error: entry {entry.get('id')!r} already exists; use `edit`", file=sys.stderr)
    return 1


def edit(args) -> int:
    entry = _read_entry(args.file)
    if entry is None:
        return 1
    if entry.get("id") != args.id:
        print(f"error: file id {entry.get('id')!r} does not match {args.id!r}", file=sys.stderr)
        return 1
    if not args.note:
        print("error: --note is required when editing", file=sys.stderr)
        return 1
    expected = entry.get("revision")
    return _save(entry, args, expected if isinstance(expected, int) else None)


def history(args) -> int:
    store = _store()
    revisions = store.history(args.id)
    if args.diff is not None:
        order = [r.rev for r in revisions]
        if args.diff not in order or order.index(args.diff) == 0:
            print(f"error: revision {args.diff} has no predecessor in the history",
                  file=sys.stderr)
            return 1
        print(store.diff(args.id, order[order.index(args.diff) - 1], args.diff), end="")
        return 0
    for r in revisions:
        print(f"r{r.rev}  {r.at}  {r.author}  {r.action}  {r.note}")
    return 0


def export_web(args) -> int:
    from pathlib import Path

    from wing_parser.library.web import render
    from wing_parser.library.web.export import export_web as run_export

    try:
        artifact = bool(getattr(args, "artifact", False))
        result = run_export(_store(), Path(args.out_dir), artifact=artifact)
    except render.MissingDependency as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    for item in result["missing_media"]:
        print(f"warning: diagram not exported (missing or not PNG): {item}", file=sys.stderr)
    print(f"exported {result['entries']} entries, {result['media']} images, "
          f"{result['bytes'] / 1024:.0f} KiB -> {result['path']}")
    return 0


def register(sub) -> None:
    node = sub.add_parser("library", help="the mixing knowledge library")
    inner = node.add_subparsers(dest="library_command", required=True)

    def filters(p):
        for name in ("topic", "instrument", "genre", "technique", "source"):
            p.add_argument(f"--{name}", default=None)
        p.add_argument("--json", action="store_true")

    p = inner.add_parser("list", help="list entries")
    filters(p)
    p.add_argument("--retired", action="store_true", help="include retired entries")
    p.set_defaults(handler=list_)
    p = inner.add_parser("search", help="search entries")
    p.add_argument("query")
    filters(p)
    p.set_defaults(handler=search_)
    p = inner.add_parser("show", help="print one entry")
    p.add_argument("id")
    p.add_argument("--json", action="store_true")
    p.set_defaults(handler=show)
    p = inner.add_parser("validate", help="check every entry (exit 1 on errors)")
    p.add_argument("--strict", action="store_true", help="warnings also fail")
    p.set_defaults(handler=validate_)
    p = inner.add_parser("add", help="add a new entry from a YAML file")
    p.add_argument("file")
    p.add_argument("--author", required=True)
    p.add_argument("--note", default="")
    p.set_defaults(handler=add)
    p = inner.add_parser("edit", help="replace an entry from a YAML file")
    p.add_argument("id")
    p.add_argument("file")
    p.add_argument("--author", required=True)
    p.add_argument("--note", default="")
    p.set_defaults(handler=edit)
    p = inner.add_parser("history", help="revision history of an entry")
    p.add_argument("id")
    p.add_argument("--diff", type=int, default=None, metavar="REV",
                   help="show REV against its predecessor")
    p.set_defaults(handler=history)
    p = inner.add_parser("export-web", help="write a static, read-only web export of the library")
    p.add_argument("out_dir")
    p.add_argument("--artifact", action="store_true",
                   help="write ONE page fragment library.html (inline images, link-card videos) for claude.ai artifacts")
    p.set_defaults(handler=export_web)
