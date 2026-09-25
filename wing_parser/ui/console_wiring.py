"""`ConsolePage`'s own signal wiring, split out for headroom (D-41).

A plain function over the page, not a method: it needs nothing from
`ConsolePage` beyond attribute access -- the same "a slice of the
owner's own book-keeping" shape `write_delay_support.py` uses for
`DelayedWriteDialog` -- so keeping it here costs the page nothing and
buys it back the lines its own state machine (`_fire`/`_begun`/etc.)
needs room to grow.
"""

from __future__ import annotations


def wire_console_page(page) -> None:
    """Connect every panel signal to the page's own handlers, whole.

    Extracted unchanged from `ConsolePage._wire` -- behaviour is
    identical, only the home of the code moved.
    """
    bar, walk = page.connect_bar, page.discovery
    pull, watch = page.snapshot, page.events

    bar.connect_button.clicked.connect(lambda: page._begun("connect", bar))
    bar.connected.connect(page._connected)
    bar.disconnected.connect(page._disconnected)

    walk.discover_button.clicked.connect(lambda: page._begun("walk", walk))
    walk.rerun_button.clicked.connect(lambda: page._begun("walk", walk))
    walk.discovered.connect(page._discovered)

    pull.pull_button.clicked.connect(lambda: page._begun("pull", pull))
    pull.session_pulled.connect(page._pulled)
    pull.exported.connect(page.exported)
    pull.doctor_requested.connect(page.doctor_requested)

    watch.started.connect(lambda: page._fire("watch"))
    watch.stopped.connect(lambda: page._fire("stop"))
    watch.lost.connect(lambda _exc: page._fire("lost"))
    # Reconnect is offered in `lost` but the handshake is the bar's
    # (`live_watch_bar.py:10-14`); unconnected it is a dead button.
    watch.reconnect_requested.connect(page._reconnect)

    for panel in (bar, walk, pull):
        panel.failed.connect(lambda _exc: page._fire("fail"))
        panel.cancel_button.clicked.connect(page._cancelled)
