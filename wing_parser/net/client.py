"""UDP request/reply transport for WING's OSC control port, 2223.

`net/codec.py` owns the bytes; this module owns the socket, and exists
almost entirely because of one hazard measured against the lab console
(design doc sec 2.4(b)): an oversized node-dump reply kills the console's
reply stream to whatever *source port* sent it, and every later reply on
that same batch is lost -- not delayed, lost. The only measured recovery
is a brand-new socket (a fresh source port), which came back 20/20 on
retry. A missing address, by contrast, is harmless on its own (sec
2.4(b) item 2): it just produces silence for that one request while the
rest of the batch keeps arriving. So the rule this module encodes is:
single misses are normal and never trigger anything; a *short batch* is
the signal that something poisoned the stream, and the fix is to rotate
before resending -- never retry on the same socket.

Two request shapes, both built on `codec.encode`/`codec.decode`:

- `request()` -- one address, one reply or `None` on timeout. Timeouts are
  expected (sec 2.4(b)), not exceptional, so this never raises for one.
- `get_many()` -- the performance path (sec 2.5: 2822 reads/s pipelined,
  batch 200). Fires a whole batch before reading any reply back, matches
  replies to requests by OSC address since they arrive out of order, then
  retries whatever a batch didn't answer -- on a rotated socket -- for a
  bounded number of rounds, and reports what still didn't answer rather
  than swallowing it.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass
from typing import Iterable

from wing_parser.net.codec import OscMessage, decode, encode

OSC_PORT = 2223

# Sec 2.5: 10,760 reads at batch 200 = 3.81s, 8 lost (0.07%); batch 500 was
# both slower (4.86s) and lossier (27 lost). Do not change without new
# measurements -- the doc is explicit that 200 beats 500 on both axes.
DEFAULT_BATCH_SIZE = 200

# Not a measured figure -- the doc establishes that a retry pass is
# "mandatory, not optional" and that one retry-on-a-fresh-socket recovered
# 20/20, but does not say how many rounds to budget for a worse night on a
# real network. Two rounds (three sends total) gives headroom over that
# single measured retry without letting a genuinely absent address loop
# indefinitely.
DEFAULT_RETRY_ROUNDS = 2

# No per-request timeout is measured for port 2223 either. net/identity.py's
# query_identity() (the sibling handshake on port 2222) defaults to 2.0s;
# reused here rather than inventing an unrelated number for the same console.
DEFAULT_TIMEOUT = 2.0

# Pipelining means replies trickle in, not arrive as one block, so a batch
# has no single natural deadline. Instead: keep collecting as long as
# packets keep showing up, and stop once this long passes with nothing new
# -- a genuine drop (sec 2.4(b)) never arrives at all, so waiting longer
# after the last arrival only slows down the unresolved case, never helps it.
DEFAULT_IDLE_TIMEOUT = 0.2

_RECV_BUFSIZE = 4096


@dataclass(frozen=True)
class BatchResult:
    """What a pipelined batch (plus its retries) actually resolved.

    `unresolved` is kept as its own field rather than just returning a
    possibly-short `replies` dict so a caller can tell "this address does
    not exist" (sec 2.4(b): harmless, expected) from "we gave up after
    retrying" -- and so an address that legitimately replies with an empty
    payload (present in `replies`, e.g. typetag "") is never confused with
    one that never answered at all (absent from `replies`, present here).
    """

    replies: dict[str, OscMessage]
    unresolved: tuple[str, ...]


class WingClient:
    """One OSC session against a console's port 2223.

    A context manager so a caller never has to remember to close the
    socket; `get_many()` may replace `_sock` mid-call (see `_rotate`), so
    `close()` always closes whichever socket is current.
    """

    def __init__(
        self,
        host: str,
        port: int = OSC_PORT,
        timeout: float = DEFAULT_TIMEOUT,
        idle_timeout: float = DEFAULT_IDLE_TIMEOUT,
    ) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout
        self._idle_timeout = idle_timeout
        self._sock = self._new_socket()

    def _new_socket(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self._timeout)
        return sock  # unbound: the OS assigns a fresh ephemeral source port
        # on first sendto(), which is exactly the "rotation" sec 2.4(b) needs.

    def _rotate(self) -> None:
        # Only measured recovery from a poisoned reply stream (sec
        # 2.4(b)): a short batch always gets a new source port first.
        old_sock = self._sock
        self._sock = self._new_socket()
        old_sock.close()

    def __enter__(self) -> "WingClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        self._sock.close()

    # -- single request/reply --------------------------------------------

    def request(self, address: str) -> OscMessage | None:
        # `None` on timeout, not a raise: sec 2.4(b) measured that a GET
        # on a missing address simply produces no reply -- expected, not
        # an error.
        self._sock.sendto(encode(address), (self._host, self._port))
        try:
            data, _ = self._sock.recvfrom(_RECV_BUFSIZE)
        except socket.timeout:
            return None
        return decode(data)

    # -- pipelined batch, with retry-on-rotated-socket -----------------------

    def get_many(
        self,
        addresses: Iterable[str],
        batch_size: int = DEFAULT_BATCH_SIZE,
        retry_rounds: int = DEFAULT_RETRY_ROUNDS,
    ) -> BatchResult:
        # Round 0 runs on whatever socket is current; every round after
        # that rotates first (sec 2.4(b)) -- a short batch is the signal
        # that something poisoned this socket's reply stream. Rotating
        # unconditionally on any shortfall is deliberate: detecting which
        # single request was the poison isn't worth it when rotating is
        # cheap and measured to recover completely.
        pending = list(dict.fromkeys(addresses))  # de-dup, keep first-seen order
        replies: dict[str, OscMessage] = {}

        for round_index in range(retry_rounds + 1):
            if not pending:
                break
            if round_index > 0:
                self._rotate()
            pending = self._run_one_pass(pending, batch_size, replies)

        return BatchResult(replies=replies, unresolved=tuple(pending))

    def _run_one_pass(
        self, addresses: list[str], batch_size: int, replies: dict[str, OscMessage]
    ) -> list[str]:
        """Send `addresses` in batches of `batch_size`, collecting into
        `replies` as they land. Returns whatever this pass never got."""
        still_pending: list[str] = []
        for start in range(0, len(addresses), batch_size):
            chunk = addresses[start : start + batch_size]
            still_pending.extend(self._send_and_collect(chunk, replies))
        return still_pending

    def _send_and_collect(
        self, chunk: list[str], replies: dict[str, OscMessage]
    ) -> list[str]:
        """Fire every address in `chunk` before reading any reply back --
        the pipelining sec 2.5 measured at 2822 reads/s -- then collect
        until either everything answers or the idle gap closes it out."""
        wanted = set(chunk)
        for address in chunk:
            self._sock.sendto(encode(address), (self._host, self._port))

        self._sock.settimeout(self._idle_timeout)
        try:
            while wanted:
                try:
                    data, _ = self._sock.recvfrom(_RECV_BUFSIZE)
                except socket.timeout:
                    break  # idle gap: nothing more is coming for this chunk
                message = decode(data)
                wanted.discard(message.address)
                replies[message.address] = message
        finally:
            self._sock.settimeout(self._timeout)

        return [address for address in chunk if address in wanted]
