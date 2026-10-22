"""Wave 5 (spec section 6): the Log page -- shows, writes, Export report."""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")

from wing_parser import writelog

DESK = {"name": "WING-GIAQUY", "serial": "01009Y90604AAE", "model": "wing-rack",
        "firmware": "3.1", "ip": "192.168.128.28"}


@pytest.fixture
def knowledge(tmp_path, monkeypatch):
    from wing_parser import config

    monkeypatch.setattr(config, "knowledge_dir", lambda override=None: tmp_path)
    return tmp_path


def _entry(code="AZ-1501", ts="2026-10-20T13:05:12.481+07:00", outcome="sent",
           kind="repair", show="BIDV Gala", venue="GEM Center", label="Insert"):
    return writelog.LogEntry(
        v=writelog.ENTRY_VERSION, ts=ts, show_code=code, show=show, venue=venue,
        desk=DESK, kind=kind, finding="G7:bus.iem.3", label=label,
        address="/bus/3/dyn/on", path="ae_data.bus.3.dyn.on", file_before=0,
        desk_before=0, written=1, readback=1, outcome=outcome, scene="bidv.snap",
        app="0.1.0")


@pytest.fixture
def page(qt_app, knowledge):
    from wing_parser.ui.log_page import LogPage

    return LogPage()


def test_an_empty_log_shows_the_empty_state(page):
    page.refresh()
    assert page.shows_list.count() == 0
    assert not page.empty_label.isHidden()
    assert page.export_button.isEnabled() is False


def test_the_page_lists_shows_newest_first_with_counts(page, knowledge):
    writelog.append(_entry("AZ-1", ts="2026-10-01T10:00:00.000+07:00"), knowledge)
    writelog.append(_entry("AZ-2", ts="2026-10-20T10:00:00.000+07:00"), knowledge)
    writelog.append(_entry("AZ-2", ts="2026-10-20T11:00:00.000+07:00",
                           outcome="clamped"), knowledge)
    page.refresh()

    assert page.shows_list.count() == 2
    first = page.shows_list.item(0).text()
    assert "AZ-2" in first and "BIDV Gala" in first and "GEM Center" in first
    assert "2 writes" in first
    assert page.empty_label.isHidden()


def test_choosing_a_show_fills_the_entries_table_in_time_order(page, knowledge):
    writelog.append(_entry(ts="2026-10-20T13:10:00.000+07:00", label="second"), knowledge)
    writelog.append(_entry(ts="2026-10-20T13:05:00.000+07:00", label="first"), knowledge)
    page.refresh()
    page.shows_list.setCurrentRow(0)

    model = page.entries_model
    assert model.rowCount() == 2
    labels = [model.item(row, 3).text() for row in range(2)]
    assert labels == ["first", "second"]
    assert model.item(0, 1).text() == "WING-GIAQUY"
    assert model.item(0, 9).text() == "✓ sent"
    assert model.columnCount() == 11


def test_the_newest_show_is_selected_by_default(page, knowledge):
    writelog.append(_entry("AZ-1", ts="2026-10-01T10:00:00.000+07:00"), knowledge)
    writelog.append(_entry("AZ-2", ts="2026-10-20T10:00:00.000+07:00"), knowledge)
    page.refresh()
    assert page.current_code() == "AZ-2"
    assert page.entries_model.rowCount() == 1
    assert page.export_button.isEnabled() is True


def test_the_page_re_reads_the_folder_each_time_it_is_shown(page, knowledge):
    page.refresh()
    assert page.shows_list.count() == 0
    writelog.append(_entry(), knowledge)
    page.show()
    assert page.shows_list.count() == 1


def test_export_writes_one_escaped_html_report_through_the_save_seam(
        page, knowledge, tmp_path, monkeypatch):
    from wing_parser.ui import log_page

    writelog.append(_entry(show="<script>alert(1)</script>"), knowledge)
    page.refresh()
    page.shows_list.setCurrentRow(0)
    target = tmp_path / "out" / "r.html"
    target.parent.mkdir()
    asked = {}

    def chooser(parent, title, suggested, file_filter):
        asked["suggested"] = suggested
        return str(target)

    monkeypatch.setattr(log_page, "choose_save_path", chooser)
    page.export_button.click()

    assert asked["suggested"].endswith("AZ-1501-report.html")
    html = target.read_text(encoding="utf-8")
    assert "AZ-1501" in html and "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "Write report" in html
    assert str(target) in page.status_label.text()


def test_the_report_is_written_in_the_ui_language(page, knowledge, tmp_path, monkeypatch):
    from wing_parser.ui import log_page, texts

    writelog.append(_entry(), knowledge)
    page.refresh()
    page.shows_list.setCurrentRow(0)
    target = tmp_path / "vi.html"
    monkeypatch.setattr(log_page, "choose_save_path", lambda *a: str(target))
    texts.set_language("vi")
    page.export_button.click()

    assert "Báo cáo ghi xuống desk" in target.read_text(encoding="utf-8")


def test_cancelling_the_save_dialog_writes_nothing(page, knowledge, tmp_path, monkeypatch):
    from wing_parser.ui import log_page

    writelog.append(_entry(), knowledge)
    page.refresh()
    page.shows_list.setCurrentRow(0)
    monkeypatch.setattr(log_page, "choose_save_path", lambda *a: "")
    page.export_button.click()
    assert page.status_label.text() == ""


