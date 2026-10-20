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

from wing_parser.ui.texts import LANGUAGES

STATE_FILE = "ui-state.json"
MAX_RECENT = 8

PAGE_KEYS = ("doctor", "overview", "channels", "routing", "diff", "import_",
             "console")

#: F6: the countdown a Delayed apply opens at. Clamped rather than
#: rejected -- a hand-edited 0 or 999 is a typo, not a reason to lose the
#: rest of the file.
MIN_APPLY_DELAY = 3
MAX_APPLY_DELAY = 60

#: Wave 5 (W8'): the show last armed for, so the Arm dialog can prefill it.
MAX_SHOW_TEXT = 80

DEFAULTS: dict = {"geometry": None, "page": None, "recent": [], "consoles": [],
                  "apply_delay": 5, "language": "en", "last_show": None}


def _last_show(raw) -> dict | None:
    """`{code, name, venue}` of strings, or `None` for anything else."""
    if not isinstance(raw, dict) or not isinstance(raw.get("code"), str):
        return None
    def clip(key: str) -> str:
        value = raw.get(key)
        return value[:MAX_SHOW_TEXT] if isinstance(value, str) else ""
    return {"code": raw["code"], "name": clip("name"), "venue": clip("venue")}


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
    # `bool` is an int subclass, and True is not a number of seconds.
    delay = state.get("apply_delay")
    if isinstance(delay, bool) or not isinstance(delay, int):
        delay = DEFAULTS["apply_delay"]
    delay = min(max(delay, MIN_APPLY_DELAY), MAX_APPLY_DELAY)
    language = state.get("language")
    return {
        "geometry": geometry if isinstance(geometry, str) else None,
        "page": page if page in PAGE_KEYS else None,
        "recent": [
            entry for entry in recent if isinstance(entry, str)
        ][:MAX_RECENT],
        "consoles": [
            entry for entry in consoles if isinstance(entry, str)
        ][:MAX_RECENT],
        "apply_delay": delay,
        "language": language if language in LANGUAGES else "en",
        "last_show": _last_show(state.get("last_show")),
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


def save_language(directory: Path, code: str) -> None:
    """Change only the language: the Settings row writes it the moment
    it changes, without waiting for (or clobbering) a close-time save."""
    save(directory, dict(load(directory), language=code))


def save_last_show(directory: Path, show: dict) -> None:
    """Change only the last show: the Arm dialog writes it the moment the
    operator arms, without waiting for a close-time save."""
    save(directory, dict(load(directory), last_show=show))


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
