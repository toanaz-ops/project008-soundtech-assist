"""Where ToanAZ's principles, cache and feedback log live.

Resolution order: an explicit override argument, then the
WING_KNOWLEDGE_DIR environment variable, then the first existing entry
in SEARCH_ORDER, then the in-repo default. The in-repo default is
deliberate: these principles are a long-lived asset, and git history
shows how the judgement behind them evolved. Setting one environment
variable moves the whole set elsewhere with no code change.
"""

from __future__ import annotations

import os
from pathlib import Path

ENV_VAR = "WING_KNOWLEDGE_DIR"

_REPO_DEFAULT = Path(__file__).resolve().parent.parent / "knowledge" / "toanaz"

SEARCH_ORDER: tuple[Path, ...] = (
    _REPO_DEFAULT,
    Path.home() / ".config" / "wing-skill",
    Path.home() / "wing-skill",
)


def knowledge_dir(override: Path | None = None) -> Path:
    if override is not None:
        return Path(override)

    from_env = os.environ.get(ENV_VAR)
    if from_env:
        return Path(from_env)

    for candidate in SEARCH_ORDER:
        if candidate.is_dir():
            return candidate

    return _REPO_DEFAULT
