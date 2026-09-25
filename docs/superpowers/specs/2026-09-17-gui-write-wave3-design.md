# GUI wave 3 — per-parameter write to a live WING console — design

**Date:** 2026-09-17 · **Status:** draft · **Cycle:** Đợt 3 (write) · **Follows:**
`2026-09-15-gui-live-console-wave2-design.md`, whose §8 drew a `ConfirmWriteDialog` "shape only, not built" (that spec,
lines 261-281) and whose §11 question 2 (`:408-410`) asked: *"Is there a wave 3, and which write? Two very different
hooks: a single-parameter repair pushed from a Doctor finding, versus a whole-scene `push`."* **ToanAZ answered in a
brainstorm on 2026-09-17**, and went further than the question: not only *which* write, but *when* it goes out. Everything
marked **F1–F8** below is his, FIXED, not for the plan writer to revisit; everything marked **W…** is the orchestrator's,
ASSUMED, with what changes if he overturns it. One part of wave 2's hook is deliberately **not** carried over verbatim:
`:277-278` drew the latch as *"this desk is in a show", default on*; here it is *"this desk is **not** running a show",
default unticked* — identical safety, but a **ticked** box meaning "danger" reads backwards at 2 a.m., and every other
checkbox in the app means "yes, do this".

**Protocol authority:** `2026-08-21-wing-net-design.md`. This spec adds a UI consumer of `wing_parser/net/write.py` and
changes nothing in it; the only `net/` changes are one new pure module (§4) and the two debt items in W9. Every claim
about existing code was checked by opening the file, with the `file:line` given so a reviewer can refute it in one
command.

## 1. Goal

**The point of this wave is the desk, not the file.** That is F2, and it inverts how the app has worked since wave 1: a
Repair edited an in-memory scene and the operator saved a `.snap`, and the console was a thing you read. From wave 3 the
console is what you *change* and the file edit is the means — Doctor re-derives from the patched document
(`ui/session.py:46-49`), so the scene must move for the findings to stay true, but moving it was never the goal.

So the operator picks how eagerly a repair reaches the desk — **Manual**, **Delayed** or **Immediate** (F3) — arms the
connection once (F4), and from then on clicking **Repair** either does nothing to the desk, opens a countdown he can
extend or cancel, or writes straight out. Every transmission is still **exactly one OSC leaf** (F1), and everything
written this session is listed with the value the desk held before it, revertable one row at a time or all in reverse
(F7). `edit/journal.py:11-14` has said since the journal was written where this goes: *"Writing
`ae_data.ch.1.send.8.mode = "PRE"` into a file and sending the equivalent OSC message to a running WING are the same
patch leaving through two different doors."* Wave 3 opens that second door, one patch wide.

## 2. What the operator sees

Every string below is keyed under `console.write.*` (W7), in `wing_parser/ui/texts_write.py`.

### 2.1 Arming, once per connection (F4)

The Doctor page grows an **apply-level selector** beside the repair area and, next to it, an explicit **Arm** button.
Before arming the selector reads **Manual** with Delayed and Immediate **disabled**, and Arm is the only way in — clicking
it opens `ArmWriteDialog`; the one other entrance is Manual's own **Send to console**, which opens the same dialog first
if unarmed. After arming, the button becomes the label `console.write.armed` and all three entries are selectable:

| key | string |
|---|---|
| `console.write.arm_title` / `.reading` | `Arm writing to this console` · `Asking the desk…` |
| `console.write.desk` / `.identity_failed` | `{name} · {model} · serial {serial}` · `Cannot identify the desk at {host}: {error} — not armed.` |
| `console.write.latch` / `.latch_why` | `This desk is NOT running a show right now.` · `CLAUDE.md: never during a show without explicit confirmation.` |
| `console.write.name_prompt` / `.name_wrong` | `Type this console's name to confirm:` · `That is not this console's name.` |
| `console.write.arm` / `.armed` | `Arm` · `Armed: {name}` (the button becomes this label) |
| `console.write.refused` | `Refused: {error}` |

Identity is re-queried **fresh at dialog time**, never reused from the earlier connect —
`net_commands._echo_identity_before_write` (`net_commands.py:80-85`) does exactly this before every CLI write, and
`identity.py:10-14` says why: the caller is about to trust *"this is the console I meant to write to"*. **Arm** enables
only when the latch is ticked **and** the typed name equals `identity.name` exactly. Arm state dies on Disconnect, `LOST`,
`ERROR` and app quit: the label reverts to an **Arm** button and the selector visibly falls back to Manual, so an operator
who looks up after a dropout sees the truth.

### 2.2 The three levels (F3)

**Manual** — Repair edits the in-memory scene only (`ui/session.py:57-69`). The Changes dock appears
(`main_window.py:180-181`) and each journal row carries `console.write.send` = `Send to console`. **It is disabled only
when the gate is closed** — the page not `CONNECTED`/`WATCHING` — with `console.write.blocked` =
`Connect to the console (Ctrl+7) to send this.` as its tooltip. Being unarmed does **not** disable it: clicking while unarmed opens
`ArmWriteDialog` first and the countdown after it, so Manual has one button that always means the same thing and the
arming step appears only when it is actually needed. Clicking it opens the countdown (§2.3) — deliberately, not a bare
confirm: Manual exists so the operator *sees the numbers*, and that screen is where the numbers are.

**Immediate** — Repair edits the scene and writes at once, no dialog. The row shows `console.write.sending` =
`Sending {address}…` then one of the three badges in §2.4. The level for a soundcheck where the operator is looking at the desk,
not the laptop.

### 2.3 Delayed, and the countdown (F5)

**Delayed** — Repair edits the scene and opens `DelayedWriteDialog`:

| key | string |
|---|---|
| `console.write.delay_title` / `.address` / `.countdown` | `Applying to the console in {seconds} s` · `{address}` · `{remaining} s` |
| `console.write.desk_value` / `.file_value` / `.after` | `The desk now holds: {value}` · `The scene file expected: {value}` · `It will become: {value}` |
| `console.write.mismatch` | `⚠ The desk holds {desk}, the scene file expected {file}. Applying replaces the desk's value.` |
| `console.write.no_read` | `The desk did not answer a read of this address. It may not exist here.` |
| `console.write.apply_now` / `.extend` / `.cancel` | `Apply now` · `+5 s` · `Cancel` |
| `console.write.cancelled` | `Not applied. The scene edit stays — use Undo to drop it too.` |

A progress bar runs the countdown down. **Apply now** writes at once; **+5 s** adds five seconds to whatever remains, any
number of times, with no ceiling (F5 — an operator who needs a minute presses it twelve times, and that is a legitimate
answer); **Cancel** writes nothing. **Expiry is an apply.** `console.write.desk_value` is read live off the desk and
normalised (§4), not taken from the journal's `before`; when the two differ, `console.write.mismatch` appears too —
somebody moved the desk after the scene was pulled, and what to do about it is the operator's call, not the app's.

