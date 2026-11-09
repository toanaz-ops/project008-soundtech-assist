"""Wave 12 phase 1 UI: one smoke through the dialog, the mode setting, and
the AM-20 promise that building the window never loads the engine."""

import os
import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("PySide6.QtWidgets")

ROOT = Path(__file__).resolve().parents[1]


def test_dialog_proposes_and_applies_to_the_session(qt_app, vu_path):
    from wing_parser import automix
    from wing_parser.automix.options import VENUES
    from wing_parser.ui import automix_controls
    from wing_parser.ui.automix_dialog import AutomixDialog
    from wing_parser.ui.main_window import MainWindow
    from wing_parser.ui.session import Session

    # The UI repeats the engine's tuples so that menus never import it.
    assert automix_controls.GENRES == automix.GENRES
    assert automix_controls.STAGES == automix.STAGES
    assert automix_controls.VENUES == VENUES

    window = MainWindow(Session.open(vu_path))
    dialog = AutomixDialog(window)
    panel = dialog.options_panel
    panel.genre.setCurrentIndex(panel.genre.findData("pop"))
    dialog.propose()
    count = len(dialog._proposal.changes)
    assert count > 0
    assert dialog.changes_model.rowCount() == count
    dialog.changes.selectRow(0)
    assert dialog.detail.toPlainText()

    before = len(window.session.changes())
    assert dialog.apply(confirm=False) == count
    assert len(window.session.changes()) == before + count
    assert window.session.dirty


def test_mode_round_trips_and_hides_the_menu_action(qt_app, vu_path, tmp_path,
                                                    monkeypatch):
    from wing_parser import config
    from wing_parser.ui import settings_automix, state_store
    from wing_parser.ui.main_window import MainWindow
    from wing_parser.ui.session import Session

    monkeypatch.setenv(config.ENV_VAR, str(tmp_path))
    assert settings_automix.current_mode() == "draft"
    window = MainWindow(Session.open(vu_path))
    assert window._automix_action.isVisible()
    state_store.save_automix_mode(tmp_path, "disabled")
    assert settings_automix.current_mode() == "disabled"
    settings_automix.sync_menu(window)
    assert not window._automix_action.isVisible()
    state_store.save(tmp_path, dict(state_store.load(tmp_path),
                                    automix_mode="bogus"))
    assert settings_automix.current_mode() == "draft"


def test_building_the_main_window_does_not_load_the_engine():
    code = ("import sys\n"
            "from wing_parser.ui import main_window, menus, settings_dialog\n"
            "assert 'wing_parser.automix' not in sys.modules\n")
    done = subprocess.run(
        [sys.executable, "-c", code], cwd=ROOT, capture_output=True,
        text=True, env={**os.environ, "PYTHONPATH": str(ROOT)})
    assert done.returncode == 0, done.stderr
