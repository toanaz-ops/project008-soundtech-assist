# Sub-project H — desktop application — outcome

**Date:** 2026-08-18 · **Branch** `claude_desk/soundtech-playground-handoff-6ab828`
· **688 tests passing, 1 skipped** (FastMCP, by design) · `doctor` on the
unprofiled real file still reports exactly **22 findings**

## What happened to the session's original plan

It opened on G2 — cue-sheet ingest — as the 2026-08-18 next-session prompt
recommended, and ToanAZ chose G2 from the roadmap. Two format questions in, he
redirected: he wants a desktop application that eventually drives a live WING,
and he scoped the first cut himself — *"phần cue chắc để sau đi, note lại plan
future, trước mắt chỉ làm scene 1 snap trước xem thế nào."*

G2 is therefore **deferred, not abandoned**, and everything settled about it
before the redirect is recorded in the new spec's §11.1 so the next cycle does
not re-derive it. He also waived the design-approval and plan-approval gates:
*"Ko cần tôi duyệt, viết plan xong implement luôn."*

## What shipped

**`wing_parser/edit/`** — no Qt anywhere in it, pinned by a subprocess test.

- `pointer.py` — read/write one leaf by dotted path against the whole document
  (`ae_data.ch.16.in.set.inv`). Refuses to create a missing key.
- `journal.py` — `Patch(path, before, after, because, label)` and `EditJournal`.
- `writer.py` — apply a journal to a deep copy, write a `.snap`.
- `repairs.py` + `data/repairs.yaml` — how to repair a finding, declared.

**`wing_parser/ui/`** — `session.py` is also Qt-free; everything else is widgets.

- `session.py`, `main_window.py`, `findings_model.py`, `findings_view.py`,
  `detail_panel.py`, `verdict_bar.py`, `changes_panel.py`, `__main__.py`.
- `wing-ui` console script and the optional `ui` extra.

**`core/loader.py`** gained `parse_raw(doc, path)` beside `load_raw(path)`, the
same split `showcontext` already had, so a scene can be rebuilt from a patched
document in memory.

## Measured, not assumed

Each of these decided part of the design, and each is reproducible.

| | Finding |
|---|---|
| PySide6 on Python 3.14.6 | `pip install --dry-run PySide6` resolves `pyside6-6.11.1-cp310-abi3-win_amd64.whl`; `abi3` is the stable ABI, so one wheel serves 3.10 up. Installed and running. |
| Lossless round trip | `{**meta, "ae_data": ae, "ce_data": ce} == json.loads(original)` for **both** sample files, which carry different top-level key sets — `factory-scene.snap` has six keys `example-Vu.snap` does not. `core/loader.py:37` builds `meta` as "everything except the two data blocks", so nothing unknown is dropped. |
| Re-derivation cost | `WingScene.load` 37 ms + `advisory.run` 104 ms; three whole-pipeline repeats at 90/103/99 ms. Cheap enough to re-run the entire engine after every single edit. |
| Target vs raw path | `doctor --json` targets (`ch.1.send.8`) are *nearly* the raw path (`ae_data.ch.1.send.8`). Nearly, not exactly — which is why repairs are declared per rule, not derived. |

## Four defects the work itself caught

**PB1's repair cannot be `set inv: true`.** `query/channel.py:63` defines
effective polarity as channel inversion **XOR** source inversion. PB1 fires when
the effective polarity is `False`, i.e. when `inv` *equals* the source's
polarity — so on a channel whose source is already inverted, `inv` is already
`true`, writing `true` changes nothing, and the button would report a repair that
did not happen. It has to flip the current value. Caught while writing the plan,
before a line of code existed, because the clearance test was designed first.

The sample file cannot distinguish the two — channel 16's source resolves to no
`SourceData`, so both forms produce `True` there.
`test_pb1_would_also_pass_with_a_set_descriptor_on_this_file` records exactly
that, so nobody "simplifies" the toggle away on the strength of a green suite.

**`wing-ui` built a second `QApplication`.** Qt permits one per process, and the
construction sat *before* the file named on the command line was validated. Now
the session loads first — so a bad path costs no Qt startup at all — and the
existing instance is reused.

**The matrix-send path was correct and completely untested, which is the
dangerous combination.** `_channel_sends` in the evaluator names a matrix send
target `ch.N.send.MX5`, keeping the raw file's own prefix, and the document
really does hold `ae_data.ch.N.send.MX5` beside `ae_data.ch.N.send.5` as two
different destinations — so the declared path template fills correctly for both
by construction. Nothing exercised it: ToanAZ's IEM matrix sends are all already
`PRE`, which is correct practice and exactly why G8 stays silent on them. A
template that had assumed a bare number would have looked perfect on the sample
file and written to **bus 5 instead of matrix 5** the first time an IEM send was
left post-fader — a silent wrong edit on the one signal path he most needs
protected. `test_a_matrix_send_target_repairs_the_matrix_send` now induces that
case and asserts bus 5 is untouched.

**The fourth is the worst, and it only exists in a packaged build**: a frozen
app would have written every recorded verdict into a directory the process
deletes on exit. Written up under **Packaging** below, because the packaging
work is what surfaced it.

