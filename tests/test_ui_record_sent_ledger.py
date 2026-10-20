"""A scene correction that raises must not cost the operator the ledger row
(audit 2026-10-21, finding 2). Offscreen, no socket -- `FakeDesk` throughout."""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")

from tests.fake_desk import FakeDesk
from tests.test_ui_changes_send import (
    PATH, _gate, _identity, _panel, _record, _window,
)


def test_a_raising_scene_correction_still_leaves_the_ledger_row_and_the_sent_signal(
        qt_app, vu_path):
    desk = FakeDesk(identity=_identity())
    window = _window(qt_app, vu_path)
    panel = _panel(qt_app, _gate(qt_app, desk), window)
    patch = window.session.record_value(PATH, "PRE", label="x", because="G8")
    emitted = []
    panel.sent.connect(lambda p, r: emitted.append(r))

    def _boom():
        raise RuntimeError("refresh blew up")

    window._refresh = _boom

    with pytest.raises(RuntimeError):
        panel.record_sent(patch, _record("GRP", False))   # a clamp -> apply_result refreshes

    assert len(panel.ledger.records()) == 1
    assert len(emitted) == 1


def test_a_clamped_result_keeps_its_badge_after_record_sent(qt_app, vu_path):
    """Cross-review: `apply_result` on a CLAMPED result refreshes the scene,
    which rebuilds the SendRows through `set_changes`. The badge must be
    re-applied from `_sent_rows`, so that list is filled before the refresh."""
    desk = FakeDesk(identity=_identity())
    window = _window(qt_app, vu_path)
    panel = _panel(qt_app, _gate(qt_app, desk), window)
    patch = window.session.record_value(PATH, "PRE", label="x", because="G8")
    rebuilt = []
    original_refresh = window._refresh

    def _refresh_and_rebuild():
        original_refresh()
        panel.set_changes(window.session.changes())
        rebuilt.append(True)

    window._refresh = _refresh_and_rebuild
    panel.set_changes(window.session.changes())

    panel.record_sent(patch, _record("GRP", False))   # a clamp

    assert rebuilt, "the clamp must have rebuilt the rows"
    row = panel.list.itemWidget(panel.list.item(0))
    assert row.badge.text()
    assert row.badge.isVisibleTo(row) is True
