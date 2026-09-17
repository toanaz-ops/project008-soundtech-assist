"""The one door from `ui/` to `wing_parser.net.write`. Nothing else has one.

W4 and §8.4: `tests/test_ui_live_is_read_only.py` allow-lists this file by
name, for the import and for the single verb `set`. `toggle`, `node_write`
and `push` stay offences here too -- `toggle` sends `,i -1` and flips
whatever the desk holds at send time (`write.py:139-142`), which would
destroy the deterministic `after` the countdown screen rests on.

`send` takes a `WriteConfirmation` and nothing else. That token is built
only after gate 4 has re-asked `WriteGate.can_write()` and
`ArmState.armed()` (§8.4), so "a plain call writes nothing" is a type
error, not a convention.

**Gate 4's second half is `DeskChanged`.** The confirmation names the
desk the operator confirmed against, so `send` re-queries identity and
refuses if the serial differs -- nothing is transmitted. A countdown can
run for a minute (§8.4), and a DHCP lease or a swapped cable can put a
different console on that address inside it. `write.set`'s own
`_authorize` (`write.py:93-100`) cannot catch that: it compares against
`WING_WRITE_ALLOW_SERIAL`, which wave 3 never sets (§8.5). The cost is
one extra `WING?` round trip per write, which is the point.

**`read` normalises before anything compares or displays.** A `,sfi` leaf
reads back as a Python `int` (`codec.py:126-128`) and `jsontypes.py:1-13`
gives the reason: `,sfi` covers plain integers AND WING's booleans, and the
value never carries the distinction. Eight of the eleven repair descriptors
set a JSON bool, so an unnormalised read hands the countdown `0` against a
journal `before` of `False` -- a spurious mismatch, shown as the nonsense
"the desk holds 0, the scene file expected False".

**F8/W13 (`Outcome`, `outcome`, `settle_scene`, `revert_confirmation`) and
their two record types (`WriteConfirmation`, `SentWrite`) live in
`wing_parser.ui.write_records`**, which may not import `wing_parser.net.write`
itself (this file is the only one that may) -- re-exported here so
`live_write.WriteConfirmation` etc. keep working for every other caller.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from wing_parser.net import write
from wing_parser.net.address import leaf_parts, osc_address
from wing_parser.net.client import WingClient
from wing_parser.net.codec import leaf_value
from wing_parser.net.identity import WingIdentity, query_identity
from wing_parser.net.write import SetResult
from wing_parser.ui.write_records import (
    Outcome,
    SentWrite,
    WriteConfirmation,
    outcome,
    revert_confirmation,
    scene_value,
    settle_scene,
)


class DeskChanged(RuntimeError):
    """The desk answering now is not the one the write was confirmed
    against. Raised by `send` BEFORE anything reaches the wire."""


@dataclass(frozen=True)
class WriteTransport:
    """The seam. `REAL` is the only place `ui/` names `net.write`."""

    identity: Callable[[str], WingIdentity]
    read: Callable[[str, str], Any | None]     # (host, DOTTED PATH) -> normalised
    set: Callable[..., SetResult]


def _read(host: str, path: str) -> Any | None:
    """One leaf off the desk, normalised. `None` when it did not answer."""
    with WingClient(host) as client:
        reply = client.request(osc_address(path))
    if reply is None:
        return None
    return scene_value(leaf_parts(path), leaf_value(reply)[0])


REAL = WriteTransport(identity=query_identity, read=_read, set=write.set)


def preflight(host: str, path: str,
              transport: WriteTransport = REAL) -> tuple[WingIdentity, Any | None]:
    """A fresh identity and the desk's CURRENT value for `path`.

    Identity is re-queried every time, never reused from the earlier
    connect: `net_commands._echo_identity_before_write`
    (`net_commands.py:79-85`) does exactly this before every CLI write, and
    `identity.py:10-14` says why -- the caller is about to trust "this is
    the console I meant to write to". Both errors propagate untranslated.
    """
    identity = transport.identity(host)
    return identity, transport.read(host, path)


def send(confirmation: WriteConfirmation,
         transport: WriteTransport = REAL) -> SetResult:
    """Write one leaf, read it back, and hand the caller `write.py`'s own
    verdict. Always `set`, always `confirm=True` (W3).

    Raises `TypeError` for anything but a `WriteConfirmation`, and
    `DeskChanged` if the desk at `confirmation.host` no longer answers
    with the serial the confirmation was built against. Neither
    transmits.
    """
    if not isinstance(confirmation, WriteConfirmation):
        raise TypeError(
            "live_write.send takes a WriteConfirmation built behind gate 4, "
            f"not {type(confirmation).__name__}"
        )
    now = transport.identity(confirmation.host)
    if now.serial != confirmation.identity.serial:
        raise DeskChanged(
            f"refusing to write to {confirmation.host}: this write was confirmed "
            f"against {confirmation.identity.name!r} (serial "
            f"{confirmation.identity.serial!r}), but the desk there now answers "
            f"as {now.name!r} (serial {now.serial!r})"
        )
    return transport.set(
        confirmation.host, confirmation.address, confirmation.after,
        confirm=True,
    )
