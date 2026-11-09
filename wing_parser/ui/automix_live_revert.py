"""Revert automix, worker side (wave 12 phase 2, AM-55/AM-56): no Qt.

Puts each touched leaf back to its pre-automix desk value, last touched
first -- but only a leaf that is still where automix left it. A leaf the
operator locked or moved since is theirs now and is skipped, never
clobbered. Every row sent is kept (even if this thread is abandoned on a
timeout), and a mid-way fault returns what was already done.
"""

from __future__ import annotations

from wing_parser.net.address import osc_address
from wing_parser.ui import live_write
from wing_parser.ui.automix_live_worker import WriteRow


def revert_all(runner, locked) -> None:
    from wing_parser.automix.live_loop import differs

    ctx = runner.ctx
    runner.skipped, runner.revert_error = [], ""
    try:
        for path in reversed(list(runner.originals)):
            if ctx.abort.is_set():
                runner.revert_error = "stopped"
                return
            target = runner.originals[path]
            last = runner.last_written.get(path)
            if target is None:                       # the desk never described it
                runner.skipped.append((path, "unknown_original"))
            elif path in locked:
                runner.skipped.append((path, "locked"))
            else:
                now = ctx.transport.read(ctx.host, path)
                if now is None:                      # kept: a later revert may retry
                    runner.skipped.append((path, "unread"))
                    continue
                if last is None or not differs(last, now, runner.tolerance_for(path, last)):
                    conf = live_write.confirmation_for(
                        ctx.host, osc_address(path), target, ctx.identity, last)
                    result = live_write.send(conf, ctx.transport)
                    stage, label = runner.meta.get(path, ("", path))
                    runner.add_revert_row(WriteRow(path, last, target, stage, label, result))
                else:
                    runner.skipped.append((path, "changed"))
            runner.originals.pop(path, None)         # reverted, or not ours to revert
    except live_write.DeskChanged as exc:
        runner.revert_error = str(exc)
        ctx.abort.set()
    except Exception as exc:  # noqa: BLE001 - rows already sent stay recorded
        runner.revert_error = str(exc)
