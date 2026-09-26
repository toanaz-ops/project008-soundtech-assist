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
        "Problems found in classifier.yaml (from a hand edit) — "
        "fix the entry below or Reset it to the shipped default:"
    ),
}
