"""Pure full-auto loop (spec section 7): no Qt, no network, injected clock.

Each tick re-reads the desk, re-runs `propose` on the live state and walks
the desk toward the proposal in small, rate-limited steps. The loop never
imports a writer: it receives `write_leaf`, and the UI wires that to its one
audited door. A leaf the operator moved is locked for the session (AM-19).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any, Callable

from wing_parser.automix import knowledge
from wing_parser.automix.bounds import Bounds
from wing_parser.automix.engine import propose
from wing_parser.automix.live_limits import LiveLimits, _is_number
from wing_parser.automix.options import AutomixOptions

# Audible, high-value moves first; inserts and FX last.
WRITE_ORDER = ("fader", "eq", "hpf", "comp", "gate", "sends", "fx", "inserts")


class LoopState(enum.Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass(frozen=True)
class TickReport:
    state: LoopState
    written: tuple = ()          # ((path, value), ...)
    skipped_locked: tuple = ()   # paths the proposal wanted but are locked
    newly_locked: tuple = ()     # paths the operator touched this tick
    refused: tuple = ()          # paths blocked by the final bounds check
    pending: int = 0             # unlocked changes still short of their target after this tick
    errors: tuple = ()           # ((path or "read", message), ...)


@dataclass
class LiveAutomix:
    options: AutomixOptions
    load_scene: Callable[[dict], Any]
    read_document: Callable[[], dict]
    write_leaf: Callable[[str, Any], Any]
    clock: Callable[[], float]
    limits: LiveLimits = field(default_factory=LiveLimits)
    propose_fn: Callable = propose
    bounds: Bounds | None = None
    state: LoopState = LoopState.RUNNING

    def __post_init__(self) -> None:
        self._bounds = self.bounds or Bounds(knowledge.load().bounds)
        self._last_written: dict = {}
        self._locked: set = set()
        self._failing = 0
        self._last_tick: float | None = None

    @property
    def locked_paths(self) -> frozenset:
        return frozenset(self._locked)

    def stop(self) -> None:
        if self.state is LoopState.RUNNING:
            self.state = LoopState.STOPPED

    def due(self) -> bool:
        return self.state is LoopState.RUNNING and (
            self._last_tick is None or self.clock() - self._last_tick >= self.limits.tick_s)

    def tick(self) -> TickReport:
        if self.state is not LoopState.RUNNING:
            return TickReport(self.state)
        self._last_tick = self.clock()
        try:
            document = self.read_document()
            proposal = self.propose_fn(self.load_scene(document), document, self.options)
        except Exception as exc:  # noqa: BLE001 - a desk or engine fault must not escape the loop
            return self._finish(errors=(("read", str(exc)),))
        newly, skipped, refused, todo = [], [], [], []
        for change in sorted(proposal.changes, key=_priority):
            path = change.path
            if path not in self._locked and path in self._last_written and _differs(
                    self._last_written[path], change.before, self.limits.tolerance):
                self._locked.add(path)
                newly.append(path)
            if path in self._locked:
                skipped.append(path)
                continue
            value = self.limits.next_value(path, change.before, change.after)
            if value is None:
                continue
            if self._bounds.violation(path, value) or self._bounds.violation(path, change.after):
                refused.append(path)
                continue
            todo.append((path, value, change.after))
        written, errors = [], []
        for path, value, _ in todo[: self.limits.max_writes_per_tick]:
            try:
                self.write_leaf(path, value)
            except Exception as exc:  # noqa: BLE001 - recorded; stop writing this tick
                errors.append((path, str(exc)))
                break
            self._last_written[path] = value
            written.append((path, value))
        done = {path for (path, value), (_, _, after) in zip(written, todo) if value == after}
        pending = sum(1 for path, _, _ in todo if path not in done)
        return self._finish(tuple(written), tuple(skipped), tuple(newly), tuple(refused), pending, tuple(errors))

    def _finish(self, written=(), skipped=(), newly=(), refused=(), pending=0, errors=()) -> TickReport:
        self._failing = self._failing + 1 if errors else 0
        if self._failing >= self.limits.max_failing_ticks:
            self.state = LoopState.FAILED
        return TickReport(self.state, written, skipped, newly, refused, pending, errors)


def _priority(change) -> tuple:
    rank = WRITE_ORDER.index(change.stage) if change.stage in WRITE_ORDER else len(WRITE_ORDER)
    return rank, change.path


def _differs(written, current, tolerance: float) -> bool:
    if _is_number(written) and _is_number(current):
        return abs(written - current) > tolerance
    return written != current
