# GUI waves 1+1b complete — desktop parity + Sodium Rack house style

**Date:** 2026-08-26 · **Branch:** `feature/gui-parity-wave1` (not yet merged to
`main`) · **Final:** 1433 passed, 3 skipped, measured on `04db887` ·
Spec `docs/superpowers/specs/2026-08-25-gui-parity-design.md` ·
Plans `docs/superpowers/plans/2026-08-25-gui-parity-wave1.md` +
`docs/superpowers/plans/2026-08-26-gui-house-style-wave1b.md`

## What landed

| Piece | Where |
|---|---|
| Six-page shell (Doctor, Overview, Channels, Routing, Diff, Import wizard) | `wing_parser/ui/` (pages split per ≤200-line cap; shell in `main_window.py` + `menus.py`) |
| Token table → generated QSS, zero colour literals outside `theme/` | `wing_parser/ui/theme/` (`tokens.py`, `qss.py`, `resources/theme.qss` + `chrome.qss`) |
| Vendored OFL faces (Saira Condensed, IBM Plex Sans/Mono), tracked caption faces | `wing_parser/ui/resources/fonts/`, `theme/fonts.py` |
| Style-drawn focus ring + full-row selection (`QProxyStyle`) | `theme/proxy_style.py` |
| Keyboard map Ctrl+O/Ctrl+Shift+S/Ctrl+Z/F5/Ctrl+1…6/Esc + explicit tab chain | `menus.py`, `focus_chain.py`, pinned by `tests/test_ui_keyboard.py` |
| Cancellable model-call workers with timeouts (D-25 law) | `import_controller.py`, `session.py` (Task C) |
| Remembered geometry, last page, recent scenes | `session.py`, `main_window.py` |
| Diff magnitude bar (2 px, behind `SHOW_MAGNITUDE_BAR`) with A/B captures | `diff_page.py`, `findings_view.py` |
| Import wizard step rail + honest empty states | `import_page.py`, `pick_step.py`, `terms_step.py`, `save_step.py` |
| Packaging: resources in DATAS, debug spec generated, exe screenshot gate | `packaging/wing-ui.spec`, `packaging/make-debug-spec.py` (task 1b-22) |

## Measured acceptance

1. Bare suite on `04db887`: **1433 passed / 3 skipped**
   (`.venv\Scripts\python.exe -m pytest`, 2026-08-26).
2. Every page renders in the house palette — `test_every_page_renders_in_the_house_palette`
   samples every pixel of each grab and requires house tokens.
3. **Exe gate passed**: `dist\wing-ui.exe` rebuilt with resources in DATAS;
   all six pages screenshot-verified FROM the exe (task 1b-22).
4. Every surface commit ended with PNGs the author viewed; per-surface
   verdicts live in `.superpowers/sdd/2026-08-25-gui-parity-wave1/task-1b18-report.md`
   et al.

## What a human can try

```bash
.venv\Scripts\python.exe -m wing_parser.ui --screenshot screenshots user-files\example-Vu.snap
```

Open `screenshots\doctor.png`: dark Sodium Rack shell, tracked uppercase
sidebar with the orange edge on the live page. Or run `dist\wing-ui.exe`
(copied to local disk first) and Tab through Doctor — the focus ring is
the style's, not the OS dotted rect.

## What is left open

1. **Merge to `main`** — the branch is ahead of `origin` and unmerged; that
   call is ToanAZ's.
2. **Live provider smoke from the exe** — Settings → Test connection with a
   real key, on a machine with the frozen build.
3. Deferred minors in `docs/tech-debt.md` (D-1…D-14, D-17) and the SDD
   ledger's deferred notes; import_page.py is at the 220-line cap and wants
   a split before it grows again.
4. `screenshots/`, `shots-test/`, `memory/` and `packaging/wing-ui-debug.spec`
   are untracked working artifacts — regenerated, not shipped.
