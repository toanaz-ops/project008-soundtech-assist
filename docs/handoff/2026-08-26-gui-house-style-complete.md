# GUI parity wave 1 + house style wave 1b complete

**Date:** 2026-08-26 · **Branch:** `feature/gui-parity-wave1` @ `04db887`,
**not merged** — awaiting ToanAZ's merge call ·
**Suite:** 1433 passed / 3 skipped (measured on that commit) ·
**Specs:** `docs/superpowers/specs/2026-08-25-gui-parity-design.md` ·
**Plans:** `docs/superpowers/plans/2026-08-25-gui-parity-wave1.md` +
`2026-08-26-gui-house-style-wave1b.md` · **Defect ledger:** `docs/tech-debt.md`

## What shipped

Six-page wing-ui: **Doctor / Overview / Channels / Routing / Diff / Import**
(G2a+G2b wizard with model assist). Dark **Sodium Rack** house style ported
from PROJECT005-AZ-handsfree: 19 int tokens → `string.Template` QSS, hex-scan
test with an empty allowlist, vendored OFL faces (weight chosen via
`QFontInfo`, never by family name), middle elision keeping the tail, every
number in mono. Model calls run on cancellable workers with numeric timeouts
(proposal 120 s / guesses 180 s / probe 30 s) and visible Cancel chrome.
Keyboard map Ctrl+O / Ctrl+Shift+S / Ctrl+Z / F5 / Esc / Ctrl+1…6; geometry,
last page and recent scenes persist under the knowledge dir. Settings dialog:
each user pastes their OWN provider key; Test connection is real.

## What ToanAZ can try right now

| Try | Command | Expect |
|---|---|---|
| The app | `dist\wing-ui.exe` (double-click works too) | Dark themed window, sidebar six pages |
| Open a scene | Ctrl+O → `user-files\example-Vu.snap` | Doctor fills, first finding preselected |
| Browse facts | click Overview / Channels / Routing | counts as legends + mono numerals, no inputs |
| Diff two scenes | Diff page → "Compare with..." a second .snap | magnitude-first rows, optional 2px bar |
| Import Excel | Import page → pick `tests\data\BIDV TPHCM - KỊCH BẢN SK YEP 2025..xlsx` | mapping proposal verified by checker; step rail lights up |
| AI assist | Tools ▸ Settings → paste own key → Test connection | real provider answer or honest failure; Cancel + timeout everywhere |
| Screenshots of any build | `dist\wing-ui.exe --screenshot <dir> <scene.snap>` | 7 PNGs at exactly 1280×760 |

## Decisions pending a human

- **Merge** `feature/gui-parity-wave1` into `main` — everything else is done.
- A/B review artifacts: `diff.png` vs `diff-b.png` (magnitude bar on/off) —
  flip `SHOW_MAGNITUDE_BAR` in `wing_parser/ui/diff_page.py` to change ships.

## Known pitfalls

- **Onefile layout:** the exe is `dist\wing-ui.exe`, not
  `dist\wing-ui\wing-ui.exe`. A stale Aug-25 `wing-ui-debug.exe` shipped
  without `wing_parser` (pre-pathex-fix) and produced
  `ModuleNotFoundError: No module named 'wing_parser.ui.__main__'` on 26/08 —
  delete stale exes after rebuilding; regenerate debug spec via
  `.venv\Scripts\python.exe packaging\make-debug-spec.py` after ANY spec
  change, then rebuild it separately.
- **Never add `-q`:** pyproject already sets it; `-qq` swallows the pytest
  summary line. Run bare `.venv\Scripts\python.exe -m pytest`.
- **Two tab-order skips are honest:** overview/channels hold exactly one
  focusable widget today; adding a second auto-unskips.
- **provider.yaml at repo root is real and gitignored:** tests chdir-isolate
  themselves from it (micro-task 0 + settings isolation); keep it that way.

## Still open (see `docs/tech-debt.md`)

D-24 scanner test (narrowed), D-29 import_page.py at 246 lines,
D-30 placeholder-key detection, D-31 `settings.cancel` texts key,
deliberate D-2/D-17, live DeepSeek smoke inside the app (needs his key).
