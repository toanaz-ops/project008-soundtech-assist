"""Remember window geometry, last page and recent scenes between runs.

Plain functions over one JSON file inside ``config.knowledge_dir()``
— the repo's established per-user store, already isolated by the test
suite's conftest. Deliberately not QSettings: one readable file next to
the verdicts, and pure-logic load/save that need no QApplication.

Everything read back from disk goes through :func:`normalize`, so a
hand-edited or half-written file degrades to defaults instead of
crashing the startup path.
"""

from __future__ import annotations

import json
from pathlib import Path

STATE_FILE = "ui-state.json"
MAX_RECENT = 8

PAGE_KEYS = ("doctor", "overview", "channels", "routing", "diff", "import_",
             "console")

DEFAULTS: dict = {"geometry": None, "page": None, "recent": [], "consoles": []}


def normalize(state: dict) -> dict:
    """Coerce any input to the exact on-disk shape or drop the field."""
    geometry = state.get("geometry")
    page = state.get("page")
    # A list or nothing: a hand-edited `"consoles": "192.168.1.1"` is
    # iterable, and `or []` would have let it through as eight
    # one-character addresses (final review, I2).
    recent = state.get("recent")
    consoles = state.get("consoles")
    recent = recent if isinstance(recent, list) else []
    consoles = consoles if isinstance(consoles, list) else []
    return {
        "geometry": geometry if isinstance(geometry, str) else None,
        "page": page if page in PAGE_KEYS else None,
        "recent": [
            entry for entry in recent if isinstance(entry, str)
        ][:MAX_RECENT],
        "consoles": [
            entry for entry in consoles if isinstance(entry, str)
        ][:MAX_RECENT],
    }


def state_path(directory: Path) -> Path:
    return Path(directory) / STATE_FILE


def load(directory: Path) -> dict:
    try:
        raw = state_path(directory).read_text(encoding="utf-8")
        return normalize(json.loads(raw))
    except (OSError, ValueError):
        return dict(DEFAULTS, recent=[], consoles=[])


def save(directory: Path, state: dict) -> None:
    clean = normalize(state)
    path = state_path(directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(clean, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def remember_recent(recents: list[str], path: str) -> list[str]:
    """Move `path` to the top, drop its older selves, cap the list."""
    rest = [entry for entry in recents if Path(entry) != Path(path)]
    return [str(path), *rest][:MAX_RECENT]


def forget_recent(recents: list[str], path: str) -> list[str]:
    return [entry for entry in recents if Path(entry) != Path(path)]


def remember_console(consoles: list[str], host: str) -> list[str]:
    """Move `host` to the top, drop its older selves, cap the list.

    Addresses are opaque strings (an IP or a hostname), not filesystem
    paths, so this compares plain strings -- unlike `remember_recent`.
    """
    rest = [entry for entry in consoles if entry != host]
    return [str(host), *rest][:MAX_RECENT]


def forget_console(consoles: list[str], host: str) -> list[str]:
    return [entry for entry in consoles if entry != host]
