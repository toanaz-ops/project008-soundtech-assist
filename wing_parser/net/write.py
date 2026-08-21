"""The write path: set, toggle, node write, push -- gated by sec 6.

Sec 2.6 (pushing example-Vu.snap's 21344 leaves, reading every one back):
default to a display-domain STRING (`,s`), never dispatch the OSC type
from the Python value's type -- a `.snap` int is often a schema-list
*index*, not the value, so type-dispatch was wrong on 1919 leaves vs. 5
for the string form (scientific notation, `_format_float_plain`). `OK` is
not proof either: the console clamps out-of-range values and still
answers `OK`, so every write here is read back and a clamp reported.

A parameter write expects no reply (sec 2.6), so those sends go straight
out on a bare socket -- WingClient's reply-matching and socket rotation
have nothing to do. Everything that does expect a reply, including the
node-write acknowledgement and every read-back, goes through WingClient
so it keeps that recovery. Sec
6: dry-run (default) touches no socket; `confirm=True` echoes identity,
refuses on a `WING_WRITE_ALLOW_SERIAL` mismatch, reads every write back.
"""

from __future__ import annotations

import math
import os
import socket
from dataclasses import dataclass
from typing import Any, Mapping

from wing_parser.core.normalizer import SENTINEL_MINUS_INF, from_db
from wing_parser.net.client import DEFAULT_TIMEOUT, OSC_PORT, WingClient
from wing_parser.net.codec import encode, leaf_value
from wing_parser.net.identity import IDENTITY_PORT, query_identity

_SERIAL_ENV_VAR = "WING_WRITE_ALLOW_SERIAL"
_OK = "OK"

class SerialMismatchError(RuntimeError):
    """Refused: WING_WRITE_ALLOW_SERIAL is set and does not match (sec 6)."""

@dataclass(frozen=True)
class SetResult:
    address: str
    expected: Any
    sent: str
    dry_run: bool
    readback: Any
    matched: bool | None  # None only for a dry run: nothing was read

@dataclass(frozen=True)
class NodeWriteResult:
    node: str
    payload: str
    dry_run: bool
    ok: bool | None  # None for a dry run
    error: str | None
    verified: dict[str, bool]  # per-parameter read-back match

@dataclass(frozen=True)
class PushResult:
    landed: tuple[str, ...]
    mismatched: dict[str, tuple[Any, Any]]  # address -> (expected, readback)
    absent: tuple[str, ...]  # sec 2.7: genuinely missing on this console
    dry_run: bool

def _format_float_plain(value: float) -> str:
    # repr() goes scientific only for very small/large magnitudes -- fx.N.thr_3 = 1.490116119e-07, which WING's parser rejected (sec 2.6).
    text = repr(value)
    if "e" not in text and "E" not in text:
        return text
    text = f"{value:.10f}"
    return (text.rstrip("0").rstrip(".") if "." in text else text) or "0"

def _format_value(value: Any) -> str:
    # Sec 2.6: display-domain string, plain decimal, `-oo` at/below -144 (via normalizer.from_db, so float("-inf") works too).
    if isinstance(value, bool):  # bool is an int subclass -- check first
        return "1" if value else "0"
    if isinstance(value, (int, float)):
        if from_db(float(value)) <= SENTINEL_MINUS_INF:
            return "-oo"
        return str(value) if isinstance(value, int) else _format_float_plain(value)
    return str(value)

def _values_match(expected: Any, readback: Any) -> bool:
    # Against leaf_value's reconstruction (sec 2.3): a clamp or an index-vs-value re-expression must still be a mismatch.
    if isinstance(expected, bool):
        return bool(readback) == expected
    if isinstance(expected, (int, float)) and isinstance(readback, (int, float)):
        exp, got = from_db(float(expected)), float(readback)
        if exp <= SENTINEL_MINUS_INF or got <= SENTINEL_MINUS_INF:
            return exp <= SENTINEL_MINUS_INF and got <= SENTINEL_MINUS_INF
        return math.isclose(exp, got, rel_tol=1e-6, abs_tol=1e-6)
    return str(expected) == str(readback)

def _authorize(host: str, identity_port: int, timeout: float) -> None:
    identity = query_identity(host, identity_port, timeout=timeout)
    allowed = os.environ.get(_SERIAL_ENV_VAR)
    if allowed and allowed != identity.serial:
        raise SerialMismatchError(
            f"refusing to write to {identity.name!r} (serial {identity.serial!r}): "
            f"{_SERIAL_ENV_VAR}={allowed!r} does not match"
        )

