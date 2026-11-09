"""What a Full auto tick or revert leaves behind (wave 12 phase 2).

Real writes become Sent-ledger rows (so Revert all covers them) and write-log
entries carrying the arm's show code; a revert is emitted on the ledger's
`reverted` signal, which the log sink records as kind `revert`. Simulated
rows only become table cells.
"""

from __future__ import annotations

from wing_parser.edit.journal import Patch
from wing_parser.net.address import osc_address
from wing_parser.ui.automix_live_view import mode_text
from wing_parser.ui.texts import text
from wing_parser.ui.write_records import SentWrite, outcome


def _sent(ctx, row) -> SentWrite:
    show = dict(ctx.show) if ctx.show else None
    return SentWrite(osc_address(row.path), row.path, row.before, row.after,
                     row.result, ctx.identity, show)


def record_rows(window, ctx, genre: str, rows) -> list:
    """Ledger + log every real write; the table cells for all rows."""
    changes = getattr(window, "changes_panel", None)
    cells = []
    for row in rows:
        kind = "" if row.result is None else outcome(row.result).value
        cells.append((row.path, row.before, row.after, row.stage,
                      mode_text(row, kind)))
        if row.result is not None and changes is not None:
            changes.record_sent(
                Patch(row.path, row.before, row.after,
                      f"automix-live:{genre}:{row.stage}", row.label),
                _sent(ctx, row))
    return cells


def record_reverts(window, ctx, rows) -> list:
    ledger = getattr(getattr(window, "changes_panel", None), "ledger", None)
    cells = []
    for row in rows:
        cells.append((row.path, row.before, row.after, row.stage,
                      mode_text(row, "revert")))
        if ledger is not None:
            ledger.reverted.emit(_sent(ctx, row), row.result)
    return cells


def lock_other_writers(window, running: bool) -> None:
    """While automix writes (loop, revert, or a thread still out there), Repair,
    the journal's Send and the Sent ledger's Revert stay dead (W10)."""
    doctor = getattr(window, "pages", {}).get("doctor")
    if doctor is not None:
        doctor.set_controls_enabled(not running)
    changes = getattr(window, "changes_panel", None)
    if changes is not None:
        changes.list.setEnabled(not running)
        changes.ledger.setEnabled(not running)       # Revert / Revert all too


def status_line(loop, ticks: int, rows: int, pending: int) -> str:
    return text("automix.live.status").format(
        state=text(f"automix.live.state.{loop.state.value}"), ticks=ticks,
        rows=rows, pending=pending, locked=len(loop.locked_paths))
