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
(`main_window.py:163-165`), so nothing in the app would -- and a
`QThread` still running when Qt tears the application down prints
"QThread: Destroyed while thread is still running" and can take the
process with it.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import QCoreApplication

from wing_parser.ui.generator_worker import GeneratorWorker
from wing_parser.ui.live_guard import MAX_INTERVAL, RoundGuard

#: How long `finish` waits for a round to end, in milliseconds --
#: DERIVED from the slowest interval the panel offers, not picked. A
#: cancel is seen before the next `get_many`, and now (D-42) the pace
#: sleep sees it too: `poller.watch`'s `_pace` waits on `self.cancel`
#: itself (`poller.py:121-123`), so the wait after Stop covers only the
#: round already in flight, not a whole extra interval on top of it.
#: 2000 ms -- the first number tried here -- was SHORTER than one round
#: at interval 5 and returned False with the thread alive; the bound
#: below is left generous rather than retuned, since shrinking it needs
#: its own measurement against a real desk (see D-42 in
#: docs/tech-debt.md).
WAIT_MS = int((MAX_INTERVAL + 1.0) * 1000)


def on_quit(slot) -> None:
    """Call `slot` when the application is about to quit, if there is one.

    **`slot`'s answer is discarded, deliberately.** `shutdown` returns
    False when the thread outlived its wait, and at `aboutToQuit` there
    is nothing left to do with that: `QThread.terminate` is the only
    stronger move and it is unsafe -- it can stop the thread inside the
    socket read or inside the interpreter. So the wait is sized to cover
    the worst legal case (see `WAIT_MS`) and a False is accepted as a
    fact rather than acted on.

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
                    guard, watch_list, interval=interval, cancel=self.cancel)

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
        page, and only the payload differs (`on_end` takes it optional).

        The two terminal ones go through `_gate`, so an abandoned
        session answers for ITSELF. A page asking "was the current
        session abandoned?" gets the wrong answer in the one sequence
        that matters: abandon A, start B, and A's queued terminal signal
        is then judged against B's flag, ends B's watch on the page and
        -- through the disconnect guard -- abandons B too. Reproduced in
        review round 2.
        """
        self.worker.produced.connect(on_change)
        self.worker.progress.connect(on_round)
        self.worker.finished.connect(self._gate(on_end))
        self.worker.finished_cancelled.connect(self._gate(on_end))
        self.worker.failed.connect(self._gate(on_fail))

    def _gate(self, callback):
        """`callback`, unless THIS session was abandoned by then.

        The closure holds the session and the callback, so the worker's
        connection keeps both alive until it really stops -- which is
        also why a late signal cannot reach a half-destroyed page: it
        reaches a whole one, and is dropped there.
        """
        def deliver(*payload) -> None:
            if not self.abandoned:
                callback(*payload)

        return deliver

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
        the destroyed-while-running abort above. **The bound stays
        generous rather than shrunk** (D-42): the guard raises before the
        next `get_many`, and the pace sleep now sees the cancel too, so
        in practice the wait covers only the round in flight -- but
        `WAIT_MS` is left sized for a whole interval plus that round,
        since shrinking it needs its own measurement against a real desk.
        False means the thread outlived even that.
        """
        self.abandon()
        return self.worker.wait(wait_ms)
