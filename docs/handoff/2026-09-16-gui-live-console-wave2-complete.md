---
project: PROJECT008-SOUNDTECH-ASSIST
branch: feat/gui-live-console-wave2
worktree: D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.claude/worktrees/feat-gui-live-console-wave2
feature: GUI wave 2 - live console page (read-only)
phase: GUI2
status: wip
next: merge PR #1 then PR #2, #3, #4 on GitHub; then real-desk acceptance §9.3
decisions_pending: 15
date: 2026-09-16
---

# GUI wave 2 — live console page, task 17 handoff

**PROGRESS 18/18 — tasks 1–17 done · task 18 whole-branch review done, its 10-item fix list applied 2026-09-16 (see §9)**

## 1. Quick-locate

- Repo root (main checkout): `D:\DEV CAVE EP3\PROJECT008-SOUNDTECH-ASSIST`
- This worktree: `D:\DEV CAVE EP3\PROJECT008-SOUNDTECH-ASSIST\.claude\worktrees\feat-gui-live-console-wave2`
- Branch: `feat/gui-live-console-wave2`, stacked on `fix/ui-debt-wave1b-leftovers`. Task 17 wrote
  this file at `f88a460`; task 17's own commit (`764609f`) and then the seven commits of the task-18
  fix dispatch landed after it, the last of them this update — `git log --oneline ac39cfa..HEAD |
  wc -l` gives **39**.
- Nothing after `f88a460` is pushed: `git branch -vv` shows the branch ahead of
  `origin/feat/gui-live-console-wave2`.
- `git status --short` is clean. `packaging/wing-ui-debug.spec` is generated output and is now
  gitignored (D-46 closed), so it no longer sits there waiting for a careless `git add -A`.
