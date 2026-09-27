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
    "vocabulary.overwrite_confirm": "{name} already exists — overwrite it?",
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
    "import.terms.key": "Key",
    "import.terms.match_word": "match inside a sentence",
    "import.terms.ignore_remember": "Ignore (remember)",
    "import.terms.ai_propose": "AI: propose for unread rows",
    "import.terms.empty_key": "Type a key before recording — never write a blank.",
    "import.terms.not_matching": (
        "Saved, but {fragment!r} still does not match its own key -- check "
        "the key or the \"match inside a sentence\" checkbox."
    ),
    "import.scene.source": "Scene",
    "import.scene.source.doctor": "Doctor's scene",
    "import.scene.source.file": "Open .snap…",
    "import.scene.source.pull": "Console's last Pull",
    "import.scene.open_file": "Open .snap…",
    "import.scene.col.segment": "Segment",
    "import.scene.col.needed": "Kinds needed",
    "import.scene.col.found": "Found",
    "import.scene.col.missing": "Missing",
    "import.scene.skip": "Skip",
    "import.scene.continue": "Continue",
    "import.scene.no_scene": "No scene loaded for this source yet.",
    "import.scene.no_pull_yet": "Nothing pulled from a console this run yet.",
    "import.scene.file_error": "Could not read {path}: {error}",
    "import.scene.file_error_named": "Could not read that .snap: {error}",
    "import.step.scene": "Scene check",
    "import.lint.title": "Check a show-context file",
    "import.lint.open": "Check an existing show-context file…",
    "import.lint.fix": "Fix",
    "import.lint.close": "Close",
    "import.lint.confirm": "Write repairs into this file? A .bak copy is made first.",
    "import.lint.clean": "{count} segments, nothing to repair.",
    "import.lint.fixed": "fixed {n} item(s):",
    "import.lint.backup_failed": "Could not write a backup: {error}",
    "import.lint.read_failed": "Could not read {path}: {error}",
    "import.lint.repair_failed": (
        "Could not write repairs (the .bak is still there): {error}"
    ),
    "import.lint.fixable_mark": "[auto-fixable] {anomaly}",
    "import.lint.unfixable_mark": "[manual only] {anomaly}",
    "import.try_ai.button": "Try AI on this file",
    "import.try_ai.cancel": "Cancel",
    "import.try_ai.running": "Asking the model...",
    "import.try_ai.cancelled": "Cancelled.",
    "import.try_ai.timeout": "The model did not answer within {seconds} s.",
    "import.try_ai.busy": "A model request is already running — cancel it or wait.",
    "import.try_ai.no_key": (
        "No model key configured — Try AI needs one. Set it in Settings."
    ),
    "import.try_ai.kill_switch": "AI is disabled (WING_DISABLE_LLM).",
    "import.try_ai.result": "{provider}, {seconds}s",
    "import.try_ai.field.sheet": "sheet: {value}",
    "import.try_ai.field.header_row": "header_row: {value}",
    "import.try_ai.field.columns": "columns: {value}",
    "import.try_ai.field.headers": "headers: {value}",
    "import.try_ai.field.problems": "problems: {value}",
    "vocabulary.assistant.kill_switch": "AI is disabled (WING_DISABLE_LLM).",
}
