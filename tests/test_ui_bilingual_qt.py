"""Window-level bilingual behaviour: the real MainWindow in each language,
the Settings dialog (language row, real Test connection path), and the
strings that used to be literals inside widgets."""

import json

import pytest

pytest.importorskip("PySide6.QtWidgets")

from wing_parser.ui import state_store, texts


@pytest.fixture
def language():
    """Set the UI language; conftest's autouse fixture resets it after."""
    return texts.set_language


@pytest.fixture
def knowledge(qt_app, monkeypatch, tmp_path):
    """A private knowledge dir: ui-state.json is written here, not shared."""
    from wing_parser import config

    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    monkeypatch.setattr(config, "knowledge_dir", lambda override=None: tmp_path)
    return tmp_path


def _window():
    from wing_parser.ui.main_window import MainWindow

    return MainWindow(None)


def _expect(table: dict, window) -> None:
    from wing_parser.ui.main_window import PAGE_ORDER

    labels = [window.sidebar.item(i).text() for i in range(len(PAGE_ORDER))]
    assert labels == [table[f"page.{k.removesuffix('_')}"].upper()
                      for k in PAGE_ORDER]
    titles = [action.text() for action in window.menuBar().actions()]
    assert titles == [table[f"menu.{m}"] for m in
                      ("file", "edit", "tools", "help")]
    assert window.pages["diff"].compare_button.text() == table["diff.compare"]
    assert (window.pages["import_"].pick_step.choose_button.text()
            == table["import.pick"])


def test_the_window_builds_in_vietnamese(knowledge, language):
    language("vi")
    _expect(texts.VI, _window())
    # Guard against a vacuous pass: the two languages really differ here.
    assert texts.VI["menu.tools"] != texts.TEXTS["menu.tools"]
    assert texts.VI["diff.compare"] != texts.TEXTS["diff.compare"]


def test_the_window_builds_in_english(knowledge, language):
    language("en")
    _expect(texts.TEXTS, _window())


def test_the_scene_filter_is_read_when_the_dialog_opens(
        knowledge, language, monkeypatch):
    """The FILTER constants used to be frozen at import time."""
    from PySide6.QtWidgets import QFileDialog

    seen = []
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName",
        staticmethod(lambda *a, **k: seen.append(a[3]) or ("", "")))
    language("vi")
    _window().open_file()
    assert seen == [texts.VI["menu.scene_filter"]]


# -- Settings > Language -------------------------------------------------


def _language_row(window=None):
    from PySide6.QtWidgets import QComboBox, QLabel

    from wing_parser.ui.settings_dialog import SettingsDialog

    dialog = SettingsDialog(window)
    combo = dialog.findChild(QComboBox, "language_combo")
    note = dialog.findChild(QLabel, "language_note")
    hint = dialog.findChild(QLabel, "language_run_hint")
    return dialog, combo, note, hint


def test_the_language_row_starts_on_the_saved_language(knowledge):
    state_store.save_language(knowledge, "vi")
    _dialog, combo, note, _hint = _language_row()
    assert combo.currentData() == "vi"
    assert combo.currentText() == texts.TEXTS["lang.vi"]
    assert note.isHidden()


def test_choosing_vietnamese_saves_it_and_shows_the_restart_note(knowledge):
    state_store.save(knowledge, {
        "geometry": "aabbcc", "page": "diff", "recent": ["x.snap"],
        "consoles": ["10.0.0.5"], "apply_delay": 12,
    })
    dialog, combo, note, _hint = _language_row()
    assert combo.currentData() == "en"
    combo.setCurrentIndex(combo.findData("vi"))
    saved = json.loads((knowledge / state_store.STATE_FILE)
                       .read_text(encoding="utf-8"))
    assert saved == {
        "geometry": "aabbcc", "page": "diff", "recent": ["x.snap"],
        "consoles": ["10.0.0.5"], "apply_delay": 12, "language": "vi",
    }
    dialog.show()
    assert note.isVisible()
    assert note.text() == texts.TEXTS["settings.language_note"]
    assert "Restart" in note.text()
    assert texts.VI["settings.language_note"].split("/")[1].strip() in note.text()


def test_closing_the_window_does_not_revert_the_language(knowledge):
    """`save_on_close` rewrites ui-state.json from the window's own copy
    of the state; the language is not part of that copy."""
    window = _window()
    _dialog, combo, _note, _hint = _language_row(window)
    combo.setCurrentIndex(combo.findData("vi"))
    window.close()
    assert state_store.load(knowledge)["language"] == "vi"


