"""Copy a dry-run draft into principles.yaml (wave 9).

Only the owner's button calls this. The draft's raw YAML entries are
merged into principles.yaml at text level (header comments survive),
re-parsed and validated on a temp file, and only then swapped in with a
`.bak` of the previous file. A layout the merge cannot prove it handled
is refused and nothing is written.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yaml

from wing_parser import config
from wing_parser.advisory import draft_dry_run as dd
from wing_parser.advisory import layers

PROMOTED_DIR = "promoted"
ODD_LAYOUT = "unrecognised principles.yaml layout, copy by hand"
_TOP_KEY = re.compile(r"^[A-Za-z_][\w.-]*\s*:")
_PRINCIPLES_LINE = re.compile(r"^principles:\s*(\[\s*\])?\s*(#.*)?$")


@dataclass(frozen=True)
class PromoteResult:
    ok: bool
    error: str | None = None
    backup: Path | None = None
    moved_to: Path | None = None
    rule_ids: tuple[str, ...] = ()


def _fail(msg: str) -> PromoteResult:
    return PromoteResult(ok=False, error=msg)


def _entries_text(entries: list[dict]) -> str:
    out: list[str] = []
    for entry in entries:
        body = yaml.safe_dump(entry, allow_unicode=True, sort_keys=False,
                              default_flow_style=False, width=10_000)
        lines = body.rstrip("\n").split("\n")
        out.append("  - " + lines[0])
        out.extend("    " + ln if ln else ln for ln in lines[1:])
    return "\n".join(out) + "\n"


def _merge_text(old: str, entries: list[dict]) -> str:
    lines = old.splitlines()
    top = [i for i, ln in enumerate(lines) if _TOP_KEY.match(ln)]
    idx = [i for i in top if lines[i].startswith("principles:")]
    if len(idx) != 1 or top[-1] != idx[0]:
        raise ValueError(ODD_LAYOUT)
    i = idx[0]
    m = _PRINCIPLES_LINE.match(lines[i])
    if m is None:
        raise ValueError(ODD_LAYOUT)
    block = _entries_text(entries)
    if m.group(1):  # inline empty list
        head = "\n".join(lines[:i]) + ("\n" if i else "")
        comment = m.group(2)
        tail = "".join(ln + "\n" for ln in lines[i + 1:])
        return (head + "principles:" + (f"  {comment}" if comment else "")
                + "\n" + block + tail)
    return old + ("" if old.endswith("\n") else "\n") + block


def promote(draft_path: Path, directory: Path | None = None,
            now: datetime | None = None) -> PromoteResult:
    draft_path = Path(draft_path)
    load = dd.load_draft(draft_path, directory)
    if load.error:
        return _fail(load.error)
    if not load.promotable:
        return _fail("; ".join(load.promote_blockers) or "draft not promotable")
    root = config.knowledge_dir(directory)
    target = root / layers.PRINCIPLES_FILE
    try:
        raw = yaml.safe_load(draft_path.read_text(encoding="utf-8"))
        entries = [dict(e) for e in raw["principles"]]
        # Keep the owner's line endings: read_text folds CRLF to LF.
        bom = False
        crlf = target.exists() and b"\r\n" in target.read_bytes()
        if target.exists():
            old = target.read_text(encoding="utf-8")
            bom = old.startswith("\ufeff")
            old = old.lstrip("\ufeff")
            old_list = (yaml.safe_load(old) or {}).get("principles") or []
        else:
            old = ("# ToanAZ's personal mixing principles.\n"
                   "principles: []\n")
            old_list = []
        merged = _merge_text(old, entries)
        if (yaml.safe_load(merged) or {}).get("principles") != old_list + entries:
            raise ValueError(ODD_LAYOUT)
        root.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(dir=root, suffix=".tmp")
        tmp = Path(tmp_name)
        try:
            with os.fdopen(fd, "w", encoding="utf-8",
                           newline="\r\n" if crlf else "") as fh:
                fh.write(("\ufeff" if bom else "") + merged)
            dd.check_rules(tmp, layers._as_rules(
                tmp, layer="toanaz", key="principles"))
            backup = None
            if target.exists():
                backup = target.with_name(target.name + ".bak")
                shutil.copyfile(target, backup)
            os.replace(tmp, target)
        finally:
            if tmp.exists():
                tmp.unlink()
    except (ValueError, OSError, KeyError, TypeError, AttributeError,
            yaml.YAMLError) as exc:
        return _fail(f"{exc}")
    ids = tuple(str(e.get("id")) for e in entries)
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M")
    dest = root / dd.DRAFTS_DIR / PROMOTED_DIR / f"{draft_path.stem}-{stamp}.yaml"
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(draft_path), str(dest))
    except OSError as exc:
        return PromoteResult(True, f"copied, but could not move the draft: {exc}",
                             backup, None, ids)
    return PromoteResult(True, None, backup, dest, ids)
