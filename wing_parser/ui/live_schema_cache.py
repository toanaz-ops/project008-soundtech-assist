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

import threading

from wing_parser.net.schema import SchemaResult


class SchemaCache:
    """One remembered walk, or none.

    **I1 (fix round):** exactly which thread calls what --
    `get()`/`clear()` run on the GUI thread, as part of `ConsolePage`'s
    own state (`_connected`/`_disconnected`, and reading a cached schema
    back out); `generation()` and `set()` run on the `FunctionWorker`
    thread (`workers.py`) that `discover`/`pull` actually execute on,
    called from `live_controller._schema_for` -- `generation()` right
    before that thread starts its own walk, `set()` after the walk
    returns. A walk started against one connection can still be running
    on its worker thread when the operator disconnects and reconnects to
    a different desk on the GUI thread; without a guard, that walk's
    late `set()` would overwrite the new connection's schema with the
    OLD desk's leaves.

    A generation counter alone is not enough: `set()`'s "compare, then
    write" is two separate steps, and the GIL can switch threads BETWEEN
    them -- `clear()` running on the GUI thread right after the
    comparison passes but before the assignment would still let a stale
    schema land immediately after a clear. `_lock` (a plain
    `threading.Lock`) makes every method below one atomic unit instead,
    so no interleaving of `get`/`set`/`clear`/`generation` across the two
    threads can produce that outcome. Every `clear()` -- called on every
    connect and disconnect -- bumps `_generation`; `set()` only writes
    when the generation it is handed still matches current, so a walk
    that started under generation N and finishes after `clear()` has
    moved the cache to N+1 writes nothing.
    """

    def __init__(self) -> None:
        self._schema: SchemaResult | None = None
        self._generation = 0
        self._lock = threading.Lock()

    def generation(self) -> int:
        """Capture this (worker thread) before starting a walk; hand it
        back to `set()` once that walk returns."""
        with self._lock:
            return self._generation

    def get(self) -> SchemaResult | None:
        """GUI thread only."""
        with self._lock:
            return self._schema

    def set(self, schema: SchemaResult, generation: int) -> None:
        """Worker thread. Write only if `generation` is still current --
        see class docstring (I1). A stale write is silently dropped, not
        an error: the walk it came from is simply no longer relevant to
        anything on screen."""
        with self._lock:
            if generation == self._generation:
                self._schema = schema

    def clear(self) -> None:
        """GUI thread only. A new connection lifecycle (connect OR
        disconnect): drop the schema and bump the generation, so a walk
        still running under the old one can never write here again."""
        with self._lock:
            self._schema = None
            self._generation += 1
