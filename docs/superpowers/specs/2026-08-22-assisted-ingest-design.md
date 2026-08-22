# Sub-project G2a — reading a cue sheet (the deterministic half)

**Date:** 2026-08-22 · **Status:** design authority for
`wing_parser/showcontext/ingest/`

Every claim this spec makes about existing code was made by opening the named
file at the time of writing, not from memory, and each carries its
`file:line`. Every claim about ToanAZ's working reality was answered by him on
2026-08-22 and is marked as such. Where something is **not** established, §12
says so rather than letting silence read as agreement.

This spec follows `2026-08-17-input-pipelines-design.md`, which built
sub-project G1 (`wing_parser/showcontext/`). It does not modify that subsystem;
it adds a producer of the records G1 already consumes.

It **supersedes §8 of that spec**, "G2 — assisted ingest (designed, not built)".
§8 was written before ToanAZ described his real inputs, and three of its
premises turned out to be wrong (§2).

## 1. Purpose, and why G2 is two specs

G1 made a show-context file useful. It did not make one easy to obtain: today
the file is hand-typed. G2 closes that gap.

G2 splits along one axis — **does it need the network?**

| | | needs network |
|---|---|---|
| **G2a** | this spec: sheet → show-context, by declared mapping | no |
| **G2b** | later: a model proposes the mapping, and guesses unknown terms | yes |

The split is not "small half / large half". It is the project's existing
boundary, drawn in the same place `wing_parser/classifier/llm.py` draws it: the
deterministic layer must work with the uplink dead, because this tool is used in
venues where the uplink is dead.

**G2a is useful alone.** ToanAZ writes one mapping file per recurring client and
adds vocabulary entries as he meets new words. G2b only removes typing; it
unlocks no capability.

## 2. What the input actually is — established with ToanAZ, 2026-08-22

Asked what reaches him, ToanAZ named **all four** of: Excel/Google Sheets, PDF
(print or export), phone photograph, and **loose Zalo messages / a spoken
running order**. The fourth was not anticipated by G1 §8 at all.

Asked which single one he would want working before the next show, he chose
**Excel/Sheets**. G2a therefore reads spreadsheets and nothing else. PDF, photo
and free text each get their own reader later, behind the same interface (§8).

Three answers overturned G1 §8's premises:

1. **The sheet does not carry channel numbers.** A row names people and
   instruments, gives a time or running order, and carries free-text notes.
   Channel numbers are the sound engineer's own annotation, not the director's.
   G1 §8 assumed a row could be mapped to a cue with `channels:`; it cannot.
2. **Every producer sends a different layout.** Different column names, different
   column counts, and a header row that is often not row 1. G1 §8's "CSV/Excel
   map columns by declaration" survives, but "declaration" has to mean a
   per-client file, not one built-in schema.
3. **The free-text note column carries real information** and cannot be mapped to
   any closed vocabulary.

Because of (2), reading an arbitrary spreadsheet's *structure* is itself a
judgement task. G2a does not perform it — ToanAZ declares the structure once per
client, in a file he keeps (§4). G2b will offer to propose that file.

## 3. What G2a delivers, and what it does not

A row becomes a `Segment` with `expects:`. It does **not** become a `Cue`,
because there are no cues on the paper (§2, item 1).

That has a measured consequence for the advisory layer. Reading
`wing_parser/advisory/base_rules/showcontext.yaml`:

| rule | line | `for_each:` | fires on an imported file? |
|---|---|---|---|
| Q1 "Cue names a channel the scene does not have" | 5 | cues | no |
| Q2 "Cue names a channel that carries no name" | 26 | cues | no |
| Q3 "Cue names a DCA number the console does not have" | 46 | cues | no |
| **Q4 "Show expects a source with no channel for it"** | **72** | **`expects`** | **yes** |
| **Q5 "Show expects a source whose channels are all parked"** | **102** | **`expects`** | **yes** |
| Q6 "Cue repeats a channel state an earlier cue already set" | 130 | cues | no |
| Q7 "Two cues sit closer together than the operation needs" | 163 | cues, but **ships `enabled: false`** (:166) | no, and never |

