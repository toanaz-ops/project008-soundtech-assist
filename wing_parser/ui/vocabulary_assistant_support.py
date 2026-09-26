"""Plumbing for the Assistant tab, split out of vocabulary_assistant.py to
stay under this project's 200-line-per-UI-file ceiling (the same reason
vocabulary_tab_support.py/vocabulary_tab_widgets.py exist for the
Sets/Terms tabs -- ToanAZ's standing preference for short,
single-responsibility files).
"""

from __future__ import annotations

from functools import partial

from PySide6.QtWidgets import QCheckBox, QTableWidgetItem

from wing_parser.classifier import provider_errors, vocab_changes
from wing_parser.ui.vocabulary_tab_support import write_or_report

COLUMNS = (
    "vocabulary.assistant.col.apply", "vocabulary.assistant.col.before",
    "vocabulary.assistant.col.after", "vocabulary.assistant.col.reason",
)

#: provider_errors classes that mean nothing will succeed until something
#: OUTSIDE this window changes (a bad/missing key, no network, a missing
#: SDK in a frozen exe) -- these grey `propose_button`/`instruction_edit`
#: out on top of reporting the message (design spec §8.1).
UNRECOVERABLE = (provider_errors.BAD_KEY, provider_errors.NO_KEY,
                provider_errors.NO_NETWORK, provider_errors.SDK_MISSING)


def propose_via_factory(provider_factory, *, instruction, fragments, vocabulary, known_kinds):
    """Runs on the worker thread `VocabularyAssistant._start` schedules --
    `provider_factory` can raise (a malformed provider.yaml, a missing
    named config) exactly where a model call failing would, so both
    reach `_failed` the same way instead of the factory's own error
    escaping a Qt slot silently on the GUI thread and, from
    `VocabularyWindow(initial_fragments=...)`, aborting the window's
    `__init__` (fix round 1, I1)."""
    provider = provider_factory()
    return vocab_changes.propose_changes(
        provider, instruction=instruction, fragments=fragments,
        vocabulary=vocabulary, known_kinds=known_kinds)


def populate_row(table, row: int, validated: vocab_changes.Validated, vocabulary) -> QCheckBox:
    """One proposal row: a tickbox (enabled+checked only when valid),
    Before (the REAL stored entry, `vocab_changes.current_before` --
    fix round 1, I3 -- never the model's own `before` claim), After, and
    the reason (the model's, plus every validation problem when
    invalid)."""
    change = validated.change
    reason = change.reason if validated.valid else (
        f"{change.reason} — {'; '.join(validated.problems)}"
    )
    before = vocab_changes.current_before(change, vocabulary)
    check = QCheckBox()
    check.setEnabled(validated.valid)
    check.setChecked(validated.valid)
    table.setCellWidget(row, 0, check)
    table.setItem(row, 1, QTableWidgetItem("" if before is None else str(before)))
    table.setItem(row, 2, QTableWidgetItem("" if change.after is None else str(change.after)))
    table.setItem(row, 3, QTableWidgetItem(reason))
    return check


def apply_ticked(parent, checks, validated_list, vocabulary) -> tuple[int, int]:
    """Write every ticked-and-valid change; return (applied, failed).

    A row ticked-and-valid at proposal time is re-checked here for real:
    `vocab_changes.apply` calls straight into `vocabulary.put_set`/
    `put_term`, which validate again immediately before writing --
    catching what a batch of several changes can create (an earlier
    applied change altering what a later one's cycle/kind/set check
    sees; see vocab_changes.py's own docstring for why this module does
    not chain-validate the whole batch up front instead).
    `write_or_report` (shared with the Sets/Terms tabs) reports any such
    failure with the house QMessageBox on `parent` and lets the rest of
    the ticked rows proceed."""
    applied = failed = 0
    for check, validated in zip(checks, validated_list):
        if not (check.isChecked() and validated.valid):
            continue
        change = validated.change
        if write_or_report(parent, partial(vocab_changes.apply, change, vocabulary)):
            applied += 1
        else:
            failed += 1
    return applied, failed
