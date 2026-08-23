# Next steps — after the 2026-08-23 branch consolidation

**Context:** all orphan branches were merged into `main` (sub-project H, the
desktop app, was the only one carrying unmerged code) and deleted.
`main @ d298b78`, 1225 tests passing, 1 skipped. This file sequences what comes
next; `docs/ROADMAP.md` remains the source of truth for *what exists*.

---

## Step 0 — two cheap blockers only ToanAZ can clear (before G2b)

G2a was built entirely against an invented fixture. Both of these are judgement
calls about his own material (ROADMAP §5.1–5.2):

1. **Drop ONE real running-order `.xlsx` into `tests/data/`.** One hour, and it
   may change what G2b's column-mapping proposer should even look like.
2. **Seed ~20 Vietnamese performer terms into the `cuesheet:` vocabulary.**
   It ships empty; only loanwords (`guitar`, `bass`, `piano`) resolve today.

## Step 1 — G2b: the assisted half of ingest

Full cycle per ROADMAP §7: brainstorm → spec → plan → implement → whole-branch
review. Design constraints already recorded:

- **Multi-provider is the real question** (ToanAZ asked 2026-08-21). The
  concrete work: `wing_parser/classifier/llm.py` hard-codes Anthropic at three
  levels — `MODEL` (:22), `import anthropic` (:66, :74) are renames; the
  `client.messages.parse(...)` structured-output call (:82-102) is
  provider-specific. Keep G2a's pattern: judgement enters as an injected
  callable, so the deterministic core stays model-free.
- Two jobs only: propose a column mapping from a ~20-line header sample;
  guess terms the vocabulary lacks and offer to record the answer permanently.

## Step 2 — close the live-watch acceptance tests (needs the console back)

The desk went out on a show 2026-08-22 (ROADMAP §6). When it returns, one
sitting closes both:

1. Does polling *detect* a change? Run watch, move one fader from WING-Edit,
   record actual output either way.
2. Does it *coexist* with WING-Edit? Never run; this is the hard requirement.

```powershell
python -m wing_parser.cli net watch 192.168.128.28 --until 120
```

A negative result gets written up, not retried into silence.

## Do not start

- **E (audio analysis)** — blocked on a UDP metering transport that does not
  exist; that transport needs its own spec first.
- **F (decision tier / auto-mix)** — depends on everything including unbuilt G.

## Standing rules carried forward

- Whole-branch review every cycle — it has caught a cross-file defect four
  cycles running that no single task's diff contained.
- Reviewers may run the code; a claim about another module must be checked by
  opening that module (ten false-description defects landed in G2a alone).