Two of seven. State this plainly in the README and in the command's own output,
because a file that produces two rules' worth of findings must not read as a
file that produced all seven.

The two that do fire are the pre-doors check: the paperwork calls for a source
and the scene has no confidently-classified channel for it (Q4), or has one that
is unpatched, muted, unrouted, or parked below the −90 dB floor (Q5).

Both already **aggregate per expected kind, not per segment** — Q4's and Q5's
`rationale:` record that as ToanAZ's decision of 2026-08-17. A thirty-row ROS
therefore cannot produce thirty identical warnings. That trap was closed in G1
and G2a inherits the closure; no new work is needed for it.

For Q1, Q2, Q3 and Q6 the imported file is a **skeleton to add cues into**. Q7
is excluded from that list on purpose: it carries `enabled: false`
(`showcontext.yaml:166`) and `evaluator.evaluate` returns `[]` unconditionally
for a disabled rule (`evaluator.py:158-160`), so no cue revives it. G2a
never invents a cue.

## 4. The mapping file

One file per recurring client, kept in `knowledge/toanaz/sheets/`. Around ten
lines, written while looking at the spreadsheet.

```yaml
source: "Công ty ABC — ROS template 2026"   # free text, for the human
sheet: "KỊCH BẢN"        # sheet name, or a 1-based index if the sheet is unnamed
header_row: 4            # 1-based, the number Excel shows in the row gutter
columns:                 # identified by column letter
  title: C
  time: B
headers:                 # identified by the text in the header cell
  performers: "Nghệ sĩ / Thành phần"
  note: "Ghi chú"
```

**`title` is the only required field**, in either block. `id`, `time`,
`performers` and `note` are optional; an absent `performers` means every segment
gets an empty `expects:`, which is valid and produces a skeleton.

`sheet:` is read by YAML type, not by guessing: an **integer** is a 1-based
index, a **string** is a sheet name. A workbook whose sheet is literally named
`3` is therefore addressed as `sheet: "3"`, and the quoting carries the whole
distinction. This is the one place where the format's own types settle an
ambiguity that would otherwise need a heuristic, which is why it is worth
stating rather than leaving to the reader.

`header_row` must be the row containing the column headings, not the first data
row. Its cells are what `headers:` matches against (§4.2), and it is also the
row from which data reading starts, at `header_row + 1`.

### 4.1 Why two blocks and not one

A single block would have to decide, per value, whether `STT` means "column
STT" or "the header cell reading STT". Vietnamese running orders very commonly
head their first column **STT** (số thứ tự) — a string that is simultaneously a
plausible three-letter column reference and a real header. Any heuristic picks
one and is silently wrong on the other.

Two blocks remove the question instead of answering it. A field named in **both**
blocks is refused, naming both, in the same spirit as
`wing_parser/showcontext/vocabulary.py:resolve` refusing a tie rather than
picking a side.

### 4.2 Header matching is exact, not repaired

A header name is matched by **exact equality after normalisation** — trim,
collapse internal whitespace, casefold. There is deliberately **no
distance-1 repair**, even though `vocabulary.py` provides one and the header row
is a closed set.

The reason is the one §3.1 of the G1 spec established: that module's radius comes
from a **measurement** — the channel vocabulary's minimum pairwise
Damerau-Levenshtein distance is 2, which is why repair runs at radius 1 with a
uniqueness requirement. The minimum pairwise distance between the header cells
of a real cue sheet has never been measured, and it is easy to imagine a sheet
with `Ghi chú 1` and `Ghi chú 2` sitting at distance 1. **No measurement, no
radius.**

When a declared header is not found, the error lists the header cells actually
present in that row, verbatim. That is more useful than a guess: ToanAZ copies
the right one back into the mapping.

A header text that appears in **two** columns of the header row is also refused,
naming both column letters.

