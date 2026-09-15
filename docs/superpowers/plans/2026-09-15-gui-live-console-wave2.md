# GUI wave 2 — the live console page — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` (recommended)
> or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** One **Console** page in `wing-ui` that connects to a WING desk, discovers its shape, pulls the
running state into a `Session` indistinguishable from an opened `.snap`, exports it, and watches it live —
read-only, with a mouse, at a venue.

**Architecture:** Two non-Qt modules hold every decision — `ui/live_state.py` (the transition table) and
`ui/live_controller.py` (the `Transport` seam, `pull`'s two ported guards, `RoundGuard`) — so plain pytest
with no socket covers them. Four small Qt widgets assemble into `console_page.py`. Nothing under
`wing_parser/net/` is modified, and an AST test enforces that no write path reaches `wing_parser/ui/`.

**Tech Stack:** Python, PySide6, pytest (`QT_QPA_PLATFORM=offscreen`), PyInstaller. **Spec:** `docs/superpowers/specs/2026-09-15-gui-live-console-wave2-design.md` — D1–D17 in §5, page design
§6, controller and threading §7, safety §8, tests §9, task sketch §10, open questions §11. Every "why" below
points at a section there rather than repeating it.

## How to start (branching — read this first)

PR #1 `fix/ui-debt-wave1b-leftovers` (<https://github.com/toanaz-ops/project008-soundtech-assist/pull/1>,
open) fixes two `tests/test_ui_import_page.py` key-status tests that **fail on a clean `main`** (D-30,
placeholder-key masking), so a wave-2 branch cut from `main` starts red and no implementer can tell their
own breakage from the inherited one.

- [ ] Cut the branch from **that branch's head**, not `main`: `git worktree add <path> -b
      feature/gui-live-console-wave2 fix/ui-debt-wave1b-leftovers`
- [ ] Open the wave-2 PR with **base `fix/ui-debt-wave1b-leftovers`** — a stacked PR, so its diff shows only
      wave-2 work. The moment PR #1 merges, **retarget to `main`** (`gh pr edit <n> --base main`).
- [ ] Task 1 re-measures the suite on its own first commit and puts that number in the PR body. The last
      recorded figure — 1433 passed / 3 skipped at `04db887`, 2026-08-26 — is **historical**; do not quote
      it forward.

## Global Constraints

- **`$PY` below means** `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe"`, run from
  your worktree's repo root. **Never add `-q`**: `pyproject.toml` sets it, and `-qq` kills the summary line.
- **No socket in any test.** Everything talks to `FakeDesk` (Task 1). `tests/fake_wing.py` stays the
  loopback fake for `net/`'s own tests and is not used here.
- **`wing_parser/net/` is not modified by this wave** — not one line — and **no write path**:
  `wing_parser/net/write.py` is never imported under `wing_parser/ui/` (Task 14).
- ~200-line **file** ceiling, split by responsibility. Each task's **Files** line gives the current count of
  every existing file it touches, measured on `d28e00f`.
- Every user-facing string goes through `ui/texts.py`, namespace `console.*` (D17).
- Every colour is a token. `test_ui_house_style.py::test_no_colour_literals_outside_the_theme_package` scans
  every `.py` **and `.qss`** under `wing_parser/ui/` outside `ui/theme/` with an **empty allowlist** — a new
  QSS rule uses `$ok` / `$warn` / `$danger` / `$faded`, never a hex value.
- UTF-8 explicit on every file read and write (`encoding="utf-8"`).
- **A claim about another module is checked by opening that module.** ROADMAP §7: ten instances of one
  defect shape — correct code carrying a false description — landed in G2a, every one caught in review and
  **none by a test**. Each task ends with the claims to check.

## Review cadence (ROADMAP §7)

A **fresh reviewer after every task**, which may *run* the code and not only read it; a **scoped re-review
per fix round** over only the files that fix touched; and **Task 18, the whole-branch review on the
strongest model** — it has earned its cost four cycles running. Not optional polish.

## Sequencing

**Tasks 2, 3, 4, 5 all edit `wing_parser/ui/live_controller.py`: they run sequentially, in order, on one
implementer** — separate tasks for review granularity, not for parallelism. Otherwise: Task 1 → 2; 6, 7 and
14 are free; 8 → 9–13; 11 also needs 4 and 7; 12 also needs 5 and 6; 13 needs 9–12.

**Files this wave creates:** `ui/live_state.py` (~80, no Qt) · `ui/live_controller.py` (~170, `Transport`, connect/discover/pull,
`RoundGuard`, no Qt) · `ui/live_connect_bar.py` (~110) · `ui/live_discovery.py` (~110) ·
`ui/live_snapshot.py` (~120) · `ui/live_events_view.py` (~120) · `ui/live_wiring.py` (~40) ·
`ui/console_page.py` (~170) · `tests/fake_desk.py` (~90, the shared in-memory desk).

### Task 1: The state machine, and the `FakeDesk` every later test uses

**Files:** create `wing_parser/ui/live_state.py`, `tests/fake_desk.py`, `tests/test_live_state.py`,
`tests/test_fake_desk.py`. Read spec §6 and §9.1 first.

**Produces:** `LiveState` (enum: `disconnected connecting connected walking pulling watching error lost`) ·
`transition(state, event) -> LiveState`, which **raises `ValueError` on an illegal pair, naming state and
event, rather than silently staying put** · `allowed_actions(state) -> frozenset[str]` over `{connect,
disconnect, discover, pull, export, watch, stop, rerun}`. Events: `connect ok fail disconnect reset walk
pull watch stop lost`. And `tests/fake_desk.py`, the **only** desk any test in this wave sees:

```python
class FakeDesk:
    """Everything live_controller can reach, in memory. No socket anywhere.

    identity   : WingIdentity | Exception   -- returned, or raised
    leaves     : dict[str, OscMessage]      -- the console's whole surface
    unresolved : tuple[str, ...]            -- what the walk could not resolve
    strips     : dict[str, int]             -- per-family counts for the WatchList
    rounds     : list[dict[str, object]]    -- scripted samples, consumed one per get_many;
                 an EMPTY dict is a round the desk ignored, and a list that runs out
                 repeats its last entry forever
    calls      : list[tuple[str, int]]      -- ("get_many", len(addresses)), in order
    """
    def transport(self): ...          # -> live_controller.Transport; imports live_controller
                                      #    INSIDE the method, so this file stands alone now
    def client(self, host=None): ...  # -> _FakeClient: get_many/request/close/__enter__/__exit__
```