def test_a_failed_export_is_said_not_raised(page, knowledge, tmp_path, monkeypatch):
    from wing_parser.ui import log_page

    writelog.append(_entry(), knowledge)
    page.refresh()
    page.shows_list.setCurrentRow(0)
    monkeypatch.setattr(log_page, "choose_save_path",
                        lambda *a: str(tmp_path / "no-such-dir" / "r.html"))
    page.export_button.click()
    assert page.status_label.text() != ""


def test_open_log_folder_goes_through_a_seam_and_creates_the_folder(
        page, knowledge, monkeypatch):
    from wing_parser.ui import log_page

    opened = []
    monkeypatch.setattr(log_page, "open_folder", opened.append)
    page.folder_button.click()
    assert opened == [writelog.log_dir()]
    assert writelog.log_dir().is_dir()


def test_skipped_lines_raise_a_warning(page, knowledge):
    writelog.append(_entry(), knowledge)
    path = writelog.log_dir(knowledge) / "AZ-1501.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write("{not json\n")
    with pytest.warns(UserWarning):
        page.refresh()                      # selects the newest show
    assert "1" in page.warning_label.text()
    assert not page.warning_label.isHidden()


@pytest.mark.parametrize("field,value", [("desk", "WING"), ("ts", 1)])
def test_a_wrongly_typed_line_is_skipped_not_fatal(page, knowledge, field, value):
    import json

    writelog.append(_entry(), knowledge)
    path = writelog.log_dir(knowledge) / "AZ-1501.jsonl"
    bad = _entry().to_json()
    bad[field] = value
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(bad) + chr(10))
    with pytest.warns(UserWarning):
        page.refresh()
    assert page.entries_model.rowCount() == 1
    assert "1" in page.warning_label.text()
    assert not page.warning_label.isHidden()


def test_a_sink_failure_shows_on_the_page(qt_app, page):
    from wing_parser.ui.write_log_sink import WriteLogSink

    sink = WriteLogSink(window=None)
    page.attach_sink(sink)
    sink.warning = "disk on fire"
    sink.warning_changed.emit(sink.warning)
    assert page.warning_label.text() == "disk on fire"
    assert not page.warning_label.isHidden()


def test_a_warning_that_already_exists_is_shown_on_attach(qt_app, page):
    from wing_parser.ui.write_log_sink import WriteLogSink

    sink = WriteLogSink(window=None)
    sink.warning = "earlier failure"
    page.attach_sink(sink)
    assert page.warning_label.text() == "earlier failure"


def test_refresh_keeps_the_chosen_show(page, knowledge):
    writelog.append(_entry("AZ-1", ts="2026-10-01T10:00:00.000+07:00"), knowledge)
    writelog.append(_entry("AZ-2", ts="2026-10-20T10:00:00.000+07:00"), knowledge)
    page.refresh()
    page.shows_list.setCurrentRow(1)
    chosen = page.shows_list.currentItem().data(0x0100)       # Qt.UserRole
    page.refresh()
    assert page.shows_list.currentItem().data(0x0100) == chosen


def test_refresh_loads_the_chosen_show_once(page, knowledge, monkeypatch):
    writelog.append(_entry("AZ-1", ts="2026-10-01T10:00:00.000+07:00"), knowledge)
    writelog.append(_entry("AZ-2", ts="2026-10-20T10:00:00.000+07:00"), knowledge)
    page.refresh()
    loads = []
    original = page._load
    monkeypatch.setattr(page, "_load", lambda code: (loads.append(code), original(code)))
    page.refresh()                                  # keeps the chosen show
    assert loads == ["AZ-2"]
    loads.clear()
    page.shows_list.setCurrentRow(1)                # the user's click still loads
    assert loads == ["AZ-1"]


# -- the window: eighth page, Ctrl+8, Tab order ----------------------------


@pytest.fixture
def window(qt_app, monkeypatch, knowledge):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.main_window import MainWindow

    return MainWindow(None)


def test_the_log_is_the_eighth_page(window):
    from wing_parser.ui.main_window import PAGE_ORDER

    assert PAGE_ORDER[-1] == "log" and len(PAGE_ORDER) == 8
    assert window.sidebar.count() == 8
    assert window.sidebar.item(7).text() == "LOG"


def test_ctrl_8_switches_to_the_log_page(window):
    from PySide6.QtGui import QShortcut

    shortcut = next(s for s in window.findChildren(QShortcut)
                    if s.key().toString() == "Ctrl+8")
    shortcut.activated.emit()
    assert window.stack.currentWidget() is window.pages["log"]


def test_the_window_wires_the_sink_to_the_log_page(window):
    assert window.pages["log"]._sink is window.write_log_sink


def test_tab_order_stays_inside_the_log_page(window):
    from wing_parser.ui.main_window import _tab_stops

    page = window.pages["log"]
    stops = _tab_stops(page)
    assert len(stops) >= 4
    walk, current = [], stops[0]
    for _ in range(500):
        walk.append(current)
        current = current.nextInFocusChain()
        if current is None:
            break
    position = {id(node): index for index, node in enumerate(walk)}
    assert all(id(s) in position for s in stops)
    order = [position[id(s)] for s in stops]
    assert order == sorted(order)
    segment = walk[order[0]:order[-1] + 1]
    assert not [n for n in segment if n is not page and not page.isAncestorOf(n)]