### 4.3 Why letters at all, given headers are more robust

Because ToanAZ writes this file with the spreadsheet open, and the column letter
is what the application is showing him. `header_row` is 1-based for the same
reason. Robustness against an inserted column is exactly why `headers:` exists
alongside; the two coexist so he can use whichever the sheet makes safe.

A letter may name a column **whose header cell is blank**. That is not an
oversight to tolerate but the case letters exist for: an unlabelled notes or STT
column is common on a real running order, and it is precisely what `headers:`
cannot express. The escape hatch has to be open in the one situation it is the
only way in.

The bound is the sheet, not the header row: a letter is accepted anywhere up to
the **last column holding anything at all** (`sheet.py` reports that extent
alongside the headers) and refused past it, naming that last column and listing
the columns that do have a heading. Refusing every letter absent from the header
row instead — which is what "column X has no header" once meant — closed the
hatch exactly where it was needed.

## 5. What one row becomes

One data row → one `Segment`.

| mapped field | becomes |
|---|---|
| `title` | `title:`, verbatim |
| `id` | `id:`, verbatim unless it repeats one already used (below); absent → generated `S1`, `S2`, … in file order, stepping over any the sheet already spent |
| `performers` | split on `,`, `/`, `;` and newline → each fragment resolved through the `cuesheet` vocabulary (§6) → deduplicated into `expects:` |
| `note` | a **YAML comment** on that segment |
| `time` | a **YAML comment** on that segment, verbatim |
| a `performers` fragment that resolves to nothing | a **YAML comment**, verbatim |

**Segment ids are unique, and `build.py` is where that is enforced.** Nothing
about a producer's spreadsheet prevents two rows carrying the same number, and
two things downstream cannot survive it. `showcontext/loader.py:104` refuses a
file whose ids collide after `.lower()`, so the importer would otherwise write,
with exit 0, a file this project's own loader then rejects. Worse,
`propose.for_segments` returns a dict **keyed by segment id** and `emit.render`
looks each proposal up by that key: a collision is last-write-wins, and one
segment's channel numbers are printed above another's `cues:` — a `# --scene:`
line saying a bass channel belongs to a segment expecting a guitar. That is a
claim the sheet never made, in the one place the file asks to be read literally,
and it fails silently.

A repeat is therefore disambiguated rather than passed through: the later
occurrence becomes `S1-2`, then `S1-3`, folded the same way the loader folds
(`.lower()`), and **the change is recorded as a comment on that segment** —
nothing is altered without saying so. A generated id steps over any the sheet
already spent, so `S1, <blank>` cannot produce `S1` twice either.

### 5.1 Why `note:` and `time:` are comments and not fields

`Segment` has no `note` field (`wing_parser/showcontext/models.py:24-29`), and
adding one would create a field with no consumer.

`Segment` *does* have `time`, and G2a still refuses to populate it. Two measured
reasons:

1. **`Segment.time` is read by nothing.** `grep '\.time\b'` across
   `wing_parser/` returns exactly one hit — `wing_parser/showcontext/view.py:226`
   — and that reads `cue.time`, serving Q7. Since G2a produces no cues, nothing
   downstream would ever look at a segment time it wrote.
2. **The formats do not meet.** `wing_parser/showcontext/loader.py:27
   _parse_time` accepts only show-relative `T+HH:MM:SS`, `T+MM:SS` or the `T-`
   forms; anything else returns `None` and the loader records an anomaly and
   discards the value. A spreadsheet's time cell is wall-clock, and `openpyxl`
   commonly hands it back as a `datetime.time` object, which fails
   `_parse_time`'s `isinstance(text, str)` guard on its first line.

Converting wall-clock to show-relative would need a declared show start and
would produce a value **no code reads**. It is therefore not built. This
paragraph exists so a later cycle does not mistake the omission for an oversight
— if segments ever gain a time consumer, revisit it then, with that consumer in
hand.

## 6. The Vietnamese vocabulary — a third `classifier.yaml` domain

