"""Tests for the live connection state machine (design spec S6).

`transition()` and `allowed_actions()` are both plain lookup tables, so
these tests exhaust them rather than exercising a branchy implementation:
every documented (state, event) pair is checked against a table written
out here independently of production, every undocumented pair must
raise, and every state's action set is pinned by a written-out assertion.
"""

from __future__ import annotations

import itertools

import pytest

from wing_parser.ui.live_state import LiveState, allowed_actions, transition

ALL_EVENTS = (
    "connect",
    "ok",
    "fail",
    "disconnect",
    "reset",
    "walk",
    "pull",
    "watch",
    "stop",
    "lost",
)

# The transitions design spec S6 documents. Anything not listed here is
# illegal and must raise -- see test_every_undocumented_pair_raises.
DOCUMENTED = {
    (LiveState.DISCONNECTED, "connect"): LiveState.CONNECTING,
    (LiveState.CONNECTING, "ok"): LiveState.CONNECTED,
    (LiveState.CONNECTING, "fail"): LiveState.ERROR,
    (LiveState.CONNECTED, "walk"): LiveState.WALKING,
    (LiveState.CONNECTED, "pull"): LiveState.PULLING,
    (LiveState.CONNECTED, "watch"): LiveState.WATCHING,
    (LiveState.CONNECTED, "disconnect"): LiveState.DISCONNECTED,
    (LiveState.WALKING, "ok"): LiveState.CONNECTED,
    (LiveState.WALKING, "fail"): LiveState.ERROR,
    (LiveState.PULLING, "ok"): LiveState.CONNECTED,
    (LiveState.PULLING, "fail"): LiveState.ERROR,
    (LiveState.WATCHING, "stop"): LiveState.CONNECTED,
    (LiveState.WATCHING, "lost"): LiveState.LOST,
    (LiveState.ERROR, "reset"): LiveState.DISCONNECTED,
    (LiveState.ERROR, "disconnect"): LiveState.DISCONNECTED,
    (LiveState.LOST, "connect"): LiveState.CONNECTING,
    (LiveState.LOST, "reset"): LiveState.DISCONNECTED,
    (LiveState.LOST, "disconnect"): LiveState.DISCONNECTED,
}


def test_every_documented_pair_reaches_its_documented_target():
    for (state, event), target in DOCUMENTED.items():
        assert transition(state, event) is target


def test_every_undocumented_pair_raises():
    for state, event in itertools.product(LiveState, ALL_EVENTS):
        if (state, event) in DOCUMENTED:
            continue
        with pytest.raises(ValueError):
            transition(state, event)


def test_an_illegal_pair_raises_naming_the_state_and_the_event():
    with pytest.raises(ValueError) as excinfo:
        transition(LiveState.DISCONNECTED, "watch")
    message = str(excinfo.value)
    assert "disconnected" in message
    assert "watch" in message


def test_allowed_actions_is_pinned_for_every_state():
    assert allowed_actions(LiveState.DISCONNECTED) == frozenset({"connect"})
    assert allowed_actions(LiveState.CONNECTING) == frozenset()
    assert allowed_actions(LiveState.CONNECTED) == frozenset(
        {"disconnect", "discover", "pull", "watch", "export", "rerun"}
    )
    assert allowed_actions(LiveState.WALKING) == frozenset()
    assert allowed_actions(LiveState.PULLING) == frozenset()
    assert allowed_actions(LiveState.WATCHING) == frozenset(
        {"stop", "disconnect", "export"}
    )
    assert allowed_actions(LiveState.ERROR) == frozenset({"disconnect"})
    assert allowed_actions(LiveState.LOST) == frozenset({"connect", "disconnect"})


def test_lost_is_not_error_because_it_still_allows_reconnect():
    assert transition(LiveState.LOST, "connect") is LiveState.CONNECTING
    assert "connect" in allowed_actions(LiveState.LOST)
    # error, by contrast, cannot re-connect straight away -- it must
    # reset (or disconnect) back to disconnected first.
    assert "connect" not in allowed_actions(LiveState.ERROR)
