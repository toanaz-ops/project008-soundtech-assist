"""The wave-12 Automix strings: the Tools dialog and the Settings row.

Namespace `automix.*`, plus the `menu.automix` and `settings.automix*`
keys. Mixer nouns (EQ, Gate, Comp, Fader, FX, Send, Insert, HPF) stay
English in the Vietnamese table (repo rule B2).
"""

from __future__ import annotations

AUTOMIX_TEXTS: dict[str, str] = {
    "menu.automix": "&Automix...",
    "settings.automix": "Automix",
    "settings.automix.disabled": "Disabled",
    "settings.automix.draft": "Draft only",
    "settings.automix_note": (
        "Draft only: Tools > Automix proposes channel-strip changes that "
        "you review and apply to the open scene. Nothing is sent to a desk."),

    "automix.title": "Automix (draft)",
    "automix.banner": (
        "Draft only: nothing is sent to a desk. These are low-confidence "
        "textbook defaults for the chosen genre; the owner reviews every "
        "change before saving."),
    "automix.propose": "Propose",
    "automix.apply": "Apply to scene (draft)",
    "automix.confirm": (
        "Record {count} changes in the open scene as a draft? Nothing is "
        "saved or sent until you use Save as."),
    "automix.summary": (
        "{changes} changes, {suggestions} suggestions, {skipped} skipped, "
        "headroom trim {trim:.1f} dB"),
    "automix.genre": "Genre",
    "automix.bpm": "BPM",
    "automix.venue": "Venue",
    "automix.strength": "Strength",
    "automix.stages": "Stages",
    "automix.percent": "{value} %",

    "automix.genre.pop": "Pop",
    "automix.genre.rock": "Rock",
    "automix.genre.ballad": "Ballad",
    "automix.genre.jazz": "Jazz",
    "automix.genre.edm": "EDM",
    "automix.genre.bolero": "Bolero",
    "automix.genre.speech": "Conference / speech",
    "automix.venue.small": "Small",
    "automix.venue.medium": "Medium",
    "automix.venue.large": "Large",
    "automix.stage.hpf": "HPF",
    "automix.stage.eq": "EQ",
    "automix.stage.gate": "Gate",
    "automix.stage.comp": "Comp",
    "automix.stage.fader": "Fader",
    "automix.stage.fx": "FX",
    "automix.stage.sends": "Sends",
    "automix.stage.inserts": "Inserts",

    "automix.tab.changes": "Changes",
    "automix.tab.suggestions": "Suggestions",
    "automix.tab.skipped": "Skipped",
    "automix.col.channel": "Channel",
    "automix.col.source": "Source",
    "automix.col.stage": "Stage",
    "automix.col.parameter": "Parameter",
    "automix.col.before": "Before",
    "automix.col.after": "After",
    "automix.col.confidence": "Confidence",
    "automix.col.text": "Suggestion",
    "automix.col.reason": "Reason",
    "automix.detail.sources": "Sources:",
    "automix.detail.no_sources": "No cited source: engineering default.",
}