`wing_parser/classifier/data/patterns.yaml` is 111 lines and every pattern in it
is English or a console abbreviation: `\bgtr\b`, `\bhs\d*\b`, `\bspd\b`, `kick`,
`snare`. It is tuned for **strip labels on a desk**. A Vietnamese running order
saying *trống*, *đàn tranh*, *ca sĩ nữ*, *tốp múa* matches none of it. Where a
word does match — *guitar*, *bass*, *piano* — that is a loanword coinciding, not
a design.

These are two different naming domains: nobody labels a console strip "ca sĩ
nữ", and no director writes "HS4".

ToanAZ chose (2026-08-22) **vocabulary first, model second**: a table he curates,
with a model consulted only for terms the table lacks, and its answers offered
for permanent recording. G2a builds the table half; G2b adds the model half.

### 6.1 Reuse `classifier.yaml`, do not build a second store

`wing_parser/classifier/cache.py` already provides everything this table needs,
and adding a domain to it is backward-compatible with files already on disk:

- `DOMAINS` (`cache.py:22`) is referenced in exactly two places, both inside
  `cache.py` itself (`:64`, `:120`) — verified by grep across the repo.
- `_read` fills a missing domain with `{}` (`cache.py:65-66`), so an existing
  `classifier.yaml` with no `cuesheet:` section loads unchanged.
- `remember` already creates an absent domain (`cache.py:135-136`), and `lookup`
  takes the domain as a plain string.
- Entries are written through a sibling temp file and one atomic rename
  (`cache.py:75-91`), and via `ruamel` round-trip so comments survive.
- A hand-written entry outranks the pattern matcher — stated in the file's own
  seed header (`cache.py:24-36`).

The entry shape already fits: a `cuesheet` entry maps a normalised Vietnamese
phrase to `kind` + `confidence` + `origin`, exactly what `_one` requires
(`cache.py:96-109`).

Add `"cuesheet"` to `DOMAINS` and extend `_SEED` with a `cuesheet: {}` section
and a comment saying what the domain is for.

### 6.2 One mandatory repair that no test will catch

`cache.py:60-63` raises with a message hard-coded to
*"the top level must be a mapping with a channels: and a buses: section"*. Adding
a third domain makes that sentence false while the code around it stays correct.

This is the failure shape the C2 handoff §9 named as this project's recurring
one — correct code with a false description, which survives every green suite
because **no test runs an error message**. Fixing it is a required task, not a
nicety, and the fix must be checked by reading the message, not by running the
suite.

### 6.3 Resolution order for a performers fragment

1. Normalise (`wing_parser/classifier/normalize.py:clean`, the same
   normalisation the cache keys on).
2. `cache.lookup(fragment, "cuesheet")` — a hand-written or previously recorded
   entry wins.
3. Fall through to the existing `channels` pattern matcher, which catches the
   loanwords (*guitar*, *bass*, *piano*) for free.
4. Nothing → emit the fragment as a verbatim comment (§5). **Never** guess.

Step 3 uses the confident band the advisory layer already uses. A fragment
resolved below it is treated as unresolved and goes to step 4, because a weak
guess entering `expects:` would make Q4 stop catching the thing it exists for —
the same argument Q4's own `rationale:` makes about channel classification.

## 7. `--scene`: proposing a cue skeleton, as comments only

`channels:` is **not** a segment field. Reading
`wing_parser/showcontext/models.py`, `Segment` (`:24-29`) carries
`id / title / time / expects / cues`, and `channels` belongs to `Cue`
(`:14-20`). An importer that produces no cues therefore has nowhere to put a
channel number at all — not even an empty one.

So the proposal `--scene` writes is a whole **commented-out cue**, which is the
concrete form of the "skeleton to add cues into" that §3 promises:

```yaml
  - id: S3
    title: "Tiết mục 3 — Guitar solo"
    expects: [instrument.guitar]
    # --scene: ch 13 'GTR' is instrument.guitar
    # delete this and the line(s) above; replace "cues: []" below with:
    # cues:
    #   - id: "S3 cue 1"
    #     action: open
    #     channels: [13]
    cues: []
```

