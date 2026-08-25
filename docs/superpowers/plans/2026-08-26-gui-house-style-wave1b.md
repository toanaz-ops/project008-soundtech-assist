# GUI house style "Sodium Rack" — Wave 1b implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development`
> (recommended) or `superpowers:executing-plans` to implement this plan task-by-task.
> Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** wing-ui and AZ Handsfree read as one product. Every colour, metric and
face comes from one token module a test guards; every number is set in mono; and
the screenshot gate that proves it shows what a human will actually see.

**Why a second plan rather than more tasks on the first:** wave 1's Task 4 shipped a
theme that was never applied and could not have worked (`docs/tech-debt.md` D-19,
D-20). Tasks 14 and 15 of that plan are still open and are folded in at the end here.
Wave 1's numbering is preserved; this plan starts at Task 16.

**Spec:** `docs/superpowers/specs/2026-08-25-gui-parity-design.md` (wave 1) plus the
house-style source of truth in `PROJECT005-AZ-handsfree/docs/spec-ui-mockup.md` —
**branch `main`**; the worktree copy is three commits behind and names the wrong faces.

**Defect ledger:** `docs/tech-debt.md`. Do not restate a fact from it here; link to it.

## Global Constraints

- Baseline suite: `.venv\Scripts\python.exe -m pytest` → **1342 passed, 1 skipped**
  (measured 2026-08-26 on `029e989`). Never leave it red.
  Do **not** add `-q`: `pyproject.toml` already sets it, and `-qq` suppresses the
  summary line entirely — which is why two earlier runs appeared to report nothing.
- No scattered `setStyleSheet()`. One generated stylesheet, one token module.
- ~200-line file ceiling; split by responsibility.
- UTF-8 explicit on every read/write.
- Icons only via `qtawesome`; no emoji.
- Commit style: short imperative sentences.

## The one rule this plan exists to install

> Every colour, radius and spacing value in `wing_parser/ui/` comes from
> `wing_parser/ui/theme/tokens.py`. A hex literal anywhere else under
> `wing_parser/ui/` is a test failure, not a variation.

Enforceable from day one at zero cost: the UI currently contains **zero** colour
literals outside `theme.py`, so the scan lands green with an empty allowlist.

---

### Task 16: Vendored faces and a screenshot loop that tells the truth

**Why first:** every later task is judged by looking at a PNG, and today those PNGs
are not of this app. Measured: `QT_QPA_PLATFORM=offscreen` gives
`QFontDatabase.families() == 0`, so Qt falls back to a stub face and renders the
whole UI in caps. Vendoring the faces fixes it — also measured:
`addApplicationFont()` populates the database even when the system database is
empty (0 families → 3).

**Files:**
- Create `wing_parser/ui/resources/fonts/` — copy from
  `D:/DEV CAVE EP3/PROJECT005-AZ-handsfree/assets/fonts/`:
  `SairaCondensed-SemiBold.ttf`, `SairaCondensed-Bold.ttf`,
  `IBMPlexSans-Regular.ttf`, `IBMPlexMono-Regular.ttf`, `IBMPlexMono-Medium.ttf`,
  plus `OFL-SairaCondensed.txt`, `OFL-IBMPlexSans.txt`, `OFL-IBMPlexMono.txt`
  (the OFL requires the licence travel with the binary).
- Create `wing_parser/ui/theme/fonts.py`
- Modify `wing_parser/ui/__main__.py` — fixed size + scale pinning
- Modify `tests/test_ui_screenshot.py` — replace the byte-size assertion

**Interfaces:**
- `fonts.load()` — idempotent; registers all five files; records which fell back
- `fonts.failed() -> tuple[str, ...]` — empty in a correct build
- `fonts.legend_font(size, bold=True, tracking=...)`, `fonts.mono_font(size, medium=False)`,
  `fonts.base_font(size)`

**Two measured traps this task must handle:**

1. **Both Saira weights register under ONE family.** Measured: file ids 0 and 1 both
   report `['Saira Condensed']`; IBM Plex Mono likewise. The weight therefore cannot
   be chosen by family name — load both files, then request by weight
   (`QFont.Weight.Bold` / `DemiBold`) on the single family. Never hardcode a family
   string; read it back from `applicationFontFamilies(font_id)`. Asking for Bold on
   the wrong family makes Qt synthesise a fake bold, silently.