**Cancel leaves the scene edit in place.** The Repair already happened, the journal holds the `Patch`, Doctor already
re-derived. Undo in the Changes panel drops the file side (`ui/session.py:71-75`); Cancel drops only the transmission.
Different doors, and the text says so.

### 2.4 The result, and what happens to the scene (F8)

`write.py:122` computes `matched = readback is not None and (...)`, so `matched=False` with `readback=None` means the desk
**never answered the read-back** (the packet may or may not have landed) while `matched=False` with a `readback` means it
answered a *different* value, a clamp. Three outcomes, never two, each doing something different to the scene:

| outcome | badge | key | scene leaf |
|---|---|---|---|
| `matched is True` | ✓ | `console.write.sent` = `sent ✓ the desk holds {readback}` | **set to `after`, not to `readback`** — see below |
| `readback` present, ≠ after | ⚠ | `console.write.clamped` = `⚠ the desk holds {readback}, not {after} — the console clamped it.` | **set to `scene_value(parts, readback)`**, so Doctor re-derives against what the desk really holds |
| `readback is None` | ✗ | `console.write.no_reply` = `✗ {address}: the desk did not answer. It may or may not have landed.` | **left exactly as Repair set it** — inventing a value for a silent desk is the one thing worse than admitting ignorance |

**`readback` is not safe to store raw, which is why the matched row writes `after`.** `SetResult.readback` is
`leaf_value(reply)[0]` (`write.py:121`) — an `int` for every `,sfi` leaf (`codec.py:127-129`) — while `_values_match`
(`write.py:84-90`) deliberately calls a match on `bool(1) == True`, on a float within tolerance, and on any two values at
or below the −144 dB sentinel. So a *matched* write of `True` reads back `1`, and one of `-999.0` reads back `-144.0`:
storing that would quietly retype the document the operator is editing. Hence **matched → write `after`** (what the
journal and the dialog both showed) and **clamped → write `scene_value(parts, readback)`**, one coercion in `live_write` —
`bool(readback)` when `jsontypes.is_boolean_shape(parts)` says the leaf is a JSON boolean, else `readback` unchanged. One
function, tested per JSON type (§9.1), used by revert too (W13).

The clamp row is why F8 matters at all: `net/write.py:5-9` records that the console clamps an out-of-range value **and
still answers `OK`**, which is why every write there is read back — without F8 the app would show a repaired finding the
desk had quietly refused. `console.write.refused` carries `SerialMismatchError`'s own text (`write.py:97-100`) unchanged,
and `console.write.gate_closed` = `The console connection dropped. Nothing was sent.` is gate 4 (§8.4).

### 2.5 The sent ledger, Revert and Revert all (F7)

Below the journal list, a second list headed `console.write.sent_heading` = `Sent to console` holds one row per parameter
written **this session**: address, the desk-live value captured *before* the write, the value written, the read-back
result. Its rows survive an Undo, which is a file-side action — a desk change the UI cannot revert is worse than a longer
panel.

| key | string |
|---|---|
| `console.write.revert` / `.revert_all` / `.revert_stop` | `Revert` · `Revert all` · `Stop` |
| `console.write.reverting` / `.reverted` | `Reverting {done}/{total}: {address}` · `reverted ✓ the desk holds {readback}` |
| `console.write.revert_stopped` | `Stopped after {done} of {total}. The rest were left as they are.` |

**Revert** writes that row's captured desk-before value through the **current apply level**: Immediate at once, Delayed
and Manual via the countdown. **Revert all** walks the rows **in reverse order** — last written, first undone — and is
**still one parameter per transmission** (F1): the next starts only after the previous read-back returns (§7.2). In
Immediate that shows as a running `console.write.reverting` line; **in Delayed it means one countdown dialog per
parameter**, slow on purpose and exactly what "delayed" asked for (§11 ii asks whether he would rather have one countdown
for the whole batch). **Stop** ends the run between parameters; the one already on the wire completes, because nothing can
un-send a packet.

## 3. Scope

**In.** Three apply levels behind one arming step; one `Patch` → one OSC leaf → one `write.set(..., confirm=True)`;
read-back reporting that moves the scene (F8); the sent ledger with per-row and sequential all-rows revert; one new
Settings key; the two debt items in W9. **Out.** `push`, `node_write`, any `ce_data` / `$ctl` address, a raw address+value
box, a multi-parameter packet, a durable write log, a watch-list editor, auto-connect. §12 gives the reasons.

## 4. Architecture

### New

| Module | Budget | Qt? | Names `net`? |
|---|---|---|---|
| `wing_parser/net/address.py` | ≤60 | no | it *is* `net` |
| `wing_parser/ui/apply_level.py` — `ApplyLevel`, `ArmState`, `RevertQueue` | ≤200 | **no** | no |
| `wing_parser/ui/write_queue.py` — the one-at-a-time FIFO (W10) | ≤120 | **no** | no |
| `wing_parser/ui/live_write.py` — incl. `scene_value` (F8) | ≤200 | no | **yes — the only one** |
| `wing_parser/ui/write_arm_dialog.py` | ≤200 | yes | no |
| `wing_parser/ui/write_delay_dialog.py` | ≤200 | yes | no |
| `wing_parser/ui/changes_send.py` — Send button per journal row, result badges | ≤120 | yes | no |
| `wing_parser/ui/changes_ledger.py` — the sent ledger, Revert, Revert all, Stop, progress | ≤200 | yes | no |
| `wing_parser/ui/texts_write.py` | ≤120 | no | no |
| `wing_parser/ui/settings_io.py` — the split that makes room for F6 (below) | ≤80 | no | no |

Plus `tests/test_net_address.py`, `test_apply_level.py`, `test_ui_live_write.py`, `test_ui_write_dialogs.py`,
`test_ui_changes_send.py`.

**`net/address.py`** holds two pure functions. `leaf_parts(path) -> list[str]` strips the `ae_data.` root, splits on `.`,
and raises `ValueError` naming the path for a non-`ae_data` root or any empty segment; `osc_address(path)` is
`"/" + "/".join(leaf_parts(path))`, so `ae_data.ch.1.send.8.mode` → `/ch/1/send/8/mode`. That is the exact inverse of
`net/snapshot.py:_place` (`snapshot.py:116-123`), whose docstring is the authority: *"Everything else is ae_data, keyed
exactly as the OSC address reads, which is already the .snap layout"* — and also why `$ctl` is refused rather than mapped,
since `ce_data`'s top-level keys are `$ctl`'s **children**, so such a path is not one segment from its address, and no
descriptor in `wing_parser/edit/data/repairs.yaml` targets one. **Prior art:** `cli/net_commands.py:61-77` (`_flatten` /
`_leaves_from_raw`) already inverts `_place` for `wing net push`, over a tree instead of one path, so `osc_address` is
tested *against it* — flatten a real scene (`user-files/GIAQUY_WING.snap`, or `tests/conftest.py:36`'s `example-Vu.snap`
fixture) and assert every `ae_data.` path it is given lands in `_leaves_from_raw`'s key set — and `_flatten` is refactored
onto its join so the two cannot drift.