Every segment carries a real `cues: []`. It is true — the segment has no cues —
the loader reads it as empty (`entry.get("cues") or []`), and it gives the
proposal a key to anchor to. `ruamel`'s
`yaml_set_comment_before_after_key` needs a real key to attach a comment before,
and without `cues` a segment has none after `expects`. The alternative was
hand-rolled YAML scalar quoting, which has silent edge cases (U+2028, an
all-whitespace scalar) and would be new code where existing code will do.

Applying it does more than fill in a number: it turns the segment into
something Q1, Q2 and Q6 can read -- and Q3 too, once he names a DCA -- which is
how ToanAZ moves an imported file
from two live rules to seven.

**Stripping the `#` is not applying it.** `cues: []` is still standing below the
uncommented lines, the loader reads a segment's cues with `entry.get("cues")`
and ignores every other key, and an unrecognised key is not an error — so a
naively uncommented proposal parses cleanly and changes nothing. That is why the
proposal's own text names the lines to delete and says the rest **replaces**
`cues: []`. Nothing in the generated file, the CLI summary or the README may say
"uncomment" of it.

The join itself reuses `wing_parser/showcontext/view.py:138 _channels_of`, which
already selects channels whose classification matches the kind at or above the
confident band (`HIGH`, 0.8) — the same threshold Q4 and Q5 use. Promote it to a
public `channels_of` rather than importing a private name, and update its two
existing call sites (`view.py:183`, `:187`).

Nothing is ever written outside a comment. This is a join between two things
already computed — it adds **no new name-guessing layer**, which matters because
this project has exactly one such layer on purpose.

## 8. Modules

```
wing_parser/showcontext/ingest/
  sheet.py     spreadsheet -> RawRow list                   ~120 lines
  mapping.py   parse and validate the mapping file          ~160 lines
  build.py     RawRow + vocabulary -> Segment + comments    ~140 lines
  propose.py   Segment + scene -> commented-out cue (§7)     ~50 lines
  emit.py      Segment -> YAML with comments (ruamel)       ~110 lines
```

Line counts are targets against the ~200-line ceiling, not budgets. `mapping.py`
is the largest because refusing an ambiguity means *explaining* it, and every one
of its error messages prints the real alternatives (§9).

Data flows one way: `sheet.py` → `mapping.py` → `build.py` → `propose.py` →
`emit.py`. No module calls back up.

`propose.py` is separate from `build.py` rather than folded into it precisely
because it needs the scene. `build.py`'s whole guarantee is that it performs no
I/O and takes no scene, which is what lets every interpretation decision be
tested without a filesystem; giving it a scene would dissolve that.

`mapping.py` needs the header row's cells to resolve the `headers:` block, so it
**receives** that row as an argument rather than opening the file itself. This
keeps `sheet.py` the single module that knows `openpyxl` exists — which is what
makes a later CSV, PDF or photo reader a sibling of `sheet.py` with the other
three untouched.

`build.py` performs no I/O. It takes rows and a vocabulary lookup and returns
records plus the comment list, which makes it the module where every
interpretation decision is unit-testable without a file.

`emit.py` writes through `ruamel.yaml`, following
`wing_parser/showcontext/rewrite.py`'s existing precedent and reason: comments
are the payload here, not decoration, so a plain `yaml.dump` would destroy the
output's whole point.

### 8.1 CLI

```
wing showcontext import <sheet.xlsx> --map <mapping.yaml> [-o out.yaml] [--scene <scene.snap>] [--force]
```

Registered beside the existing `showcontext lint` at
`wing_parser/cli/__main__.py:98-104`.

- `--map` is **required** in G2a. Its absence is an error naming the flag; G2b
  will make that path propose a mapping instead.
- Without `-o`, the YAML goes to stdout, so ToanAZ can read it before anything
  touches his disk.
