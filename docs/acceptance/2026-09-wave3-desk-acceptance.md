# GUI wave 3 — real-desk acceptance runbook

**Console:** WING-GIAQUY, `192.168.128.28` · **Operator:** ToanAZ ·
**WING-Edit connected throughout** — this is a standing constraint, not a
nice-to-have; if WING-Edit drops during a step, stop, reconnect it, and
repeat that step.

This turns spec §11 acceptance list
(`docs/superpowers/specs/2026-09-17-gui-write-wave3-design.md`) and handoff
§4 steps 1–6 (`docs/handoff/2026-09-18-gui-write-wave3-complete.md`) into a
form to fill in at the desk. Every design and implementation decision this
runbook depends on (spec §5, §11, C1) was resolved by ToanAZ on 2026-09-25 —
see that handoff's §6 "Resolved 2026-09-25" block. Nothing below has touched
a real console before this session.

## Coverage note — D-52 item 3

`docs/tech-debt.md` D-52 item 3 records that `live_write.REAL._read` (the
function that actually reads a live leaf off the desk) has no unit test —
the suite has no real socket, so it cannot. **Every Delayed step below
exercises it**: opening `DelayedWriteDialog` always does a pre-flight read
of the target address before showing the countdown. Steps 4, 5b, 5c, 5d and
6 each perform at least one such read against the real desk. Treat a
Delayed step's countdown successfully showing a live desk value (not a
stale or default one) as this item closed; note it in the Notes column of
step 4.

## Pre-conditions — check every one before starting

| # | Pre-condition | Done? |
|---|---|---|
| P1 | **The desk is NOT running a show.** Confirm with whoever is at the venue before touching anything. | ☐ |
| P2 | **Use the release exe rebuilt 2026-09-25 from `main` at `3c2cda9`** (after PR #9, the debt-cleanup branch, merged), `dist\wing-ui.exe` (71,034,002 bytes), built from a venv with the C1 extras installed: `pip install -e ".[ui,ingest,llm,llm-openai]"` (see `README.md` "Building a standalone .exe" and `memory/MEMORY.md`'s 2026-08-24 pitfall entry, updated 2026-09-25). Confirm the exe is alive after launch (`Start-Process dist\wing-ui.exe`, wait ~6 s, check the process is still running) before going further. | ☐ |
| P3 | **Baseline identity recorded**, from the CLI, before opening the app: `wing net identity 192.168.128.28`. Write the name/model/serial it prints below — every later "identity matches" check compares against this line, not against memory. | `_______________________` |
| P4 | **WING-Edit is open and connected** to the same console, and stays that way for the whole session. | ☐ |
| P5 | A finding is available to repair that maps to rule **G8** (a send to a monitor bus left in POST, `wing_parser/edit/data/repairs.yaml:19-23`) and one that maps to **R1** (a `to: false` boolean repair, `repairs.yaml:52-55`), in whatever scene is pulled from the desk. Pull the scene first (step 1) and open Doctor to confirm both are present before relying on them in later steps. | ☐ |

## Steps

### 1 — Connect and Pull

| Action | Expected result |
|---|---|
| Launch the exe, go to Console (Ctrl+7), Connect to `192.168.128.28`. | Connection lamp turns green. Identity shown matches the P3 baseline exactly (name, model, serial). |
| Pull the scene, then open Doctor (Ctrl+1). | Doctor fills with findings from the live scene. The apply-level selector reads **Manual**; opening it shows **Delayed** and **Immediate** greyed out. |

**Result:** ☐ PASS ☐ FAIL
**Notes:** _______________________________________________

### 2 — Arm

| Action | Expected result |
|---|---|
| Click **Arm**. | `ArmWriteDialog` opens and re-queries identity fresh; it names the desk **with the serial**, matching P3. |
| Type the wrong name, e.g. `WING-GIAQUI` (note the swapped letters). | Arm button stays disabled, `console.write.name_wrong` shown. |
| Correct the name, but leave the "this desk is NOT running a show" latch **unticked**. | Arm button still disabled. |
| Tick the latch and type the exact correct name. | Arm enables. Click it. |
| After arming. | Doctor's button now reads `console.write.armed` = "Armed: {name}". All three levels (Manual/Delayed/Immediate) are selectable. |

**Result:** ☐ PASS ☐ FAIL
**Notes:** _______________________________________________

### 3 — Manual

| Action | Expected result |
|---|---|
| Selector on **Manual**. Repair the G8 finding (P5). | The finding's row updates in the Changes dock. **Nothing reaches the desk** — check WING-Edit shows no change. |
| Click that journal row's **Send to console**. | Countdown dialog opens, showing the desk's current (live) value and the value the repair would apply. |
| Press **+5 s** three times. | The remaining time visibly grows by 5 s each press, no ceiling. |
| Press **Cancel**. | Nothing is written — WING-Edit still shows the pre-repair value. The journal row for the repair stays intact (Undo would still remove it separately). |

**Result:** ☐ PASS ☐ FAIL
**Notes:** _______________________________________________

### 4 — Delayed, expiry and Apply now

| Action | Expected result |
|---|---|
| Selector on **Delayed**. Repair the same G8 finding again (or an equivalent one). | The countdown dialog **opens itself** at the Settings ▸ "Default apply delay (s)" value, showing a **live pre-flight read** of the desk's current value (this is the D-52 item 3 coverage point — confirm the value shown is the desk's real live value, not a placeholder). |
| Let the countdown **expire** without touching it. | `sent ✓` (or the current mark — see step 5a) badge appears, and **WING-Edit shows that send flip to PRE** (or whatever the repair's target state is). |
| Repair another finding, and this time press **Apply now**. | It lands immediately, without waiting for the countdown to run out. |
| Switch the selector to **Immediate**, repair a third finding. | It lands with **no dialog at all**, badge shown directly on the row. |

**Result:** ☐ PASS ☐ FAIL
**Notes (record the live value the pre-flight read showed, for D-52 item 3):** _______________________________________________

### 5 — Outcomes: bool normalisation, mismatch, clamp, no reply

| Action | Expected result |
|---|---|
| **5a — Bool normalisation.** In Delayed, repair the R1 finding (P5, a `to: false` boolean repair). | The dialog reads **`True`/`False`**, never `1`/`0`, for both the desk's current value and the new value. No mismatch warning, if the desk has not been moved. |
| **5b — Mismatch.** Before applying a repair, move that same parameter on WING-Edit. | The countdown shows `console.write.mismatch` (or its current text), with **both** the desk's live value and the scene file's expected value displayed. |
| **5c — Clamp.** Aim a numeric leaf repair outside the desk's valid range (or use `wing net set --confirm` once by hand if no shipped repair produces a clamp, then confirm the app renders the same `SetResult` shape). | Badge is the "clamped" mark (`!`, per D-51's font fix — not `⚠`). Both the requested and the desk-clamped value are shown. **Doctor's finding reflects the value the desk actually took**, not the one the repair asked for. |
| **5d — No reply.** Aim a repair at an address this console does not have. | Badge is the "no reply" mark (`×`, per D-51 — not `✗`). `console.write.no_reply` text shown. The scene leaf is left exactly as the repair set it (not overwritten with a guess). |

