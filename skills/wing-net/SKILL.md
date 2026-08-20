---
name: wing-net
description: Use when asked to read from, write to, or analyse a Behringer WING console over the network rather than from a .snap file — connecting to a live desk by IP, taking a snapshot, changing a parameter, or running the advisory against the desk as it currently stands.
---

# Talking to a live WING console

Two surfaces. Use `--live` when you want an existing analysis against a
running desk; use `wing net` when you want the console itself.

```bash
python -m wing_parser.cli doctor --live 192.168.128.28
python -m wing_parser.cli analyze --live 192.168.128.28
python -m wing_parser.cli routing --live 192.168.128.28
python -m wing_parser.cli channel --live 192.168.128.28 11
```

`--live <ip>` and a file argument are mutually exclusive. Everything
downstream is identical to reading a file, so `--profile` and `--show`
work with `--live` exactly as they do with a `.snap`.

```bash
python -m wing_parser.cli net identity 192.168.128.28
python -m wing_parser.cli net snapshot 192.168.128.28 -o today.snap
python -m wing_parser.cli net get 192.168.128.28 /ch/1/fdr
python -m wing_parser.cli net set 192.168.128.28 /ch/1/fdr -6.0 --confirm
python -m wing_parser.cli net toggle 192.168.128.28 /ch/1/mute --confirm
python -m wing_parser.cli net push 192.168.128.28 show.snap --confirm
```

## Writing is dry-run until you say otherwise

`set`, `toggle` and `push` send **nothing** without `--confirm` — they
print what they would send and stop. With `--confirm` they first echo the
console's name, model and serial, so it is visible which desk is about to
change.

**Always read the value back.** The command does this for you and reports
a mismatch, because an out-of-range write is **silently clamped and still
answers OK**: `fdr=999` stores `+10.0`. A success reply is not proof the
value landed.

Set `WING_WRITE_ALLOW_SERIAL` to a console's serial to refuse writes to
any other desk. Unset, no pin applies.

## Reading the output

`net get` prints the display text and the native value, and they are not
always the same number — that is deliberate, not noise. A float's display
is rounded (`0.9979702234268188` shows as `1.00`), and an integer's
native value is often a **0-based index** rather than the value
(`/io/in/CRD/1/col` reads native `0` where the file holds `1`). A snapshot
takes the correct one per type; `net get` shows you both.

`net snapshot` reports how many leaves it read and how many were
unresolved. A whole console is around 25 000 leaves and takes a few
seconds. **Unresolved should be zero** — if it is not, say so rather than
treating the scene as complete.

`net push` reports three outcomes and they mean different things:

- **landed** — written and verified
- **mismatched** — written but read back different. A real problem.
- **absent** — the leaf does not exist on this console. Usually hardware:
  a rack with no StageConnect device has no `/io/in/SC/*` at all. Not a
  failure.

## Gotchas

**An OSC address starts with `/`, and Git Bash rewrites that into a
Windows path** — `/ch/1/fdr` silently becomes `C:/Program Files/Git/ch/1/fdr`
and the command reports no reply. Use PowerShell, or quote and prefix the
argument. PowerShell has no such problem.

**A console holds only one OSC subscription at a time**, so a tool that
subscribes takes it from whatever had it. This subsystem never
subscribes, so it cannot steal WING-Edit's connection — but that is why
it reads by polling rather than listening.

**The scene a console reports is the scene it currently has.** A node's
parameters change with its model: a `dyn` block set to `GATE` exposes
different keys than one set to `COMP`. The shape is therefore re-read on
every snapshot and never cached.

## When a console is not reachable

Every network failure prints `error: <message>` and exits non-zero. A
desk that is switched off is the normal case, not a crash — say so
plainly and suggest checking the IP with `net identity` first.
