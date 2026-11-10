"""Full-auto loop: pure, fake desk (a dict document) and fake clock."""

import copy
import json

import pytest

from conftest import USER_FILES
from wing_parser import WingScene
from wing_parser.automix import AutomixOptions, Change, Proposal
from wing_parser.automix.live_limits import LiveLimits
from wing_parser.automix.live_loop import LiveAutomix, LoopState
from wing_parser.core.loader import parse_raw
from wing_parser.edit import pointer

OPTIONS = AutomixOptions("pop")


class Desk:
    def __init__(self, document, fail=False):
        self.doc, self.fail, self.writes = document, fail, []

    def read(self):
        return copy.deepcopy(self.doc)

    def write(self, path, value):
        if self.fail:
            raise OSError("desk offline")
        self.writes.append((path, value))
        pointer.write(self.doc, path, value)


class Clock:
    now = 0.0

    def __call__(self):
        return self.now


def _change(path, before, after, stage):
    return Change(path, before, after, stage, "ch.1", "label", "why", (), "high")


def _fake_propose(targets):
    """propose_fn that always aims the live document at `targets` {path: (after, stage)}."""
    def run(scene, document, options):
        changes = [_change(p, pointer.read(document, p), after, stage)
                   for p, (after, stage) in targets.items() if pointer.read(document, p) != after]
        return Proposal(options, tuple(changes), (), (), 0.0)
    return run


def _loop(desk, targets, **kwargs):
    return LiveAutomix(OPTIONS, lambda doc: None, desk.read, desk.write, Clock(),
                       propose_fn=_fake_propose(targets), **kwargs)


def _doc(**leaves):
    return {"ae_data": {"ch": {"1": {"fdr": leaves.get("fdr", -20.0),
                                     "eq": {"1g": leaves.get("g", 0.0), "1f": 200.0},
                                     "flt": {"lcf": 80.0}, "mute": False}}}}


def test_converges_in_steps_never_exceeding_limits():
    desk = Desk(_doc(fdr=-30.0, g=0.0))
    loop = _loop(desk, {"ae_data.ch.1.fdr": (-20.0, "fader"), "ae_data.ch.1.eq.1g": (-4.0, "eq")})
    previous = {"ae_data.ch.1.fdr": -30.0, "ae_data.ch.1.eq.1g": 0.0}
    ticks = 0
    while loop.tick().pending and ticks < 20:
        ticks += 1
    assert ticks == 6 and pointer.read(desk.doc, "ae_data.ch.1.fdr") == -20.0
    assert pointer.read(desk.doc, "ae_data.ch.1.eq.1g") == -4.0
    for path, value in desk.writes:
        limit = 1.5 if path.endswith("fdr") else 1.0
        assert abs(value - previous[path]) <= limit + 1e-9
        previous[path] = value


def test_max_writes_per_tick_and_priority_order():
    targets = {"ae_data.ch.1.flt.lcf": (120.0, "hpf"), "ae_data.ch.1.eq.1g": (-3.0, "eq"),
               "ae_data.ch.1.fdr": (-10.0, "fader")}
    desk = Desk(_doc())
    loop = _loop(desk, targets, limits=LiveLimits(max_writes_per_tick=2))
    report = loop.tick()
    assert [p for p, _ in report.written] == ["ae_data.ch.1.fdr", "ae_data.ch.1.eq.1g"]
    assert report.pending == 3


def test_operator_change_locks_path_for_the_session():
    desk = Desk(_doc(fdr=-30.0))
    loop = _loop(desk, {"ae_data.ch.1.fdr": (-10.0, "fader")})
    loop.tick()
    pointer.write(desk.doc, "ae_data.ch.1.fdr", -3.0)  # operator grabs the fader
    report = loop.tick()
    assert report.newly_locked == ("ae_data.ch.1.fdr",) and not report.written
    assert loop.locked_paths == {"ae_data.ch.1.fdr"}
    pointer.write(desk.doc, "ae_data.ch.1.fdr", -9.0)
    assert not loop.tick().written and len(desk.writes) == 1


