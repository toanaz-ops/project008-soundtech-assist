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
`error` in that the event list stays on screen (a watch that lost the
desk mid-stream still has everything it already collected) and a
reconnect is one click away rather than requiring a reset first.
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


# One row per documented arrow in spec S6's diagram. Anything not listed
# here is illegal and transition() raises for it.
_TABLE: dict[tuple[LiveState, str], LiveState] = {
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

# One row per state: which page actions its buttons enable. `walking`
# and `pulling` refuse everything -- the busy states above forbid
# starting a second action while one is already in flight.
_ACTIONS: dict[LiveState, frozenset[str]] = {
    LiveState.DISCONNECTED: frozenset({"connect"}),
    LiveState.CONNECTING: frozenset(),
    LiveState.CONNECTED: frozenset(
        {"disconnect", "discover", "pull", "watch", "export", "rerun"}
    ),
    LiveState.WALKING: frozenset(),
    LiveState.PULLING: frozenset(),
    LiveState.WATCHING: frozenset({"stop", "disconnect", "export"}),
    # error needs a reset back to disconnected before reconnecting --
    # only lost (see module docstring) skips that step.
    LiveState.ERROR: frozenset({"disconnect"}),
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