## Which rules have a repair, and why the rest do not

**11 of the 39 base rules**, including **five of the seven `error`-severity
rules**:

| | Rule | What the repair writes |
|---|---|---|
| G8 | Monitor send is post-fader | `send.mode` → `PRE` |
| R4 | Send to a record destination is post-fader | `send.mode` → `PRE` |
| R5 | Main-send to a record main is post-fader | `main.pre` → `true` |
| R1 | Click reaches a FOH main | `main.on` → `false` |
| R2 | Talkback reaches a FOH main | `main.on` → `false` |
| R3 | Timecode into a mix destination | `send.on` → `false` |
| R3M | Timecode into a main | `main.on` → `false` |
| R6 | Remote caller feeds its own mix-minus | `send.on` → `false` |
| S1 | Speech channel without a high-pass | `flt.lc` → `true` |
| PC8 | Q&A mic unmuted | `mute` → `true` |
| PB1 | Snare bottom not polarity inverted | **toggle** `in.set.inv` |

R1/R2/R3/R3M/R6 share one argument: each fires on a send being *on* toward a
destination the signal must never reach, so off is the only value the predicate
admits. S1 switches an absent high-pass on and deliberately leaves `lcf` exactly
where the scene stored it — choosing a corner frequency is a different rule's
job, and every rule that *does* state a corner has no one-click repair.

Only two of the eleven fire on the untouched real file, so
`tests/test_edit_clearance.py` carries an `INDUCERS` table: a mutation per rule,
each lifted from the fixture that rule's own test already uses, so the two
suites cannot drift on what "this rule fires" means. A descriptor with neither a
real-file finding nor an inducer fails with a message saying exactly that.

Everything else deliberately has none. The line is whether the rule's own
predicate determines a single value:

- **A window or a count.** PB2–PB5, PC1, PC6 give an acceptable frequency
  *range*; G11 says there are too many notches without saying which to drop; G12
  says a boost is too high without saying what it should be.
- **A configuration, not a value.** G7 and G9 want a whole dynamics block.
- **Two defensible answers.** E6 (gate off, or leave the automix group?), S2.
- **Not about the scene at all.** Q1–Q7 are findings about the cue sheet.

The two remaining `error` rules, G7 and S2, are in that list on purpose: G7
wants a whole dynamics configuration, and S2's answer is either "take the
channel out of the automix group" or "turn the group off", which are different
decisions about the same fact.

## The load-bearing tests

- `test_each_repair_clears_its_own_finding` — asserts the total dropped by
  **exactly one**, not merely that the target vanished. Proven to bite: breaking
  G8's `to:` made it fail naming the surviving finding.
- `test_an_empty_journal_round_trips_both_sample_files` — parametrised over both
  files on purpose. A model-based writer would pass on one and lose six keys on
  the other.
- `test_the_edit_package_never_imports_qt` — a clean subprocess, not this
  process's `sys.modules`, which would pass trivially whenever no other test had
  imported Qt first.
- `test_a_matrix_send_target_repairs_the_matrix_send` — the `MX` branch, which
  no rule reaches on the untouched file.
- `test_the_unprofiled_real_file_still_yields_22_findings`.

## Next

**His stated destination is the live console**, and §4 of the spec is built for
it: writing `ae_data.ch.1.send.8.mode = "PRE"` to a file and sending the
equivalent OSC message are the same `Patch` leaving through two different doors.
Sub-project C needs a new sink, not a new edit layer.

**Read `docs/handoff/2026-08-18-wing-remote-probe.md` first.** It splits C into
the two questions that were being treated as one, answers the first, and closes
two dead ends so nobody walks into them again. In short:

- **The transport is known and cited.** The WING manual, page 50, documents OSC
  remote control on **IP port 2223** (with a second remote channel on 2222), a
  console **REMOTE LOCK** that blocks both, a ceiling of **16 simultaneous
  remote devices**, and that the console must be wired by Ethernet.
- **The address vocabulary is not, anywhere here.** One page of the manual's
  167 mentions OSC at all, and only to say the port can be locked.
  `WING-Edit.exe` yields nothing to an ASCII or UTF-16 string scan — its payload
  is packed. So this half has to come from observing a live console, or from an
  external protocol reference treated as hypothesis until probed.
- **The `ce_data.osc` probe is done, and it is a small answer.** Both sample
  files hold exactly `{"ronly": false}`. Worth carrying: the scene file has its
  own OSC read-only flag, *and* the console has REMOTE LOCK. Whether they are
  the same switch is unknown — a one-minute experiment at the console settles
  it. Until then a write path must account for both.

**An earlier version of this section claimed the whole protocol had to come from
outside the repo.** That was wrong about the transport half, and the mistake was
citing the knowledge-base summary instead of opening the manual sitting in
`user-files/`. The correction is the probe document; the lesson is in the last
section below.

Also open, unchanged by this cycle: the four questions in
`2026-08-18-next-session-prompt.md` §5 — the limiter `dyn.mdl` token, G10's
verdict, the `expects:` vocabulary split, and the missing MCP `show` parameter —
plus G2 (spec §11.1) and the twelve triaged G1 residuals.