`_FakeClient.get_many(addresses, **kw)` returns a real `net.client.BatchResult(replies=…, unresolved=…)`
holding real `net.codec.OscMessage` objects built directly — `OscMessage("/ch/1/$fdr", "sff", ("-6.0", 0.5,
-6.0))` for a float leaf, `("sfi", ("1", 0.0, 0))` for a list leaf, `("s", ("KICK",))` for a name — because
`leaf_value` (`codec.py:107`) takes `args[-1]` for `,sff`, `int(args[0])` for `,sfi` and `args[0]` for `,s`.

- [ ] **1. Failing tests.** `test_live_state.py`: `test_every_documented_pair_reaches_its_documented_target`,
      `test_an_illegal_pair_raises_naming_the_state_and_the_event`,
      `test_allowed_actions_is_pinned_for_every_state` (one written-out assertion per state),
      `test_lost_is_not_error_because_it_still_allows_reconnect`. `test_fake_desk.py`:
      `test_get_many_returns_real_batchresult_objects`, `test_a_scripted_round_is_consumed_once_per_get_many`,
      `test_an_exhausted_round_list_repeats_its_last_entry`,
      `test_calls_records_the_address_count_of_every_round`.
- [ ] **2. Run → FAIL** (`ModuleNotFoundError`). **3. Implement** as one `_TABLE: dict[tuple[LiveState,
      str], LiveState]` and one `_ACTIONS: dict[LiveState, frozenset[str]]` — no `if` chains, because a
      table is the only shape a test can exhaust.
- [ ] **4. Run → PASS**, then the full suite; **put that count in the PR body as the baseline.**
- [ ] **5. Show each new test red once** (live-watch design §4.3): revert one table entry, capture the
      failure, restore; paste both into the task report. **6. Commit.**

**Verify:** `$PY -m pytest tests/test_live_state.py tests/test_fake_desk.py`
**Commit:** `feat(ui): add the live connection state machine and the FakeDesk double` — body names spec §6
and §9.1.
**Check by opening:** `BatchResult`'s fields `replies`/`unresolved` (`net/client.py:76-88`); `OscMessage` is
`(address, typetag, args)` (`net/codec.py:19-23`); `leaf_value`'s per-tag rule (`net/codec.py:107-135`).

### Task 2: `Transport` seam, `connect`, `discover`

*Sequential block 2→5.* **Files:** create `wing_parser/ui/live_controller.py`,
`tests/test_live_controller.py`. Read spec §7.1 and `ui/import_controller.py` (143 lines), the precedent.

```python
@dataclass(frozen=True)
class Transport:
    identity: Callable[[str], WingIdentity]     # net.identity.query_identity
    walk:     Callable[[str], WatchList]        # net.watch.list.build_watch_list
    snapshot: Callable[[str], SnapshotResult]   # net.snapshot.take_snapshot
    client:   Callable[[str], WingClient]       # net.client.WingClient

REAL = Transport(...)                           # the ONLY place net/ is named
def connect(host: str, transport: Transport = REAL) -> WingIdentity: ...
def discover(host: str, transport: Transport = REAL) -> WatchList: ...
```

Both let `TimeoutError` / `ValueError` through **untranslated** — one error line, no second taxonomy (the
`import_controller.read_with` precedent); `IdentityError` is already a `ValueError` (`net/identity.py:29`).
`discover` returns the `WatchList` **as-is**: it already carries `addresses`, `unresolved` and a per-family
`strips` count, so there is nothing to reshape.

- [ ] **1. Failing tests:** `test_connect_returns_the_desks_identity`,
      `test_connect_lets_a_timeout_through_untranslated`,
      `test_connect_lets_a_malformed_reply_raise_identityerror`,
      `test_discover_returns_the_watchlist_untouched`,
      `test_discover_reports_the_families_the_walk_could_not_resolve`,
      `test_real_transport_names_only_read_only_entry_points` (the four attribute names, and
      `REAL.identity is query_identity`).
- [ ] **2. Run → FAIL. 3. Implement. 4. Run → PASS** + full suite. **5. Show each new test red once**;
      capture. **6. Commit.**

**Verify:** `$PY -m pytest tests/test_live_controller.py`
**Commit:** `feat(ui): add the live transport seam with connect and discover` — body names spec §7.1 and D2:
Connect is the WING? handshake, the only call that fails loudly, because OSC on 2223 is UDP.
**Check by opening:** `query_identity`'s 2.0 s socket timeout and its `TimeoutError` wrap
(`net/identity.py:68-85`); `build_watch_list` (`net/watch/list.py:67-111`); `take_snapshot`
(`net/snapshot.py:69-75`).

### Task 3: `pull` — **both** of `_load()`'s guards, ported

*Sequential block 2→5.* **Files:** modify `wing_parser/ui/live_controller.py`,
`tests/test_live_controller.py`. Read `wing_parser/cli/commands.py:17-80` first — the original, comments
included.

**Produces:** `EmptyReadError(OSError)` carrying host, node count and leaf count ·
`pull(host, transport=REAL) -> SnapshotResult` · `incomplete_report(result) -> str | None`.

`pull` raises `EmptyReadError` when `not result.raw.ae and not result.raw.ce` (`cli/commands.py:47`).
**Without it, Pull against an unreachable desk returns a valid empty scene, the advisory truthfully finds
nothing wrong with nothing, and Doctor shows "No findings." for a desk never reached** — what `doctor
--live` did before the guard existed. It reports **both** counts, because `walk_schema` runs first and can
succeed while every later leaf read times out. `incomplete_report` returns `None` on a clean read — **that
silence is deliberate**, a warning printed every time teaches the reader to skip it — and otherwise names
both counts plus the node names (`:63-78`).

- [ ] **1. Failing tests:** `test_pull_against_a_silent_desk_raises_naming_host_and_both_counts` (host, node
      count and leaf count each in `str(exc)`, and **no `Session` is built**),
      `test_pull_returns_the_snapshot_result_on_a_clean_read`,
      `test_incomplete_report_is_none_on_a_clean_read`,
      `test_incomplete_report_names_the_counts_and_the_node_names`,
      `test_pull_lets_an_oserror_from_the_transport_through`.
