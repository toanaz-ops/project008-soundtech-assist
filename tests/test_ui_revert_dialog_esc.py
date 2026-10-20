"""Esc / window-close on a countdown inside Revert all ends the run
(audit 2026-10-21, finding 1): W12 must hold for `reject()`, not only for the
Cancel button. Offscreen, no socket -- `FakeDesk` throughout."""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")

from tests.fake_desk import FakeDesk
from tests.test_ui_changes_send import _identity, _ledger, _sent, _window
from wing_parser.net.codec import OscMessage


def _open_run(qt_app, settle, vu_path, monkeypatch):
    from wing_parser.ui.apply_level import ApplyLevel
    from wing_parser.ui.write_delay_dialog import DelayedWriteDialog

    desk = FakeDesk(identity=_identity(),
                    leaves={f"/ch/{n}/fdr": OscMessage(f"/ch/{n}/fdr", "sff",
                                                       ("-6.0", 0.0, -6.0))
                            for n in (1, 2)},
                    readbacks={f"/ch/{n}/fdr": -12.0 for n in (1, 2)})
    window = _window(qt_app, vu_path)
    ledger = _ledger(qt_app, desk, window,
                     [_sent(f"/ch/{n}/fdr", f"ae_data.ch.{n}.fdr", -12.0, -6.0)
                      for n in (1, 2)])
    ledger._gate.arm.arm(_identity())
    ledger._gate.arm.level = ApplyLevel.DELAYED
    heard = []
    ledger.run_started.connect(lambda: heard.append("started"))
    ledger.run_finished.connect(lambda: heard.append("finished"))

    # `open()` would show an application-modal window; the offscreen run has
    # nobody to dismiss it, so only record it (the countdown logic is unchanged).
    dialogs = []
    monkeypatch.setattr(DelayedWriteDialog, "open", lambda self: dialogs.append(self))

    ledger.revert_all()

    assert len(dialogs) == 1 and heard == ["started"]
    # let the pre-flight read land: closing under a live worker is a
    # different (teardown) problem from the one under test
    assert settle(lambda: dialogs[0].desk_before is not None)
    return ledger, dialogs[0], desk, heard


def test_esc_on_a_countdown_inside_revert_all_ends_the_run(qt_app, settle, vu_path, monkeypatch):
    ledger, dialog, desk, heard = _open_run(qt_app, settle, vu_path, monkeypatch)
    cancelled = []
    dialog.cancelled.connect(lambda: cancelled.append(True))

    dialog.reject()                       # Esc / the title-bar X

    assert cancelled == [True]
    assert heard == ["started", "finished"]
    assert ledger._queue is None
    assert ledger.stop_button.isEnabled() is False
    assert desk.sets == [], "nothing was sent"


def test_the_cancel_button_still_ends_the_run_exactly_once(qt_app, settle, vu_path, monkeypatch):
    ledger, dialog, _desk, heard = _open_run(qt_app, settle, vu_path, monkeypatch)

    dialog.cancel_button.click()

    assert heard == ["started", "finished"]
    assert ledger._queue is None