def _fire_and_forget(host: str, port: int, address: str, typetag: str, args: tuple) -> None:
    """A parameter write expects no reply at all (sec 2.6: WING never echoes
    one), so this deliberately does not use WingClient. WingClient's whole
    job is matching replies to requests and rotating away from a poisoned
    reply stream, and neither applies when nothing comes back. Anything
    that DOES expect a reply goes through WingClient instead, so it keeps
    that recovery."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.sendto(encode(address, typetag, args), (host, port))

def _set_leaf(host: str, address: str, tag: str, args: tuple, sent: str, expected: Any, *,
               osc_port: int, identity_port: int, timeout: float, confirm: bool) -> SetResult:
    # Shared by set()/toggle(); toggle() passes expected=None (no target).
    if not confirm:
        return SetResult(address, expected, sent, True, None, None)
    _authorize(host, identity_port, timeout)
    _fire_and_forget(host, osc_port, address, tag, args)
    with WingClient(host, osc_port, timeout=timeout) as client:
        reply = client.request(address)
    readback = leaf_value(reply)[0] if reply is not None else None
    matched = readback is not None and (expected is None or _values_match(expected, readback))
    return SetResult(address, expected, sent, False, readback, matched)

def set(host: str, address: str, value: Any, *, typetag: str | None = None, osc_port: int = OSC_PORT,
        identity_port: int = IDENTITY_PORT, timeout: float = DEFAULT_TIMEOUT, confirm: bool = False) -> SetResult:
    """Write one leaf: `typetag=None` sends the sec 2.6 display-domain
    string (default); "f"/"i" overrides are honoured too."""
    if typetag is None:
        tag, args, sent = "s", (_format_value(value),), _format_value(value)
    elif typetag == "f":
        tag, args, sent = "f", (float(value),), _format_value(float(value))
    elif typetag == "i":
        tag, args, sent = "i", (int(value),), str(int(value))
    else:
        raise ValueError(f"unsupported override type tag {typetag!r}")
    return _set_leaf(host, address, tag, args, sent, value, osc_port=osc_port, identity_port=identity_port, timeout=timeout, confirm=confirm)

def toggle(host: str, address: str, *, osc_port: int = OSC_PORT, identity_port: int = IDENTITY_PORT,
           timeout: float = DEFAULT_TIMEOUT, confirm: bool = False) -> SetResult:
    """`,i -1` on a 0/1 int leaf -- flips it (sec 2.6)."""
    return _set_leaf(host, address, "i", (-1,), "-1", None, osc_port=osc_port, identity_port=identity_port, timeout=timeout, confirm=confirm)

def node_write(host: str, node: str, params: Mapping[str, Any], *, osc_port: int = OSC_PORT,
                identity_port: int = IDENTITY_PORT, timeout: float = DEFAULT_TIMEOUT, confirm: bool = False) -> NodeWriteResult:
    """Several params in one packet, e.g. `/ch/40 ,s "fdr=4,mute=1"`. Reply
    lands on `/*` -- matched on payload, not address (sec 2.6). Any
    payload but the literal `OK` is an error, known or not."""
    payload = ",".join(f"{key}={_format_value(val)}" for key, val in params.items())
    if not confirm:
        return NodeWriteResult(node, payload, True, None, None, {})
    _authorize(host, identity_port, timeout)
    # Through WingClient, not a bare socket: this one DOES expect a reply,
    # so it should get the same retry-on-rotated-socket handling as every
    # other read on this connection.
    with WingClient(host, osc_port, timeout=timeout) as client:
        reply = client.request(node, "s", (payload,))
    text = reply.args[0] if reply is not None and reply.args else None
    if text != _OK:
        return NodeWriteResult(node, payload, False, False, text or "no reply", {})
    addresses = [f"{node.rstrip('/')}/{key}" for key in params]
    with WingClient(host, osc_port, timeout=timeout) as client:
        batch = client.get_many(addresses)
    verified = {}
    for key, leaf_address in zip(params, addresses):
        if leaf_address not in batch.replies:
            verified[key] = False
            continue
        native = leaf_value(batch.replies[leaf_address])[0]
        verified[key] = _values_match(params[key], native)
    return NodeWriteResult(node, payload, False, True, None, verified)

def push(host: str, leaves: Mapping[str, Any], *, osc_port: int = OSC_PORT, identity_port: int = IDENTITY_PORT,
         timeout: float = DEFAULT_TIMEOUT, confirm: bool = False) -> PushResult:
    """Write many leaves fire-and-forget (sec 2.6: 21344 in 1.1s), verify
    with one pipelined read-back batch. `get_many`'s `unresolved` becomes
    `absent` directly -- sec 2.7's leaves genuinely missing, not failed."""
    if not confirm:
        return PushResult((), {}, (), True)
    _authorize(host, identity_port, timeout)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        for address, value in leaves.items():
            sock.sendto(encode(address, "s", (_format_value(value),)), (host, osc_port))
    with WingClient(host, osc_port, timeout=timeout) as client:
        batch = client.get_many(list(leaves.keys()))
    landed: list[str] = []
    mismatched: dict[str, tuple[Any, Any]] = {}
    for address, expected in leaves.items():
        if address not in batch.replies:
            continue  # -> absent, via batch.unresolved below
        native = leaf_value(batch.replies[address])[0]
        if _values_match(expected, native):
            landed.append(address)
        else:
            mismatched[address] = (expected, native)
    return PushResult(tuple(landed), mismatched, batch.unresolved, False)