- [ ] **2. Run → FAIL. 3. Implement** — port the guards as functions; do **not** import them from
      `cli.commands`, which prints to stderr and returns exit codes. **4. Run → PASS** + suite.
- [ ] **5. Show each new test red once**; capture. **6. Commit.**

**Verify:** `$PY -m pytest tests/test_live_controller.py`
**Commit:** `feat(ui): carry both live-read guards into the UI pull path` — body names spec §7.1.
**Check by opening:** the guard's condition and both counts (`cli/commands.py:47-62`); `SnapshotResult`'s
three fields (`net/snapshot.py:54-66`); that `RawScene.ae`/`.ce` are the dicts it tests (`:90-108`).

### Task 4: `session_from_snapshot`, `suggested_name`, and the two parity tests

*Sequential block 2→5.* **Files:** modify `wing_parser/ui/live_controller.py`,
`tests/test_live_controller.py`. Read `ui/session.py` (96 lines) and `net/export.py:66` first.

**Produces:** `session_from_snapshot(result, identity, profile=None) -> tuple[Session, str]` — take
`text = net.export.to_snap_json(result.raw, identity)`, then
`Session(json.loads(text), Path(suggested_name(identity, host)), profile)`, returning the session and that
pull-time text as the untouched original · `suggested_name(identity, host) -> str`, e.g.
`"WING-GIAQUY-20260915-1432.snap"`, falling back to `"wing-192.168.128.28-….snap"`. **A bare filename, no
directory:** it names nothing on disk (D4).

**D3, the decision this task encodes:** Export writes `Session.save_as`, **not** the pull-time bytes.
`save_as` writes the *patched* document (`ui/session.py:92-96` → `_document()` at `:43-44`), so a repair
made after the pull is in the exported file; exporting the pull-time bytes would silently drop every repair.

- [ ] **1. Failing tests:** `test_a_pulled_session_carries_findings_and_channels_like_an_opened_file` — the
      wave's whole claim in one test: `session.findings()` non-empty and `session.scene.channels()`
      populated; `test_export_writes_the_repaired_document_not_the_pull_time_bytes` — repair a **named**
      finding, `save_as(tmp_path/"out.snap")`, reopen with `Session.open`, assert the repair is in the file
      **and** still absent from the pull-time original string;
      `test_suggested_name_uses_the_desk_name_when_identity_is_known`,
      `test_suggested_name_falls_back_to_the_host_without_identity`,
      `test_the_suggested_name_is_a_bare_filename_with_no_directory`.
- [ ] **2. Run → FAIL. 3. Implement.** Build this test's `FakeDesk.leaves` from a real fixture —
      `user-files/example-Vu.snap` — or the smallest `RawScene` that yields a repairable finding; the test
      names the finding it repairs, so it cannot pass vacuously.
- [ ] **4. Run → PASS** + suite. **5. Show each new test red once**; capture. **6. Commit.**

**Verify:** `$PY -m pytest tests/test_live_controller.py`
**Commit:** `feat(ui): turn a pulled snapshot into an ordinary Session` — body names spec D3 and §7.1.
**Check by opening:** `Session.__init__(document, path, profile)` and that `save_as` writes the *patched*
`_document()` (`ui/session.py:29-34, 43-44, 92-96`); `to_snap_json(raw, identity=None)` (`net/export.py:66`).

### Task 5: `RoundGuard` — cancel before the round, desk-lost after it — and `watch_rate`

*Sequential block 2→5, last in it.* **Files:** modify `wing_parser/ui/live_controller.py`,
`tests/test_live_controller.py`. Read all 123 lines of `wing_parser/net/watch/poller.py` first.

```python
class Cancelled(Exception): ...
class DeskLost(OSError):                       # (host, rounds)
class RoundGuard:          # wraps a WingClient, delegating get_many/request/close/__enter__/__exit__
    def __init__(self, client, host: str, cancel: threading.Event,
                 on_round: Callable[[int, int], None] = lambda a, t: None,
                 lost_after: int = 3) -> None: ...
def watch_rate(events: int, seconds: float) -> tuple[float, float]: ...   # rate, elapsed
```

**Before** every `get_many`: cancel set → raise `Cancelled`. This check **cannot** live in the injected
`sleep`, because `poller.py:121-123` sleeps only when `remaining > 0` — on a desk slower than the interval
the sleep is never reached and a cancel would never be observed; stop latency is bounded by one round
instead. **After** every `get_many`: record `answered=len(result.replies)` against `total=len(addresses)`,
call `on_round(answered, total)`, and on the third consecutive `answered == 0` raise `DeskLost`. Raising is
required — `poller.watch` yields only on a `Change` (`:101-114`) and a dead desk produces none, because the
poller carries the previous value forward for a silent address on purpose (`:116-119`).

**Correction to spec §9.1's sketch, found by opening the poller:** `watch` calls `read_labels` **first**
(`:84`) — one `get_many` over one `/<strip>/name` address per strip, **84** for the shipped list, not 220 —
then a priming `sample` (`:86`), then the loop (`:99`). `RoundGuard` counts every delegated `get_many`, so
on a dead desk `on_round` sees `(0, 84)`, `(0, 220)`, `(0, 220)` and `DeskLost` lands on the loop's **first**
round. Assert that triple, not `(0, 220)` three times.

- [ ] **1. Failing tests:** `test_the_guard_raises_desklost_on_the_third_consecutive_empty_round` — drive
      the **real** `poller.watch` with a `FakeDesk` whose `rounds` go empty; assert the raise, assert
      **zero** `Change`es were produced before it (why D6 could not be output-driven), and assert `on_round`
      recorded `[(0, 84), (0, 220), (0, 220)]`; `test_one_answering_round_resets_the_lost_counter`;
      `test_the_guard_raises_cancelled_before_the_next_round` — set the event, assert the next `get_many`
      raises, with `interval=0` so the injected `sleep` is provably not what stopped it;
      `test_the_guard_delegates_request_close_and_the_context_manager_pair`;
      `test_watch_rate_returns_events_per_second_and_elapsed`,
      `test_watch_rate_is_zero_rather_than_a_zero_division_at_time_zero`.
- [ ] **2. Run → FAIL. 3. Implement. 4. Run → PASS** + suite.
- [ ] **5. Show each new test red once** — in particular move the cancel check to *after* the `get_many` and
      watch the cancel test fail; capture. **6. Commit.**

