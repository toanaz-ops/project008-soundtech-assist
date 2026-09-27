"""Spec §5, F6: three sources, read-only, Skip leaves the file unchanged."""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtGui import QColor

from wing_parser import WingScene
from wing_parser.classifier.matcher import HIGH
from wing_parser.showcontext.ingest.build import BuildResult, BuiltSegment
from wing_parser.showcontext.models import Segment
from wing_parser.showcontext.view import channels_of
from wing_parser.ui import import_controller as ic_module
from wing_parser.ui import scene_step as scene_step_module
from wing_parser.ui.import_page import ImportPage
from wing_parser.ui.main_window import MainWindow
from wing_parser.ui.scene_step import SceneStep
from wing_parser.ui.session import Session
from wing_parser.ui.theme import tokens

BIDV = "tests/data/BIDV TPHCM - KỊCH BẢN SK YEP 2025..xlsx"


def _result(kinds):
    return BuildResult(
        segments=(BuiltSegment(segment=Segment(id="S1", title="t", expects=kinds), comments=()),),
        loose_comments=(), data_rows=1, comment_rows=0, blank_rows=0,
    )


def _confident_kind(scene) -> str:
    return next(c.source_type.kind for c in scene.channels()
                if c.source_type.confidence >= HIGH)


def _found_text(scene, kind: str) -> str:
    """The exact string _populate_table builds for one found kind: number
    + name over channels_of(scene, kind) -- the same fields and the same
    walk propose.for_segments uses (propose.py:46-49)."""
    return ", ".join(f"{c.data.number} {c.data.name}" for c in channels_of(scene, kind))


@pytest.fixture
def step(qt_app):
    return SceneStep(doctor_scene_provider=lambda: None)


def test_with_no_scene_at_all_the_status_line_says_so(step):
    step.set_result(_result(("speech.mc",)))
    assert step.status_label.text() != ""
    assert step.table.rowCount() == 0
    assert not step.continue_button.isEnabled()


def test_doctors_scene_populates_the_table_with_channel_number_and_name(qt_app, vu_path):
    scene = WingScene.load(vu_path)
    kind = _confident_kind(scene)
    step = SceneStep(doctor_scene_provider=lambda: scene)
    step.set_result(_result((kind,)))
    assert step.table.rowCount() == 1
    # number + name, not the kind (spec §5 gap 1)
    assert step.table.item(0, 2).text() == _found_text(scene, kind)
    assert kind not in step.table.item(0, 2).text()
    assert step.table.item(0, 3).text() == ""            # nothing missing
    assert step.continue_button.isEnabled()


def test_a_missing_kind_is_shown_in_the_warn_colour(qt_app, vu_path):
    scene = WingScene.load(vu_path)
    step = SceneStep(doctor_scene_provider=lambda: scene)
    step.set_result(_result(("instrument.theremin",)))
    missing_item = step.table.item(0, 3)
    assert missing_item.text() == "instrument.theremin"
    assert missing_item.foreground().color() == QColor(tokens.COLOURS["warn"])


def test_every_segment_gets_a_row_even_one_with_no_expects(qt_app, vu_path):
    scene = WingScene.load(vu_path)
    result = BuildResult(
        segments=(
            BuiltSegment(segment=Segment(id="S1", title="t", expects=()), comments=()),
            BuiltSegment(segment=Segment(id="S2", title="t2",
                         expects=("instrument.theremin",)), comments=()),
        ),
        loose_comments=(), data_rows=2, comment_rows=0, blank_rows=0,
    )
    step = SceneStep(doctor_scene_provider=lambda: scene)
    step.set_result(result)
    assert step.table.rowCount() == 2
    assert step.table.item(0, 1).text() == ""
    assert step.table.item(0, 2).text() == ""
    assert step.table.item(0, 3).text() == ""


