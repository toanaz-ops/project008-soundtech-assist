---
project: PROJECT008-SOUNDTECH-ASSIST
branch: feat/gui-write-wave3
worktree: D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.claude/worktrees/pull-latest-code-continue-4aa165
feature: GUI wave 3 - per-parameter write to a live WING console
phase: GUI3
status: wip
next: PR #8 open (https://github.com/toanaz-ops/project008-soundtech-assist/pull/8), CI pending; ToanAZ: look at the 16 screenshots, run 9.3 on WING-GIAQUY, rule on 19 decisions, then Merge
decisions_pending: 19
date: 2026-09-18
updated: 2026-09-18 (task 16 whole-branch review + its fixes)
---

# GUI wave 3 — write to a live console, task 14 handoff

**PROGRESS 16/16 — tasks 1–13, 15 and 14 (this file) done. Task 16, the
whole-branch review on the strongest model, HAS now run; its nine findings are
fixed and §12 below records what changed.**

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

**Task 14's number, at `f56813c`**, run from this worktree:

```
$PY -m pytest -q -p no:faulthandler --junitxml=<scratchpad>/junit-task14.xml
```
```
tests="1764" failures="0" errors="0" skipped="3"   →  1761 passed / 3 skipped
```

**Final, after task 16's fixes.** `f8ed487` (this file's own commit) added no
tests, so `1761 / 3` is also the review's baseline. The four fix commits add
**17 tests**:

```
$PY -m pytest --junitxml=dist-reports/suite.xml -p no:faulthandler
```
```
tests="1781" failures="0" errors="0" skipped="3"   →  1778 passed / 3 skipped
```

**One caveat, and it is D-52 item 6, not a regression.** Under
`QT_QPA_PLATFORM=offscreen` the same run is **1777 passed / 1 failed / 3 skipped**:
`test_ui_state_store.py::test_geometry_and_last_page_survive_close_and_reopen` fails
there and **only** there (`$PY -m pytest tests/test_ui_state_store.py` → 31 passed on
the real platform). It was failing that way before this wave.

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
exactly one module** — `wing_parser/ui/live_write.py`, matched on the path
**relative to the scan root** (task 16: `path.name` would have handed the same
rights to any `ui/<sub>/live_write.py`), so a `bus_live_write.py` is still
reported. Rule 1 is narrowed there,
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
   leaf out of range — badge `!` and Doctor's finding must reflect what the desk
   actually took), no reply (aim at an address this console lacks — badge `×`).
   **The badge marks changed at task 16** (D-51): `✓` / `!` / `×`, all three of
   which the vendored font can actually draw.
6a. **New at task 16, and worth doing on the desk:** aim a repair at an address
   the console lacks so the pre-flight read gets no answer, let it write anyway, and
   check the resulting ledger row — its **Revert button must be greyed** with the
   tooltip *"The desk never said what it held before…"*, and **Revert all must step
   over it** and say so. Before the fix that row's Revert put the literal string
   `None` on the wire.
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

**`06`, `07` and the exe pages are now STALE** (task 16, D-51): the badge marks
are `✓` / `!` / `×` and the countdown's mismatch line leads with `!`. Re-run
`dist-shots/shoot_write_surfaces.py` and `dist\wing-ui.exe --screenshot dist-shots
user-files\example-Vu.snap` before putting anything in front of ToanAZ. The point
of D-51 was always what the operator sees, so the font check alone does not close
the screenshot gate.

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
  enforces** (D-50), and it is back at exactly 200 after task 16's fix — which was
  paid for by moving the "somebody moved the desk" line out to
  `write_records.mismatch_line`, not by dropping a guard. `changes_ledger.py` is now
  198. The next line added to either fails `test_ui_house_style.py`. The plan
  expected `live_wiring.py` to be the tight file; task 11's split moved the
  pressure, it did not remove it.
- **`write_delay_dialog` must NOT import from `live_wiring`** (fixed at task 16).
  `live_wiring` → `write_router` → `write_delay_dialog` is a cycle, and it bit
  whenever this module was imported first: running its own test file alone raised
  `ImportError`. Take `GateClosed`/`WriteJob` from `write_gate` directly, which is
  what `write_router` already documents doing.
- **W3b's int-typed-leaf risk is real** — the warning **landed at task 16**
  (D-53 closed): head of `wing_parser/edit/data/repairs.yaml` and beside `KINDS` in
  `wing_parser/edit/repairs.py`. No shipped repair descriptor writes an int today,
  so nothing is broken. The first one that does needs the `typetag="i"` path and a
  test **before** it ships, or it goes out as a display string and may select the
  wrong enum entry silently — the read-back compares the same re-expression, so it
  would pass.
- **Marks in `texts_write.py` are limited to what the VENDORED font carries**
  (D-51 closed at task 16): `✓` U+2713, `×` U+00D7 and plain `!`. U+26A0 and U+2717
  are **not** in IBM Plex Sans; they came back from a per-machine Windows fallback
  or, on the no-reply badge, as a replacement box. `test_ui_texts.py` fails if either
  reappears anywhere in `WRITE_TEXTS`.