- Pull requests, from `gh pr list --state all` (all four OPEN):
  | PR | Title | Base from Head |
  |---|---|---|
  | [#1](https://github.com/toanaz-ops/project008-soundtech-assist/pull/1) | fix(ui): close wave-1b leftovers D-24, D-29, D-30, D-31 | `main` from `fix/ui-debt-wave1b-leftovers` |
  | [#2](https://github.com/toanaz-ops/project008-soundtech-assist/pull/2) | chore(ci): GitHub Actions test workflow | `fix/ui-debt-wave1b-leftovers` from `chore/github-workflow` |
  | [#3](https://github.com/toanaz-ops/project008-soundtech-assist/pull/3) | docs: GUI wave 2 design spec + implementation plan | `main` from `docs/gui-live-console-wave2-plan` |
  | [#4](https://github.com/toanaz-ops/project008-soundtech-assist/pull/4) | feat(ui): GUI wave 2 — live console page (read-only) | `fix/ui-debt-wave1b-leftovers` from `feat/gui-live-console-wave2` |
  Stacking: PR #1 is the root (targets `main`); PR #2 and PR #4 both target PR #1's branch, so PR #1
  must merge first or their diffs keep including PR #1's commits. PR #3 (the design doc) targets
  `main` directly and is independent of the stack.
- Spec: `docs/superpowers/specs/2026-09-15-gui-live-console-wave2-design.md` (incl. `## Deviations
  recorded 2026-09-16` — read this before trusting the body above it literally).
- Plan: `docs/superpowers/plans/2026-09-15-gui-live-console-wave2.md`.
- SDD ledger (source of truth for what shipped): `.superpowers/sdd/2026-09-15-gui-live-console-wave2/progress.md`.

## 2. Baseline measured now

Baseline, measured by Task 1 on the wave's own first commit (not re-run by me — checking out
`ac39cfa` in a second location was judged not worth the risk to this worktree's state):
```
$PY -m pytest
1462 passed, 3 skipped, 2 warnings in 138.78s (0:02:18)
```
at `ac39cfa`. Source: `.superpowers/sdd/2026-09-15-gui-live-console-wave2/task-1-report.md`,
"Full-suite baseline (step 4)". (The wave-1 figure of 1433/3 at `04db887` is older still — not the
baseline for this wave.)

Task 17's own measurement, at `f88a460`:
```
".venv/Scripts/python.exe" -m pytest -q --junitxml=<scratchpad>/junit-task17.xml
```
The plain `-q` summary line never printed — the run reached 100% then crashed at interpreter exit
with `Windows fatal exception: code 0x8001010d` / `<cannot get C stack on this system>` (the known Qt
teardown crash, task 15/16's C2). Tallied from the junitxml instead, written to disk before the crash:
```
<testsuite name="pytest" errors="0" failures="0" skipped="3" tests="1576" .../>
```

Re-measured after the task-18 fix dispatch (2026-09-16), same command, and this run printed its
own summary as well as writing the XML — the teardown print is intermittent, not certain (D-47):
```
<testsuite name="pytest" errors="0" failures="0" skipped="3" tests="1583" .../>
1580 passed, 3 skipped, 2 warnings in 79.49s (0:01:19)
```
Seven new tests, all of them the fix list's: the sanitised desk name (3, parametrised), the
file-opened export suggestion, the scalar-where-a-list-belongs guard, the relative dynamic import,
and the panel that no longer keeps the as-pulled JSON.
(Before the fix dispatch, at `764609f`, the same command gave 1573 passed / 3 skipped / 0 failed /
0 errors, 1576 collected — matching task 16's own number; the seven new tests are the whole delta.)

## 3. Done with evidence

Per the SDD ledger (`progress.md`), all ranges verified against `git log --oneline ac39cfa..HEAD`
(39 commits after the task-18 fix dispatch, matches exactly):

| Task | Commit range | Proof (test file) |
|---|---|---|
| 1 — connection state machine + table | `ac39cfa..33d80a9` | `tests/test_live_state.py` |
| 2 — Transport seam, connect, discover | `33d80a9..efbc91c` | `tests/test_live_controller.py` |
| 3 — pull: both `_load()` guards | `efbc91c..35dbe33` | `tests/test_live_controller.py` |
| 4 — session_from_snapshot, suggested_name | `35dbe33..ad2295b` | `tests/test_live_controller.py` |
| 5 — RoundGuard, watch_rate | `ad2295b..922fd9e` | `tests/test_live_guard.py` |
| 6 — GeneratorWorker + TIMEOUTS | `922fd9e..db105dd` | `tests/test_ui_workers.py` |
| 7 — consoles field in the state store | `db105dd..6dde19b` | `tests/test_ui_state_store.py` |
| 8 — page registration, Ctrl+7 | `6dde19b..254998c` | `tests/test_ui_shell.py`, `tests/test_ui_texts.py` |
| 9 — ConnectBar | `254998c..bb2dc77` | `tests/test_ui_console.py` |
| 10 — DiscoveryPanel | `bb2dc77..b82ff43` | `tests/test_ui_console.py` |
| 11 — SnapshotPanel + window wiring | `b82ff43..f39c71a` | `tests/test_ui_console.py` |
| 12 — LiveEventsView | `f39c71a..5d36f53` | `tests/test_ui_console.py` |
| 13 — ConsolePage assembly | `5d36f53..661c2e8` | `tests/test_ui_console.py` |
| 14 — AST no-write scan | `661c2e8..0af451c` | `tests/test_ui_live_is_read_only.py` |
| 15 — exe + 7 screenshots | `0af451c..e8e3de1` | no test file — evidence is `dist/wing-ui.exe` plus the 7 PNGs (see §4) |
| 16 — docs (manual, ROADMAP, tech-debt) | `e8e3de1..f88a460` | docs-only; suite unchanged, 1573/3 confirmed above |

Every task went through at least one review round per the ledger; all are marked "complete, review
clean" except task 16, which is "review pending" in `progress.md` — task 18's whole-branch review is
the outstanding gate, not a per-task one.

## 4. What ToanAZ can run and what he should see

- Exe (exists in this worktree): `dist\wing-ui.exe` — double-click, or from the worktree root.
- Screenshot all seven pages:
  ```
  Start-Process -FilePath ".\dist\wing-ui.exe" -ArgumentList "--screenshot","<dir>","user-files\example-Vu.snap" -PassThru -Wait
  ```
  The seven committed PNGs (verified present): `docs/screenshots/2026-09-16-gui-wave2/` with
  `overview.png`, `doctor.png`, `channels.png`, `routing.png`, `diff.png`, `import_.png`,
  `console.png` (plus a `README.md` in that folder). These are what ToanAZ needs to look at — wave
  1's rule was no page ships until he has seen its screenshot from the exe.
- Console page walk-through (sidebar row 7, or Ctrl+7):
  1. Connect — type or pick a console address, click Connect; lamp goes green on a real handshake,
     red with a message naming the host on failure (D2).
  2. Discover — walks the schema; shows the inventory (40 ch, 16 bus, 4 main, 8 mtx, 16 dca expected)
     and an unresolved-families banner with Rerun if anything came back short.
  3. Pull, then Open Doctor — pulls a live snapshot into a normal Session; stays on the Console page
     (D16) with a "scene loaded — N findings" line and a button to jump to Doctor when ready. Export
     writes the patched document via `Session.save_as`, not the raw pull bytes (D3) — a Doctor repair
     made after the pull is in the exported file.
  4. Start watch — live event table, about 4 per second max; Stop ends it cleanly; unplugging the
     desk mid-watch should report the loss within about 1 second, not sit green and silent (D6).
- Acceptance checklist — HUMAN-ONLY, needs the real desk (spec §9.3, unchanged, all boxes still
  unchecked): run against WING-GIAQUY (`192.168.128.28`) with WING-Edit connected throughout
  (coexistence is one of the checks). Full list is in
  `docs/superpowers/specs/2026-09-15-gui-live-console-wave2-design.md` §9.3 — ten checks including
  connect and the red-lamp case, discover counts, pull-with-desk-off, repair-export-reopen round
  trip, watch events against a fader and solo on WING-Edit, and the desk-unplugged-mid-watch case.

## 5. In progress

None. All 18 tasks are either complete (1–17) or explicitly the final gate (18, whole-branch review —
not started).

## 6. Decisions pending a human

Three open questions, spec §11 (only ones that change what gets built):
1. Does a watch need alerts (per-channel arming), or is a scrolling log enough? Today ships the log.
2. Is there a wave 3, and which write — a single Doctor-finding repair, or a whole-scene push?
3. Auto-connect to the last console at startup? Default shipped: no.

Twelve ASSUMED rulings (spec §5 unless noted) — each reversible, with what changes if overturned:
- D1 (no write in wave 2) — overturning starts wave-3's write scope now; the read-only AST scan
  (task 14, `tests/test_ui_live_is_read_only.py`) would need an explicit allow-list carve-out.
- D6 (DeskLost after 3 silent rounds, in RoundGuard) — a different threshold or detection method
  changes `live_guard.py`'s `lost_after` default and its dedicated tests in `test_live_guard.py`.
- D9 (Console is page 7, Ctrl+7) — moving it re-numbers `PAGE_KEYS`/`PAGE_ICONS` and every other
  page's accelerator, since `menus.build_accelerators` binds Ctrl+{index} positionally.
- D10 (remembered addresses in `ui-state.json.consoles`, capped 8) — switching to e.g. QSettings
  replaces `state_store.normalize` (`state_store.py:27-47`) and the `remember_console` helper
  wholesale.
- D12 (watch list not editable in the UI) — reversing needs a new family/key picker panel, not a
  patch.
- D14 (timeouts 5s / 60s / 90s) — changes the `TIMEOUTS` entries in `workers.py` and any test pinned
  to those exact numbers.
- D15 (no single-address probe box) — adding one means a new dev-mode panel, per the existing
  dev-vs-show-flow convention (project memory, 2026-08-24).
- D16 (stays on Console after Pull, via `live_wiring.adopt_pulled_session`) — reverting to "jump to
  Doctor" lets `main_window.py` reuse `window_state.adopt_session` and drop `adopt_pulled_session`.
- D17 (`console.*` texts namespace, not `live.*`) — a rename means a sweep of every
  `text("console....")` call site plus `texts_console.py`.
- Export gated on a loaded session, not `allowed_actions` (deviation from D16's mechanism, ruled at
  task 11, `live_snapshot.py:114`) — reversing makes Export respect ERROR/LOST states, currently it
  does not.
- ERROR allows connect in one click, and is now table-identical to LOST (task 13 sweep,
  `live_state.py`) — un-collapsing them means re-splitting the transition table and `_ACTIONS`, and
  updating the view logic that currently tells them apart only by event-list and label.
- `set_session` is a synchronous push to SnapshotPanel, re-adoption is a no-op (task 13,
  `console_page.py:95` forwarding to `live_snapshot.py:120`) — changing this risks reintroducing the
  bug it fixed: a Pull's own `_refresh` round trip clearing the "scene loaded" banner the same Pull
  just raised.

Plus C1, from Task 15 — the shared build venv (`D:\DEV CAVE EP3\PROJECT008-SOUNDTECH-ASSIST\.venv`)
has neither `anthropic` nor `openai` installed, so `dist\wing-ui.exe` ships without AI-assisted
ingest — same gap as wave 1's exe, so this is parity, not a regression. Decision needed: install
those extras into the shared venv and rebuild, or leave AI assist exe-unavailable (CLI-only) for now.

## 7. Debt filed, machine-doable

D-41 through D-46, filed at task 16 — by number only; see `docs/tech-debt.md` for the text (do not
duplicate it here, it drifts).

## 8. Known pitfalls

| Trap | Right way |
|---|---|
| A fresh or shared venv missing an optional extra (`[ui]`, `[ingest]`, `[llm-openai]`) makes UI tests silently skip in pytest, and a built exe exits instantly with no error (`console=False`). | Before trusting a green suite or a build, `pip install -e ".[ui]"` etc.; use `packaging/wing-ui-debug.spec` (console=True) to see a crashing exe's real traceback. |
| The shared venv's editable install maps `wing_parser` to the main checkout (`__editable__...pth`), so a naive build could silently bundle the wrong worktree's code. | The editable finder is appended behind `PathFinder` on `sys.meta_path`, so running the build from inside a worktree's own root resolves `wing_parser` to that worktree. Proved, not assumed: `grep -c "feat-gui-live-console-wave2.{1,4}wing_parser" build/wing-ui/Analysis-00.toc` gives 207; the same grep rooted at `PROJECT008-SOUNDTECH-ASSIST` gives 0. |
| `state_store.normalize` (`state_store.py:27-47`) rebuilds a fixed dict — any field added to the on-disk JSON without also adding it here is silently dropped on the next save. | `consoles` was added to both the dict literal and its own plain-string coercion in the same commit (task 7) — treat `normalize` as the single place a new persisted field must be declared. |
| `RoundGuard` (`live_guard.py`) counts every delegated `get_many`, including `poller.watch`'s priming label lookup — so a fresh watch's round sequence is `(0, 84)` (one address per strip, not per key) before the real `(0, 220)`-address rounds. A hand-rolled loop that only counted the 220-wide rounds would never reproduce this and would look correct while disagreeing with the real poller. | Drive `RoundGuard` against the real `poller.watch`, not a stand-in; `test_the_watch_list_fixture_is_the_shipped_84_strips_and_220_addresses` in `test_live_guard.py` pins the exact sequence. |
| `poller.watch` (`wing_parser/net/watch/poller.py:101-114`) yields only on a Change — a dead desk produces zero yields, indistinguishable downstream from a quiet-but-alive one (the poller carries the last value forward on purpose). Watching the generator's output for silence cannot detect a lost desk. | Detection has to live inside the counting proxy (`RoundGuard`), which raises `DeskLost` from what it counts going in, not from what comes out. |
| A plain `pytest -q` full run reaches 100% then crashes at interpreter exit (`Windows fatal exception: code 0x8001010d`, pre-existing, unrelated to this wave) — its "N passed" summary line never prints, and the crash can appear to overlap a real test if stdout and stderr interleave oddly. | Add `--junitxml=<path>`; the XML is written to disk before the crash and gives an exact tests/failures/skipped tally regardless. |
| Updating a PR body from a scratchpad file (`gh pr edit N --body-file <scratchpad>/...`) with a generic name lets two parallel sessions overwrite each other's draft. **This happened**, to PR #1: its body was replaced with PR #2's CI text at `2026-09-15T14:17:49Z` and restored at `14:19:48Z` — both edits are in `gh api graphql ... pullRequest(number:1){userContentEdits}`, which returns four body versions for that PR. | Name the file per task or session, as task 15 did (`pr4-body-task15.md`) — not a bare `pr-body.md`. Check `userContentEdits` before assuming a body was never clobbered. |
| The Write tool can refuse a path under a worktree it does not recognise as the active cwd. | Fall back to writing via the shell (heredoc or an equivalent), explicit UTF-8, no BOM — hit and confirmed live while writing this file. |
| `live_events_view.py` sits at exactly 200 lines; `live_snapshot.py` and `live_controller.py` at 199 each after the task-18 fixes (verified with `wc -l` on all three). | The next change to any of them needs a split first, not a squeeze. The two 199s are not slack — each was paid for by trimming a docstring to fit a one-line fix, which is a trick that works once. |

## 9. Verification commands

Run from this worktree root, snapshot after the task-18 fix dispatch:
```
git log --oneline ac39cfa..HEAD | wc -l                     # 39
git status --short                                          # clean
git check-ignore -v packaging/wing-ui-debug.spec            # .gitignore:25:packaging/wing-ui-debug.spec
git branch -vv | grep gui-live-console                      # in sync with origin: 681aecf pushed 2026-09-16 07:33
wc -l wing_parser/ui/live_snapshot.py wing_parser/ui/live_events_view.py wing_parser/ui/live_controller.py
                                                              # 199 200 199
ls docs/screenshots/2026-09-16-gui-wave2/                    # 7 PNGs plus README.md
gh pr list --state all                                       # #1 #2 #3 #4, all OPEN
```

The task-18 fix list and what each item changed are in
`.superpowers/sdd/2026-09-15-gui-live-console-wave2/final-fix-report.md`; the four debt items it
closed (D-43, D-44, D-45, D-46) and the one it opened (D-47) are in `docs/tech-debt.md`.

## 10. Lessons

See `memory/MEMORY.md`, entry "## 2026-09-16 — GUI wave 2: trang Console (read-only) tren nhanh,
cho merge" — records the page's scope, the suite number at `e8e3de1`, the PR stack, and the same
open questions and ASSUMED rulings listed above (§6), in Vietnamese, for the project's own index.
