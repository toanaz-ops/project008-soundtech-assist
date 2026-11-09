"""Pure verdict-summary report: counts, order, candidate flag, notes."""

from wing_parser.advisory.feedback import Verdict


def _v(rule, verdict, note="", when="2026-11-01T10:00:00+00:00", layer="L1"):
    return Verdict(finding_id=f"{rule}:x", rule_id=rule, layer=layer,
                   verdict=verdict, note=note, scene="s", target="x",
                   recorded_at=when)


def _report(entries):
    from wing_parser.advisory.feedback_report import build_report
    return build_report(entries)


def test_empty_log_gives_empty_report():
    assert _report([]) == []


def test_counts_per_rule():
    rows = _report([_v("G1", "correct"), _v("G1", "false-positive"),
                    _v("G1", "irrelevant"), _v("G1", "irrelevant")])
    assert len(rows) == 1
    row = rows[0]
    assert (row.rule_id, row.correct, row.false_positive, row.irrelevant) == (
        "G1", 1, 1, 2)
    assert row.layer == "L1"


def test_sorted_by_rejections_then_rule_id():
    rows = _report([_v("B", "false-positive"), _v("A", "irrelevant"),
                    _v("C", "false-positive"), _v("C", "irrelevant"),
                    _v("D", "correct")])
    assert [r.rule_id for r in rows] == ["C", "A", "B", "D"]


def test_candidate_threshold():
    rejected = [_v("R", "false-positive")] * 2 + [_v("R", "irrelevant")]
    assert _report(rejected)[0].candidate is True            # 3 > 0
    assert _report(rejected[:2])[0].candidate is False       # only 2
    tie = rejected + [_v("R", "correct")] * 3
    assert _report(tie)[0].candidate is False                # 3 not > 3
    assert _report(rejected + [_v("R", "correct")] * 2)[0].candidate is True


def test_notes_drop_empty_and_newest_first():
    rows = _report([
        _v("G", "correct", "old", when="2026-11-01T10:00:00+00:00"),
        _v("G", "irrelevant", "   ", when="2026-11-02T10:00:00+00:00"),
        _v("G", "false-positive", "new", when="2026-11-03T10:00:00+00:00"),
        _v("G", "correct", "", when="2026-11-04T10:00:00+00:00"),
    ])
    assert rows[0].notes == ("new", "old")
    assert rows[0].last == "2026-11-04T10:00:00+00:00"
