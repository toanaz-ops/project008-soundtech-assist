# Sub-project H — desktop application — design

**Date:** 2026-08-18 · **Decided with ToanAZ in session** · Supersedes nothing;
this is a new subsystem alongside `cli/` and `mcp/`.

## 1. Scope, and what this is not

A Windows desktop application that opens one `.snap` scene, shows what the
advisory engine found, lets ToanAZ repair the things it found, records his
verdict on each finding, and saves the result as a **new** `.snap` file.

The long-term goal he stated is different and larger: an application that talks
to a live WING over the network — read parameters, push faders. That is
sub-projects C and D in the Phase 1 roadmap, and this spec deliberately stops
short of it. He scoped this cut himself: *"trước mắt chỉ làm scene 1 snap trước
xem thế nào."*

**Not in this cut:** any network traffic, any OSC, any live console, cue-sheet
ingest (§11.1), and any parameter edit the advisory engine cannot justify (§5).

**The constraint that shapes everything else:** this app must not become a
second implementation of the tool. `core`, `query`, `advisory`, `classifier` and
`showcontext` stay exactly as they are, deterministic and offline. The
application is a **presentation layer plus an edit layer**, nothing more. If a
question about a scene can be answered by `WingScene`, the UI asks `WingScene`
rather than reading raw JSON itself.

## 2. Decisions taken in this session

Recorded so they are not re-litigated. Each names who decided it.

| | Decision | By |
|---|---|---|
| 2.1 | Qt via **PySide6**, native desktop, not a local web UI | ToanAZ, from three options |
| 2.2 | First cut is **one `.snap` file, offline** — no live console | ToanAZ |
| 2.3 | The app **may edit and save**, always to a new file, never over the original | ToanAZ |
| 2.4 | The editable set is **exactly what the advisory rules complain about** | ToanAZ, from three options |
| 2.5 | The main window is the **findings report**, not a console mirror | ToanAZ approved from three options |
| 2.6 | Edits are held as an **edit journal**, not applied in place | ToanAZ approved |
| 2.7 | Cue-sheet ingest (G2) is **deferred**, recorded in §11.1 | ToanAZ |

**Verified in session, not assumed:**

- **PySide6 6.11.1 installs on this machine.** `pip install --dry-run PySide6`
  resolved `pyside6-6.11.1-cp310-abi3-win_amd64.whl`. The `abi3` tag is the
  CPython stable ABI, so one wheel serves 3.10 upward, including the 3.14.6
  interpreter here. There is no Python-version risk in choice 2.1.
- **`RawScene` reassembles losslessly.** `{**meta, "ae_data": ae, "ce_data": ce}`
  compares equal to `json.loads(original)` for **both** sample files.
  `example-Vu.snap` and `factory-scene.snap` carry *different* top-level key sets
  — the latter additionally has `ae_globals`, `ce_globals`, `created`,
  `creator_fw`, `creator_sn`, `creator_version` — and both round-trip, because
  `core/loader.py:37` builds `meta` as "every key except `ae_data` and `ce_data`"
  rather than from a known list. A writer therefore cannot silently drop a key
  this project does not understand.
- **A full re-analysis costs about 100 ms.** `WingScene.load` 37 ms plus
  `advisory.run` 104 ms on `example-Vu.snap`; three repeated whole-pipeline runs
  measured 90, 103 and 99 ms. The UI can re-run the entire engine synchronously
  after every single edit without a progress indicator. This is what makes §4's
  design affordable.
- **A finding's `target` is nearly the raw JSON path.** `doctor --json` yields
  targets such as `ch.1.send.8`, and the raw document holds
  `ae.ch.1.send.8 = {"on": true, "lvl": -15, "pon": false, "mode": "POST", ...}`.
  The correspondence is close because both mirror how the WING organises a scene.
  It is *not* exact, and §5 refuses to rely on it.

## 3. Architecture — where the Qt boundary sits

Two new packages. The split is not stylistic: it is what makes the edit logic
testable without a running GUI.

```
wing_parser/edit/          NO Qt. Pure data. Fully unit-tested.
  journal.py     Patch record + EditJournal (append, undo, iterate)
  pointer.py     resolve a dotted path against the raw document
  repairs.py     load the repair descriptors, answer "how do I fix this finding?"
  writer.py      apply a journal to a raw document and write a .snap
  data/repairs.yaml   the descriptors themselves

wing_parser/ui/            Qt only. Widgets, models, signals. No rule knowledge.
  __main__.py       QApplication boot, nothing else
  session.py        holds scene + journal, re-runs the engine, emits changed
  main_window.py    window shell, menus, Open / Save As
  findings_model.py QAbstractTableModel over the findings
  findings_view.py  the table, severity and layer filters
  detail_panel.py   the selected finding: rationale, source, evidence, controls
  repair_widgets.py the small edit controls, built from a descriptor
  verdict_bar.py    correct / false-positive / irrelevant -> advisory.feedback
  changes_panel.py  the journal as a list, with undo
```

