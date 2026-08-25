# Sub-project G2b complete — assisted ingest, the model half

**Date:** 2026-08-24 · **Branch:** `feature/g2b-assisted-ingest`, merged into local
`main` · **Final:** 1271 passed, 21 skipped (environmental: PySide6/mcp not
installed) · Spec `docs/superpowers/specs/2026-08-24-g2b-assisted-ingest-model-design.md`
· Plan `docs/superpowers/plans/2026-08-24-g2b-assisted-ingest-model.md`

## What landed

| Piece | Where |
|---|---|
| Provider protocol + flat-schema validator + config/factory | `classifier/provider.py` |
| OpenAI-compatible adapter (DeepSeek via base_url) | `classifier/provider_openai.py`, extra `[llm-openai]` |
| Anthropic adapter; llm.py routed through the layer | `classifier/provider_anthropic.py`, `classifier/llm.py` |
| Structured fields sound/lighting/led, emit+load round-trip | `showcontext/models.py`, `ingest/{mapping,build,emit}.py`, `showcontext/loader.py` |
| Workbook sampler | `ingest/sample.py` |
| Proposal checker + proposer (model proposes, workbook verifies) | `ingest/suggest.py` |
| Interactive wizard + `--one-shot` fast lane | `ingest/wizard.py`, `cli/__main__.py`, `cli/commands.py` |
| Term guessing, recorded only on explicit yes | `ingest/guess.py` (+ `cache.remember`, origin `g2b-assisted`) |

## Measured acceptance (spec §11)

1. BIDV real sheet: proposal `header_row: 5`, `title: E` accepted by checker —
   pinned by `tests/test_g2b_acceptance.py` against the committed real `.xlsx`.
2. vivo real sheet: `Rundown` chosen over junk pivot `LIST`; blank column A
   survives — pinned likewise.
3. Vocabulary writes only after explicit `y`; suite leaves
   `knowledge/toanaz/classifier.yaml` untouched (verified every run).
4. Whole suite green with extras uninstalled.

Whole-branch review ran (found 4 Important: EOF traceback, kill-switch not
gating new paths, `--map` flow dropping folded columns, unverified proposals
unmarked) — all fixed in the wave `65ee8e2..db6c7c0` and re-reviewed ADDRESSED.

## What is left open

1. **Live DeepSeek smoke** — needs ToanAZ's `DEEPSEEK_API_KEY` and a
   `provider.yaml` (`provider: openai-compat`, `base_url:
   https://api.deepseek.com`, model of his account). One command after merge;
   record actual output either way.
2. **Cuesheet vocabulary still ships empty** (ROADMAP §5 item 2) — J2 now
   offers terms during import, but seeding ~20 common ones is still his call.
3. Parked minors in the SDD ledger
   (`.superpowers/sdd/2026-08-24-g2b-assisted-ingest-model/progress.md`),
   notably: apostrophe-containing performer fragments miss the unresolved-term
   regex; wizard error stream split stdout/stderr; llm.py prompt sentence
   duplicated.

## Pitfalls for the next session

- The worktree had no own `.venv`; tests must run from the worktree root using
  the main checkout's interpreter (`pythonpath=["."]` resolves the worktree
  package). After merge this matters less, but the pattern recurs next cycle.
- `provider.yaml` named-but-missing raises by design (controller ruling);
  unset falls through to defaults silently — do not "fix" the asymmetry.
- Real client files are committed in `tests/data/` at ToanAZ's direction
  (outdated material); do not treat them as sensitive later.
