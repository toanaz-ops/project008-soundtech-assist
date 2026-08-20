"""Rendering for the `wing net` commands.

Split from `render.py` rather than left in it: that file renders a scene
-- channels, buses, findings, a diff -- and these render a conversation
with a console. Different subject, different reason to change, and the
project keeps files near 200 lines by splitting on exactly that line.

`commands.py` and `net_commands.py` both import from their own renderer,
so neither has to know the other exists.
"""

from __future__ import annotations

from typing import Any

# One definition, in the module that owns the scene-rendering vocabulary.
from wing_parser.cli.render import BULLET


def net_identity(identity: Any) -> str:
    return (
        f"{identity.name}  ({identity.model})\n"
        f"  serial    {identity.serial}\n"
        f"  firmware  {identity.firmware}\n"
        f"  ip        {identity.ip}"
    )


def _count_leaves(tree: dict) -> int:
    total = 0
    for value in tree.values():
        total += _count_leaves(value) if isinstance(value, dict) else 1
    return total


def net_snapshot_summary(result: Any) -> str:
    raw = result.raw
    leaf_count = _count_leaves(raw.ae) + _count_leaves(raw.ce)
    lines = [
        f"{raw.source}  [{raw.version.type_id} / {raw.version.label}]",
        f"  {leaf_count} leaves read",
    ]
    if result.unresolved_nodes:
        lines.append(f"  {len(result.unresolved_nodes)} unresolved node(s):")
        for node in result.unresolved_nodes:
            lines.append(f"{BULLET}{node}")
    if result.unresolved_leaves:
        lines.append(f"  {len(result.unresolved_leaves)} unresolved leaf/leaves:")
        for leaf in result.unresolved_leaves:
            lines.append(f"{BULLET}{leaf}")
    if not result.unresolved_nodes and not result.unresolved_leaves:
        lines.append("  0 unresolved")
    return "\n".join(lines)


def net_snapshot_saved(path: str, result: Any) -> str:
    return net_snapshot_summary(result) + f"\n  written to {path}"


def net_get(address: str, native: Any, display: str) -> str:
    return f"{address}  {display}  (native {native!r})"


def net_set_result(result: Any) -> str:
    if result.dry_run:
        return f"dry run: would send {result.address} = {result.sent!r}  (re-run with --confirm to send)"
    status = "OK" if result.matched else "MISMATCH -- read-back did not confirm the write"
    return f"{result.address}  sent {result.sent!r}  readback {result.readback!r}  [{status}]"


def net_push_result(result: Any, total: int) -> str:
    if result.dry_run:
        return f"dry run: {total} leaf/leaves would be pushed  (re-run with --confirm to send)"
    lines = [
        f"landed={len(result.landed)}  mismatched={len(result.mismatched)}  "
        f"absent={len(result.absent)}  (of {total})"
    ]
    if result.mismatched:
        lines.append(f"  {len(result.mismatched)} mismatched (did not read back as sent):")
        for address, (expected, readback) in sorted(result.mismatched.items()):
            lines.append(f"{BULLET}{address}: expected {expected!r}, read back {readback!r}")
    if result.absent:
        lines.append(
            f"  {len(result.absent)} absent on this console -- hardware not present, "
            "not a failure (e.g. StageConnect inputs with nothing attached):"
        )
        for address in sorted(result.absent):
            lines.append(f"{BULLET}{address}")
    return "\n".join(lines)
