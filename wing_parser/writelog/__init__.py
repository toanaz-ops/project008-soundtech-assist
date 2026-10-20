"""Durable per-show write log and post-show HTML report (no Qt, no net)."""

from .codes import adhoc_code, normalize_code
from .entry import ENTRY_VERSION, LogEntry, now_ts
from .report import REPORT_LABEL_KEYS, render_html
from .store import ShowSummary, append, list_shows, log_dir, read_show

__all__ = [
    "ENTRY_VERSION",
    "LogEntry",
    "REPORT_LABEL_KEYS",
    "ShowSummary",
    "adhoc_code",
    "append",
    "list_shows",
    "log_dir",
    "normalize_code",
    "now_ts",
    "read_show",
    "render_html",
]