Every file above is expected to sit well under 200 lines. `session.py` is the
only place that knows both halves, and it holds no widgets.

`PySide6` becomes an optional extra, `ui`, exactly as `mcp` and `anthropic`
already are. Importing `wing_parser.edit` must never import Qt; a test asserts
this, because the moment it does, the CLI grows a GUI dependency.

## 4. The edit journal

The application never mutates the loaded document. It holds:

- `original: dict` — the parsed `.snap`, immutable by convention
- `journal: EditJournal` — an ordered list of `Patch`

```python
@dataclass(frozen=True)
class Patch:
    path: str          # "ae.ch.1.send.8.mode"
    before: Any        # what was there, captured at append time
    after: Any         # what it becomes
    because: str       # "G8:ch.1.send.8", or "manual"
    label: str         # one human line for the review list
```

After every append the session applies the whole journal to a **deep copy** of
`original`, rebuilds `WingScene` from it, re-runs the advisory, and emits the new
findings. At 100 ms this is imperceptible, and it buys a property worth far more
than the milliseconds: **the findings list is always the truth about the current
state, never a stale list with edits pencilled on top.** A repair that does not
actually clear its finding is visible immediately, in the same second it is made.

Three things fall out for free, and they are the reason this shape was chosen
over mutating in place:

1. **Undo** is dropping the last patch and re-deriving.
2. **"What have I changed?"** is the journal, displayed as a list before saving —
   not a diff the user must compute against the original file.
3. **It is the bridge to sub-project C/D.** Writing
   `ae.ch.1.send.8.mode = "PRE"` into a file and sending the equivalent OSC
   message to a live console are the *same patch* leaving through two different
   doors. Choosing this structure now means the OSC work is a new sink, not a
   rewrite of the edit layer.

`before` is captured when the patch is appended, not recomputed at save time, so
a journal remains a truthful record of what the operator saw when they decided.

**Saving.** `writer.py` deep-copies `original`, applies the journal, and writes
`json.dumps` to the new path. It never writes to the path it loaded from; Save As
is the only save. The window title carries the loaded file name and an asterisk
while the journal is non-empty.

## 5. Repair descriptors — the app must not invent a fix

The dangerous version of this feature is a [Fix] button that guesses. The rule
here is the same one Q7 already follows in the advisory layer: **an honest
absence beats a confident guess.**

`edit/data/repairs.yaml` declares, per rule, what a repair is. A rule with no
entry simply shows no repair control, and that is a complete and honest answer.

```yaml
repairs:
  - rule: G8
    kind: set                     # set | toggle | text | number
    path: "ae.ch.{channel}.send.{send}.mode"
    to: "PRE"
    label: "Đổi send sang PRE"
    rationale: >
      G8 fires only on mode POST reaching a monitor bus, so PRE is the
      single value that clears it. No other key is touched.
```

Two categories, and the difference is decided by the rule's own predicate:

- **Determined repair** — the rule fires on one value, so exactly one value
  clears it. `G8` (send `mode` POST → PRE), `R4`/`R5` (same shape on record
  destinations), `R1`/`R2`/`R3`/`R3M`/`R6` (turn the offending send `on: false`),
  `PC8` (`mute: true`), `S1` (`flt.lc: true` — the channel already carries an
  `lcf` frequency; the rule complains the filter is off, not that it is
  mistuned), `PB1` (`in.set.inv: true`). These get a one-click repair.
- **Undetermined repair** — the rule states a *window* or a *count*, so no single
  value follows. Every HPF-window rule (`PB2`–`PB5`, `PC1`, `PC6`), `G11` (which
  notch?), `G12` (reduce to what?), `PC7` (which weight?), `G7`/`G9` (a whole
  dynamics configuration), `E6` and `S2` (gate off, or leave the automix group?
  two defensible answers). These get **no** one-click button. They get a manual
  field showing the current value and the window the rule cites, so the operator
  chooses and the app records the choice.

`Q1`–`Q7` get nothing at all: they are findings about the cue sheet, not about
the scene, and no scene edit can answer them.

