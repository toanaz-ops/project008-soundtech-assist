"""Every UI string lives in one place for future language switching.

The Console page's own strings live in `texts_console.py` and are
merged in below: wave 2 pushed this file past the ~200-line ceiling
(`test_ui_house_style.py:173`), and a page's vocabulary is the one
seam a flat table of strings actually has.
"""

from wing_parser.ui.texts_console import CONSOLE_TEXTS
from wing_parser.ui.texts_write import WRITE_TEXTS

TEXTS: dict[str, str] = {
    "app.title": "wing",
    "window.title": "{app} — {file}{profile}{mark}",
    "page.doctor": "Doctor",
    "page.overview": "Overview",
    "page.channels": "Channels",
    "page.routing": "Routing",
    "page.diff": "Diff",
    "page.import": "Import",
    "page.console": "Console",
    "empty.open_hint": "Open a scene file to begin.",
    "empty.open_button": "Open a scene...",
    "overview.counts": "Scene counts",
    "overview.channels": "Channels",
    "overview.buses": "Buses",
    "overview.mains": "Mains",
    "overview.matrices": "Matrices",
    "overview.live": "Live channels",
    "overview.named": "Named channels",
    "overview.anomalies": "Anomalies",
    "overview.table": "Channels",
    "overview.col.number": "Number",
    "overview.col.name": "Name",
    "overview.col.fader": "Fader",
    "overview.col.kind": "Kind",
    "channels.table": "Channels",
    "channels.col.number": "Number",
    "channels.col.name": "Name",
    "channels.col.kind": "Kind",
    "channels.col.confidence": "Confidence",
    "channels.col.fader": "Fader",
    "channels.col.muted": "Muted",
    "channels.detail_empty": "",
    "channels.title": "Channel {number}: {name}",
    "detail.title": "{rule} — {title}   [{severity} · {layer}]",
    "detail.no_repair": (
        "No one-click repair for this rule: it states a window or a "
        "count, so no single value follows from it. Adjust it by hand "
        "on the console."
    ),
    "routing.summary": "Routing summary",
    "routing.col.label": "Item",
    "routing.col.value": "Count",
    "routing.unclassified": "Unclassified",
    "diff.compare": "Compare with...",
    "changes.undo": "Undo the last change",
    "changes.row": "{label}  —  {path}: {before!r} → {after!r}",
    "findings.severity": "Severity",
    "findings.layer": "Layer",
    "diff.clear": "Clear",
    "diff.table": "Differences",
    "diff.col.path": "Path",
    "diff.col.before": "Before",
    "diff.col.after": "After",
    "diff.col.magnitude": "Magnitude",
    "diff.no_session": "Open a scene first — it is the left side of the diff.",
    "diff.error": "Cannot read that file: {error}",
    "import.pick": "Pick a rundown (.xlsx)...",
    "import.xlsx_filter": "Excel workbook (*.xlsx)",
    "import.yaml_filter": "YAML (*.yaml);;All files (*)",
    "import.sample_pane": "What is in this workbook",
    "import.resting": (
        "Pick a rundown workbook (.xlsx) — its sheets and first rows "
        "appear here, then the wizard walks you to mapping."
    ),
    "import.step.pick": "Pick",
    "import.step.mapping": "Mapping",
    "import.step.vocabulary": "Vocabulary",
    "import.step.save": "Save",
    "import.no_key": (
        "No model key configured — assisted term guessing needs one."
    ),
    "import.open_settings": "Open Settings…",
    "import.sheet": "Sheet",
    "import.header_row": "Header row",
    "import.verified": "Model proposal verified",
    "import.unverified": "Model proposal unverified",
    "import.manual_hint": (
        "No model assist — name the sheet, header row and columns by hand."
    ),
    "import.back": "Back",
    "import.next": "Next",
    "import.load_guesses": "Load guesses",
    "import.record": "Record",
    "import.skip": "Skip",
    "import.preview": "Preview",
    "import.save_as": "Save As...",
    "import.error": (
        "Could not read that sheet — check the header row, "
        "then try again: {error}"
    ),
    "import.needs_kind": "Type a kind before recording — never write a blank.",
    "import.proposing": "Reading the workbook with the model...",
    "import.guessing": "Asking the model about each term...",
    "import.cancel": "Cancel",
    "import.cancelled": "Cancelled — nothing was applied.",
    "import.timeout": "The model did not answer within {seconds} s.",
    "import.busy": "A model request is already running — cancel it or wait.",
    "menu.open": "&Open...",
    "menu.open_title": "Open a WING scene",
    "menu.save_title": "Save the edited scene",
    "menu.scene_filter": "WING scene (*.snap);;All files (*)",
    "menu.save_as": "Save &As...",
    "menu.undo": "&Undo",
    "menu.knowledge": "Where my judgements are stored...",
    "menu.settings": "&Settings...",
    "menu.reanalyse": "&Reanalyse",
    "menu.recent": "Open &Recent",
    "recent.missing.title": "File is gone",
    "recent.missing.body": (
        "{file} is no longer on disk — it has been removed from this list."
    ),
    "menu.file": "&File",
    "menu.edit": "&Edit",
    "menu.tools": "&Tools",
    "menu.help": "&Help",
    "error.open": "Cannot open that file",
    "error.save": "Cannot save",
    "save.done": "Saved",
    "save.body": "Wrote {file}",
    "knowledge.title": "Knowledge directory",
    "knowledge.body": (
        "Verdicts, principles and show profiles live in:\n\n{directory}\n\n"
        "feedback.jsonl holds every verdict recorded here.\n"
        "principles.yaml and shows/ are yours to edit."
    ),
    "verdict.note": "Note (optional)",
    "settings.title": "Settings",
    "settings.provider": "Provider",
    "settings.model": "Model",
    "settings.base_url": "Base URL",
    "settings.api_key": "API key",
    "settings.key_placeholder": (
        "Paste your own key — it stays in provider.yaml on this machine."
    ),
    "settings.api_key_env": "API key env var (optional)",
    "settings.apply_delay": "Default apply delay (s)",
    "settings.save": "Save",
    "settings.cancel": "Cancel",
    "settings.test": "Test connection",
    "settings.close": "Close",
    "settings.probe_ok": "Connection OK — {message}",
    "settings.probe_fail": "Connection FAILED — {message}",
    "settings.save_failed": "Could not write {path}: {error}",
    "settings.probing": "Testing the connection...",
    "settings.cancelled": "Probe cancelled.",
    "settings.timeout": "No reply within {seconds} s — check the base URL.",
    "settings.busy": "A connection test is already running.",
    **CONSOLE_TEXTS,
    **WRITE_TEXTS,
}


def text(key: str) -> str:
    return TEXTS[key]
