"""Spec §5 F3/F4/F7 and W10: the write policy layer, with no Qt in sight.

Everything here is plain objects, so `pytest` covers the rules that decide
whether a packet leaves at all -- and covers them exhaustively, which is the
whole reason these three classes are not methods on a widget.
"""
from __future__ import annotations

from wing_parser.ui.apply_level import ApplyLevel, ArmState, RevertQueue
from wing_parser.ui.write_queue import WriteQueue


class _Identity:
    """Stands in for `net.identity.WingIdentity`; this module names no net."""
    name = "WING-GIAQUY"
    serial = "01009Y90604AAE"
    ip = "192.168.128.28"


# -- ArmState (F4) ------------------------------------------------------


def test_arm_state_starts_unarmed_at_manual():
    state = ArmState()
    assert state.armed() is False
    assert state.level is ApplyLevel.MANUAL
    assert state.identity is None


def test_arming_records_the_identity_it_was_armed_for():
    state = ArmState()
    state.arm(_Identity())
    assert state.armed() is True
    assert state.identity.serial == "01009Y90604AAE"


def test_disarm_returns_to_manual_from_either_other_level():
    for level in (ApplyLevel.DELAYED, ApplyLevel.IMMEDIATE):
        state = ArmState()
        state.arm(_Identity())
        state.level = level
        state.disarm()
        assert state.armed() is False
        assert state.level is ApplyLevel.MANUAL
        assert state.identity is None


# -- RevertQueue (F7, W12) ----------------------------------------------


def test_the_revert_queue_hands_records_out_in_reverse_order():
    queue = RevertQueue(["a", "b", "c"])
    assert [queue.next(), queue.next(), queue.next()] == ["c", "b", "a"]


def test_the_revert_queue_returns_none_once_exhausted():
    queue = RevertQueue(["a"])
    assert queue.next() == "a"
    assert queue.next() is None


def test_progress_counts_what_has_been_handed_out_against_the_total():
    queue = RevertQueue(["a", "b", "c"])
    assert queue.progress == (0, 3)
    queue.next()
    assert queue.progress == (1, 3)
    queue.next()
    assert queue.progress == (2, 3)


def test_stop_ends_the_run_and_leaves_the_rest_countable():
    queue = RevertQueue(["a", "b", "c"])
    assert queue.next() == "c"
    queue.stop()
    assert queue.next() is None
    assert queue.remaining == ("b", "a")
    assert queue.progress == (1, 3)


# -- WriteQueue (W10) ---------------------------------------------------


def test_the_write_queue_starts_the_first_item_at_once():
    started = []
    queue = WriteQueue(started.append)
    queue.enqueue("one")
    assert started == ["one"]
    assert queue.in_flight == "one"


def test_two_rapid_enqueues_both_survive_and_neither_overlaps():
    started = []
    queue = WriteQueue(started.append)
    queue.enqueue("one")
    queue.enqueue("two")
    assert started == ["one"], "the second write went out while the first was in flight"
    assert queue.pending == ("two",)
    queue.settle()
    assert started == ["one", "two"]
    assert queue.pending == ()


def test_the_queue_is_fifo_not_a_stack():
    started = []
    queue = WriteQueue(started.append)
    for item in ("one", "two", "three"):
        queue.enqueue(item)
    queue.settle()
    queue.settle()
    assert started == ["one", "two", "three"]


def test_settling_an_idle_queue_is_harmless():
    started = []
    queue = WriteQueue(started.append)
    queue.settle()
    assert started == [] and queue.in_flight is None


def test_clear_drops_what_has_not_gone_out_and_keeps_the_one_in_flight():
    started = []
    queue = WriteQueue(started.append)
    queue.enqueue("one")
    queue.enqueue("two")
    queue.clear()
    assert queue.pending == ()
    assert queue.in_flight == "one", "nothing can un-send a packet already on the wire"
