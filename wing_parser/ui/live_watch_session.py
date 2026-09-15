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
"""

from __future__ import annotations

import threading

from wing_parser.ui.generator_worker import GeneratorWorker
from wing_parser.ui.live_guard import RoundGuard


class WatchSession:
    """The `GeneratorWorker` draining one watch, and the way to stop it."""

    def __init__(self, transport, host, watch_list, interval):
        self.cancel = threading.Event()

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

    def start(self) -> None:
        """Run it. The worker keeps itself referenced until it stops."""
        self.worker.start()

    def stop(self) -> None:
        """Ask for the end; the guard raises before its next round."""
        self.cancel.set()

    def is_running(self) -> bool:
        return self.worker.isRunning()
