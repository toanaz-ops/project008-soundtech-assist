"""The Mapping step's 'Try AI on this file' panel (design spec §7).

Calls suggest.propose_mapping DIRECTLY, not import_controller.proposal_for
-- the latter swallows every provider-shaped failure into None (correct
for the wizard's silent auto-assist, wrong here: this panel exists to
SHOW a classified failure, which a swallowed exception cannot be).
Reuses the page's one shared CallRunner -- never a second one on this
page.

**Fix round 1, controller ruling (supersedes this file's own earlier
docstring): the kill switch IS honoured here.** `classifier/llm.py`'s
own policy (`kill_switch_on`'s docstring) is that every path which
would construct a provider must ask it first; `_try()` now does, before
anything else, and shows `import.try_ai.kill_switch` without ever
calling `self._provider_factory`. Tests that need a real call now
route through the panel's `panel` fixture (which never sets the switch)
or explicitly `monkeypatch.delenv("WING_DISABLE_LLM", raising=False)`;
`tests/test_ui_import_page.py`'s own end-to-end test does the latter,
since its `page` fixture sets the switch for every OTHER wizard test.
Settings' own "Test connection" is UNCHANGED by this ruling -- a
deliberately deferred decision, not an oversight.

One departure from the plan's own draft remains, load-bearing:
`_call_provider` runs the provider factory (and the config read for the
provider/model line) on the WORKER thread, never the GUI thread, so a
bad provider.yaml reaches `_failed` like any other provider failure
instead of escaping this button's Qt slot (mirrors
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
from wing_parser.classifier.llm import kill_switch_on
from wing_parser.classifier.provider import resolve_config
from wing_parser.showcontext.ingest import suggest
from wing_parser.ui import key_status
from wing_parser.ui import vocabulary_assistant_support as support
from wing_parser.ui.ai_error_text import ai_message
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
        still running. The kill switch takes priority over the no-key
        hint when both apply -- either one alone is reason enough to
        stay disabled."""
        self._key_ok = key_status.key_configured()
        switched_off = kill_switch_on()
        enabled = self._key_ok and not switched_off and not self._runner.busy
        self.try_button.setEnabled(enabled)
        if self._runner.busy:
            return
        kill_switch_text = text("import.try_ai.kill_switch")
        no_key_text = text("import.try_ai.no_key")
        if switched_off:
            self.result_label.setText(kill_switch_text)
        elif not self._key_ok:
            self.result_label.setText(no_key_text)
        elif self.result_label.text() in (no_key_text, kill_switch_text):
            self.result_label.setText("")

    def _try(self) -> bool:
        if kill_switch_on():
            self.result_label.setText(text("import.try_ai.kill_switch"))
            return False
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
            text("import.try_ai.field.sheet").format(value=proposal.sheet),
            text("import.try_ai.field.header_row").format(value=proposal.header_row),
            text("import.try_ai.field.columns").format(value=proposal.columns),
            text("import.try_ai.field.headers").format(value=proposal.headers),
        ]
        if proposal.problems:
            lines.append(text("import.try_ai.field.problems").format(
                value="; ".join(proposal.problems)))
        self.proposal_view.setPlainText("\n".join(lines))

    def _failed(self, exc: Exception) -> None:
        """M7: an UNRECOVERABLE failure (bad/missing key, no network, a
        missing SDK) greys the button too, same as
        VocabularyAssistant._failed -- nothing will succeed until
        something OUTSIDE this panel changes. `_update_key_status`'s own
        showEvent recheck is what recovers it, exactly like the no-key/
        kill-switch grey-out already does."""
        code, message = provider_errors.classify(exc)
        self.result_label.setText(ai_message(code, message))
        self.proposal_view.setPlainText("")
        if code in support.UNRECOVERABLE:
            self.try_button.setEnabled(False)
