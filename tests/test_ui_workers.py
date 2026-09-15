"""The concurrency law: every model call on a cancellable worker.

Task C (wave 1b), ruled 2026-08-26: a model call runs off the GUI
thread under a numeric timeout, with Cancel semantics and a one-call-
at-a-time guard. No test here sleeps more than a tick: callables block
on threading.Event gates the test controls, and timeouts are injected
as 0-second overrides.
"""

import threading
import time

import pytest

pytest.importorskip("PySide6.QtCore")

from PySide6.QtCore import QTimer

from tests.fake_desk import FakeDesk
from wing_parser.net.codec import OscMessage
from wing_parser.net.watch import poller
from wing_parser.net.watch.list import WatchList
from wing_parser.ui.generator_worker import GeneratorWorker, running_workers
from wing_parser.ui.live_guard import Cancelled, DeskLost, RoundGuard
from wing_parser.ui.workers import (
    TIMEOUTS,
    CallRunner,
    CallTimedOut,
    FunctionWorker,
)


def hold_gate(gate: threading.Event) -> str:
    """A stand-in model call: returns only when the test opens the gate."""
    gate.wait(timeout=5.0)
    return "wire result"


def boom() -> None:
    raise ValueError("offline")


@pytest.fixture
def runner(qt_app):
    return CallRunner()


def settle(qt_app, predicate, limit_s=2.0):
    """Pump Qt events until predicate() holds; queued signals need this."""
    deadline = time.monotonic() + limit_s
    while time.monotonic() < deadline:
        if predicate():
            return True
        qt_app.processEvents()
        time.sleep(0.005)
    return False


# -- FunctionWorker -----------------------------------------------------


def test_finished_delivers_the_result(qt_app):
    gate = threading.Event()
    got = []
    worker = FunctionWorker(hold_gate, gate)
    worker.finished.connect(got.append)
    worker.start()
    gate.set()
    assert settle(qt_app, lambda: bool(got))
    assert got == ["wire result"]
    assert settle(qt_app, lambda: not worker.isRunning())


def test_failed_delivers_the_exception(qt_app):
    got = []
    worker = FunctionWorker(boom)
    worker.failed.connect(got.append)
    worker.start()
    assert settle(qt_app, lambda: bool(got))
    assert isinstance(got[0], ValueError)
    assert "offline" in str(got[0])
    assert settle(qt_app, lambda: not worker.isRunning())


def test_cancel_discards_the_result_and_reports_cancelled(qt_app):
    gate = threading.Event()
    results, failures, cancelled = [], [], []
    worker = FunctionWorker(hold_gate, gate)
    worker.finished.connect(results.append)
    worker.failed.connect(failures.append)
    worker.finished_cancelled.connect(lambda: cancelled.append(1))
    worker.start()
    worker.cancel()
    gate.set()
    assert settle(qt_app, lambda: bool(cancelled))
    assert results == [] and failures == []
    assert settle(qt_app, lambda: not worker.isRunning())


def test_the_gui_thread_keeps_pumping_while_a_worker_runs(qt_app):
    """The ruling's point: the window must not freeze during a model call."""
    gate = threading.Event()
    worker = FunctionWorker(hold_gate, gate)
    worker.start()
    ticks = []
    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start()
    try:
        assert settle(qt_app, lambda: len(ticks) >= 5), "event loop stalled"
    finally:
        gate.set()
        settle(qt_app, lambda: not worker.isRunning())
        timer.stop()


# -- CallRunner ---------------------------------------------------------


def test_timeouts_table_carries_the_ruled_numbers():
    assert TIMEOUTS == {
        "proposal": 120, "guesses": 180, "probe": 30,
        "connect": 5, "walk": 60, "snapshot": 90,
    }


def test_runner_timeout_fails_the_call_with_a_distinct_error(qt_app, runner):
    gate = threading.Event()
    successes, failures = [], []
    started = runner.start(
        "probe", hold_gate, gate,
        timeout=0, on_success=successes.append, on_failure=failures.append,
    )
    try:
        assert started
        assert settle(qt_app, lambda: bool(failures))
        exc = failures[0]
        assert isinstance(exc, CallTimedOut)
        assert exc.kind == "probe" and exc.seconds == 0
        assert successes == []
        assert not runner.busy
    finally:
        gate.set()
        settle(qt_app, lambda: not runner.busy)


