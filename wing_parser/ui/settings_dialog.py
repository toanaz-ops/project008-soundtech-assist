"""The Settings dialog: each end user pastes their own AI provider key.

The key lives in provider.yaml inside the knowledge directory, never in
the repo. Saving writes that file and pins $WING_PROVIDER_CONFIG to it
immediately, so the running process picks the new settings up without a
restart; if the write fails, the previous env pin survives untouched.
`Test connection` is injectable (`probe(cfg) -> (ok, message)`); the
default is `provider.ping`, run on a cancellable worker under the ruled
30 s timeout (task C). Tests inject fakes -- no network here.
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
from wing_parser.ui.call_button import ButtonRunner
from wing_parser.ui.texts import text
from wing_parser.ui.workers import CallRunner

MASK = "•" * 4


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
        self._probe = probe or provider.ping
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

        self.test_button = QPushButton(text("settings.test"))
        self.test_button.clicked.connect(self.run_probe)
        self.cancel_button = QPushButton(text("settings.cancel"))
        self.cancel_button.setVisible(False)
        save_btn = QPushButton(text("settings.save"))
        save_btn.clicked.connect(self._save_and_close)
        close_btn = QPushButton(text("settings.close"))
        close_btn.clicked.connect(self.reject)
        self._runner = CallRunner(self)
        self._probe_call = ButtonRunner(
            runner=self._runner, primary=self.test_button,
            cancel=self.cancel_button, report=self.status_label.setText,
            running=text("settings.probing"),
            cancelled=text("settings.cancelled"),
            timeout_text=text("settings.timeout"),
            busy_text=text("settings.busy"),
            on_error=self._show_probe_error,
        )
        self.cancel_button.clicked.connect(self._probe_call.cancel)
        buttons = QHBoxLayout()
        buttons.addWidget(self.test_button)
        buttons.addWidget(self.cancel_button)
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

    def fill(self, name: str, model: str, base_url: str, api_key: str,
             api_key_env: str = "") -> None:
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

    def run_probe(self) -> bool:
        """Save, then ping off the GUI thread; False when one runs already.

        The outcome lands in the status label either way -- the dialog
        never blocks on the network, and Cancel settles the wait now.
        """
        self.save()
        cfg = provider.resolve_config(config.knowledge_dir())
        return self._probe_call.run(
            "probe", self._probe, cfg, on_success=self._show_probe_result)

    def _show_probe_result(self, pair) -> None:
        ok, message = pair
        self._probe_line(ok, message)

    def _show_probe_error(self, exc) -> None:
        self._probe_line(False, str(exc))

    def _probe_line(self, ok: bool, message: str) -> None:
        key = "settings.probe_ok" if ok else "settings.probe_fail"
        self.status_label.setText(text(key).format(message=message))

    # -- internals -------------------------------------------------------

    def _current_key(self) -> str:
        shown = self.key_edit.text()
        if shown == self._loaded_mask:
            return self._loaded_key
        return shown

    def _save_and_close(self) -> None:
        if self.save():
            self.accept()