- With `-o`, an existing file is **not** overwritten unless `--force` is given.
- `import` is a Python keyword but appears here only as a subcommand string, so
  it raises no `argparse` dest problem. (The C2 cycle lost time to `--for`,
  whose dest `args.for` is a syntax error; this one is checked and safe.)

### 8.2 Dependencies

`openpyxl` and `pypdf` are **installed in the current environment but declared
nowhere** — `pyproject.toml:13` lists only `PyYAML` and `ruamel.yaml`. Code
importing them today works on this machine and fails on a clean one, silently
and only at runtime.

G2a declares `openpyxl` in a new `ingest` extra **and** in the `dev` extra. The
`ingest` extra keeps the core install light, matching how `llm` and `mcp` are
handled. Putting it in `dev` too is deliberate: the load-bearing fixture test
(§10) must never skip on a developer machine, because a skipped test hides a
regression exactly as well as a missing one.

`sheet.py` catches the `ImportError` and raises a message naming the extra. Note
that this is the **opposite** of what `wing_parser/classifier/llm.py:available`
does with a missing `anthropic` — it swallows the `ImportError` and returns
`False` (`:60-69`), because the model is an optional fallback and the tool is
designed to work without it. A spreadsheet reader is not optional to a
spreadsheet reader, so its absence is a stop, not a quieter path.

`pypdf` is not used by G2a and stays undeclared.

## 9. Error handling — the never-invent guarantee

One rule across every layer: **anything unreadable becomes a verbatim comment.
Nothing disappears.**

| situation | behaviour |
|---|---|
| mapping file malformed, or `title` declared in neither block | raise, naming the file, the problem and the accepted fields |
| a field declared in both `columns:` and `headers:` | raise, naming both |
| named sheet absent | raise, listing the sheet names that exist |
| `header_row` out of range or empty | raise, giving the row count |
| a declared header not found in the header row | raise, listing the header cells found, verbatim |
| a header text found in two columns | raise, naming both column letters |
| a `columns:` letter past the sheet's last populated column | raise, naming that last column and listing the columns that do have a heading (§4.3) |
| a `columns:` letter inside the sheet whose header cell is blank | **accepted** — this is what letters are for (§4.3) |
| two rows carrying the same `id` | the later one is written `S1-2`, and the change is a comment on that segment (§5) |
| blank row inside the table | skipped, and counted |
| row whose `title` cell is empty | verbatim comment, **not** a segment |
| performers fragment that resolves to nothing | verbatim comment on that segment, and counted |
| unreadable `time` cell | verbatim comment (it is always a comment) |
| malformed or unparseable `classifier.yaml` | raise, naming the file — it is documented as hand-editable, so a typo in it is an expected outcome and must reach the CLI as `error: …`, never a traceback |

The output file always ends with a reconciliation line, and the `-o` summary on
stderr states the same counts:

```yaml
# imported 34 data row(s) -> 31 segment(s) carrying 22 expectation(s), 3 row(s) and 2 performer fragment(s) kept as comments, 1 blank row(s) skipped
```

This exists because the failure mode G1 §8 named — *a cue sheet that looks fully
imported and is missing three rows* — is not prevented by never dropping a row.
It is prevented by making the count checkable at a glance.

**It must count expectations, not only rows.** `performers:` is optional (§4),
and a mapping that omits it gives every segment `expects: []` — which is valid,
and which produces row counts, a summary line and a trailer **byte for byte
identical** to a correct import's. It is invisible further downstream too: such
a file adds nothing to a `doctor --show` run, so the finding count matches a run
with no `--show` at all. Without a number for what the segments actually expect,
the same failure G1 §8 named is simply displaced from rows down to fields, and
every surface the user looks at says the import succeeded. The count of
performer fragments kept as comments is stated for the same reason: it is the
other way `expects:` ends up emptier than the sheet.

## 10. Testing

