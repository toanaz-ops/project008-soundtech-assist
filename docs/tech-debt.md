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
  - status: closed 2026-09-15 — `ast` scanner over `wing_parser/ui/**/*.py` (`0b5e295`, widened `63a8d6c` after review refuted the first pass) fails naming file:line. **Covers:** the ten setters (setText/setWindowTitle/setToolTip/setPlaceholderText/setTitle/setTabText/setStatusTip/setWhatsThis/addMenu/addAction), seven widget constructors (QPushButton/QLabel/QGroupBox/QAction/QMenu/QCheckBox/QRadioButton), the QMessageBox statics bare or attribute-qualified, and the QFileDialog statics' caption and filter arguments — plain literals and f-strings alike. **Cannot cover** (named in tests/test_ui_texts.py's module docstring, and the reason a clean run is not proof the rule holds): a string bound to a name first (`FILTER = "..."` reaches the call as a Name), a string built at runtime by `.format`/`%`/concatenation/`join`, and any Qt class or method not in the hand-edited lists. Eighteen strings routed through texts.py in total — eight by the first pass (`0a7eaa2`, `6be328e`, `fad8076`, `fd8f15e`) and ten more by the widened one, five of those bound to a module constant first and so found by reading, not by the test. Argued and left: `__main__.py:18` MISSING_PYSIDE (printed before Qt exists), `findings_view.py:28` ALL (a compared-against sentinel), `elide.py:23` ELLIPSIS (typography), and `overview_page.py:49` `QLabel("0")` (a digit, allowlisted by value). All four re-read from the files 2026-09-15. Pinned by `test_no_user_facing_literal_bypasses_texts_py`, `test_the_scan_would_catch_a_regression` and `test_a_module_level_constant_is_a_known_blind_spot` (tests/test_ui_texts.py).

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
    the repo's committed-shape placeholder value ("PASTE_KEY...") would hide
    the unconfigured warning while the assisted path fails on first model call.
  - close: treat known placeholder prefixes as unconfigured in KeyStatusLine;
    add a test with a placeholder-bearing provider.yaml.
  - status: closed 2026-09-15 — the placeholder set lives once as `provider.is_placeholder_key` / `has_usable_key`, shared by KeyStatusLine and both adapters (so the CLI says "no API key" instead of earning a 401), and the key line now also reads the knowledge-dir provider.yaml the Settings dialog writes (`02cadb6`), pinned by `test_the_paste_key_convention_is_not_a_key` (tests/test_provider_config.py).

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
