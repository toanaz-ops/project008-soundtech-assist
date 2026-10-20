# GUI wave 5 — durable write log + post-show report

Status: design, 2026-10-20. Reviewed once by Fable against `main` @ 7a839e9.
Builds on wave 3 (`2026-09-17-gui-write-wave3-design.md`) and **overturns
its ruling W8** ("exactly one new persisted key, no write log").

## 1. Goal

Every value the app writes to a live WING desk survives the app closing.
After the show, ToanAZ opens one page, picks the show by its show code, and
exports one HTML report. The report says what changed, when, on which desk,
why (which Doctor finding), what the desk held before, what it reads back
now, and whether the change was reverted.

Why: today the "Sent to console" ledger exists only in memory
(`ui/changes_ledger.py:70`). If the app is closed or crashes, the record of
what was done to a venue's desk is lost. A sound engineer gets asked for
exactly that record after a show ("what did you change on our desk?"), and
needs it himself before the next show at the same venue.

## 2. Decisions

| # | Decision | Who |
|---|---|---|
| F1 | Wave 5 direction: write log + post-show report. It comes before the mix-taste advisory and before metering | ToanAZ 2026-10-20 |
| F2 | Report format: **one self-contained HTML file**. It opens in a browser and prints to PDF | ToanAZ 2026-10-20 |
| F3 | The log is grouped **by show**. A show is identified by its **show code** from the company system (PRJ012 / ClickUp), not by its name. One show code gives one log and one report | ToanAZ 2026-10-20 |
| F4 | The log is viewed on a **new 8th sidebar page "Log"** (Ctrl+8), with an Export report button | ToanAZ 2026-10-20 |
| W1 | One JSONL file per show code, under `<knowledge_dir>/write-log/`, named `<CODE>.jsonl` (e.g. `AZ-1501.jsonl`). Arming the same code again (a multi-day show, or a re-arm) appends to the same file | ASSUMED (orchestrator) |
| W2 | The file is append-only, one JSON object per line, UTF-8, written with `ensure_ascii=False`. A corrupt line is skipped with a warning, never fatal. This is the pattern `advisory/feedback.py:46-97` already uses | ASSUMED |
| W3 | A log write failure (any `Exception`) **never blocks or undoes a desk write, and never skips anything downstream of it**. The failure appears as a persistent warning line on the Log page and in the Changes dock, naming the folder | ASSUMED |
| W4 | One line is appended when each write or revert settles, not at app close | ASSUMED |
| W5 | The Log page is **read-only**. There is no revert from a past session, because the desk's present state is unknown. Wave 3's revert stays in the Changes dock of the session that sent the write | ASSUMED |
| W6 | No automatic deletion or rotation; a show's log is tens of lines. "Open log folder" lets him delete old logs by hand | ASSUMED |
| W7 | The report is written in the UI language at export time (EN or VI), using the same `text()` tables. Mixer nouns stay English (B2) | ASSUMED |
| W8' | Persisted UI state gains one key, `last_show` = `{code, name, venue}`. Together with the log itself, this overturns wave-3 W8 | ASSUMED |
| W9 | The show code is required to arm. It must match `^(AZ-\d+\|AZA-\d{6,})$` after folding to upper case. PRJ012 gives a ClickUp-origin show `AZ-<n>` (`clickup_custom_id`) and an in-app show `AZA-NNNNNN` (`show_code`). Both are unique and never reused. Name and venue are optional free text, at most 80 characters each, and printed in the report | ASSUMED |
| W10 | The non-UI parts (store, entry shape, code validation, HTML rendering) live in a new package `wing_parser/writelog/` that can be tested without Qt. The UI only adapts signals into entries | ASSUMED |
| W11 | No online code → name/venue lookup in this wave. PRJ012's `GET /shows?search=` needs a JWT or an agent token, and the laptop is often offline at the venue. A cached lookup may come in a later wave | ASSUMED |
| W12 | For a show that has no code yet, a **No code (ad-hoc)** tick generates `ADHOC-YYYYMMDD-HHMM` from local time. A repair is never blocked because the office has not created the job | ASSUMED |
| W13 | Desk identity and the show (code, name, venue) are captured **when the write is submitted** and travel with it to the log. They are never read from the gate at settle time: `WriteGate.close()` calls `arm.disarm()`, which clears the identity, while an in-flight write can still settle afterwards (`write_gate.py:102-113`, `apply_level.py:54`) | ASSUMED (Fable review) |
| W14 | A revert's `finding` comes from an in-session map of `path` → the finding of the last repair on that path. It is `null` only when unknown | ASSUMED (Fable review) |

