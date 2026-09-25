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
    """One remembered walk, or none. Not thread-safe -- read and written
    only from the GUI thread, like every other piece of `ConsolePage`'s
    own state."""

    def __init__(self) -> None:
        self._schema: SchemaResult | None = None

    def get(self) -> SchemaResult | None:
        return self._schema

    def set(self, schema: SchemaResult) -> None:
        self._schema = schema

    def clear(self) -> None:
        self._schema = None