2. **Tracking is `AbsoluteSpacing`, not `PercentageSpacing`.** Measured: Arial at
   `setPixelSize(20)` with `AbsoluteSpacing 4.0` moved `horizontalAdvance("ABCDE")`
   from 100.0 to 120.0 — exactly 4 px x 5 glyphs, which is what JUCE's
   `withExtraKerningFactor` and CSS `em` both mean. `PercentageSpacing` scales each
   glyph's own advance, so the study's `.20em` is about 144% on a condensed face and
   the figure moves with the font — it must never be written as a constant.

- [ ] **Step 1: Failing tests** — new file `tests/test_ui_house_style.py`

```python
import pytest

pytest.importorskip("PySide6.QtWidgets")


def test_every_face_is_vendored_rather_than_resolved_from_the_machine(qt_app):
    """A missing font does not fail at runtime -- it silently falls back.
    This is the only way to tell a vendored face from a substitution."""
    from wing_parser.ui.theme import fonts
    fonts.load()
    assert fonts.failed() == (), f"fell back to system faces: {fonts.failed()}"


def test_the_licences_ship_beside_the_faces():
    from wing_parser.ui.theme.paths import resource_path
    folder = resource_path("fonts")
    assert {p.name for p in folder.glob("*.ttf")} == {
        "SairaCondensed-SemiBold.ttf", "SairaCondensed-Bold.ttf",
        "IBMPlexSans-Regular.ttf",
        "IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf",
    }
    assert len(list(folder.glob("OFL-*.txt"))) == 3


def test_bold_is_a_real_face_not_a_synthesised_one(qt_app):
    from PySide6.QtGui import QFontInfo
    from wing_parser.ui.theme import fonts
    bold = fonts.legend_font(14.0, bold=True)
    assert QFontInfo(bold).weight() == bold.weight()


def test_tracking_adds_the_studys_em_per_glyph(qt_app):
    from PySide6.QtGui import QFontMetricsF
    from wing_parser.ui.theme import fonts, tokens
    sample = "ACTIVE NOTCHES"
    plain = fonts.legend_font(tokens.CAPTION_SIZE, tracking=0.0)
    tracked = fonts.legend_font(tokens.CAPTION_SIZE, tracking=tokens.TRACK_CAPTION)
    delta = (QFontMetricsF(tracked).horizontalAdvance(sample)
             - QFontMetricsF(plain).horizontalAdvance(sample))
    expected = tokens.TRACK_CAPTION * int(tokens.CAPTION_SIZE + 0.5) * len(sample)
    assert abs(delta - expected) < 0.6
```

  And replace the assertion in `tests/test_ui_screenshot.py`. The current one cannot
  fail: measured, an empty 1280x760 widget grabs to **4575 bytes**, 4.5x the
  1000-byte threshold (600x400 gives 1608 B, 1440x920 gives 6089 B). Assert pixels:

```python
def test_every_page_renders_in_the_house_palette(tmp_path, qt_app, vu_path,
                                                 monkeypatch):
    """The assertion that would have caught theme.apply() having no caller."""
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from PySide6.QtGui import QImage
    from wing_parser.ui.__main__ import main
    from wing_parser.ui.theme import tokens

    out = tmp_path / "shots"
    assert main(["--screenshot", str(out), str(vu_path)]) == 0
    house = set(tokens.COLOURS.values())
    for key in ("doctor", "overview", "channels", "routing", "diff", "import_"):
        image = QImage(str(out / f"{key}.png"))
        assert not image.isNull()
        assert (image.width(), image.height()) == (1280, 760)
        sampled = {image.pixel(x, y) & 0xFFFFFF
                   for x in range(0, image.width(), 97)
                   for y in range(0, image.height(), 89)}
        assert len(sampled) >= 3, f"{key}.png is one flat colour"
        assert len(sampled & house) >= 2, f"{key}.png carries no house token"
```

- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement.** `fonts.py` per the interfaces above. In `__main__.py`,
  when `--screenshot` is given and **before** `QApplication` is constructed,
  `os.environ.setdefault("QT_SCALE_FACTOR", "1")` and
  `setdefault("QT_ENABLE_HIGHDPI_SCALING", "0")` — Qt reads them at construction,
  not later. Add `window.setFixedSize(1280, 760)` before the grab loop so frames
  compare across machines.
- [ ] **Step 4:** PASS + full suite · **Commit** — `Vendor the three house faces and make the screenshot loop truthful`
- [ ] **Step 5:** Run `--screenshot` and **look at the six PNGs**. They must now show
  normal mixed-case text. Attach them to the task report.

---

### Task 17: The token module and a generated stylesheet

**Files:**
- Create `wing_parser/ui/theme/{tokens,qss,palette,paths,install,__init__}.py`
- Delete `wing_parser/ui/theme.py` — the package re-exports its three public names,
  so `tests/test_ui_theme.py` keeps importing them
- Rewrite `wing_parser/ui/resources/theme.qss` as a `$token` template
- Modify `tests/test_ui_theme.py` — its `"@" in qss` assertion dies here, same commit

**Interfaces:**
- `tokens.COLOURS: dict[str, int]` — 19 entries as `0xRRGGBB` **ints, not `#` strings**,
  so the no-hex scan runs with an empty allowlist and even this file cannot cheat
- `tokens.METRICS`, `tokens.*_SIZE`, `tokens.TRACK_*`
- `qss.build() -> str` — `string.Template(...).substitute(mapping())`.
  **`substitute`, never `safe_substitute`**: a `$typo` must raise at startup rather
  than ship a literal `$typo` into a rule Qt then discards with no diagnostic
- `theme.apply(app)` — idempotent, guarded by an app property because the suite
  shares one `QApplication`. Order inside: style, `fonts.load()`, `app.setFont`,
  `app.setPalette`, `qtawesome.set_global_defaults`, `app.setStyleSheet`.
  It must stay called **before** `MainWindow` is constructed — qtawesome resolves an
  icon's colour from the application palette at icon-construction time, and
  `MainWindow.__init__` builds six sidebar icons.

**The palette** (from `spec-ui-mockup.md` section 2, branch `main`):

```
background 0x0A0B0D   panel   0x131519   raise_  0x1B1E24   well    0x0C0E11
border     0x2B2F37   shade   0x060709   grid    0x1D2128
text       0xE8EAED   dim     0x868D98   faded   0x5C636E
accent     0xFF9F1C   warn    0xFFC24D   ok      0x6EE7A0   danger  0xFF5A4E
trace      0xFFB552   peak    0xDDE6F0   marker  0xFF9F1C
cooling    0xC9D1D9   settled 0x5FC9FF
```

Keep the tokens this app has no consumer for (`trace`, `grid`, `peak`, `marker`,
`cooling`, `settled`). The shared table is the point, and a parity test asserts both
apps carry the identical set, so drift shows up in one place.
`raise_` carries the trailing underscore because `raise` is a Python keyword.

The neutrals are warm graphite, deliberately **not** blue-black. Handsfree's reason
holds here: blue-black plus one bright accent is the look every dark audio tool
already has, and next to real gear it reads cold and screeny.

**Severity mapping, with its gap stated rather than papered over:**
`error -> danger`, `warning -> warn`, `info -> dim`. `ok` is reserved for one state
and `accent` is THE accent, so **`info` gets no hue of its own** — that is the
correct answer, not a compromise. Layers (`base`/`toanaz`/`show`) get **no colour at
all**; they are a ghost chip in `faded`. Three more hues would wreck the discipline
that makes the palette readable at a glance.

- [ ] **Step 1: Failing tests** — add to `tests/test_ui_house_style.py`

