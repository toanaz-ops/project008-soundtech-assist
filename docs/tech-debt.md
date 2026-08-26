# Tech debt ledger

The single source of truth for known defects and deliberate omissions in this
repo. Other documents **link** here (`docs/tech-debt.md#d-7`); they never restate
a fact from this file. Four documents saying the same thing look like four pieces
of evidence when they are one unverified claim.

Numbering is monotonic. A number is never reused. Closing an item requires the
close command's **output**, not the intention to run it.

**Provenance.** D1–D18 were rescued on 2026-08-26 from
`.superpowers/sdd/2026-08-25-gui-parity-wave1/progress.md`, which `.gitignore`
excludes — one `git clean -xfd` or `git worktree remove` and they were gone.
Wording is the ledger's own; the `line` field points at the rescued source line.
Claims marked *(inherited)* were recorded by the implementing agent and have
**not** been independently re-verified — treat them as leads, not findings.

D19–D28 were found on 2026-08-26 during the GUI spec review and **were** verified
by the command shown.

---

## Rescued from the wave-1 SDD ledger

- **D-1** `channel_detail_rows` duplicates `render.channel_detail` by design
  - owner: machine-doable
  - evidence: ledger line 30, Task 1 (commits `6d99ede..b441397`). The duplication
    is intended — what is missing is the comment saying so, so the next reader
    does not "fix" it. *(inherited)*
  - close: add the cross-reference comment to both sites; `grep -n "channel_detail" wing_parser/ui/data.py wing_parser/cli/render.py`
  - status: open

- **D-2** Task 1 tests are shallow, per plan scope
  - owner: deliberate-no — the plan scoped them that way; recorded so the
    shallowness is not mistaken for coverage
  - evidence: ledger line 31, Task 1. *(inherited)*
  - close: n/a unless someone decides to deepen them
  - status: open (deliberate)

- **D-3** `test_diffcore` lexicographic-vs-natural assertion is trivially true
  - owner: machine-doable
  - evidence: ledger line 33, Task 2+3 (`1f03170..adceb2f`). The assertion passes
    with a single mutation, so it does not actually pin the ordering. *(inherited)*
  - close: add a second row that orders differently under the two schemes; run
    `.venv/Scripts/python.exe -m pytest tests/test_diffcore.py -q`
  - status: open

- **D-4** Function-level imports in the briefed tests
  - owner: machine-doable
  - evidence: ledger line 34, Task 2+3. *(inherited)*
  - close: hoist to module level; `.venv/Scripts/python.exe -m pytest -q`
  - status: open

- **D-5** `theme.qss` `var()` is dead until literal substitution
  - owner: machine-doable
  - evidence: ledger line 36, Task 4 (`b6ba324`). Superseded in scope by **D-20**,
    which establishes that Qt's QSS engine has no custom-property support at all,
    so this was never going to work rather than merely being unfinished.
  - close: closed together with D-20
  - status: open

- **D-6** `MainWindow.switch_to` has no unknown-key guard
  - owner: machine-doable
  - evidence: ledger line 39, Task 5 (`b6ba324..545045e`). A typo'd page key fails
    silently or raises from deep inside Qt rather than at the seam. *(inherited)*
  - close: raise `KeyError` naming the valid keys; add a test asserting it
  - status: open

- **D-7** `DoctorPage.show_finding` emits `selected` on programmatic clears
  - owner: machine-doable
  - evidence: ledger line 40, Task 5. Recorded with "revisit when pages land" —
    the pages have now landed. *(inherited)*
  - close: guard the emit, or rename the signal to say what it means
  - status: open

- **D-8** Channels detail pane goes stale on session swap
  - owner: machine-doable
  - evidence: ledger line 42, Task 7 (`545045e..6854625`). Opening a second scene
    leaves the previously selected channel's detail on screen until restart.
    Ledger calls it "a one-line reset candidate". *(inherited)*
  - close: reset in `set_session`; test that a swap clears the pane
  - status: open

