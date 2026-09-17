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
    "cancel",
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
    (LiveState.WATCHING, "disconnect"): LiveState.DISCONNECTED,
    (LiveState.CONNECTING, "cancel"): LiveState.DISCONNECTED,
    (LiveState.WALKING, "cancel"): LiveState.CONNECTED,
    (LiveState.PULLING, "cancel"): LiveState.CONNECTED,
    (LiveState.ERROR, "connect"): LiveState.CONNECTING,
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
    assert allowed_actions(LiveState.CONNECTING) == frozenset({"cancel"})
    assert allowed_actions(LiveState.CONNECTED) == frozenset(
        {"disconnect", "discover", "pull", "watch", "export", "rerun"}
    )
    assert allowed_actions(LiveState.WALKING) == frozenset({"cancel"})
    assert allowed_actions(LiveState.PULLING) == frozenset({"cancel"})
    assert allowed_actions(LiveState.WATCHING) == frozenset(
        {"stop", "disconnect", "export"}
    )
    assert allowed_actions(LiveState.ERROR) == frozenset(
        {"connect", "disconnect"}
    )
    assert allowed_actions(LiveState.LOST) == frozenset({"connect", "disconnect"})


def test_error_and_lost_both_reconnect_in_one_click():
    """Task-13 orchestrator ruling; `error` used to need a reset first.

    Two failed states offering the same way back, so what separates them
    is no longer in this table at all -- it is the view: `lost` keeps
    the events it already collected on screen and shows Reconnect
    (`live_watch_bar.py:80`), `error` shows the failure line. A test
    that asserted the difference HERE would now be asserting a
    difference the machine does not make.
    """
    for state in (LiveState.LOST, LiveState.ERROR):
        assert transition(state, "connect") is LiveState.CONNECTING
        assert "connect" in allowed_actions(state)


def test_every_button_driven_event_is_offered_by_the_state_it_fires_from():
    """The two halves of the table must agree, or a page wedges.

    `_ACTIONS` enables a button; `_TABLE` accepts the event that button
    fires. Both mismatches are real bugs and both were present before
    task 13: `watching` offered Disconnect with no row to accept it (the
    page's `transition` would have raised on the click), and `cancel`
    had a row in neither half although Cancel is the ONLY way out of the
    three busy states. `ok`, `fail` and `lost` are outcomes a worker
    reports rather than buttons, and `walk` is fired by two buttons
    whose action names are `discover` and `rerun`, so the mapping below
    is written out rather than assumed to be identity.
    """
    fired_by = {
        "connect": "connect", "disconnect": "disconnect",
        "stop": "stop", "watch": "watch", "cancel": "cancel",
        "pull": "pull", "walk": "discover",
    }
    for (state, event), _target in DOCUMENTED.items():
        action = fired_by.get(event)
        if action is None:
            continue                    # an outcome, not a button
        assert action in allowed_actions(state), (
            f"{state.value} accepts {event!r} but enables no button for it"
        )