def test_requantised_value_is_not_an_override():
    desk = Desk(_doc(fdr=-30.0))
    loop = _loop(desk, {"ae_data.ch.1.fdr": (-10.0, "fader")})
    loop.tick()
    pointer.write(desk.doc, "ae_data.ch.1.fdr", -28.6)  # desk rounded -28.5 by 0.1
    assert loop.tick().written and not loop.locked_paths


def test_forbidden_or_out_of_bounds_path_is_refused():
    desk = Desk(_doc())
    loop = _loop(desk, {"ae_data.ch.1.mute": (True, "fader"), "ae_data.ch.1.fdr": (12.0, "fader")})
    report = loop.tick()
    assert set(report.refused) == {"ae_data.ch.1.mute", "ae_data.ch.1.fdr"}
    assert not desk.writes


def test_write_error_stops_tick_and_three_failing_ticks_stop_the_loop():
    desk = Desk(_doc(), fail=True)
    loop = _loop(desk, {"ae_data.ch.1.fdr": (-10.0, "fader"), "ae_data.ch.1.eq.1g": (-3.0, "eq")})
    first = loop.tick()
    assert len(first.errors) == 1 and not first.written and loop.state is LoopState.RUNNING
    loop.tick()
    assert loop.tick().state is LoopState.FAILED
    assert loop.tick().written == () and not desk.writes


def test_success_resets_failure_streak():
    desk = Desk(_doc(), fail=True)
    loop = _loop(desk, {"ae_data.ch.1.fdr": (-10.0, "fader")})
    loop.tick()
    loop.tick()
    desk.fail = False
    assert loop.tick().written
    desk.fail = True
    pointer.write(desk.doc, "ae_data.ch.1.fdr", -20.0)
    loop.tick()
    assert loop.state is LoopState.RUNNING


def test_stop_halts_writes_and_due_follows_clock():
    desk = Desk(_doc())
    loop = _loop(desk, {"ae_data.ch.1.fdr": (-10.0, "fader")})
    assert loop.due()
    loop.tick()
    assert not loop.due()
    loop.clock.now = 2.0
    assert loop.due()
    loop.stop()
    assert loop.state is LoopState.STOPPED and not loop.tick().written and len(desk.writes) == 1


def test_real_scene_converges_within_limits():
    path = USER_FILES / "LIVE.snap"
    if not path.exists():
        pytest.skip("LIVE.snap not present")
    desk = Desk(json.loads(path.read_text(encoding="utf-8")))
    loop = LiveAutomix(AutomixOptions("pop", stages=frozenset({"fader", "eq", "hpf"})),
                       lambda doc: WingScene(parse_raw(doc, path)), desk.read, desk.write, Clock())
    reports = [loop.tick() for _ in range(40)]
    assert any(r.written for r in reports)
    assert all(len(r.written) <= 10 and not r.errors for r in reports)
    assert reports[-1].pending == 0 and not loop.locked_paths


def test_unresolved_leaves_are_neither_written_nor_locked():
    desk = Desk(_doc(fdr=-30.0))
    unknown = {"ae_data.ch.1.fdr"}
    targets = {"ae_data.ch.1.fdr": (-10.0, "fader"), "ae_data.ch.1.eq.1g": (-3.0, "eq")}
    loop = _loop(desk, targets, unknown_fn=lambda: frozenset(unknown))
    report = loop.tick()
    assert [p for p, _ in report.written] == ["ae_data.ch.1.eq.1g"]
    assert report.pending >= 2 and not loop.locked_paths
    unknown.clear()
    assert "ae_data.ch.1.fdr" in [p for p, _ in loop.tick().written]


def test_clamped_readback_is_not_an_operator_override():
    class Clamping(Desk):
        def write(self, path, value):
            clamped = round(value - 1.0, 2)
            super().write(path, clamped)
            return clamped

    desk = Clamping(_doc(fdr=-30.0))
    loop = _loop(desk, {"ae_data.ch.1.fdr": (-10.0, "fader")})
    loop.tick()
    report = loop.tick()
    assert report.written and not loop.locked_paths and not report.newly_locked


def test_frequency_tolerance_is_relative():
    limits = LiveLimits()
    assert limits.tolerance_for("ae_data.ch.1.eq.1f", 4000.0) == 40.0
    assert limits.tolerance_for("ae_data.ch.1.fdr", 4000.0) == limits.tolerance
