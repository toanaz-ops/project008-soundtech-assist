"""Self-contained HTML post-show report. No Qt, no network, no external assets."""

from __future__ import annotations

from collections.abc import Mapping
from html import escape

from .entry import LogEntry, ts_key
from .layout import COLUMNS, OUTCOME_BADGE
from .store import ShowSummary

REPORT_LABEL_KEYS: tuple[str, ...] = (
    "log.report.title",
    "log.report.show_code",
    "log.report.show",
    "log.report.venue",
    "log.report.dates",
    "log.report.desks",
    "log.report.app",
    "log.report.exported",
    "log.report.summary",
    "log.report.total",
    "log.report.sent",
    "log.report.clamped",
    "log.report.no_reply",
    "log.report.reverts",
    "log.report.findings",
    "log.report.col.time",
    "log.report.col.desk",
    "log.report.col.address",
    "log.report.col.label",
    "log.report.col.finding",
    "log.report.col.file_before",
    "log.report.col.desk_before",
    "log.report.col.written",
    "log.report.col.readback",
    "log.report.col.outcome",
    "log.report.col.kind",
    "log.report.kind.repair",
    "log.report.kind.revert",
    "log.report.footnote.sent",
    "log.report.footnote.clamped",
    "log.report.footnote.no_reply",
)

_CSS = """
body{font:14px/1.45 system-ui,Segoe UI,Arial,sans-serif;color:#111;margin:24px;max-width:1200px}
h1{font-size:22px;margin:0 0 12px}h2{font-size:16px;margin:24px 0 8px}
dl{display:grid;grid-template-columns:max-content 1fr;gap:2px 16px;margin:0}dt{color:#555}dd{margin:0}
table{border-collapse:collapse;width:100%;font-size:12px}
th,td{border:1px solid #bbb;padding:3px 6px;text-align:left;vertical-align:top}
th{background:#eee}td.n,.mono{font-family:Consolas,monospace}
.ok{color:#0a7a2f}.warn{color:#a15c00}.bad{color:#b00020}.badge{font-weight:700}
p.foot{font-size:12px;color:#444;margin:4px 0}
@media print{body{margin:8mm}tr{page-break-inside:avoid}}
"""


def _e(value: object) -> str:
    return "" if value is None else escape(str(value), quote=True)


def _desk(desk: dict | None) -> str:
    if not desk:
        return ""
    return str(desk.get("name") or desk.get("serial") or "")


def _desk_full(desk: dict) -> str:
    parts = [str(desk.get("name") or ""), str(desk.get("serial") or ""), str(desk.get("firmware") or "")]
    return " / ".join(p for p in parts if p)


def render_html(
    summary: ShowSummary,
    entries: list[LogEntry],
    labels: Mapping[str, str],
    exported_at: str,
) -> str:
    def lab(key: str) -> str:
        return _e(labels.get(key, key))

    desks: list[str] = []
    for entry in entries:
        if entry.desk:
            full = _desk_full(entry.desk)
            if full and full not in desks:
                desks.append(full)
    findings = sorted({e.finding for e in entries if e.finding and e.kind == "repair"})
    apps = sorted({e.app for e in entries if e.app})
    dates = summary.first_ts[:10] if summary.first_ts[:10] == summary.last_ts[:10] else (
        f"{summary.first_ts[:10]} – {summary.last_ts[:10]}")

    header = [
        ("log.report.show_code", summary.code),
        ("log.report.show", summary.show),
        ("log.report.venue", summary.venue),
        ("log.report.dates", dates),
        ("log.report.desks", "; ".join(desks)),
        ("log.report.app", ", ".join(apps)),
        ("log.report.exported", exported_at),
    ]
    head_html = "".join(f"<dt>{lab(k)}</dt><dd>{_e(v)}</dd>" for k, v in header)

    summary_rows = [
        ("log.report.total", summary.writes, ""),
        ("log.report.sent", summary.sent, "ok"),
        ("log.report.clamped", summary.clamped, "warn"),
        ("log.report.no_reply", summary.no_reply, "bad"),
        ("log.report.reverts", summary.reverts, ""),
    ]
    sum_html = "".join(f'<dt>{lab(k)}</dt><dd class="n {c}">{_e(v)}</dd>' for k, v, c in summary_rows)
    sum_html += f"<dt>{lab('log.report.findings')}</dt><dd class=\"mono\">{_e(', '.join(findings))}</dd>"

    th = "".join(f"<th>{lab('log.report.col.' + c)}</th>" for c in COLUMNS)
    rows = []
    for e in sorted(entries, key=lambda x: ts_key(x.ts)):
        glyph, cls = OUTCOME_BADGE.get(e.outcome, ("?", ""))
        rows.append(
            "<tr>"
            f'<td class="n">{_e(e.ts)}</td><td>{_e(_desk(e.desk))}</td>'
            f'<td class="mono">{_e(e.address)}</td><td>{_e(e.label)}</td>'
            f'<td class="mono">{_e(e.finding)}</td>'
            f'<td class="n">{_e(e.file_before)}</td><td class="n">{_e(e.desk_before)}</td>'
            f'<td class="n">{_e(e.written)}</td><td class="n">{_e(e.readback)}</td>'
            f'<td class="badge {cls}">{glyph}</td>'
            f"<td>{lab('log.report.kind.' + e.kind) if e.kind in ('repair', 'revert') else _e(e.kind)}</td>"
            "</tr>"
        )
    foot = "".join(
        f'<p class="foot"><span class="badge {cls}">{glyph}</span> {lab("log.report.footnote." + key)}</p>'
        for key, (glyph, cls) in OUTCOME_BADGE.items()
    )
    title = f"{lab('log.report.title')} {_e(summary.code)}"
    return (
        '<!DOCTYPE html>\n<html><head><meta charset="utf-8">'
        f"<title>{title}</title><style>{_CSS}</style></head><body>"
        f"<h1>{title}</h1><dl>{head_html}</dl>"
        f"<h2>{lab('log.report.summary')}</h2><dl>{sum_html}</dl>"
        f"<h2>{lab('log.report.title')}</h2>"
        f"<table><thead><tr>{th}</tr></thead><tbody>{''.join(rows)}</tbody></table>"
        f"<div>{foot}</div></body></html>\n"
    )
