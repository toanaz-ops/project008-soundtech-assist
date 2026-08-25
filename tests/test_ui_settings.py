import os

import pytest

pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture
def knowledge(tmp_path, monkeypatch):
    from wing_parser import config

    monkeypatch.setenv(config.ENV_VAR, str(tmp_path))
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


def test_probe_failure_is_reported_not_raised(qt_app, knowledge):
    from wing_parser.ui.settings_dialog import SettingsDialog

    def bad_probe(config):
        raise RuntimeError("no network here")

    dlg = SettingsDialog(probe=bad_probe)
    ok, message = dlg.run_probe()
    assert ok is False
    assert "no network here" in message


def test_existing_config_loads_masked(qt_app, knowledge):
    from wing_parser.ui.settings_dialog import SettingsDialog

    (knowledge / "provider.yaml").write_text(
        "provider: anthropic\nmodel: claude-opus-5\napi_key: sk-secret-abcd\n",
        encoding="utf-8",
    )
    dlg = SettingsDialog()
    assert "abcd" in dlg.key_display.text() and "secret" not in dlg.key_display.text()
