"""D-41: one schema walk shared across a round trip through the Console page.

`net.snapshot.take_snapshot` and `net.watch.list.build_watch_list` each
accept a keyword-only `schema: SchemaResult | None = None` and skip their
own internal `walk_schema` call when one is supplied -- that seam already
existed (D-41, "partially closed"). What was missing is a caller that
actually HANDS one in: Discover then Pull (or Pull then Discover) walked
the console's shape twice, once inside each call, for the one thing nothing
else in ConsolePage's own state can change between them.

Owned by `ConsolePage`, not by `live_controller.discover`/`pull`
themselves -- neither function caches anything on its own account (the
default stays a fresh walk every call, unchanged, per S2.10). A caller
hands in a `SchemaCache` only when it actually wants to remember one walk
across two calls, and it is the CALLER's job to `clear()` it -- on
disconnect, on a fresh connect, or a different desk answering. A schema
is never valid across desks, so `ConsolePage` clears this on every
`connected`/`disconnected` transition rather than trying to compare
serials.
"""

from __future__ import annotations

from wing_parser.net.schema import SchemaResult


class SchemaCache:
    """One remembered walk, or none.

    **I1 (fix round):** `get()`/`clear()` run on the GUI thread, like the
    rest of `ConsolePage`'s state -- but `set()` is called from
    `live_controller._schema_for`, which runs INSIDE `discover`/`pull`,
    which run on a `FunctionWorker` thread (`workers.py`), not the GUI
    thread. A slow, cancelled or timed-out walk started against one
    connection can still be running when the operator disconnects and
    connects to a different desk; without a guard, that walk's late
    `set()` would overwrite the new connection's schema (or plant a
    schema where none should exist yet) with the OLD desk's leaves.

    `_generation` closes that: every `clear()` -- called on every
    connect and disconnect (`console_page.py`) -- bumps it, and `set()`
    only writes when the generation it is handed still matches current.
    A caller captures `generation()` right before it starts its own walk
    and hands it back to `set()` once that walk returns; a walk that
    starts under generation N and finishes after `clear()` has moved the
    cache to N+1 writes nothing. Reading/comparing a plain `int` and
    reassigning a reference are each a single GIL-protected step, so this
    check-then-write needs no lock.
    """

    def __init__(self) -> None:
        self._schema: SchemaResult | None = None
        self._generation = 0

    def generation(self) -> int:
        """Capture this before starting a walk; hand it back to `set()`."""
        return self._generation

    def get(self) -> SchemaResult | None:
        return self._schema

    def set(self, schema: SchemaResult, generation: int) -> None:
        """Write only if `generation` is still current -- see class
        docstring (I1). A stale write is silently dropped, not an error:
        the walk it came from is simply no longer relevant to anything
        on screen."""
        if generation == self._generation:
            self._schema = schema

    def clear(self) -> None:
        """A new connection lifecycle (connect OR disconnect): drop the
        schema and bump the generation, so a walk still running under
        the old one can never write here again."""
        self._schema = None
        self._generation += 1