def test_selecting_pull_with_nothing_pulled_yet_says_so_and_the_item_is_disabled(step):
    step.set_result(_result(("speech.mc",)))
    pull_item = step.source_box.model().item(step.source_box.findData("pull"))
    assert not pull_item.isEnabled()
    step.source_box.setCurrentIndex(step.source_box.findData("pull"))
    assert "pulled" in step.status_label.text() or "Pull" in step.status_label.text()
    assert not step.continue_button.isEnabled()


def test_a_set_pulled_session_populates_the_table_and_enables_the_item(qt_app, vu_path):
    """Source 3 of 3 (F6): the Console's last Pull, faked as a Session-shaped
    stand-in carrying a real .scene -- set_pulled_session is the seam
    live_wiring wires ConsolePage.session_pulled to (Task 8)."""
    scene = WingScene.load(vu_path)
    kind = _confident_kind(scene)
    fake_session = type("FakeSession", (), {"scene": scene})()

    step = SceneStep(doctor_scene_provider=lambda: None)
    step.set_result(_result((kind,)))
    step.source_box.setCurrentIndex(step.source_box.findData("pull"))
    assert step.table.rowCount() == 0   # nothing pulled yet

    step.set_pulled_session(fake_session)
    assert step.source_box.model().item(step.source_box.findData("pull")).isEnabled()
    assert step.table.rowCount() == 1
    assert step.table.item(0, 2).text() == _found_text(scene, kind)


def test_opening_a_snap_file_populates_the_table(qt_app, vu_path, step):
    """Source 2 of 3 (F6): 'Open .snap…'. Sets the private `_file_scene`
    directly rather than driving the real `QFileDialog` -- `_open_file`
    itself is a few lines wrapping that dialog and a `WingScene.load`
    call already covered by `net`/`WingScene`'s own tests; what this test
    proves is that once a file scene is present, `_refresh_table` reads
    it exactly like the other two sources."""
    scene = WingScene.load(vu_path)
    kind = _confident_kind(scene)
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
    assert step.table.item(0, 2).text() == _found_text(scene, kind)


# -- fix round 1, item 3: preselecting the source on every set_result -----


def test_preselect_picks_doctor_when_it_has_a_scene_even_if_others_do_too(qt_app, vu_path):
    scene = WingScene.load(vu_path)
    fake_session = type("FakeSession", (), {"scene": scene})()
    step = SceneStep(doctor_scene_provider=lambda: scene)
    step.set_pulled_session(fake_session)
    step._file_scene = scene
    step.set_result(_result(("speech.mc",)))
    assert step.source_box.currentData() == "doctor"


def test_preselect_falls_back_to_pull_when_doctor_has_none(qt_app, vu_path):
    scene = WingScene.load(vu_path)
    fake_session = type("FakeSession", (), {"scene": scene})()
    step = SceneStep(doctor_scene_provider=lambda: None)
    step.set_pulled_session(fake_session)   # enables + would win over file
    step._file_scene = scene
    step.set_result(_result(("speech.mc",)))
    assert step.source_box.currentData() == "pull"


def test_preselect_falls_back_to_file_when_doctor_and_pull_have_none(qt_app, vu_path, step):
    scene = WingScene.load(vu_path)
    step._file_scene = scene
    step.set_result(_result(("speech.mc",)))
    assert step.source_box.currentData() == "file"


def test_preselect_defaults_to_doctor_when_nothing_has_a_scene(step):
    step.set_result(_result(("speech.mc",)))
    assert step.source_box.currentData() == "doctor"


# -- fix round 1, minors: file-load failure handling -----------------------


def test_a_snap_that_fails_to_load_names_the_file_and_the_step_stays_usable(
        step, monkeypatch, tmp_path, vu_path):
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
    assert step.table.rowCount() == 0
    assert not step.continue_button.isEnabled()

    # "stays usable" means something real: a subsequent successful open
    # still works, not just that no exception was raised.
    monkeypatch.setattr(
        scene_step_module.QFileDialog, "getOpenFileName",
        lambda *a, **k: (str(vu_path), ""))
    step._open_file()

    assert step._file_scene is not None
    assert step.table.rowCount() == 1
    assert step.continue_button.isEnabled()


