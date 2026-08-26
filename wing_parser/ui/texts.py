"""Every UI string lives in one place for future language switching."""

TEXTS: dict[str, str] = {
    "app.title": "wing",
    "page.doctor": "Doctor",
    "page.overview": "Overview",
    "page.channels": "Channels",
    "page.routing": "Routing",
    "page.diff": "Diff",
    "page.import": "Import",
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
    "routing.summary": "Routing summary",
    "routing.col.label": "Item",
    "routing.col.value": "Count",
    "routing.unclassified": "Unclassified",
    "diff.compare": "Compare with...",
    "diff.clear": "Clear",
    "diff.table": "Differences",
    "diff.col.path": "Path",
    "diff.col.before": "Before",
    "diff.col.after": "After",
    "diff.col.magnitude": "Magnitude",
    "diff.no_session": "Open a scene first — it is the left side of the diff.",
    "diff.error": "Cannot read that file: {error}",
    "import.pick": "Pick a rundown (.xlsx)...",
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
    "knowledge.title": "Knowledge directory",
    "knowledge.body": (
        "Verdicts, principles and show profiles live in:\n\n{directory}\n\n"
        "feedback.jsonl holds every verdict recorded here.\n"
        "principles.yaml and shows/ are yours to edit."
    ),
    "settings.title": "Settings",
    "settings.provider": "Provider",
    "settings.model": "Model",
    "settings.base_url": "Base URL",
    "settings.api_key": "API key",
    "settings.key_placeholder": (
        "Paste your own key — it stays in provider.yaml on this machine."
    ),
    "settings.api_key_env": "API key env var (optional)",
    "settings.save": "Save",
    "settings.test": "Test connection",
    "settings.close": "Close",
    "settings.probe_ok": "Connection OK — {message}",
    "settings.probe_fail": "Connection FAILED — {message}",
    "settings.save_failed": "Could not write {path}: {error}",
}


def text(key: str) -> str:
    return TEXTS[key]
