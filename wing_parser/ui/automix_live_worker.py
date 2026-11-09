"""Worker side of Full auto (wave 12 phase 2): no Qt, runs on a CallRunner thread.

`TickRunner` feeds the pure loop (`automix.live_loop`): each tick it overlays
one batched desk read on a base copy of the pulled scene, and `write_leaf`
goes through `live_write.send` -- the one audited door (AM-1). In simulate
mode it records "would write" rows and overlays them on the next read so the
loop converges visibly without touching the desk.
"""

from __future__ import annotations

import copy
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

from wing_parser.edit import pointer
from wing_parser.net.address import leaf_parts, osc_address
from wing_parser.net.codec import leaf_value
from wing_parser.ui import live_write


@dataclass(frozen=True)
class LiveContext:
    host: str
    identity: Any
    show: dict | None
    transport: Any                       # live_write.WriteTransport (gate.transport)
    client_factory: Callable[[str], Any]  # host -> client with get_many (context manager)
    simulate: bool
    stop: threading.Event                # no new loop writes
    abort: threading.Event               # the gate is down: not even a revert
    tick_budget_s: float | None = None   # no new write once a tick has run this long (AM-53)


@dataclass(frozen=True)
class WriteRow:
    path: str
    before: Any
    after: Any
    stage: str
    label: str
    result: Any                          # SetResult; None when simulated


class TickRunner:
    def __init__(self, ctx: LiveContext, base_document: dict, load_scene, options) -> None:
        self.ctx, self.options, self.load_scene = ctx, options, load_scene
        self.base = copy.deepcopy(base_document)
        self.leaves: set = set()
        self.meta: dict = {}             # path -> (stage, label)
        self.simulated: dict = {}
        self.originals: dict = {}        # path -> desk value before the first write
        self.last_written: dict = {}
        self.tolerance_for = lambda path, value: 0.25   # make_loop wires the real limits
        self.fatal = ""
        self._doc: dict = self.base
        self.unknown: frozenset = frozenset()   # leaves the last read did not resolve (AM-58)
        self.busy = threading.Event()           # set by `begin` (GUI), cleared when the thread ends
        self._lock = threading.Lock()
        self._rows: list = []                   # every row sent, kept until the GUI takes it (AM-52)
        self._revert_rows: list = []
        self.skipped: list = []                 # (path, reason) a revert left alone (AM-55)
        self.revert_error = ""
        self._deadline: float | None = None

    # -- the thread handshake (AM-52) ---------------------------------------

    def begin(self) -> None:
        """GUI thread, right before the CallRunner starts a thread function."""
        self.busy.set()

    def take_rows(self) -> tuple:
        with self._lock:
            rows, self._rows = tuple(self._rows), []
        return rows

    def take_revert_rows(self) -> tuple:
        with self._lock:
            rows, self._revert_rows = tuple(self._revert_rows), []
        return rows

    def add_revert_row(self, row) -> None:
        with self._lock:
            self._revert_rows.append(row)

    def propose(self, scene, document, options):
        from wing_parser.automix import propose

        found = propose(scene, document, options)
        for change in found.changes:
            self.leaves.add(change.path)
            self.meta[change.path] = (change.stage, change.label)
        return found

    def read_document(self) -> dict:
        if not self.leaves:              # seed, so tick 1 already reads live values
            self.propose(self.load_scene(self.base), self.base, self.options)
        document = copy.deepcopy(self.base)
        wanted = {osc_address(path): path for path in sorted(self.leaves)}
        if wanted:
            with self.ctx.client_factory(self.ctx.host) as client:
                batch = client.get_many(tuple(wanted), batch_size=200)
            if not batch.replies:
                raise OSError("the desk did not answer the read")
            self.unknown = frozenset(
                path for address, path in wanted.items() if address not in batch.replies)
            for address, message in batch.replies.items():
                path = wanted[address]
                self._put(document, path, live_write.scene_value(
                    leaf_parts(path), leaf_value(message)[0]))
        for path, value in self.simulated.items():
            self._put(document, path, value)
        self._doc = document
        return document

    @staticmethod
    def _put(document: dict, path: str, value) -> None:
        try:
            pointer.write(document, path, value)
        except KeyError:
            pass                         # a leaf the pulled scene does not hold

    def write_leaf(self, path: str, value):
        """Returns the value the desk settled on (read-back), or None."""
        if self.ctx.stop.is_set():
            raise RuntimeError("stopped")
        if self._deadline is not None and time.monotonic() > self._deadline:
            raise TimeoutError("tick time budget used up")
        before = pointer.read(self._doc, path)
        stage, label = self.meta.get(path, ("", path))
        if self.ctx.simulate:
            self.simulated[path] = value
            self._add_row(WriteRow(path, before, value, stage, label, None))
            return value
        conf = live_write.confirmation_for(
            self.ctx.host, osc_address(path), value, self.ctx.identity, before)
        try:
            result = live_write.send(conf, self.ctx.transport)
        except live_write.DeskChanged as exc:
            self.fatal = str(exc)
            self.ctx.stop.set()
            self.ctx.abort.set()
            raise
        self.originals.setdefault(path, before)
        self.last_written[path] = value
        self._add_row(WriteRow(path, before, value, stage, label, result))
        if result.readback is None:
            raise OSError(f"no read-back for {path}")
        settled = live_write.scene_value(leaf_parts(path), result.readback)
        self.last_written[path] = settled
        return settled

    def _add_row(self, row) -> None:
        with self._lock:
            self._rows.append(row)

    def tick_once(self, loop):
        """Rows stay in `take_rows` even if this is abandoned on a timeout."""
        try:
            budget = self.ctx.tick_budget_s
            self._deadline = time.monotonic() + budget if budget else None
            return loop.tick(), self.fatal
        finally:
            self.busy.clear()

    def revert(self, locked=frozenset()):
        from wing_parser.ui.automix_live_revert import revert_all

        try:
            revert_all(self, locked)
            return list(self.skipped), self.revert_error
        finally:
            self.busy.clear()


def make_loop(runner: TickRunner, options, limits=None, clock=None):
    """The pure loop wired to `runner`; the engine is imported here only."""
    from wing_parser.automix.live_limits import LiveLimits
    from wing_parser.automix.live_loop import LiveAutomix

    limits = limits or LiveLimits()
    runner.tolerance_for = limits.tolerance_for
    return LiveAutomix(
        options, runner.load_scene, runner.read_document, runner.write_leaf,
        clock or time.monotonic, limits=limits,
        propose_fn=runner.propose, unknown_fn=lambda: runner.unknown)
