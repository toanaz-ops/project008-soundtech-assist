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
}


def text(key: str) -> str:
    return TEXTS[key]