## Packaging — done, and it exposed the worst bug of the cycle

`pyinstaller packaging\wing-ui.spec` builds a 66 MB `dist\wing-ui.exe` needing
no Python on the target machine. It was deferred at first as mechanical work.
It was not.

**A frozen build would have destroyed the feedback log.**
`config.knowledge_dir()` derives from `__file__`, and inside a PyInstaller
bundle that is the temporary extraction directory the process deletes on exit.
Everything that directory holds — `feedback.jsonl`, `principles.yaml`, `shows/`
— is written or edited by the operator. So the packaged app would have accepted
every verdict, written it, reported success, and thrown the file away on close.
No error, no warning, and the one loop this application exists to make usable.

The fix: when frozen, `knowledge_dir()` returns
`%USERPROFILE%\.config\wing-skill` and **deliberately does not consult
`SEARCH_ORDER`**, whose first entry is the bundle's own copy and would win.
`config.seed_user_dir()` copies the shipped set across once, never overwriting
anything already present, and is called from the entry point rather than from
the resolver — resolving a path should not write to disk.

Two things about how this was confirmed are worth carrying:

- **The tests were proven to bite.** Removing the frozen branch turns two red,
  including an end-to-end case that records a verdict, deletes a simulated
  bundle, and reads the log back.
- **The real binary was run, not reasoned about.** On its first launch it
  created `%USERPROFILE%\.config\wing-skill` containing `principles.yaml`,
  `classifier.yaml`, `feedback.jsonl` and `shows\small.yaml`. That copy is
  itself the proof the frozen branch fired: `seed_user_dir` only copies when the
  destination does not exist, so had `knowledge_dir()` still resolved to the
  bundle's own copy, nothing would have been written at all.

**Run the `.exe` from local disk, not from the Google Drive path.** Launched
from `Z:\My Drive\...` it did not start within two minutes and `Start-Process`
itself blocked; copied to local disk it starts in seconds. A one-file bundle
unpacks 66 MB before its first line of code runs. This is a property of where
the file sits, not of the build — and it is the same Drive-path slowness the
environment notes already warn about for `git` and `ripgrep`.

Also noted: `pip` reports *"Defaulting to user installation"* on this machine,
so the interpreter in use has no virtualenv.

## What this cycle taught

- **Designing the test before the descriptor caught a defect the descriptor
  would have hidden.** PB1's XOR was invisible on the sample file and would have
  stayed invisible; it was found by asking "what would make this repair a no-op?"
  while there was still nothing to run.
- **A test that passes on the only available fixture can still be blind.** Both
  PB1 forms are green on `example-Vu.snap`. The response was not to weaken the
  claim but to write down, in the test file, what the fixture cannot prove.
- **The honest-absence rule scales.** Q7 ships disabled for want of a citable
  threshold; the repair table covers 11 rules of 39 and says nothing about the
  other 28. Both are the same decision, and stating it in the UI — "no one-click
  repair for this rule, and here is why" — costs one label and buys trust in
  every button that *is* there.
- **A correct-looking path that no test walks is a bug waiting for the worst
  input.** The `MX` prefix was right by construction and unexercised, because the
  only file available has that case already *correct*. The general shape:
  when a fixture is a real working system, the paths it never lights up are
  exactly the paths that will first be lit by a mistake. Go and induce them.
- **The cheap probe is worth doing even when the answer is small.** Opening
  `ce_data.osc` took a minute and returned two words — `{"ronly": false}`. That
  is not an address table, and knowing so retires a line that had been carried
  forward twice as "someone should look". It also produced one fact a write path
  will need: the console can be set to refuse OSC writes.
- **A summary is not a source, and this cycle proved it the expensive way.**
  This document first stated that the WING OSC protocol was undocumented here,
  citing `Behringer-WING-Integration.md` — a knowledge-base *summary*. The
  actual manual was sitting in `user-files/` unopened, and page 50 names the
  port. The project's own standing rule already says a citation is not
  verification and to open the file the claim actually names; the failure was
  opening a file *about* the subject instead of the primary document. Ask "what
  is the most primary source I have?" before writing "there is no source".
- **A worktree is not the checkout.** The manual and `WING-Edit.exe` are
  gitignored, so they do not exist inside a git worktree. The first probe failed
  with `FileNotFoundError` and read exactly like "the file is not here". Any
  probe touching an ignored artefact must run from the main checkout.
- **"Mechanical" work is where the environment-shaped bugs live.** Packaging was
  deferred as the boring part and turned out to hold the most damaging defect of
  the cycle, because freezing changes what `__file__` means and every path in
  this project is derived from it. The general form: a step that changes the
  *shape of the runtime* rather than the code deserves the same suspicion as a
  feature, not less.
- **Run the artefact.** The frozen fix had passing tests before the binary was
  ever built. Running it produced a second, independent proof — the seeded
  directory could only exist if the frozen branch fired — and also the Google
  Drive launch failure, which no test would ever have found.
