"""Tools > Draft rule dry-run: picker, status, Run, summary and detail."""

import pytest

pytest.importorskip("PySide6.QtWidgets")

GOOD = "ToanAZ, voice note, 2026-11-09"
GATE = """
principles:
  - id: draft.gate_on
    severity: info
    source: "{source}"
    when:
      for_each: channel
      where:
        channel.gate.on: true
    message: "Gate on channel {{channel.number}}"
"""


def _draft(root, body, name="d.yaml"):
    folder = root / "drafts"
    folder.mkdir(exist_ok=True)
    (folder / name).write_text(body, encoding="utf-8")


def _dialog(root, scenes=()):
    from wing_parser.ui.draft_dry_run_dialog import DraftDryRunDialog

    return DraftDryRunDialog(None, scenes=scenes, directory=root)


def _cell(model, row, col):
    return model.item(row, col).text()


def test_no_drafts_shows_guidance_with_path(qt_app, tmp_path):
    dialog = _dialog(tmp_path)
    assert not dialog.guidance.isHidden()
    assert str(tmp_path / "drafts") in dialog.guidance.text()
    assert not dialog.open_folder.isHidden()
    assert not dialog.run_btn.isEnabled()


def test_run_fills_summary_and_filters_detail(qt_app, tmp_path, vu_path):
    from wing_parser import WingScene
    from wing_parser.advisory import draft_dry_run as dd

    _draft(tmp_path, GATE.format(source=GOOD))
    load = dd.load_draft(tmp_path / "drafts" / "d.yaml", tmp_path)
    delta = dd.dry_run(WingScene.load(vu_path), load.rules, tmp_path)
    assert delta.added
    dialog = _dialog(tmp_path, [vu_path, vu_path])
    assert dialog.scene_list.count() == 1  # de-duplicated
    assert "1 rule" in dialog.status.text()
    assert "Ready to copy" in dialog.status.text()
    assert dialog.run_btn.isEnabled()
    dialog.run()
    m = dialog.summary_model
    assert m.rowCount() == 1
    assert _cell(m, 0, 1) == str(delta.before)
    assert _cell(m, 0, 2) == str(delta.after)
    assert _cell(m, 0, 3) == "+" + str(len(delta.added))
    assert _cell(m, 0, 4) == "-0"
    assert dialog.detail_model.rowCount() == len(delta.added)
    assert dialog.no_change.isHidden()
    dialog.summary.selectRow(0)
    assert dialog.detail_model.rowCount() == len(delta.added)
    assert _cell(dialog.detail_model, 0, 1) == "+"


def test_selecting_a_summary_row_filters_detail(qt_app, tmp_path, vu_path):
    _draft(tmp_path, GATE.format(source=GOOD))
    dialog = _dialog(tmp_path, [vu_path, tmp_path / "missing.snap"])
    dialog.run()
    total = dialog.detail_model.rowCount()
    assert total > 0
    dialog.summary.selectRow(1)  # the failed scene has no findings
    assert dialog.detail_model.rowCount() == 0
    dialog.summary.selectRow(0)
    assert dialog.detail_model.rowCount() == total


def test_missing_scene_shows_error_row_others_still_run(qt_app, tmp_path, vu_path):
    _draft(tmp_path, GATE.format(source=GOOD))
    dialog = _dialog(tmp_path, [tmp_path / "missing.snap", vu_path])
    dialog.run()
    m = dialog.summary_model
    assert m.rowCount() == 2
    assert _cell(m, 0, 5) != ""
    assert _cell(m, 0, 1) == ""
    assert _cell(m, 1, 5) == "" and _cell(m, 1, 3).startswith("+")


def test_broken_yaml_shows_error_and_disables_run(qt_app, tmp_path, vu_path):
    _draft(tmp_path, "principles: [unterminated")
    dialog = _dialog(tmp_path, [vu_path])
    assert dialog.status.text()
    assert "Ready to copy" not in dialog.status.text()
    assert not dialog.run_btn.isEnabled()


def test_undated_source_shows_not_ready_blocker(qt_app, tmp_path, vu_path):
    _draft(tmp_path, GATE.format(source="ToanAZ voice note"))
    dialog = _dialog(tmp_path, [vu_path])
    assert "Not ready to copy into principles.yaml" in dialog.status.text()
    assert "draft.gate_on" in dialog.status.text()
    assert dialog.run_btn.isEnabled()


