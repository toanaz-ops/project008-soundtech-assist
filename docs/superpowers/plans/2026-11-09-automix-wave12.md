# Plan — GUI 12 Automix

Spec: `docs/superpowers/specs/2026-11-09-automix-wave12-design.md`. Decisions: `docs/decisions/2026-11-09-automix-decisions.md`.
Branch `claude_desk/automix-06baab` (worktree `wave6-c77839`). Research inputs (cited YAML) in the shared
notes folder `automix-research-*.yaml` / `automix-codebase-map.md`.

## Phase 1 (PR A)

| Task | Owner | Files | Done when |
|---|---|---|---|
| T1 Knowledge data | agent (opus) | `wing_parser/automix/data/*.yaml`, `docs/knowledge-base/05-mixing-targets/*.md`, `knowledge/toanaz/automix.yaml` (empty header) | every value has `src` or `eng_default`; notes cite URLs |
| T2 Engine | same agent | `wing_parser/automix/*.py` (≤200 lines each) | `propose` / `to_patches` per spec §4–6 |
| T3 Engine tests | same agent | `tests/test_automix_golden.py`, `_invariants.py`, `_knowledge.py`, `tests/data/automix_golden/` | narrow run green |
| T4 Packaging | same agent | `pyproject.toml` package-data, `packaging/wing-ui.spec` datas | data importable from installed package |
| T5 UI | agent (opus), after T2 | `ui/settings_automix.py`, `ui/automix_dialog.py`, `ui/automix_tables.py`, `ui/texts_automix(_vi).py`, `ui/menus.py`, `ui/texts.py`, `ui/texts_vi_all.py`, `tests/test_ui_bilingual.py`, `tests/test_ui_automix.py` | smoke test green; texts/house-style tests green |
| T6 Review | Fable agent | read-only | findings fixed |
| T7 Ship | me | PR, CI `test`, merge, exe rebuild, ROADMAP row GUI 12, MEMORY entry | CI green, exe alive |

## Phase 2 (PR B)

| Task | Files |
|---|---|
| P2-1 live loop (pure) | `wing_parser/automix/live_loop.py`, `tests/test_automix_live_loop.py` |
| P2-2 meter reader (experimental) | `wing_parser/net/meters.py`, `tests/test_net_meters.py` |
| P2-3 UI full auto | `ui/automix_live.py` (arm, start/stop, locked-leaf list), Settings option, wiring via `ui/live_write.send` |
| P2-4 Fable review, ship, exe, handoff, Decision Box card | |

Test budget (owner): per phase run only the new test files + the bilingual/house-style/read-only tests
they can break; full suite only on CI.
