"""Tests for wing_parser.writelog: codes, entries, store (no Qt)."""

import ast
import json
from datetime import datetime
from pathlib import Path

import pytest

from wing_parser.writelog import (
    LogEntry,
    adhoc_code,
    append,
    list_shows,
    log_dir,
    normalize_code,
    now_ts,
    read_show,
)


def make(code="AZ-1501", outcome="sent", kind="repair", ts="2026-10-20T13:05:12.481+07:00", **kw):
    base = dict(
        v=1, ts=ts, show_code=code, show="BIDV Gala", venue="GEM", desk={"name": "W"},
        kind=kind, finding="G7:bus.iem.3", label="L", address="/a", path="p",
        file_before=0, desk_before=0, written=1, readback=1, outcome=outcome,
        scene="x.snap", app="0.1.0",
    )
    base.update(kw)
    return LogEntry(**base)


def test_normalize_code():
    assert normalize_code("AZ-1501") == "AZ-1501"
    assert normalize_code(" aza-000001 ") == "AZA-000001"
    assert normalize_code("ADHOC-20261020-1305") == "ADHOC-20261020-1305"
    for bad in ("AZ-", "ABC-1", "../x", "", "AZA-123", "AZ-1/../x", "AZ-1\nX"):
        assert normalize_code(bad) is None


def test_adhoc_code():
    code = adhoc_code(datetime(2026, 10, 20, 13, 5))
    assert code == "ADHOC-20261020-1305"
    assert normalize_code(code) == code


def test_now_ts_has_offset_and_millis():
    ts = now_ts()
    parsed = datetime.fromisoformat(ts)
    assert parsed.utcoffset() is not None
    assert len(parsed.isoformat(timespec="milliseconds")) == len(ts)


def test_round_trip(tmp_path):
    e = make()
    append(e, tmp_path)
    entries, skipped = read_show("AZ-1501", tmp_path)
    assert entries == [e] and skipped == 0
    assert (log_dir(tmp_path) / "AZ-1501.jsonl").exists()


def test_append_to_existing_and_unicode(tmp_path):
    append(make(show="Đêm nhạc"), tmp_path)
    append(make(kind="revert"), tmp_path)
    entries, _ = read_show("AZ-1501", tmp_path)
    assert [x.kind for x in entries] == ["repair", "revert"]
    assert "Đêm nhạc" in (log_dir(tmp_path) / "AZ-1501.jsonl").read_text(encoding="utf-8")


def test_corrupt_and_unknown_version_skipped(tmp_path):
    append(make(), tmp_path)
    path = log_dir(tmp_path) / "AZ-1501.jsonl"
    with path.open("a", encoding="utf-8") as h:
        h.write("\n{not json\n")
        h.write(json.dumps({**make().to_json(), "v": 99}) + "\n")
        h.write("[1]\n")
    with pytest.warns(UserWarning):
        entries, skipped = read_show("AZ-1501", tmp_path)
    assert len(entries) == 1 and skipped == 3


def test_read_missing_show(tmp_path):
    assert read_show("AZ-9", tmp_path) == ([], 0)


def test_bad_code_refused(tmp_path):
    with pytest.raises(ValueError):
        append(make(code="../x"), tmp_path)
    with pytest.raises(ValueError):
        read_show("../x", tmp_path)


def test_list_shows_tallies(tmp_path):
    assert list_shows(tmp_path) == []
    append(make(ts="2026-10-20T10:00:00.000+07:00"), tmp_path)
    append(make(outcome="clamped", ts="2026-10-20T11:00:00.000+07:00"), tmp_path)
    append(make(outcome="no_reply", ts="2026-10-20T12:00:00.000+07:00"), tmp_path)
    append(make(kind="revert", ts="2026-10-20T12:30:00.000+07:00"), tmp_path)
    append(make(code="AZA-000002", ts="2026-10-21T09:00:00.000+07:00"), tmp_path)
    (log_dir(tmp_path) / "notes.txt").write_text("x")
    shows = list_shows(tmp_path)
    assert [s.code for s in shows] == ["AZA-000002", "AZ-1501"]
    s = shows[1]
    assert (s.writes, s.sent, s.clamped, s.no_reply, s.reverts) == (4, 2, 1, 1, 1)
    assert s.first_ts.startswith("2026-10-20T10") and s.last_ts.startswith("2026-10-20T12:30")
    assert s.show == "BIDV Gala" and s.venue == "GEM" and s.skipped == 0


def test_writelog_never_imports_net():
    root = Path(__file__).parent.parent / "wing_parser" / "writelog"
    files = list(root.glob("*.py"))
    assert files
    for f in files:
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = ["." * node.level + (node.module or "")]
            for n in names:
                assert "wing_parser.net" not in n and not n.lstrip(".").startswith("net"), (f, n)