- **A ledger row whose `desk_before` is `None` cannot be reverted** and three
  separate places now say so (task 16, CRITICAL 1). If a future path needs to revert
  one, the answer is to READ the desk again, never to send the record's `written`
  value back as if it were the old one.
- **D-47:** the suite's summary line is unreliable. Use `--junitxml`.

## 8. Debt this wave touched

Everything is in `docs/tech-debt.md`; nothing is restated here.

- **Closed:** D-42, and (at task 16) D-51 and D-53.
- **Partially closed:** D-41 — the `net/` seam exists, the UI has not adopted it.
- **Corrected:** D-47 — `-p no:faulthandler` and `--junitxml` are not
  interchangeable.
- **Opened:** D-48 (the spec's §4 table is four modules short), D-49 (`SentWrite`
  carries both spellings of a leaf, deliberately), D-50 (the 200-line ceiling),
  D-51 (missing glyphs on two badges — **closed at task 16**), D-52 (the wave's ten
  deferred minors, rescued out of gitignored scratch; items 8 and 9 are now partly
  answered by task 16's fixes), D-53 (W3b's missing warning — **closed at task 16**),
  D-54 (`dist-reports/` untracked but not gitignored).

## 9. Verification commands

Run from this worktree root, snapshot after task 16's four fix commits:

```
git status --short                                      # dist-reports/ only (D-54)
git branch -vv | grep gui-write                         # no upstream: not pushed
gh pr list --state all --limit 3                        # nothing for wave 3
wc -l wing_parser/ui/*.py | sort -n | tail -3           # nothing over 200 (D-50)
grep -n "26a0\|2717" wing_parser/ui/texts_write.py      # nothing (D-51)
grep -n "typetag" wing_parser/edit/data/repairs.yaml    # the W3b note (D-53)
grep -o "pull-latest[^']*write_gate.py" build/wing-ui/Analysis-00.toc
                                                        # this worktree's copy
ls dist-shots/*.png                                     # 8 write surfaces + 8 exe pages
.venv\Scripts\python.exe -m pytest -q --junitxml=dist-reports\suite.xml
.venv\Scripts\python.exe -m pytest tests/test_examples.py
```

## 10. What the next session should do first

1. **Task 16 has run** and earned its cost a fifth time: it found a CRITICAL that
   put the literal string `None` on the wire, and a modal dialog that could not be
   dismissed. §12 records all nine findings. What is left is a **fresh pair of eyes
   on the fixes themselves** — nobody has refuted them yet.
2. **Regenerate and put the write-surface PNGs in front of ToanAZ.** Wave 1's gate,
   and `06`/`07` are stale after the badge change — see §5.
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

## 12. Task 16 — the whole-branch review, and what it changed

The review ran over the whole branch on the strongest model. Nine findings, all
fixed, in four commits on `feat/gui-write-wave3`. Every behavioural change was
driven by a test written red first; each is named below.

**Baseline 1761 passed / 3 skipped (`f8ed487`) → 1778 passed / 3 skipped.**

### CRITICAL 1 — Revert could put the string `None` on the wire

A pre-flight read that fails or goes unanswered leaves `SentWrite.desk_before=None`
(`write_router.ImmediateWrite._write` writes anyway, deliberately — F5's "admit
ignorance" rule applies to the SCENE, not to the send). `LedgerRow` had no guard, so
that row's **Revert** reached `plan_write` with `after=None` and `write.set`'s
default typetag re-expressed it as the display string `"None"` — `,s "None"` on the
wire. The reviewer proved it end to end on `FakeDesk`.

Three locks now: the row's button is **disabled with a tooltip**
(`console.write.revert_unknown`); **Revert all leaves such rows out** of the run and
reports how many it skipped (`console.write.revert_skipped`); and `route_revert`
**raises `ValueError`** if handed one anyway, before gate 2 is even asked.
Tests: `test_a_row_the_desk_never_described_cannot_be_reverted`,
`test_revert_all_skips_the_row_the_desk_never_described`,
`test_route_revert_refuses_a_record_the_desk_never_described`.

### IMPORTANT 2 — a refused countdown could not be dismissed

`_apply`'s gate-4 branch set `_settled`, emitted `failed` and **returned without
closing**; `_cancel` returned early on `_settled`, so Cancel did nothing; `_failed`
had the same shape. The dialog is `ApplicationModal`, so a desk that dropped
mid-countdown left Apply, Cancel and Escape all dead and the whole app unreachable —
at a venue, a force-quit. Both paths now `reject()` after emitting `failed`, and
`_cancel` gates on `_sent` (a packet really on the wire) rather than `_settled`.
Tests: `test_a_gate_four_refusal_closes_the_countdown`,
`test_a_refused_write_closes_the_countdown_too`,
`test_cancel_is_inert_only_while_a_packet_is_actually_on_the_wire`.

Two things fell out of touching that file: `write_delay_dialog` now takes
`GateClosed`/`WriteJob` from `write_gate` instead of `live_wiring` (the cycle
`live_wiring → write_router → write_delay_dialog` made the module unimportable
first), and the mismatch line moved to `write_records.mismatch_line` to pay for the
new guard inside the 200-line ceiling.

### IMPORTANT 3 — an error advanced a Revert-all run instead of ending it

`on_error=lambda _exc: self._step_done(None, None)` walked on to the next row. Every
remaining row needs the same connection that just died; in **Delayed** that is one
modal countdown stacked per row, all doomed. `_step_failed` now stops the queue,
names the error in the progress line (`console.write.revert_failed`) and lets
`_end_run` emit `run_finished` exactly once.
Test: `test_a_gate_that_closes_mid_run_stops_it_instead_of_advancing`.

### IMPORTANT 4 — three holes in the structural write-path scan

`tests/test_ui_live_is_read_only.py` rule 2 keyed its binding table on "the import
path starts with `wing_parser.net`", so **`from wing_parser import net`** (binds off
the package) and **`import wing_parser`** (binds only the top name) both bound
nothing, and `net.write.push(...)` walked past rules 1 and 2 untouched. The
allow-list also keyed on `path.name`, which would have handed the one door's rights
to any `ui/<sub>/live_write.py`.

