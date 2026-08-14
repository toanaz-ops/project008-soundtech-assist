import json
from datetime import datetime, timezone

import pytest

from wing_parser.advisory import feedback
from wing_parser.advisory.models import Finding

FIXED = datetime(2026, 8, 13, 19, 30, tzinfo=timezone.utc)


@pytest.fixture
def knowledge(tmp_path):
    directory = tmp_path / "knowledge"
    directory.mkdir()
    return directory


def a_finding(**overrides) -> Finding:
    base = dict(
        rule_id="G8", layer="base", severity="warning",
        target="ch.8.send.8", message="post-fader monitor send",
        evidence={"mode": "POST"}, confidence=0.9,
    )
    base.update(overrides)
    return Finding(**base)


def test_finding_id_is_stable_and_readable():
    assert feedback.finding_id(a_finding()) == "G8:ch.8.send.8"
    assert feedback.finding_id(a_finding()) == feedback.finding_id(a_finding())


def test_record_appends_one_json_line(knowledge):
    feedback.record(a_finding(), "false-positive", note="shared IEM rig",
                    scene="example-Vu.snap", directory=knowledge, now=FIXED)

    lines = (knowledge / "feedback.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["finding_id"] == "G8:ch.8.send.8"
    assert entry["verdict"] == "false-positive"
    assert entry["note"] == "shared IEM rig"
    assert entry["scene"] == "example-Vu.snap"
    assert entry["layer"] == "base"
    assert entry["recorded_at"] == "2026-08-13T19:30:00+00:00"


def test_record_is_append_only(knowledge):
    feedback.record(a_finding(), "correct", directory=knowledge, now=FIXED)
    feedback.record(a_finding(target="ch.9.send.8"), "correct", directory=knowledge, now=FIXED)

    assert len(feedback.read_log(directory=knowledge)) == 2


def test_unknown_verdict_is_rejected(knowledge):
    with pytest.raises(ValueError, match="verdict"):
        feedback.record(a_finding(), "maybe", directory=knowledge, now=FIXED)


def test_read_log_on_a_missing_file_is_empty(knowledge):
    assert feedback.read_log(directory=knowledge) == []


def test_read_log_skips_a_corrupt_line(knowledge):
    path = knowledge / "feedback.jsonl"
    feedback.record(a_finding(), "correct", directory=knowledge, now=FIXED)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("this is not json\n")
    feedback.record(a_finding(target="ch.9"), "correct", directory=knowledge, now=FIXED)

    assert len(feedback.read_log(directory=knowledge)) == 2


def test_summarise_counts_verdicts_per_rule(knowledge):
    feedback.record(a_finding(), "false-positive", directory=knowledge, now=FIXED)
    feedback.record(a_finding(target="ch.9.send.8"), "false-positive", directory=knowledge, now=FIXED)
    feedback.record(a_finding(rule_id="G7", target="bus.8"), "correct", directory=knowledge, now=FIXED)

    counts = feedback.summarise(directory=knowledge)
    assert counts["G8"]["false-positive"] == 2
    assert counts["G7"]["correct"] == 1
    assert counts["G8"].get("correct", 0) == 0