- **D-9** Import-order nit: `QtCore` after `QtWidgets`
  - owner: machine-doable
  - evidence: ledger line 43, Tasks 6-8. *(inherited)*
  - close: reorder; `.venv/Scripts/python.exe -m pytest -q`
  - status: open

- **D-10** Diff sort test is trivially true with one magnitude row
  - owner: machine-doable
  - evidence: ledger line 45, Task 9 (`6854625..9adcce2`). *(inherited)*
  - close: add rows that only sort correctly under descending magnitude
  - status: open

- **D-11** A failed compare keeps the last good rows beside the error label
  - owner: needs-human — this is a UX ruling, not a bug
  - evidence: ledger line 46, Task 9, recorded as "deliberate UX decision to note
    in final review". It has never been written into a spec, so it currently
    exists only as behaviour nobody agreed to.
  - close: own it or reverse it in the wave-1 spec's per-page acceptance for the
    Diff page, then link that section here
  - status: open — **needs ToanAZ**

- **D-12** Lazy `sample_workbook` import inconsistency
  - owner: machine-doable
  - evidence: ledger line 48, Task 10 (`9adcce2..61c120a`). *(inherited)*
  - close: make the import style consistent with the rest of `import_controller.py`
  - status: open

- **D-13** Save As filter offers `.xlsx` for a YAML output
  - owner: machine-doable
  - evidence: ledger line 51, Task 11 (`61c120a..d7cffeb`). The import wizard
    writes a show-context `.yaml`; the dialog filter says xlsx. *(inherited)*
  - close: correct the filter; assert the filter string in the page test
  - status: open

- **D-14** `import.error` shows raw exception text with no lead-in
  - owner: machine-doable
  - evidence: ledger line 52, Task 11. The operator sees a Python exception
    rendered as a sentence. *(inherited)*
  - close: covered by the error taxonomy in the rewritten wave-1 spec; the string
    must read as a sentence and name a next action
  - status: open

- **D-15** Import tests reach page privates `_result` / `_directory`
  - owner: machine-doable
  - evidence: ledger line 53, Task 11. Tests coupled to private attributes break
    on any refactor — and a restyle is a refactor. *(inherited)*
  - close: route through the existing public seams (`pick_file`, `show_terms_step`,
    `save_as`); `.venv/Scripts/python.exe -m pytest tests/test_ui_import_page.py -q`
  - status: open — **raise the priority before any theme work touches these pages**

- **D-16** `theme.py` docstring lines 4-5 state something untrue
  - owner: machine-doable
  - evidence: ledger line 37, routed from Task 4 to Task 14: *"Task 14 MUST also
    fix theme.py docstring lines 4-5 (claims spec maps ui/resources; it does not
    yet)"*. Task 14 never ran. Confirmed still true — see **D-26**, which is the
    packaging half of the same problem.
  - close: fix the docstring in the same commit that adds the DATAS entry (D-26)
  - status: closed 2026-08-26 — `theme/paths.py` docstring now states the mapping;
    fixed in the same commit as **D-26** (task 1b-22)

- **D-17** A raising `provider_factory` propagates by design
  - owner: deliberate-no
  - evidence: ledger line 49, routed from Task 10 to Task 11: the caller handles
    it. Recorded so nobody adds a second swallow layer.
  - close: n/a
  - status: open (deliberate)

- **D-18** Task 13's PNG assertion `size > 1000 bytes` may be flaky
  - owner: machine-doable
  - evidence: ledger line 19, accepted as a pre-flight risk for wave 1 with
    "reviewer may flag, adjudicate then". Independently confirmed during the
    2026-08-26 review: a flat 600×400 PNG measures ~1664 bytes, so a page that
    renders nothing at all can pass this assertion.
  - close: assert the pixels instead of the byte count — sample the image and
    require at least two house-palette colours present
  - status: open — **the assertion as written cannot detect an unstyled app**

---

## Found in the 2026-08-26 GUI spec review

