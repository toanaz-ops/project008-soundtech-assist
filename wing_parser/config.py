"""Where ToanAZ's principles, cache and feedback log live.

Resolution order: an explicit override argument, then the
WING_KNOWLEDGE_DIR environment variable, then the first existing entry
in SEARCH_ORDER, then the in-repo default. The in-repo default is
deliberate: these principles are a long-lived asset, and git history
shows how the judgement behind them evolved. Setting one environment
variable moves the whole set elsewhere with no code change.

**A frozen build must not use the in-repo default.** `_REPO_DEFAULT` is
derived from `__file__`, and inside a PyInstaller bundle that resolves
into the temporary extraction directory, which is deleted when the
process exits. Everything this directory holds is either written by the
user or edited by them -- the feedback log above all -- so resolving
there would mean every verdict recorded in a packaged app vanished on
close, silently and with no error. The frozen branch below sends the
whole set to a real per-user directory instead, and `seed_user_dir`
copies the bundled starting set into it once.
"""

from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ENV_VAR = "WING_KNOWLEDGE_DIR"

_REPO_DEFAULT = Path(__file__).resolve().parent.parent / "knowledge" / "toanaz"

USER_DEFAULT = Path.home() / ".config" / "wing-skill"

SEARCH_ORDER: tuple[Path, ...] = (
    _REPO_DEFAULT,
    USER_DEFAULT,
    Path.home() / "wing-skill",
)


def is_frozen() -> bool:
    """True inside a PyInstaller (or similar) bundle."""
    return bool(getattr(sys, "frozen", False))


def bundled_dir() -> Path:
    """The read-only starting set shipped inside a frozen build.

    The same path `_REPO_DEFAULT` names, which is why it is only ever a
    *source* to copy from when frozen, never a destination.
    """
    return _REPO_DEFAULT


def knowledge_dir(override: Path | None = None) -> Path:
    if override is not None:
        return Path(override)

    from_env = os.environ.get(ENV_VAR)
    if from_env:
        return Path(from_env)

    if is_frozen():
        # SEARCH_ORDER is deliberately not consulted: its first entry is
        # the bundle's own temporary copy, which exists and would win.
        return USER_DEFAULT

    for candidate in SEARCH_ORDER:
        if candidate.is_dir():
            return candidate

    return _REPO_DEFAULT


def seed_user_dir(target: Path | None = None, source: Path | None = None) -> bool:
    """Copy the bundled starting set into the user's directory, once.

    Returns True if a copy happened. Existing content is never touched:
    the whole point of this directory is that the user edits it, so a
    second run must not overwrite an edited principles.yaml or truncate
    a feedback log. That makes this safe to call on every startup.

    Called from the application's entry point rather than from
    `knowledge_dir`, because resolving a path should not write to disk.
    """
    destination = Path(target) if target is not None else knowledge_dir()
    origin = Path(source) if source is not None else bundled_dir()

    if destination.exists() or not origin.is_dir() or origin == destination:
        return False

    shutil.copytree(origin, destination)
    return True
