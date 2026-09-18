"""One dotted `.snap` path becomes one OSC address, and back again.

The exact inverse of `net/snapshot.py:_place` (`snapshot.py:116-123`), whose
docstring is the authority: everything but `/$ctl/...` is ae_data "keyed
exactly as the OSC address reads, which is already the .snap layout".

`ce_data` is refused rather than mapped (W2). S2.2 makes ce_data's own
top-level keys `$ctl`'s CHILDREN, so a `ce_data.` path is not one segment
away from its address, and no descriptor in `edit/data/repairs.yaml` targets
one. Mapping it would need the `$ctl` re-prefix plus a test per shape.

`leaf_parts` exists so no caller has to get the shape right by hand:
`jsontypes.is_boolean_shape` (`jsontypes.py:48-59`) wants the ae-STRIPPED
parts and answers `False` in silence for anything else, so a caller that
passed the document-rooted path would get no error and no coercion -- only a
bool quietly stored as an int.
"""

from __future__ import annotations

from collections.abc import Sequence

ROOT = "ae_data"


def leaf_parts(path: str) -> list[str]:
    """The leaf's segments with the `ae_data.` root stripped.

    Raises `ValueError` naming the input for any other root or an empty
    segment -- both callers below inherit that refusal, so neither can be
    laxer than the other.
    """
    segments = path.split(".")
    if segments[0] != ROOT or len(segments) < 2:
        raise ValueError(
            f"{path!r}: not an {ROOT} leaf path -- only ae_data leaves map "
            f"to an OSC address (W2)"
        )
    rest = segments[1:]
    if any(not segment for segment in rest):
        raise ValueError(f"{path!r}: empty path segment")
    return rest


def join_segments(segments: Sequence[str]) -> str:
    """`["ch", "1"]` -> `/ch/1`. The one join; `_flatten` uses it too."""
    return "/" + "/".join(segments)


def osc_address(path: str) -> str:
    """`ae_data.ch.1.send.8.mode` -> `/ch/1/send/8/mode`."""
    return join_segments(leaf_parts(path))
