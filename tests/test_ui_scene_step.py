"""Spec §5, F6: three sources, read-only, Skip leaves the file unchanged."""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")

from wing_parser.showcontext.ingest.build import BuildResult, BuiltSegment
from wing_parser.showcontext.models import Segment


def _result(kinds):
    return BuildResult(
        segments=(BuiltSegment(segment=Segment(id="S1", title="t", expects=kinds), comments=()),),
        loose_comments=(), data_rows=1, comment_rows=0, blank_rows=0,
    )


@pytest.fixture
def step(qt_app):
    from wing_parser.ui.scene_step import SceneStep

    return SceneStep(doctor_scene_provider=lambda: None)


def test_with_no_scene_at_all_the_status_line_says_so(step):
    step.set_result(_result(("speech.mc",)))
    assert step.status_label.text() != ""
    assert step.table.rowCount() == 0


def test_doctors_scene_populates_the_table(qt_app, vu_path):
    from wing_parser import WingScene
    from wing_parser.showcontext.ingest.build import BuildResult, BuiltSegment
    from wing_parser.showcontext.models import Segment
    from wing_parser.showcontext.view import channels_of
    from wing_parser.ui.scene_step import SceneStep

    scene = WingScene.load(vu_path)
    kind = next(c.source_type.kind for c in scene.channels()
               if c.source_type.confidence >= 0.8)
    result = BuildResult(
        segments=(BuiltSegment(segment=Segment(id="S1", title="t", expects=(kind,)), comments=()),),
        loose_comments=(), data_rows=1, comment_rows=0, blank_rows=0,
    )
    step = SceneStep(doctor_scene_provider=lambda: scene)
    step.set_result(result)
    assert step.table.rowCount() == 1
    assert step.table.item(0, 2).text() == kind         # found, no gap
    assert step.table.item(0, 3).text() == ""            # nothing missing


def test_selecting_pull_with_nothing_pulled_yet_says_so(step):
    step.set_result(_result(("speech.mc",)))
    step.source_box.setCurrentIndex(step.source_box.findData("pull"))
    assert "pulled" in step.status_label.text() or "Pull" in step.status_label.text()


def test_a_set_pulled_session_populates_the_table_once_pull_is_selected(qt_app, vu_path):
    """Source 3 of 3 (F6): the Console's last Pull, faked as a Session-shaped
    stand-in carrying a real .scene -- set_pulled_session is the seam
    live_wiring wires ConsolePage.session_pulled to (Task 8)."""
    from wing_parser import WingScene
    from wing_parser.ui.scene_step import SceneStep

    scene = WingScene.load(vu_path)
    kind = next(c.source_type.kind for c in scene.channels()
               if c.source_type.confidence >= 0.8)
    fake_session = type("FakeSession", (), {"scene": scene})()

    step = SceneStep(doctor_scene_provider=lambda: None)
    step.set_result(_result((kind,)))
    step.source_box.setCurrentIndex(step.source_box.findData("pull"))
    assert step.table.rowCount() == 0   # nothing pulled yet

    step.set_pulled_session(fake_session)
    assert step.table.rowCount() == 1
    assert step.table.item(0, 2).text() == kind


def test_opening_a_snap_file_populates_the_table(qt_app, vu_path, step):
    """Source 2 of 3 (F6): 'Open .snap…'. Sets the private `_file_scene`
    directly rather than driving the real `QFileDialog` -- `_open_file`
    itself is three lines wrapping that dialog and a `WingScene.load`
    call already covered by `net`/`WingScene`'s own tests; what this test
    proves is that once a file scene is present, `_refresh_table` reads
    it exactly like the other two sources."""
    from wing_parser import WingScene

    scene = WingScene.load(vu_path)
    kind = next(c.source_type.kind for c in scene.channels()
               if c.source_type.confidence >= 0.8)
    step.set_result(_result((kind,)))
    step.source_box.setCurrentIndex(step.source_box.findData("file"))
    # isVisibleTo, not isVisible: `step` is a standalone top-level widget
    # in this test and is never shown on screen, so isVisible() would be
    # False regardless of the button's own state (established idiom in
    # this suite, e.g. test_ui_import_page.py's cancel_button check).
    assert step.open_file_button.isVisibleTo(step)

    step._file_scene = scene
    step._refresh_table()

    assert step.table.rowCount() == 1
    assert step.table.item(0, 2).text() == kind


