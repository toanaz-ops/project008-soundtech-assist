import os
import threading

import pytest

pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture
def knowledge(tmp_path, monkeypatch):
    from wing_parser import config

    monkeypatch.setenv(config.ENV_VAR, str(tmp_path))
    # load_config(None) falls back to ./provider.yaml relative to cwd;
    # chdir out of the repo so a real checkout's git-ignored key file
    # (or a malformed one) can never leak into these tests.
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_save_writes_yaml_and_pins_env(qt_app, knowledge, monkeypatch):
    from wing_parser.ui.settings_dialog import SettingsDialog

    dlg = SettingsDialog()
    dlg.fill(name="openai-compat", model="deepseek-chat",
             base_url="https://api.deepseek.com", api_key="sk-test-1234")
    dlg.save()
    text = (knowledge / "provider.yaml").read_text(encoding="utf-8")
    assert "api_key: sk-test-1234" in text
    assert os.environ["WING_PROVIDER_CONFIG"] == str(knowledge / "provider.yaml")


def test_probe_failure_is_reported_not_raised(qt_app, knowledge, settle):
    from wing_parser.ui.settings_dialog import SettingsDialog

    def bad_probe(config):
        raise RuntimeError("no network here")

    dlg = SettingsDialog(probe=bad_probe)
    assert dlg.run_probe()                   # starts; raises nothing here
    assert settle(lambda: "no network here" in dlg.status_label.text())
    assert "no network here" in dlg.status_label.text()
    assert dlg.test_button.isEnabled()


def test_a_working_probe_reports_ok(qt_app, knowledge, settle):
    from wing_parser.ui.settings_dialog import SettingsDialog

    dlg = SettingsDialog(
        probe=lambda cfg: (True, f"{cfg.name} replied"))
    assert dlg.run_probe()
    assert settle(lambda: "replied" in dlg.status_label.text())
    assert "Connection OK" in dlg.status_label.text()


def test_a_stuck_probe_times_out_naming_the_seconds(qt_app, knowledge,
                                                    monkeypatch, settle):
    from wing_parser.ui import workers
    from wing_parser.ui.settings_dialog import SettingsDialog

    gate = threading.Event()

    def stuck(cfg):
        gate.wait(timeout=5.0)

    monkeypatch.setitem(workers.TIMEOUTS, "probe", 0)
    dlg = SettingsDialog(probe=stuck)
    assert dlg.run_probe()
    try:
        assert settle(lambda: "No reply within 0 s" in dlg.status_label.text())
        assert dlg.test_button.isEnabled()
    finally:
        gate.set()


def test_cancelling_a_probe_restores_the_dialog_and_allows_retry(
        qt_app, knowledge, monkeypatch, settle):
    from wing_parser.ui.settings_dialog import SettingsDialog

    gate = threading.Event()
    started = threading.Event()

    def slow_ok(cfg):
        started.set()
        gate.wait(timeout=5.0)
        return True, "late"

    dlg = SettingsDialog(probe=slow_ok)
    assert dlg.run_probe()
    assert settle(lambda: started.is_set())
    dlg.cancel_button.click()                # settles without waiting
    assert dlg.test_button.isEnabled()
    assert not dlg.cancel_button.isVisibleTo(dlg)
    assert "cancelled" in dlg.status_label.text().lower()

    dlg._probe = lambda cfg: (True, "fast")
    assert dlg.run_probe()
    assert settle(lambda: "fast" in dlg.status_label.text())
    gate.set()


def test_existing_config_loads_masked(qt_app, knowledge):
    from wing_parser.ui.settings_dialog import SettingsDialog

    (knowledge / "provider.yaml").write_text(
        "provider: anthropic\nmodel: claude-opus-5\napi_key: sk-secret-abcd\n",
        encoding="utf-8",
    )
    dlg = SettingsDialog()
    assert "abcd" in dlg.key_display.text() and "secret" not in dlg.key_display.text()


def test_cancel_uses_its_own_texts_key(qt_app, knowledge):
    """docs/tech-debt.md#d-31: the dialog used to borrow `import.cancel`.

    It read the same today, which is exactly why nobody noticed; the next
    reader retitling the wizard's Cancel would have silently retitled this
    one too.
    """
    from wing_parser.ui.settings_dialog import SettingsDialog
    from wing_parser.ui.texts import TEXTS, text

    assert "settings.cancel" in TEXTS
    dialog = SettingsDialog()
    assert dialog.cancel_button.text() == text("settings.cancel")