def test_runner_rejects_a_second_call_while_one_is_running(qt_app, runner):
    gate = threading.Event()
    first, second = [], []
    assert runner.start(
        "guesses", hold_gate, gate,
        on_success=first.append, on_failure=lambda exc: None,
    )
    rejected = runner.start(
        "proposal", hold_gate, gate,
        on_success=second.append, on_failure=lambda exc: None,
    )
    try:
        assert not rejected, "a second concurrent call must queue-reject"
        assert runner.busy
        gate.set()
        assert settle(qt_app, lambda: bool(first))
        assert second == []
    finally:
        gate.set()


def test_runner_cancel_settles_now_and_leaves_room_for_a_retry(qt_app, runner):
    gate = threading.Event()
    outcomes = {"success": [], "cancel": []}
    assert runner.start(
        "proposal", hold_gate, gate,
        on_success=outcomes["success"].append,
        on_failure=lambda exc: None,
        on_cancel=lambda: outcomes["cancel"].append(1),
    )
    runner.cancel()
    assert outcomes["cancel"] == [1], "cancel settles without waiting"
    assert not runner.busy, "the page is usable again immediately"
    retry = runner.start(
        "proposal", lambda: "fast",
        on_success=outcomes["success"].append,
        on_failure=lambda exc: None,
    )
    assert retry
    assert settle(qt_app, lambda: outcomes["success"] == ["fast"])
    gate.set()
    never = settle(qt_app, lambda: len(outcomes["success"]) > 1)
    assert not never, "the cancelled wire result must never arrive"


def test_runner_delivers_exceptions_through_on_failure(qt_app, runner):
    failures = []
    assert runner.start(
        "probe", boom, on_success=lambda r: None, on_failure=failures.append,
    )
    assert settle(qt_app, lambda: bool(failures))
    assert isinstance(failures[0], ValueError)


# -- ButtonRunner: the ruled chrome around one call ----------------------


@pytest.fixture
def chrome(qt_app):
    from PySide6.QtWidgets import QLabel, QPushButton

    from wing_parser.ui.call_button import ButtonRunner

    primary = QPushButton("go")
    cancel = QPushButton("cancel")
    cancel.setVisible(False)
    status = QLabel("")
    runner = CallRunner()
    seen = {"errors": [], "success": []}
    chrome = ButtonRunner(
        runner=runner, primary=primary, cancel=cancel,
        report=status.setText,
        running="working...", cancelled="stopped",
        timeout_text="gave up after {seconds} s", busy_text="one at a time",
        on_error=seen["errors"].append,
    )
    return chrome, primary, cancel, status, runner, seen


def test_running_state_disables_primary_and_shows_cancel(chrome):
    chrome_obj, primary, cancel, status, runner, seen = chrome
    gate = threading.Event()
    assert chrome_obj.run(
        "probe", hold_gate, gate, on_success=seen["success"].append,
    )
    try:
        assert not primary.isEnabled() and cancel.isVisibleTo(primary.parent())
        assert status.text() == "working..."
    finally:
        gate.set()


def test_delivery_restores_buttons_clears_status_and_continues(qt_app, chrome):
    chrome_obj, primary, cancel, status, runner, seen = chrome
    assert chrome_obj.run(
        "probe", lambda: 42, on_success=seen["success"].append,
    )
    assert settle(qt_app, lambda: seen["success"] == [42])
    assert primary.isEnabled() and not cancel.isVisibleTo(primary.parent())
    assert status.text() == ""


def test_timeout_reports_the_distinct_message_and_restores(qt_app, chrome):
    chrome_obj, primary, cancel, status, runner, seen = chrome
    gate = threading.Event()
    assert chrome_obj.run(
        "probe", hold_gate, gate, timeout=0,
        on_success=seen["success"].append,
    )
    try:
        assert settle(qt_app, lambda: "gave up" in status.text())
        assert "0 s" in status.text()
        assert primary.isEnabled()
        assert seen["errors"] == []
    finally:
        gate.set()


def test_a_failure_is_routed_to_on_error(qt_app, chrome):
    chrome_obj, primary, cancel, status, runner, seen = chrome
    assert chrome_obj.run("probe", boom, on_success=seen["success"].append)
    assert settle(qt_app, lambda: bool(seen["errors"]))
    assert isinstance(seen["errors"][0], ValueError)
    assert primary.isEnabled()