The table now binds anything under `wing_parser`; `_net_target` rebuilds the dotted
path an attribute chain spells before deciding, so both shapes resolve to
`wing_parser.net.write` while `wing_parser.config.set(...)` stays innocent; a `Call`
in the chain still falls back to the leftmost binding, so
`client.WingClient(host).set(...)` is caught exactly as before. The allow-list is now
the path relative to the scan root. Five planted self-tests, including the two "and
this must NOT be reported" halves. **`getattr(write, "push")` is documented as the
remaining blind spot** — both scans read `ast.Attribute`/`ast.Name`.

### IMPORTANT 5 — the revert value rule existed twice, and the copies disagreed

`write_records.revert_confirmation` held the ruling (`desk_before = readback`,
falling back to `written` when the readback is `None`) and **nothing in production
called it**. `route_revert` built its own `Patch` with `before=record.result.readback`
and no fallback, so a silent send made the countdown read *"The scene file expected:
None"*. The rule is now one helper, `write_records.desk_now`, used by `route_revert`;
`revert_confirmation` **was deleted** along with its two tests, which moved to
`desk_now`. (Of the ruling's two options — use it or delete it — delete was right:
even after the refactor nothing would have called it.)
Tests: `test_desk_now_is_the_read_back_the_send_actually_got`,
`test_desk_now_falls_back_to_written_when_the_send_got_no_reply`,
`test_a_revert_countdown_shows_what_the_desk_holds_now_not_none`.

### MINOR 6 — D-51 closed: badges the shipped font can draw

`⚠` → `!` and `✗` → `×` on the two badges, and `⚠` → `!` on the countdown's mismatch
line. Words unchanged. `test_ui_texts.py` now fails if U+26A0 or U+2717 reappears
anywhere in `WRITE_TEXTS`, and pins the three distinct marks.
**The screenshots are stale because of this — see §5.**

### MINOR 7 — the Doctor page's Arm bypassed the gate's transport

`arm_now(gate, self.window())` passed no `transport=`, so `ArmWriteDialog` fell back
to `live_write.REAL`: the one call site in the app where a fake gate would have
opened a real socket. `_doctor`'s gate in the tests also moved off `timeout=0`, which
`CallRunner` reads as a zero-second budget.
Test: `test_arm_from_the_doctor_page_uses_the_gates_own_transport`.

### MINOR 8 — `WriteQueue.clear()` was dead; it is now what a closing gate calls

Of the ruling's two options, the behaviour was chosen over the deletion. A dropped
desk left queued jobs in the deque with **neither callback ever run**, which freezes
whatever was waiting on them — a Revert-all run stalls on the row that died.
`clear()` hands the dropped jobs back and `WriteGate.close()` gives each one
`GateClosed`. The in-flight write is untouched; nothing can un-send a packet.
Test: `test_closing_the_gate_tells_every_queued_write_it_will_never_go`.

### MINOR 9 — D-53 closed: W3b's warning reached the data

At the head of `wing_parser/edit/data/repairs.yaml` and beside `KINDS` in
`wing_parser/edit/repairs.py`: an int-typed (schema-index) `to:` needs the `,i`
typetag path through `write.set` **and a test asserting the packet's typetag** before
it may ship.

### What task 16 did NOT do

- **MINOR 10** (the ledger line reference) was the controller's own file.
- **The screenshots were not regenerated** and the exe was not rebuilt. D-51 is
  closed on the strings; the gate is still what ToanAZ sees.
- **§9.3 against a real desk is still unrun.** Nothing here changes that, and
  step 6a above is a new item for it.
- **Nobody has refuted these fixes.** A fresh pair of eyes on the four commits is
  the next thing owed.
