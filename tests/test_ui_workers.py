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
    assert TIMEOUTS == {"proposal": 120, "guesses": 180, "probe": 30}


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