```python
import re
from pathlib import Path

import wing_parser.ui as ui_package

UI_ROOT = Path(ui_package.__file__).resolve().parent
THEME_DIR = UI_ROOT / "theme"

# EMPTY BY DESIGN. tokens.py holds ints and theme.qss holds $placeholders,
# so even the theme package would pass this scan. If this ever needs an
# entry, the port has gone wrong -- fix the source, do not widen the rule.
ALLOWED: set[Path] = set()

LITERALS = (
    re.compile(r"#[0-9A-Fa-f]{3}\b|#[0-9A-Fa-f]{6}\b"),
    re.compile(r"\brgba?\s*\(\s*\d"),
    re.compile(r"\bQColor\s*\(\s*[\d\"']"),      # QColor(255,159,28) has no '#'
    re.compile(r"\bQt\.GlobalColor\."),
)


def _sources():
    for path in sorted(UI_ROOT.rglob("*")):
        if not path.is_file() or path.suffix not in (".py", ".qss"):
            continue
        if "__pycache__" in path.parts:
            continue
        if THEME_DIR in path.parents or path in ALLOWED:
            continue
        yield path


def test_no_colour_literals_outside_the_theme_package():
    offenders = []
    for path in _sources():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for pattern in LITERALS:
                hit = pattern.search(line)
                if hit:
                    offenders.append(f"{path.relative_to(UI_ROOT)}:{number}: {hit.group(0)}")
    assert offenders == [], "colour literals outside theme/:\n  " + "\n  ".join(offenders)


def test_the_scan_actually_reaches_the_pages():
    """A scan that walks nothing passes forever."""
    names = {p.name for p in _sources()}
    assert {"main_window.py", "overview_page.py", "settings_dialog.py"} <= names
    assert len(names) >= 20


EXPECTED = {
    "background": 0x0A0B0D, "panel": 0x131519, "raise_": 0x1B1E24,
    "well": 0x0C0E11, "border": 0x2B2F37, "shade": 0x060709,
    "text": 0xE8EAED, "dim": 0x868D98, "faded": 0x5C636E,
    "accent": 0xFF9F1C, "warn": 0xFFC24D, "ok": 0x6EE7A0,
    "danger": 0xFF5A4E, "trace": 0xFFB552, "grid": 0x1D2128,
    "peak": 0xDDE6F0, "marker": 0xFF9F1C, "cooling": 0xC9D1D9,
    "settled": 0x5FC9FF,
}


def test_palette_matches_the_approved_table():
    """A change here means ToanAZ re-approved the palette. Not a broken test."""
    from wing_parser.ui.theme import tokens
    assert tokens.COLOURS == EXPECTED


def test_the_stylesheet_is_fully_substituted_and_declares_no_type():
    from wing_parser.ui.theme import load_stylesheet
    qss = load_stylesheet()
    assert "$" not in qss, "an unsubstituted $token reached the stylesheet"
    assert "var(--" not in qss, "Qt QSS has no CSS custom properties -- tech-debt D-20"
    assert "#0a0b0d" in qss
    for banned in ("font-family", "font-size", "font-weight", "font:"):
        assert banned not in qss, (
            f"{banned} in theme.qss: a QSS font rule can override the QFont that "
            "carries the tracking, and Qt QSS has no letter-spacing to replace it."
        )


def test_the_type_scale_keeps_the_studys_ordering():
    """Pin the ratios, not the pixels -- a size tweak stays a tweak."""
    from wing_parser.ui.theme import tokens as t
    assert t.SWITCH_SIZE > t.BRAND_SIZE > t.CAPTION_SIZE > t.COLUMN_SIZE > t.HINT_SIZE
    assert t.TABLE_SIZE < t.BASE_SIZE
    assert t.TRACK_CAPTION > t.TRACK_COLUMN > t.TRACK_SWITCH
```

- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement.**
- [ ] **Step 4:** PASS + full suite · **Commit** — `Put every colour behind one token table and generate the stylesheet`
- [ ] **Step 5:** Screenshot all six pages and look. The app is dark from here on.

---

### Task 18: Style the shell against the token table

**Files:** `wing_parser/ui/resources/theme.qss`, `theme/proxy_style.py`, `theme/widgets.py`

One surface per commit, screenshot after each: containers, then tables and headers,
then inputs, then sidebar, then splitters and scrollbars, then dock/menus/dialogs.

**Three things QSS alone cannot do, and their mechanism:**

