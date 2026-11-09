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
    "settings.automix.full_auto": "Full auto (live desk)",
    "settings.automix_note": (
        "Draft only: Tools > Automix proposes channel-strip changes that "
        "you review and apply to the open scene. Nothing is sent to a desk. "
        "Full auto also offers a live mode that changes the connected desk "
        "continuously until you press Stop."),

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
        "headroom trim {trim:.1f} dB, {warnings} knowledge warnings"),
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
    "automix.tab.warnings": "Warnings",
    "automix.col.channel": "Channel",
    "automix.col.source": "Source",
    "automix.col.stage": "Stage",
    "automix.col.parameter": "Parameter",
    "automix.col.before": "Before",
    "automix.col.after": "After",
    "automix.col.confidence": "Confidence",
    "automix.col.text": "Suggestion",
    "automix.col.reason": "Reason",
    "automix.col.warning": "Warning",
    "automix.detail.sources": "Sources:",
    "automix.detail.no_sources": "No cited source: engineering default.",

    "automix.full_auto": "Full auto...",
    "automix.col.path": "Parameter",
    "automix.col.mode": "Result",
    "automix.live.title": "Automix (full auto, live desk)",
    "automix.live.banner": (
        "Full auto changes the connected desk continuously, step by step, "
        "through the same audited write path as Repair. Pull the scene on "
        "the Console page first. A parameter you move by hand is locked "
        "and left alone. Simulate (on by default) reads the desk but "
        "writes nothing."),
    "automix.live.ack": (
        "FULL AUTO: the app will change this desk continuously until Stop"),
    "automix.live.simulate": "Simulate (no writes)",
    "automix.live.confirm_real": (
        "Turn Simulate off? The next Start will write to the real desk."),
    "automix.live.start": "Start",
    "automix.live.stop": "Stop (Esc)",
    "automix.live.revert": "Revert automix",
    "automix.live.locked": "Locked by hand (left alone):",
    "automix.live.need_connection": (
        "Connect to a console first (Console page), then pull its scene."),
    "automix.live.need_scene": "Pull or open a scene first (Console page).",
    "automix.live.busy": "A write is already running; try again.",
    "automix.live.state.idle": "Idle",
    "automix.live.state.running": "Running",
    "automix.live.state.stopped": "Stopped",
    "automix.live.state.failed": "Failed",
    "automix.live.status": (
        "{state} - ticks {ticks}, rows {rows}, pending {pending}, "
        "locked {locked}"),
    "automix.live.mode.simulated": "Would write",
    "automix.live.mode.sent": "Sent",
    "automix.live.mode.clamped": "Clamped",
    "automix.live.mode.no_reply": "No reply",
    "automix.live.mode.revert": "Reverted",
    "automix.live.error": "Error: {error}",
    "automix.live.gate_closed": (
        "Stopped: the console connection or the arming was lost."),
    "automix.live.reverted": "Reverted {count} parameters to their desk values.",
    "automix.live.nothing_to_revert": "Nothing to revert.",
}