**`ui/apply_level.py`** is the policy layer, deliberately Qt-free: `ApplyLevel` (`MANUAL` / `DELAYED` / `IMMEDIATE`);
`ArmState`, holding the `WingIdentity` this arming is for plus the current level, with `armed()` and a `disarm()` back to
`MANUAL` with no identity; and `RevertQueue(records)`, reversing on entry and exposing `next() -> SentWrite | None`
(`None` when exhausted **or** stopped), `stop()` and a `progress` `(done, total)` tuple.

**`ui/live_write.py`** is the seam, and the only `ui/` file that names `net.write`:

```python
class WriteTransport:   # frozen dataclass; REAL = WriteTransport(...) is the ONLY place ui/ names net.write
    identity: Callable[[str], WingIdentity]    # net.identity.query_identity
    read:     Callable[[str, str], Any | None] # host, address -> NORMALISED value (below)
    set:      Callable[..., SetResult]         # net.write.set
class WriteConfirmation:  # frozen; the token gate 4 hands to send() -- see §8.4
    host: str; address: str; after: Any; identity: WingIdentity; desk_before: Any | None
class SentWrite:          # frozen; one ledger row
    address: str; desk_before: Any | None; written: Any; result: SetResult
def preflight(host, address, transport=REAL) -> tuple[WingIdentity, Any | None]: ...
def send(confirmation: WriteConfirmation, transport=REAL) -> SetResult: ...
def revert_confirmation(record: SentWrite, identity) -> WriteConfirmation: ...
def scene_value(parts: Sequence[str], readback: Any) -> Any: ...   # F8's one coercion
```

`parts` is the leaf path with `ae_data.` already stripped, exactly as `jsontypes.py:52-57` requires —
`is_boolean_shape(['ae_data', ...])` returns False silently, so a caller that passes the document-rooted path gets no
error and no coercion, only a bool quietly stored as an int. That failure is unobservable at the call site, so the shape
is not left to each caller: `osc_address` and `scene_value` both take it from one helper,
**`leaf_parts(path) -> list[str]`** in `net/address.py`, which strips the `ae_data.` root, splits on `.`, and raises `ValueError` for a
non-`ae_data` root or any empty segment. `osc_address` is then `"/" + "/".join(leaf_parts(path))`, and nobody can pass the
wrong shape to either.

