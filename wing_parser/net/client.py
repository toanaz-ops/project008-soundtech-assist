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
from typing import Any, Iterable, Sequence

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
# Enough rounds for the chunk size to bisect from DEFAULT_BATCH_SIZE down
# to 1 (200 -> 100 -> 50 -> 25 -> 12 -> 6 -> 3 -> 1). Costs nothing when
# nothing is wrong: the loop breaks as soon as nothing is pending. With
# only 2 rounds a live schema walk left 27 nodes unresolved; with 8 it
# leaves only the one node that genuinely cannot answer.
DEFAULT_RETRY_ROUNDS = 8

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

# The console's own ceiling is 32 kB (design doc S2.1). Sizing the buffer
# above that rather than at it matters because an undersized recvfrom
# truncates a UDP datagram *silently* on Windows -- the reply would decode
# into plausible nonsense rather than fail.
_RECV_BUFSIZE = 65536


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

    def request(
        self, address: str, typetag: str | None = None, args: Sequence[Any] = ()
    ) -> OscMessage | None:
        # `None` on timeout, not a raise: sec 2.4(b) measured that a GET
        # on a missing address simply produces no reply -- expected, not
        # an error.
        #
        # `typetag` exists so a schema query -- address plus `,s "?"` --
        # goes through this same socket, and therefore through the same
        # rotate-on-shortfall recovery. A schema walk that opened its own
        # socket instead lost every reply from the first poisoned request
        # onward: 901 of 5330 nodes, deterministically.
        self._sock.sendto(encode(address, typetag, args), (self._host, self._port))
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
        typetag: str | None = None,
        args: Sequence[Any] = (),
    ) -> BatchResult:
        # Each retry round halves the chunk size, down to 1, which is what
        # ISOLATES a poisoned request rather than merely surviving it. An
        # oversized reply kills every reply after it on the socket, so a
        # chunk holding one poison node loses its innocent neighbours too
        # and resending that chunk reproduces the same casualty list
        # forever. Measured: a schema walk stuck at 27 unresolved nodes at
        # 2 and 5 rounds alike, of which only ONE was truly unanswerable.
        # At chunk size 1 a silent address can only be its own fault.
        pending = list(dict.fromkeys(addresses))  # de-dup, keep first-seen order
        replies: dict[str, OscMessage] = {}
        chunk_size = max(1, batch_size)

        for round_index in range(retry_rounds + 1):
            if not pending:
                break
            if round_index > 0:
                self._rotate()
                chunk_size = max(1, chunk_size // 2)
            before = len(pending)
            pending = self._run_one_pass(pending, chunk_size, replies, typetag, args)
            # A round that recovers NOTHING means the rest is genuinely
            # unanswerable, not poisoned: halving further can only isolate
            # a poison node, and there is no poison node to find. Without
            # this, a push carrying leaves the console does not have --
            # 128 StageConnect inputs on a rack with no device attached --
            # drives the ladder to chunk size 1 and pays an idle timeout
            # per address. Measured before this guard: a whole-scene push
            # ran past two minutes where the writes themselves take 1.1s.
            if len(pending) == before:
                break

        return BatchResult(replies=replies, unresolved=tuple(pending))

    def _run_one_pass(
        self,
        addresses: list[str],
        batch_size: int,
        replies: dict[str, OscMessage],
        typetag: str | None = None,
        args: Sequence[Any] = (),
    ) -> list[str]:
        """Send `addresses` in batches of `batch_size`, collecting into
        `replies` as they land. Returns whatever this pass never got.

        A short chunk rotates the socket before the NEXT chunk runs, not
        merely before the next round. That distinction is the whole fix:
        an oversized reply poisons the source port, so once one chunk goes
        short every later chunk in the same pass is talking to a dead
        port. Rotating per round instead of per chunk left a schema walk
        stuck at 27 unresolved nodes even with the chunk size bisected all
        the way down to 1 -- the isolation worked, but each isolated
        request after the first still landed on the poisoned socket.
        """
        still_pending: list[str] = []
        for start in range(0, len(addresses), batch_size):
            chunk = addresses[start : start + batch_size]
            missing = self._send_and_collect(chunk, replies, typetag, args)
            if missing:
                still_pending.extend(missing)
                self._rotate()
        return still_pending

    def _send_and_collect(
        self,
        chunk: list[str],
        replies: dict[str, OscMessage],
        typetag: str | None = None,
        args: Sequence[Any] = (),
    ) -> list[str]:
        """Fire every address in `chunk` before reading any reply back --
        the pipelining sec 2.5 measured at 2822 reads/s -- then collect
        until either everything answers or the idle gap closes it out."""
        wanted = set(chunk)
        for address in chunk:
            self._sock.sendto(encode(address, typetag, args), (self._host, self._port))

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
