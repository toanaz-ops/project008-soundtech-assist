"""Show-code validation. A code names the log file, so it must be path-safe."""

from __future__ import annotations

import re
from datetime import datetime

_CODE = re.compile(r"(AZ-\d+|AZA-\d{6,}|ADHOC-\d{8}-\d{4})")


def normalize_code(raw: str) -> str | None:
    """Strip and upper-case ``raw``; return it if valid, else ``None``."""
    code = str(raw).strip().upper()
    return code if _CODE.fullmatch(code) else None


def adhoc_code(now: datetime) -> str:
    """Code for a show that has none yet: ``ADHOC-YYYYMMDD-HHMM``."""
    return now.strftime("ADHOC-%Y%m%d-%H%M")