def test_busy_reports_the_queue_rejection(qt_app, chrome):
    chrome_obj, primary, cancel, status, runner, seen = chrome
    gate = threading.Event()
    assert chrome_obj.run(
        "probe", hold_gate, gate, on_success=seen["success"].append,
    )
    try:
        assert not chrome_obj.run(
            "probe", hold_gate, gate, on_success=lambda r: None,
        )
        assert status.text() == "one at a time"
    finally:
        gate.set()
        settle(qt_app, lambda: not runner.busy)


# -- GeneratorWorker: the watch loop's thread (wave 2, spec S7.2/S7.3) ----


HOST = "192.168.128.28"


def counting(limit: int):
    """A stand-in watch: yields `limit` items and ends of its own accord."""
    for index in range(limit):
        yield index


def cancelled_after(limit: int):
    """...and then Stop was pressed, the way `RoundGuard` reports it."""
    yield from counting(limit)
    raise Cancelled(f"watch on {HOST} stopped before the next round")


def lost_after(limit: int):
    """...and then the desk stopped answering, three rounds running."""
    yield from counting(limit)
    raise DeskLost(HOST, 3)


def hold_gate_then_yield(gate: threading.Event):
    """A watch that is still running until the test opens the gate."""
    gate.wait(timeout=5.0)
    yield "one late change"


def _fader(address: str, db: float) -> OscMessage:
    return OscMessage(address, "sff", (str(db), 0.5, db))


def _small_watch_list() -> WatchList:
    """Two watched leaves on one strip -- enough to count rounds by hand."""
    return WatchList(
        addresses=("/ch/1/$fdr", "/ch/1/$mute"), unresolved=(), strips={"ch": 1}
    )


def _answering_desk() -> FakeDesk:
    """A desk whose /ch/1 fader moves once, on the loop's first round."""
    leaves = {
        "/ch/1/$fdr": _fader("/ch/1/$fdr", -6.0),
        "/ch/1/$mute": OscMessage("/ch/1/$mute", "sfi", ("0", 0.0, 0)),
        "/ch/1/name": OscMessage("/ch/1/name", "s", ("KICK",)),
    }
    return FakeDesk(
        leaves=leaves,
        rounds=[
            {"/ch/1/$fdr": _fader("/ch/1/$fdr", -6.0)},   # read_labels
            {"/ch/1/$fdr": _fader("/ch/1/$fdr", -6.0)},   # priming sample
            {"/ch/1/$fdr": _fader("/ch/1/$fdr", -3.0)},   # round 1: a change
        ],
    )


def test_generator_worker_emits_every_produced_item_in_order(qt_app):
    produced, done, failures = [], [], []
    worker = GeneratorWorker(counting, 5)
    worker.produced.connect(produced.append)
    worker.finished.connect(done.append)
    worker.failed.connect(failures.append)

    worker.start()

    assert settle(qt_app, lambda: bool(done))
    assert produced == [0, 1, 2, 3, 4], "every item, in the generator's order"
    assert failures == []
    summary = done[0]
    assert summary.events == 5
    # No RoundGuard in this drive, so nothing ever reported a round: the
    # count comes from the guard, never from the worker's own bookkeeping.
    assert summary.rounds == 0
    assert summary.seconds >= 0.0
    assert settle(qt_app, lambda: not worker.isRunning())


def test_generator_worker_reports_cancelled_separately_from_failed(qt_app):
    produced, done, failures, cancelled = [], [], [], []
    worker = GeneratorWorker(cancelled_after, 2)
    worker.produced.connect(produced.append)
    worker.finished.connect(done.append)
    worker.failed.connect(failures.append)
    worker.finished_cancelled.connect(lambda: cancelled.append(1))

    worker.start()

    assert settle(qt_app, lambda: bool(cancelled))
    assert cancelled == [1]
    # Stop is not a failure, and it is not a normal end either: exactly
    # one terminal signal fires, and it is this one.
    assert failures == [] and done == []
    # The changes that arrived before Stop were real and stay on screen.
    assert produced == [0, 1]
    assert settle(qt_app, lambda: not worker.isRunning())


def test_generator_worker_turns_desklost_into_failed(qt_app):
    produced, done, failures, cancelled = [], [], [], []
    worker = GeneratorWorker(lost_after, 2)
    worker.produced.connect(produced.append)
    worker.finished.connect(done.append)
    worker.failed.connect(failures.append)
    worker.finished_cancelled.connect(lambda: cancelled.append(1))

    worker.start()

    assert settle(qt_app, lambda: bool(failures))
    exc = failures[0]
    assert isinstance(exc, DeskLost)
    assert exc.host == HOST and exc.rounds == 3
    assert done == [] and cancelled == []
    assert produced == [0, 1], "the events before the desk went away are kept"
    assert settle(qt_app, lambda: not worker.isRunning())