def test_a_failed_language_save_says_so_and_reverts_the_combo(
        knowledge, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    shown = []
    monkeypatch.setattr(
        QMessageBox, "critical",
        staticmethod(lambda parent, title, body: shown.append((title, body))))

    def broken(directory, code):
        raise OSError("disk is read-only")

    state_store.save_language(knowledge, "en")
    _dialog, combo, note, _hint = _language_row()
    monkeypatch.setattr(state_store, "save_language", broken)
    combo.setCurrentIndex(combo.findData("vi"))
    assert combo.currentData() == "en"
    assert note.isHidden()
    assert len(shown) == 1
    title, body = shown[0]
    assert title == texts.TEXTS["settings.title"]
    assert "disk is read-only" in body
    assert state_store.load(knowledge)["language"] == "en"


def test_a_one_off_run_language_is_named_next_to_the_saved_choice(
        knowledge, language):
    """`--lang vi` with "en" saved: the combo shows the saved choice, so
    the row must say what THIS run is showing."""
    state_store.save_language(knowledge, "en")
    language("vi")
    dialog, combo, _note, hint = _language_row()
    dialog.show()
    assert combo.currentData() == "en"
    assert hint.isVisible()
    assert texts.VI["lang.vi"] in hint.text()


def test_no_run_hint_when_this_run_matches_the_saved_language(
        knowledge, language):
    state_store.save_language(knowledge, "vi")
    language("vi")
    dialog, _combo, _note, hint = _language_row()
    dialog.show()
    assert not hint.isVisible()


# -- Settings > Test connection, through the REAL probe --------------------


class _Unauthorized(Exception):
    status_code = 401


@pytest.fixture
def real_probe(knowledge, monkeypatch):
    """A Settings dialog on the REAL default probe (`settings_probe`),
    with only the provider constructor faked -- so the failure travels
    ping_raw -> classify -> ai_message -> the dialog's own status line."""
    from wing_parser.classifier import provider

    monkeypatch.delenv("WING_DISABLE_LLM", raising=False)
    (knowledge / "provider.yaml").write_text(
        "provider: anthropic\n", encoding="utf-8")
    # `save()` pins this env var for the process; make the teardown undo it.
    monkeypatch.setenv(provider.ENV_VAR, str(knowledge / "provider.yaml"))
    return provider


def _run_real_probe(settle, expected: str):
    from wing_parser.ui.settings_dialog import SettingsDialog

    dialog = SettingsDialog()
    assert dialog.run_probe()
    assert settle(lambda: expected in dialog.status_label.text()), (
        dialog.status_label.text())
    return dialog


def _refuse(cfg):
    raise _Unauthorized("nope")


def test_test_connection_shows_a_rejected_key_in_vietnamese(
        real_probe, language, settle, monkeypatch):
    monkeypatch.setattr(real_probe, "make_provider", _refuse)
    language("vi")
    dialog = _run_real_probe(settle, texts.VI["ai_error.bad_key"])
    assert dialog.status_label.text() == texts.VI["settings.probe_fail"].format(
        message=texts.VI["ai_error.bad_key"])


def test_test_connection_keeps_english_wording_in_english(
        real_probe, settle, monkeypatch):
    from wing_parser.classifier import provider_errors

    monkeypatch.setattr(real_probe, "make_provider", _refuse)
    _run_real_probe(settle, provider_errors._MESSAGES[provider_errors.BAD_KEY])


def test_test_connection_reports_success_in_vietnamese(
        real_probe, language, settle, monkeypatch):
    from wing_parser import config

    monkeypatch.setattr(real_probe, "make_provider", lambda cfg: object())
    monkeypatch.setattr(real_probe, "complete_json",
                        lambda *args, **kwargs: {"ok": "ok"})
    language("vi")
    dialog = _run_real_probe(settle, "đã phản hồi")
    name = real_probe.resolve_config(config.knowledge_dir()).name
    assert dialog.status_label.text() == texts.VI["settings.probe_ok"].format(
        message=texts.VI["settings.probe_replied"].format(name=name))


def test_the_cli_ping_is_unchanged_and_still_english(monkeypatch):
    """`ping` wraps `ping_raw`: same (ok, English message) contract."""
    from wing_parser.classifier import provider, provider_errors

    monkeypatch.setattr(provider, "make_provider", _refuse)
    texts.set_language("vi")
    assert provider.ping(provider.ProviderConfig()) == (
        False, provider_errors._MESSAGES[provider_errors.BAD_KEY])


# -- a Vietnamese Settings dialog ------------------------------------------


def test_the_settings_dialog_labels_are_vietnamese(knowledge, language):
    from PySide6.QtWidgets import QLabel

    from wing_parser.ui.settings_dialog import SettingsDialog

    language("vi")
    dialog = SettingsDialog()
    labels = {label.text() for label in dialog.findChildren(QLabel)}
    for key in ("settings.language", "settings.apply_delay",
                "settings.api_key_env"):
        assert texts.VI[key] in labels, key
        assert texts.TEXTS[key] not in labels, key
    assert dialog.windowTitle() == texts.VI["settings.title"]
    assert dialog.test_button.text() == texts.VI["settings.test"]


# -- strings that used to be literals inside widgets -----------------------


def test_the_verdict_buttons_are_vietnamese(qt_app, language):
    from wing_parser.advisory import feedback
    from wing_parser.ui.verdict_bar import VerdictBar

    language("vi")
    bar = VerdictBar()
    assert {v: b.text() for v, b in bar.buttons.items()} == {
        "correct": texts.VI["verdict.correct"],
        "false-positive": texts.VI["verdict.false_positive"],
        "irrelevant": texts.VI["verdict.irrelevant"],
    }
    assert set(bar.buttons) == set(feedback.VERDICTS)


def test_the_findings_table_headers_follow_the_language(language):
    from PySide6.QtCore import Qt

    from wing_parser.ui.findings_model import COLUMNS, FindingsModel

    model = FindingsModel()
    for code, table in (("en", texts.TEXTS), ("vi", texts.VI)):
        language(code)
        headers = [model.headerData(i, Qt.Orientation.Horizontal)
                   for i in range(len(COLUMNS))]
        assert headers == [table[f"findings.col.{key}"] for key in COLUMNS]


def test_the_detail_panel_box_titles_are_vietnamese(qt_app, language):
    from PySide6.QtWidgets import QGroupBox

    from wing_parser.ui.detail_panel import DetailPanel

    language("vi")
    panel = DetailPanel()
    titles = {box.title() for box in panel.findChildren(QGroupBox)}
    assert titles == {texts.VI["detail.why"], texts.VI["detail.source"],
                      texts.VI["detail.evidence"]}