def test_a_snap_that_fails_to_load_shows_an_error_naming_the_file(
        step, monkeypatch, tmp_path):
    """Controller requirement on top of the brief: a bad .snap must name
    the file it failed on, and the step must stay usable afterwards."""
    from wing_parser.ui import scene_step as scene_step_module

    bad = tmp_path / "broken.snap"
    bad.write_text("not json", encoding="utf-8")

    monkeypatch.setattr(
        scene_step_module.QFileDialog, "getOpenFileName",
        lambda *a, **k: (str(bad), ""))
    step.set_result(_result(("speech.mc",)))
    step.source_box.setCurrentIndex(step.source_box.findData("file"))

    step._open_file()

    assert str(bad) in step.status_label.text()
    assert step._file_scene is None
    # the step is still usable: switching source and back does not raise
    step.source_box.setCurrentIndex(step.source_box.findData("doctor"))
    step.source_box.setCurrentIndex(step.source_box.findData("file"))


def test_skip_emits_the_skip_signal_not_continue(step, qt_app):
    seen = []
    step.skip_requested.connect(lambda: seen.append("skip"))
    step.continue_requested.connect(lambda scene: seen.append(("continue", scene)))
    step.set_result(_result(("speech.mc",)))
    step.skip_button.click()
    assert seen == ["skip"]


def test_continue_emits_the_currently_selected_scenes_value(qt_app, vu_path):
    from wing_parser import WingScene
    from wing_parser.ui.scene_step import SceneStep

    scene = WingScene.load(vu_path)
    step = SceneStep(doctor_scene_provider=lambda: scene)
    step.set_result(_result(("speech.mc",)))
    seen = []
    step.continue_requested.connect(lambda s: seen.append(s))
    step.continue_button.click()
    assert seen == [scene]


def test_the_full_wizard_reaches_save_through_the_scene_step_with_a_real_scene(
        qt_app, tmp_path, monkeypatch, vu_path, settle):
    """End-to-end through the real MainWindow: pick a real workbook,
    finish mapping, skip Terms straight to Preview, choose 'Doctor's
    scene' (a real loaded Session), Continue, and the rendered YAML
    carries a --scene proposal exactly as the CLI's --scene does."""
    from wing_parser import config
    from wing_parser.ui import import_page
    from wing_parser.ui.main_window import MainWindow
    from wing_parser.ui.session import Session

    monkeypatch.setenv(config.ENV_VAR, str(tmp_path))
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    monkeypatch.setattr(import_page.ic, "unresolved", lambda result: ())

    window = MainWindow(Session.open(vu_path))
    window._refresh()   # fans window.session out to every page's set_session
    page = window.pages["import_"]
    BIDV = "tests/data/BIDV TPHCM - KỊCH BẢN SK YEP 2025..xlsx"
    page.pick_file(BIDV)
    assert settle(lambda: page.step_area.currentIndex() == 1)
    for field, letter in (("id", "A"), ("time", "B"), ("title", "E")):
        page.letter_edit(field).setText(letter)
    page.header_edit("performers").setText("Thực hiện")
    page.sheet_edit.setText("KB 8.1")
    page.header_row_spin.setValue(5)
    page.next_button.click()
    assert page.step_area.currentIndex() == 2

    page.preview_button.click()
    assert page.step_area.currentIndex() == 3
    assert page.scene_step.source_box.currentData() == "doctor"
    page.scene_step.continue_button.click()
    assert page.step_area.currentIndex() == 4
    rendered = page.preview_pane.toPlainText()
    assert rendered != ""

    # Controller requirement: Save must render byte-identically to what
    # Continue just previewed, scene proposals included -- not only the
    # Skip (scene=None) path tested elsewhere.
    out = tmp_path / "out.yaml"
    assert page.save_as(str(out))
    assert out.read_text(encoding="utf-8") == rendered
