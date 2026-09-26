"""`is_fixable_anomaly`: whether `apply_repairs` would touch the entry an
anomaly names (Task 9 fix round 1, spec §6)."""
from __future__ import annotations

from wing_parser.showcontext.rewrite import is_fixable_anomaly


def test_an_expects_repair_message_is_fixable():
    assert is_fixable_anomaly("f.yaml: segment S1: expects 'gutiar' read as 'guitar'")


def test_a_cue_action_repair_message_is_fixable():
    assert is_fixable_anomaly("f.yaml: segment S1, cue c1: action 'colse' read as 'close'")


def test_a_cue_time_anomaly_is_not_fixable():
    assert not is_fixable_anomaly(
        "f.yaml: segment S1, cue c1: time 'bogus' is not T+H:MM:SS or T-MM:SS and was ignored"
    )


def test_a_segment_time_anomaly_is_not_fixable():
    assert not is_fixable_anomaly("f.yaml: segment S1: time 'bogus' is not readable and was ignored")
