"""The Diff page: comparing the live scene against another file."""

import json

import pytest

pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture
def other_snap(vu_path, tmp_path):
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"]["8"]["fdr"] = -13.0
    out = tmp_path / "other.snap"
    out.write_text(json.dumps(doc), encoding="utf-8")
    return out


def test_comparing_two_files_lists_changes(qt_app, vu_path, other_snap,
                                           monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.diff_page import DiffPage
    from wing_parser.ui.session import Session

    page = DiffPage()
    page.set_session(Session.open(vu_path))
    page.compare_with(str(other_snap))       # public seam for the dialog
    assert page.model.rowCount() >= 1


def test_bad_other_file_is_an_error_not_a_crash(qt_app, vu_path, tmp_path,
                                                monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.diff_page import DiffPage
    from wing_parser.ui.session import Session

    page = DiffPage()
    page.set_session(Session.open(vu_path))
    bad = tmp_path / "bad.snap"
    bad.write_text("not json", encoding="utf-8")
    page.compare_with(str(bad))              # must not raise
    assert page.model.rowCount() == 0
    assert page.error_label.text() != ""


def test_magnitude_rows_sort_first_largest_first(qt_app, vu_path, tmp_path,
                                                 monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.diff_page import DiffPage
    from wing_parser.ui.session import Session

    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"]["8"]["fdr"] = -13.0   # numeric: has a magnitude
    doc["ae_data"]["ch"]["2"]["mute"] = True   # boolean: magnitude is None
    out = tmp_path / "mixed.snap"
    out.write_text(json.dumps(doc), encoding="utf-8")

    page = DiffPage()
    page.set_session(Session.open(vu_path))
    page.compare_with(str(out))
    texts = [page.model.item(row, 3).text()
             for row in range(page.model.rowCount())]
    magnitudes = [float(value) for value in texts if value]
    assert magnitudes == sorted(magnitudes, reverse=True)
    first_empty = texts.index("")
    assert all(value for value in texts[:first_empty])