ToanAZ also answered on 2026-10-20 (recorded in ROADMAP §5): keep G10
suppressed on small shows; audience rules read `$fdr` and strip rules read
`fdr`; the limiter list comes later. None of these are part of this wave.

## 3. Entry shape

One line per settled write or revert:

```json
{"v": 1,
 "ts": "2026-10-20T13:05:12.481+07:00",
 "show_code": "AZ-1501", "show": "BIDV Gala", "venue": "GEM Center",
 "desk": {"name": "WING-GIAQUY", "serial": "…", "model": "WING", "firmware": "3.1", "ip": "192.168.128.28"},
 "kind": "repair",
 "finding": "G7:bus.iem.3",
 "label": "Insert limiter (IEM 3)",
 "address": "/bus/3/dyn/on", "path": "ae_data.bus.3.dyn.on",
 "file_before": 0, "desk_before": 0, "written": 1, "readback": 1,
 "outcome": "sent",
 "scene": "bidv.snap",
 "app": "0.1.0"}
```

- **`kind`**: `repair` for a Doctor Repair, or `revert` for a Changes-dock
  Revert or Revert all.
- **`finding`**: for a repair, `Patch.because` (`rule_id:target`,
  `edit/repairs.py:110`). For a revert, see W14.
- **`label`**: the Patch label, `"<repair label> (<target>)"`
  (`edit/repairs.py:111`).
- **`outcome`**: `sent`, `clamped` or `no_reply`, from
  `write_records.outcome()` (`ui/write_records.py:72-96`). These are the same
  three states as the ✓ / ⚠ / ✗ badges.
- **`desk`**: the `WingIdentity` fields (`net/identity.py:34-39`), captured
  at submit time (W13). `WriteConfirmation.identity` already carries this to
  the Delayed dialog.
- **`app`**: `wing_parser.__version__`.
- **`scene`**: `window.session.path`. For a pulled session this is a bare
  filename.
- **`ts`**: `datetime.now().astimezone().isoformat(timespec="milliseconds")`,
  stored and rendered as-is, never converted. This deliberately differs from
  `feedback.py`, which records UTC.
- **`v`**: the entry-format version. A reader skips a line whose `v` it does
  not know, with a warning.

## 4. Where it hooks in

- **Settled repair.** All three apply levels converge on
  `ChangesPanel.record_sent` (`ui/changes_panel.py:69-73`):
  - Manual arrives via `SendRow.sent`.
  - Delayed and Immediate arrive directly from `route_repair`'s `on_sent`
    (`live_wiring.py:106-109`).

  `SendRow`s are rebuilt on every refresh, so they are not a stable hook.
  Instead, add `sent = Signal(object, object)` on `ChangesPanel` and emit it
  at the **end** of `record_sent`, after the badge, the ledger row and the
  scene correction. The adapter subscribes to that signal.
- **Settled revert.** `SentLedger.reverted(record, result)`
  (`ui/changes_ledger.py:66`).
- **Desk identity and show.** These are captured at submit (W13). The
  cleanest carrier is a new field on `SentWrite`, set in
  `write_router._record` (`write_router.py:37-40`). The builder may choose
  another carrier, as long as nothing is read from the gate at settle time.
- **Wiring** goes in `live_wiring.install_write_gate`
  (`ui/live_wiring.py:80-115`).
- **Errors.** The adapter catches `Exception`, never re-raises, and is
  connected after `record_sent` has done its own work (W3).
- **Threading.** The append runs on the GUI thread, because settle callbacks
  arrive there via `CallRunner`. That is fine for a local file. A
  `WING_KNOWLEDGE_DIR` on a network share would stall the UI; this is
  accepted and documented.
- **Allow-list.** The AST allow-list (`tests/test_ui_live_is_read_only.py:85`)
  must stay at exactly one module, `live_write.py`. The adapter must not
  import `wing_parser.net.write`; it duck-types the result, as
  `write_records.py` does.
- **The `writelog` package.** `wing_parser/writelog/` is outside the AST
  scan root (`:71`), so the scan will not catch it. It still must not import
  `wing_parser.net`: add a test that asserts this.

## 5. Arm dialog

Wave 3's Arm step has a fresh identity check, the "desk NOT running a show"
tick, and typing the desk name. It gains these fields above the confirm
button:

- **Show code**: required, validated per W9, with the No code (ad-hoc) tick
  from W12.
- **Show name**: optional.
- **Venue**: optional.