Every descriptor carries `rationale:`, and the loader refuses one without it —
the same contract `advisory/loader.py:49` already enforces on rules. A repair
that cannot say why it is correct does not ship.

**The load-bearing test, one per descriptor:** load the sample scene, confirm the
finding is present, apply the descriptor's patch, re-run the advisory, and assert
**that finding is gone and the total count dropped by exactly one.** A descriptor
that does not clear its own finding is a bug the suite catches, not something
discovered in front of a console. This is what keeps §2's "nearly the raw path"
observation from becoming an assumption.

## 6. The window

One window, three regions, and a menu.

- **Findings table** (centre, the front door). Columns: severity, rule, target,
  message, layer. Sorted severity-first. Filter chips for severity and for layer,
  because the layer a finding came from is the thing that tells him whether it is
  a shipped rule or his own principle firing.
- **Detail panel** (right, follows selection). The finding's message, the rule's
  `title`, `rationale` and `source` verbatim — the rationale is the argument he
  is being asked to accept or reject, so it belongs on screen, not behind a
  tooltip — the `evidence` map, and whatever repair control §5 allows.
- **Verdict bar** (under the detail). Three buttons, `correct` /
  `false-positive` / `irrelevant`, plus a note field, writing straight through
  `advisory.feedback.record`. Today this costs him typing
  `wing feedback G8:ch.8.send.8 --verdict false-positive --scene ...` with the id
  copied by eye. Making it two clicks is the single highest-value thing this
  window does, because the verdict log is how his judgement enters the rule set
  at all.
- **Changes list** (a dockable panel, hidden until the journal is non-empty). The
  journal, with undo.
- **Menu:** Open, Save As, Undo, and a profile selector for
  `--profile <name>`, which is already a first-class concept in the engine.

The verdict bar shows the running count from `feedback.summarise()` for the
selected rule — "G8: 4 correct, 7 false-positive" — because that count is the
evidence a principle should be written, and it is invisible today.

**Honest naming.** The feedback log is not training in the machine-learning
sense, and the UI must not imply that it is. `advisory/feedback.py:3` states it
plainly: the log exists so a pattern becomes visible across many shows, and *a
human writes the resulting principle*. The button is "ghi nhận", not "dạy".

## 7. Error handling

The existing layers already raise `ValueError` with the file name in the message,
and the CLI prints `error: {exc}`. The window does the same in a message box and
stays open on the previously loaded scene — a failed Open must never leave the
operator with an empty window and a lost session.

- **A file that is not a WING snapshot** → `core/loader.py` already refuses with a
  named message. Surface it verbatim.
- **A repair whose path does not exist in this document** → refuse the patch and
  say which path was missing. Do not create intermediate keys. A scene from a
  different firmware may legitimately lack a key, and inventing it writes a
  structure the console never had.
- **Save fails** (path locked, disk full) → the journal is untouched and the
  window stays dirty. Nothing is lost.
- **PySide6 missing** → `wing-ui` prints one line naming the extra to install.
  The engine and CLI must keep working with no GUI installed at all.

## 8. Testing

- `edit/` is tested with no Qt import at all: journal append/undo, pointer
  resolution against a real loaded document, writer round-trip, descriptor
  loading.
- **The round-trip test is load-bearing:** open a sample `.snap`, save it with an
  empty journal, and assert the re-parsed result equals the re-parsed original.
  Run it against **both** sample files, because they have different top-level key
  sets and that is exactly what proves the writer preserves what it does not
  understand.
- **One clearance test per determined repair** (§5).
- The unprofiled real file must still yield exactly **22 findings**. This app adds
  no rules, so that contract is untouched and a test must confirm it stayed that
  way.
- Qt widget tests are kept thin and are not the safety net — the safety net is
  that no decision lives inside a widget.

## 9. Packaging

`pip install -e ".[ui]"` and a `wing-ui` console script, matching the existing
`wing` and `wing-mcp` entries. A single-file `.exe` via PyInstaller is worth
doing but is **not** part of this cut: it is an independent piece of work with
its own failure modes, and shipping the app runnable from the repo first means
the packaging work can be verified against something already known to run.

Noted for whoever does it: `pip` reports *"Defaulting to user installation
because normal site-packages is not writeable"* on this machine, so the
interpreter in use has no virtualenv. That will matter when freezing.

## 10. Rejected approaches

**A local web UI (FastAPI + browser, or pywebview).** Faster to make attractive,
and genuinely tempting. Rejected because it inserts an HTTP and WebSocket layer
between the UI and the engine that buys nothing in this cut and becomes a
liability in the next one: live fader movement over a socket to a local server
that then speaks OSC is two hops where one will do. It also puts a listening
socket into a tool whose defining property is that it is fully offline.

