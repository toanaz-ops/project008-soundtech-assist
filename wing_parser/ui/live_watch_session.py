"""One watch session: the thread, its cancel event, and no widgets.

Built here rather than inside `LiveEventsView` so the view holds only
chrome, and so the one piece of wiring with a rule behind it is written
once, in the open:

* **A generator, not a plain return.** `run_watch` yields from the
  poller inside a `with`, so the socket stays open for the whole stream
  and is closed however the loop ends -- run out, `Cancelled`, or
  `DeskLost`. A function that returned `poller.watch(...)` would close
  the client before the first round was read.
* **The guard is built inside it**, so nothing touches the desk until
  the thread actually runs, and so its rounds report straight into this
  worker's `progress` signal (`generator_worker.py:94-97`).
* **`stop` sets an event, and nothing else.** `RoundGuard` raises
  `Cancelled` before its next `get_many` (`live_guard.py:89-91`), so
  stop latency is bounded by one round whatever the desk's speed -- and
  no watch logic lives in a widget. One session per watch (D5): the
  loop never runs on a `QTimer` on the GUI thread.

It names a `Transport` but never `net` itself, the rule every `ui/`
module but `live_controller.py` follows.

`finish` and `on_quit` are the other end of the same rule: a watch has
no deadline, so something has to end it when the process does.
`MainWindow.closeEvent` only saves window state
(`main_window.py:162-164`), so nothing in the app would -- and a
`QThread` still running when Qt tears the application down prints
"QThread: Destroyed while thread is still running" and can take the
process with it.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import QCoreApplication

from wing_parser.ui.generator_worker import GeneratorWorker
from wing_parser.ui.live_guard import RoundGuard

#: How long `finish` waits for a round to end, in milliseconds. Generous
#: against the 0.05-5 s interval the panel offers, and bounded so a desk
#: that has gone quiet cannot hang the quit.
WAIT_MS = 2000


def on_quit(slot) -> None:
    """Call `slot` when the application is about to quit, if there is one.

    The `None` guard is not defensive dressing: a widget built before
    `QApplication` exists is legal, and the import-time half of the test
    suite does it.
    """
    application = QCoreApplication.instance()
    if application is not None:
        application.aboutToQuit.connect(slot)


class WatchSession:
    """The `GeneratorWorker` draining one watch, and the way to stop it."""

    def __init__(self, transport, host, watch_list, interval):
        self.cancel = threading.Event()
        #: Set by `abandon` and `finish`. The worker still fires exactly
        #: one terminal signal after either, and the view must NOT act on
        #: it: the page has already moved on -- disconnected, or quitting
        #: -- and re-transitioning from that signal would drag it back
        #: out of the state it was just put in.
        self.abandoned = False

        def run_watch():
            with transport.client(host) as client:
                guard = RoundGuard(
                    client, host, self.cancel,
                    on_round=self.worker.report_progress)
                yield from transport.watch(
                    guard, watch_list, interval=interval)

        # **No Qt parent**, deliberately. `GeneratorWorker.start` keeps
        # every started worker in a module list and prunes it by calling
        # `isRunning()` on each (`generator_worker.py:101-103`). Give the
        # thread a widget parent as well and Qt deletes the C++ QThread
        # with that widget while the Python wrapper is still in that
        # list, so the NEXT watch's `start()` dies with "Internal C++
        # object (GeneratorWorker) already deleted" -- measured, and it
        # took down four tests in a row before this line said so.
        self.worker = GeneratorWorker(run_watch)

    def bind(self, on_change, on_round, on_end, on_fail) -> None:
        """The worker's five signals onto four callbacks: a watch that
        ran itself out and one that was stopped end the same way for a
        page, and only the payload differs (`on_end` takes it optional)."""
        self.worker.produced.connect(on_change)
        self.worker.progress.connect(on_round)
        self.worker.finished.connect(on_end)
        self.worker.finished_cancelled.connect(on_end)
        self.worker.failed.connect(on_fail)

    def start(self) -> None:
        """Run it. The worker keeps itself referenced until it stops."""
        self.worker.start()

    def stop(self) -> None:
        """Ask for the end; the guard raises before its next round."""
        self.cancel.set()

    def is_running(self) -> bool:
        return self.worker.isRunning()

    def abandon(self) -> None:
        """Stop, and disown whatever the worker says next."""
        self.abandoned = True
        self.stop()

    def finish(self, wait_ms: int = WAIT_MS) -> bool:
        """Stop, then block until the thread really ends. True if it did.

        The only blocking call in this module, and it blocks the GUI
        thread on purpose: the caller is quitting, and the alternative is
        the destroyed-while-running abort above. The guard raises before
        its next round, so the wait is one round plus whatever the
        in-flight `get_many` still owes.
        """
        self.abandon()
        return self.worker.wait(wait_ms)
