# Sub-project C2 — live watch — outcome and residuals

**Date:** 2026-08-22 · **Branch** `claude_desk/project-capabilities-next-steps-8ec61c`,
from `2f3d7a7` · **1055 tests passing, 1 skipped** (FastMCP, by design)

## What shipped

**`wing net watch <ip>`** reports what changes on a running console, by
**polling** — it subscribes to nothing, so it runs alongside WING-Edit,
Companion or any other OSC client without displacing them. That was ToanAZ's
hard requirement (`"cần song song không đá nhau"`), and it is what selected the
mechanism: only one OSC subscription exists console-wide and it expires after
10 s, so subscription cannot satisfy it at all.

- New package `wing_parser/net/watch/`: `list.py`, `events.py`, `poller.py`,
  and `data/watchlist.yaml`.
- CLI: `wing net watch <ip> [--json] [--interval SECONDS] [--until SECONDS]`.
- Seventh skill: `skills/wing-watch/`. (`wing-net` landed in the C/D cycle, so
  the shipped set is analyze, channel, diff, doctor, net, routing, watch —
  named, not counted, in `tests/test_examples.py`.)

**Three closures ToanAZ approved.**

- **MCP gained `show` and `live`** on `analyze`, `routing`, `channel` and
  `doctor`, by delegating to the CLI's `_load` instead of each tool calling
  `WingScene.load` itself. Closes the open question carried since the G1
  handoff (`2026-08-21-next-session-prompt.md` §5.4).
- **`diff` reads a console on either side** — `--live-before IP` /
  `--live-after IP`.
- **Five real scenes are now a test corpus**, with pinned finding counts.

**One shipped defect fixed, found mid-cycle.** See §2.

## 2. The defect that was not on the plan

`wing doctor --live <an-address-with-no-console>` printed **`No findings.`** and
exited 0. `analyze --live` on the same address printed `0 channels, 0 buses`.

To a working engineer, "No findings" reads as *your desk is clean*. It meant
*I never reached your desk* — and `doctor` is the command most likely to be
trusted at face value in the last minutes before doors.

**`net/snapshot.py` was never at fault and was not changed.** `take_snapshot`
already returns `unresolved_nodes` and `unresolved_leaves`, and its own
docstring states the contract it honours: a caller "must be able to tell
'empty' apart from 'incomplete'". `commands._load` read only `.raw` and threw
the report away. Nothing raised, because OSC is UDP — an unreachable host
produces no connection-level error, so every leaf simply timed out into
`unresolved` and the `except (OSError, ValueError)` never fired.

The fix distinguishes three cases where there was one:

| | behaviour |
|---|---|
| nothing came back at all | error naming the host **and both counts**, return `None`, caller exits 1 |
| something came back, not all | build the scene, warn on stderr saying how much is missing |
| everything came back | **say nothing** — a warning on every clean read teaches the reader to skip it |

`docs/probes/probe11_unreachable_console.py` reported the original defect
and now demonstrates the fix: post-fix it takes the `scene is None`
branch and prints "Nothing to fix here."

**It was found by typing a wrong IP while verifying an unrelated task**, not by
reading code. Two independent traces then agreed on the cause.

## 3. NOT proven — do not write these up as done

Both are spec §4.4 acceptance tests, and both are still open. §2.6 of the
design doc records why silence is not evidence here.

1. **That polling detects a change** (§2.6(2)). `wing net watch` was run against
   the lab rack for 240 s. It built the list correctly —
   `watching 220 leaves (40 ch, 16 bus, 4 main, 8 mtx, 16 dca)`, no unresolved
   warning, exit 0 — and 220 matches `probe9_stripset.py`'s prediction exactly.
   But **zero change events**, because nobody moved a control during the
   window. The **loop** is proven against a real console. **Detection is not.**
2. **That it coexists with WING-Edit** (§2.6(3)). Not run — it needs a human
   driving the desk from WING-Edit while the watcher runs. This is the direct
   test of ToanAZ's hard requirement, so it matters more than its size.

Both close in one sitting: start the watcher, move one fader from WING-Edit.

```powershell
python -m wing_parser.cli net watch 192.168.128.28 --until 120
```

## 4. Residuals — what is genuinely left

The final whole-branch review triaged these. Everything it ruled must-fix was
fixed in the fix wave (§4.1); what remains is below it.

**Still open, deferred deliberately:**

1. **File lengths.** `wing_parser/cli/commands.py` is **257** lines and
   `wing_parser/cli/net_commands.py` is **258**, both past the ~200 norm.
   `commands.py`'s live branch is a clean `_load_live` extraction candidate.
   The reviewer's judgement — which I follow — is that an extraction belongs in
   its own commit rather than stacked onto a behaviour fix in the same function.
2. `poller.sample()` swallows `ValueError` from `codec.leaf_value`, so a
   malformed reply is indistinguishable from an absent one, with no diagnostic.
   Triaged as able to stand: no watched leaf can currently produce it.
3. No test covers `--json` combined with a network failure or `KeyboardInterrupt`.
   Safe by inspection today — both prints are structurally stderr — but an
   unguarded future edit would not be caught.
