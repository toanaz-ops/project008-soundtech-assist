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
        self.rows: list = []
        self.fatal = ""
        self._doc: dict = self.base

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

    def write_leaf(self, path: str, value) -> None:
        if self.ctx.stop.is_set():
            raise RuntimeError("stopped")
        before = pointer.read(self._doc, path)
        stage, label = self.meta.get(path, ("", path))
        if self.ctx.simulate:
            self.simulated[path] = value
            self.rows.append(WriteRow(path, before, value, stage, label, None))
            return
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
        self.rows.append(WriteRow(path, before, value, stage, label, result))
        if result.readback is None:
            raise OSError(f"no read-back for {path}")

    def tick_once(self, loop):
        self.rows = []
        report = loop.tick()
        return report, tuple(self.rows), self.fatal

    def revert(self) -> list:
        """Each touched path back to its pre-automix desk value, once, last
        touched first; stops when the gate goes down."""
        rows = []
        for path in reversed(list(self.originals)):
            target = self.originals[path]
            if target is None or self.ctx.abort.is_set():
                continue
            last = self.last_written.get(path)
            conf = live_write.confirmation_for(
                self.ctx.host, osc_address(path), target, self.ctx.identity, last)
            result = live_write.send(conf, self.ctx.transport)
            stage, label = self.meta.get(path, ("", path))
            rows.append(WriteRow(path, last, target, stage, label, result))
        return rows


def make_loop(runner: TickRunner, options, limits=None, clock=None):
    """The pure loop wired to `runner`; the engine is imported here only."""
    import time

    from wing_parser.automix.live_limits import LiveLimits
    from wing_parser.automix.live_loop import LiveAutomix

    return LiveAutomix(
        options, runner.load_scene, runner.read_document, runner.write_leaf,
        clock or time.monotonic, limits=limits or LiveLimits(),
        propose_fn=runner.propose)
