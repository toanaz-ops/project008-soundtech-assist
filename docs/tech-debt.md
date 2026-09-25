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
by the command shown. The wave-1 / wave-1b closures below were written on
2026-08-26 by task 1b-23, each re-verified by running its close command that day
(final suite: **1433 passed / 3 skipped**).

---

## Rescued from the wave-1 SDD ledger

- **D-1** `channel_detail_rows` duplicates `render.channel_detail` by design
  - owner: machine-doable
  - evidence: ledger line 30, Task 1 (commits `6d99ede..b441397`). The duplication
    is intended — what is missing is the comment saying so, so the next reader
    does not "fix" it. *(inherited)*
  - close: add the cross-reference comment to both sites; `grep -n "channel_detail" wing_parser/ui/data.py wing_parser/cli/render.py`
  - status: closed 2026-08-26 (task 16W1) — `rg -n "channel_detail" wing_parser/ui/data.py wing_parser/cli/render.py` returns
    the cross-reference comments at `data.py:57-59` ("Label/value pairs mirroring
    render.channel_detail … Keep in sync — the duplication is intended") and
    `render.py:49` ("Keep in sync with wing_parser.ui.data.channel_detail_rows").

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
  - status: closed 2026-08-26 (task 16W1, commit `3a6173e` "Strengthen the
    ordering tests") — `test_diffcore.py:26`
    `test_natural_order_survives_two_digit_channel_numbers` seeds ch.2/ch.10 so
    lexicographic and natural order differ; included in the targeted run below.
- **D-4** Function-level imports in the briefed tests
  - owner: machine-doable
  - evidence: ledger line 34, Task 2+3. *(inherited)*
  - close: hoist to module level; `.venv/Scripts/python.exe -m pytest -q`
  - status: closed 2026-08-26 (task 16W1) — `tests/test_diffcore.py:5` now
    imports `WingScene` at module level; suite green (1433/3). Note: the same
    function-level pattern survives in `tests/test_ui_data.py` (a Task 1 file,
    outside this item's original Task 2+3 evidence) — treat that as cosmetic.

- **D-5** `theme.qss` `var()` is dead until literal substitution
  - owner: machine-doable
  - evidence: ledger line 36, Task 4 (`b6ba324`). Superseded in scope by **D-20**,
    which establishes that Qt's QSS engine has no custom-property support at all,
    so this was never going to work rather than merely being unfinished.
  - close: closed together with D-20
  - status: closed 2026-08-26 — with D-20's substitution (task 1b-17).
    Measured on the generated sheet:
    `.venv\Scripts\python.exe -c "from wing_parser.ui.theme import load_stylesheet; q=load_stylesheet(); print(q.count('var(--'), q.count(chr(36)))"`
    → `0 0`.

- **D-6** `MainWindow.switch_to` has no unknown-key guard
  - owner: machine-doable
  - evidence: ledger line 39, Task 5 (`b6ba324..545045e`). A typo'd page key fails
    silently or raises from deep inside Qt rather than at the seam. *(inherited)*
  - close: raise `KeyError` naming the valid keys; add a test asserting it
  - status: closed 2026-08-26 — switch_to raises KeyError listing PAGE_ORDER; pinned by test (task 16W1, commit `ef0b36c`).

- **D-7** `DoctorPage.show_finding` emits `selected` on programmatic clears
  - owner: machine-doable
  - evidence: ledger line 40, Task 5. Recorded with "revisit when pages land" —
    the pages have now landed. *(inherited)*
  - close: guard the emit, or rename the signal to say what it means
  - status: closed 2026-08-26 — programmatic clears are silent; only the view's selection chain emits; silence pinned (task 16W1 `ef0b36c`; select_first hardened in 1b-19 `752f990`).

- **D-8** Channels detail pane goes stale on session swap
  - owner: machine-doable
  - evidence: ledger line 42, Task 7 (`545045e..6854625`). Opening a second scene
    leaves the previously selected channel's detail on screen until restart.
    Ledger calls it "a one-line reset candidate". *(inherited)*
  - close: reset in `set_session`; test that a swap clears the pane
  - status: closed 2026-08-26 — set_session resets title+grid unconditionally; swap test added (task 16W1, commit `ef0b36c`).

- **D-9** Import-order nit: `QtCore` after `QtWidgets`
  - owner: machine-doable
  - evidence: ledger line 43, Tasks 6-8. *(inherited)*
  - close: reorder; `.venv/Scripts/python.exe -m pytest -q`
  - status: closed 2026-08-26 — import blocks merged alphabetically, second QtWidgets block folded (task 16W1).

- **D-10** Diff sort test is trivially true with one magnitude row
  - owner: machine-doable
  - evidence: ledger line 45, Task 9 (`6854625..9adcce2`). *(inherited)*
  - close: add rows that only sort correctly under descending magnitude
  - status: closed 2026-08-26 — exact descending-magnitude-first sequence asserted with discriminating rows (task 16W1, commit `3a6173e`).

- **D-11** A failed compare keeps the last good rows beside the error label
  - owner: needs-human — this is a UX ruling, not a bug
  - evidence: ledger line 46, Task 9, recorded as "deliberate UX decision to note
    in final review". It has never been written into a spec, so it currently
    exists only as behaviour nobody agreed to.
  - close: own it or reverse it in the wave-1 spec's per-page acceptance for the
    Diff page, then link that section here
  - status: closed 2026-08-26 — owned by ruling (ToanAZ-delegated): Diff keeps last-good rows beside the error label; recorded in the wave SDD ledger and the completion handoff; diff.png/diff-b.png A/B capture shipped for his review.

- **D-12** Lazy `sample_workbook` import inconsistency
  - owner: machine-doable
  - evidence: ledger line 48, Task 10 (`9adcce2..61c120a`). *(inherited)*
  - close: make the import style consistent with the rest of `import_controller.py`
  - status: closed 2026-08-26 — sample_workbook import hoisted (task 16W1).

- **D-13** Save As filter offers `.xlsx` for a YAML output
  - owner: machine-doable
  - evidence: ledger line 51, Task 11 (`61c120a..d7cffeb`). The import wizard
    writes a show-context `.yaml`; the dialog filter says xlsx. *(inherited)*
  - close: correct the filter; assert the filter string in the page test
  - status: closed 2026-08-26 — Save As uses a YAML filter; filter string asserted (task 16W1, commit `ef0b36c`).

- **D-14** `import.error` shows raw exception text with no lead-in
  - owner: machine-doable
  - evidence: ledger line 52, Task 11. The operator sees a Python exception
    rendered as a sentence. *(inherited)*
  - close: covered by the error taxonomy in the rewritten wave-1 spec; the string
    must read as a sentence and name a next action
  - status: closed 2026-08-26 — import.error reads as a sentence naming the next action (task 16W1, commit `ef0b36c`).

- **D-15** Import tests reach page privates `_result` / `_directory`
  - owner: machine-doable
  - evidence: ledger line 53, Task 11. Tests coupled to private attributes break
    on any refactor — and a restyle is a refactor. *(inherited)*
  - close: route through the existing public seams (`pick_file`, `show_terms_step`,
    `save_as`); `.venv/Scripts/python.exe -m pytest tests/test_ui_import_page.py -q`
  - status: closed 2026-08-26 — commit `4c72bbf` exposed the public seams
    (result property, `set_output_directory`, `show_terms_step`). Close
    output: `rg -n "_result|_directory" tests/test_ui_import_page.py`
    matches only the public `page.set_output_directory(...)` at lines
    180 and 208; the file passes inside
    `45 passed, 2 skipped` (measured 2026-08-26 on `04db887`).

- **D-16** `theme.py` docstring lines 4-5 state something untrue
  - owner: machine-doable
  - evidence: ledger line 37, routed from Task 4 to Task 14: *"Task 14 MUST also
    fix theme.py docstring lines 4-5 (claims spec maps ui/resources; it does not
    yet)"*. Task 14 never ran. Confirmed still true — see **D-26**, which is the
    packaging half of the same problem.
  - close: fix the docstring in the same commit that adds the DATAS entry (D-26)
  - status: closed 2026-08-26 — `theme/paths.py` docstring now states the mapping;
    fixed in the same commit as **D-26** (task 1b-22). Clarification (reviewer
    Minor finding): there is no `theme.py` any more — it became the
    `wing_parser/ui/theme/` package (`tokens.py`, `paths.py`, `fonts.py`,
    `proxy_style.py`, …), so every `theme.py` citation in older documents reads
    as that package today.

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
  - status: closed 2026-08-26 — `tests/test_ui_screenshot.py::
    test_every_page_renders_in_the_house_palette` converts each grabbed
    frame to RGBA8888, walks every pixel's bytes, and asserts ≥3 distinct
    colours and ≥2 house tokens per page. Close output: that test passes
    (inside `45 passed, 2 skipped`, measured 2026-08-26 on `04db887`).

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
  - status: closed 2026-08-26 — `wing_parser/ui/__main__.py` calls
    `apply_theme(application)` before `MainWindow(session)` (commit
    `a473e90`, task 1b-16/17). Close output: the test built for exactly
    this, `test_every_page_renders_in_the_house_palette`, passes — a
    frame from an unstyled app cannot carry two house tokens.

- **D-20** `theme.qss` is built on `var(--…)`, which Qt's QSS engine ignores
  - owner: machine-doable
  - evidence: `wing_parser/ui/resources/theme.qss:6-11` declares
    `--background/--foreground/--accent` and line 11 reads
    `background: var(--background)`. Qt stylesheets have no CSS custom
    properties; the whole rule is discarded with no diagnostic.
  - close: generate the stylesheet from a token table by substitution; assert
    `"$" not in load_stylesheet()` and `"var(--" not in load_stylesheet()`
  - status: closed 2026-08-26 — task 1b-17 (commit `2d34d6d`): 19 int
    tokens in `theme/tokens.py`, `string.Template.substitute()` (not
    `safe_substitute`) over `theme.qss` + `chrome.qss`, and
    `test_the_stylesheet_is_fully_substituted_and_declares_no_type`
    asserting both bans. Close output:
    `var(--) count: 0, unsubstituted dollar: 0` from `load_stylesheet()`
    (measured 2026-08-26 on `04db887`).

- **D-21** `PySide6-Fluent-Widgets` is a declared dependency that nothing imports
  - owner: needs-human — removing a dependency is the owner's call
  - evidence: declared in `pyproject.toml` under the `ui` extra; a repo-wide
    `grep -rni "qfluent" --include=*.py .` matches only `.venv/`. Every install
    downloads a library the app never touches.
  - close: remove it from the `ui` extra, or state in the spec which wave intends
    to use it
  - status: closed 2026-08-26 — ruled by ToanAZ (delegated): removed from the ui extra and uninstalled; suite green without it (task 1b-22, `04db887`).

- **D-22** The cited look-and-feel authority does not exist
  - owner: machine-doable
  - evidence: the skill `pyside6-ui-quality` is cited 9 times across the wave-1
    spec, its plan and `AGENTS.md` as the source of the visual rules, the
    screenshot loop and the packaging discipline.
    `find /c/Users/id_az/.claude -iname "*ui-quality*"` returns nothing, and the
    repo's own `skills/` holds only `wing-*` skills. Every visual requirement in
    the wave is therefore delegated to a document nobody can open.
  - close: repoint every citation at the house-style spec; `grep -rn "pyside6-ui-quality" docs/ AGENTS.md` must be empty
  - status: closed 2026-08-26 — resolution: the skill EXISTS at `C:\Users\id_az\.config\opencode\skills\pyside6-ui-quality\SKILL.md` (the original search covered only ~/.claude); AGENTS.md now cites both that path and the in-repo house-style plan as authorities (task 1b-23).
    missing**: the authority DOES exist on this machine. Close output:
    `Get-ChildItem C:\Users\id_az\.config\opencode\skills\pyside6-ui-quality`
    → `SKILL.md  (2586 bytes)`. The original evidence searched
    `~/.claude` only; the skill lives under `~/.config/opencode/skills/`
    (correction first recorded in the SDD ledger, 2026-08-26). The
    original close criterion ("grep must be empty") was wrong once the
    citation resolves; the criterion that matters — every citation
    resolves to a document that exists — is met, and `AGENTS.md` now
    cites both the skill and the in-repo house-style plan
    (`2026-08-26-gui-house-style-wave1b.md`) so neither host nor repo
    holds the rules alone.

- **D-23** No accessibility affordances at all
  - owner: machine-doable
  - evidence:
    `grep -rn "setShortcut\|QKeySequence\|setAccessibleName\|setTabOrder" wing_parser/ui/`
    returns zero matches. One `setToolTip` exists, in the pre-existing
    `detail_panel.py`. There is no Ctrl+O and no Ctrl+S; the menus carry Alt
    mnemonics only.
  - close: the keyboard map, tab order and visible focus ring ruled by ToanAZ on
    2026-08-26; assert each accelerator in a shell test
  - status: closed 2026-08-26 — keyboard map per ruling (Ctrl+O/Ctrl+Shift+S/Ctrl+Z/Ctrl+1..6/F5/Esc), per-page tab-order tests, visible focus ring via QProxyStyle (tasks 1b-18/1b-21, `b75097c`/`e7bb449`). Two honest skips: overview/channels hold exactly one focusable widget today.
    `menus.py` binds Ctrl+O / Ctrl+Shift+S / Ctrl+Z / F5 and the
    Ctrl+1…6 page QShortcuts; **Esc is NOT a binding** — it is
    QDialog's built-in reject, characterised (not implemented) by
    `test_escape_closes_the_settings_dialog`; `focus_chain.py` keeps
    Tab inside the visible page, and `HouseStyle`
    (`theme/proxy_style.py`) draws the focus ring from the style.
    Close output:
    `tests/test_ui_keyboard.py` (161 lines) passes — inside
    `45 passed, 2 skipped` (measured 2026-08-26 on `04db887`).

- **D-24** `main_window.py` bypasses `texts.py`, breaking the spec's own i18n rule
  - owner: machine-doable
  - evidence: hardcoded English user-facing strings — `"Cannot open that file"`,
    `"Cannot save"`, `"Saved"`, `"Knowledge directory"` — plus the menu titles
    `&File` / `&Edit` / `&Tools` / `&Help`. The wave-1 spec requires that all new
    user-facing strings go through `wing_parser/ui/texts.py`.
  - close: move them into `texts.py`; add a test that scans `wing_parser/ui/` for
    quoted strings passed to `setText`/`setWindowTitle`/`QMessageBox`
  - status: closed 2026-09-15 — `ast` scanner over `wing_parser/ui/**/*.py` (`0b5e295`, widened `63a8d6c` after review refuted the first pass) fails naming file:line. **Covers:** the ten setters (setText/setWindowTitle/setToolTip/setPlaceholderText/setTitle/setTabText/setStatusTip/setWhatsThis/addMenu/addAction), seven widget constructors (QPushButton/QLabel/QGroupBox/QAction/QMenu/QCheckBox/QRadioButton), the QMessageBox statics bare or attribute-qualified, and the QFileDialog statics' caption and filter arguments — plain literals and f-strings alike. **Cannot cover** (named in tests/test_ui_texts.py's module docstring, and the reason a clean run is not proof the rule holds): a string bound to a name first (`FILTER = "..."` reaches the call as a Name), a string built at runtime by `.format`/`%`/concatenation/`join`, and any Qt class or method not in the hand-edited lists. Eighteen strings routed through texts.py in total — eight by the first pass (`0a7eaa2`, `6be328e`, `fad8076`, `fd8f15e`) and ten more by the widened one, five of those bound to a module constant first and so found by reading, not by the test. Argued and left: `__main__.py:18` MISSING_PYSIDE (printed before Qt exists), `findings_view.py:28` ALL (a compared-against sentinel), `elide.py:23` ELLIPSIS (typography), and `overview_page.py:49` `QLabel("0")` (a digit, allowlisted by value). All four re-read from the files 2026-09-15. A fifth, of a different kind, argued and left 2026-09-16 (wave 2): `live_snapshot.py:195` shows an exception's own message with `setText(str(exc))` for `EmptyReadError`, whose sentence is authored at `live_controller.py:59-64` (ported from `cli/commands.py:47-62`) -- the `menus.py:82` precedent, `QMessageBox.critical(window, text("error.open"), str(exc))`, which this rule has accepted since wave 1; invisible to the scan either way, being a Call and not a Constant. Pinned by `test_no_user_facing_literal_bypasses_texts_py`, `test_the_scan_would_catch_a_regression` and `test_a_module_level_constant_is_a_known_blind_spot` (tests/test_ui_texts.py).

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
  - status: closed 2026-08-26 — FunctionWorker + CallRunner: cancellable workers, Cancel chrome at all three model-call sites, numeric timeouts {proposal 120s, guesses 180s, probe 30s}; QTimer-tick responsiveness proof during a blocked provider (Task C, commit `6d0747d`).

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

- **D-29** `import_page.py` exceeds the ~200-line file ceiling
  - owner: machine-doable
  - evidence: measured 246 lines after task C (`git show HEAD --stat` era);
    grew past 200 during 1b-19 wiring despite correct extraction into
    step_rail.py/key_status.py.
  - close: extract remaining step orchestration (pick/mapping glue) into its
    own module; `.venv/Scripts/python.exe -m pytest tests/test_ui_import_page.py -q`
  - status: closed 2026-09-15 — step builders and the `finish_mapping`/`show_preview` transitions extracted to `wing_parser/ui/import_steps.py`; import_page.py 246 → 177, the new module 117, tests/test_ui_import_page.py unchanged (`be22878`), pinned by `test_no_ui_module_is_over_the_line_ceiling` (tests/test_ui_house_style.py).

- **D-30** Placeholder API key reads as configured
  - owner: machine-doable
  - evidence: KeyStatusLine treats any non-empty provider.yaml as configured;
    a local, untracked provider.yaml carrying the `PASTE_KEY_<PROVIDER>_VAO_DAY`
    convention (or the manual's `sk-xxxxxxxx...`, docs/user-manual/04 lines 14
    and 24) would hide the unconfigured warning while the assisted path fails
    on the first model call. Nothing of the sort is committed: provider.yaml
    has never been tracked (.gitignore line 28; `git log --all -- provider.yaml`
    is empty), because it holds a key. Wording corrected 2026-09-15 — the
    original said "the repo's committed-shape placeholder value", which reads
    as a key file in git.
  - close: treat known placeholder prefixes as unconfigured in KeyStatusLine;
    add a test with a placeholder-bearing provider.yaml.
  - status: closed 2026-09-15 in two halves. **Placeholder rejection** (`02cadb6`): the placeholder set lives once as `provider.is_placeholder_key` / `has_usable_key`, shared by KeyStatusLine and both provider adapters — so a placeholder earns the local "no API key" message naming provider.yaml and the env var, rather than a 401 from the far end. Pinned by `test_the_paste_key_convention_is_not_a_key` (tests/test_provider_config.py). **One resolver** (`44e222d`): the first attempt gave the key line a second, nearly-identical search chain, and review found it disagreeing with the call it describes — a keyless knowledge-dir provider.yaml (Settings saved with an empty key field) stopped the hint while the model call walked on to ./provider.yaml and found a real key. The search now lives once as `provider.resolve_config(knowledge_dir)` — pin → knowledge-dir copy IF it carries a usable key → `load_config(None)` — taken by KeyStatusLine, `ImportPage._provider_factory` and the Settings dialog's Test connection. Pinned by `test_the_key_hint_and_the_model_call_read_the_same_config` (tests/test_ui_import_page.py), which asserts the built provider's key and the hint's verdict together. **Scope:** this unifies the DESKTOP app only. `wing showcontext import` still resolves with `load_config(None)` and does not read the knowledge dir — see **D-39**.

- **D-31** Settings Cancel button reuses the `import.cancel` texts key
  - owner: machine-doable
  - evidence: settings_dialog.py builds its Cancel from texts["import.cancel"];
    works today, misleads the next texts.py reader.
  - close: add settings.cancel key and consume it.
  - status: closed 2026-09-15 — `settings.cancel` added to texts.py and consumed by settings_dialog.py (`b5c506d`), pinned by `test_cancel_uses_its_own_texts_key` (tests/test_ui_settings.py).

- **D-32** `fonts._family_for` falls back silently when a face is missing
  - owner: machine-doable (parked — guarded elsewhere)
  - evidence: final review 2026-08-26, `wing_parser/ui/theme/fonts.py` — a
    missing face returns `QFont().family()` instead of failing; the
    `failed() == ()` test is the only guard.
  - close: raise or return a guaranteed-absent name; keep the failed() pin.
  - status: open

- **D-33** `theme/install.py` bypasses the stylesheet cache; qtawesome
  ImportError degrades silently
  - owner: machine-doable (parked — cosmetic)
  - evidence: final review 2026-08-26 — apply() calls `qss.build()` directly
    so applied sheet and cached copy come from different paths; bare
    `except ImportError: pass` around qtawesome means missing icon dep ships
    unstyled icons with no log.
  - close: route through load_stylesheet(); log once on qtawesome miss.
  - status: open

- **D-34** Magnitude-bar peak cache keyed on row count only
  - owner: machine-doable (parked — latent)
  - evidence: final review 2026-08-26, `wing_parser/ui/elide.py` `_bar_peak` —
    same row count with different data scales bars against a stale peak.
    Latent because compare rebuilds rows wholesale.
  - close: invalidate on model reset / dataChanged.
  - status: open

- **D-35** `SHOW_MAGNITUDE_BAR` restore in --screenshot is not exception-safe
  - owner: machine-doable (parked — process exits anyway)
  - evidence: final review 2026-08-26, `wing_parser/ui/__main__.py` A/B block;
    a raise between flag-off and flag-on leaves it off. Impact nil (screenshot
    mode exits); corroborated by the offscreen COM banner there.
  - close: wrap in try/finally on next touch of that block.
  - status: open

- **D-36** `tests/test_ui_elide.py` shipped with a UTF-8 BOM
  - owner: machine-doable
  - evidence: final review 2026-08-26 measured `EF BB BF`; violates the house
    UTF-8 rule the same branch enforces for its qss templates.
  - close: strip bytes; done in the final-review fix commit.
  - status: closed 2026-08-26 — BOM stripped (`xxd`-equivalent byte read shows
    `2F 20` head now); no test change needed.

- **D-37** Delegate paint-elision smoke test asserts nothing
  - owner: machine-doable (parked)
  - evidence: final review 2026-08-26, tests/test_ui_elide.py paint smoke —
    renders but no assertion; bar tests carry real pixel assertions.
  - close: one pixel-differs-vs-untruncated assertion.
  - status: open

- **D-38** Spec text still promises the removed QFluentWidgets shell
  - owner: machine-doable
  - evidence: final review 2026-08-26 — spec `2026-08-25-gui-parity-design.md`
    §Theme still names QFluentWidgets components + hidden-import hooks after
    D-21's removal ruling; also §Import says terms are offered "one at a
    time" while TermsStep renders simultaneous rows (explicit-Record
    invariant preserved).
  - close: add a superseding note pointing at the wave-1b plan + rulings.
  - status: closed 2026-08-26 — superseding note added to the spec in the
    final-review fix commit.

- **D-39** A key saved in the desktop Settings dialog never reaches the CLI
  - owner: machine-doable
  - evidence: found 2026-09-15 while closing **D-30**, which unified the
    DESKTOP config chain and made this gap visible by contrast.
    `SettingsDialog.save()` writes `<knowledge_dir>/provider.yaml` and pins
    `$WING_PROVIDER_CONFIG` at `settings_dialog.py:164` — but that pin lives in
    the dialog's own process. A later `wing showcontext import` starts fresh,
    and the wizard resolves with `make_provider(load_config(None))` at
    `wing_parser/showcontext/ingest/wizard.py:53` (mapping proposal) and `:223`
    (term guessing). `load_config` walks `$WING_PROVIDER_CONFIG` →
    `./provider.yaml` → defaults; it never looks in the knowledge directory.
    So the operator pastes a key into Settings, the app works, and the CLI
    still prints `(no model assist: ...)`.
    Measured, same environment, no pin, no env keys, no `./provider.yaml`:

    ```
    knowledge dir            : ...\tmp7mb7fpms\knowledge
    UI  (resolve_config)     : 'sk-saved-from-settings'
    CLI (load_config(None))  : ''
    DIVERGE                  : True
    ```

    Not fixed with D-30 deliberately: the knowledge directory does not reach
    the wizard. `commands.py:271-279` calls `run_wizard(args.sheet, output=,
    force=, scene=, one_shot=)` — there is no `--knowledge` flag anywhere in
    `wing_parser/cli/`, no `knowledge_dir=` keyword, and **no CLI module calls
    `config.knowledge_dir()` at all** (every caller outside `config.py` is
    under `wing_parser/ui/`). Making the wizard read it would be the first
    CLI↔knowledge-dir coupling in the codebase, and the CLI's documented
    contract (docs/user-manual/04) is `./provider.yaml` plus the env var. That
    is a design call, not a tidy-up, so it is filed rather than smuggled into
    a debt-closing PR.
  - close: pass the knowledge directory into `run_wizard` and resolve both
    sites through `provider.resolve_config(knowledge_dir)`, the same function
    the desktop app uses; test that a key written the way
    `SettingsDialog.save()` writes it is picked up by the wizard's provider
    factory in a process with no `$WING_PROVIDER_CONFIG`. Decide at the same
    time whether the CLI should honour the knowledge dir at all, or whether
    Settings should instead offer to write `./provider.yaml` — the user manual
    has to agree with whichever is chosen.
  - status: closed 2026-09-17 (this PR) — **decision: the CLI honours the
    knowledge directory; Settings does NOT write `./provider.yaml`.** One
    resolver serves both surfaces, so the desktop app and `wing showcontext
    import` can no longer disagree about which key exists.
    `showcontext_import` resolves `config.knowledge_dir()` and passes it as
    `run_wizard(..., knowledge_dir=)` (the first CLI↔knowledge-dir coupling in
    the codebase, taken deliberately); both wizard model sites —
    `_propose_or_none` for the mapping proposal and the term-guess
    `provider_factory` — build through `provider.resolve_config(knowledge_dir)`,
    the same chain the desktop takes (pin → knowledge-dir copy IF it carries a
    usable key → `load_config(None)`). `knowledge_dir` defaults to `None`, and
    `resolve_config(None)` IS `load_config(None)`, so every direct caller keeps
    its old behaviour. Pinned by
    `test_the_wizard_reads_the_key_settings_saved_in_the_knowledge_dir`
    (mapping proposal), `test_the_term_guess_reads_the_same_saved_key` (the
    second site, and that one run builds both from the same config),
    `test_without_a_knowledge_dir_the_wizard_still_resolves_the_old_way` (the
    default is unchanged) and `test_cli_passes_the_knowledge_dir_to_the_wizard`
    (the wiring) — all in tests/test_ingest_wizard.py.
    `docs/user-manual/04-cau-hinh-model.md` §Cách 1 now states the same order.

- **D-40** `page_base.EmptyState` is now reachable only from a test
  - owner: machine-doable
  - evidence: task 13 (GUI wave 2) filled the last placeholder slot --
    `main_window.py` builds a real `ConsolePage` -- so nothing in
    `wing_parser/` constructs `EmptyState` any more. Its only live caller
    is `tests/test_ui_console.py::test_wiring_a_page_without_the_signals_connects_nothing`,
    which uses it as a widget that has none of the three console signals.
    Its two texts keys (`empty.open_hint`, `empty.open_button`) and its
    `open_requested` signal are unused with it.
  - close: decide between deleting `page_base.py` plus those two keys (and
    giving that test a plain `QWidget`), and keeping it as the documented
    placeholder for the next page that arrives over several tasks. Do not
    half-delete: `test_ui_texts.py::test_known_keys_resolve` asserts
    `empty.open_hint` resolves.
  - status: open

- **D-41** A live pull walks the schema twice
  - owner: machine-doable, deferred to wave 3 (it is a `net/` change)
  - evidence: GUI wave 2 (task 16 brief item 3). `take_snapshot` walks
    internally (`wing_parser/net/snapshot.py:83-85`, calling `walk_schema`
    before reading any leaf) and `build_watch_list` walks again
    (`wing_parser/net/watch/list.py:89`) -- neither function accepts a
    pre-computed `SchemaResult` from the other. Console page Discover then
    Pull (or the reverse) therefore costs two walks where one would do;
    the wave-2 design spec priced one walk at ~1 s (`docs/superpowers/specs/
    2026-09-15-gui-live-console-wave2-design.md` D11), so this is roughly a
    second of avoidable latency per round trip through the page, not a
    correctness bug.
  - close: add a `schema: SchemaResult | None = None` parameter to both
    `take_snapshot` and `build_watch_list` that skips the internal
    `walk_schema` call when supplied, and have `ConsolePage` pass the
    Discovery panel's result into a later Pull (and vice versa). This
    touches `wing_parser/net/`, which is why wave 2 did not do it (its own
    rule: a UI consumer does not modify `net/client.py`, `codec.py` or
    `schema.py`).
  - status: closed 2026-09-25 (debt-cleanup branch) -- the UI now adopts
    the seam. `Transport` gained a sixth entry, `walk_schema`; a new
    `wing_parser/ui/live_schema_cache.SchemaCache` remembers one walk;
    `discover`/`pull` take an optional `cache:` that, when given, walks
    once via `transport.walk_schema` and shares the result the other
    way. `ConsolePage` owns one `SchemaCache`, hands it to its
    `DiscoveryPanel` and `SnapshotPanel` (`functools.partial` binds
    `cache=` at the call site), and clears it on every disconnect and
    every fresh connect -- a schema is never reused across connections,
    per S2.10. `live_events_view.py` needed no change: Start Watch only
    ever consumes Discover's `WatchList`, it never walks on its own.
    Headroom needed splitting `console_page.py` (199 -> 188, `_wire`
    moved to `console_wiring.wire_console_page`), `live_controller.py`
    (199 -> 168, `EmptyReadError` moved to `live_errors.py`,
    `suggested_name`/`session_from_snapshot` moved to
    `live_session_build.py`, both re-exported) and `live_snapshot.py`
    (stayed at 199, a docstring trim plus one import line collapsed).
    Proven with a real `ConsolePage` driven through Connect/Discover/
    Pull/Disconnect against `FakeDesk` (`tests/test_ui_console.py`:
    `test_a_round_trip_through_discover_and_pull_walks_the_schema_once`,
    `test_the_schema_cache_is_dropped_on_disconnect_and_on_reconnect`),
    counting `FakeDesk.walks` (new: `_walk`/`_snapshot` only append there
    when NOT already handed a schema). Verified:
    `python -m pytest -q -p no:faulthandler --junitxml=dist-reports/suite.xml`
    -> 1785 passed / 3 skipped.

- **D-42** Quitting the app can wait up to ~5 s for a watch round in flight
  - owner: machine-doable
  - evidence: GUI wave 2, task 12's own concern, carried forward at task
    16. `net/watch/poller.py:121-123` computes the remaining time in the
    round and calls a plain `sleep(remaining)` with no cancellation seam;
    at `MAX_INTERVAL` (`wing_parser/ui/live_guard.py:37`, 5.0 s) a quit
    requested right after a round starts waits out that sleep before the
    `GeneratorWorker` thread can notice it has been cancelled and join.
  - close: give `poller.watch` a cancel-aware sleep (short slices checked
    against a `threading.Event`, or `Event.wait(remaining)` in place of
    `sleep`), which is a `net/` change -- same wave-3 boundary as D-41.
  - status: closed (task 15b, this commit) -- `poller.watch` takes
    a keyword-only `cancel: threading.Event | None = None`; its pace step
    (`_pace`) calls `cancel.wait(remaining)` when one is supplied, which
    returns the moment the event is set, instead of the plain `sleep`
    that had no cancellation seam. Default (omitted) behaviour is
    unchanged and pinned by test. `wing_parser/ui/live_watch_session.py`
    now passes `self.cancel` through; `WAIT_MS` is left at
    `(MAX_INTERVAL + 1.0) * 1000` deliberately -- shrinking it needs its
    own measurement against a real desk, and a generous bound is not a
    bug.

- **D-43** Save As suggests an unsanitised name for a pulled scene
  - owner: machine-doable
  - evidence: GUI wave 2, flagged at task 4 (deferred to task 11, then
    carried to final review). `suggested_name` (`wing_parser/ui/
    live_controller.py:159-173`) builds a bare filename from
    `identity.name` with no sanitisation --
    `f"{who}-{stamp}.snap"` -- and `session_from_snapshot`
    (`live_controller.py:195-199`) sets that string as the pulled
    `Session.path`. `menus.save_as` (`wing_parser/ui/menus.py:88-93`)
    then derives its dialog's suggestion from that same path
    (`.with_name(stem + "-edited.snap")`), so any character a desk's
    identity string carries -- a path separator, a leading dot -- reaches
    the Save As dialog unsanitised. No desk observed so far has produced
    one; this is a latent input-handling gap, not a reproduced failure.
  - close: split the seam -- have `suggested_name` sanitise the desk-
    supplied part only (e.g. `re.sub(r"[^\w.-]", "_", who)`) before it
    ever becomes a `Session.path`, and add a test with a desk name
    containing `/`, `\` and `..`.
  - status: closed 2026-09-16 (final review of GUI wave 2, item 1) --
    `suggested_name` (`wing_parser/ui/live_controller.py:169-172`) now
    filters the stem through `re.sub(r"[^\w.\-]", "_", stem)` before it
    becomes the `Session.path`, so `menus.save_as` can only ever derive
    from a sanitised name. Pinned by
    `test_the_suggested_name_sanitises_a_desk_name_that_is_a_path`
    (`tests/test_live_controller.py:386-399`), parametrised over
    `FOH/Monitors`, `..\evil` and `a:b`. The review also found the same
    gap from the other side -- Export mangling a *file-opened* path --
    and `live_export.export_name` (`live_export.py:43-49`) now proposes
    `Path(path).name` only, pinned by
    `test_the_export_dialog_suggests_a_bare_name_for_a_file_opened_scene`
    (`tests/test_ui_console.py:697-722`).

- **D-44** The read-only scan misses a relative dynamic import
  - owner: machine-doable
  - evidence: GUI wave 2, task 14's fix round (deferred to final review).
    `tests/test_ui_live_is_read_only.py`'s `_dynamic_call_reaches_write`
    (`:78-99`) recognises `import_module("wing_parser.net.write")` and
    `import_module("wing_parser.net", fromlist=["write"])`, but never
    reads `args[1]` or a `package=` keyword -- so the relative form
    `importlib.import_module(".write", "wing_parser.net")` resolves to
    the same module at runtime and is invisible to the scan (`target` at
    `:90` is `".write"`, which matches neither branch at `:91-93`). No
    module under `wing_parser/ui/` uses this form today; the scan's own
    stated job is to make a future one fail loudly, and right now it
    would not.
  - close: in `_dynamic_call_reaches_write`, when `target` starts with a
    dot, resolve it against `args[1]` (or the `package=` keyword) before
    comparing, the same way `importlib.import_module` itself does; add a
    planted-relative-import test alongside
    `test_the_scan_catches_a_planted_dynamic_import`.
  - status: closed 2026-09-16 (final review of GUI wave 2, item 4) --
    `_dynamic_call_reaches_write` (`tests/test_ui_live_is_read_only.py:93-101`)
    now resolves a dot-leading target through `importlib.util.resolve_name`
    against the literal second positional argument or the `package=`
    keyword, and returns `None` only when that package is not a literal.
    Pinned by `test_the_scan_catches_a_planted_relative_dynamic_import`
    (`:203-214`), which plants both spellings and asserts 2 offenders; it
    failed with `0 == 2` before the change. Note: the file is 225 lines,
    past the ~200 task 14 held it to -- the enforced ceiling
    (`tests/test_ui_house_style.py:173-184`) covers `wing_parser/ui/`
    only, and trimming 25 lines here would have cost the S8 narrative
    that documents the scan's rules and its remaining blind spots.

- **D-45** The wheel drops a YAML the exe already carries
  - owner: machine-doable
  - evidence: GUI wave 2, task 15 (C5), found while fixing the exe's own
    version of this gap. `pyproject.toml:31-32`'s
    `[tool.setuptools.package-data]` lists `net/watch/data/*.yaml` but not
    `net/data/*.yaml`, so `pip install .` ships `watchlist.yaml` and
    drops `wing_jsontypes.yaml` -- read by `net/jsontypes.py:28` via
    `net/export.py:41`, needed by any `wing net snapshot`, CLI included,
    not only the UI. `packaging/wing-ui.spec`'s DATAS list was fixed at
    the same task (task 15) and now names both directories explicitly, so
    only the wheel install path has the gap.
  - close: add `"net/data/*.yaml"` to the `package-data` glob list; test
    with a built wheel installed into a clean venv running `wing net
    snapshot` against `tests/fake_desk.py`. Out of this task's scope
    (task 16 was told not to touch `pyproject.toml`).
  - status: closed 2026-09-16 (final review of GUI wave 2, item 6) --
    `"net/data/*.yaml"` added to `pyproject.toml:32`. Measured both
    ways, each a `pip install .` into its own fresh venv on `D:` (not
    under `%TEMP%`, where Qt DLLs hang), then
    `importlib.resources.files("wing_parser.net").joinpath("data/wing_jsontypes.yaml").is_file()`
    read from `site-packages`, not the source tree: **False** from a
    `git archive` of the commit before the change, **True** after.

- **D-46** The generated debug spec is untracked but not gitignored
  - owner: machine-doable
  - evidence: GUI wave 2, task 15 (C3). `packaging/make-debug-spec.py:8`
    states "It is generated output and stays UNTRACKED -- never
    hand-edit it", but `.gitignore:21-22` covers only `*.spec.bak`; the
    generated `packaging/wing-ui-debug.spec` sits as `??` in `git status`
    and would be swept into a careless `git add -A`, against the
    generator's own header.
  - close: add `packaging/wing-ui-debug.spec` to `.gitignore`. Out of
    this task's scope (task 16 was told not to touch `.gitignore`).
  - status: closed 2026-09-16 (final review of GUI wave 2, item 5) --
    added at `.gitignore:23-25`, under the existing PyInstaller block
    and naming the generator. `git check-ignore -v
    packaging/wing-ui-debug.spec` prints
    `.gitignore:25:packaging/wing-ui-debug.spec`, and `git status
    --short` no longer lists it.

- **D-47** A `Windows fatal exception: code 0x8001010d` print during the suite
  - owner: machine-doable (parked — nothing is broken, the cost is a misread)
  - evidence: seen in every GUI wave-2 task run (tasks 6, 8, 9, 10, 11, 12, 14,
    15, 16) and again at the wave's final-review fix dispatch. `faulthandler`,
    which pytest enables by default, prints a C-stack dump for a *first-chance*
    structured exception; `0x8001010d` is COM's
    `RPC_E_CANTCALLOUT_ININPUTSYNCCALL`, raised and handled inside Qt when a
    widget is polished while Windows is in an input-synchronous call. Task 14
    traced one to `test_ui_console.py::test_an_empty_read_shows_an_error_line_and_no_session_reaches_the_window`
    -> `main_window.py` -> `import_page.py:63`
    (`self.step_area.addWidget(step)`, a `QStackedLayout` adopting native
    widgets). Nothing raises in Python and the process exits 0. Two ways it
    misleads: the dump interleaves into stdout and reads as a crash *at*
    whichever test was printing (task 16 chased exactly this), and at
    interpreter exit it can beat `pytest`'s own summary line to the console, so
    `N passed` never prints on a run that fully passed.
  - close: not a defect to fix in this repo -- record the two mitigations and
    stop re-diagnosing it. Run with `--junitxml=<path>` (the XML is written
    before the teardown print and carries the exact tally), or with
    `-p no:faulthandler` to silence the dump entirely. Only reopen if the
    exception ever becomes second-chance, i.e. a non-zero exit code.
  - correction 2026-09-18 (GUI wave 3, task 14): **the two mitigations are
    not interchangeable.** Measured twice at `f56813c`: a plain
    `python -m pytest -q` printed the faulthandler dump AND lost the summary
    line; the same run with `-p no:faulthandler` silenced the dump but
    **still printed no `N passed` line** and still exited 0. So
    `-p no:faulthandler` fixes only the interleaved-dump half of the
    problem. **`--junitxml` is the only reliable way to read the tally** --
    the XML at that commit carried `tests="1764" failures="0" errors="0"
    skipped="3"`, i.e. 1761 passed / 3 skipped, which is the number the
    wave-3 ROADMAP row and handoff quote.
  - status: open (parked)

---

## Opened by GUI wave 3 (write to a live console), 2026-09-18

Numbering continues from D-47. Each was verified by the command shown, on
branch `feat/gui-write-wave3` at `f56813c`, unless marked *(inherited)*.

D-48 to D-51 and D-53 are what the wave itself earned. D-52 rescues the
deferred minors out of `.superpowers/`, which `.gitignore` excludes -- the
same loss that made D1-D18 a rescue job.

- **D-48** The spec's section 4 module table is four modules short of what shipped
  - owner: machine-doable (a spec addendum, not a code change)
  - evidence: `docs/superpowers/specs/2026-09-17-gui-write-wave3-design.md`
    section 4 lists ten new modules. Fourteen landed: the table's ten plus
    `wing_parser/ui/write_router.py` (146 lines), `write_gate.py` (132),
    `write_records.py` (160) and `write_apply.py` (54). Three of the four
    are ceiling splits the plan did not foresee and the SDD ledger records
    as rulings (`.superpowers/sdd/2026-09-17-gui-write-wave3/progress.md`,
    tasks 4, 11 and 13); `write_router.py` is the routing layer section 4
    folded into prose. A reader who trusts that table will look for
    `route_repair` in `live_write.py` and not find it.
  - close: add a `## Deviations recorded 2026-09-18` block to the spec, the
    way the wave-2 spec carries one, listing the four modules and the ruling
    that produced each; `ls wing_parser/ui/write_*.py`
  - status: open, and **two more deviations joined it at task 16**, both
    recorded in `docs/handoff/2026-09-18-gui-write-wave3-complete.md` §12
    rather than in the spec: `revert_confirmation` (spec §, plan lines
    1247/1399) was **deleted** in favour of `write_records.desk_now`, and the
    W4 allow-list is keyed on the path **relative to the scan root**, not on
    `path.name` (plan line 70/971/996). The block should list six, not four.

- **D-49** `SentWrite` carries both spellings of the same leaf
  - owner: deliberate-no -- recorded so the duplication is not mistaken for
    an oversight
  - evidence: `wing_parser/ui/write_records.py:49-50` holds `address`
    (`/ch/1/send/8/mode`) and `path` (`ae_data.ch.1.send.8.mode`) for one
    leaf. Revert needs the dotted path back -- to build a `Patch` and to
    reach `jsontypes` -- and this project has **no inverse of
    `osc_address`** (`wing_parser/net/address.py`). Carrying the value
    cannot drift; deriving it would be a second mapper to keep in step with
    `snapshot.py:_place` (W2).
  - close: n/a unless a `path_from_address` is ever written, at which point
    it needs the `$ctl` re-prefix rule and a test per shape, and this field
    can go
  - status: open (deliberate)

- **D-50** `write_delay_dialog.py` is at exactly the 200-line ceiling
  - owner: machine-doable
  - evidence: `wc -l wing_parser/ui/write_delay_dialog.py` gives **200**, and
    `tests/test_ui_house_style.py:170` sets `CEILING = 200` -- so the next
    line added to that file fails the suite. It is the wave's tightest file.
    The wave-3 plan expected `live_wiring.py` to be the tight one; Task 11's
    escape hatch split `write_gate.py` out of it and it now sits at 115, so
    the pressure moved rather than went away. `console_page.py`,
    `live_controller.py` and `live_snapshot.py` remain at 199 each --
    pre-existing, and the reason D-41's UI half is still open.
  - close: split the pre-flight read (`_read_desk` / `_no_read`) or the
    terminal-state handling out of the dialog before the next change to it;
    `wc -l wing_parser/ui/write_delay_dialog.py`
  - status: closed 2026-09-25 (debt-cleanup branch) -- split for real
    headroom this time, not just enough for the next line. New
    `wing_parser/ui/write_delay_support.py` holds `PreflightRead` (was
    `_read_desk`/`_no_read`), `WriteOutcome` (was `_done`/`_failed`) and
    `cancel()` (was `_cancel`), each mutating the dialog instance it is
    given, same behaviour. `write_delay_dialog.py`: 200 -> 179 (168
    right after the split, +11 for the D-52 #8 fix that landed in the
    same session). `changes_ledger.py` also got a small win: its two
    identical `write_router.route_revert` call sites collapsed behind a
    `_route()` helper, 198 -> 197. Verified:
    `python -m pytest -q -p no:faulthandler tests/test_ui_write_dialogs.py
    tests/test_ui_changes_send.py tests/test_ui_house_style.py
    tests/test_ui_live_is_read_only.py` -> 99 passed, 0 failed.

- **D-51** Two of the three result badges have no glyph in the shipped font
  - owner: machine-doable
  - evidence: seen in the task-14 screenshot `07-changes-dock-badges.png`
    and then measured. With the app's own theme applied,
    `QRawFont.fromFont(label.font()).supportsCharacter(...)` on the vendored
    **IBM Plex Sans** returns `True` for U+2713, U+00B7, U+2026 and U+2192,
    but **`False` for U+26A0 (the clamped badge's warning sign) and U+2717
    (the no-reply badge's cross)** -- the two characters
    `wing_parser/ui/texts_write.py:70-77` puts on those badges. In the grab,
    U+26A0 came back from a Windows fallback font while **U+2717 rendered as
    a replacement box**. The no-reply badge is the most dangerous of the
    three (the desk did not answer; the packet may or may not have landed)
    and it is the one that renders as tofu. Fallback coverage is per-machine,
    so a venue laptop may show it differently again.
  - close: decide between vendoring a symbol face for those two codepoints
    and replacing them with characters IBM Plex Sans carries; then re-run
    `dist-shots/shoot_write_surfaces.py` and look at the badges. Do not close
    it on the font check alone -- the point is what the operator sees.
  - status: closed 2026-09-18 (task 16, review MINOR 6) -- the second
    option. `wing_parser/ui/texts_write.py` now uses **U+2713 `✓`**, plain
    **`!`** and **U+00D7 `×`**, all three of which the vendored faces carry;
    the countdown's mismatch line loses U+26A0 for the same reason. The words
    on each badge are unchanged. Pinned two ways in `tests/test_ui_texts.py`:
    `test_no_write_string_uses_a_glyph_the_vendored_font_lacks` fails if
    U+26A0 or U+2717 reappears ANYWHERE in `WRITE_TEXTS`, and
    `test_each_badge_still_carries_a_mark_of_its_own` fails if a swap
    flattens three outcomes into one shape. `grep -n "26a0\|2717"
    wing_parser/ui/texts_write.py` returns nothing.
    **Caveat, deliberately recorded:** the screenshots were NOT regenerated,
    so `06-delayed-mismatch.png` and `07-changes-dock-badges.png` still show
    the old marks. The strings are fixed; the look-at-it gate is not, and the
    handoff §5 says so.

- **D-52** Wave-3 minors deferred during implementation
  - owner: mixed; rescued here because
    `.superpowers/sdd/2026-09-17-gui-write-wave3/progress.md` is gitignored
    and one `git worktree remove` deletes it
  - evidence: that ledger's own lines, one per task. *(inherited -- recorded
    by the implementing agents and, except where marked, not independently
    re-verified here.)*
    1. `net/address.py`'s error text hardcodes `"ae_data"` beside `{ROOT}`
       (task 1). **Closed 2026-09-25** -- both mentions in `leaf_parts`'s
       `ValueError` now read `{ROOT}`.
    2. `RevertQueue.next` pops index 0 of a list, O(n) (task 2) --
       `wing_parser/ui/apply_level.py:76`. Re-verified by reading.
       **Closed 2026-09-25** -- `_pending` is a `collections.deque` now,
       `next()` calls `popleft()`; order, `progress` and `remaining` are
       unchanged and covered by the existing tests.
    3. `live_write.REAL._read` has no unit test (task 3); it must therefore
       be on the section 9.3 real-desk acceptance list.
    4. ~~`tests/test_live_state.py:70` re-imports `pytest` inside a
       function (task 5).~~ **Not reproducible 2026-09-18:**
       `grep -n "import pytest" tests/test_live_state.py` returns one hit,
       at module level (`:14`), and no function-level import anywhere in the
       file. Either it was cleaned up in a later fix round or the ledger line
       was wrong. Nothing to do.
    5. An unreachable requeue branch in `WriteGate._start` (task 8) --
       `wing_parser/ui/write_gate.py:120-125`. Re-verified by reading.
       **Closed 2026-09-25** -- proved unreachable (`WriteQueue._pump` only
       calls `_start` when its own in-flight slot is empty, which clears
       only after `CallRunner._settle` already cleared `_active`, and this
       `WriteGate`'s runner has no other caller); the branch was also
       WRONG on top of being dead (it would recurse into `_start` while
       the runner was still busy, not actually wait). Replaced with a
       `RuntimeError` naming the assumption -- `WriteQueue._pump` already
       catches and propagates a raising `start()`.
    6. `tests/test_ui_state_store.py`'s geometry test fails **only** under
       `QT_QPA_PLATFORM=offscreen` (task 8, pre-existing).
    7. The step-5 red-mutation demo was skipped for the classifier (task 9).
    8. `+5 s` is inert while the countdown is held at zero awaiting the
       pre-flight read, and a gate-closed path leaves buttons
       enabled-but-inert (task 10). **Second half fixed 2026-09-18 (task 16,
       review IMPORTANT 2):** a gate-closed path now CLOSES the dialog, so
       there are no enabled-but-inert buttons left to be stuck behind.
       **First half closed 2026-09-25:** per spec F5 ("+5 s (extends the
       remainder, unbounded presses)"), `+5 s` at zero now clears
       `_expired` and restarts `_timer`, resuming the countdown from 5s
       rather than sitting inert until the read lands and applies
       immediately with none of the extra time actually bought. TDD:
       `test_plus_five_resumes_a_countdown_held_at_zero_awaiting_the_read`
       (`tests/test_ui_write_dialogs.py`), confirmed failing on the
       unfixed code by temporarily stashing the fix and re-running it.
    9. `ImmediateWrite` submits `desk_before=None` on a failed pre-flight
       (task 11; plan-mandated), and `_LevelBox` raises on a non-`ApplyLevel`
       string. **Half-answered 2026-09-18 (task 16, review CRITICAL 1):** the
       submit is still plan-mandated and unchanged, but the ledger row it
       produces can no longer be reverted -- the button is disabled with a
       tooltip, `revert_all` steps over it, and `route_revert` raises
       `ValueError`. Reverting one used to put `,s "None"` on the wire.
    10. The end-to-end revert-all test asserts order but not strictly "the
        second did not start before the first settled" (task 13);
        serialisation is proven by a separate base-round mutation test.
  - close: (3), (6), (7), (9) second half and (10) still need triage --
    (3) and parts of (9)/(10) need a real desk (§9.3) or a larger
    behaviour decision. Read the source lines out of
    `.superpowers/sdd/2026-09-17-gui-write-wave3/progress.md` while that
    file still exists.
  - status: partially closed 2026-09-25 (items 1, 2, 5, 8) -- items 3, 4
    (n/a), 6, 7, 9, 10 remain open

- **D-53** W3b's warning never reached `repairs.yaml`
  - owner: machine-doable
  - evidence: the spec states it in the present tense -- W3b says *"a comment
    says so in `repairs.yaml` beside the `KINDS` tuple it mirrors
    (`repairs.py:30`)"* -- and it does not.
    `git diff --stat main..HEAD -- wing_parser/edit/` is **empty**, so the
    whole `edit/` package is untouched by this wave, and
    `grep -n "typetag" wing_parser/edit/data/repairs.yaml` finds nothing.
    What the missing comment was to warn about is real and unchanged: every
    `to:` in the eleven descriptors is a string or a bool today, and the
    first **int-valued** one would go out as a display string through
    `write.set`'s default `typetag=None` (`wing_parser/net/write.py:125-137`)
    and could select the wrong enum entry silently, because the read-back
    compares the same re-expression (`write.py:82-91`).
  - close: add the comment beside `KINDS` in `wing_parser/edit/repairs.py:30`
    and at the head of `wing_parser/edit/data/repairs.yaml`, naming the
    `typetag="i"` path and the test an int descriptor must ship with;
    `grep -n "typetag" wing_parser/edit/repairs.py wing_parser/edit/data/repairs.yaml`
  - status: closed 2026-09-18 (task 16, review MINOR 9) -- both places, as
    the close criterion asked. The YAML header carries the full statement
    (why the default `typetag=None` path can select the wrong enum entry
    silently, and that the read-back compares the same re-expression so it
    agrees with itself); `repairs.py` carries the short form beside `KINDS`
    and points at the YAML. Verified with the grep above: four hits in the
    YAML, two in `repairs.py`. Nothing shipped changes -- every `to:` is
    still a string or a bool.

- **D-54** `dist-reports/` is untracked but not gitignored
  - owner: machine-doable
  - evidence: GUI wave 3, task 14. Task 1 of this wave wrote its JUnit XML
    to `dist-reports/suite.xml` (`.superpowers/sdd/2026-09-17-gui-write-wave3/
    task-1-report.md`, step 4) and the directory now holds `probe.xml` and
    `suite.xml`. `.gitignore` covers `dist/`, `junit.xml` and `/*.junit.xml`
    but not `dist-reports/`, so it sits as `??` in `git status --short` on a
    branch whose only other change is docs -- exactly the shape D-46 had
    before it was closed, and exactly what a careless `git add -A` sweeps up.
  - close: add `dist-reports/` to `.gitignore` beside the other build
    output; `git check-ignore -v dist-reports/suite.xml`
  - status: closed 2026-09-25 (debt-cleanup branch) -- added at
    `.gitignore:23`, under the `junit.xml` line and above the PyInstaller
    block. Verified: `git check-ignore -v dist-reports/suite.xml` prints
    `.gitignore:23:dist-reports/`.

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
