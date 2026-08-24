# Sub-project G2b — assisted ingest (the model half)

**Date:** 2026-08-24 · **Status:** design authority for the provider layer and
the assisted half of `wing_parser/showcontext/ingest/`

Every claim this spec makes about existing code was made by opening the named
file on 2026-08-24 (`main` @ `1c9aaae`) and carries its `file:line`. Every claim
about ToanAZ's preferences was answered by him in this session and is marked as
such. Where something is **not** established, §12 says so rather than letting
silence read as agreement.

This spec follows `2026-08-22-assisted-ingest-design.md` (G2a), which built the
deterministic half: a declared mapping turns a spreadsheet into a show-context
file, entirely offline. G2b removes the typing in the two places where judgement
is genuinely required. It modifies G2a's field set in exactly one documented way
(§7).

## 1. Purpose

G2a made a cue sheet obtainable without the network, but every new client still
costs ToanAZ one hand-written mapping file, and every Vietnamese performer term
outside the vocabulary becomes an unclassified comment. Both are judgement
tasks; both are small, reviewable artefacts — not 200 rows through a model.

G2b adds exactly two model jobs, and nothing else:

| | job | output ToanAZ reviews |
|---|---|---|
| J1 | propose a column mapping from a header sample | a `map.yaml`, checked before use |
| J2 | guess a term the `cuesheet:` vocabulary lacks | one vocabulary entry, recorded only on his yes |

## 2. What the real inputs are — measured 2026-08-24

ToanAZ dropped five real files into `tests/data/` (committed this cycle at his
direction — they are outdated client material, nothing sensitive). Two are
`.xlsx` running orders, which is what G2a/G2b read. Header samples were read
with openpyxl on 2026-08-24:

| | fixture (`ingest-fixture.xlsx`) | vivo `05102022` Event Rundown | BIDV TPHCM YEP 2025 |
|---|---|---|---|
| header row | 4 | **4** | **5** |
| first populated column | A | **B** (A blank) | A |
| time columns | one `time` | Start + End + Duration | start + duration + end |
| title column | C (`Tên tiết mục`) | F (`Description`) | E (`Nội dung`) |
| people columns | `performers` | On stage + PIC | Thực hiện + BIDV + Bình Yên |
| technical columns | `note` (one) | Sound, Lighting, LED screen, CHUẨN BỊ | Led, Âm thanh |
| junk sheet first | no | **yes** (`LIST` is a pivot table) | no |

Three consequences shape everything below:

1. **The closed field set cannot express a real sheet.**
   `wing_parser/showcontext/ingest/mapping.py:18` defines
   `FIELDS = ("id", "title", "time", "performers", "note")`. The vivo sheet has
   four distinct technical columns; under today's schema they all collapse into
   one `note`, or the mapping refuses. G2b extends the field set (§7).
2. **Sheet selection is real work.** A workbook's first sheet can be unrelated
   pivot output. The proposer must name its sheet choice and say why.
3. **The header sample must carry column letters**, because the header row is
   not row 1 and the first populated column is not always A.

## 3. The provider layer — closing the multi-provider question

ToanAZ asked on 2026-08-21 that the design admit providers other than
Anthropic, decided on 2026-08-22 to defer it out of G2a, and answered in this
session (2026-08-24): his preferred working model is **DeepSeek over its
OpenAI-compatible API**.

What exists today: `wing_parser/classifier/llm.py` hard-codes Anthropic at
three levels. `MODEL = "claude-opus-5"` (:22) and the two `import anthropic`
statements (:66 inside `available()`, :74 inside `_ask()`) are mechanical.
`client.messages.parse(..., output_format=SourceGuess)` (:82–103) is the
provider-specific structured-output call — DeepSeek's chat-completions API
spells structured output differently: `response_format={"type":
"json_object"}`, which requires the prompt itself to carry the word "json" and
an example, and does **not** enforce a schema. Validation therefore moves into
our code (§4).

G2b introduces one protocol and two adapters:

```
wing_parser/classifier/provider.py      Protocol: complete_json(system, user,
                                        schema: dict) -> dict
                                          - validates the reply against the
                                            schema (pure-python check)
                                          - retries once on invalid JSON or
                                            schema mismatch, then raises a
                                            typed error the caller degrades on
  ├─ AnthropicProvider   wraps what llm.py:82–103 does today
  └─ OpenAICompatProvider  OpenAI SDK against a configurable base_url;
                           covers DeepSeek (base_url=api.deepseek.com),
                           OpenAI, and any compatible endpoint
```

Selection is a YAML config block (`provider:`, `model:`, `api_key_env:`,
optional `base_url:`). `llm.py` keeps its public `classify()` signature and its
contract — every failure path returns `None` (:8–13); the provider error lands
on that same path. `anthropic` stays an optional extra; `openai` joins it as a
second optional extra, and no test imports either.

## 4. J1 — proposing the column mapping

Input to the model: each candidate sheet's name plus a **~20-row structural
sample** — header candidates and cell values truncated, with Excel-style column
letters attached. It is ToanAZ's own data processed locally; nothing leaves the
machine except that prompt.