def test_generator_worker_keeps_a_stopped_thread_referenced(qt_app):
    """A running watch thread must never be GC'd, the way CallRunner keeps
    retired workers referenced (`workers.py:166-169`)."""
    gate = threading.Event()
    worker = GeneratorWorker(hold_gate_then_yield, gate)
    worker.start()
    try:
        assert worker in running_workers(), "a live thread must stay referenced"
    finally:
        gate.set()
    assert settle(qt_app, lambda: not worker.isRunning())

    later = GeneratorWorker(counting, 1)
    later.start()
    # The list is pruned, not grown forever: a thread that really stopped
    # is dropped the next time one starts.
    assert worker not in running_workers()
    assert settle(qt_app, lambda: not later.isRunning())


def test_the_gui_thread_keeps_pumping_while_a_generator_worker_runs(qt_app):
    """A watch runs for a whole show; the window must stay alive under it."""
    gate = threading.Event()
    worker = GeneratorWorker(hold_gate_then_yield, gate)
    worker.start()
    ticks = []
    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start()
    try:
        # The worker must still be ON the wire while the ticks land --
        # otherwise this would pass against a thread that did nothing.
        assert settle(qt_app, lambda: len(ticks) >= 5 and worker.isRunning())
    finally:
        gate.set()
        settle(qt_app, lambda: not worker.isRunning())
        timer.stop()


def test_a_real_watch_over_a_fake_desk_produces_changes_and_counts_rounds(qt_app):
    """The real poller, the real guard, a real thread -- no stand-ins."""
    desk = _answering_desk()
    cancel = threading.Event()
    rounds: list[tuple[int, int]] = []

    def run_watch():
        # `worker` resolves when this runs, on the worker thread: the
        # guard reports its rounds straight into the worker's signal.
        guard = RoundGuard(
            desk.client(HOST), HOST, cancel, on_round=worker.report_progress
        )
        return poller.watch(guard, _small_watch_list(), interval=0, max_rounds=1)

    produced, done = [], []
    worker = GeneratorWorker(run_watch)
    worker.produced.connect(produced.append)
    worker.finished.connect(done.append)
    worker.progress.connect(lambda answered, total: rounds.append((answered, total)))

    worker.start()

    assert settle(qt_app, lambda: bool(done))
    assert [change.address for change in produced] == ["/ch/1/$fdr"]
    assert produced[0].before == -6.0 and produced[0].after == -3.0
    # read_labels asks for one name, then the priming sample and the
    # loop's single round ask for both watched leaves (`poller.py:84-86`).
    assert rounds == [(1, 1), (2, 2), (2, 2)]
    assert done[0].events == 1 and done[0].rounds == 3
    assert settle(qt_app, lambda: not worker.isRunning())


def test_a_real_watch_fails_when_the_guard_declares_the_desk_lost(qt_app):
    desk = FakeDesk(rounds=[{}])          # answers nothing, raises nothing
    cancel = threading.Event()

    def run_watch():
        guard = RoundGuard(
            desk.client(HOST), HOST, cancel, on_round=worker.report_progress
        )
        return poller.watch(guard, _small_watch_list(), interval=0, max_rounds=10)

    produced, done, failures = [], [], []
    worker = GeneratorWorker(run_watch)
    worker.produced.connect(produced.append)
    worker.finished.connect(done.append)
    worker.failed.connect(failures.append)

    worker.start()

    assert settle(qt_app, lambda: bool(failures))
    assert isinstance(failures[0], DeskLost) and failures[0].rounds == 3
    # D6: a dead desk yields nothing at all, so there was never anything
    # for the worker to judge -- the guard had to raise.
    assert produced == [] and done == []
    assert settle(qt_app, lambda: not worker.isRunning())


def test_the_three_live_budgets_are_the_ruled_numbers():
    """Spec S7.2/D14: UDP to a desk, not HTTP to a provider."""
    assert TIMEOUTS["connect"] == 5      # backstop over identity.py's 2.0 s
    assert TIMEOUTS["walk"] == 60        # ~60x the measured ~1.00 s clean walk
    assert TIMEOUTS["snapshot"] == 90    # 9x the measured ~10 s console read