- **D-19** `theme.apply()` is never called; the app runs completely unstyled
  - owner: machine-doable
  - evidence: `grep -rn "theme" wing_parser/ tests/` returns only `theme.py`
    itself and `tests/test_ui_theme.py`. `wing_parser/ui/__main__.py` builds
    `QApplication` and then `MainWindow` without importing `theme`.
  - close: call `theme.apply(application)` **before** `MainWindow` is constructed
    (qtawesome resolves an icon's colour from the application palette at
    icon-construction time, and `MainWindow.__init__` builds six sidebar icons)
  - status: open

- **D-20** `theme.qss` is built on `var(--…)`, which Qt's QSS engine ignores
  - owner: machine-doable
  - evidence: `wing_parser/ui/resources/theme.qss:6-11` declares
    `--background/--foreground/--accent` and line 11 reads
    `background: var(--background)`. Qt stylesheets have no CSS custom
    properties; the whole rule is discarded with no diagnostic.
  - close: generate the stylesheet from a token table by substitution; assert
    `"$" not in load_stylesheet()` and `"var(--" not in load_stylesheet()`
  - status: open — supersedes **D-5**

- **D-21** `PySide6-Fluent-Widgets` is a declared dependency that nothing imports
  - owner: needs-human — removing a dependency is the owner's call
  - evidence: declared in `pyproject.toml` under the `ui` extra; a repo-wide
    `grep -rni "qfluent" --include=*.py .` matches only `.venv/`. Every install
    downloads a library the app never touches.
  - close: remove it from the `ui` extra, or state in the spec which wave intends
    to use it
  - status: open — **needs ToanAZ**

- **D-22** The cited look-and-feel authority does not exist
  - owner: machine-doable
  - evidence: the skill `pyside6-ui-quality` is cited 9 times across the wave-1
    spec, its plan and `AGENTS.md` as the source of the visual rules, the
    screenshot loop and the packaging discipline.
    `find /c/Users/id_az/.claude -iname "*ui-quality*"` returns nothing, and the
    repo's own `skills/` holds only `wing-*` skills. Every visual requirement in
    the wave is therefore delegated to a document nobody can open.
  - close: repoint every citation at the house-style spec; `grep -rn "pyside6-ui-quality" docs/ AGENTS.md` must be empty
  - status: open

- **D-23** No accessibility affordances at all
  - owner: machine-doable
  - evidence:
    `grep -rn "setShortcut\|QKeySequence\|setAccessibleName\|setTabOrder" wing_parser/ui/`
    returns zero matches. One `setToolTip` exists, in the pre-existing
    `detail_panel.py`. There is no Ctrl+O and no Ctrl+S; the menus carry Alt
    mnemonics only.
  - close: the keyboard map, tab order and visible focus ring ruled by ToanAZ on
    2026-08-26; assert each accelerator in a shell test
  - status: open

- **D-24** `main_window.py` bypasses `texts.py`, breaking the spec's own i18n rule
  - owner: machine-doable
  - evidence: hardcoded English user-facing strings — `"Cannot open that file"`,
    `"Cannot save"`, `"Saved"`, `"Knowledge directory"` — plus the menu titles
    `&File` / `&Edit` / `&Tools` / `&Help`. The wave-1 spec requires that all new
    user-facing strings go through `wing_parser/ui/texts.py`.
  - close: move them into `texts.py`; add a test that scans `wing_parser/ui/` for
    quoted strings passed to `setText`/`setWindowTitle`/`QMessageBox`
  - status: open

- **D-25** Provider calls block the GUI thread with no cancel and no timeout
  - owner: machine-doable — ToanAZ ruled on 2026-08-26 that a worker, a Cancel
    button and a numeric timeout are required
  - evidence: `import_page.py` and `terms_step.py` contain the package's entire
    concurrency story: `QApplication.setOverrideCursor(WaitCursor)`. No `QThread`,
    no `QTimer`, no timeout, no cancel. The mapping proposal and term guessing are
    remote API round trips, so the window can stop repainting for tens of seconds
    — indistinguishable from a crash.
    The measurement that licensed synchronous work does not extend to them: the
    2026-08-18 spec measured a **full re-analysis at ~100 ms** (90/103/99 ms over
    three runs), two to three orders of magnitude away from a network call.
  - close: worker + Cancel + timeout; a test that the UI stays responsive while a
    stubbed slow provider runs
  - status: open

