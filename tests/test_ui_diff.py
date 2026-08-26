"""The Diff page: comparing the live scene against another file."""

import json

import pytest

pytest.importorskip("PySide6.QtWidgets")

from wing_parser.ui.diff_page import DiffPage  # noqa: E402
from wing_parser.ui.session import Session  # noqa: E402


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
    page = DiffPage()
    page.set_session(Session.open(vu_path))
    page.compare_with(str(other_snap))       # public seam for the dialog
    assert page.model.rowCount() >= 1


def test_bad_other_file_is_an_error_not_a_crash(qt_app, vu_path, tmp_path,
                                                monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    page = DiffPage()
    page.set_session(Session.open(vu_path))
    bad = tmp_path / "bad.snap"
    bad.write_text("not json", encoding="utf-8")
    page.compare_with(str(bad))              # must not raise
    assert page.model.rowCount() == 0
    assert page.error_label.text() != ""


def test_seeded_other_gives_the_ab_capture_rows_to_bar(vu_path, tmp_path,
                                                       monkeypatch):
    """The screenshot A/B pair is dead on an empty table, so the capture
    seeds a comparison: the live scene against a copy with every stored
    fader nudged. The seed must land in the directory the caller named
    and yield a non-empty diff."""
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.cli.diffcore import diff_rows
    from wing_parser import WingScene
    from wing_parser.ui.diff_page import seeded_other

    session = Session.open(vu_path)
    path = seeded_other(session, tmp_path)
    assert path.parent == tmp_path
    rows = diff_rows(session.scene, WingScene.load(path))
    assert len(rows) >= 1
    assert any(row.magnitude for row in rows)


def test_magnitude_rows_sort_first_largest_then_the_rest(qt_app, vu_path,
                                                         tmp_path,
                                                         monkeypatch):
    """Descending magnitude groups first; only then the None-magnitude rows.

    The magnitudes are chosen so descending order (ch.10 > ch.8 > ch.12)
    is NOT natural path order (ch.2 < ch.8 < ch.10 < ch.12) — a sort by
    path alone, or by magnitude without grouping, fails this sequence.
    """
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"]["8"]["fdr"] = -20.0   # magnitude 12.1
    doc["ae_data"]["ch"]["10"]["fdr"] = -30.0  # magnitude 27.4
    doc["ae_data"]["ch"]["12"]["fdr"] = -0.5   # magnitude 0.9
    doc["ae_data"]["ch"]["2"]["mute"] = True   # boolean: magnitude is None
    out = tmp_path / "mixed.snap"
    out.write_text(json.dumps(doc), encoding="utf-8")

    page = DiffPage()
    page.set_session(Session.open(vu_path))
    page.compare_with(str(out))
    paths = [page.model.item(row, 0).text()
             for row in range(page.model.rowCount())]
    assert paths == [
        "ch.10.fader_dB",
        "ch.8.fader_dB",
        "ch.12.fader_dB",
        "ch.2.muted",
    ]
