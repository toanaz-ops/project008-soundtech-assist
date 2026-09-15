"""The live connection state machine (design spec S6). No Qt import.

`LiveState` names every state the console connection can be in;
`transition()` and `allowed_actions()` are both plain lookup tables so a
pytest can exhaust every (state, event) pair and every state's button
set -- no `if` chains, no scattered `setEnabled` calls hidden in the
page. `transition()` raises on an illegal pair rather than silently
staying put: a page that fires an event its own state does not expect
is a bug, and this makes it fail loudly instead of freezing quietly.

`pulling` and `lost` are states of their own, not flags on `connected`:
`take_snapshot` runs its own walk plus ~25,062 leaf reads and every
other action must be refused while it runs, and `lost` differs from
`error` in that the event list stays on screen -- a watch that lost the
desk mid-stream still has everything it already collected. That is now
the WHOLE difference: task 13 ruled that `error` reconnects in one
click too, so the two states hold identical rows here and only the view
tells them apart.
"""

from __future__ import annotations

from enum import Enum


class LiveState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    WALKING = "walking"
    PULLING = "pulling"
    WATCHING = "watching"
    ERROR = "error"
    LOST = "lost"


# Every row traces to spec S6, but not every row is a literal arrow in
# its ASCII diagram -- two are inferred from adjacent prose, two from a
# diagram arrow that does not name its events, and one from the task-1
# brief's own test:
#   (CONNECTED, "disconnect")  -- S6's Connect/Disconnect button pair,
#                                 not drawn as a return arrow
#   (WATCHING, "stop")         -- S7.2: "a watch ends on Stop"
#   (ERROR, "reset")           -- error needs a documented way back to
#   (ERROR, "disconnect")         disconnected; the diagram shows the
#                                 arrow but not which event(s) fire it
#   (LOST, "connect")          -- not in the diagram at all; dictated by
#                                 the task-1 brief's own test
#                                 (test_lost_is_not_error_because_it_still_allows_reconnect)
# Every other row below is a literal drawn arrow. Anything not listed
# here is illegal and transition() raises for it.
#
# Five rows are task 13's, added when the page that fires these events
# was finally assembled and the two halves of this module were made to
# agree (orchestrator ruling, disclosed here as asked):
#   (ERROR, "connect")         -- RULED: error reconnects in one click,
#                                 like lost. It no longer has to reset
#                                 first, which is why `error` and `lost`
#                                 now hold the same rows; what still
#                                 separates them is the view, not this
#                                 table (live_watch_bar.py:80, and the
#                                 event list `lost` keeps on screen).
#   (WATCHING, "disconnect")   -- a MISMATCH, not a new feature:
#                                 _ACTIONS[WATCHING] has offered
#                                 `disconnect` since task 1 and
#                                 ConnectBar's Disconnect button is live
#                                 there, so the page's own transition()
#                                 would have raised on that click.
#   (CONNECTING, "cancel")     -- the same mismatch, the other way: the
#   (WALKING, "cancel")           Cancel button is the ONLY way out of
#   (PULLING, "cancel")           the three busy states and had a row in
#                                 neither half. The targets are exactly
#                                 the panels' own `_cancel_fallback`
#                                 (live_connect_bar.py:153-156,
#                                 live_discovery.py:126-129,
#                                 live_snapshot.py:170-173).
# The rule those four enforce, checked by
# test_every_button_driven_event_is_offered_by_the_state_it_fires_from:
# every event a state accepts that a BUTTON fires must also be in that
# state's _ACTIONS. `ok`, `fail` and `lost` are outcomes a worker
# reports, not buttons, and are deliberately absent from _ACTIONS.
_TABLE: dict[tuple[LiveState, str], LiveState] = {
    (LiveState.DISCONNECTED, "connect"): LiveState.CONNECTING,
    (LiveState.CONNECTING, "ok"): LiveState.CONNECTED,
    (LiveState.CONNECTING, "fail"): LiveState.ERROR,
    (LiveState.CONNECTING, "cancel"): LiveState.DISCONNECTED,
    (LiveState.CONNECTED, "walk"): LiveState.WALKING,
    (LiveState.CONNECTED, "pull"): LiveState.PULLING,
    (LiveState.CONNECTED, "watch"): LiveState.WATCHING,
    (LiveState.CONNECTED, "disconnect"): LiveState.DISCONNECTED,
    (LiveState.WALKING, "ok"): LiveState.CONNECTED,
    (LiveState.WALKING, "fail"): LiveState.ERROR,
    (LiveState.WALKING, "cancel"): LiveState.CONNECTED,
    (LiveState.PULLING, "ok"): LiveState.CONNECTED,
    (LiveState.PULLING, "fail"): LiveState.ERROR,
    (LiveState.PULLING, "cancel"): LiveState.CONNECTED,
    (LiveState.WATCHING, "stop"): LiveState.CONNECTED,
    (LiveState.WATCHING, "lost"): LiveState.LOST,
    (LiveState.WATCHING, "disconnect"): LiveState.DISCONNECTED,
    (LiveState.ERROR, "connect"): LiveState.CONNECTING,
    (LiveState.ERROR, "reset"): LiveState.DISCONNECTED,
    (LiveState.ERROR, "disconnect"): LiveState.DISCONNECTED,
    (LiveState.LOST, "connect"): LiveState.CONNECTING,
    (LiveState.LOST, "reset"): LiveState.DISCONNECTED,
    (LiveState.LOST, "disconnect"): LiveState.DISCONNECTED,
}

# One row per state: which page actions its buttons enable. The three
# busy states refuse everything but `cancel` -- they forbid starting a
# second action while one is in flight, and Cancel is the one way out of
# them. Action names, not event names: `discover` and `rerun` are two
# buttons firing the one `walk` event, and `export` fires no event at
# all (it writes a file; the desk does not move).
_ACTIONS: dict[LiveState, frozenset[str]] = {
    LiveState.DISCONNECTED: frozenset({"connect"}),
    LiveState.CONNECTING: frozenset({"cancel"}),
    LiveState.CONNECTED: frozenset(
        {"disconnect", "discover", "pull", "watch", "export", "rerun"}
    ),
    LiveState.WALKING: frozenset({"cancel"}),
    LiveState.PULLING: frozenset({"cancel"}),
    LiveState.WATCHING: frozenset({"stop", "disconnect", "export"}),
    LiveState.ERROR: frozenset({"connect", "disconnect"}),
    LiveState.LOST: frozenset({"connect", "disconnect"}),
}


def transition(state: LiveState, event: str) -> LiveState:
    """The state reached by firing `event` in `state`.

    Raises `ValueError`, naming both, for any pair spec S6 does not
    document -- never silently returns `state` unchanged.
    """
    try:
        return _TABLE[(state, event)]
    except KeyError:
        raise ValueError(
            f"illegal event {event!r} in state {state.value!r}"
        ) from None


def allowed_actions(state: LiveState) -> frozenset[str]:
    """The page actions enabled while in `state`."""
    return _ACTIONS[state]