The model returns proposed `{sheet, header_row, columns{id,time,title},
headers{performers,note,...}}` as JSON against a fixed schema. Before anything
is shown to a human, a **pure-python validator** checks the proposal against
the workbook itself:

- the named sheet exists;
- the claimed header row actually carries text in the claimed columns;
- no mapped column is entirely empty below the header row;
- `title` is mapped (mapping.py:19 makes it `REQUIRED`).

Invalid → one retry with the validator's complaints appended → if still
invalid, the proposal is shown marked unverified for hand-editing. **The tool
never applies an unchecked proposal**: import still consumes a mapping *file*,
exactly as G2a did.

## 5. Interaction — interactive first, one-shot when rushed

Answered by ToanAZ 2026-08-24: interactive by default, with a fast lane.

```
wing showcontext import <file.xlsx>             # interactive
wing showcontext import <file.xlsx> --one-shot  # write proposed map.yaml, stop
```

Interactive flow, one group of decisions per screen, each answerable with
Enter-to-accept: sheet → header row → core columns (`id/time/title`) → people
and technical columns → save. The final artifact is the same per-client
`map.yaml` G2a already reads; nothing about the downstream pipeline changes.

No key, no `openai`/`anthropic` extra installed, `WING_DISABLE_LLM` set, or
provider unreachable → print one line saying so and fall back to the manual G2a
flow (write the map by hand). Same degrade-not-raise contract as
`llm.py:8–13`.

## 6. J2 — guessing a missing vocabulary term

When a performer term fails resolution during import (the path that today
writes an unclassified comment), G2b offers one model call: given the term and
its surrounding row, propose `[term ≈ dotted kind]`. The proposal is shown;
**only an explicit yes from ToanAZ appends it** to the cuesheet vocabulary,
stamped `source: g2b-assisted <date>`. This reuses the pattern
`classifier/llm.py` + `classifier/cache.py` already establish: asked once per
term, remembered permanently after confirmation.

## 7. Structured technical fields — the one change to G2a's contract

Answered by ToanAZ 2026-08-24 ("B và A"): technical columns become **structured
fields where the kind is known, prefixed notes where it is not**.

- `FIELDS` (mapping.py:18) grows to include `sound`, `lighting`, `led`.
- `Segment` (`showcontext/models.py:24–29`) grows three optional str fields:
  `sound=""`, `lighting=""`, `led=""`.
- `build.py` fills them verbatim from their columns; any **other** unmapped-
  to-field column folds into the existing comment stream
  (build.py:139–166) as `[<header text>] <cell text>` — nothing dropped
  silently, per the standing constraint.
- `emit.py` writes the new fields only when non-empty, keeping existing
  show-context files byte-stable when the feature is unused.

Q-rules are untouched: none of Q1–Q7 reads these fields; they ride along as
information the show-context file now preserves.

## 8. Testing

Standing constraints hold: deterministic code tested offline, no test opens a
socket, `mcp`/`anthropic`/`openai` stay uninstalled in CI.

- Validator, sample extraction, field-folding, and config loading: pure python,
  ordinary unit tests.
- Provider protocol: tested through fakes injected as callables (the pattern
  G2a set with the vocabulary lookup).
- Adapters: construction and request-shaping only, behind the optional-extra
  import guard; no live call anywhere in the suite.
- Real sheets: the two `.xlsx` files in `tests/data/` become acceptance inputs
  for J1's validator (structure assertions, not model calls).

## 9. Out of scope

PDF, DOCX and photographed cue sheets (three of the five real files dropped are
exactly that) — each gets its own reader later, behind the same interface G2a
§8 drew. No new advisory rule reads `sound/lighting/led` yet. No streaming, no
conversation memory, no retry beyond one.

## 10. Cycle process

Per ROADMAP §7: brainstorm (done — this spec closes it) → writing-plans →
subagent-driven development with per-task review → whole-branch review on the
strongest model. The two carried-forward lessons apply: reviewers may run the
code, and a claim about another module must be checked by opening that module.

## 11. Success criteria

1. `wing showcontext import tests/data/BIDV*.xlsx --one-shot` produces a
   mapping whose header_row/columns match what a human reads off the sheet,
   with zero network calls in the deterministic path when disabled.
2. An interactive run against the vivo workbook proposes `Rundown` (not
   `LIST`) and survives its blank column A.
3. A term like "Nhạc đón khách" ends in the vocabulary only after ToanAZ
   answers yes, and never appears there from a test run.
4. Existing suite stays green with the extras uninstalled.

## 12. Not established

- **Exact DeepSeek model id** for the config default (`deepseek-chat` vs a
  v4 variant): ToanAZ's key and account determine this; the config accepts any
  string, so nothing blocks.
- **Which of Thực hiện/BIDV/Bình Yên maps to `performers`** on the BIDV sheet
  is a judgement the proposer will make per-sheet; the interactive screen lets
  him correct it. Not pre-decided here.
- **Whether `CHUẨN BỊ` deserves a fourth structured field** rather than the
  note fold: deferred until he has imported one real sheet with §7 live.
