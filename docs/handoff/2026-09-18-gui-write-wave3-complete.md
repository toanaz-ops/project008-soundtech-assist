---
project: PROJECT008-SOUNDTECH-ASSIST
branch: feat/gui-write-wave3
worktree: D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.claude/worktrees/pull-latest-code-continue-4aa165
feature: GUI wave 3 - per-parameter write to a live WING console
phase: GUI3
status: wip
next: real-desk acceptance §9.3 against WING-GIAQUY, ToanAZ's review of 19 pending decisions, then push and open the PR
decisions_pending: 19
date: 2026-09-18
---

# GUI wave 3 — write to a live console, task 14 handoff

**PROGRESS 15/16 — tasks 1–13 and 15 done, task 14 (this file) done. Task 16, the
whole-branch review on the strongest model, has NOT run.**

This is the first wave whose failure mode is a wrong value at a venue rather than a
wrong report on a screen. Nothing in it has touched a real console.

## 1. Quick-locate

- Repo root (main checkout): `D:\DEV CAVE EP3\PROJECT008-SOUNDTECH-ASSIST`
- This worktree: `D:\DEV CAVE EP3\PROJECT008-SOUNDTECH-ASSIST\.claude\worktrees\pull-latest-code-continue-4aa165`
- Branch `feat/gui-write-wave3` at `f56813c`, base `main` at `21fc3fb`.
  `git log --oneline 21fc3fb..HEAD | wc -l` → **26** (27 with this file's commit).
- **The branch is local only.** `git branch -vv` shows no upstream; `git branch -r`
  lists only `origin/main` and `origin/HEAD`. **No PR exists for wave 3** —
  `gh pr list --state all` tops out at #7 (merged 2026-09-17).
- Spec: `docs/superpowers/specs/2026-09-17-gui-write-wave3-design.md` — §2 the
  operator walkthrough, §5 the F/W rulings table, §9.3 the real-desk acceptance
  list, §11 the three open questions. **Its §4 module table is four modules short
  of what shipped** — see D-48.
- Plan: `docs/superpowers/plans/2026-09-17-gui-write-wave3.md`.
- SDD ledger, the source of truth for what shipped and every ruling:
  `.superpowers/sdd/2026-09-17-gui-write-wave3/progress.md`. **`.superpowers/` is
  gitignored** — one `git worktree remove` deletes it, which is why its deferred
  minors were rescued into `docs/tech-debt.md` as D-52 before this file was written.

## 2. The numbers, both measured today

**Baseline, at the base commit `21fc3fb`.** Measured by extracting the commit
read-only into the scratchpad (`git archive 21fc3fb | tar -x -C <scratchpad>/base21fc3fb`)
rather than checking it out — another session may be live in a sibling worktree, and
`pyproject.toml`'s `pythonpath = ["."]` makes an extracted tree run its own code:

```
$PY -m pytest -q -p no:faulthandler --junitxml=<scratchpad>/junit-base-21fc3fb.xml
```
```
tests="1587" failures="0" errors="0" skipped="3"   →  1584 passed / 3 skipped
```

So the wave added **177 tests**. (The SDD ledger's `task-1-report.md` calls 1600 "the
wave's baseline"; it is not — that figure was taken *after* task 1's own thirteen
`net/address.py` tests had landed. 1584/3 at `21fc3fb` is the real one. The last
number recorded for `main` in the ROADMAP, 1580/3 at `dcf897a`, is three merged PRs
older still.)

**Final, at `f56813c`**, run from this worktree:

```
$PY -m pytest -q -p no:faulthandler --junitxml=<scratchpad>/junit-task14.xml
```
```
tests="1764" failures="0" errors="0" skipped="3"   →  1761 passed / 3 skipped
```

**Neither number came off the terminal, and that is not sloppiness — it is D-47.**
Both runs exited 0 and **neither printed a `N passed` summary line**. The plain
run also printed the familiar `Windows fatal exception: code 0x8001010d` C-stack
dump. Measured today: `-p no:faulthandler` silences the dump but **does not** bring
the summary line back, so `--junitxml` is the only reliable way to read this
suite's tally. D-47 has been corrected to say so.

## 3. What shipped

The Doctor page's **Repair** button can now reach a live desk. Exactly one OSC leaf
per transmission (F1) — no `push`, no `node_write`, no multi-parameter packet, not
even inside Revert all.

- **Arming, once per connection** (F4): `ArmWriteDialog` re-queries identity fresh,
  requires an **unticked-by-default** latch reading *"This desk is NOT running a show
  right now."*, and the console's **exact name typed**. Arm dies on Disconnect,
  `LOST`, `ERROR` and quit, and the level selector visibly falls back to Manual.
- **Three apply levels** (F3) on a selector beside the repair area: **Manual** (scene
  only; the journal row's own **Send to console** opens the countdown), **Delayed**
  (Repair opens the countdown), **Immediate** (Repair writes at once, no dialog).
  Delayed and Immediate are greyed until armed.
- **The countdown** (F5): address, the desk's live value, the scene file's expected
  value with a **mismatch warning** when they differ, the new value, a progress bar,
  and **Apply now / +5 s (unbounded presses) / Cancel**. **Expiry is an apply.**
  Cancel leaves the scene edit alone — Undo is the other door.
- **Three outcomes, not two** (F8), each moving the scene differently: matched → the
  leaf takes `after`; clamped → the leaf takes `scene_value(parts, readback)` so
  Doctor re-derives against the desk's truth; **no reply → the leaf is left exactly
  as Repair set it**.
- **The sent ledger** (F7): one row per parameter written this session, with the
  desk-live value captured *before* the write. Per-row **Revert** through the current
  level; **Revert all** in reverse order, sequential, one packet at a time, with a
  `Reverting 3/7` progress line and **Stop** between parameters.
- **Five gates.** Only `CONNECTED`/`WATCHING` (a new `"write"` action in those two
  `_ACTIONS` rows, `live_state.py:119,123`); armed; the dialog or Send button; a
  re-check of both immediately before the confirmation is built (`GateClosed`); and
  `live_write.send` re-querying identity and raising **`DeskChanged`** on a serial
  change before anything reaches the wire.
- **One new persisted key**, `apply_delay` (F6), 3–60, default 5, through
  `state_store` — Settings ▸ *Default apply delay (s)*.
- **`net/` debt rode along** (W9): D-42 **closed** (a cancel-aware pace sleep), D-41
  **partially closed** — the `net/` seam now exists (`take_snapshot` and
  `build_watch_list` both take `schema=`), but the UI has not adopted it.

**The structural rule changed shape.** `tests/test_ui_live_is_read_only.py` was a
blanket ban on `wing_parser/ui/` naming `net.write`. It is now an **allow-list of
exactly one module** — `wing_parser/ui/live_write.py`, matched by `path.name`
**equality**, so a `bus_live_write.py` is still reported. Rule 1 is narrowed there,
not waived: an allow-listed file may bind the write *module*; `from
wing_parser.net.write import push` is still an offence. And **rule 2 — the verb rule
— still runs on the allow-listed file**: only `set` is permitted, and `toggle`,
`node_write` and `push` remain offences in every directory, allow-list included.

## 4. What ToanAZ can run, and what he should see

All from this worktree. `$PY` = `D:\DEV CAVE EP3\PROJECT008-SOUNDTECH-ASSIST\.venv\Scripts\python.exe`.

**The exe.** `dist\wing-ui.exe` was rebuilt today (62.4 MB, onefile). Launched with
`Start-Process`, it was **still alive after 8 s** (pid 56240) — the check that
matters, because `console=False` turns a missing extra into a silent exit 1.

```bash
Start-Process 'dist\wing-ui.exe'
```

Open it, load `user-files\example-Vu.snap`, go to **Doctor** (Ctrl+1). Beside the
repair area: **Apply to console [ Manual ] [ Arm ]**. Open the dropdown — **Delayed
and Immediate are greyed**. That is the honest resting state and needs no console.

**The page screenshots, regenerated from the exe:**

```bash
dist\wing-ui.exe --screenshot dist-shots user-files\example-Vu.snap
```

Exits 0 and writes seven page PNGs plus `diff-b.png` and the `ab-seed.snap` the
Diff page compares against.

**The suite** (read the tally out of the XML, never off the terminal — §2):

```bash
.venv\Scripts\python.exe -m pytest -q --junitxml=dist-reports\suite.xml
```

**The shipped skill set, pinned by name:**

```bash
.venv\Scripts\python.exe -m pytest tests/test_examples.py
```

**What needs the desk — spec §9.3, none of it run.** Against **WING-GIAQUY,
`192.168.128.28`**, from `dist\wing-ui.exe`, **with WING-Edit connected throughout**
(the coexistence requirement is a standing constraint, not a nice-to-have). The list
is in the spec; the six steps in short:

1. Connect → lamp green, identity matches `wing net identity`. Pull → Doctor fills.
   Selector reads Manual, the other two greyed.
2. Arm: the dialog names the desk **with the serial**. A wrong name → Arm stays
   greyed. Latch unticked with the right name → still greyed. Both → Arm enables.
3. Manual: repair a **G8** finding → nothing reaches the desk. Row's Send →
   countdown; **+5 s** three times and watch the remainder grow; Cancel → nothing
   written, WING-Edit unchanged, journal row intact.
4. Delayed: let one **expire** → `sent ✓`, and **WING-Edit shows that send flip to
   PRE**. Another with **Apply now**. Immediate: a third lands with no dialog.
5. Bool normalisation (a `to: false` repair must read `True`/`False`, **never
   `1`/`0`**), mismatch (move the parameter on WING-Edit first), clamp (aim a numeric
   leaf out of range — badge ⚠ and Doctor's finding must reflect what the desk
   actually took), no reply (aim at an address this console lacks — badge ✗).
6. Revert one row; Revert all over five or more rows — reverse order, `3/7`
   progress, **WING-Edit never showing two moving at once**, one countdown per
   parameter in Delayed; Stop mid-run. Then the two refusals: a wrong
   `WING_WRITE_ALLOW_SERIAL`, and unplugging the desk mid-countdown (on expiry
   **nothing is sent**, `gate_closed` shows, selector back to Manual).

## 5. The screenshots — ToanAZ must look at them

Wave 1's gate: **no surface is done until he has.** They are **not committed**
(`dist-shots/` is gitignored, `.gitignore:48`); they go in the PR body.

`D:\DEV CAVE EP3\PROJECT008-SOUNDTECH-ASSIST\.claude\worktrees\pull-latest-code-continue-4aa165\dist-shots\`

From the exe (`--screenshot`), the seven pages: `doctor.png` (102 654 bytes), `overview.png`, `channels.png`, `routing.png`, `diff.png`
(plus `diff-b.png`, the magnitude-bar-off variant), `import_.png`, `console.png`.
**`doctor.png` already carries the wave-3 change**: the *Apply to console / Manual /
Arm* bar, unarmed.

The eight surfaces the exe cannot reach were grabbed from the **real widgets**,
offscreen, against `tests/fake_desk.py`'s `FakeDesk` — no socket — by a throwaway
script, `dist-shots/shoot_write_surfaces.py`, which is **not committed and not under
`wing_parser/`**:

| PNG | bytes | what it shows |
|---|---|---|
| `01-doctor-manual.png` | 176 519 | Doctor in a real `MainWindow`, unarmed: selector **Manual**, button **Arm** |
| `02-doctor-levels-greyed.png` | 2 011 | the selector open — **Delayed and Immediate greyed** |
| `03-doctor-armed.png` | 177 737 | armed: selector **Delayed**, button **Armed: WING-GIAQUY** |
| `04-arm-before-latch.png` | 13 146 | `ArmWriteDialog` with identity landed, latch unticked, **Arm disabled** |
| `05-arm-latched-named.png` | 14 496 | latch ticked and the name typed — **Arm enabled** |
| `06-delayed-mismatch.png` | 14 639 | `DelayedWriteDialog`: desk holds PRE, file expected POST, **the ⚠ mismatch line**, the three buttons |
| `07-changes-dock-badges.png` | 33 152 | `ChangesPanel`: three rows carrying **one ✓, one ⚠, one ✗**, and the ledger below |
| `08-ledger-revert-all.png` | 25 265 | `SentLedger` mid **Revert all** — `Reverting 1/5: /ch/5/send/8/mode`, Stop live |

`08` is a **real run**, not a posed label: `revert_all()` sets the progress line and
hands the first record out before the packet leaves, and the address proves the
reverse order (five rows added `/ch/1..5`, the first reverted is `/ch/5`).

**Look at `07` first.** The ✗ badge renders as a **replacement box** — see D-51.

## 6. Decisions pending a human — 19

Every one is the orchestrator's, made *for* ToanAZ. Nothing here was his.

### 6.1 Three questions that change what gets built (spec §11)

1. **Immediate while `WATCHING`, or only `CONNECTED`?** Default: allowed. Forbidding
   it turns one `frozenset` row into a level-aware gate check.
2. **In Delayed, one countdown for a whole Revert-all batch?** Default: one per
   parameter, because that is what "delayed" asked for. One-for-the-batch is a
   different dialog.
3. **Should arm survive a reconnect to the *same serial*?** Default: no — a dropout
   at a venue is exactly when he should re-confirm which desk he is on.

### 6.2 Fifteen `W…` rulings, each overturnable

W1 write allowed in `CONNECTED` **and** `WATCHING` · W2 `osc_address()` in a new
`net/address.py`, `ce_data`/`$ctl` refused · W3 always `set`, **never `toggle`** ·
W3b int-typed leaves are a known future risk, not a current one · W4 the AST test
becomes an allow-list of one module · W5 each dialog owns its own `CallRunner` for
pre-flight reads, `TIMEOUTS["write"] = 10` · W7 `console.write.*` texts, 200-line
ceilings, no colour literals · W8 one new persisted key and nothing else — no write
log, no remembered arm, no auto-connect · W9 D-41/D-42 ride along · W10 one write
runner, one packet on the wire, queued not dropped · W11 both dialogs
application-modal · W12 Cancel inside a Revert-all **stops the whole run** · W13 a
revert moves the scene back so **the finding reappears**, and the journal patch is
**not** undone · W14 the level cannot change mid-run · W15 a Delayed run is stopped
by the countdown's own Cancel.

The spec's §5 table gives, for each, what changes if he overturns it. **The eight
`F…` rulings are his own** (brainstorm 2026-09-17) and are not in this count.

### 6.3 C1 — the build venv deliberately has no model SDK

`anthropic` and `openai` are **not installed** in `D:\DEV CAVE EP3\PROJECT008-SOUNDTECH-ASSIST\.venv`,
by instruction, so **Settings ▸ Test connection could not be exercised from this
exe**. The spec header of `packaging/wing-ui.spec` says the anthropic SDK is
deliberately *not* excluded from the bundle because Settings performs user-initiated
provider calls — so an exe built from a venv without it ships without it. **Decision
needed:** does the release exe carry the provider SDKs or not?

### 6.4 Seven rulings made during implementation, not in the spec

Recorded in the SDD ledger, listed here because that file is gitignored:

1. **Task 3** — `send()` re-queries identity and raises **`DeskChanged`** on a serial
   change (an addendum to W4 / gate 4's second half).
2. **Task 4** — `live_write.py` hit 220 lines and was split: `ui/write_records.py`
   took `WriteConfirmation`, `SentWrite`, `scene_value`, `Outcome`, `outcome`,
   `settle_scene` and `revert_confirmation`; `live_write.py` kept transport /
   preflight / send and re-exports.
3. **Task 4** — a revert's `desk_before` is `result.readback`, falling back to the
   written value only when the readback is `None`.
4. **Task 11** — the escape hatch: `WriteGate` / `WriteJob` / `GateClosed` moved out
   of `live_wiring.py` into a new `ui/write_gate.py`, re-exported.
5. **Task 11 → 12** — `main_window` built the body (and so `install_write_gate`)
   **before** the changes dock, leaving `send_requested` wired to nothing; the call
   moved into `__init__` after `_build_changes_dock`.
6. **Task 12** — `WriteGate.transport` is a **new seam** the spec did not have, so a
   caller building its own dialog reaches the same desk the gate does instead of
   defaulting past it to `live_write.REAL`. Only `SendRow` reads it.
7. **Task 13** — `apply_result` / `apply_revert` moved to a non-Qt
   `ui/write_apply.py`.

## 7. Known pitfalls — read before touching any of this

- **The editable install points at the MAIN checkout, not the worktree.** Found
  today: `__editable___wing_parser_0_1_0_finder.py` in the shared `.venv` resolved
  `wing_parser` to `D:\DEV CAVE EP3\PROJECT008-SOUNDTECH-ASSIST\wing_parser`.
  Building the exe from this worktree without reinstalling would have **silently
  packaged main's code**, and the exe would have started and looked fine. Fixed with
  `$PY -m pip install -e ".[ui,ingest]"` from this worktree, and verified in
  `build/wing-ui/Analysis-00.toc`, which now names this worktree's
  `wing_parser\ui\write_gate.py`. **The shared `.venv` is now pointed at this
  worktree** — repoint it after the merge, or the main checkout builds this branch.
- **A venv missing an extra makes the exe exit 1 in silence** (`console=False`).
  The tell is UI tests *skipping* in pytest. `packaging/wing-ui-debug.spec` —
  generated by `packaging/make-debug-spec.py`, never hand-edited — builds a console
  variant that prints the traceback.
- **`state_store.normalize` drops a bad value silently.** A non-`int` (or a `bool`,
  which is an `int` subclass) `apply_delay` becomes the default, and any int is
  clamped to 3–60. Correct, and invisible: a hand-edited `ui-state.json` does not
  complain, it just does something else.
- **`save_on_close` spells the key as a literal** (`window_state.py:128-129`, and it is read back at `:27`). The key
  name is written out in `state_store.DEFAULTS`, in `normalize`, in the settings
  dialog and again there. Adding a second persisted key means touching that literal
  too, and forgetting it loses the value on close with nothing logged.
- **`write_delay_dialog.py` is at exactly 200 lines, the ceiling the suite
  enforces** (D-50). The next line added to it fails `test_ui_house_style.py`. The
  plan expected `live_wiring.py` to be the tight file; task 11's split moved the
  pressure, it did not remove it.
- **W3b's int-typed-leaf risk is real and its warning never landed** (D-53). No
  shipped repair descriptor writes an int today, so nothing is broken. The first one
  that does needs the `typetag="i"` path and a test **before** it ships, or it goes
  out as a display string and may select the wrong enum entry silently — the
  read-back compares the same re-expression, so it would pass.
- **`✗` has no glyph in the shipped font** (D-51) and renders as a box. It is the
  badge for the most dangerous outcome.
- **D-47:** the suite's summary line is unreliable. Use `--junitxml`.

## 8. Debt this wave touched

Everything is in `docs/tech-debt.md`; nothing is restated here.

- **Closed:** D-42.
- **Partially closed:** D-41 — the `net/` seam exists, the UI has not adopted it.
- **Corrected:** D-47 — `-p no:faulthandler` and `--junitxml` are not
  interchangeable.
- **Opened:** D-48 (the spec's §4 table is four modules short), D-49 (`SentWrite`
  carries both spellings of a leaf, deliberately), D-50 (the 200-line ceiling),
  D-51 (missing glyphs on two badges), D-52 (the wave's ten deferred minors,
  rescued out of gitignored scratch), D-53 (W3b's missing warning), D-54
  (`dist-reports/` untracked but not gitignored).

## 9. Verification commands

Run from this worktree root, snapshot at `f56813c` plus this file's commit:

```
git log --oneline 21fc3fb..HEAD | wc -l                 # 26, before this commit
git status --short                                      # dist-reports/ only (D-54)
git branch -vv | grep gui-write                         # no upstream: not pushed
gh pr list --state all --limit 3                        # nothing for wave 3
wc -l wing_parser/ui/write_delay_dialog.py              # 200 (D-50)
grep -o "pull-latest[^']*write_gate.py" build/wing-ui/Analysis-00.toc
                                                        # this worktree's copy
ls dist-shots/*.png                                     # 8 write surfaces + 8 exe pages
.venv\Scripts\python.exe -m pytest -q --junitxml=dist-reports\suite.xml
.venv\Scripts\python.exe -m pytest tests/test_examples.py
```

## 10. What the next session should do first

1. **Task 16 — the whole-branch review on the strongest model.** It has not run, and
   ROADMAP §7 records that it has earned its cost four cycles running, every time by
   catching a defect spanning files no single task's diff contained. This wave writes
   to real audio hardware. Do not skip it.
2. **Put the eight write-surface PNGs in front of ToanAZ.** Wave 1's gate.
3. **Get §9.3 run against WING-GIAQUY** with WING-Edit connected throughout.
4. **Then** push, open the PR, let CI go green, and let ToanAZ click Merge —
   `docs/git-workflow.md`.

Wave 4 is not scoped. Whether there is one, and what it contains, is a question for
ToanAZ (ROADMAP §5.9).

## 11. Lessons

`memory/MEMORY.md` gained one entry at the bottom, in Vietnamese — what shipped, the
measured suite number, what remains pending, and the editable-install trap. The
2026-08-24 entry's "only `net set/toggle/push/get` are CLI-only" note was updated
rather than left to mislead: wave 3 put the *write* on the UI, but not those four
commands, and they stay CLI-only on purpose.
