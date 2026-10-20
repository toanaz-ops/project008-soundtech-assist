"""Durable per-show write log and post-show HTML report (no Qt, no net)."""

from .codes import adhoc_code, normalize_code
from .entry import ENTRY_VERSION, LogEntry, now_ts, ts_key
from .layout import COLUMNS, OUTCOME_BADGE
from .report import REPORT_LABEL_KEYS, render_html
from .store import ShowSummary, append, list_shows, log_dir, read_show

__all__ = [
    "COLUMNS",
    "ENTRY_VERSION",
    "LogEntry",
    "OUTCOME_BADGE",
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
    "ts_key",
]
