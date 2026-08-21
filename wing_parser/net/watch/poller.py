"""The loop: sample, compare with the previous sample, yield differences.

`clock` and `sleep` are parameters so a test can drive many rounds
without waiting for any of them. The loop paces itself rather than
spinning: S2.4 measured a 208-leaf round at well under the default
interval, so a quiet desk should leave the network almost entirely idle
between rounds.
"""

from __future__ import annotations

import time
from typing import Callable, Iterable, Iterator, Sequence

from wing_parser.net.client import WingClient
from wing_parser.net.codec import leaf_value
from wing_parser.net.watch.events import Change, split_address
from wing_parser.net.watch.list import WatchList

DEFAULT_INTERVAL = 0.25


def read_labels(client: WingClient, strips: Iterable[str]) -> dict[str, str]:
    """One batch for every strip's name, read once at startup.

    Names are read from the ordinary `name` leaf, not `$name`: both exist
    (measured 2026-08-21), and `name` is the one the .snap carries, so a
    label here matches what every other command prints.
    """
    wanted = [f"{strip}/name" for strip in strips]
    if not wanted:
        return {}
    result = client.get_many(wanted)
    labels: dict[str, str] = {}
    for address, message in result.replies.items():
        strip = address.rpartition("/")[0]
        try:
            value, _display = leaf_value(message)
        except ValueError:
            continue
        labels[strip] = str(value)
    return labels


def sample(client: WingClient, addresses: Sequence[str]) -> dict[str, object]:
    """One round. Absent addresses are simply missing from the result --
    never present with a fabricated value."""
    result = client.get_many(list(addresses))
    values: dict[str, object] = {}
    for address, message in result.replies.items():
        try:
            value, _display = leaf_value(message)
        except ValueError:
            # A reply that is not a leaf triplet is not a value. Skipping
            # it keeps a malformed round from looking like a change.
            continue
        values[address] = value
    return values


def watch(
    client: WingClient,
    watch_list: WatchList,
    *,
    interval: float = DEFAULT_INTERVAL,
    duration: float | None = None,
    max_rounds: int | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> Iterator[Change]:
    """Yield a Change for every difference between consecutive rounds.

    `duration` bounds a real session in seconds. `max_rounds` bounds one
    in rounds, which is what a test needs: this loop calls `clock()`
    twice per round plus once per change, so how much simulated time a
    run consumes depends on the data, and a wall-clock bound would make
    a test's round count data-dependent too.
    """
    addresses = list(watch_list.addresses)
    strips = sorted({split_address(a)[0] for a in addresses})
    labels = read_labels(client, strips)

    previous = sample(client, addresses)
    started = clock()
    rounds = 0

    while True:
        if max_rounds is not None and rounds >= max_rounds:
            return
        now = clock()
        if duration is not None and now - started >= duration:
            return
        rounds += 1

        round_started = now
        current = sample(client, addresses)

        for address, after in current.items():
            before = previous.get(address)
            if before is None or before == after:
                continue
            strip, key = split_address(address)
            yield Change(
                address=address,
                strip=strip,
                key=key,
                label=labels.get(strip, ""),
                before=before,
                after=after,
                elapsed=clock() - started,
            )

        # Carry forward, never overwrite with a gap: an address that went
        # silent keeps its last known value, so the next answer is
        # compared against a real reading rather than against nothing.
        previous.update(current)

        remaining = interval - (clock() - round_started)
        if remaining > 0:
            sleep(remaining)