**Electron or Tauri with a separate frontend.** Two languages, two build chains,
a Python sidecar. Against the stated goal of finishing quickly.

**A console-mirror main window** (a strip per channel, as the WING presents
itself). It is the right shape for the OSC era and the wrong shape now: forty
strips of faders and EQ is a large amount of interface, and in this cut almost
none of it would be editable, because §2.4 limits editing to what the rules
complain about. Deferred rather than rejected — §11.2.

**Mutating the loaded document in place.** Simpler by one indirection, and it
loses undo, loses the review-before-save list, and loses the patch record that
sub-project D needs. See §4.

**A generic JSON tree editor.** Powerful and quick to build, and it has no idea
what a legal value is for any key. It would let a typo reach a console with
nothing in the path to stop it.

## 11. Future work, recorded so it is not re-derived

### 11.1 G2 — cue-sheet ingest, deferred 2026-08-18

Designed in `2026-08-17-input-pipelines-design.md` §8 and analysed further in
this session before ToanAZ deferred it. What was established, so the next cycle
starts here rather than from the beginning:

- **The four enabled cue rules need no LLM.** `Q1`, `Q2`, `Q3` and `Q6` are fed
  entirely by cue id, action, channels and DCAs, and the ROS template
  (`docs/knowledge-base/04-templates-and-matrices/Master-Run-Of-Show-ROS.md` §1.1)
  carries all of them in one column — the **Audio Cue** column, in the documented
  form `SQ 8 GO — CH3 open, DCA2 up`. `Q7` needs only the **Time** column, in the
  documented form `T-12:00` / `T+1:04:30`. A purely deterministic spreadsheet
  importer therefore feeds every cue rule that is switched on.
- **Only `Q4` and `Q5` need `expects:`, and no ROS column carries it.** The
  nearest source is the Talent table's `Mic` column ("Shure Axient AD2 handheld —
  CH4"), which lives in a different section and in prose. This is the only part
  of the import that requires inference, and it is worth one warning and one info
  rule — which is what makes deferring the whole LLM boundary affordable.
- **Order decided:** Excel/CSV first, PDF and photo second.
- **Output shape decided:** deterministic cues written live; any inferred
  `expects:` written as **commented-out** lines carrying confidence and the source
  row, so no guessed value is ever in force without a human uncommenting it.
- ToanAZ can supply real cue sheets in both Excel and PDF/photo form. **Get them
  before designing further** — and note that `user-files/` is not wholly
  gitignored (only three named entries are), while a real cue sheet carries client,
  talent and venue names. Add ignore lines and build anonymised fixtures.

### 11.2 Sub-projects C and D — the live console

The stated destination: read parameters from a running WING and push faders back.
§4's journal is the join. Two things to know before starting:

- **This repository does not document the WING OSC protocol.**
  `docs/knowledge-base/01-live-audio-ai/Behringer-WING-Integration.md` mentions
  exactly one address, `/ch/5/in/set/srcauto`, twice (lines 57 and 183), and both
  times in the context of assigning a User Button. There is no address table and
  no OSC code anywhere in the tree. C is genuine protocol work, which is why the
  roadmap sizes it "large".
- A scene's `ce` block contains an `osc` key. Nobody has looked at what is in it.
  That is the cheapest first probe available and it costs one session-minute.

### 11.3 Remaining from earlier cycles

The four open questions in `2026-08-18-next-session-prompt.md` §5 are untouched by
this work and still need him: the limiter `dyn.mdl` token, G10's verdict, the
`expects:` vocabulary split, and the missing MCP `show` parameter.

## 12. Open questions

1. **Which repairs are genuinely determined** is asserted in §5 from the rule
   texts, and each one must be confirmed against the raw document during
   implementation, one at a time, by the clearance test. Where a rule turns out
   to fire on more than one value, it moves to the undetermined list rather than
   acquiring a guessed default.
2. **Whether the app should read a show context** (`--show`) at all in this cut.
   It would light up `Q1`–`Q6` in the table for free, since the engine already
   takes the parameter. Left out for now because §11.1 defers the file's
   *production*, and a feature that requires hand-writing YAML before it does
   anything is not the fastest path to something he can use.
3. **Vietnamese or English interface text.** All existing user-facing output is
   English. This is a personal tool for a Vietnamese engineer, and the labels are
   the one place where that could reasonably change. Not decided.