| Need | Mechanism |
|---|---|
| A visible focus ring | `QProxyStyle.drawPrimitive` on `PE_FrameFocusRect`. Qt draws it from the **style**, not the stylesheet, so Fusion's dotted OS rect survives every QSS rule and reads as a rendering fault on graphite. |
| Full-row selection in item views | `styleHint(SH_ItemView_ShowDecorationSelected) -> 1` |
| Uppercase tracked captions | `Caption(QLabel)` + `fonts.legend_font()`. Qt QSS has neither `text-transform` nor `letter-spacing`. |

**The `azStyle` idiom** — the direct port of the handsfree property trick. Qt resolves
a `[azStyle="..."]` selector **once, at polish**, so `setProperty` on a live widget is
invisible without the unpolish/polish pair:

```python
def set_style(widget, style: str | None) -> None:
    widget.setProperty("azStyle", style)
    widget.style().unpolish(widget)
    widget.style().polish(widget)
    widget.update()
```

**Destructive controls:** outline only, filling on hover — never a solid slab.
Handsfree's reason applies unchanged: a destructive button that looks like every
other button is one somebody eventually hits by accident.

**Sidebar:** the transport lamp rotated ninety degrees — `raise_` fill plus a 3 px
`accent` left edge on the live page, rows at least `touch_target` tall, label in the
tracked legend face, icon in `dim`.

- [ ] Screenshot-driven rather than test-driven: each commit ends with a PNG.
- [ ] Full suite green after each commit.
- [ ] **Commit** per surface — e.g. `Style the sidebar as the transport lamp rotated`

---

### Task 19: The three UX defects the rendered frames exposed

None of these is a styling question; all three are behaviour. Found by rendering the
six pages on the `windows` platform and looking at them.

**19a — Doctor: the verdict controls are live with nothing selected.**
The three verdict buttons and the Note field are enabled before any finding is
chosen, so pressing one records a verdict against nothing. Disable them until a
finding is selected, and select the first row in `set_session` — which also fills
the detail pane and removes the empty state that currently reads as broken.

**19b — Overview: the seven counts are read-only `QLineEdit`s.**
They look exactly like editable fields. A number that cannot be edited must not look
like an input. Replace with a legend plus a mono value. This is an affordance defect,
not a decoration one.

**19c — Import: a four-step wizard with no step indicator, and a 560 px void.**
Add a read-only step rail (`Pick / Mapping / Vocabulary / Save`) reusing the segmented
primitive, and a resting-state sentence in the workbook pane. Add the "no API key
configured" state with a route to Settings — the whole assisted path depends on it
silently today.

- [ ] **Step 1: Failing tests** — one per defect: the verdict bar is disabled before
      selection and enabled after; the Overview count widget is a `QLabel`, not a
      `QLineEdit`; the import step rail reports step 0 and the resting text is non-empty.
- [ ] **Step 2: Run** → FAIL · **Step 3: Implement** · **Step 4:** PASS + suite
- [ ] **Commit** — three commits, one per defect.

---

### Task 20: Middle elision and mono numerals

Both tables truncate at the **end**, which throws away the discriminating part:
`"...sends post-fader to bu..."` loses the bus number; `unknown.bare_...` loses the
class. Handsfree's rule: elide in the **middle**, protecting the last two characters
— "Ana...1" is readable, "Analogue" twice is not.

`QFontMetrics.elidedText(Qt.ElideMiddle, ...)` elides in the middle but does not
guarantee the two tail characters, so port the hand-rolled loop for identifier-shaped
values and use Qt's for prose.

Every number — fader dB, counts, channel numbers, magnitudes, `ch.1.send.8` — is set
in `fonts.mono_font()` and right-aligned, so columns compare down the page.

- [ ] **Step 1: Failing tests** — `elide_middle("Analogue 1", width).endswith("e 1")`;
      a delegate test that the fader column uses the mono family.
- [ ] **Steps 2-4** as above · **Commit** — `Elide in the middle and set every number in the mono face`

---

### Task 21: Keyboard and persistence

ToanAZ ruled both on 2026-08-26. The app currently has **no** shortcuts at all
(`docs/tech-debt.md` D-23).