**The load-bearing test is the invariance one**, carried over from G1 §9: a scene
loaded **without** `--show` still yields exactly the **22** findings pinned in
`tests/test_advisory_realfile.py`. That is what proves this feature cannot leak
into existing behaviour. Measured baseline at the start of this cycle:
**1056 tests collected, exit code 0** (1055 passing, 1 skipped by design).

Beyond it:

- **A real `.xlsx` fixture, generated by a script left behind in
  `docs/probes/`** — because §11 of the C2 handoff holds that a measurement
  nobody can re-run is not evidence. The fixture must contain, deliberately: a
  header on row 4 rather than row 1; a column headed `STT`; a blank row inside
  the table; a row with an empty `title`; and a performers fragment that
  resolves to nothing.
- **A contract test** pinning that fixture plus its mapping to the exact YAML
  output, with the regeneration command in the docstring, matching the existing
  real-file test's style.
- **A test that a field declared in both blocks raises**, asserting the message
  names both.
- **A test that an unreadable row is present in the output as a comment** — not a
  test that it fails to crash. The C2 handoff §9 records three tests in this
  repo that asserted nothing and were green the whole time; a "does not crash"
  test on an emitter is exactly that shape.
- **A test that the reconciliation count matches** the number of segments plus
  comment rows.
- Unit tests per module. `build.py` needs no filesystem at all.

For every new test, ask *"if this broke, would it go red?"* — and then **break it
and watch**. Green is the best camouflage.

## 11. Rejected approaches, recorded so they are not revisited

**Hand the whole sheet to a model and take back a show-context file.** Fastest to
write and the least trustworthy. It cannot be tested, it gives no way to tell
which rows were dropped, and it violates the standing constraint against
fabricating a value the source does not state. Two hundred rows through a model
is precisely the "looks fully imported, missing three rows" failure G1 §8 was
written to prevent.

**A skeleton-only importer** that interprets nothing and emits every row as a
stub. Zero risk and nearly zero help — but it is retained as the **fallback
behaviour** for any row the mapping cannot read (§9), which is where it belongs.

**Fuzzy-matching header names.** Rejected in §4.2: the radius would rest on no
measurement.

**One `columns:` block accepting letters or header text.** Rejected in §4.1: the
`STT` collision is real and any resolution of it is a guess.

**Converting wall-clock times to show-relative.** Rejected in §5.1: no consumer
exists.

## 12. Open questions

1. **No real cue sheet of ToanAZ's has been read yet.** This spec is built from
   his description of his sheets (§2), not from a file. A real `.xlsx` dropped
   into the repo before implementation would likely change the fixture and may
   change the mapping fields. **Ask for one before Task 1.**
2. **The `cuesheet` vocabulary starts empty.** Which Vietnamese terms seed it is
   ToanAZ's call about his own work, not a technical one. It can start empty and
   grow, but a seed of twenty common terms would make the first run useful.
3. **Should a resolved `performers` fragment record its source row?** The cache
   entry has a `matched:` field that could hold it. Nothing reads it today.
4. **Google Sheets is named in §2 but not handled.** G2a reads a downloaded
   `.xlsx`. Whether a link should be fetched directly is a separate question with
   an authentication answer attached, and is not in this spec.

## 13. Relationship to the multi-provider question

ToanAZ asked on 2026-08-21 for the design to admit providers other than
Anthropic. On 2026-08-22 he chose: **not this cycle, but leave the room.**

G2a contains no model call, so it neither creates nor blocks that work. G2b will
contain two — proposing a mapping, and guessing an unknown term — and both
should go through one interface taking a prompt plus a schema and returning a
validated object.

What makes this non-trivial is recorded here so G2b's brainstorm starts from it:
`wing_parser/classifier/llm.py` hard-codes Anthropic at three levels, and only
two are renames. `MODEL` (`llm.py:22`) and `import anthropic` (`llm.py:66` and `:74`) are
trivial. `client.messages.parse(..., output_format=SourceGuess)`
(`llm.py:82-102`) is a **provider-specific structured-output call** that OpenAI
and Gemini each spell differently. That is the actual content of the question.
