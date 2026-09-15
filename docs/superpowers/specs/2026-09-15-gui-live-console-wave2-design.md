# GUI wave 2 — the live console in wing-ui — design

**Date:** 2026-09-15 · **Status:** draft, awaiting ToanAZ · **Cycle:** Đợt 2 of 2 (live console) ·
**Follows:** `2026-08-25-gui-parity-design.md` (wave 1, which scoped "Wave 2 = Live console (`net`)"
in its decisions table, line 26) · **Protocol authority:** `2026-08-21-wing-net-design.md` and
`2026-08-21-live-watch-design.md` — this spec adds a UI consumer and **modifies nothing under
`wing_parser/net/`**. Every claim below about an existing module was checked by opening it; the
`file:line` is given so a reviewer can refute it in one command.

## 1. Problem

`wing_parser/net/` can identify a desk, walk its schema, read the whole console into a `.snap`, and
report what changes on it while it runs. It has **two** CLI consumers, not one:

- **the `wing net` group** — `cli/net_commands.py`, wired at `cli/__main__.py:126-190`, seven
  subcommands: `identity`, `snapshot [-o FILE]`, `get ADDRESS`, `set ADDRESS VALUE [--confirm]`,
  `toggle ADDRESS [--confirm]`, `push FILE [--confirm]`, `watch [--json] [--interval S] [--until S]`;
- **`--live IP` on the ordinary scene commands** — `cli/commands.py:17-75` `_load()` calls
  `take_snapshot` (`commands.py:32`) and hands the result to `WingScene`, wired onto
  `analyze`/`routing` (`__main__.py:30-36`), `channel` (`:38-41`), `doctor` (`:43-56`), and as
  `--live-before`/`--live-after` onto `diff` (`:58-79`).

**The UI must match the second behaviour, not re-invent it.** A desk pulled in the app has to feed
Doctor / Overview / Channels / Routing / Diff exactly the way `--live` feeds them — same scene, same
findings, same counts — including the two guards `_load()` already carries (§7.1). None of this has a
button today, and project memory (ToanAZ, 2026-08-24) says *"Đi show xài giao diện UI bấm chuột,
**không ai chạy script tại venue**"* — a feature without a button does not exist.

## 2. Goal

One **Console** page that lets an operator, with a mouse, at a venue:

1. name a console (with remembered addresses) and **Connect** — name, model,
   serial, firmware, and a status lamp;
