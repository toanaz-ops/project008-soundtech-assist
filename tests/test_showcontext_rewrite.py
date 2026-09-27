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


def test_a_time_value_containing_the_read_as_phrase_is_not_fixable():
    """Fix round 2, minor 3: a bare ' read as ' substring check would
    wrongly mark this fixable -- the phrase sits inside the TIME VALUE
    itself, not in the ': expects ... read as ...' / ', cue ...: action
    ... read as ...' shape apply_repairs actually acts on."""
    anomaly = (
        "f.yaml: segment S1: time 'junk read as junk' is not readable and was ignored"
    )
    assert not is_fixable_anomaly(anomaly)


def test_a_cue_time_value_containing_the_read_as_phrase_is_not_fixable():
    anomaly = (
        "f.yaml: segment S1, cue c1: time 'junk read as junk' is not "
        "T+H:MM:SS or T-MM:SS and was ignored"
    )
    assert not is_fixable_anomaly(anomaly)
