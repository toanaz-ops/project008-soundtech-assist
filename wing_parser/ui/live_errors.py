"""`EmptyReadError`, split out of `live_controller.py` for headroom (D-41).

Re-exported from `live_controller` (`from .live_errors import
EmptyReadError`), so every existing `from wing_parser.ui.live_controller
import EmptyReadError` keeps working unchanged.
"""

from __future__ import annotations


class EmptyReadError(OSError):
    """A pull that reached the desk's address and read nothing at all.

    Ported from `cli/commands.py:47-62`, where it is a printed line and a
    `None` return. It has to be an *error* rather than an empty result:
    OSC is UDP, so an unreachable host raises nothing -- every leaf times
    out, `take_snapshot` faithfully returns a valid empty scene, and the
    advisory engine truthfully finds nothing wrong with it. `doctor
    --live` showed "No findings." for a desk it had never reached, until
    this guard existed. An `OSError` because that is the vocabulary every
    other live-read failure already speaks (`commands.py:25-28`). Both
    counts, never one: `walk_schema` runs first and the leaf reads run
    after it, so `nodes` can be 0 while every leaf timed out.
    """

    def __init__(self, host: str, nodes: int, leaves: int) -> None:
        super().__init__(
            f"no console answered at {host}: read nothing at all "
            f"({nodes} top-level node(s) and {leaves} leaf/leaves did not "
            f"answer). Check the address and that the desk is on the network."
        )
        self.host = host
        self.nodes = nodes
        self.leaves = leaves
