"""Persistence: geometry, last page and recent scenes survive a restart.

The store is plain functions over one JSON file under
config.knowledge_dir() — no Qt — so the round trips are testable
without a QApplication. The window-level tests cover the wiring.
"""

import json

import pytest

pytest.importorskip("PySide6.QtWidgets")

from wing_parser.ui import state_store


# -- pure store logic ---------------------------------------------------


def test_save_then_load_round_trips_a_state(tmp_path):
    state = {
        "geometry": "aabbcc", "page": "diff", "recent": ["x.snap"],
        "consoles": [],
    }
    state_store.save(tmp_path, state)
    assert state_store.load(tmp_path) == state


def test_load_without_a_file_yields_defaults(tmp_path):
    assert state_store.load(tmp_path) == {
        "geometry": None, "page": None, "recent": [], "consoles": [],
    }


def test_load_of_corrupt_json_yields_defaults_not_an_exception(tmp_path):
    (tmp_path / state_store.STATE_FILE).write_text("{not json", encoding="utf-8")
    assert state_store.load(tmp_path)["recent"] == []


def test_normalize_drops_junk_and_keeps_known_shape():
    state = {
        "geometry": 12345,               # not a hex string
        "page": "no-such-page",          # not a PAGE_ORDER key
        "recent": ["ok.snap", 7, None],  # junk entries
        "extra": True,                   # unknown key
    }
    clean = state_store.normalize(state)
    assert clean == {
        "geometry": None, "page": None, "recent": ["ok.snap"], "consoles": [],
    }


def test_remember_recent_moves_to_top_and_dedupes():
    recents = state_store.remember_recent(
        ["a.snap", "b.snap", "c.snap"], "b.snap"
    )
    assert recents == ["b.snap", "a.snap", "c.snap"]


def test_remember_recent_caps_the_list():
    seed = [f"f{i}.snap" for i in range(state_store.MAX_RECENT)]
    recents = state_store.remember_recent(seed, "new.snap")
    assert recents[0] == "new.snap"
    assert len(recents) == state_store.MAX_RECENT
    assert "f7.snap" not in recents


def test_forget_recent_removes_one_entry():
    recents = state_store.forget_recent(["a.snap", "b.snap"], "a.snap")
    assert recents == ["b.snap"]


def test_consoles_survive_a_save_and_load_round_trip(tmp_path):
    state = {
        "geometry": "aabbcc", "page": "diff", "recent": ["x.snap"],
        "consoles": ["192.168.1.10", "wing.local"],
    }
    state_store.save(tmp_path, state)
    assert state_store.load(tmp_path) == state


def test_a_state_file_without_consoles_degrades_to_an_empty_list(tmp_path):
    (tmp_path / state_store.STATE_FILE).write_text(
        json.dumps({"geometry": None, "page": None, "recent": []}),
        encoding="utf-8",
    )
    assert state_store.load(tmp_path)["consoles"] == []


def test_remember_console_moves_an_address_to_the_top_without_duplicating_it():
    consoles = state_store.remember_console(
        ["192.168.1.10", "192.168.1.11", "192.168.1.12"], "192.168.1.11"
    )
    assert consoles == ["192.168.1.11", "192.168.1.10", "192.168.1.12"]


def test_remember_console_caps_the_list_at_max_recent():
    seed = [f"192.168.1.{i}" for i in range(state_store.MAX_RECENT)]
    consoles = state_store.remember_console(seed, "192.168.1.99")
    assert consoles[0] == "192.168.1.99"
    assert len(consoles) == state_store.MAX_RECENT
    assert "192.168.1.7" not in consoles


def test_remember_console_compares_plain_strings_not_paths():
    # Path() would normalize "wing.local/" and "wing.local" to the same
    # thing, and would treat "a/b" as a path with a parent -- addresses
    # are opaque strings, not filesystem paths.
    consoles = state_store.remember_console(
        ["wing.local/", "a/b"], "wing.local"
    )
    assert consoles == ["wing.local", "wing.local/", "a/b"]


def test_forget_console_removes_only_that_address():
    consoles = state_store.forget_console(
        ["192.168.1.10", "192.168.1.11"], "192.168.1.10"
    )
    assert consoles == ["192.168.1.11"]


# -- window wiring ------------------------------------------------------


@pytest.fixture
def isolated_state(qt_app, monkeypatch, tmp_path):
    from wing_parser import config

    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    monkeypatch.setattr(
        config, "knowledge_dir", lambda override=None: tmp_path
    )
    from wing_parser.ui.main_window import MainWindow

    return tmp_path, MainWindow


def test_geometry_and_last_page_survive_close_and_reopen(isolated_state):
    tmp_path, MainWindow = isolated_state
    from PySide6.QtCore import QSize

    first = MainWindow(None)
    first.resize(1010, 604)
    first.switch_to("channels")
    first.close()
    second = MainWindow(None)
    assert second.size() == QSize(1010, 604)
    assert second.stack.currentWidget() is second.pages["channels"]


def test_recent_menu_lists_most_recent_first_and_opens(
        isolated_state, vu_path):
    tmp_path, MainWindow = isolated_state

    window = MainWindow(None)
    window._remember_recent(str(vu_path))
    other = tmp_path / "other.snap"
    other.write_text(vu_path.read_text(encoding="utf-8"), encoding="utf-8")
    window._remember_recent(str(other))
    labels = [a.text() for a in window._recent_menu.actions()]
    assert len(labels) == 2
    window._recent_menu.actions()[0].trigger()
    assert window.session is not None
    assert window.session.path == other


def test_opening_a_scene_records_it_in_the_recent_menu(
        isolated_state, vu_path, monkeypatch):
    _tmp_path, MainWindow = isolated_state
    from PySide6.QtWidgets import QFileDialog

    window = MainWindow(None)
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName",
        staticmethod(lambda *a, **k: (str(vu_path), "")),
    )
    window.open_file()
    labels = [a.text() for a in window._recent_menu.actions()]
    assert labels == [vu_path.name]


def test_clicking_a_missing_recent_entry_degrades_and_drops_it(
        isolated_state, monkeypatch):
    tmp_path, MainWindow = isolated_state
    from PySide6.QtWidgets import QMessageBox

    shown = []
    monkeypatch.setattr(QMessageBox, "information",
                        lambda *a, **k: shown.append(a))
    gone = tmp_path / "deleted.snap"
    gone.write_text("{}", encoding="utf-8")

    window = MainWindow(None)
    window._remember_recent(str(gone))
    gone.unlink()
    window._recent_menu.actions()[0].trigger()
    assert len(shown) == 1, "the operator is told the file is gone"
    labels = [a.text() for a in window._recent_menu.actions()]
    assert labels == [], "the dead entry is removed from the menu"
    assert window.session is None, "a missing file opens nothing"


def test_the_persisted_file_is_json_under_the_knowledge_dir(isolated_state):
    tmp_path, MainWindow = isolated_state
    window = MainWindow(None)
    window._remember_recent("x.snap")
    window.close()
    raw = json.loads(
        (tmp_path / state_store.STATE_FILE).read_text(encoding="utf-8")
    )
    assert raw["recent"] == ["x.snap"]
    assert raw["page"] == "doctor"
    assert isinstance(raw["geometry"], str)
