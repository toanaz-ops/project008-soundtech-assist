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
}


def text(key: str) -> str:
    return TEXTS[key]
