"""Closing an owner mid-call never destroys a running QThread (D-58).

PySide6 6.12 aborts the process when a running QThread is destroyed. Each
test hangs a call on a gate the test opens at the end, closes the owner,
and checks the worker is finished or still parked in the keep-alive
registry -- never gone while running.
"""

import dataclasses
import gc
import threading
import time

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import QEvent  # noqa: E402


def _active_worker(runner):
    return runner._active["worker"]


def _assert_safe(worker, gate, qt_app):
    """Parked while running, then really stops once the gate opens."""
    from wing_parser.ui import worker_registry

    assert (not worker.isRunning()) or worker in worker_registry._LIVE
    gate.set()
    assert worker.wait(5000)
    qt_app.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    gc.collect()


def _hang(gate):
    return lambda *args: gate.wait(timeout=5.0)


def test_helper_waits_once_for_all_runners_and_is_bounded(qt_app):
    from PySide6.QtWidgets import QWidget
    from wing_parser.ui.runner_shutdown import shutdown_runners
    from wing_parser.ui.workers import CallRunner

    gate = threading.Event()
    owner = QWidget()
    runners = [CallRunner(owner) for _ in range(3)]
    for runner in runners:
        runner.start("probe", _hang(gate), on_success=lambda r: None,
                     on_failure=lambda e: None)
    workers = [_active_worker(r) for r in runners]
    t0 = time.monotonic()
    shutdown_runners(owner, 300)
    assert time.monotonic() - t0 < 1.5          # one bound, not three
    for worker in workers:
        _assert_safe(worker, gate, qt_app)


def test_closing_settings_mid_probe_parks_the_worker(qt_app, tmp_path, monkeypatch):
    from wing_parser import config
    from wing_parser.ui.settings_dialog import SettingsDialog

    monkeypatch.setenv(config.ENV_VAR, str(tmp_path))
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("WING_DISABLE_LLM", raising=False)
    gate = threading.Event()
    dlg = SettingsDialog(probe=lambda cfg: gate.wait(5.0) or (True, "ok"))
    dlg.show()
    assert dlg.run_probe()
    worker = _active_worker(dlg._runner)
    dlg.reject()
    assert not dlg._runner.busy
    _assert_safe(worker, gate, qt_app)
    dlg.deleteLater()


def test_closing_the_vocabulary_dialog_mid_assistant_call_parks_the_worker(
        qt_app, tmp_path, monkeypatch):
    from wing_parser.ui.vocabulary_window import VocabularyWindow

    monkeypatch.delenv("WING_DISABLE_LLM", raising=False)
    gate = threading.Event()
    window = VocabularyWindow(None, directory=tmp_path)
    runner = window.assistant_tab._runner
    runner.start("proposal", _hang(gate), on_success=lambda r: None,
                 on_failure=lambda e: None)
    worker = _active_worker(runner)
    window.reject()
    assert not runner.busy
    _assert_safe(worker, gate, qt_app)
    window.deleteLater()


def test_closing_the_main_window_mid_import_and_console_calls(qt_app, monkeypatch):
    from tests.fake_desk import FakeDesk
    from wing_parser.net.identity import WingIdentity
    from wing_parser.ui.main_window import MainWindow

    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    gate = threading.Event()
    window = MainWindow(None)
    window.show()
    import_runner = window.pages["import_"]._runner
    import_runner.start("proposal", _hang(gate), on_success=lambda r: None,
                        on_failure=lambda e: None)
    bar = window.pages["console"].connect_bar
    bar._transport = dataclasses.replace(
        FakeDesk().transport(),
        identity=lambda host: gate.wait(5.0) or WingIdentity(
            ip=host, name="x", model="y", serial="z", firmware="f"))
    bar.address.setCurrentText("192.168.128.28")
    assert bar.connect_now()
    workers = [_active_worker(import_runner), _active_worker(bar._runner)]

    window.close()
    assert not import_runner.busy and not bar._runner.busy
    for worker in workers:
        _assert_safe(worker, gate, qt_app)
    window.deleteLater()