All three are prefilled from `last_show`. Arm stays disabled until the code
is valid. On arm, `last_show` is saved, and the show stays attached to the
arm state for the rest of the connection. Wave 3 does not keep arm across a
reconnect, so re-arming after a reconnect asks again, prefilled.

The dialog is `ui/write_arm_dialog.py` (157 lines). If it reaches the
200-line ceiling, split it by responsibility; never raise the ceiling.

Because `normalize` drops unknown keys, `last_show` must be added in three
places: `state_store.DEFAULTS`, `normalize`, and
`window_state.save_on_close`. Extend the DEFAULTS tests to cover it.

## 6. Log page (8th, Ctrl+8)

- **Left pane:** the list of shows, newest first. Each row shows the show
  code, name, venue, first–last date, number of writes, and ✓ / ⚠ / ✗
  counts.
- **Right pane:** the chosen show's entries in time order, as a table with
  the same columns as the report (§7).
- **Buttons:**
  - **Export report…** opens a save dialog with default name
    `<CODE>-report.html`.
  - **Open log folder.**
  - **Refresh.** This is a button, not F5: F5 is bound app-wide to
    reanalyse (`menus.py:55`).

  The page also re-reads the folder each time it is shown.
- **Warning line:** shown when an append failed this session (W3), or when
  lines were skipped as unreadable.
- **Empty state:** "No writes logged yet. Repairs sent to a desk appear
  here."
- **Wiring:**
  - Add the page to `PAGE_KEYS` (`state_store.py:23-24`). Ctrl+8 follows
    automatically (`menus.py:58-62`).
  - Also add it to `PAGE_ICONS`, the `pages` dict, and a `page.log` text
    key.
  - `main_window.py` is at 198 lines, so split it first.
  - Merge `texts_log_vi.py` in `texts_vi_all.py`.

## 7. HTML report

One file with inline CSS and no external fonts or scripts, readable when
printed. Every inserted value goes through `html.escape`. The report has
four parts:

1. **Header:** show code, show name, venue, date range, desk(s) (name,
   serial, firmware), app version, and export time.
2. **Summary:** total writes, ✓ / ⚠ / ✗ counts, reverts, and the findings
   addressed.
3. **Table:** one row per entry, in time order, with these columns: time,
   desk, address, label, finding, file before, desk before, written, read
   back, outcome badge, and kind.
4. **Footnote:** what ✓ / ⚠ / ✗ mean, in the export language.

## 8. Texts

- The new namespace `log.*` lives in a new `texts_log.py` /
  `texts_log_vi.py` pair, merged into the tables like `texts_write.py`.
- The Arm fields use keys under `console.write.arm_*`.
- The existing parity, placeholder and no-literal tests apply to all of it.

## 9. Tests and acceptance

- **`writelog` store:**
  - It round-trips.
  - A corrupt line is skipped with a warning; so is an unknown `v`.
  - Show code validation: `AZ-1501` is accepted, and `aza-000001` is
    accepted as `AZA-000001`. `AZ-`, `ABC-1` and `../x` are refused.
  - ADHOC code generation works.
  - Appending to an existing file works.
  - The package does not import `wing_parser.net`.
- **Report:**
  - HTML is escaped: a show name `<script>` renders as text.
  - Counts are correct.
  - It renders in both languages.
- **Adapter**, with FakeDesk, at **all three levels** (Manual, Delayed,
  Immediate):
  - A repair writes one `repair` line with finding, desk and outcome.
  - A revert writes one `revert` line whose finding comes from W14.
  - If an append raises any `Exception`, the write still settles; the badge,
    ledger row and scene correction still happen; and the warning shows (W3).
  - A write that settles after `gate.close()` still logs its desk (W13).
- **Arm dialog:**
  - The code is required and validated.
  - The ad-hoc tick works.
  - All three fields are prefilled from `last_show`, and `last_show` is
    saved.
- **Log page:**
  - It lists shows and shows the chosen show's entries.
  - It exports through a save seam.
  - Ctrl+8 and the tab order work.
- **House style:**
  - Every UI file is ≤200 lines.
  - The allow-list is still exactly one module.
  - EN/VI parity holds.
- **Acceptance:**
  - End to end with FakeDesk.
  - The real desk gets one added step in
    `docs/acceptance/2026-09-wave3-desk-acceptance.md`: after the repairs
    there, open Log, export the report, and read it.

## 10. Out of scope

- Reverting from a past session (W5).
- Log retention or rotation (W6).
- Online code lookup against PRJ012 (W11).
- Logging writes made with the CLI `net set/push`. The CLI is not used
  during a show.
- PDF export. The browser prints the HTML to PDF.
- Syncing the log anywhere off this machine.