def test_draft_that_changes_nothing_says_so(qt_app, tmp_path, vu_path):
    body = (GATE.format(source=GOOD)
            + "    hardness: flexible\n    applies_when:\n"
            "        channel_count: 99999\n")
    _draft(tmp_path, body)
    dialog = _dialog(tmp_path, [vu_path])
    dialog.run()
    assert not dialog.no_change.isHidden()


def test_remove_scene_disables_run(qt_app, tmp_path, vu_path):
    _draft(tmp_path, GATE.format(source=GOOD))
    dialog = _dialog(tmp_path, [vu_path])
    dialog.scene_list.selectAll()
    dialog._remove()
    assert not dialog.run_btn.isEnabled()


def test_tools_menu_has_the_action(qt_app):
    from PySide6.QtGui import QAction

    from wing_parser.ui.main_window import MainWindow
    from wing_parser.ui.texts import text

    window = MainWindow(None)
    labels = [a.text() for a in window.findChildren(QAction)]
    assert text("menu.dryrun") in labels


def _prepare_promote(root):
    (root / "principles.yaml").write_text(
        "# h\nprinciples: []\n", encoding="utf-8")
    _draft(root, GATE.format(source=GOOD))


def _answer(monkeypatch, button):
    from PySide6.QtWidgets import QMessageBox

    for name in ("information", "warning"):
        monkeypatch.setattr(QMessageBox, name,
                            staticmethod(lambda *a, **k: None))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: button))


def test_promote_button_disabled_when_not_promotable(qt_app, tmp_path):
    _draft(tmp_path, GATE.format(source="ToanAZ no date"))
    dialog = _dialog(tmp_path)
    assert not dialog.promote_btn.isEnabled()
    assert dialog.run_btn.isEnabled() is False  # no scenes, unrelated gate


def test_promote_confirm_yes_writes_and_calls_back(qt_app, tmp_path,
                                                   monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    _prepare_promote(tmp_path)
    called = []
    from wing_parser.ui.draft_dry_run_dialog import DraftDryRunDialog

    dialog = DraftDryRunDialog(None, directory=tmp_path,
                               on_promoted=lambda: called.append(1))
    assert dialog.promote_btn.isEnabled()
    _answer(monkeypatch, QMessageBox.StandardButton.Yes)
    dialog.promote_btn.click()
    assert "draft.gate_on" in (tmp_path / "principles.yaml").read_text(
        encoding="utf-8")
    assert called == [1]
    assert dialog.combo.count() == 0
    assert not dialog.promote_btn.isEnabled()


def test_promote_cancel_changes_nothing(qt_app, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    _prepare_promote(tmp_path)
    called = []
    from wing_parser.ui.draft_dry_run_dialog import DraftDryRunDialog

    dialog = DraftDryRunDialog(None, directory=tmp_path,
                               on_promoted=lambda: called.append(1))
    before = (tmp_path / "principles.yaml").read_bytes()
    _answer(monkeypatch, QMessageBox.StandardButton.No)
    dialog.promote_btn.click()
    assert (tmp_path / "principles.yaml").read_bytes() == before
    assert called == []
    assert (tmp_path / "drafts" / "d.yaml").exists()


def test_promote_callback_error_is_shown_not_raised(qt_app, tmp_path,
                                                    monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    _prepare_promote(tmp_path)
    from wing_parser.ui.draft_dry_run_dialog import DraftDryRunDialog

    def bad():
        raise RuntimeError("reanalyse blew up")

    dialog = DraftDryRunDialog(None, directory=tmp_path, on_promoted=bad)
    _answer(monkeypatch, QMessageBox.StandardButton.Yes)
    shown = []
    monkeypatch.setattr(QMessageBox, "critical",
                        staticmethod(lambda *a, **k: shown.append(a)))
    dialog.promote_btn.click()
    assert shown and "reanalyse blew up" in shown[0][2]
    assert "draft.gate_on" in (tmp_path / "principles.yaml").read_text(
        encoding="utf-8")