**Verify:** `$PY -m pytest tests/test_live_controller.py`
**Commit:** `feat(ui): judge and interrupt a watch inside one RoundGuard` — body names spec §7.1 and D6.
**Check by opening:** `read_labels` runs before the first sample, one address per strip (`poller.py:82-86`);
the carry-forward (`:116-119`); the conditional sleep (`:121-123`); and the arithmetic — `watchlist.yaml`
gives ch/bus/main/mtx three keys and dca one, so 40·3 + 16·3 + 4·3 + 8·3 + 16·1 = **220** addresses over
**84** strips.

### Task 6: `GeneratorWorker`, and the three new timeout budgets

**Files:** modify `wing_parser/ui/workers.py` (**158 lines**), `tests/test_ui_workers.py` (**278 lines**).
If `workers.py` crosses ~200, move the class to `ui/generator_worker.py` and say so in the commit body —
this is the one task where an existing file is genuinely near the cap.

**Produces:** `TIMEOUTS` gains `"connect": 5, "walk": 60, "snapshot": 90` beside `proposal`/`guesses`/
`probe`, and `GeneratorWorker(QThread)` with signals `produced(object)` (one `Change`),
`progress(int, int)` (answered, total, from `RoundGuard.on_round`), `finished(object)` (a summary: rounds,
events, seconds), `failed(object)` (`DeskLost`, or any `OSError`/`ValueError`) and `finished_cancelled()`.

It iterates `poller.watch(guard, watch_list, interval=…)` and emits per item, holding **no** desk-lost or
cancel logic of its own — both live in `RoundGuard`, non-Qt and therefore covered by plain pytest. Its only
jobs: translate `Cancelled` → `finished_cancelled` and `DeskLost` → `failed`, and keep the thread referenced
until it really stops, the way `CallRunner._settle` does (`workers.py:152-157`). Budgets (§7.2): connect
**5 s**, a backstop over `query_identity`'s own 2.0 s socket timeout; walk **60 s**, ~60× the measured
~1.00 s clean walk; snapshot **90 s**, 9× the measured ~10 s whole-console read.

- [ ] **1. Failing tests:** `test_generator_worker_emits_every_produced_item_in_order`,
      `test_generator_worker_reports_cancelled_separately_from_failed`,
      `test_generator_worker_turns_desklost_into_failed`,
      `test_generator_worker_keeps_a_stopped_thread_referenced`,
      `test_the_three_live_budgets_are_the_ruled_numbers` (pin 5/60/90 by value). Drive it with a plain
      generator function, not a desk — the worker is transport-agnostic.
- [ ] **2. Run → FAIL. 3. Implement. 4. Run → PASS** + suite. **5. Show each new test red once**; capture.
      **6. Commit.**

**Verify:** `$PY -m pytest tests/test_ui_workers.py`
**Commit:** `feat(ui): add a generator worker and the live call budgets` — body names spec §7.2, §7.3 and
D5: a 220-leaf round costs tens of milliseconds at best and ~0.4 s against a stale list.
**Check by opening:** `CallRunner.start` returns `False` while a call runs, so connect/discover/pull cannot
interleave (`workers.py:100-101`); the retired-worker list (`:152-157`); `FunctionWorker`'s
exactly-one-terminal-signal contract (`:37-71`).

### Task 7: A remembered list of console addresses in the state store

**Files:** modify `wing_parser/ui/state_store.py` (**68 lines**), `tests/test_ui_state_store.py`
(**159 lines**).

**Produces:** `DEFAULTS` gains `"consoles": []` · `remember_console(consoles, host) -> list[str]` (capped at
`MAX_RECENT`, 8) · `forget_console(consoles, host) -> list[str]`.

**Two traps, both read straight out of the module.** `normalize` (`state_store.py:26-37`) rebuilds a
**fixed dict**, so a field not added there is **silently dropped on save** — `consoles` goes into
`normalize`, `DEFAULTS` and `load`'s fallback, or it does not persist at all. And `remember_recent`
(`:61-64`) compares entries with `Path()`, right for files and wrong for addresses; `remember_console`
compares plain strings.

- [ ] **1. Failing tests:** `test_consoles_survive_a_save_and_load_round_trip`,
      `test_a_state_file_without_consoles_degrades_to_an_empty_list`,
      `test_remember_console_moves_an_address_to_the_top_without_duplicating_it`,
      `test_remember_console_caps_the_list_at_max_recent`,
      `test_remember_console_compares_plain_strings_not_paths`,
      `test_forget_console_removes_only_that_address`.
- [ ] **2. Run → FAIL. 3. Implement. 4. Run → PASS** + suite. **5. Show it red once** by deleting the
      `consoles` line from `normalize` and watching the round-trip test fail — the silent-drop trap,
      demonstrated. **6. Commit.**

**Verify:** `$PY -m pytest tests/test_ui_state_store.py`
**Commit:** `feat(ui): remember the console addresses an operator has used` — body names spec D10.
**Check by opening:** `normalize`'s fixed rebuild (`state_store.py:26-37`); the `Path()` comparison
(`:61-64`); that `save` writes through `normalize` (`:52-58`).

### Task 8: Register the page — texts, keys, icon, Ctrl+7