**`WriteTransport.read` must normalise before it compares or displays.** It wraps one `WingClient.request` plus
`codec.leaf_value` (`codec.py:107`), as `net_get` does (`net_commands.py:122-141`) — not enough here. A `,sfi` leaf reads
back as a Python `int` (`codec.py:127-129`), and `jsontypes.py:1-13` gives the reason: `,sfi` covers plain integers
**and** WING's booleans, and the value never carries the distinction. **Eight of the eleven repair descriptors set a JSON
bool** (`repairs.yaml` lines 55, 68, 80, 93, 102, 130, 142, 156, plus PB1's computed `not before`), so an unnormalised
read hands the countdown `0` against a journal `before` of `False` — a spurious mismatch, shown as the nonsense *"the desk
holds 0, the scene file expected False"*. So `read` applies `scene_value` (F8), the same coercion the read-back path uses,
and comparison then follows `write._values_match` (`write.py:82-91`).

### Changed

| File | Change | Lines now |
|---|---|---|
| `ui/doctor_page.py` | the apply-level selector and the Arm button (F4, W14) | 70 |
| `ui/detail_panel.py` | Repair routes through the level instead of stopping at the scene | 127 |
| `ui/changes_panel.py` | per-row widget via `QListWidget.setItemWidget`, composed from `changes_send.py`; hosts `changes_ledger.py` | 37 |
| `ui/live_state.py` | one action name in two `_ACTIONS` rows (§6) | 144 |
| `ui/live_wiring.py` | **owns, constructs and publishes the `WriteGate` and the `ArmState`** | 69 |
| `ui/main_window.py` | **≤4 new lines, hard budget**: the `_refresh` dock-visibility change (`:181`) and one call into `live_wiring` | 191 |
| `ui/workers.py` | `TIMEOUTS["write"] = 10` (`workers.py:34-37`) | 170 |
| `ui/settings_dialog.py` | the F6 delay row — **but see below** | 199 |
| `ui/state_store.py` | `apply_delay` in `DEFAULTS` (`:24`) **and** in `normalize` (`:27-47`) | 92 |
| `ui/window_state.py` | `apply_delay` read in `restore` (`:21-34`) **and** written in `save_on_close` (`:116-128`) — miss either and it is erased at quit | 128 |
| `ui/texts.py` | one import and one `**WRITE_TEXTS` line, beside `**CONSOLE_TEXTS` (`texts.py:9,157`) | 162 |
| `tests/test_ui_live_is_read_only.py` | blanket ban → allow-list of one module (§8.4) | 225 |

**F6 cannot simply add a row: `settings_dialog.py` is already at 199** of the 200-line ceiling
`test_ui_house_style.py:170,173` enforces. So the task **splits first** — `_mask` and `_dump_yaml`
(`settings_dialog.py:38-48`) move to a new `ui/settings_io.py`, freeing ~11 lines — and only then does the dialog gain a
`QSpinBox` row in its `QFormLayout` (`:75-80`) and one save line in `_save_and_close` (`settings_dialog.py:197`; `:90`
only connects the button to it). **The value does not go in `provider.yaml`** — that file is the AI provider key
(`settings_dialog.py:1-10`); the delay is UI state, written through `state_store.save`, and **it must be declared in four
places or it is silently lost**: `DEFAULTS` (`state_store.py:24`) and the rebuilt dict in `normalize` (`:38-47`) — the
wave-2 pitfall this project has already been bitten by — plus `window_state.restore` (`:21-34`), which reads each key by
name, and `window_state.save_on_close` (`:116-128`), which rebuilds the saved dict from an explicit literal, so a key
missing *there* is erased on every quit. `normalize` clamps to **3–60, default 5**. `live_controller.py` and
`console_page.py` (199 each) **must not grow** (W7); **`main_window.py`** at 191 has nine lines of headroom and two tasks
want it, which is why the gate and the arm state are *owned* by `live_wiring.py` — it ends this wave at **195 or under**,
measured.

### Data flow

```
Doctor selector -> ArmState.level [MANUAL|DELAYED|IMMEDIATE]; armed?        [GATE 2]
Repair -> Session.repair (ui/session.py:57-69) -> Patch -> journal
       -> MainWindow._refresh (main_window.py:170-181) -> ChangesPanel
  MANUAL: stop; the row's Send resumes it | DELAYED: countdown              [GATE 3]
  | IMMEDIATE: straight through.  WriteGate: CONNECTED/WATCHING?            [GATE 1]
   -> osc_address(patch.path) -> preflight: .identity (fresh) + .read (normalised)
   -> WriteConfirmation, after can_write()+armed() RE-CHECK -> send()       [GATE 4]
        -> net.write.set(...confirm=True): _authorize (write.py:93-100)     [GATE 5]
           datagram (:102-110); read-back (:119-123) -> SetResult -- §2.4
   -> badge + SentWrite appended to the ledger + scene leaf per F8
```

## 5. Rulings

**FIXED** = ToanAZ, brainstorm 2026-09-17. **ASSUMED** = the orchestrator's safest default, for him.

**Update 2026-09-25:** ToanAZ reviewed every `W…` row below in chat and approved
each as written. They are relabelled **FIXED (ToanAZ 2026-09-25)** — the "If
overturned" column stays as a record of what each ruling was and what changing
it would cost, but none of them is open any more.

| # | Question | Decision | If overturned |
|---|---|---|---|
| **F1** | How much goes out per transmission? | **One parameter. Exactly one OSC leaf.** No `push`, no `node_write`, no multi-param packet — including inside Revert all. | **FIXED.** |
| **F2** | What is this wave *for*? | **Applying to the desk.** Editing the file is a means, not the goal: Doctor must re-derive, so the scene has to move, but the desk is the point. This is what justifies Immediate existing at all. | **FIXED.** |
| **F3** | How eagerly does a repair reach the desk? | **Three apply levels**, on a selector beside the Doctor repair area, remembered for the current connection only: **Manual** (scene only; the row's Send button, which opens the countdown), **Delayed** (Repair edits and opens the countdown), **Immediate** (Repair edits and writes at once, no dialog, badge on the row). | **FIXED.** |
| **F4** | What must happen before any write? | **Arming, once per connection**: `ArmWriteDialog` with a fresh identity re-query, an unticked *"this desk is NOT running a show"* latch, and the console's exact name typed. Required before Delayed or Immediate can even be *selected*, and before the first Manual Send. Cleared on Disconnect / `LOST` / `ERROR` / quit, with the selector visibly falling back to Manual. | **FIXED.** |
| **F5** | What does Delayed show? | `DelayedWriteDialog`: address, desk-live current value (jsontypes-normalised), scene-file before with a mismatch warning when they differ, the new value, a countdown and progress bar. **Apply now** · **+5 s** (extends the remainder, unbounded presses) · **Cancel** (nothing written; the scene edit stays, Undo reverts that). **Expiry applies.** | **FIXED.** |
| **F6** | Where does the default countdown come from? | **Settings → "Default apply delay (s)"**, integer 3–60, default 5, persisted as one new key in `ui-state.json` through `state_store`. The only new persisted key in this wave. | **FIXED.** |
| **F7** | What can be undone on the desk? | A session-lifetime **sent ledger** — address, desk-before, written value, read-back — with per-row **Revert** (writes desk-before through the *current* level) and **Revert all** (reverse order, sequential, one parameter per transmission, next starts after the previous read-back; **Stop** ends it between parameters, the in-flight one completes). | **FIXED.** |
| **F8** | What does the read-back do to the scene? | **Matched** → set the leaf to **`after`**, the value the journal and the dialog both showed — *not* to `readback`, which `write.py:84-90` will have called a match while being a different Python type or a clamped-to-sentinel number (§2.4). **Clamp** (`readback` present, ≠ after) → set the leaf to **`scene_value(parts, readback)`**, so Doctor re-derives against the desk's truth, badge ⚠. **No reply** (`readback is None`) → leave the leaf exactly as Repair set it, badge ✗. | **FIXED.** |
| W1 | When is writing available at all? | Only while the Console page is `CONNECTED` or `WATCHING` — every level, Immediate included: a new `"write"` action in those two `_ACTIONS` rows (§6); the three busy states, `ERROR`, `LOST` and `DISCONNECTED` never offer it. The Doctor side learns this through a `WriteGate` owned and built by `live_wiring.py` — **the Changes panel and the Doctor page never import the Console page**. **FIXED (ToanAZ 2026-09-25)** | Dropping `WATCHING` (§11 i) changes one `frozenset` literal and the two pinned tests named in §6; nothing else. Dropping the gate means Send is always live and gate 1 disappears — do not. |
| W2 | How does a `Patch.path` become an OSC address? | `osc_address()` in a new `net/address.py`, cross-checked against `_leaves_from_raw` on a real fixture, with `_flatten` refactored onto it (§4). `ValueError` for `ce_data` / `$ctl` and any empty segment. **FIXED (ToanAZ 2026-09-25)** | If `ce_data` writes are ever wanted, the function needs the `$ctl` re-prefix `snapshot.py:118-122` describes plus a test per shape; callers are unaffected. |
| W3 | Which write verb? | Always `write.set(host, address, value, confirm=True)` (`write.py:125-137`). **Never `toggle`** — it sends `,i -1` and flips whatever the desk holds *now* (`write.py:139-142`), so its outcome depends on the desk at send time, while `after` is deterministic and already on screen. `push` and `node_write` stay unreachable. Encoding is `write._format_value` (`write.py:72-80`): `bool` → `"1"`/`"0"`, a level at or below −144 dB → `"-oo"`, `float` → plain decimal, else `str()`. **FIXED (ToanAZ 2026-09-25)** | Using `toggle` for `kind: toggle` repairs would destroy the deterministic-`after` property the countdown display rests on, and needs its own read-back rule: `toggle` passes `expected=None` (`write.py:142`), so `matched` would mean only "something answered". |
| W3b | Int-typed leaves | **A known risk, not a current one.** `codec.py:107-129` records that a `,sfi` native int is often a 0-based *index*, which is why `set` defaults to the display string. No repair of the eleven reaches that today: every `to:` in `repairs.yaml` is a string (lines 22, 116) or a bool (55, 68, 80, 93, 102, 130, 142, 156), and `kind: toggle` computes `not before` (`repairs.py:99`), also a bool — the same eight lines that force the §4 normalisation. **The first int-valued descriptor needs the `typetag="i"` path (`write.py:134`) and a test before it ships**; a comment says so in `repairs.yaml` beside the `KINDS` tuple it mirrors (`repairs.py:30`). **FIXED (ToanAZ 2026-09-25)** | An int repair landing before that test goes out as a display string and may select the wrong enum entry — silently, since the read-back compares the same re-expression (`write.py:82-91`). |
| W4 | The structural gate | Exactly one `ui/` module may import `wing_parser.net.write`: `ui/live_write.py`, non-Qt, ≤200 lines. The AST test becomes an allow-list keyed on `path.name`, exempting **only** the import rule; the verb rule (`set` only) keeps running on allow-listed files too, in any directory. `send` requires a `WriteConfirmation` that only the arm + per-write dialog path constructs. **FIXED (ToanAZ 2026-09-25)** | Allow-listing a second module re-opens the blast radius the AST test exists to bound. The test is the enforcement, not this prose. |
| W5 | Threading | Each dialog owns **its own** `CallRunner` **for its pre-flight read**; `TIMEOUTS["write"] = 10`; pre-flight reads reuse the `connect` budget; every *write* goes through the gate's single runner and queue (W10); Revert all is a non-Qt `RevertQueue` driven one write at a time (§7). **FIXED (ToanAZ 2026-09-25)** | Borrowing the Console page's runner for a pre-flight read would make that read fail on `start() → False` whenever the page is mid-call — during a watch, most of the time — so the dialog could not even show the desk's current value. |
| W7 | Texts and ceilings | `console.write.*` in `ui/texts_write.py`, merged into `TEXTS` as `CONSOLE_TEXTS` is (`texts.py:9,157`). No colour literal — tokens only. Every `ui/` file ≤200 (`test_ui_house_style.py:170,173`); `live_controller.py` and `console_page.py` do not grow; `settings_dialog.py` is split before it gains the F6 row (§4). **FIXED (ToanAZ 2026-09-25)** | A `write.*` namespace would collide with the existing `changes.*` keys; renaming later is a sweep of every call site. |
| W8 | Persistence | Exactly one new key, `apply_delay` (F6). No write log, no remembered arm state, no auto-connect. **FIXED (ToanAZ 2026-09-25)** | A durable log (§11 iii territory) needs a path, a rotation rule and a decision about recording venue and desk names — a wave, not a task. |
| W10 | What if two writes are asked for at once? | **One write runner, one packet on the wire.** `WriteGate` owns a single `CallRunner` plus a non-Qt FIFO `WriteQueue` (`ui/write_queue.py`); **every** write — an Immediate Repair, a dialog's Apply, a single Revert, each step of Revert all — is enqueued, and the next starts only when the previous read-back returns or times out. Two rapid Immediate Repairs queue; neither is dropped. Dialogs keep their own `CallRunner` for **pre-flight reads only**. **FIXED (ToanAZ 2026-09-25)** | Letting sends run concurrently would break F1 at the transport level, not just the UI, and make the ledger's ordering a lie. A per-call runner is the alternative and it is what this forbids. |
| W11 | Can a second Repair be clicked while a countdown runs? | **No.** Both dialogs are `Qt.ApplicationModal`, so the Doctor page cannot be reached while one is open; pinned by a test rather than by layout accident. **FIXED (ToanAZ 2026-09-25)** | Window-modal dialogs would let a second Repair open a second countdown, and two countdowns racing the same queue is the state F5 has no answer for. |
| W12 | What does Cancel mean *inside* a Revert-all countdown? | **It stops the whole run**, exactly as the ledger's Stop does: already-sent and in-flight reverts stay, the remainder is left. It gets its own string, `console.write.revert_cancelled` = `Not reverted. The desk keeps the written value.`; `console.write.cancelled` stays for forward writes only. **FIXED (ToanAZ 2026-09-25)** | Treating it as "skip this one, continue" would make a seven-row revert need seven deliberate cancels to abandon, which is the opposite of what a Cancel button promises. |
| W13 | What does a successful revert do to the scene? | Moves the leaf back to the reverted value, coerced through `scene_value` exactly as F8 does, **so Doctor re-derives and the finding reappears** — the honest outcome, since the desk really is back in the state the rule objects to. **The journal `Patch` is NOT undone**: the journal is the *file-side* record of what the operator decided, Undo remains available separately, and silently dropping a patch because a desk write was reverted would conflate the two doors this whole wave keeps apart. **FIXED (ToanAZ 2026-09-25)** | Undoing the patch too would make Revert a compound action with no way to get the file edit back. |
| W14 | Can the level change mid-run? | **No.** The selector and the Arm button are disabled while Revert all runs, and Stop re-enables them — a run that changed level halfway would send some parameters through a countdown and others instantly, from one click. **FIXED (ToanAZ 2026-09-25)** | Allowing it means every queued item must capture its own level at enqueue time, which is a bigger change than it looks. |
| W15 | How is a Delayed Revert-all stopped? | Through the countdown's own **Cancel**, which is W12's stop-the-run. The ledger's **Stop** button is for a run with no dialog on screen — the Immediate case. So each mode has exactly one visible way out and neither needs the other's control. **FIXED (ToanAZ 2026-09-25)** | A Stop button reachable behind a modal dialog is not reachable at all; that is the bug this ruling avoids. |
| W9 | Debt riding along | First wave to touch `net/` since wave 2, so **D-41** (double schema walk, `docs/tech-debt.md:508-527`) and **D-42** (cancel-aware pace sleep, `net/watch/poller.py:121-123`, `tech-debt.md:529-540`) are the last two tasks, independent, each with its own test. **Droppable if they endanger the wave.** **FIXED (ToanAZ 2026-09-25)** | Dropping both leaves the entries open as written; nothing in wave 3's behaviour depends on either. |

## 6. State machine delta

`live_state.py` gains **one action name in two rows** and **no new `_TABLE` row**:

```python
    LiveState.CONNECTED: frozenset(
        {"disconnect", "discover", "pull", "watch", "export", "rerun", "write"}),
    LiveState.WATCHING: frozenset({"stop", "disconnect", "export", "write"}),
```

Every other `_ACTIONS` row (`live_state.py:114-125`) is untouched and `_TABLE` (`:82-106`) entirely so. `"write"` is an
**action, not an event**: a send does not move the connection state machine, exactly as `export` does not —
`live_state.py:111-113` says so (*"`export` fires no event at all (it writes a file; the desk does not move)"*). Because
`test_every_button_driven_event_is_offered_by_the_state_it_fires_from` (`tests/test_live_state.py:114`) checks events
against `_ACTIONS` and not the reverse, an action with no event keeps it green. **Two existing tests WILL fail until
updated — the point of their task, not collateral:** `test_allowed_actions_is_pinned_for_every_state`
(`tests/test_live_state.py:82`) spells both `frozenset`s out literally, and
`test_timeouts_table_carries_the_ruled_numbers` (`tests/test_ui_workers.py:121-125`) pins the whole `TIMEOUTS` dict.

Arm state is **not** in this table: it is a property of the operator's intent, not of the socket, and is *cleared by* the
transitions into `DISCONNECTED`, `LOST` and `ERROR` rather than being one of them — `live_wiring.py` watches the page's
state signal and calls `ArmState.disarm()`.

## 7. Threading and timeouts

### 7.1 Budgets

| Call | Vehicle | Budget | Why |
|---|---|---|---|
| arm / pre-flight (`identity`, or `identity` + one leaf read) | `FunctionWorker` under the dialog's own `CallRunner` | **`"connect"` = 5 s**, reused | Precisely `query_identity` (own socket timeout 2.0 s, `identity.py:68-69`) plus at most one `WingClient.request` (`DEFAULT_TIMEOUT` 2.0 s, imported at `write.py:29`). 4.0 s of socket waits worst case; the 5 s backstop already ruled for `connect` (wave-2 D14, `workers.py:28-33`) covers those same two numbers, so no second entry is added. |
| the send | `FunctionWorker` | **`"write"` = 10 s**, new | `write.set(confirm=True)` has three deadlined steps: `_authorize`'s `query_identity` (2.0 s, `write.py:93-94`), a fire-and-forget datagram that waits for nothing (`write.py:102-110`), and one read-back `request` (2.0 s, `write.py:119-121`). ~4 s worst case; 10 s is ~2.5× that — enough for a busy show network without letting a dead desk hold a dialog open. |

**Each dialog owns its own `CallRunner` for its pre-flight read; neither borrows the Console page's.** That matters
precisely because W1 allows writing while the page is `WATCHING`: the page's runner may legitimately be busy, and
`CallRunner.start` returns `False` when it is (`workers.py:112-113`), so a shared runner would refuse every read made
during a watch. Sends are a separate matter — they all go through the gate's single runner and queue (W10).
`CallRunner.cancel` settles from the UI's side at once and keeps the worker referenced until the thread really stops
(`workers.py:148-169`); the callable keeps running, its result discarded. **A cancel after the datagram has left the
socket does not un-send it** — why `console.write.cancelled` speaks only about the scene edit, and why Stop lets the
in-flight parameter finish. The countdown is a `QTimer` on the GUI thread: it counts seconds and touches no socket, so
`+5 s` cannot block the window.

### 7.2 Revert all, sequentially

**Every write goes through one `WriteQueue`** (`ui/write_queue.py`, non-Qt, owned by `WriteGate` — W10), so "one parameter
at a time" is enforced at the transport, not by the UI happening not to offer a second button. `RevertQueue`
(`ui/apply_level.py`, non-Qt) is the ordering on top of it, holding the reversed records and handing out **one at a
time**.

## 8. Safety — five gates

Not a promise; a structure. **No gate is claimed sufficient on its own**: gates 1, 2 and 3 check state that can go stale
between the check and the packet, which is why gate 4 re-checks before every send.

**8.1 The state gate.** `_ACTIONS` offers `"write"` in two states only (§6). The Doctor selector and the ledger read it
through `WriteGate`, owned and built by `live_wiring.py` beside the four signals it already connects
(`live_wiring.py:55-69`); neither imports `console_page`, so a Console page that failed to build cannot leave anything
enabled by accident, and the gate starts closed.

**8.2 The arm gate (F4).** Nothing writes, and Delayed/Immediate cannot even be *selected*, until `ArmWriteDialog` has
re-queried identity, had the show latch ticked and had the console's exact name typed. One arming covers the connection;
every `DISCONNECTED` / `LOST` / `ERROR` disarms. The latch text quotes `CLAUDE.md`:

> 🛑 **Live console over OSC — read freely, ask before writing.** […] Writing or pushing any
> parameter change to a live console reaches real audio at a venue — ask before writing to a live
> desk, and never during a show without explicit confirmation.

**8.3 The per-write gate.** In Manual and Delayed, a countdown to watch, extend or cancel (F5). **In Immediate there is no
per-write gate — that is the trade F3 buys**, and exactly why Immediate cannot be reached without arming and why the
selector falls back to Manual the moment the connection drops.

**8.4 The structural gate.** `live_write.send` accepts only a `WriteConfirmation`; a plain call raises. The AST scan in
`tests/test_ui_live_is_read_only.py` becomes an **allow-list of one path**, `wing_parser/ui/live_write.py`, keyed on
`path.name`, plus two assertions:

1. the allow-listed module's calls on a `wing_parser.net`-bound name are **only** `set`; `toggle`, `node_write` and `push`
   stay offences everywhere, including there;
2. every other `ui/` module still fails on any import or verb call reaching `net.write`, by the existing rules 1 and 2
   (`test_ui_live_is_read_only.py:115-159`).

**The allow-list exempts rule 1 entirely, and rule 2 for the single verb `set`.** That second half is not optional:
`live_write.py` exists in order to call `write.set(...)`, and rule 2 as written today (`:144-159`, against `WRITE_VERBS`
at `:41`) would flag exactly that call. Exempt for `set` and **nothing else** — `toggle`, `node_write` and `push` stay
offences in every file, that one included, which is what assertion 1 pins. Both rules walk whatever root they are handed,
so exemption and verb check behave identically in `UI_ROOT` and in a `tmp_path`.

**Gate 4's late re-check.** A countdown can run for a minute and the desk can go `LOST` underneath it (`RoundGuard` raises
`DeskLost` after three silent rounds, ~0.75 s at the default interval) without the dialog knowing. So **every** path —
Apply now, expiry, Immediate, each Revert-all step — re-asks `WriteGate.can_write()` and `ArmState.armed()` immediately
before building the `WriteConfirmation`; if either has closed, nothing is sent and `console.write.gate_closed` shows.
Checking a live-state gate once, at paint time, is the classic form of this bug.

**8.5 The identity/serial gate, inherited untouched.** `write.set(confirm=True)` calls `_authorize` (`write.py:93-100`)
before any packet: it re-queries identity and, if `WING_WRITE_ALLOW_SERIAL` (`write.py:33`) is set and does not match,
raises `SerialMismatchError` (`:36-37`). Wave 3 neither sets nor reads that variable, only surfaces its text as
`console.write.refused`.

## 9. Tests

### 9.1 Plain pytest, no socket, no console

`tests/test_net_address.py` — `leaf_parts` and `osc_address` over one root-strip: `ae_data.ch.1.send.8.mode` →
`/ch/1/send/8/mode`; `ae_data.ch.16.in.set.inv` → `/ch/16/in/set/inv`; every `path:` template in `repairs.yaml`, filled
with a plausible target, lands in `_leaves_from_raw`'s key set on the real fixture; and `ce_data.…`, a bare `ch.1.mute`,
an empty segment and an empty string each raise `ValueError` naming the input — from `leaf_parts`, and so from both
callers.

`tests/test_apply_level.py` — `ArmState` starts unarmed at `MANUAL` and `disarm()` returns it there from either other
level; `RevertQueue` hands out records in **reverse** order, one per `next()`, reports `progress` as `(done, total)`,
returns `None` after `stop()` **and** when exhausted, and a mid-run `stop()` leaves the remaining records untouched and
re-countable.

`tests/test_ui_live_write.py` — against a fake. **Reuse `tests/fake_desk.py`** (`FakeDesk` at `fake_desk.py:91`,
`_FakeClient.request` at `:57-59`, no socket anywhere): add a `write_transport()` returning a `WriteTransport` whose `set`
records the call, mutates `desk.leaves` and answers a real `SetResult`, so the read-back runs through the surface
`preflight` reads. Pinned:

- `preflight` returns the identity and the desk's current value; a `TimeoutError` from `identity` propagates untouched and
  no `set` is recorded;
- **normalisation, one test per JSON type**: a `,sfi` leaf at a boolean shape reads back `True`/`False`, **not** `1`/`0`,
  and compares equal to a journal `before` of `True`/`False` with **no** mismatch; a non-boolean `,sfi` stays `int`;
  `,sff` stays `float`; `,s` stays `str`;
- `send` transmits `confirm=True`, the mapped address and one value — one call, one address;
  `send(anything_but_a_WriteConfirmation)` raises and records nothing;
- **the three F8 outcomes, one test each**: `matched=True` → ✓ **and the scene leaf equals `after`, not the read-back** —
  pinned with a bool leaf whose read-back is `1` and a `-999.0` leaf whose read-back is `-144.0`, the two cases
  `_values_match` (`write.py:84-90`) calls matched; `False` with a `readback` → ⚠ **and the scene leaf is rewritten to
  `scene_value(parts, readback)`**; `False` with `readback=None` → ✗, `console.write.no_reply`, **scene leaf still holding
  what Repair set**;
- **`scene_value`, one test per JSON type**: a boolean-shape leaf coerces `1`/`0` to `True`/`False`, a non-boolean `,sfi`
  leaf keeps its `int`, `,sff` keeps its `float`, `,s` keeps its `str`;
- `SerialMismatchError` from a scripted `set` reaches the caller with its own text, and `revert_confirmation` carries the
  **desk-before captured at send time**, proven with a desk value differing from the journal's `before`.

`tests/test_live_state.py`, `tests/test_ui_workers.py` — the two pinned tests named in §6. `tests/test_apply_level.py`
also covers `WriteQueue`: FIFO order, exactly one item in flight, the next released only on the previous terminal signal,
two rapid enqueues both surviving (W10). `tests/test_ui_state_store.py` — `apply_delay` round-trips, appears in **both**
`DEFAULTS` and `normalize`, and a hand-edited `0`, `"five"` or `999` all normalise inside 3–60; `tests/test_ui_shell.py`
adds the **quit** half: set a delay, close the window, reload — `save_on_close` must not have erased it (MAJOR 2).
`tests/test_net_write.py` — two cases it lacks; its `set` coverage is all numeric (`:80`, `:87`, `:94`, `:101`), so add
`set(..., "PRE")` → `,s "PRE"` and `set(..., True)` → `,s "1"` (`write.py:74-75`) on the loopback fake it already uses.
`tests/test_ui_live_is_read_only.py` — amended per §8.4, including the planted-`push` case.

### 9.2 Qt, offscreen

`tests/test_ui_write_dialogs.py` — **Arm:** disabled on open; the latch alone does not enable it; the name alone does not;
both do; an identity failure shows `console.write.identity_failed` and leaves it disabled for that dialog's life.
**Delayed:** the countdown starts at the Settings value; `+5 s` adds five to the remainder, repeatably; **Apply now**
sends at once; **expiry sends**; **Cancel sends nothing and leaves the journal `Patch` in place**; the mismatch line
appears only when the desk value differs from the journal's `before`. **Gate 4:** with a dialog open, close the gate (or
disarm) and let the countdown expire → nothing sent, no `set` recorded, `console.write.gate_closed`.

