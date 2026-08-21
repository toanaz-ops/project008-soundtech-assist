"""A loopback UDP fake console -- the only thing any `net/` test may talk to.

Every `net/` test, present and future, needs the same three things: no
real socket to a real desk, exact-bytes request/reply lookup seeded
from the recorded fixtures, and a way to prove silence (design doc
sec 2.4(b) and sec 6.1's dry-run-sends-nothing guarantee) without
reading source code to believe it.

**Two sockets, not one.** The real console answers two protocols on
two different UDP ports: the plain-text `WING?` handshake on 2222 and
OSC on 2223 (sec 2.1). `FakeWing` mirrors that split with an OSC
socket and an identity socket, each bound to its own ephemeral
127.0.0.1 port, rather than multiplexing both wire formats through one
socket behind a flag -- a caller that has both `fake.osc_address` and
`fake.identity_address` never needs to know which physical port a real
console would use, and a test that wants to prove the client rotates
its *source* port (sec 2.4(b)) never has to worry about the fake's own
two ports colliding with that.

Public interface:

    with FakeWing() as fake:
        fake.osc_address          # (host, port) for OSC exchanges
        fake.identity_address     # (host, port) for the WING? handshake
        fake.osc_packets_received      # int, counts datagrams landed on the OSC socket
        fake.identity_packets_received # int, counts datagrams landed on the identity socket
        fake.register(tx_bytes, rx_bytes_or_None)           # add/replace an OSC pair
        fake.register_identity(tx_bytes, rx_bytes_or_None)  # add/replace an identity pair

A registered reply of `None` means the fake sends nothing at all --
reproducing sec 2.4(b)'s two silent-failure cases (an oversized node
dump, a GET on a non-existent address) and giving later tests a way to
manufacture a timeout on demand.
"""

from __future__ import annotations

import json
import socket
import threading
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent / "data"
_OSC_FIXTURES = _DATA_DIR / "wing_osc_fixtures.json"
_WRITE_FIXTURES = _DATA_DIR / "wing_write_fixtures.json"

_RECV_BUFSIZE = 4096
# Bounds how long a stuck _serve loop can delay shutdown; short enough
# that closing a FakeWing never makes a test suite feel slow.
_POLL_TIMEOUT = 0.1


def _hex_or_none(value: str | None) -> bytes | None:
    return bytes.fromhex(value) if value is not None else None


class FakeWing:
    def __init__(self) -> None:
        self._osc_table: dict[bytes, bytes | None] = {}
        self._identity_table: dict[bytes, bytes | None] = {}
        self._load_osc_fixtures()
        self._load_write_fixtures()
        self._load_identity_fixture()

        self._lock = threading.Lock()
        self.osc_packets_received = 0
        self.identity_packets_received = 0
        self._stop = threading.Event()

        self._osc_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._osc_sock.bind(("127.0.0.1", 0))
        self._osc_sock.settimeout(_POLL_TIMEOUT)

        self._identity_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._identity_sock.bind(("127.0.0.1", 0))
        self._identity_sock.settimeout(_POLL_TIMEOUT)

        self._osc_thread = threading.Thread(
            target=self._serve, args=(self._osc_sock, self._osc_table, "osc"),
            daemon=True,
        )
        self._identity_thread = threading.Thread(
            target=self._serve,
            args=(self._identity_sock, self._identity_table, "identity"),
            daemon=True,
        )

    # -- fixture loading ---------------------------------------------

    def _load_osc_fixtures(self) -> None:
        doc = json.loads(_OSC_FIXTURES.read_text(encoding="utf-8"))
        for exchange in doc["exchanges"].values():
            tx = bytes.fromhex(exchange["tx"])
            self._osc_table[tx] = _hex_or_none(exchange.get("rx"))

    def _load_write_fixtures(self) -> None:
        # Writes are never echoed (design doc sec 2.1), and this fixture
        # file records that by omitting "rx" entirely rather than setting
        # it to null -- .get() treats the two identically.
        entries = json.loads(_WRITE_FIXTURES.read_text(encoding="utf-8"))
        for entry in entries:
            tx = bytes.fromhex(entry["tx"])
            self._osc_table[tx] = _hex_or_none(entry.get("rx"))

    def _load_identity_fixture(self) -> None:
        doc = json.loads(_OSC_FIXTURES.read_text(encoding="utf-8"))
        identity = doc["identity"]
        tx = bytes.fromhex(identity["tx"])
        self._identity_table[tx] = _hex_or_none(identity.get("rx"))

    # -- runtime registration -----------------------------------------

    def register(self, tx: bytes, rx: bytes | None) -> None:
        """Add or replace one OSC request -> reply pair at runtime, so
        later `net/` tests can cover cases beyond the 74 recorded
        exchanges without editing this file."""
        self._osc_table[tx] = rx

    def register_identity(self, tx: bytes, rx: bytes | None) -> None:
        """Same as `register`, for the identity-port table -- e.g. to
        feed `identity.parse_identity` a malformed reply, or to force
        silence for a timeout test."""
        self._identity_table[tx] = rx

    # -- addresses ------------------------------------------------------

    @property
    def osc_address(self) -> tuple[str, int]:
        return self._osc_sock.getsockname()

    @property
    def identity_address(self) -> tuple[str, int]:
        return self._identity_sock.getsockname()

    # -- lifecycle --------------------------------------------------------

    def __enter__(self) -> "FakeWing":
        self._osc_thread.start()
        self._identity_thread.start()
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def close(self) -> None:
        self._stop.set()
        self._osc_thread.join(timeout=2)
        self._identity_thread.join(timeout=2)
        self._osc_sock.close()
        self._identity_sock.close()

    # -- server loop --------------------------------------------------------

    def _serve(
        self, sock: socket.socket, table: dict[bytes, bytes | None], kind: str
    ) -> None:
        counter = "osc_packets_received" if kind == "osc" else "identity_packets_received"
        while not self._stop.is_set():
            try:
                data, addr = sock.recvfrom(_RECV_BUFSIZE)
            except socket.timeout:
                continue
            except OSError:
                return  # socket closed under us during shutdown

            with self._lock:
                setattr(self, counter, getattr(self, counter) + 1)

            if data not in table:
                continue  # unrecognised request: real WING answers nothing either

            reply = table[data]
            if reply is not None:
                sock.sendto(reply, addr)
