"""A QThread destroyed while running aborts the process on PySide6 6.12 (D-58).

Each scenario runs in a subprocess so an abort is a failed test, not a dead suite.
"""

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

pytest.importorskip("PySide6")

ROOT = Path(__file__).resolve().parents[1]

_PRELUDE = """
import sys; sys.path.insert(0, %r)
import gc, threading
from PySide6.QtWidgets import QApplication, QWidget
from wing_parser.ui.workers import CallRunner
app = QApplication([])
gate = threading.Event()
owner = QWidget()
runner = CallRunner(owner)
runner.start("probe", lambda: gate.wait(5), on_success=lambda r: None,
             on_failure=lambda e: None)
"""


def _run(body: str):
    code = (textwrap.dedent(_PRELUDE) % str(ROOT)) + textwrap.dedent(body)
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    return subprocess.run([sys.executable, "-I", "-c", code], capture_output=True,
                          text=True, timeout=60, env=env,
                          cwd=os.getcwd(), check=False)


def test_owner_destroyed_with_a_hung_active_worker_does_not_abort():
    out = _run("""
        runner.cancel()                 # settled, thread still hanging in gate.wait
        del runner
        owner.close(); owner.deleteLater(); del owner
        app.processEvents(); gc.collect()
        gate.set()
        from wing_parser.ui.workers import shutdown_all
        shutdown_all(5000)
        print("SURVIVED")
    """)
    assert out.returncode == 0 and "SURVIVED" in out.stdout, out.stderr[-500:]


def test_shutdown_is_bounded_and_keeps_stragglers_alive():
    out = _run("""
        import time
        t0 = time.monotonic()
        runner.shutdown(200)            # worker hangs 5 s; must not block longer
        assert time.monotonic() - t0 < 2.0
        del runner; owner.deleteLater(); del owner; gc.collect()
        gate.set()
        from wing_parser.ui.workers import shutdown_all
        shutdown_all(5000)
        print("BOUNDED")
    """)
    assert out.returncode == 0 and "BOUNDED" in out.stdout, out.stderr[-500:]