`tests/test_ui_write_dialogs.py` also pins **modality** (both dialogs report `Qt.ApplicationModal`, W11) and that a
Revert-all countdown's **Cancel stops the whole run** with `console.write.revert_cancelled`, leaving the already-sent
reverts in place (W12).

`tests/test_ui_changes_send.py` — the selector offers Delayed/Immediate only when armed and falls back to Manual on
disarm; Manual's row button is disabled by a **closed gate only**, stays enabled while unarmed, and when clicked unarmed
opens `ArmWriteDialog` before the countdown; Immediate's Repair produces exactly one `set` with no dialog; a successful
send appends one ledger row; Undo removes the journal row and **leaves the ledger row with its Revert button**; the dock
stays visible with a clean session and a non-empty ledger (`main_window.py:181`); **Revert all** sends in reverse with
**never more than one `set` in flight**, **Stop** between parameters leaves the remainder untouched while the in-flight
one completes, the selector and Arm stay disabled for the run and are re-enabled by Stop (W14), and a successful revert
puts the scene leaf back so **the finding reappears** while the `Patch` stays (W13). `tests/test_ui_texts.py` and
`tests/test_ui_settings.py` cover the `console.write.*` keys and the delay row. Per the wave-2 practice (that spec's §9.1,
line 332): **each new test is shown red once** by reverting the production line it covers, failure captured.