**Result:** ☐ PASS ☐ FAIL
**Notes:** _______________________________________________

### 5e — Un-revertable row (D-52 item 9 / CRITICAL 1 regression check)

| Action | Expected result |
|---|---|
| Using the same no-reply write from 5d (or a fresh one aimed the same way), open the sent ledger. | That row's **Revert button is disabled**, with a tooltip reading that the desk never said what it held before this write. |
| With that row present among others, run **Revert all**. | The run **skips this row** and says how many it skipped (`console.write.revert_skipped` or current text) rather than reverting it. **It must never put the literal string `None` on the wire** — this is the bug CRITICAL 1 in the wave-3 whole-branch review fixed; this step re-proves it against a real desk instead of `FakeDesk`. |

**Result:** ☐ PASS ☐ FAIL
**Notes:** _______________________________________________

### 6 — Revert and Revert all

| Action | Expected result |
|---|---|
| Pick one ledger row from the writes made in steps 3–5 and click **Revert**. | The desk returns to the value captured as "before" for that row. One countdown if the current level is Delayed; instant if Immediate. |
| Build up **five or more** ledger rows (repeat repairs as needed), then click **Revert all**. | Rows revert in **reverse order** (last written, first undone). A progress line counts up, e.g. `3/7`. **WING-Edit never shows two parameters moving at the same time.** In Delayed, this means **one countdown dialog per parameter**, not one for the whole batch (per ToanAZ's 2026-09-25 answer to spec §11 q2). |
| Mid-run, click **Stop**. | The run ends after the parameter currently in flight completes; the remaining rows are visibly left un-reverted. |

**Result:** ☐ PASS ☐ FAIL
**Notes:** _______________________________________________

### 7 — Refusals: serial mismatch and a desk lost mid-countdown

| Action | Expected result |
|---|---|
| Relaunch the exe with `WING_WRITE_ALLOW_SERIAL` set to a wrong value, arm, and attempt a write. | The write is refused; badge shows `console.write.refused` carrying `_authorize`'s own error text. **WING-Edit shows no change.** |
| In Delayed, start a watch, repair a finding to open a countdown, then unplug the desk (network cable or Wi-Fi) while the countdown is running. | On expiry, **nothing is sent** — `console.write.gate_closed` (or current text) is shown, and the apply-level selector has **fallen back to Manual** (arm state cleared, per F4). |

**Result:** ☐ PASS ☐ FAIL
**Notes:** _______________________________________________

### 8 — Coexistence and screenshots

| Action | Expected result |
|---|---|
| Throughout every step above, check WING-Edit periodically. | It stayed connected and usable the entire session — never displaced by the app under test. |
| Screenshot every affected surface from the exe (Doctor with the apply-level bar, the Arm dialog, the Delayed countdown, the Changes dock with all three badge types, the sent ledger mid Revert-all). | Screenshots exist and **ToanAZ has looked at every one of them** — this is wave 1's standing gate: no surface counts as done until he has. |

**Result:** ☐ PASS ☐ FAIL
**Notes:** _______________________________________________

### 9 — C1 check: Settings ▸ Test connection

| Action | Expected result |
|---|---|
| Open Settings, paste ToanAZ's own API key for a configured provider (Anthropic or the OpenAI-compatible one), click **Test connection**. | The frozen exe's bundled SDK (`anthropic` and/or `openai`, per C1) loads and the call either succeeds or fails on the key/network — never on `ModuleNotFoundError`. This proves the bundled SDK actually loads inside the frozen exe built 2026-09-25 from `3c2cda9` (gap noted in `docs/handoff/2026-09-18-gui-write-wave3-complete.md` §6.3). |

**Result:** ☐ PASS ☐ FAIL
**Notes:** _______________________________________________

## Sign-off

| | |
|---|---|
| Run date | _______________ |
| Firmware / console state at run time | _______________ |
| Overall result | ☐ ALL PASS ☐ SOME FAILED (list step numbers below) |
| Failed steps, if any | _______________________________________________ |
| Signed | ToanAZ |

On a clean pass, update `docs/ROADMAP.md` §5 item 9 (this closes the last
open item from GUI wave 3) and `docs/handoff/2026-09-18-gui-write-wave3-complete.md`
to record the run, and close D-52 item 3 in `docs/tech-debt.md`.
