"""Tests for wing_parser.writelog.report (no Qt)."""

from wing_parser.writelog import REPORT_LABEL_KEYS, ShowSummary, render_html

from wing_parser.writelog import LogEntry


def make(outcome="sent", kind="repair", **kw):
    base = dict(
        v=1, ts="2026-10-20T13:05:12.481+07:00", show_code="AZ-1501", show="BIDV Gala", venue="GEM",
        desk={"name": "W", "serial": "S1", "firmware": "3.1"}, kind=kind, finding="G7:bus.iem.3",
        label="L", address="/a", path="p", file_before=0, desk_before=0, written=1, readback=1,
        outcome=outcome, scene="x.snap", app="0.1.0",
    )
    base.update(kw)
    return LogEntry(**base)


LABELS = {k: f"[{k}]" for k in REPORT_LABEL_KEYS}


def summary(**kw):
    base = dict(code="AZ-1501", show="BIDV Gala", venue="GEM", first_ts="2026-10-20T10:00:00.000+07:00",
                last_ts="2026-10-20T12:00:00.000+07:00", writes=3, sent=1, clamped=1, no_reply=1,
                reverts=0, skipped=0)
    base.update(kw)
    return ShowSummary(**base)


def test_escapes_script_everywhere():
    s = summary(show="<script>alert(1)</script>")
    e = make(show="<script>alert(1)</script>", label="<b>x</b>", desk={"name": "<i>W</i>"})
    out = render_html(s, [e], LABELS, "2026-10-21 08:00")
    assert "<script" not in out.lower()
    assert "&lt;script&gt;" in out and "&lt;b&gt;x&lt;/b&gt;" in out and "&lt;i&gt;W&lt;/i&gt;" in out


def test_self_contained_and_counts():
    es = [make(), make(outcome="clamped"), make(outcome="no_reply"), make(kind="revert")]
    out = render_html(summary(writes=4, reverts=1), es, LABELS, "t")
    assert out.startswith("<!DOCTYPE html>") and "<style>" in out
    for bad in ("http://", "https://", "<link", "<script", "src="):
        assert bad not in out
    for badge in ("✓", "⚠", "✗"):
        assert badge in out
    assert "AZ-1501" in out and "G7:bus.iem.3" in out
    for k in REPORT_LABEL_KEYS:
        assert LABELS[k] in out


def test_missing_label_and_none_values():
    out = render_html(summary(), [make(desk=None, finding=None, desk_before=None, readback=None)], {}, "t")
    assert "<table" in out