### 9.3 Acceptance — human only, needs the real desk

Against **WING-GIAQUY, `192.168.128.28`**, from `dist\wing-ui.exe`, **WING-Edit connected throughout**. Record the output
whatever it says. ToanAZ must look at the screenshots — wave 1's gate.

- [ ] Connect → lamp green, identity matches `wing net identity`. Pull → Doctor fills. The selector reads **Manual**;
      Delayed and Immediate are greyed out.
- [ ] **Arm:** the dialog names the desk *with the serial* `wing net identity` prints. **Wrong name** `WING-GIAQUI` → Arm
      greyed, `console.write.name_wrong`. **Latch unticked**, correct name → Arm greyed. Tick and type → Arm enables, all
      three levels become selectable.
- [ ] **Manual:** Repair a **G8** finding (a send to a monitor bus in POST, `repairs.yaml:19-23`) → nothing reaches the
      desk. Click the row's Send → countdown; press **+5 s** three times and watch the remainder grow; **Cancel** →
      nothing written, WING-Edit unchanged, journal row intact.
- [ ] **Delayed:** Repair the same finding → the countdown opens itself at the Settings default. Let it **expire** →
      `sent ✓`, and **WING-Edit shows that send flip to PRE**. Repair another, press **Apply now** → it lands without waiting.
      **Immediate:** select it, Repair a third finding → it lands with no dialog at all, badge ✓.
