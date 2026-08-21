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


# Pushing a scene authored on another console routinely leaves thousands of
# leaves absent -- 3235 of 28056 in one measured run, most of them a WEDIT
# layer this desk has never had. Printing every one buries the summary line
# that actually matters under pages of addresses, so both lists are capped
# and the shapes are summarised instead.
_LIST_CAP = 12


def _shape(address: str) -> str:
    return "/".join("N" if part.isdigit() else part for part in address.split("/"))


def _by_shape(addresses: Any) -> list[str]:
    """A count per address shape -- which is what tells you whether the
    remainder is one family or a real spread."""
    shapes: dict[str, int] = {}
    for address in addresses:
        shapes[_shape(address)] = shapes.get(_shape(address), 0) + 1
    lines = [f"    ... and {len(list(addresses))} more, by shape:"]
    ranked = sorted(shapes.items(), key=lambda item: -item[1])
    for shape, count in ranked[:6]:
        lines.append(f"      {count:6d}  {shape}")
    if len(ranked) > 6:
        lines.append(f"      ... and {len(ranked) - 6} further shapes")
    return lines


def _capped(addresses: Any) -> list[str]:
    """The first few in full, then the rest summarised by shape."""
    listed = sorted(addresses)
    lines = [f"{BULLET}{address}" for address in listed[:_LIST_CAP]]
    if len(listed) > _LIST_CAP:
        lines += _by_shape(listed[_LIST_CAP:])
    return lines


def net_push_result(result: Any, total: int) -> str:
    if result.dry_run:
        return f"dry run: {total} leaf/leaves would be pushed  (re-run with --confirm to send)"
    lines = [
        f"landed={len(result.landed)}  mismatched={len(result.mismatched)}  "
        f"absent={len(result.absent)}  (of {total})"
    ]
    if result.mismatched:
        lines.append(f"  {len(result.mismatched)} mismatched (did not read back as sent):")
        listed = sorted(result.mismatched.items())
        for address, (expected, readback) in listed[:_LIST_CAP]:
            lines.append(f"{BULLET}{address}: expected {expected!r}, read back {readback!r}")
        if len(listed) > _LIST_CAP:
            lines += _by_shape([address for address, _ in listed[_LIST_CAP:]])
    if result.absent:
        lines.append(
            f"  {len(result.absent)} absent on this console -- hardware or a feature this "
            "desk does not have, not a failure:"
        )
        lines += _capped(result.absent)
    return "\n".join(lines)
