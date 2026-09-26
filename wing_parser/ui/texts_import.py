"""Every wave-4 string: the Vocabulary window, its assistant, the Scene
cross-check step, the lint dialog, and the Mapping step's Try AI. Merged
into TEXTS the way CONSOLE_TEXTS/WRITE_TEXTS already are (texts.py)."""

from __future__ import annotations

IMPORT_TEXTS: dict[str, str] = {
    "vocabulary.title": "Vocabulary",
    "vocabulary.open_button": "Vocabulary…",
    "vocabulary.tab.sets": "Sets",
    "vocabulary.tab.terms": "Terms",
    "vocabulary.close": "Close",
    "vocabulary.col.label": "Label",
    "vocabulary.col.kinds": "Kinds",
    "vocabulary.col.nested": "Nested sets",
    "vocabulary.col.source": "Source",
    "vocabulary.col.key": "Term",
    "vocabulary.col.match": "Match",
    "vocabulary.add": "Add…",
    "vocabulary.edit": "Edit…",
    "vocabulary.delete": "Delete",
    "vocabulary.reset": "Reset to default",
    "vocabulary.dialog.name": "Name",
    "vocabulary.dialog.label": "Label",
    "vocabulary.dialog.kinds": "Kinds",
    "vocabulary.dialog.sets": "Sets",
    "vocabulary.dialog.ignore": "Ignore this term (no kind)",
    "vocabulary.dialog.match": "Match",
    "vocabulary.dialog.match.exact": "the whole fragment, exactly",
    "vocabulary.dialog.match.word": "as a whole word inside a sentence",
    "vocabulary.broken": "broken — {names} no longer exists",
    "vocabulary.problems_header": (
        "Problems found in classifier.yaml (from a hand edit) — fix the "
        "entry directly in classifier.yaml, or remove it here with "
        "Delete/Reset where a row exists for it:"
    ),
    "vocabulary.search_placeholder": "Search…",
    "vocabulary.source.default_deleted": "default, deleted",
    "vocabulary.pick_set": "Pick another set…",
    "vocabulary.drop_reference": "Drop the reference",
    "vocabulary.pick_set_prompt": "Choose a set to replace {name}:",
    "vocabulary.no_sets_to_pick": "There are no sets to choose from.",
    "vocabulary.name_required": "Name cannot be empty.",
    "vocabulary.name_exists": "already exists — use Edit",
    "vocabulary.write_failed": "Could not save: {error}",
    "vocabulary.kind_drop_confirm": (
        "Saving will drop unknown kind(s) {kinds}, which this build does "
        "not recognise. Continue?"
    ),
    "vocabulary.delete_confirm": "Delete {name}? This cannot be undone from here.",
    "vocabulary.tab.assistant": "Assistant",
    "vocabulary.assistant.placeholder": (
        "e.g. \"my drum kit has no kick out, add a second tom\", "
        "\"cajon is percussion\""
    ),
    "vocabulary.assistant.propose": "Propose",
    "vocabulary.assistant.cancel": "Cancel",
    "vocabulary.assistant.apply": "Apply ticked changes",
    "vocabulary.assistant.running": "Asking the model...",
    "vocabulary.assistant.cancelled": "Cancelled — nothing was applied.",
    "vocabulary.assistant.timeout": "The model did not answer within {seconds} s.",
    "vocabulary.assistant.busy": "A model request is already running — cancel it or wait.",
    "vocabulary.assistant.col.apply": "",
    "vocabulary.assistant.col.before": "Before",
    "vocabulary.assistant.col.after": "After",
    "vocabulary.assistant.col.reason": "Reason",
    "vocabulary.assistant.no_key": (
        "No model key configured — the assistant needs one. Set it in Settings."
    ),
    "vocabulary.assistant.apply_result": "{applied} applied, {failed} failed.",
}
