"""The `wing net` command group -- talk to a live console over OSC.

Same shape as commands.py: one function per (sub)command, returning a
process exit code, errors printed to stderr as `error: <message>`, all
rendering in `render_net.py`. `wing_parser/net/` is owned by other agents and
is not edited here -- this module only calls its public surface
(`net/identity.py`, `net/client.py`, `net/snapshot.py`, `net/write.py`).

`OSC_PORT`/`IDENTITY_PORT` are referenced as bare module globals rather
than baked into argparse defaults, on purpose: a default parameter value
is bound once, at function-definition time, so a test could never redirect
it at a real console's fixed ports (2222/2223, design doc S2.1) onto
`tests/fake_wing.py`'s ephemeral loopback ports. A bare global lookup
happens at call time, so `monkeypatch.setattr(net_commands, "OSC_PORT",
fake_port)` retargets every command here without adding port flags the
design's command surface never asked for.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from wing_parser.cli import render_net
from wing_parser.core.loader import load_raw
from wing_parser.net import write
from wing_parser.net.client import OSC_PORT, WingClient
from wing_parser.net.codec import leaf_value
from wing_parser.net.identity import IDENTITY_PORT, query_identity
from wing_parser.net.snapshot import take_snapshot
from wing_parser.net.watch.events import change_as_dict, format_change
from wing_parser.net.watch.list import build_watch_list
from wing_parser.net.watch.poller import watch

# Errors a `net/` call can raise that must reach the user as `error: ...`,
# never a traceback: OSError covers every socket failure (timeout,
# unreachable host, refused port), ValueError covers a malformed WING?
# reply (net/identity.IdentityError), RuntimeError covers sec 6's
# WING_WRITE_ALLOW_SERIAL refusal (net/write.SerialMismatchError).
_NETWORK_ERRORS = (OSError, ValueError, RuntimeError)


def _parse_value(text: str) -> Any:
    """A CLI argument is always a string. Parse it to int/float first so
    `write._values_match`'s numeric branch (float tolerance) runs instead
    of an exact string compare that would fail on any console-side
    rounding or clamp (design doc S2.6/S2.7)."""
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        pass
    return text


def _flatten(tree: dict, prefix: str, leaves: dict[str, Any]) -> None:
    for key, value in tree.items():
        address = f"{prefix}/{key}"
        if isinstance(value, dict):
            _flatten(value, address, leaves)
        else:
            leaves[address] = value


def _leaves_from_raw(raw) -> dict[str, Any]:
    """Flatten a RawScene's ae/ce trees into OSC leaf addresses -- the
    exact inverse of net/snapshot.py's `_place` (design doc S2.2). Only
    `wing net push` needs a flat address -> value view."""
    leaves: dict[str, Any] = {}
    _flatten(raw.ae, "", leaves)
    _flatten(raw.ce, "/$ctl", leaves)
    return leaves


def _echo_identity_before_write(host: str) -> None:
    """Design doc S6, guard 2: print which desk is about to change before
    any packet that could alter it goes out. Errors are left to propagate
    to the caller's own `_NETWORK_ERRORS` handler -- a write must never
    proceed past a console it could not positively identify."""
    print(render_net.net_identity(query_identity(host, IDENTITY_PORT)))


def net_identity(args) -> int:
    try:
        identity = query_identity(args.ip, IDENTITY_PORT)
    except _NETWORK_ERRORS as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(render_net.net_identity(identity))
    return 0


def net_snapshot(args) -> int:
    try:
        result = take_snapshot(args.ip, OSC_PORT)
    except _NETWORK_ERRORS as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.output is None:
        print(render_net.net_snapshot_summary(result))
        return 0

    try:
        # Written by a concurrent agent (design doc S4.1); import lazily
        # so the rest of the CLI still imports cleanly if it lands late.
        from wing_parser.net.export import to_snap_json
    except ImportError as exc:
        print(f"error: wing_parser.net.export is not available yet ({exc})", file=sys.stderr)
        return 1

    Path(args.output).write_text(to_snap_json(result.raw), encoding="utf-8")
    print(render_net.net_snapshot_saved(args.output, result))
    return 0


def net_get(args) -> int:
    try:
        with WingClient(args.ip, OSC_PORT) as client:
            reply = client.request(args.address)
    except _NETWORK_ERRORS as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if reply is None:
        print(f"error: no reply from {args.address}", file=sys.stderr)
        return 1

    try:
        native, display = leaf_value(reply)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(render_net.net_get(args.address, native, display))
    return 0


def net_set(args) -> int:
    value = _parse_value(args.value)
    try:
        if args.confirm:
            _echo_identity_before_write(args.ip)
        result = write.set(
            args.ip, args.address, value,
            osc_port=OSC_PORT, identity_port=IDENTITY_PORT, confirm=args.confirm,
        )
    except _NETWORK_ERRORS as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(render_net.net_set_result(result))
    return 0 if result.dry_run or result.matched else 1


def net_toggle(args) -> int:
    try:
        if args.confirm:
            _echo_identity_before_write(args.ip)
        result = write.toggle(
            args.ip, args.address,
            osc_port=OSC_PORT, identity_port=IDENTITY_PORT, confirm=args.confirm,
        )
    except _NETWORK_ERRORS as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(render_net.net_set_result(result))
    return 0 if result.dry_run or result.matched else 1


def net_push(args) -> int:
    try:
        raw = load_raw(args.file)
    except OSError:
        print(f"error: cannot open {args.file}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    leaves = _leaves_from_raw(raw)

    try:
        if args.confirm:
            _echo_identity_before_write(args.ip)
        result = write.push(
            args.ip, leaves,
            osc_port=OSC_PORT, identity_port=IDENTITY_PORT, confirm=args.confirm,
        )
    except _NETWORK_ERRORS as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(render_net.net_push_result(result, len(leaves)))
    return 0 if result.dry_run or not result.mismatched else 1


def net_watch(args) -> int:
    """Report what changes on a running console, by polling.

    Subscribes to nothing (design doc S3.1), so it runs alongside
    WING-Edit, Companion or anything else without displacing them.

    In --json mode stdout carries JSON and nothing else: the first line
    is a header naming the watch-list, then one object per change. The
    unresolved report goes to stderr in text mode and into that header in
    --json mode -- never as a bare line on stdout, which is the defect
    that shipped twice in earlier cycles.
    """
    try:
        with WingClient(args.host) as client:
            watch_list = build_watch_list(args.host, client=client)

            if args.json:
                header = {
                    "watching": len(watch_list.addresses),
                    "strips": watch_list.strips,
                    "unresolved": list(watch_list.unresolved),
                }
                print(json.dumps(header), flush=True)
            else:
                inventory = ", ".join(
                    f"{count} {family}" for family, count in watch_list.strips.items()
                )
                print(f"watching {len(watch_list.addresses)} leaves ({inventory})")
                if watch_list.unresolved:
                    # S3.2: an incomplete list must say so. A bare total
                    # while four mains are missing is the exact failure
                    # this line exists to prevent.
                    print(
                        f"warning: {len(watch_list.unresolved)} node(s) did not "
                        f"resolve and are NOT being watched: "
                        f"{', '.join(watch_list.unresolved)}",
                        file=sys.stderr,
                    )
                print("watching -- Ctrl+C to stop")

            for change in watch(
                client,
                watch_list,
                interval=args.interval,
                duration=args.until,
            ):
                if args.json:
                    print(json.dumps(change_as_dict(change)), flush=True)
                else:
                    print(format_change(change), flush=True)
    except KeyboardInterrupt:
        # Stopping a watch is how it ends, not a failure.
        if not args.json:
            print("\nstopped", file=sys.stderr)
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