2. **Discover** the desk's shape, and be told honestly when the walk came back
   short (the 2026-08-23 lesson, ROADMAP §6: *"if a watch session opens with
   unresolved families, rerun before believing the list is small"*);
3. **Pull** the running state into a `Session` **identical to opening a `.snap`**,
   so every other page works on it unchanged — the integration that makes the
   wave worth doing;
4. **Export** that scene to a `.snap` file;
5. **Watch** the desk, each change as it happens, with rate and elapsed.

## 3. Non-goals

- **No write path of any kind.** See §8. `wing_parser/net/write.py` exists and works; wave 2 does not
  reach it, and a test enforces that.
- **No metering.** ROADMAP §4 (E): live-watch design §2.3 measured that there is no meter anywhere in
  the OSC tree and that `/$stat/ppm` is a setting, not a meter. Metering needs the console's native
  UDP transport — a second transport that does not exist yet. Nothing here pretends otherwise.
- **No subscribe.** Closed negative on the real desk 2026-08-23
  (`docs/handoff/2026-08-23-live-watch-acceptance-complete.md`, Test 3): all ten candidate verbs
  silent *while controls were moving*, with a passing control GET proving the harness. **Polling is
  the only mechanism.**
- No TUI, no watch-list editor, no `net get` box (D15), no change to `net/`, no Mac build.

## 4. The two hard constraints, quoted

`CLAUDE.md`:

> 🛑 **Live console over OSC — read freely, ask before writing.** Reading scene
> state (import, doctor, analyze) from a live WING console is safe. Writing or
> pushing any parameter change to a live console reaches real audio at a venue —
> ask before writing to a live desk, and never during a show without explicit
> confirmation.

`docs/ROADMAP.md` §2, standing constraint *Coexist with the desk*:

> Anything touching a live console must run alongside WING-Edit and Companion
> without displacing them. ToanAZ's words: *"cần song song không đá nhau."*

The first selects §3's first non-goal. The second is already satisfied by the
mechanism: polling claims no shared console resource (live-watch design §3.1),
and was proven alongside WING-Edit for a 120 s window on 2026-08-23.

## 5. Decisions

ASSUMED = decided here with the safest default because ToanAZ is away; the
orchestrator lists these for him. Everything unmarked is forced by evidence.

| # | Question | Decision | Rejected alternative |
|---|---|---|---|
| D1 | Does wave 2 include any write? | **No.** Read-only: connect, discover, pull, export, watch. Write deferred to wave 3, with a hook shape in §8. | A "dry-run only" write panel. Rejected: a dry-run button one property away from `confirm=True` is a live-audio accident waiting for a tired operator. **ASSUMED** |
| D2 | What does "Connect" actually do? | The `WING?` handshake on UDP 2222 (`net/identity.py:68`), whose timeout raises `TimeoutError` (`identity.py:80-83`). | An OSC read on 2223. Rejected on measured grounds: `cli/commands.py:30-45` records that **OSC is UDP, so an unreachable host raises nothing at all** — every leaf times out, `take_snapshot` returns an empty scene, and `doctor --live` once printed "No findings." for a desk it never reached. Only the identity handshake fails *loudly*. |
| D3 | How does a pulled desk become a Session, and what does Export write? | Pull: `take_snapshot` → `net/export.to_snap_json` → `json.loads` → `Session(document, path)`. **Export writes `Session.save_as`, not the pull-time bytes.** `Session.save_as` writes the *patched* document (`ui/session.py:92-96` → `_document()` at `:43-44`), so a Doctor repair made after the pull is in the exported file. The pull-time JSON text is kept in memory as the untouched **original**, offered to the Diff page as "as pulled". | Exporting the pull-time bytes. Rejected: it would silently drop every repair the operator made — the file would disagree with the window. |
| D4 | Does a pulled scene join the recent-files menu? | **No**, until it is exported. Its `Session.path` names no file on disk; `window_state.open_recent` (`window_state.py:50-66`) would later pop "File is gone" and self-heal the entry away. After a successful Export, the exported path *is* remembered. | Recording it anyway. Rejected: teaches the operator that the recent menu lies. |
| D5 | Where does the watch loop run? | A dedicated `GeneratorWorker` thread (§7.3), one per watch session. | A GUI-thread `QTimer` calling `poller.sample`. Rejected on the measured rounds (live-watch design §2.4, lines 100-110): 24 leaves → 0.017 s, **120 leaves → 0.022 s**, 144 leaves → **0.425 s** (that row is not network trouble: 24 of those addresses do not exist and the retry ladder hunts each one every round — §2.5). A 208-leaf list sustained **819 rounds in 90 s** (~0.11 s per round). The shipped list is 220 leaves, so a round costs tens of milliseconds *at best* and ~0.4 s if the list ever goes stale against the desk — blocking the GUI four times a second either way. Wave 1b's ruling: no network call runs on the GUI thread. |
| D6 | How is "the desk disappeared" detected? | Inside the counting proxy, which **raises** `DeskLost` after three consecutive rounds answering zero addresses (§7.1). | Watching the generator's output. It cannot work: `poller.watch` yields only on a `Change` (`poller.py:101-114`), and a dead desk produces none — measured, 12 `get_many` calls, 0 yields. A silent desk and a quiet desk are identical downstream, because the poller carries the previous value forward for a silent address on purpose (`poller.py:116-119`). Threshold 3 ≈ 0.75 s at the default interval. **ASSUMED** |
| D7 | Progress bar for the schema walk? | **No** — an indeterminate busy state plus a result summary. `walk_schema` (`schema.py:68`) is a breadth-first loop with no callback seam, and this wave does not modify `net/`. | Adding a progress callback to `schema.py`. Rejected by the C2 rule that `net/client.py`, `codec.py` and `schema.py` are not modified by a consumer. |
| D8 | Reuse `changes_panel.py` for watch events? | **No.** New `live_events_view.py`. | Reuse. `ChangesPanel.set_changes` takes `edit.journal.Patch` tuples (`changes_panel.py:13,30-36`), and the dock's visibility is bound to `session.dirty` (`main_window.py:175-176`). A watch event is not an unsaved edit; conflating them makes the dock mean two things. |
| D9 | Where does the page sit? | Last in `PAGE_KEYS`, sidebar row 7, **Ctrl+7** — `menus.build_accelerators` already binds `Ctrl+{index}` over `PAGE_KEYS` (`menus.py:55-59`), so the shortcut appears with no new code. | A separate window. Rejected: wave 1 ruled sidebar navigation. **ASSUMED** |
| D10 | Remembered console addresses? | A new `"consoles"` list in `ui-state.json`, capped at `MAX_RECENT` (8). Note `state_store.normalize` (`state_store.py:26-37`) rebuilds a fixed dict, so a field not added there is **silently dropped on save**; and `remember_recent` (`:61-64`) compares with `Path()`, so addresses get their own plain-string helper. | QSettings, or a free-text box with no memory. **ASSUMED** |
| D11 | One schema walk or two? | Two, accepted. `take_snapshot` walks internally (`snapshot.py:83-85`) and `build_watch_list` walks again (`watch/list.py:89`); neither accepts a pre-computed `SchemaResult`. At a measured ~1 s per walk this is a second of latency, not a defect. Logged as tech debt for wave 3. | Adding a `schema=` parameter to both. That is a `net/` change (D7's rule). |
| D12 | Can the operator edit the watch list? | **No.** `net/watch/data/watchlist.yaml` ships as-is (ch/bus/main/mtx `$fdr $mute $solo`, dca `$solo`). The UI shows what is watched and what did not resolve. | A family/key picker. Rejected for wave 2: widening coverage is a data edit anyone can make in the YAML, and the UI has no way to warn that an absent address costs 20× (live-watch design §2.5). **ASSUMED** |
| D13 | Diff a live desk against a file? | Pull first, then the existing Diff page's "Compare with..." (`diff_page.py:129`). No new plumbing. | Reimplementing `--live-before/--live-after` in the UI. Rejected: a pulled Session *is* the left side already. |
| D14 | Timeout budgets | connect 5 s, walk 60 s, snapshot 90 s (§7.2). | Reusing the model-call budgets. They describe HTTP to a provider, not UDP to a desk. **ASSUMED** |
| D15 | A "read one address" box, mirroring `net get`? | **No** for wave 2 — listed in §3/§12. It is a debugging affordance, and project memory (2026-08-24 §2) puts probes and measuring tools in a dev area, not in the show flow. | Shipping it on the main panel. **ASSUMED** |
| D16 | Where does the window land after a Pull? | **Stays on the Console page**, which shows a "scene loaded — N findings" line and an **Open Doctor** button. The watch may be running and the operator may want to pull again; yanking the view away mid-session is worse than one click. This needs a new adopt path: `window_state.adopt_session` (`:68-72`) unconditionally calls `switch_to("doctor")`. | Reusing `adopt_session` as-is. **ASSUMED** |
| D17 | Texts namespace for the page | `console.*`, page key `"console"`, `page.console` → visible label **"Console"**. `texts.py:18` already holds `"overview.live": "Live channels"` (unmuted channels), so a `live.*` namespace would collide in meaning. Module names stay `live_*`. | `live.*`. **ASSUMED** |

## 6. Page design

```
ConsolePage  (wing_parser/ui/console_page.py, ~170 lines)
├── ConnectBar        console address (QComboBox, editable, recents) ·
│                     Connect / Disconnect · lamp · identity readout
├── DiscoveryPanel    Discover · leaves + per-family inventory ·
│                     unresolved banner + Rerun
├── SnapshotPanel     Pull snapshot from desk · scene-loaded line +
│                     Open Doctor (D16) · Export to .snap...
└── LiveEventsView    Start watch / Stop · interval · rate · elapsed ·
                      event table (time · strip · key · before → after)
```

Every string goes through `texts.py` under `console.*`; every colour is a Sodium Rack token
(`ui/theme/tokens.py:17-37`). The lamp is a `QLabel` whose `azStyle` is set with
`theme.widgets.set_style` (`widgets.py:17-22`) — **no new colour literal**, which
`tests/test_ui_house_style.py::test_no_colour_literals_outside_the_theme_package` enforces with an
empty allowlist. Mapping: `disconnected` → `faded`, `connecting`/`walking`/`pulling` → `warn`,
`connected`/`watching` → `ok`, `error`/`lost` → `danger`.

**The unresolved banner is the load-bearing UI element of this page.** When a walk returns unresolved
families it shows their names, the count of leaves it *would* watch, the ruled sentence *rerun before
believing the list is small*, and a Rerun button. The 2026-08-23 session opened a watch on **16
leaves with seven families unresolved**; an immediate rerun resolved all **220**. A bare total is the
exact failure this element prevents (live-watch design §3.2).

### The connection state machine (non-Qt)

`wing_parser/ui/live_state.py`, ~80 lines, no Qt import:

```
disconnected --connect--> connecting --ok--> connected --watch--> watching
     ^                         |                 |                  |
     |                         +--fail--> error  +--walk--> walking |
     +--disconnect/reset---------------+         +--pull--> pulling |
                                       |   walking/pulling --ok/fail-+-> connected
                                       |                             |     / error
                                       +-------- lost <--DeskLost----+
```

`LiveState` is an enum plus a `transition(state, event) -> LiveState` table that **raises on an
illegal pair** rather than silently staying put, and `allowed_actions(state) -> frozenset[str]`
driving every button's enabled-ness from one table a plain pytest can exhaust — no scattered
`setEnabled`. `pulling` and `lost` are states of their own: `take_snapshot` runs its own walk plus
~25 062 leaf reads¹ and every other action must be refused during it, and `lost` differs from `error`
in that the event list stays on screen.

> ¹ Live-watch design §3.2 line 195 (`probe9_stripset.py`, 2026-08-21: 25 062 leaves, 0 unresolved,
> 1.00 s). The wing-net design §2.5 line 165 says **25 060** for the same console on a different day
> — the tree's shape depends on live parameter values (wing-net §2.10/§2.11). Neither is
> load-bearing here.

## 7. The controller, and threading

### 7.1 `wing_parser/ui/live_controller.py` (~170 lines, no Qt)

Mirrors `import_controller.py`: plain functions plus one seam, each testable
headless.

```python
@dataclass(frozen=True)
class Transport:
    """The four net/ entry points the Console page uses, injectable."""
    identity: Callable[[str], WingIdentity]     # net.identity.query_identity
    walk:     Callable[[str], WatchList]        # net.watch.list.build_watch_list
    snapshot: Callable[[str], SnapshotResult]   # net.snapshot.take_snapshot
    client:   Callable[[str], WingClient]       # net.client.WingClient

REAL = Transport(...)   # the only place net/ is named
```

Functions and types:

- `connect(host, transport) -> WingIdentity` — raises `TimeoutError`/`ValueError` unchanged; the page
  shows one error line and does not invent a second taxonomy (the `import_controller.read_with`
  precedent).
- `discover(host, transport) -> WatchList` — `build_watch_list` (`watch/list.py:67`) already returns
  `addresses`, `unresolved` and a per-family `strips` count; no reshaping needed.
- `pull(host, transport) -> PullResult` — **carries both of `_load()`'s guards, ported from
  `cli/commands.py`, because a UI that drops them repeats the incident that motivated them:**
  - **Empty-read guard** (`commands.py:47-62`): `if not snapshot.raw.ae and not snapshot.raw.ce:`
    raise `EmptyReadError(host, len(unresolved_nodes), len(unresolved_leaves))`. Without it, Pull
    against an unreachable desk returns a perfectly valid `Session` whose scene is empty, the
    advisory truthfully finds nothing wrong with nothing, and **Doctor shows "No findings." for a
    desk that was never reached** — exactly what `doctor --live` did before that guard. It is
    leaf-driven but reports both counts, because `walk_schema` runs first and can succeed while
    every later leaf read times out.
  - **Partial-read report** (`commands.py:63-75`): `incomplete_report(result) -> str | None` naming
    how many nodes and leaves did not answer, plus the node names. A clean read returns `None` —
    silence there is deliberate; a warning printed every time teaches the reader to skip it. The
    page shows it as a persistent banner above the scene-loaded line, not a transient.
- `session_from_snapshot(result, identity, profile=None) -> tuple[Session, str]` — the `Session` and
  the pull-time JSON text (D3's "original"):
  `Session(json.loads(text), Path(suggested_name(identity, host)), profile)`.
- `suggested_name(identity, host) -> str` — `"WING-GIAQUY-20260915-1432.snap"`, falling back to
  `"wing-192.168.128.28-….snap"` without identity. Bare filename, no directory: it names nothing on
  disk (D4) and `menus.save_as` derives its dialog suggestion from it (`menus.py:87-89`).
- `RoundGuard` — **the non-Qt heart of both cancel and desk-lost.** It wraps a `WingClient`,
  delegates `get_many`, `request`, `close` and the context-manager pair, and is the *only* place the
  watch loop can be interrupted or judged:
  - **before** every `get_many`: cancel event set → raise `Cancelled`. This check cannot live in the
    injected `sleep`, because `poller.py:121-123` calls `sleep` only when `remaining > 0` — on a desk
    slower than the interval the sleep is never reached and a cancel would never be observed. Stop
    latency is therefore bounded by **one round**, whatever the desk's speed.
  - **after** every `get_many`: record `answered=len(result.replies)` against `total=len(addresses)`,
    call `on_round(answered, total)`, and on the third consecutive `answered == 0` raise
    `DeskLost(host, rounds)`. Raising is required — `poller.watch` yields only on a `Change`, so a
    dead desk produces no output to inspect (D6).
- `watch_rate(events, seconds) -> tuple[float, float]` — events/s and elapsed, a plain function, so
  `LiveEventsView` holds no arithmetic.

### 7.2 Which call runs where

| Call | Vehicle | Budget | Why that number |
|---|---|---|---|
| `connect` | `FunctionWorker` under the page's `CallRunner` | **5 s** | `query_identity`'s own socket timeout is 2.0 s (`identity.py:68`); the worker budget is a backstop, not the deadline. |
| `discover` | `FunctionWorker` | **60 s** | A clean walk is **~1.00 s** for ~25 000 leaves with 0 unresolved (live-watch §3.2; wing-net §2.5 measures 0.95 s). The budget covers the retry ladder as it actually works: `get_many` (`client.py:157-195`) sends in chunks of `DEFAULT_BATCH_SIZE = 200` (`:41`) and each chunk stops collecting after `DEFAULT_IDLE_TIMEOUT = 0.2 s` with nothing new (`:66`); each of up to `DEFAULT_RETRY_ROUNDS = 8` (`:54`) retry rounds rotates the socket and **halves** the chunk size (200→100→…→1), and the loop **breaks early** the moment a round recovers nothing (`:193-194`). `DEFAULT_TIMEOUT = 2.0` (`:59`) is the per-socket request timeout, not a per-round cost. So the real worst case is idle-timeouts × chunks, and 60 s is ~60× the clean walk — enough for the pathological shape §2.5 measured (24 absent addresses turning a 0.022 s round into 0.425 s, 20×) without letting a dead desk hang the button forever. |
| `pull` | `FunctionWorker` | **90 s** | Measured whole-console snapshot ≈ **10 s** (≈1 s shape + ~9 s of ~25 000 values at 2822 reads/s, batch 200 — wing-net §2.5). 90 s is 9× the measured figure. |
| `watch` | `GeneratorWorker` (new) | **none** | A watch has no deadline; it ends on Stop, or when `RoundGuard` raises `DeskLost`. |

`TIMEOUTS` in `ui/workers.py:25` gains `"connect": 5, "walk": 60, "snapshot": 90`. `CallRunner`
already serialises: `start()` returns `False` while a call runs (`workers.py:100-101`), so
connect/discover/pull can never interleave and the page shows the busy text instead. `ButtonRunner`
(`call_button.py:16`) supplies the disable-primary / show-Cancel / status-line dance unchanged.

### 7.3 `GeneratorWorker` — the one new thing in `workers.py` (~40 lines)

```python
class GeneratorWorker(QThread):
    produced = Signal(object)          # one Change
    progress = Signal(int, int)        # answered, total  (from RoundGuard)
    finished = Signal(object)          # summary: rounds, events, seconds
    failed   = Signal(object)          # DeskLost, or any OSError/ValueError
    finished_cancelled = Signal()      # Cancelled from RoundGuard
```

It iterates `poller.watch(guard, watch_list, interval=…)` (`poller.py:64`) and emits per item. It
holds **no** desk-lost or cancel logic of its own — both live in `RoundGuard` (§7.1), non-Qt and
therefore covered by plain pytest. Its only jobs: translate `Cancelled` → `finished_cancelled` and
`DeskLost` → `failed`, and keep the thread referenced until it really stops, the way
`CallRunner._settle` does (`workers.py:152-157`). On `DeskLost` the page moves to `lost`, keeps the
event list on screen — those events were real — and offers Reconnect.

## 8. Safety — how a write is impossible in this wave

Not a promise; a structure.

1. **No code path.** `live_controller.Transport` names exactly four callables, all read-only.
   `wing_parser/net/write.py` is never imported under `wing_parser/ui/`.
2. **An AST test enforces it** — precise, not textual. `tests/test_ui_live_is_read_only.py` parses
   every `.py` under `wing_parser/ui/` with `ast` and fails, naming file and line, on any
   `Import`/`ImportFrom` reaching `wing_parser.net.write` (including `from wing_parser.net import
   write`), and on any `Call` whose func is an `Attribute` named `set`/`toggle`/`node_write`/`push`
   **whose base name was bound from `wing_parser.net` in that module**, tracked from the module's own
   import table. No bare-name matching: grepping for `set`/`push` would flag `dict.set`-shaped noise
   and teach everyone to ignore the test.
3. **The CLI's own gate stays untouched**: `write.set(...)` defaults to `confirm=False` and a dry run
   "touches no socket" (`net/write.py:16-17`). Wave 2 never calls the function at all.

### The wave-3 hook (shape only, not built)

When a write wave happens, it enters through **one** dialog, and nothing else:

```
ConfirmWriteDialog(desk: WingIdentity, changes: tuple[(address, before, after)])
```

- Names the desk — name, model **and serial** — read fresh from `query_identity` at dialog time, not
  from the earlier connect, mirroring `net_commands._echo_identity_before_write`
  (`net_commands.py:80-85`): say which desk is about to change before any packet that could alter it
  goes out.
- Shows every address with `before → after` using the codec's display-string rule (`codec.py:107`);
  requires the operator to **type the console's name** to enable the button.
- Wires `WING_WRITE_ALLOW_SERIAL` (`net/write.py:33`, `_authorize` at `:93`) so a serial mismatch
  refuses, surfacing `SerialMismatchError` as its own message.
- Carries a *"this desk is in a show"* latch, default on, that disables the button entirely —
  CLAUDE.md: *never during a show without explicit confirmation*.
- Reports the read-back: `OK` is not proof, the console clamps and still answers `OK`
  (`net/write.py:5-8`), so every write is read back and a clamp is shown.

## 9. Test strategy

### 9.1 Plain pytest, no socket, no console

`tests/test_live_state.py` — the transition table exhaustively: every (state, event) pair either
maps to the documented target or raises; every `allowed_actions` set pinned.

`tests/test_live_controller.py` — against `FakeDesk`, specified here so no test ever needs a desk:

```python
class FakeDesk:
    """Everything live_controller can reach, in memory. No socket anywhere.

    identity   : WingIdentity | Exception   -- returned, or raised
    leaves     : dict[address, OscMessage]  -- the console's whole surface
    unresolved : tuple[str, ...]            -- what the walk could not resolve
    rounds     : list[dict[address, value]] -- scripted watch samples, consumed
                 one per get_many; an EMPTY dict is a round the desk ignored,
                 and a list that runs out repeats its last entry forever
    """
    def transport(self) -> live_controller.Transport: ...
    def client(self) -> _FakeClient:  # get_many/request/close/__enter__/__exit__
```

`_FakeClient.get_many(addresses)` returns a real `net.client.BatchResult(replies=…, unresolved=…)`
whose values are real `net.codec.OscMessage` objects built directly —
`OscMessage("/ch/1/$fdr", "sff", ("-6.0", 0.5, -6.0))` for a float leaf, `("sfi", ("1", 0.0, 0))` for
a list leaf, `("s", ("KICK",))` for a name — because `leaf_value` (`codec.py:107`) reads args by tag
and takes the **display string** for `,sfi`. No bytes, no `encode`/`decode`, no port.
`tests/fake_wing.py` stays the loopback fake for `net/`'s own tests, which need real wire bytes; the
controller layer does not.

Coverage, one test each:

- connect: success, `TimeoutError`, malformed identity; discover: clean, and unresolved-families;
  `suggested_name` shape;
- **pull against a desk that answers nothing** (`ae` and `ce` both empty) raises `EmptyReadError`
  naming the host and both counts — no `Session` is built;
- pull partial: `incomplete_report` is a non-`None` string naming the counts;
- pull clean → `Session` → `session.findings()` non-empty and `session.scene.channels()` populated —
  the wave's whole claim in one test;
- **Export parity**: repair a finding on the pulled Session, `save_as` to `tmp_path`, reopen with
  `Session.open` — the repair is in the file and the pull-time original still is not (D3);
- **`RoundGuard` desk-lost**: drive the *real* `poller.watch` with a `FakeDesk` whose `rounds` go
  empty; assert `DeskLost` is raised on the third zero round, that the generator produced **zero**
  `Change`es before it (the reason D6 could not be output-driven), and that `on_round` saw `(0, 220)`
  three times;
- **`RoundGuard` cancel**: set the cancel event, then assert the next `get_many` raises `Cancelled`,
  with `interval=0` so the injected `sleep` is provably never the thing that stopped it.

Per live-watch design §4.3: **each new test is shown red once** by reverting the production line it
covers, and the failure captured.

### 9.2 Qt, offscreen

`tests/test_ui_console.py` — page builds; buttons enable/disable exactly as `allowed_actions` says at
each state; the unresolved banner appears with a `WatchList` carrying unresolved families and not
otherwise; `EmptyReadError` surfaces as an error line and **no** session reaches `MainWindow`; a good
pull reaches `MainWindow` and every other page sees it while the view stays on the Console page
(D16); `GeneratorWorker` delivers scripted `Change`es to the table and settles on Stop; Cancel
restores the buttons. Existing tests to update: `tests/test_ui_shell.py:16` (six pages → seven) and
`tests/test_ui_texts.py` (add `page.console`). `ui/__main__.py:95-112` screenshots `PAGE_ORDER`, so
the new page is captured with no change to the loop.

### 9.3 Acceptance — **human only, needs the real desk**

Run against WING-GIAQUY (`192.168.128.28` on 2026-08-21/23), from `dist\wing-ui.exe`, with WING-Edit
connected throughout. Record the output whatever it says.

- [ ] Connect to a live desk → lamp green, identity matches `wing net identity`.
- [ ] Connect to an address with nothing on it → lamp red within ~2 s, message names the host (D2).
- [ ] Discover → 220 leaves, `40 ch, 16 bus, 4 main, 8 mtx, 16 dca`, none unresolved. If families do
      come back unresolved, **the banner names them and Rerun clears them** — 2026-08-23 in the UI.
- [ ] **Pull with the desk switched off → "no console answered", not an empty Doctor.** The one step
      that proves §7.1's first guard.
- [ ] Pull → Doctor fills; Overview counts match `wing analyze --live`; Channels and Routing populate.
- [ ] Repair one finding, Export, reopen with Ctrl+O → the repair is in it (D3).
- [ ] Start watch, drag a fader and press a solo **on WING-Edit** → events ~250 ms apart, `-144`
      shown as the fully-down sentinel.
- [ ] Coexistence: WING-Edit stays connected and usable throughout.
- [ ] Unplug the desk mid-watch → the loss is reported within ~1 s and the watch stops; it does not
      sit green and silent.
- [ ] Every page screenshotted **from the exe**, and ToanAZ has looked at them — wave 1's gate.

## 10. Task list

Cut in the wave-1 plan's style: one fresh implementer per task, a reviewer after each. The ~200-line
rule is a **file** ceiling (ROADMAP §2), not a per-task budget; tasks are cut so no file crosses it.

**Baseline.** The last measured suite is **1433 passed / 3 skipped at `04db887`, 2026-08-26** —
historical; re-measure on this wave's own first commit rather than quoting it forward. On a clean
checkout of `d28e00f` two `tests/test_ui_import_page.py` key-status tests fail (D-30 placeholder-key
masking), fixed in **PR #1 `fix/ui-debt-wave1b-leftovers`**. **Branch wave 2 from `main` only after
PR #1 merges**, so the first re-measurement starts green.

Tasks **2–5 all edit `live_controller.py`**: they are **sequential on one implementer**, in order —
separate tasks for review granularity, not for parallelism. Everything else is independent.

| # | Task | Files |
|---|---|---|
| 1 | Connection state machine + transition table (incl. `lost`) | `ui/live_state.py`, `tests/test_live_state.py` |
| 2 | `Transport` seam, `connect`, `discover` | `ui/live_controller.py`, `tests/test_live_controller.py` |
| 3 | `pull`: **both** `_load()` guards — `EmptyReadError` and `incomplete_report` | `ui/live_controller.py`, tests |
| 4 | `session_from_snapshot`, `suggested_name`, the Session-parity and Export-parity tests | `ui/live_controller.py`, tests |
| 5 | `RoundGuard`: cancel-before-round, desk-lost-after-round, `watch_rate` | `ui/live_controller.py`, tests |
| 6 | `GeneratorWorker` + the three new `TIMEOUTS` entries | `ui/workers.py`, `tests/test_ui_workers.py` |
| 7 | `consoles` field in the state store (normalize, defaults, plain-string helper) | `ui/state_store.py`, `tests/test_ui_state_store.py` |
| 8 | Page registration: `console.*` texts, `PAGE_KEYS`, `PAGE_ICONS`, Ctrl+7, shell test to seven | `ui/texts.py`, `ui/state_store.py`, `ui/main_window.py`, `tests/test_ui_shell.py`, `tests/test_ui_texts.py` |
| 9 | `ConnectBar`: address combo + recents, Connect/Disconnect, lamp, identity readout | `ui/live_connect_bar.py`, `tests/test_ui_console.py` |
| 10 | `DiscoveryPanel`: walk result, inventory, unresolved banner + Rerun | `ui/live_discovery.py`, tests |
| 11 | `SnapshotPanel` + **window wiring**: Pull, the empty/partial banners, scene-loaded line, Open Doctor, Export (via `Session.save_as`, then remember the path). `main_window.py` is already **183 lines**, so the `session_pulled` → adopt connection and a `adopt_pulled_session(window, session)` (which does *not* `switch_to("doctor")`, unlike `adopt_session` at `window_state.py:68-72`) go into a new `ui/live_wiring.py`; `main_window.py` gains only the import and one `.connect(...)` line | `ui/live_snapshot.py`, `ui/live_wiring.py`, `ui/main_window.py`, tests |
| 12 | `LiveEventsView`: start/stop, interval, event table; rate and elapsed rendered from `live_controller.watch_rate` (no arithmetic in the widget) | `ui/live_events_view.py`, tests |
| 13 | `ConsolePage` assembly + `allowed_actions`-driven enabling | `ui/console_page.py`, tests |
| 14 | The AST no-write scan test | `tests/test_ui_live_is_read_only.py` |
| 15 | Exe: rebuild, regenerate the debug spec (`packaging/make-debug-spec.py`), screenshot all seven pages from `dist\wing-ui.exe` | `packaging/` |
| 16 | Docs: `docs/user-manual/03-console-truc-tiep.md` gains the UI route beside each `net` command; ROADMAP §3/§4; `docs/tech-debt.md` (D11 double walk) | docs |
| 17 | Handoff for the next wave, written while the context is live | `docs/handoff/` |
| 18 | **Whole-branch review on the strongest model.** ROADMAP §7: it has earned its cost four cycles running, catching defects spanning files no single task's diff contained. Not optional polish. | — |

## 11. Open questions for ToanAZ

Only the ones that change what gets built.

1. **Does a watch need alerts, or is a log enough?** Today's design is a scrolling event list, like
   the CLI. If he wants "tell me when *these* channels move" the page needs a rule layer and a
   per-strip arming UI — a different page, decided before task 12, not after.
2. **Is there a wave 3, and which write?** Two very different hooks: a single-parameter repair pushed
   from a Doctor finding, versus a whole-scene `push`. §8's dialog is drawn for the first. Nothing in
   wave 2 depends on the answer, but the hook's shape does.
3. **Auto-connect to the last console at startup?** Default here is **no** — the app should not put
   packets on a venue network before anyone asks it to.

Not re-asked: ROADMAP §5.5 (`$fdr` vs `fdr`) is open and unchanged by this wave.

## 12. Out of scope

Metering and the native transport (E). Subscription (closed negative). Any modification to
`wing_parser/net/`. A watch-list editor. A `net get` read-one-address box (D15). Writing to a desk.
Language switching (structure is ready). Mac packaging.

## Deviations recorded 2026-09-16

Task 16 (docs). The body above is left as designed and reviewed; this section
records where the shipped code (tasks 1-15, `ac39cfa..e8e3de1`) diverges from it,
so the design stays legible as a historical record rather than being rewritten to
match the outcome. Each item names the module and the reviewing task that ruled
on it; full detail is in that task's report under
`.superpowers/sdd/2026-09-15-gui-live-console-wave2/`.

- **RoundGuard and watch_rate live in a new `wing_parser/ui/live_guard.py`, not in
  `live_controller.py`** as S7.1 says. Decided at task 5: `live_controller.py`
  names `net` and was approaching its 200-line ceiling, so the pure logic
  (`RoundGuard` at `live_guard.py:64`, `watch_rate` at `:130`, plus `Cancelled`,
  `DeskLost`, `DEFAULT_INTERVAL`/`MIN_INTERVAL`/`MAX_INTERVAL`) moved to a sibling
  module that imports no `net` at all, so "only one `ui/` file names `net`" still
  holds.
- **`Transport` carries five callables, not four.** S7.1 and S7.3 describe four.
  Task 6 added a fifth, `watch` (`live_controller.py:70-84`), so `GeneratorWorker`
  can drain the poller through the same injectable seam as `identity`, `walk`,
  `snapshot` and `client`, without importing `net` itself.
- **A shared `CallPanel` base class** (`wing_parser/ui/live_call_panel.py:34`) is
  not in the design. Task 10's review found `ConnectBar` and `DiscoveryPanel`
  duplicating the same runner/state/cancel plumbing and extracted it; `SnapshotPanel`
  joined at task 11. `CallPanel.failed` and `CallPanel.state` were added at task 13
  once the assembled page needed both.
- **The page's strings split into a new `wing_parser/ui/texts_console.py`**, not
  named in the design. `texts.py` was at its own 200-line ceiling by task 11; the
  Console vocabulary is merged back into `TEXTS` so `text("console.pull")` resolves
  exactly as any other key does.
- **Export is gated on a loaded session, not on `live_state.allowed_actions`**
  (`wing_parser/ui/live_snapshot.py:101-118`, specifically the `loaded =
  self._session is not None` line at `:114`). Ruling at task 11: a file write is
  not a desk action, so it should not be table-driven the way Connect/Discover/Pull
  are.
- **`ERROR` allows `connect` in one click**, plus two related table rows the design
  did not anticipate, all found and fixed at task 13's sweep of `live_state.py`:
  `(ERROR, "connect") -> CONNECTING` (`:100`); `(WATCHING, "disconnect") ->
  DISCONNECTED` (`:99`), a row that was missing even though the Disconnect button
  had been live in `WATCHING` since task 1; and `cancel` rows for all three busy
  states -- `(CONNECTING, "cancel")`, `(WALKING, "cancel")`, `(PULLING,
  "cancel")` (`:86,93,96`) -- since Cancel had been the only way out of those
  states without ever appearing in the table. A consequence worth naming: `ERROR`
  and `LOST` are now table-identical; only the view (which keeps `LOST`'s event
  list and Reconnect label) tells them apart.
- **`set_session` is a synchronous push to `SnapshotPanel`**
  (`console_page.py:95` forwarding to `live_snapshot.py:120`), not a one-way
  adoption. Ruling at task 13: `MainWindow._refresh` already fans `set_session` to
  every page; without this, the pull -> window -> `_refresh` round trip would clear
  the "scene loaded" banner the same pull had just raised. Re-adopting the same
  session object is a no-op for exactly that reason.
- **The Console page stays on after a Pull, by a new function, not by changing
  `window_state.adopt_session`.** D16's text says this "needs a new adopt path:
  `window_state.adopt_session` (`:68-72`) unconditionally calls
  `switch_to("doctor")`" -- read as needing that function changed. Task 13 instead
  added `adopt_pulled_session` in `live_wiring.py` (everything `adopt_session` does
  except the page switch and the D4 recent-menu entry) and left
  `window_state.adopt_session` untouched, since a file-opened scene must still
  switch to Doctor. D16's *outcome* (stay on Console after a Pull) is exactly what
  shipped; only the mechanism differs from the sentence describing it.

