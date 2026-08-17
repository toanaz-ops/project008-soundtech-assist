# Sub-project G — input pipelines (show context) — design

**Date:** 2026-08-17 · **Decided with ToanAZ in session** · Supersedes nothing.
Phase-1 spec §14 deferred this as one line ("Voice, lyric, or cue-sheet input
pipelines"); everything below is new.

## 1. Scope, and the split

The advisory reads a **static** scene today: one snapshot, no notion of when a
channel is supposed to be live. Show context adds the time axis — which sources
the show calls for, and which channels each cue touches.

Decomposed into two cycles, both designed here so the file format is not
redrawn later:

| | scope | character |
|---|---|---|
| **G1** — build now | show-context format, loader, query view, two iterators, rules Q1–Q7, CLI | deterministic, offline, testable; useful even when the file is typed by hand |
| **G2** — spec only | assisted ingest from CSV/Excel and from PDF/photo into the G1 format | best-effort, boundary-only, human-reviewed |

The G1/G2 line is where determinism ends. Everything below the show-context
file is deterministic and pinned by tests. Everything above it is best-effort
and produces a file ToanAZ reads before it is used.

## 2. What it must catch

ToanAZ selected these three failures (2026-08-17), and rejected a fourth:

1. **A cue names a channel that is not there** — the cue sheet says `CH3 open`;
   the scene has no channel 3, or has one with no name.
2. **The show calls for a source that has no channel** — the setlist says this
   segment has keys; no channel classifies as `instrument.keys`, or one does
   and it is muted with the fader at -inf.
3. **Two cues disagree** — consecutive cues contradict each other's channel
   state, or sit closer together than the operation between them takes.

**Rejected: "a live channel no cue ever touches."** His scenes are templates —
`example-Vu.snap` has 34 named channels and 3 live — so that rule would fire
constantly on channels that are simply parked. Do not re-mine it.

## 3. The contract — the show-context file

```yaml
show: "Tiệc cuối năm Sơn Hải"
date: 2026-09-14

segments:
  - id: S2
    title: "Band set 1 — Bài 1: Nắng"
    time: "T+00:18:00"          # optional, ROS column 1 format
    expects: [drums.kick, instrument.bass, instrument.keys]
    cues:
      - id: "SQ 8"
        action: open             # open | close | up | down | recall
        channels: [13, 25, 29]
        dcas: [2]
        time: "T+00:18:04"       # optional
```

Three decisions, each with its reason:

**`expects:` uses the classifier's own vocabulary** (`instrument.keys`), not free
text. Rule Q4 then becomes set subtraction rather than another layer of name
guessing — and this project already has exactly one name-guessing layer, on
purpose. The loader validates every entry against the known kind vocabulary and
raises listing the valid values, the same way an unrecognised `--profile` name
and an unrecognised `event:` value already do. The cost is that ToanAZ must
consult the kind list while authoring; the error message prints it.

**`time:` is optional at both levels.** Q7 fires only when *both* cues in a pair
carry a time. A file that does not state a time gets silence, never an assumed
one. This is the standing "never fabricate a value the file does not state"
constraint applied to a new file format.

**Channel state is derived by walking the cues in order**, keeping an open/closed
book per channel. That turns "two cues disagree" into something decidable:
closing a channel already closed, opening one already open.

Only `open` and `close` move that book. `up`, `down` and `recall` are recorded
and checked for channel and DCA existence (Q1–Q3) but leave the open/closed
state untouched — a level move on a closed channel is not a contradiction, and
what a `recall` does to any given channel is not knowable from the cue sheet.
Segments and cues are read in file order; `time:` never reorders them, because a
cue sheet with times out of order is a document error the tool should show
rather than silently sort away.

## 4. Where it plugs in

New package `wing_parser/showcontext/`, split by responsibility, each file short:

- `models.py` — frozen records `ShowContext`, `Segment`, `Cue`.
- `loader.py` — YAML → records; vocabulary and structural validation.
- `view.py` — the query-layer view; derived properties resolved against the scene.

Loaded through `WingScene.load(path, show=...)`; `scene.show` is `None` when no
file was given.

Two iterators join `ITERATORS` in `wing_parser/advisory/evaluator.py:100`:
`cue` and `segment`. **Both yield nothing when `scene.show is None`** — the same
shape as the existing `_nothing` iterator, which is what keeps every current
behaviour bit-identical. `targets_for` takes only `(scene, for_each)`, so the
context must hang off the scene; changing that signature would touch every
iterator for no gain.

Target names follow the existing convention (`ch.8.send.MX5`): `cue.S2.SQ8` and
`segment.S2`. Cue ids are written the way a show caller says them (`SQ 8`), so
internal whitespace is stripped when building the target name; the id keeps its
spaces everywhere it is displayed. Two cues in one segment whose ids differ only
by whitespace are a duplicate-id error, caught at load time.

## 5. Derived properties expose counts, not collections

The predicate language has seven operators — `not`, `in`, `not_in`, `gt`, `lt`,
`is_null`, `starts_with` (`wing_parser/advisory/predicates.py:21`) — and no
emptiness test. A property returning a tuple would have to be tested as
`{not: []}`, which is **always true** in Python (`() != []`), so the rule would
sit silent forever and no test written against a tuple-returning stub would
catch it.

So every derivation is exposed as a count, matched with `gt: 0`. This is the
existing `notch_count` pattern, not a new one.

On `Cue`: `missing_channel_count`, `unnamed_channel_count`, `missing_dca_count`,
`contradiction_count`, `seconds_after_previous` (float or `None`).
On `Segment`: `unmet_expect_count`, `dark_expect_count`.

Each count has a companion `*_text` string property for the message template,
so a finding names the actual channel numbers rather than a bare count.

## 6. The rules

Prefix `Q`. Derived live with `load_base_rules()` on 2026-08-17: the 32 shipped
rules use E, G, N, R, S, PB and PC — `Q` is free.

| id | severity | fires when |
|---|---|---|
| Q1 | warning | `cue.missing_channel_count > 0` — the cue names a channel the scene does not have |
| Q2 | info | `cue.unnamed_channel_count > 0` — the channel exists but carries no name |
| Q3 | warning | `cue.missing_dca_count > 0` — the cue names a DCA the scene does not configure |
| Q4 | warning | `segment.unmet_expect_count > 0` — an expected kind has no confidently-classified channel |
| Q5 | info | `segment.dark_expect_count > 0` — a channel of that kind exists but `Channel.in_use` is False |
| Q6 | warning | `cue.contradiction_count > 0` — the cue contradicts the state the previous cues left |
| Q7 | warning | the gap to the previous timed cue is shorter than the operation needs |

Q5 reuses `Channel.in_use` (`wing_parser/query/channel.py:128`) rather than
defining a second liveness test: patched, unmuted, routed, and fader above the
-90 dB floor that keeps a factory scene from reading as live. A rule that
invented its own "is this channel on" check would drift from N1's.

Q4 and Q5 both require the classifier, so they inherit the existing
`requires_classifier` gate and are skipped for any target below the usable
confidence band — the same protection that stops the rest of the advisory
producing confident nonsense about channels nobody could identify.

**Q7 ships `enabled: false`.** No source in this repository states how long a
mic change, a scene recall or a patch change takes, and ToanAZ chose (2026-08-17)
to wait for a real number rather than accept a placeholder. Its rationale must
say so and name what would switch it on. This is the N2 precedent: an honest
disable beats a noisy rule.

## 7. CLI and error handling

`doctor scene.snap --show tonight.yaml`, combinable with `--profile`.

`feedback` takes `--show` too, and this is not cosmetic: per README:111-117,
`feedback` resolves a finding id by re-running the same rules `doctor` printed,
so a Q-finding id will not resolve unless both commands get the same flags.

Hard errors, raised naming the file and listing the valid values: file not
found, unknown `expects` kind, unknown `action`, duplicate segment or cue id.

Soft error: a malformed `time:` becomes an anomaly, not an exception. Time is
optional and feeds only Q7, which ships disabled — failing the other six rules
on show day over one mistyped clock cell is the wrong trade.

## 8. G2 — assisted ingest (designed, not built)

ToanAZ's cue sheets arrive as Excel/Google Sheets and as PDF, print or phone
photo (2026-08-17). Neither is deterministically parseable, and
`core`/`query`/`advisory` may not call an LLM.

The resolution is the pattern `wing_parser/classifier/llm.py` already
establishes: the LLM lives at the boundary, behind `WING_DISABLE_LLM` and the
optional `anthropic` extra, and what it produces carries a confidence into a
layer that is itself deterministic.

`showcontext import <file> -o tonight.yaml` — a separate command, never inline
in `doctor`. CSV/Excel map columns by declaration; PDF and photo go through the
boundary extractor. Output is always a file ToanAZ reads before it is used, with
every row carrying its confidence and its source line.

**Import never invents a cue.** A row it cannot read is emitted as a comment in
the output file, never dropped silently — the failure mode to design against is
a cue sheet that looks fully imported and is missing three rows.

## 9. Testing

The load-bearing test is the invariance one: a scene loaded **without** `--show`
still yields exactly the 22 findings pinned in `tests/test_advisory_realfile.py`.
That is what proves the feature cannot leak into existing behaviour.

Beyond it: unit tests per module; a hand-written show context for
`example-Vu.snap` pinned as a contract table with its regeneration command in
the docstring, matching the existing real-file test; `pytest.approx` for the
time arithmetic. Every Q rule carries `source:` and `rationale:` because
`wing_parser/advisory/loader.py:49` refuses to load a rule without them — no new
test is needed for that, and writing one would only re-assert an existing
guarantee.

## 10. Rejected approaches, recorded so they are not revisited

**A separate `wing rehearse` command** with its own report. Fastest to build and
touches no existing code, but its findings would sit outside the three-layer
override mechanism and outside `wing feedback`. The entire project is one
advisory, three layers, and a human verdict; this would have created a second
world exempt from that.

**Show context inside `knowledge/toanaz/shows/<name>.yaml`.** Reuses the profile
loader for free, but conflates two different lifetimes: a profile is durable
policy for a *kind* of show, a cue sheet is data for one show on one date. It
would fill `knowledge/` with dated files, and since `--profile` takes exactly one
name, ToanAZ could not use `small` and tonight's cue sheet at the same time.

**Free-text `expects:`.** Easier to type, but adds a second name-guessing layer
whose failure mode is silence — a mis-mapped name means the rule quietly never
fires, which is worse than an error at load time.

## 11. Open questions

1. **Q7's threshold.** One number per action, or one flat number. Needed before
   Q7 can be enabled. ToanAZ chose to defer it rather than guess.
2. **Whether `expects` should also accept a bus or matrix** ("this segment needs
   IEM 3 live"). Not designed; raise it only if a real cue sheet calls for it.
3. Unrelated and still open from earlier cycles: the limiter `dyn.mdl` token,
   closed as offline-underivable in `docs/handoff/2026-08-17-limiter-token-probe.md`.
