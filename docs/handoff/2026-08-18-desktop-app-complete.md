# Sub-project H — desktop application — outcome

**Date:** 2026-08-18 · **Branch** `claude_desk/soundtech-playground-handoff-6ab828`
· **677 tests passing, 1 skipped** (FastMCP, by design) · `doctor` on the
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

## Three defects the work itself caught

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

Two things to know before starting C:

- **This repository does not document the WING OSC protocol.**
  `docs/knowledge-base/01-live-audio-ai/Behringer-WING-Integration.md` mentions
  exactly one address, `/ch/5/in/set/srcauto`, at lines 57 and 183, both times
  about assigning a User Button. No address table, no OSC code anywhere.
- **The `ce_data.osc` probe is done, and it is a small answer.** Both sample
  files hold exactly `{"ronly": false}` — nothing else. So the block is a
  console *setting* for the OSC interface, not an address table, and the one
  thing it does tell us is worth carrying: **the WING has an OSC read-only
  toggle**, off in both files. A write path must read that flag and say so when
  it is on, rather than sending messages a console is configured to ignore. Do
  not re-open this looking for addresses; there are none here.

**So the address vocabulary has to come from outside this repo** — the WING OSC
documentation, or observation of a live console. That is the first real task of
sub-project C, and it is the reason the roadmap sizes it "large".

Also open, unchanged by this cycle: the four questions in
`2026-08-18-next-session-prompt.md` §5 — the limiter `dyn.mdl` token, G10's
verdict, the `expects:` vocabulary split, and the missing MCP `show` parameter —
plus G2 (spec §11.1) and the twelve triaged G1 residuals.

**Not done here, deliberately:** a frozen `.exe`. The app runs from the repo,
which is the thing to package once it is known to work. Note for whoever does
it: `pip` reports *"Defaulting to user installation"* on this machine, so the
interpreter in use has no virtualenv.

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
