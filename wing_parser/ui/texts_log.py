"""The wave-5 write-log strings: the Log page and the post-show report.

Namespace `log.*` (spec section 8). Every `log.report.*` key is also a
label the HTML report prints (`writelog.REPORT_LABEL_KEYS`); the report is
written in the UI language at export time (W7). Marks on the page are
limited to what the vendored font carries (D-51): the check mark, the
multiplication sign and `!` -- the HTML report draws its own badges.
"""

from __future__ import annotations

LOG_TEXTS: dict[str, str] = {
    "page.log": "Log",

    # -- the page ---------------------------------------------------------
    "log.shows_heading": "Shows",
    "log.entries_heading": "Writes",
    "log.export": "Export report…",
    "log.open_folder": "Open log folder",
    "log.refresh": "Refresh",
    "log.empty": "No writes logged yet. Repairs sent to a desk appear here.",
    "log.pick_show": "Pick a show on the left.",
    "log.show_row": "{code}  {name}  {venue}",
    "log.show_counts": (
        "{first} – {last}  ·  {writes} writes  ·  ✓ {sent}  ! {clamped}  × {no_reply}"
    ),
    "log.outcome.sent": "✓ sent",
    "log.outcome.clamped": "! clamped",
    "log.outcome.no_reply": "× no reply",
    "log.warning.append_failed": (
        "The write log could not be saved to {folder}: {error}. "
        "The desk write itself was not affected."
    ),
    "log.warning.skipped": (
        "{count} unreadable line(s) in {code} were skipped."
    ),
    "log.save_title": "Export report",
    "log.save_filter": "HTML report (*.html)",
    "log.export_done": "Report saved: {path}",
    "log.export_failed": "Could not save the report: {error}",

    # -- the HTML report (labels; REPORT_LABEL_KEYS) -----------------------
    "log.report.title": "Write report",
    "log.report.show_code": "Show code",
    "log.report.show": "Show",
    "log.report.venue": "Venue",
    "log.report.dates": "Dates",
    "log.report.desks": "Desk",
    "log.report.app": "App version",
    "log.report.exported": "Exported",
    "log.report.summary": "Summary",
    "log.report.total": "Writes",
    "log.report.sent": "Confirmed",
    "log.report.clamped": "Clamped",
    "log.report.no_reply": "No reply",
    "log.report.reverts": "Reverts",
    "log.report.findings": "Findings addressed",
    "log.report.col.time": "Time",
    "log.report.col.desk": "Desk",
    "log.report.col.address": "Address",
    "log.report.col.label": "Change",
    "log.report.col.finding": "Finding",
    "log.report.col.file_before": "File before",
    "log.report.col.desk_before": "Desk before",
    "log.report.col.written": "Written",
    "log.report.col.readback": "Read back",
    "log.report.col.outcome": "Result",
    "log.report.col.kind": "Kind",
    "log.report.kind.repair": "Repair",
    "log.report.kind.revert": "Revert",
    "log.report.footnote.sent": (
        "The desk read back exactly the value that was written."
    ),
    "log.report.footnote.clamped": (
        "The desk answered with a different value, so it clamped or refused "
        "the one written."
    ),
    "log.report.footnote.no_reply": (
        "The desk did not answer the read-back. The write may or may not "
        "have landed."
    ),
}
