"""Read and write one leaf of a .snap document by dotted path.

A path names the whole document, so it starts at the file's own
top-level key: "ae_data.ch.16.in.set.inv". Every segment is a literal
mapping key -- JSON object keys are strings, so a channel number
appears as "16", not 16. No path this project needs traverses an array,
so there is no index syntax.

Nothing here creates a key. A scene saved by different firmware may
legitimately lack one, and inventing it would write a structure the
console never had; refusing is the only honest answer, and it is why
`write` raises rather than assigning into a fresh dict.
"""

from __future__ import annotations

from typing import Any


def _walk(document: dict, segments: list[str], upto: int) -> Any:
    """The node `upto` segments in.

    Raises KeyError naming the path *as far as it got*, so a message
    reads "ae_data.ch.999" rather than repeating the whole path the
    caller already knows -- the useful half is where the walk stopped.
    """
    node: Any = document
    for depth, segment in enumerate(segments[:upto]):
        if not isinstance(node, dict) or segment not in node:
            raise KeyError(".".join(segments[: depth + 1]))
        node = node[segment]
    return node


def read(document: dict, path: str) -> Any:
    segments = path.split(".")
    return _walk(document, segments, len(segments))


def write(document: dict, path: str, value: Any) -> None:
    segments = path.split(".")
    parent = _walk(document, segments, len(segments) - 1)
    leaf = segments[-1]
    if not isinstance(parent, dict) or leaf not in parent:
        raise KeyError(path)
    parent[leaf] = value