- [ ] **Bool normalisation:** repair a `to: false` finding (R1, `repairs.yaml:52-55`) in Delayed → the dialog reads
      `True`/`False`, **never `1`/`0`**, no mismatch warning on an untouched desk. **Mismatch:** move that parameter on
      WING-Edit before applying → `console.write.mismatch`, both values shown. **Clamp:** aim a numeric leaf outside the
      desk's range → badge ⚠, `console.write.clamped` with both numbers, **and Doctor's finding reflects the value the
      desk actually took** (F8). If no shipped repair produces one, do it once with `wing net set --confirm` and check the
      app renders the same `SetResult` shape. **No reply:** aim at an address this console lacks → badge ✗,
      `console.write.no_reply`, scene leaf still holding what Repair set.
- [ ] **Revert** one ledger row → the desk returns to the captured before-value; one countdown in Delayed, instant in
      Immediate. **Revert all**, five or more rows → reverse order, progress counting `3/7`, **WING-Edit never showing two
      moving at once**, and in Delayed **one countdown per parameter**. **Stop** mid-run → ends after the current one, the
      rest visibly left.
- [ ] **Serial mismatch:** relaunch with `WING_WRITE_ALLOW_SERIAL` wrong, arm, apply → badge `console.write.refused` with
      `_authorize`'s text, **WING-Edit unchanged**. **LOST mid-countdown:** in Delayed, start a watch, Repair, unplug the
      desk while the countdown runs → on expiry **nothing is sent**, `console.write.gate_closed` shows, and the selector
      has fallen back to **Manual** (F4).