4. In `--json` mode an interrupted run emits nothing marking a clean stop,
   unlike text mode. A format decision with no consumer today.

### 4.1 Fixed in the fix wave — do not go looking for these

The final review found nine, and the per-task reviews had deferred three more.
All twelve are closed; they are listed so a reader of an earlier draft of this
document does not chase them.

- **The third cross-file defect this project has shipped in three cycles.**
  MCP's `_scene` captured `_load`'s stderr and consulted it **only** when the
  load returned `None`. It was written when `_load` had two outcomes. Four
  commits later, §2's fix gave `_load` a third — a partial read *warns and still
  returns a scene* — and that warning was captured and thrown away. So an MCP
  session saw a partial console read as complete: the same harm §2 set out to
  fix, inverted. Neither task's diff held both halves.
- A measurement nobody made, in two user-facing strings: `--interval`'s help and
  the `wing-watch` skill both claimed "a 208-leaf round measured 22 ms". §2.4's
  22 ms row is the **120-leaf** list; the only 208-leaf run paces itself at
  0.1 s and cannot show a sub-0.1 s round.
- MCP `doctor(show=...)` dropped the show-anomaly report the CLI prints.
- `skills/wing-diff/SKILL.md` still described a files-only command.
- `tools.channel`'s docstring omitted `live` — and an MCP docstring *is* the
  interface.
- Three places asserted that subscribing would take the slot **from WING-Edit**.
  What is measured is that one subscription exists console-wide; that WING-Edit
  holds it is §2.6(3), still unverified.
- `net/watch/list.py` cited "S2.2" twice in consecutive lines meaning two
  different documents.
- `events._shown()`'s docstring said "address" where it returns `strip`.
- Two smaller ones: `net watch` ignored the module's `OSC_PORT` convention, and
  `diff` read a live second side even after the first side had already failed.

## 5. Open questions — carried forward unchanged

From `2026-08-21-next-session-prompt.md` §5. **§5.4 (MCP `show`/`live`) is now
closed**; the rest stand:

1. The limiter `dyn.mdl` token — needs the **complete** list of limiter-capable
   models ToanAZ would use. Closed as underivable offline.
2. Whether G10's suppression is his standing practice.
3. `expects:` accepts pattern-derived kinds only. Latent today.
4. Whether a gate's `1:3` ratio should be modelled as a number.

New this cycle:

5. **Should any advisory rule read `$fdr` instead of `fdr`?** Design doc §2.2
   establishes the two differ: `fdr` is the strip's own position (intent),
   `$fdr` is the value after DCA and mute-override fold in (result). A rule
   about what the audience actually hears may want the second. This is
   ToanAZ's call about his own judgement.
6. **Metering needs a second transport.** Measured (§2.3): there is no meter
   anywhere in the OSC tree, and `/$stat/ppm` is a setting that did not move
   across 20 reads. Metering lives on the native UDP channel, which is the
   doorway to sub-project E and a spec of its own.

## 6. What this cycle taught

- **Every task's brief contained at least one real defect, and the implementer
  found it.** A test answered by a fixture it never mentioned, so it asserted
  nothing. A docstring claiming `$name` exists everywhere when `/dca/N` has
  none. A spec naming `--for`, which cannot be an argparse dest because
  `args.for` is a syntax error. A helper that discarded the error detail a
  pre-existing test depended on. None was visible on re-reading; each surfaced
  when someone *executed* the brief.
- **Three separate tests turned out to assert nothing, and all three were
  green.** Green is the best possible camouflage, because nobody audits a
  passing test. The only reliable check is to ask "if this broke, would it go
  red?" and then *break it*. Each was proved by reverting the production line
  and capturing the failure.
- **The whole-branch review earned its cost for the third cycle running,**
  and in the same shape every time: a defect spanning two files that no
  single task's diff contained. This time MCP threw away a warning that a
  later task had only just started emitting. A per-task review cannot see
  it, by construction -- both halves were correct when written.
- **The most valuable find came from a typo.** `10.0.0.1` was typed to smoke-test
  `diff --live`, and the impossible output — 76 differences against a console
  that does not exist — exposed a shipped defect that had survived a full
  design, plan and review cycle.
- **A citation that does not name its file is not a citation.** "design doc
  S2.2" was ambiguous between two design docs whose §2.2 sections say different
  things, and it slipped past me twice — once in a probe whose entire purpose
  was citation integrity.
- **Correct code with a false description is the recurring shape here.** It
  happened to `read_labels` this cycle and to Q6 in the G1 cycle. No test runs a
  docstring, so a wrong explanation survives every green suite and misleads the
  next reader indefinitely.

## 7. Environment

Unchanged from `2026-08-21-next-session-prompt.md` §8, plus two reminders that
cost time this cycle:

- **Never put backticks inside `git commit -m`** — the shell evaluates the
  enclosed word and silently deletes it from the message. Use `git commit -F -`
  with a heredoc. This is already in the standing notes and still caught me.
- **Redirecting a Python script's output needs `python -u`** — buffered stdout
  leaves the log file empty until the process exits, which reads exactly like a
  hang.
- `docs/probes/` now holds eleven scripts with a README mapping each to the
  claim it supports. A measurement nobody can re-run is not evidence.