def test_a_failed_load_after_an_earlier_success_clears_the_old_file(
        step, monkeypatch, tmp_path, vu_path):
    scene = WingScene.load(vu_path)
    kind = _confident_kind(scene)
    step.set_result(_result((kind,)))
    step.source_box.setCurrentIndex(step.source_box.findData("file"))

    monkeypatch.setattr(scene_step_module.QFileDialog, "getOpenFileName",
                        lambda *a, **k: (str(vu_path), ""))
    step._open_file()
    assert step.table.rowCount() == 1

    bad = tmp_path / "broken.snap"
    bad.write_text("not json", encoding="utf-8")
    monkeypatch.setattr(scene_step_module.QFileDialog, "getOpenFileName",
                        lambda *a, **k: (str(bad), ""))
    step._open_file()

    assert step._file_scene is None
    assert step.table.rowCount() == 0


def test_a_snap_that_fails_to_load_does_not_name_the_file_twice(
        step, monkeypatch, tmp_path):
    """parse_raw's own ValueError already starts with the path
    (loader.py); the status line must not prefix it a second time."""
    bad = tmp_path / "not_a_snap.snap"
    bad.write_text('{"nope": true}', encoding="utf-8")   # valid JSON, not a snapshot

    monkeypatch.setattr(
        scene_step_module.QFileDialog, "getOpenFileName",
        lambda *a, **k: (str(bad), ""))
    step.set_result(_result(("speech.mc",)))
    step.source_box.setCurrentIndex(step.source_box.findData("file"))

    step._open_file()

    assert step.status_label.text().count(str(bad)) == 1


def test_a_forward_slash_dialog_path_is_not_named_twice(step, monkeypatch, tmp_path):
    """M8: QFileDialog can hand back a forward-slash path on Windows
    (`path.as_posix()`); the loader's own error message names the file
    with a native (backslash) Path string. Comparing the two without
    normalising both sides names the file twice -- once per spelling."""
    bad = tmp_path / "not_a_snap.snap"
    bad.write_text('{"nope": true}', encoding="utf-8")
    posix_path = bad.as_posix()

    monkeypatch.setattr(
        scene_step_module.QFileDialog, "getOpenFileName",
        lambda *a, **k: (posix_path, ""))
    step.set_result(_result(("speech.mc",)))
    step.source_box.setCurrentIndex(step.source_box.findData("file"))

    step._open_file()

    text = step.status_label.text()
    assert posix_path not in text
    assert text.count(str(bad)) == 1


# -- Skip / Continue --------------------------------------------------------


def test_skip_emits_the_skip_signal_not_continue_and_clears_the_chosen_scene(step, qt_app, vu_path):
    step._doctor_scene_provider = lambda: WingScene.load(vu_path)
    seen = []
    step.skip_requested.connect(lambda: seen.append("skip"))
    step.continue_requested.connect(lambda scene: seen.append(("continue", scene)))
    step.set_result(_result(("speech.mc",)))
    step.skip_button.click()
    assert seen == ["skip"]
    assert step.chosen_scene is None


def test_continue_emits_and_remembers_the_currently_selected_scene(qt_app, vu_path):
    scene = WingScene.load(vu_path)
    step = SceneStep(doctor_scene_provider=lambda: scene)
    step.set_result(_result(("speech.mc",)))
    seen = []
    step.continue_requested.connect(lambda s: seen.append(s))
    step.continue_button.click()
    assert seen == [scene]
    assert step.chosen_scene is scene


# -- fix round 1, item 5: tests that can tell right from wrong -------------


def _seeded_page(monkeypatch, tmp_path, session, result):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    page = ImportPage()
    page.set_session(session)
    page.set_output_directory(tmp_path)
    page._xlsx = "fake.xlsx"
    page._result = result          # page._read/_resolved stay None, so
    return page                    # refresh_result is a no-op and keeps this