- Accelerators: `Ctrl+O`, `Ctrl+Shift+S`, `Ctrl+Z`, `Ctrl+1` through `Ctrl+6` for the
  six pages, `Esc` closes a dialog, `F5` re-analyses.
- Explicit tab order per page; the focus ring from Task 18 makes it visible.
- Persist window geometry, last page and a recent-files list via `QSettings` or a JSON
  file under `config.knowledge_dir()`, with `File > Recent`.

- [ ] **Step 1: Failing tests** — each accelerator resolves to its action; geometry
      survives a save/restore round trip.
- [ ] **Steps 2-4** · **Commit** — two commits, keyboard then persistence.

---

### Task 22: Packaging — folds in wave 1's unrun Task 14

- [ ] Add `("../wing_parser/ui/resources", "wing_parser/ui/resources")` to `DATAS`.
      One entry covers qss, fonts and licences, because `resource_path()` maps that
      directory to the same relative position in dev and under `sys._MEIPASS`.
      (`docs/tech-debt.md` D-26)
- [ ] Add `"qtawesome"` to `hiddenimports`. Do **not** add a hook entry — PyInstaller
      already ships `hook-qtawesome.py`.
- [ ] Fix the false docstring carried over into `wing_parser/ui/theme/paths.py`
      (`docs/tech-debt.md` D-16).
- [ ] Resolve the anthropic contradiction and rewrite the now-false justification
      comment in the spec file (`docs/tech-debt.md` D-27 — **needs ToanAZ**).
- [ ] Fold `packaging/wing-ui-debug.spec` into the tracked spec or delete it; it is an
      untracked copy that now has to be edited twice (`docs/tech-debt.md` D-28).
- [ ] Build: `pyinstaller packaging\wing-ui.spec --noconfirm` from the repo root.
- [ ] **Launch the exe, screenshot all six pages from it, and hand them to ToanAZ.**
      This is the standing done gate: no page is finished until he has seen it rendered
      by the packaged build. A dev run proves nothing about the bundle.
- [ ] **Commit** — `Ship the theme resources in the bundle and verify the exe by eye`

---

### Task 23: Close the paper trail — folds in wave 1's unrun Task 15

- [ ] `docs/ROADMAP.md` — add the wave row to section 3 and to the paperwork table.
      The file calls itself the single source of truth and has no row for this work.
- [ ] `AGENTS.md` — the `pyside6-ui-quality` citation points at a skill that does not
      exist on this machine (`docs/tech-debt.md` D-22). Repoint it at the house-style
      spec, and add handsfree's rule: **GUI work is not reported without a picture.**
- [ ] `README.md` section "Desktop app" — still describes the pre-wave doctor-only app.
- [ ] `docs/user-manual/` — add pointers to the new pages.
- [ ] `docs/tech-debt.md` — close every item this plan fixed, each with the **output**
      of its close command. Closing without output is a wish, not a closure.
- [ ] Update the SDD ledger: it still ends at Task 12 and never recorded Task 13.
- [ ] Write `docs/handoff/2026-08-26-gui-house-style-complete.md`.
- [ ] **Commit** — `Sync the paper trail for the house style wave`

---

## Order, and why

16, 17, 18, 19, 20, 21, 22, 23.

Task 16 is first because everything after it is judged by looking at a picture, and
today the picture is not of this app. Task 17 before 18 because a stylesheet without
a token table is the defect wave 1 already shipped once. Tasks 19 to 21 are behaviour
and could run in any order; 19 goes first because its three fixes are the cheapest
visible improvements in the plan.

## The risk that will bite, and its mitigation

**Converting `QGroupBox` to a `Panel` widget in Task 18 will break tests that reach
widgets structurally.** Four pages build `QGroupBox` and hold them as attributes.

Before touching any page, run:

```
grep -n "QGroupBox\|findChild\|itemAt\|children()" tests/test_ui_*.py
```

Then make `Panel` a **subclass of `QGroupBox`** so `findChild(QGroupBox, ...)` still
hits, keep every public attribute name byte-identical, and convert one page per commit
with the full suite in between.

Related, and worth doing first: `docs/tech-debt.md` D-15 — the import tests reach the
private `_result` and `_directory` attributes. Route them through the existing public
seams before the theme work touches those pages.