- [ ] Coexistence: WING-Edit stays connected and usable throughout. Every affected surface screenshotted **from the exe**,
      and ToanAZ has looked at them.

## 10. Task sketch

For the plan writer. One fresh implementer per task, a reviewer after each; ordered so each is independently testable, and
cut so no file crosses the 200-line ceiling. Re-measure the suite on this wave's first commit rather than quoting wave 2's
**1580 passed / 3 skipped at `dcf897a`**.

| # | Task | Files |
|---|---|---|
| 1 | `leaf_parts` and `osc_address`, sharing one root-strip, with their `ValueError` cases; the repairs.yaml sweep; the `_leaves_from_raw` cross-check on a real fixture; `_flatten` refactored onto it **or** a written reason not to | `net/address.py`, `cli/net_commands.py`, `tests/test_net_address.py` |
| 2 | `ApplyLevel`, `ArmState`, `RevertQueue`, `WriteQueue` — the whole non-Qt policy layer, exhaustively tested | `ui/apply_level.py`, `ui/write_queue.py`, `tests/test_apply_level.py` |
| 3 | `WriteTransport` (incl. the `jsontypes` normalisation), `WriteConfirmation`, `SentWrite`, `preflight`, `send`, `FakeDesk.write_transport()`, the two missing `write.set` str/bool cases — **and, in the same commit, the AST allow-list amendment**, so the suite is never red between tasks | `ui/live_write.py`, `tests/fake_desk.py`, `tests/test_ui_live_write.py`, `tests/test_net_write.py`, `tests/test_ui_live_is_read_only.py` |
| 4 | F8: `scene_value`, the three outcomes and what each does to the scene leaf, `revert_confirmation` | `ui/live_write.py`, tests |
| 5 | `TIMEOUTS["write"] = 10` **and** `"write"` in the two `_ACTIONS` rows; both pinned tests named in §6 must be updated | `ui/workers.py`, `ui/live_state.py`, their tests |
| 6 | F6: split `settings_dialog.py` into `settings_io.py` **first**, then the 3–60 delay row; `apply_delay` in all four places — `DEFAULTS`, `normalize`, `restore`, `save_on_close` | `ui/settings_io.py`, `ui/settings_dialog.py`, `ui/state_store.py`, `ui/window_state.py`, tests |
| 7 | The `console.write.*` strings | `ui/texts_write.py`, `ui/texts.py`, `tests/test_ui_texts.py` |
| 8 | **`WriteGate`** + `ArmState` + the `WriteQueue` **owned and built in `live_wiring.py`**, fed by the Console page's state, disarming on `DISCONNECTED`/`LOST`/`ERROR`; `main_window.py` gains only the one call. **Before the dialogs**, because both re-check this gate | `ui/live_wiring.py`, `ui/main_window.py`, tests |
| 9 | `ArmWriteDialog`: own `CallRunner` for the pre-flight read, fresh identity, latch, typed name, `ApplicationModal` | `ui/write_arm_dialog.py`, `tests/test_ui_write_dialogs.py` |
| 10 | `DelayedWriteDialog`: values, mismatch line, countdown + progress, Apply now / +5 s / Cancel, expiry-applies, `ApplicationModal`, and the gate-4 re-check against task 8's gate | `ui/write_delay_dialog.py`, tests |
| 11 | The Doctor apply-level selector **and the Arm button**; Repair routing for all three levels | `ui/doctor_page.py`, `ui/detail_panel.py`, tests |
| 12 | `changes_send.py`: the per-row Send button and the result badges | `ui/changes_send.py`, `ui/changes_panel.py`, `tests/test_ui_changes_send.py` |
| 13 | `changes_ledger.py`: the sent ledger, per-row Revert, Revert all through the `RevertQueue`, the progress line, Stop, and the W14 disabling | `ui/changes_ledger.py`, tests |
| 14 | Exe rebuild + screenshots of every affected surface; docs (`docs/user-manual/`, ROADMAP, `docs/tech-debt.md`) and the handoff for §9.3 and the open questions | `packaging/`, docs |
| 15 | **D-41** and **D-42** — the two `net/` debt items, one commit each (W9; droppable) | `net/snapshot.py`, `net/watch/list.py`, `net/watch/poller.py`, tests |
| 16 | **Whole-branch review on the strongest model.** ROADMAP §7; it has earned its cost five cycles running. | — |

## 11. Open questions for ToanAZ — only those that change what gets built

**Answered 2026-09-25**, in chat — all three keep their default, now as a decision rather than an assumption:

1. **Should Immediate be allowed while `WATCHING`, or only when merely `CONNECTED`?** Default: allowed (W1) — watching the
   desk confirm a write is the natural order at a venue. Forbidding it turns one `frozenset` row into a level-aware gate
   check; decided before task 5.
   **Answer (ToanAZ, 2026-09-25): ALLOWED — keep the default.**
2. **In Delayed, should Revert all use one countdown for the whole batch instead of one per parameter?** Default: one per
   parameter, because that is what "delayed" literally asked for and each revert is still its own packet.
   One-for-the-batch is friendlier for seven rows and is a different dialog; decided before task 13.
   **Answer (ToanAZ, 2026-09-25): ONE COUNTDOWN PER PARAMETER — keep the default.**
3. **Should arm state survive a reconnect to the *same serial*?** Default: no — every `DISCONNECTED` / `LOST` / `ERROR`
   disarms, and a dropout at a venue is exactly when the operator should re-confirm which desk he is on. Keeping it means
   `ArmState` holds the serial and `live_wiring` compares on reconnect — small, but it weakens gate 2.
   **Answer (ToanAZ, 2026-09-25): NOT KEPT — re-arm on every reconnect. Keep the default.**

## 12. Out of scope

`push` (whole-scene — F1). `node_write` (several parameters per packet — F1), including as a Revert-all optimisation. Any
`ce_data` / `$ctl` address (W2). A raw address+value box (wave 2's D15: a dev-mode probe, not a show affordance). A
durable write log (W8). Remembered arm state across runs. A watch-list editor (wave 2 D12). Auto-connect (wave 2 §11 q3,
still no). Metering and the native transport. Subscription (a closed negative on the real desk, 2026-08-23). Language
switching. Mac packaging.