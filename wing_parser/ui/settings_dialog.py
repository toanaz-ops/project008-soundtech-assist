"""The Settings dialog: each end user pastes their own AI provider key.

The key lives in provider.yaml inside the knowledge directory, never in
the repo. Saving writes that file and pins $WING_PROVIDER_CONFIG to it
immediately, so the running process's next `provider.load_config(None)`
picks the new settings up without a restart -- in dev and frozen alike.
If the write fails, the previous env pin survives untouched.

`Test connection` is injectable: `probe` takes the written
ProviderConfig and returns (ok, message). The default probe builds a
provider from the written config and pings one trivial completion; tests
inject fakes so nothing here ever touches the network on its own.
"""

from __future__ import annotations

import io
import os

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from wing_parser import config
from wing_parser.classifier import provider
from wing_parser.ui.texts import text

MASK = "•" * 4

_PING_SCHEMA = {
    "type": "object",
    "properties": {"ok": {"type": "string"}},
    "required": ["ok"],
}


def _default_probe(cfg: provider.ProviderConfig) -> tuple[bool, str]:
    """One trivial round-trip against the configured endpoint."""
    try:
        engine = provider.make_provider(cfg)
        provider.complete_json(engine, "You reply ok.", "ping", _PING_SCHEMA)
    except Exception as exc:  # noqa: BLE001 - every failure becomes a message
        return False, str(exc)
    return True, f"{cfg.name} replied"


def _mask(key: str) -> str:
    return MASK + key[-4:] if key else ""


def _dump_yaml(doc: dict) -> str:
    from ruamel.yaml import YAML

    engine = YAML()
    stream = io.StringIO()
    engine.dump(doc, stream)
    return stream.getvalue()


class SettingsDialog(QDialog):
    def __init__(self, parent=None, *, probe=None) -> None:
        super().__init__(parent)
        self._probe = probe or _default_probe
        self.setWindowTitle(text("settings.title"))
        self.setMinimumWidth(460)

        cfg = self._loaded_config()
        # The masked text shown for the loaded key doubles as an
        # unchanged-marker: saving it re-writes the real key untouched,
        # while anything the operator types replaces it.
        self._loaded_mask = _mask(cfg.api_key)
        self._loaded_key = cfg.api_key

        self.name_box = QComboBox()
        self.name_box.addItems(["anthropic", "openai-compat"])
        self.name_box.setCurrentText(cfg.name)
        self.model_edit = QLineEdit(cfg.model)
        self.base_url_edit = QLineEdit(cfg.base_url)
        self.key_edit = QLineEdit(self._loaded_mask)
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText(text("settings.key_placeholder"))
        self.env_edit = QLineEdit(cfg.api_key_env)

        form = QFormLayout()
        form.addRow(text("settings.provider"), self.name_box)
        form.addRow(text("settings.model"), self.model_edit)
        form.addRow(text("settings.base_url"), self.base_url_edit)
        form.addRow(text("settings.api_key"), self.key_edit)
        form.addRow(text("settings.api_key_env"), self.env_edit)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        test_btn = QPushButton(text("settings.test"))
        test_btn.clicked.connect(self.run_probe)
        save_btn = QPushButton(text("settings.save"))
        save_btn.clicked.connect(self._save_and_close)
        close_btn = QPushButton(text("settings.close"))
        close_btn.clicked.connect(self.reject)
        buttons = QHBoxLayout()
        buttons.addWidget(test_btn)
        buttons.addWidget(save_btn)
        buttons.addStretch(1)
        buttons.addWidget(close_btn)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.status_label)
        layout.addLayout(buttons)

    @property
    def key_display(self) -> QLineEdit:
        """The field as displayed: the loaded key only ever appears masked."""
        return self.key_edit

    def _loaded_config(self) -> provider.ProviderConfig:
        """This dialog manages the knowledge-dir copy, so it wins.

        The CLI's own ./provider.yaml and $WING_PROVIDER_CONFIG stay
        valid fallbacks for a first run that never saved from here.
        """
        path = config.knowledge_dir() / "provider.yaml"
        return provider.resolve(
            provider.load_config(path if path.exists() else None)
        )

    # -- driving ---------------------------------------------------------

    def fill(
        self, name: str, model: str, base_url: str, api_key: str,
        api_key_env: str = "",
    ) -> None:
        self.name_box.setCurrentText(name)
        self.model_edit.setText(model)
        self.base_url_edit.setText(base_url)
        self.key_edit.setText(api_key)
        self.env_edit.setText(api_key_env)

    def save(self) -> bool:
        doc = {
            "provider": self.name_box.currentText(),
            "model": self.model_edit.text().strip(),
            "base_url": self.base_url_edit.text().strip(),
            "api_key_env": self.env_edit.text().strip(),
            "api_key": self._current_key(),
        }
        path = config.knowledge_dir() / "provider.yaml"
        previous = os.environ.get(provider.ENV_VAR)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(_dump_yaml(doc), encoding="utf-8")
        except OSError as exc:
            os.environ.pop(provider.ENV_VAR, None)
            if previous is not None:
                os.environ[provider.ENV_VAR] = previous
            QMessageBox.critical(
                self, text("settings.title"),
                text("settings.save_failed").format(path=path, error=exc),
            )
            return False
        os.environ[provider.ENV_VAR] = str(path)
        return True

    def run_probe(self) -> tuple[bool, str]:
        self.save()
        try:
            ok, message = self._probe(provider.load_config(None))
        except Exception as exc:  # noqa: BLE001 - a probe failure is a message
            ok, message = False, str(exc)
        template = text("settings.probe_ok") if ok else text("settings.probe_fail")
        self.status_label.setText(template.format(message=message))
        return ok, message

    # -- internals -------------------------------------------------------

    def _current_key(self) -> str:
        shown = self.key_edit.text()
        if shown == self._loaded_mask:
            return self._loaded_key
        return shown

    def _save_and_close(self) -> None:
        if self.save():
            self.accept()
