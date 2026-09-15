"""The one place a watch can be interrupted, or judged dead. No Qt, no `net`.

Spec S7.1 puts `RoundGuard` in the controller; it lives here instead so
`live_controller.py` stays inside the file ceiling, and the split costs
nothing because this module names **no** `net` type at all. It wraps
whatever object offers `get_many(addresses, **kw)` and hands back
whatever that returns, reading only `.replies` off the result. So the
"only `live_controller.py` may name `net`" rule still holds, and the
guard is testable against an object `net/` has never heard of.

`GeneratorWorker` (spec S7.3) holds none of this logic: it only
translates `Cancelled` and `DeskLost` into signals. Everything that
decides *whether* to stop is here, in plain Python, so plain pytest
covers it.
"""

from __future__ import annotations

import threading
from typing import Any, Callable


class Cancelled(Exception):
    """Stop was pressed. Not a failure -- the operator asked."""


class DeskLost(OSError):
    """The desk stopped answering entirely, for `rounds` rounds running.

    Raising is not a style choice (D6). `poller.watch` yields only on a
    `Change` (`poller.py:101-114`), and it carries a silent address's
    previous value forward on purpose (`:116-119`), so a desk that has
    gone away produces **no output at all** -- there is nothing for a
    caller to inspect and conclude "lost" from. An `OSError` because
    that is what every other live-read failure already is.
    """

    def __init__(self, host: str, rounds: int) -> None:
        super().__init__(
            f"{host} stopped answering: {rounds} consecutive round(s) "
            f"read nothing at all"
        )
        self.host = host
        self.rounds = rounds


class RoundGuard:
    """A counting proxy around a watch's client. Cancel in, desk-lost out.

    Delegates `request`, `close` and the context-manager pair untouched;
    every `get_many` is bracketed:

    **Before** -- cancel set, raise `Cancelled`. This check cannot live
    in the `sleep` `poller.watch` accepts, because the poller sleeps only
    when `remaining > 0` (`poller.py:121-123`): against a desk slower
    than the interval that line is never reached, and a cancel there
    would never be observed. Here, stop latency is bounded by one round
    whatever the desk's speed.

    **After** -- report `answered` against `total` to `on_round`, and
    raise `DeskLost` once `lost_after` rounds in a row have answered
    nothing. One answering round clears the run: a single dropped batch
    on a busy network is not a lost desk.
    """

    def __init__(
        self,
        client: Any,
        host: str,
        cancel: threading.Event,
        on_round: Callable[[int, int], None] = lambda answered, total: None,
        lost_after: int = 3,
    ) -> None:
        self._client = client
        self.host = host
        self._cancel = cancel
        self._on_round = on_round
        self._lost_after = lost_after
        self._silent_rounds = 0

    def get_many(self, addresses: Any, **kwargs: Any) -> Any:
        if self._cancel.is_set():
            raise Cancelled(f"watch on {self.host} stopped before the next round")
        addresses = list(addresses)
        result = self._client.get_many(addresses, **kwargs)

        answered = len(result.replies)
        self._on_round(answered, len(addresses))
        if answered:
            self._silent_rounds = 0
        else:
            self._silent_rounds += 1
            if self._silent_rounds >= self._lost_after:
                raise DeskLost(self.host, self._silent_rounds)
        return result

    def request(self, address: str, **kwargs: Any) -> Any:
        return self._client.request(address, **kwargs)

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "RoundGuard":
        self._client.__enter__()
        # The guard, never the bare client: a caller handed the client
        # back would run its rounds unwatched and unstoppable.
        return self

    def __exit__(self, *exc_info: object) -> Any:
        return self._client.__exit__(*exc_info)


def watch_rate(events: int, seconds: float) -> tuple[float, float]:
    """Events per second, and the elapsed seconds themselves.

    A plain function so `LiveEventsView` holds no arithmetic. Zero rather
    than a `ZeroDivisionError` at time zero: the view renders a rate from
    the moment Start is pressed, which is before any time has passed.
    """
    return (events / seconds if seconds > 0 else 0.0, seconds)
