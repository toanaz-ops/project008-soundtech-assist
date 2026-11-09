"""Wave 6 (2026-11-09): the Arm dialog's soft "desk may be in use" signal."""
from __future__ import annotations

import pytest

from wing_parser.ui.desk_activity import DeskActivity


def test_counts_fader_and_mute_changes_in_window():
    a = DeskActivity()
    a.record("/ch/8/$fdr", 100.0)
    a.record("/bus/2/$mute", 110.0)
    a.record("/main/1/$fdr", 120.0)
    assert a.recent_motion(125.0) == 3


def test_window_edge_excludes_exactly_30_seconds_old():
    a = DeskActivity()
    a.record("/ch/1/$fdr", 100.0)
    assert a.recent_motion(129.9) == 1
    assert a.recent_motion(130.0) == 0


@pytest.mark.parametrize("path", [
    "/ch/1/$solo", "/ch/1/$name", "/dca/1/$solo", "/mtx/1/$fdr",
    "/ch/1/$fdrx", "/io/in/1/$mute", "garbage", ""])
def test_other_paths_are_ignored(path):
    a = DeskActivity()
    a.record(path, 100.0)
    assert a.recent_motion(101.0) == 0


@pytest.mark.parametrize("path", ["/ch/1/fdr", "/ch/1/mute", "/main/2/$mute"])
def test_bare_and_dollar_leaves_both_count(path):
    a = DeskActivity()
    a.record(path, 100.0)
    assert a.recent_motion(101.0) == 1


def test_empty_tracker_reports_zero():
    assert DeskActivity().recent_motion(5.0) == 0