- **D-26** `wing_parser/ui/resources` is not in the PyInstaller DATAS
  - owner: machine-doable
  - evidence: `packaging/wing-ui.spec` lists advisory, classifier, descriptors,
    edit and knowledge data, but not `wing_parser/ui/resources`. `load_stylesheet()`
    would raise `FileNotFoundError` in a frozen build. It is masked today only
    because **D-19** means nothing calls it.
  - close: add the entry (it covers the qss, the fonts and their OFL licences in
    one, because `resource_path()` maps that directory to the same relative
    position in dev and under `sys._MEIPASS`); rebuild and launch the exe
  - status: closed 2026-08-26 — DATAS entry added (task 1b-22); exe rebuilt and
    all six pages screenshot-verified FROM `dist\wing-ui.exe` (dark theme,
    vendored mixed-case fonts). Same commit as **D-16**.

- **D-27** `anthropic` is excluded from the bundle but offered in the Settings dialog
  - owner: needs-human
  - evidence: `packaging/wing-ui.spec` lists `anthropic` in `EXCLUDES` on the
    stated grounds that the desktop app adds no network surface of its own — a
    comment that became false when the Settings dialog shipped. The dialog's
    provider combo offers `anthropic`, and "Test connection" builds a real
    provider from it. In the frozen exe that path ends at
    `ModuleNotFoundError: No module named 'anthropic'`, which the probe swallows
    into a message, so it reads as a connection failure rather than a missing
    dependency.
  - close: pick one — drop the exclusion, or hide `anthropic` when
    `sys.frozen`. Either way translate the ImportError so it names its cause, and
    rewrite the now-false justification comment in the spec file.
  - status: closed 2026-08-26 — ruled by ToanAZ (delegated): dropped the
    `anthropic` exclusion and rewrote the false spec comment (Settings performs
    user-initiated provider calls, so the SDK ships). With the SDK bundled the
    ImportError path is unreachable (task 1b-22).

- **D-28** `packaging/wing-ui-debug.spec` is an untracked copy that will drift
  - owner: machine-doable
  - evidence: `git status` shows it untracked. It differs from `wing-ui.spec` in
    three lines only: a UTF-8 BOM, the bundle name, and `console=True`. Every
    DATAS change must now be made twice or the debug build silently diverges —
    and **D-26** is exactly such a change.
  - close: delete it, or make it read the shared spec instead of copying it
  - status: closed 2026-08-26 — `packaging/make-debug-spec.py` now GENERATES it
    from `wing-ui.spec` (two transforms: name, console=True); it is regenerated
    output, stays untracked, and is regenerated after any spec change (task
    1b-22).

---

## Appendix — rulings preserved, not debt

These are decisions already taken and applied during wave-1 execution. They are
recorded here only because they lived in the gitignored ledger. **They are not
open items.**

| Source line | Ruling |
|---|---|
| pre-flight 15 | The Task 10 test referenced a `knowledge_dir` fixture that does not exist → drop the unused fixture argument; cache calls pass `directory=tmp_path` explicitly. |
| pre-flight 16 | `routing_view` carried defensive dead branches written before anyone read the real `summary()` → trim after reading `RoutingFacade.summary()`; keep only live code. |
| pre-flight 17 | Task 5's draft code snippets are shape guidance, not transcription source. Final code must stand alone. |
| pre-flight 18 | Build exactly per the spec header comment — from the repo root, `pyinstaller packaging\wing-ui.spec --noconfirm`, with `pathex` already set. |
| execution 26 | `test_make_provider_dispatch` failed for environmental reasons (a real gitignored `provider.yaml` at the repo root, read by the cwd fallback). Fixed by micro-task 0, commit `1f03170`. |

**On the baseline that ruling 26 also recorded:** it states 1298 passed / 1 skipped
as the new baseline. That figure was measured at **Task 0**, before eleven further
tasks landed, so it is not the current baseline and must not be quoted as one. The
wave-1 plan's own figure (1271 passed / 21 skipped) is older still. Any document
needing a test count must measure it, not copy one from here.