def test_continue_puts_the_scene_marker_in_both_preview_and_the_saved_file(
        monkeypatch, tmp_path, vu_path, qt_app):
    """Continue must thread scene= into finish_scene's ic.preview_text
    render; Save (I2) then writes exactly that rendered text, with no
    ic.preview_text call of its own. Seeds a synthetic result instead of
    relying on the BIDV workbook happening to match the fixture scene's
    classified kinds."""
    scene = WingScene.load(vu_path)
    kind = _confident_kind(scene)
    fake_session = type("FakeSession", (), {"scene": scene})()
    result = _result((kind,))

    page = _seeded_page(monkeypatch, tmp_path, fake_session, result)

    page.preview_button.click()
    assert page.step_area.currentIndex() == 3
    assert page.scene_step.source_box.currentData() == "doctor"

    page.scene_step.continue_button.click()
    assert page.step_area.currentIndex() == 4

    rendered = page.preview_pane.toPlainText()
    assert "--scene:" in rendered      # emit.render's own marker text

    out = tmp_path / "out.yaml"
    assert page.save_as(str(out))
    saved = out.read_text(encoding="utf-8")
    assert "--scene:" in saved
    assert saved == rendered


def test_skip_after_a_doctor_scene_is_loaded_still_renders_with_no_scene(
        monkeypatch, tmp_path, vu_path, qt_app):
    """Skip is the no-scene path even when a real scene IS loaded and
    selected: the output must equal ic.preview_text(xlsx, result) with no
    scene and carry no scene proposal."""
    scene = WingScene.load(vu_path)
    kind = _confident_kind(scene)
    fake_session = type("FakeSession", (), {"scene": scene})()
    result = _result((kind,))

    page = _seeded_page(monkeypatch, tmp_path, fake_session, result)

    page.preview_button.click()
    assert page.scene_step.source_box.currentData() == "doctor"   # a real scene IS loaded

    page.scene_step.skip_button.click()
    assert page.step_area.currentIndex() == 4

    expected = ic_module.preview_text(page._xlsx, result)   # no scene at all
    rendered = page.preview_pane.toPlainText()
    assert rendered == expected
    assert "--scene:" not in rendered

    out = tmp_path / "out.yaml"
    assert page.save_as(str(out))
    assert out.read_text(encoding="utf-8") == expected


# -- fix round 1, item 4: the MainWindow wiring, end to end -----------------


def test_pulling_on_the_console_page_feeds_the_import_scene_steps_pull_source(
        qt_app, vu_path):
    """W4: MainWindow wires ConsolePage.session_pulled straight to
    pages['import_'].scene_step.set_pulled_session (main_window.py) --
    proven through the real window, not only at the SceneStep unit level.
    Deleting that wiring line turns this test red (see task-8-report.md,
    Fix round 1, for the captured RED output)."""
    window = MainWindow(None)
    page = window.pages["import_"]
    page.scene_step.set_result(_result(()))
    page.scene_step.source_box.setCurrentIndex(
        page.scene_step.source_box.findData("pull"))
    assert page.scene_step.table.rowCount() == 0

    pulled = Session.open(vu_path)
    window.pages["console"].session_pulled.emit(pulled)

    assert page.scene_step.table.rowCount() == 1


# -- the broad wizard smoke test --------------------------------------------


def test_the_full_wizard_reaches_save_through_the_scene_step_with_a_real_scene(
        qt_app, tmp_path, monkeypatch, vu_path, settle):
    """End-to-end through the real MainWindow: pick a real workbook,
    finish mapping, skip Terms straight to Preview, choose 'Doctor's
    scene' (a real loaded Session), Continue, and Save renders
    byte-identically to what was just previewed."""
    from wing_parser import config
    from wing_parser.ui import import_page

    monkeypatch.setenv(config.ENV_VAR, str(tmp_path))
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    monkeypatch.setattr(import_page.ic, "unresolved", lambda result: ())

    window = MainWindow(Session.open(vu_path))
    window._refresh()   # fans window.session out to every page's set_session
    page = window.pages["import_"]
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

    out = tmp_path / "out.yaml"
    assert page.save_as(str(out))
    assert out.read_text(encoding="utf-8") == rendered
