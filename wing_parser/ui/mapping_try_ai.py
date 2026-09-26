"""The Mapping step's 'Try AI on this file' panel (design spec §7).

Calls suggest.propose_mapping DIRECTLY, not import_controller.proposal_for
-- the latter swallows every provider-shaped failure into None (correct
for the wizard's silent auto-assist, wrong here: this panel exists to
SHOW a classified failure, which a swallowed exception cannot be).
Reuses the page's one shared CallRunner -- never a second one on this
page.

Two deliberate departures from the plan's own draft, both load-bearing
(see tests/test_ui_mapping_try_ai.py's own docstring for how they were
checked against the real test fixtures):

- The kill switch (`classifier.llm.kill_switch_on`) is never checked
  here, the same way Settings' own "Test connection" (settings_dialog.py)
  never checks it. Both are an explicit, one-off diagnostic action the
  operator asked for, not the wizard's silent auto-assist the switch
  exists to silence -- and `tests/test_ui_import_page.py`'s `page`
  fixture sets the switch for every wizard test, so honouring it here
  would make Try AI unreachable from the very page it lives on.
- `_call_provider` runs the provider factory (and the config read for
  the provider/model line) on the WORKER thread, never the GUI thread,
  so a bad provider.yaml reaches `_failed` like any other provider
  failure instead of escaping this button's Qt slot (mirrors
  vocabulary_assistant_support.propose_via_factory).

The no-key hint mirrors VocabularyAssistant's `_update_key_status`, but
only on showEvent, never at construction: this panel lives inside a
QStackedLayout page built long before it is ever shown, and checking
eagerly would grey out a panel no operator has looked at yet.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget,
)

from wing_parser import config
from wing_parser.classifier import provider_errors
from wing_parser.classifier.provider import resolve_config
from wing_parser.showcontext.ingest import suggest
from wing_parser.ui import key_status
from wing_parser.ui.call_button import ButtonRunner
from wing_parser.ui.texts import text


def _call_provider(provider_factory, xlsx):
    """Runs on the worker thread started by CallRunner -- a malformed
    provider.yaml or a missing SDK must reach `_failed` like any other
    provider failure (see module doc), never crash a Qt slot."""
    cfg = resolve_config(config.knowledge_dir())
    provider = provider_factory()
    proposal = suggest.propose_mapping(xlsx, provider)
    return cfg, proposal


class MappingTryAi(QWidget):
    def __init__(self, runner, provider_factory, xlsx_provider: Callable[[], str | None]) -> None:
        super().__init__()
        self._runner = runner
        self._provider_factory = provider_factory
        self._xlsx_provider = xlsx_provider
        self._key_ok = True
        self._started_at = 0.0

        self.try_button = QPushButton(text("import.try_ai.button"))
        self.try_button.clicked.connect(self._try)
        self.cancel_button = QPushButton(text("import.try_ai.cancel"))
        self.cancel_button.setVisible(False)
        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        self.proposal_view = QTextEdit()
        self.proposal_view.setReadOnly(True)

        self._call = ButtonRunner(
            runner=runner, primary=self.try_button, cancel=self.cancel_button,
            report=self.result_label.setText,
            running=text("import.try_ai.running"),
            cancelled=text("import.try_ai.cancelled"),
            timeout_text=text("import.try_ai.timeout"),
            busy_text=text("import.try_ai.busy"), on_error=self._failed,
        )
        self.cancel_button.clicked.connect(self._call.cancel)

        buttons = QHBoxLayout()
        buttons.addWidget(self.try_button)
        buttons.addWidget(self.cancel_button)

        layout = QVBoxLayout(self)
        layout.addLayout(buttons)
        layout.addWidget(self.result_label)
        layout.addWidget(self.proposal_view)

    def showEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().showEvent(event)
        self._update_key_status()

    def _update_key_status(self) -> None:
        """Proactive grey-out, same idiom as VocabularyAssistant's own
        (module doc): re-checked whenever this panel is shown, and never
        re-enabled while a call the ButtonRunner itself disabled is
        still running."""
        self._key_ok = key_status.key_configured()
        enabled = self._key_ok and not self._runner.busy
        self.try_button.setEnabled(enabled)
        if self._runner.busy:
            return
        no_key_text = text("import.try_ai.no_key")
        if not self._key_ok:
            self.result_label.setText(no_key_text)
        elif self.result_label.text() == no_key_text:
            self.result_label.setText("")

    def _try(self) -> bool:
        if not self._key_ok:
            return False
        xlsx = self._xlsx_provider()
        if not xlsx:
            return False
        self._started_at = time.monotonic()
        return self._call.run(
            "proposal", _call_provider, self._provider_factory, xlsx,
            on_success=self._succeeded,
        )

    def _succeeded(self, result) -> None:
        cfg, proposal = result
        elapsed = round(time.monotonic() - self._started_at, 1)
        self.result_label.setText(
            text("import.try_ai.result").format(
                provider=f"{cfg.name}/{cfg.model}", seconds=elapsed))
        lines = [
            f"sheet: {proposal.sheet}", f"header_row: {proposal.header_row}",
            f"columns: {proposal.columns}", f"headers: {proposal.headers}",
        ]
        if proposal.problems:
            lines.append("problems: " + "; ".join(proposal.problems))
        self.proposal_view.setPlainText("\n".join(lines))

    def _failed(self, exc: Exception) -> None:
        _code, message = provider_errors.classify(exc)
        self.result_label.setText(message)
        self.proposal_view.setPlainText("")
