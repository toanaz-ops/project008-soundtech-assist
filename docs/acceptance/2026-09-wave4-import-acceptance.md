# GUI wave 4 — cue-sheet import acceptance runbook

**Build:** the release exe, rebuilt from `main` after `feat/gui-import-wave4`
merges (see `docs/ROADMAP.md` §5 item 10) — do not run this against a dev
checkout; the point is what ships to a venue. **Operator:** ToanAZ. Nothing
in this runbook writes to a live console — every step stays inside the
Import wizard, the Vocabulary window, and Settings.

This turns the wave-4 spec's human-only acceptance list
(`docs/superpowers/specs/2026-09-26-gui-import-wave4-design.md` §9,
"Human-only") into a form to fill in.

## Pre-conditions

| # | Pre-condition | Done? |
|---|---|---|
| P1 | Exe rebuilt from `main` after this branch merges, from a venv with `.[ui,ingest,llm,llm-openai]` installed (`memory/MEMORY.md`'s 2026-08-24 pitfall entry). Launch it and confirm the process is still alive after ~6s. | ☐ |
| P2 | A real cue sheet on hand — a `.xlsx` running order from an upcoming or recent show. | ☐ |
| P3 | Your own DeepSeek (or Anthropic) API key, ready to paste into Settings. | ☐ |
| P4 | An existing show-context `.yaml` file to lint (any file a previous import produced works). | ☐ |
| P5 | A scene to cross-check against — a scene already open in Doctor, a `.snap` file, or a live desk reachable from the Console page's Pull. | ☐ |

## Steps

### 1 — Import a real cue sheet end to end

| Action | Expected result (what you should SEE) |
|---|---|
| File > Import, pick the real cue sheet. Step through Pick → Mapping → Terms → (Scene cross-check, optional) → Save. | Each step completes with no error dialog you did not expect. The Terms step lists only the fragments the vocabulary and pattern matcher could not resolve — most of a corporate or concert running order should already show as resolved, the way the two real test sheets did during build (VIVO 9 of 9; BIDV 19 of 31 resolved, 8 ignored, 4 left unread on purpose). Save writes a `.yaml` you can open in a text editor and read as correct Vietnamese. |

**Result:** [ ] PASS  [ ] FAIL
**Notes:** _______________________________________________

### 2 — Teach one term by shortening its key

| Action | Expected result |
|---|---|
| On the Terms step, pick an unresolved row. In its key field, delete everything except one representative word, tick "match inside a sentence" if it is not already ticked, choose a kind or set, click **Record**. | That row disappears from the unresolved list, AND any other unresolved row containing the same word clears at the same time (live re-resolve) — you should see more than one row vanish if the sheet repeats the word. |

**Result:** [ ] PASS  [ ] FAIL
**Notes:** _______________________________________________

### 3 — Edit "Drum kit" in Tools > Vocabulary and see "Band" follow

| Action | Expected result |
|---|---|
| Tools > Vocabulary > Sets tab. Open **Drum kit**, add or remove a kind (e.g. a second tom), save. Then open **Band**. | Band's own expanded-kinds display now includes your Drum-kit change, without touching Band directly — this is the nested-set behaviour (Band contains Drum kit). |

**Result:** [ ] PASS  [ ] FAIL
**Notes:** _______________________________________________

### 4 — Use the AI Assistant with your own key and approve one change

| Action | Expected result |
|---|---|
| Settings, paste your real API key, save. Reopen Tools > Vocabulary, type an instruction in the Assistant's box (e.g. "cajon is percussion"), submit. | A proposal list appears: each change shown as before → after with a reason and a tickbox. **Nothing is written yet.** |
| Tick only the one change you want, click **Apply**. | Only that one change now appears in the Terms/Sets tables, marked source "ai-approved"; anything left unticked is untouched. |

**Result:** [ ] PASS  [ ] FAIL
**Notes:** _______________________________________________

### 5 — Run Try AI on the Mapping step

| Action | Expected result |
|---|---|
| Import a file; on the Mapping step click **"Try AI on this file"**. | Within the timeout budget (120s) you see either a filled-in mapping proposal, or — if something goes wrong — a plain-language reason (bad key / quota / timeout / no network / SDK missing / bad reply), never a raw Python exception. |

**Result:** [ ] PASS  [ ] FAIL
**Notes:** _______________________________________________

### 6 — Lint an existing show-context file

| Action | Expected result |
|---|---|
| On the Pick step, choose "Check an existing show-context file...", pick a `.yaml` you have from a previous import. | The anomalies list appears (the same data `wing showcontext lint` prints on the CLI), each marked auto-fixable or not. |
| Click **Fix** on a fixable one, confirm. | A `.bak` copy of the file now sits beside the original, the changes made are listed, and a re-lint runs and shows the result. |

**Result:** [ ] PASS  [ ] FAIL
**Notes:** _______________________________________________

### 7 — Scene cross-check against Doctor's scene

| Action | Expected result |
|---|---|
| With a scene open in Doctor, run an import and reach the Scene cross-check step; leave the source on "Doctor's scene" (the default, preselected). | A table appears, one row per segment: segment name, kinds needed, channels found, and kinds missing highlighted. **Nothing is sent to a desk** — this step is read-only, exactly like the rest of this runbook. |

**Result:** [ ] PASS  [ ] FAIL
**Notes:** _______________________________________________

### 8 — Settings > Test connection

| Action | Expected result |
|---|---|
| Settings, with your real key saved, click **Test connection**. | The bundled SDK loads and the call either succeeds or fails on the key/network — never `ModuleNotFoundError`. |
| Set the environment variable `WING_DISABLE_LLM` (any value), relaunch the exe, click **Test connection** again. | It now reports the kill switch is on rather than attempting a call — the same behaviour Try AI and the Assistant already had, extended to Settings on 2026-09-27 (spec F15). |

**Result:** [ ] PASS  [ ] FAIL
**Notes:** _______________________________________________

## Sign-off

| | |
|---|---|
| Run date | _______________ |
| Exe build (commit) | _______________ |
| Overall result | [ ] ALL PASS  [ ] SOME FAILED (list step numbers below) |
| Failed steps, if any | _______________________________________________ |
| Signed | ToanAZ |

On a clean pass, update `docs/ROADMAP.md` §5 (close the wave-4 open items:
the exe screenshot gate, the real-key AI surfaces, and the real-cue-sheet
item) and record the run in the wave-4 completion handoff.