**Files:** modify `wing_parser/ui/texts.py` (**130 lines**), `ui/state_store.py` (**68 + Task 7**),
`ui/main_window.py` (**183 lines** — two dict entries and one page-construction line, nothing else, which is
why Task 11's wiring lives in its own module), `tests/test_ui_shell.py` (**53**), `tests/test_ui_texts.py`
(**23**).

`PAGE_KEYS` gains `"console"` **last** (sidebar row 7); `PAGE_ICONS` gains
`"console": "fa5s.network-wired"`; `TEXTS` gains `"page.console": "Console"`. **Ctrl+7 needs no new code** —
`menus.build_accelerators` already binds `Ctrl+{index}` over `PAGE_KEYS` (`menus.py:55-59`), and the sidebar
label comes from `text(f"page.{key.removesuffix('_')}")` (`main_window.py:83`). The namespace is `console.*`
and **not** `live.*` (D17): `texts.py:18` already holds `"overview.live": "Live channels"`, meaning unmuted
channels. Module filenames stay `live_*`.

- [ ] **1. Failing tests:** rename `tests/test_ui_shell.py:16` `test_sidebar_lists_six_pages_in_order` →
      `..._seven_pages_in_order`, with `"console"` appended to the expected list; add
      `test_ctrl_7_switches_to_the_console_page` (emit the `QShortcut`'s `activated`, as the existing
      accelerator tests do); add `assert text("page.console") == "Console"` to `test_known_keys_resolve`.
- [ ] **2. Run → FAIL. 3. Implement** — register a temporary `EmptyState("Console")` from `ui/page_base.py`
      as the page body; Task 13 replaces it with `ConsolePage`.
- [ ] **4. Run → PASS** + suite. `ui/__main__.py:95-112` screenshots `PAGE_ORDER`, so the page is captured
      with no change to that loop — confirm a `console.png` appears. **5. Commit.**

**Verify:** `$PY -m pytest tests/test_ui_shell.py tests/test_ui_texts.py`
**Commit:** `feat(ui): register the Console page as the seventh sidebar row` — body names spec D9 and D17.
**Check by opening:** the `Ctrl+{index}` loop (`menus.py:55-59`); the label derivation including
`removesuffix("_")` (`main_window.py:82-85`); the screenshot loop (`ui/__main__.py:95-112`); that
`normalize` validates `page` against `PAGE_KEYS` (`state_store.py:33`), so a saved `"console"` page only
survives a restart after this change.

### Task 9: `ConnectBar` — address combo, Connect/Disconnect, the lamp

**Files:** create `wing_parser/ui/live_connect_bar.py`, `tests/test_ui_console.py`; modify
`wing_parser/ui/resources/theme.qss` (**155 lines**). Read `ui/call_button.py` (82) and
`ui/theme/widgets.py` (36) first.

**Produces:** `ConnectBar(QWidget)` — `connected = Signal(object)` (a `WingIdentity`),
`failed = Signal(object)`, `disconnected = Signal()`, `host() -> str`, `set_state(state)`. Connect runs
through `CallRunner` + `ButtonRunner` under kind `"connect"`; tests pass `timeout=0` so none waits real
seconds (`workers.py:97-99`).

**The lamp, and a trap spec §6 does not mention.** The lamp is a `QLabel` whose `azStyle` is set with
`theme.widgets.set_style` (`widgets.py:17-22`): `disconnected` → `faded`, `connecting`/`walking`/`pulling` →
`warn`, `connected`/`watching` → `ok`, `error`/`lost` → `danger`. **But `theme.qss` today carries `azStyle`
rules for `QPushButton[azStyle="danger"]` only** (`:115-133`) — no `QLabel[azStyle=…]` rule exists, so
`set_style` on a label resolves to nothing and the lamp would be invisible with every test green. This task
adds the four `QLabel[azStyle="…"]` rules, each written with a **`$` token** (`$ok`, `$warn`, `$danger`,
`$faded`): the template goes through `string.Template.substitute` (`theme/qss.py:23-33`), so a typo raises
at startup, and a hex value would fail the house-style scan.

- [ ] **1. Failing tests** in `tests/test_ui_console.py`: `test_connect_puts_the_identity_on_the_bar`,
      `test_a_timeout_shows_one_error_line_naming_the_host`,
      `test_the_lamp_carries_the_style_for_every_state` (all eight states),
      `test_every_lamp_style_has_a_rule_in_the_generated_stylesheet` — assert each of the four selectors
      appears in `qss.build()`; **this is the test that catches the missing rules** —
      `test_the_address_combo_offers_the_remembered_consoles`, `test_connecting_remembers_the_address`.
- [ ] **2. Run → FAIL. 3. Implement** widget + QSS rules. **4. Run → PASS** + suite. **5. Commit.**

**Verify:** `$PY -m pytest tests/test_ui_console.py tests/test_ui_house_style.py`
**Commit:** `feat(ui): add the console connect bar and its status lamp` — body names spec §6 and the missing
QLabel azStyle rules.
**Check by opening:** `set_style`'s unpolish/polish pair (`theme/widgets.py:17-22`); that no
`QLabel[azStyle]` rule existed before (`grep -n azStyle wing_parser/ui/resources/*.qss`); `ButtonRunner.run`'s
busy path (`call_button.py:34-53`).

### Task 10: `DiscoveryPanel` — inventory, and the unresolved banner

**Files:** create `wing_parser/ui/live_discovery.py`; modify `tests/test_ui_console.py`.

**Produces:** `DiscoveryPanel(QWidget)` — `discovered = Signal(object)` (a `WatchList`),
`rerun_requested = Signal()`, `set_state(state)`, `set_result(watch_list)`. Discover runs under kind `"walk"`.

**The unresolved banner is the load-bearing element of this page.** When a walk returns unresolved families
it shows their names, the leaf count it *would* watch, the ruled sentence *rerun before believing the list
is small*, and a Rerun button. The 2026-08-23 session opened a watch on **16 leaves with seven families
unresolved**; an immediate rerun resolved all **220**. A bare total is the exact failure this prevents
(live-watch design §3.2, ROADMAP §6). No progress bar (D7) — `walk_schema` (`net/schema.py:68`) is a
breadth-first loop with no callback seam, and this wave does not modify `net/`.

- [ ] **1. Failing tests:** `test_a_clean_walk_shows_the_leaf_total_and_the_family_counts` (220, and
      `40 ch, 16 bus, 4 main, 8 mtx, 16 dca`, from a `FakeDesk`),
      `test_the_unresolved_banner_names_every_family_that_did_not_resolve`,
      `test_the_banner_carries_the_rerun_sentence`, `test_the_banner_is_absent_after_a_clean_walk`,
      `test_rerun_walks_again_and_clears_the_banner`.
- [ ] **2. Run → FAIL. 3. Implement. 4. Run → PASS** + suite. **5. Commit.**

**Verify:** `$PY -m pytest tests/test_ui_console.py`
**Commit:** `feat(ui): show what the schema walk found and what it missed` — body names spec §6 and D7.
**Check by opening:** `WatchList.strips` is a per-family count dict, not a list
(`net/watch/list.py:39-48, 98-106`); `unresolved` carries `schema.unresolved_nodes` (`:109`); that
`walk_schema` has no progress callback (`net/schema.py:68`).

### Task 11: `SnapshotPanel`, and the window wiring

**Files:** create `wing_parser/ui/live_snapshot.py`, `wing_parser/ui/live_wiring.py`; modify
`wing_parser/ui/main_window.py` (**183 lines** — **one import and one `.connect(...)` line**, nothing more),
`tests/test_ui_console.py`. Read `ui/window_state.py:68-72` and `ui/menus.py:87-89` first.

**Produces:** `live_wiring.adopt_pulled_session(window, session)` — sets `window.session`, clears the shown
finding, calls `window._refresh()`, and **deliberately does not `switch_to("doctor")`**, unlike
`window_state.adopt_session` (`window_state.py:68-72`) · `SnapshotPanel(QWidget)` with
`session_pulled = Signal(object)`, Pull under kind `"snapshot"`, the `EmptyReadError` line, the
`incomplete_report` banner, the scene-loaded line, an **Open Doctor** button, and **Export to .snap…** via
`Session.save_as` followed by `window_state.remember_recent`.

**D16:** after a Pull the window **stays on the Console page**. The watch may be running and the operator
may want to pull again; yanking the view away mid-session is worse than one click — which is why
`adopt_session`, with its unconditional `switch_to("doctor")`, cannot be reused. **D4:** a pulled scene does
not join the recent-files menu, because its `Session.path` names no file on disk and `open_recent` (`:50-66`)
would later pop "File is gone" and self-heal the entry away. **After a successful Export** it is remembered.

- [ ] **1. Failing tests:** `test_an_empty_read_shows_an_error_line_and_no_session_reaches_the_window` (the
      guard at the UI boundary), `test_a_partial_read_shows_a_persistent_banner_naming_the_counts`,
      `test_a_clean_pull_reaches_the_window_and_every_page_sees_it`,
      `test_the_view_stays_on_the_console_page_after_a_pull`, `test_open_doctor_switches_to_the_doctor_page`,
      `test_export_writes_through_save_as_and_remembers_the_exported_path`,
      `test_a_pulled_session_is_not_in_the_recent_menu_before_export`.
- [ ] **2. Run → FAIL. 3. Implement** — everything but those two lines goes in `live_wiring.py`; re-check
      `wc -l wing_parser/ui/main_window.py` afterwards and paste it. **4. Run → PASS** + suite. **5. Commit.**

**Verify:** `$PY -m pytest tests/test_ui_console.py tests/test_ui_shell.py`
**Commit:** `feat(ui): pull a desk into the window and export it` — body names spec D3, D4, D16 and §7.1.
**Check by opening:** that `adopt_session` really forces the Doctor page (`window_state.py:68-72`);
`open_recent`'s self-heal path (`:50-66`); that `menus.save_as` derives its dialog suggestion from
`session.path` (`menus.py:87-89`), which is what puts `suggested_name` in front of the operator.

### Task 12: `LiveEventsView` — start, stop, rate, elapsed, the event table

**Files:** create `wing_parser/ui/live_events_view.py`; modify `tests/test_ui_console.py`.

**Produces:** `LiveEventsView(QWidget)` — `started`, `stopped`, `lost = Signal(object)`, `set_state(state)`,
an interval spin defaulting to `poller.DEFAULT_INTERVAL` (0.25 s), and a table of **time · strip · key ·
before → after**. **No arithmetic in the widget**: rate and elapsed come from `live_controller.watch_rate`.
The loop runs on a `GeneratorWorker`, one per session, **not** a `QTimer` (D5).

**Not `changes_panel.py` (D8):** `ChangesPanel.set_changes` takes `edit.journal.Patch` tuples
(`changes_panel.py:13, 30-36`) and the dock's visibility is bound to `session.dirty`
(`main_window.py:175-176`). A watch event is not an unsaved edit, and conflating them makes the dock mean
two things. On `DeskLost` the page moves to `lost`, **keeps the event list on screen** — those events were
real — and offers Reconnect.

- [ ] **1. Failing tests:** `test_scripted_changes_land_in_the_table_in_order`,
      `test_the_row_shows_the_strip_label_the_key_and_before_to_after`,
      `test_stop_settles_the_worker_and_restores_the_buttons`,
      `test_desk_lost_leaves_the_events_on_screen_and_offers_reconnect`,
      `test_the_rate_line_comes_from_watch_rate_not_from_the_widget` (monkeypatch `watch_rate`, assert the
      rendered text follows it).
- [ ] **2. Run → FAIL. 3. Implement** — build events directly:
      `net.watch.events.Change(address, strip, key, label, before, after, elapsed)` is a frozen dataclass a
      test can construct with no socket (`events.py:13-21`). **4. Run → PASS** + suite. **5. Commit.**

**Verify:** `$PY -m pytest tests/test_ui_console.py`
**Commit:** `feat(ui): show a live watch as it happens` — body names spec D5, D8 and §7.3.
**Check by opening:** `Change`'s seven fields (`net/watch/events.py:13-21`); `ChangesPanel.set_changes`'s
`Patch` argument (`changes_panel.py:13, 30-36`); the dock's `session.dirty` binding
(`main_window.py:175-176`); `DEFAULT_INTERVAL = 0.25` (`poller.py:20`).

### Task 13: `ConsolePage` — assembly, and enabling driven by one table

**Files:** create `wing_parser/ui/console_page.py`; modify `wing_parser/ui/main_window.py` (replace Task 8's
`EmptyState` with `ConsolePage`), `tests/test_ui_console.py`.

**Produces:** `ConsolePage(QWidget)` holding a `ConnectBar`, `DiscoveryPanel`, `SnapshotPanel` and
`LiveEventsView`, one `CallRunner`, one `LiveState`, and `session_pulled = Signal(object)` re-emitted from
the snapshot panel. It exposes `set_session(session)` so `MainWindow._refresh`'s fan-out
(`main_window.py:171-173`) reaches it like every other page.

**Every button's enabled-ness comes from `live_state.allowed_actions(state)` — one table.** No scattered
`setEnabled`: a state change calls one `_apply_state` that walks the action names. That is the property a
plain pytest can exhaust, and the reason the state machine was built first.

- [ ] **1. Failing tests:** `test_every_button_matches_allowed_actions_in_every_state` — loop all eight
      states, assert each button's `isEnabled()` equals membership in `allowed_actions(state)`;
      `test_an_illegal_transition_raises_rather_than_leaving_a_stale_page`,
      `test_cancel_restores_the_buttons`, `test_the_page_builds_with_no_desk_and_no_session`.
- [ ] **2. Run → FAIL. 3. Implement. 4. Run → PASS** + suite. **5. Commit.**

**Verify:** `$PY -m pytest tests/test_ui_console.py tests/test_ui_shell.py`
**Commit:** `feat(ui): assemble the Console page from one state table` — body names spec §6.
**Check by opening:** the `set_session` fan-out and its `hasattr` guard (`main_window.py:171-173`); that
`CallRunner` serialises calls (`workers.py:100-101`), which is what makes `connecting`/`walking`/`pulling`
mutually exclusive in practice as well as in the table.

### Task 14: The AST scan that makes a write impossible

**Files:** create `tests/test_ui_live_is_read_only.py`. Read spec §8 first.

It parses **every** `.py` under `wing_parser/ui/` with `ast` and fails, naming file and line, on (1) any
`Import`/`ImportFrom` reaching `wing_parser.net.write`, `from wing_parser.net import write` included; and
(2) any `Call` whose func is an `Attribute` named `set` / `toggle` / `node_write` / `push` **whose base name
was bound from `wing_parser.net` in that module**, tracked from the module's own import table. **No
bare-name matching** — grepping for `set` or `push` would flag `dict`-shaped noise, and a test that cries
wolf teaches everyone to ignore it.

- [ ] **1. Failing tests:** `test_no_ui_module_imports_the_write_path`,
      `test_no_ui_module_calls_a_write_verb_on_a_net_binding`, `test_the_scan_catches_a_planted_import`
      (write a module into `tmp_path`, aim the scanner at it, assert it reports file and line),
      `test_the_scan_ignores_an_unrelated_dot_set_call`. The last two prove the scan is not vacuous.
- [ ] **2. Run → FAIL. 3. Implement** the scanner as a module-level function taking a root path, so the two
      synthetic tests can aim it at `tmp_path`. **4. Run → PASS** + suite.
- [ ] **5. Show it red once** by planting `from wing_parser.net import write` in a real UI module, capturing
      the failure, and reverting. **6. Commit.**

**Verify:** `$PY -m pytest tests/test_ui_live_is_read_only.py`
**Commit:** `test(ui): prove no write path is reachable from the UI` — body names spec §8 and D1.
**Check by opening:** that `net/write.py` really exposes `set` / `toggle` / `node_write` / `push`, defaults
`confirm=False` (`net/write.py:16-17`), and gates on serial in `_authorize` (`:33, 93`) — so the verb list
matches the real surface.

### Task 15: The exe, and seven screenshots taken from it

**Files:** `packaging/wing-ui.spec` (**73 lines**), `packaging/make-debug-spec.py` (**28 lines**). **Not TDD
— the deliverable is a verified binary.** Memory, 2026-08-24: a venv missing an optional extra builds an exe
that dies silently at exit 1, because `console=False` prints nothing.

- [ ] **1.** Install every extra into the build venv first — `pip install -e ".[ui]"` plus `[ingest]` and
      `[llm-openai]`. **UI tests skipping in pytest is the symptom of a venv missing PySide6**; check for
      skips before building. **2.** `.venv\Scripts\pyinstaller packaging\wing-ui.spec --noconfirm`; paste
      the tail.
- [ ] **3.** Regenerate the debug spec with `packaging/make-debug-spec.py` — a *generated* artifact, never
      hand-edited — and build `dist\wing-ui-debug.exe` if the release exe misbehaves.
- [ ] **4.** `Start-Process dist\wing-ui.exe`, wait ~6 s, confirm the process is still alive. A dead process
      here is the silent-exit trap, not a flake.
- [ ] **5.** `dist\wing-ui.exe --screenshot dist-shots user-files\example-Vu.snap` → **seven** PNGs
      including `console.png`. **Look at them.** Attach all seven to the PR. **6. Commit** (only if a
      packaging file changed).

**Verify:** that screenshot command exits 0 and writes seven PNGs; paste the directory listing.
**Commit:** `chore(packaging): rebuild the app with the Console page` — body names spec §9.2.
**Check by opening:** the screenshot loop's `PAGE_ORDER` iteration and its fixed 1280×760 frame
(`ui/__main__.py:90-112`); that `make-debug-spec.py` generates rather than edits.

### Task 16: Docs — the manual, the roadmap, the debt ledger

**Files:** `docs/user-manual/03-console-truc-tiep.md` (**42 lines**), `docs/ROADMAP.md` (**254**),
`docs/tech-debt.md` (**445**), `memory/MEMORY.md`.

- [ ] **1.** In the manual, put the **UI route beside each `net` command** — the CLI stays documented, but a
      venue reader needs the button. Vietnamese, matching the file's voice.
- [ ] **2.** ROADMAP §3 gains the wave-2 row with the **measured** test count; §4's wave-2 pointer is
      updated. Then **grep for statements this wave made false** — the "Import, analyze/channel/routing,
      diff, toàn bộ `net` — vẫn CLI" line in `memory/MEMORY.md`, and any "CLI-only" phrasing — and fix those
      too. A phase still marked "not started" that shipped last week is not a stale note; it is a lie the
      next session will act on.
- [ ] **3.** `docs/tech-debt.md` gains **D11's double schema walk**: `take_snapshot` walks internally
      (`net/snapshot.py:83-85`) and `build_watch_list` walks again (`net/watch/list.py:89`), neither accepts
      a pre-computed `SchemaResult`, ~1 s of avoidable latency, deferred to wave 3 because fixing it is a
      `net/` change. Link to the ledger from elsewhere; never copy a fact out of it.
- [ ] **4.** `memory/MEMORY.md` gains one entry: what shipped, the measured suite number, what remains.
      **5. Commit** — docs-only staging, explicit paths, confirmed with `git diff --cached --name-only`.

**Verify:** `$PY -m pytest tests/test_examples.py` — it pins the shipped skill set **by name**, so a new or
renamed skill fails loudly there.
**Commit:** `docs: record the live console page in the manual, roadmap and ledger`
**Check by opening:** every `file:line` you write into a doc; and that the ROADMAP row quotes the count you
measured this wave, not 1433.

### Task 17: The handoff for wave 3, written now

**Files:** create `docs/handoff/2026-09-XX-gui-live-console-wave2-complete.md`. Written **while the context
is live** — written later it gets written from git, and git does not hold the reasons or the decisions still
waiting on a human.

- [ ] **1.** Baseline vs final suite numbers, both measured, both pasted with their command.
- [ ] **2. What ToanAZ can run and what he should see** — the exe path, the Console page, the acceptance
      list below, the exact commands.
- [ ] **3.** Done / in-progress / **decisions pending a human**: the three open questions from spec §11
      (watch alerts vs a plain log; whether wave 3 writes, and which write; auto-connect at startup) and the
      ten **ASSUMED** decisions, listed so he can overturn any of them.
- [ ] **4.** Known pitfalls — the double walk (D11), the venv-extras exe trap, `normalize`'s silent drop,
      and the labels-round detail in `RoundGuard`'s counting. **5. Commit.**

**Verify:** `git log --oneline` matches what the handoff claims; every path it names exists — existence-check
each one before writing it.
**Commit:** `docs(handoff): hand wave 3 the live console's state and open decisions`

### Task 18: Whole-branch review, on the strongest model

**Files:** none — the deliverable is the review and the fixes it forces. ROADMAP §7: this review **has
earned its cost four cycles running**, in the same shape every time — a defect spanning files no single
task's diff contained.

- [ ] **1.** A fresh reviewer, strongest model, reads the **whole branch diff** against the base with the
      spec open beside it. **2.** It **runs** the code — suite, exe, screenshots — not only reads it.
- [ ] **3.** It hunts the G2a defect shape specifically: **correct code carrying a false description.** Ten
      landed in G2a, every one caught in review and none by a test, because no test runs a docstring, an
      error message, or a line of user-facing instructions. Every claim a comment makes about another module
      is checked by opening that module.
- [ ] **4.** A scoped re-review per fix round — only the files that fix touched. **5.** The verdict goes in
      the PR, and a verifier that did not write the code tries to **refute** it against the real files.

**Verify:** `$PY -m pytest` — full suite, count pasted into the PR.

---

## Acceptance — human only, NOT machine-verifiable

Copied from spec §9.3. **No test in this plan substitutes for any line below.** Run against WING-GIAQUY
(`192.168.128.28` on 2026-08-21/23), from `dist\wing-ui.exe`, with **WING-Edit connected throughout**.
Record the output whatever it says.

- [ ] Connect to a live desk → lamp green, identity matches `wing net identity`.
- [ ] Connect to an address with nothing on it → lamp red within ~2 s, message names the host.
- [ ] Discover → 220 leaves, `40 ch, 16 bus, 4 main, 8 mtx, 16 dca`, none unresolved. If families do come
      back unresolved, **the banner names them and Rerun clears them**.
- [ ] **Pull with the desk switched off → "no console answered", not an empty Doctor.** The one step that
      proves the first guard.
- [ ] Pull → Doctor fills; Overview counts match `wing analyze --live`; Channels and Routing populate.
- [ ] Repair one finding, Export, reopen with Ctrl+O → the repair is in it.
- [ ] Start watch, drag a fader and press a solo **on WING-Edit** → events ~250 ms apart, `-144` shown as
      the fully-down sentinel.
- [ ] Coexistence: WING-Edit stays connected and usable throughout.
- [ ] Unplug the desk mid-watch → the loss is reported within ~1 s and the watch stops; it does not sit
      green and silent.
- [ ] Every page screenshotted **from the exe**, and **ToanAZ has looked at them** — wave 1's gate; no page
      is done without it.

## Definition of done for the wave

1. **PR green in CI**, on base `main` after the retarget.
2. **A verifier that did not write the code has tried to refute the claim** against the real files, and
   failed to. Never grade your own work.
3. **Exe screenshots of the Console page attached to the PR** — from `dist\wing-ui.exe`, not a dev run.
4. **ROADMAP, `docs/tech-debt.md` and `memory/MEMORY.md` updated**, with every statement the wave made false
   fixed, not merely a new row added (Task 16).
5. **The wave-3 handoff exists** and names the decisions still waiting on a human (Task 17).
6. The full suite's count is pasted in the PR with the command that produced it. A green build does not
   prove the logic is correct — the acceptance list above is the other half.

## Deviations from the spec's task sketch (§10), and why

1. **`tests/fake_desk.py` is created in Task 1, not Task 2** — every later test needs one fixed API, and
   `FakeDesk.transport()` imports `live_controller` inside the method, so it stands alone before Task 2.
2. **Task 5's desk-lost assertion is corrected.** Spec §9.1 says `on_round` sees `(0, 220)` three times;
   `poller.watch` calls `read_labels` first (`poller.py:84`) over **84** strip-name addresses, then a
   priming `sample` (`:86`), then the loop (`:99`) — so the real sequence is `(0, 84), (0, 220), (0, 220)`.
3. **Task 9 adds four `QLabel[azStyle="…"]` rules to `theme.qss`.** The stylesheet carries `azStyle` rules
   for `QPushButton[azStyle="danger"]` only, so the spec's lamp would render unstyled with every test green.
4. **Task 8 registers an `EmptyState` placeholder**, replaced by `ConsolePage` in Task 13, so Tasks 9–12
   land against a real sidebar row instead of a dangling import.
5. **Task 6 carries an escape hatch:** `workers.py` is 158 lines and `GeneratorWorker` is ~40, landing at
   ~200; if it crosses, the class moves to `ui/generator_worker.py`.

## Self-review

**Spec coverage.** D1→Task 14; D2→2; D3→4, 11; D4→11; D5→6, 12; D6→5; D7→10; D8→12; D9→8; D10→7; D11→16
(ledger); D12→10 (shown, not editable); D13→no task, the existing Diff page needs no plumbing; D14→6;
D15→out of scope; D16→11; D17→8. §6 page design→9–13, the state machine→1. §7.1→2–5; §7.2→6; §7.3→6, 12.
§8→14. §9.1→1–5; §9.2→9–13; §9.3→the acceptance list. §10's eighteen tasks all map. §11's three open
questions→Task 17 and the PR body. §12's out-of-scope items appear in no task.

**Type consistency.** `Transport` (2) is consumed by 3, 4, 5 under the same four attribute names.
`EmptyReadError` and `incomplete_report` (3) are consumed by 11. `session_from_snapshot` returns
`(Session, str)` (4), consumed by 11. `RoundGuard(client, host, cancel, on_round, lost_after)` and
`watch_rate` (5) are consumed by 6 and 12. `LiveState` / `transition` / `allowed_actions` (1) are consumed
by 9, 10, 11, 12, 13. `remember_console` / `forget_console` (7) are consumed by 9 and 11.

**Placeholder scan.** Every task names its test functions, verify command, commit message and claims to
check; the two guards are named by their original `file:line`; no step says "similar to Task N".
