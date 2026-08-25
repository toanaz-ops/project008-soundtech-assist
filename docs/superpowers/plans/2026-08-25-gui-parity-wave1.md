# GUI Parity Wave 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every completed capability behind a button in wing-ui: sidebar shell with Doctor/Overview/Channels/Routing/Diff/Import pages, an ingest wizard over G2a+G2b, a Settings dialog for each user's own AI key, themed per `pyside6-ui-quality`, packaged and visually verified as an .exe.

**Architecture:** Sidebar (`QListWidget`) + `QStackedWidget`; the existing doctor body moves verbatim into `DoctorPage`. Scene computation is extracted into non-Qt modules (`wing_parser/ui/data.py`, `wing_parser/cli/diffcore.py`, `wing_parser/ui/import_controller.py`) consumed by both CLI renderers and Qt pages. UI never shells out to the CLI.

**Tech Stack:** Python, PySide6, qfluentwidgets (PySide6-Fluent-Widgets), qtawesome, pytest + pytest-qt (offscreen), PyInstaller.

**Spec:** `docs/superpowers/specs/2026-08-25-gui-parity-design.md`

## Global Constraints

- Baseline suite: `.venv\Scripts\python.exe -m pytest -q` → **1271 passed, 21 skipped**. Never leave it red.
- Offline first: no test opens a socket; no new network surface except the explicit Settings "Test connection" button (never called in tests against a real API).
- No scattered `setStyleSheet()` — all styling lives in `wing_parser/ui/resources/theme.qss`. Rule goes into repo `AGENTS.md` (Task 4).
- All new user-facing strings go through `wing_parser/ui/texts.py` (Task 3).
- UTF-8 explicit on every file read/write (`encoding="utf-8"`).
- ~200-line file ceiling; split by responsibility.
- Icons only via `qtawesome`; no emoji in UI.
- Layouts in Python code; no `.ui` XML files.
- Commit style matches the repo: short imperative sentences ("Add the routing page").
- Run tests from repo root with the main checkout's interpreter: `.venv\Scripts\python.exe -m pytest`.

## Fixtures available (tests/conftest.py)

- `vu_path` — `user-files/example-Vu.snap`, the standard sample scene.
- `factory_path` — `user-files/factory-scene.snap`.
- `qt_app` — session QApplication, `importorskip` PySide6 (suite stays green without the ui extra).
- `_mutated_scene(vu_path, tmp_path, mutate)` helper — mutated copy for diff tests.
- `_isolated_knowledge_dir` (session, autouse) — `config.knowledge_dir()` points at a throwaway tmp dir during every test; anything Settings writes there is disposable.

## Key existing interfaces (verified by reading the code)

- `Session.scene: WingScene` — re-derived after every repair; always current.
- `WingScene`: `.source`, `.version.type_id/.label`, `.anomalies`, `.channels() -> tuple[Channel]`, `.routing.summary()` (dataclass with `.live_channel_count`), `.unclassified()`, `.channel(n) -> Channel` (raises KeyError), `.diff(other) -> tuple[Change]`.
- `query.diff.Change`: frozen dataclass `(path: str, before: Any, after: Any, magnitude: float | None)`.
- `Channel`: `.number .name .muted .fader_dB .source_type.kind/.confidence/.origin .proc_chain .tap_point .scene_safe .dcas .mute_groups .source .effective_polarity .filter .eq .sends` (all rendered by `render.channel_detail`).
- `render.level(db: float) -> str` — formats `-inf` sentinel.
- Provider layer (`classifier/provider.py`): `ProviderConfig(name, model, api_key_env, base_url, api_key)`, `load_config(explicit|None)`, `make_provider(config)`, `complete_json(provider, system, user, schema)`, `ProviderError`, `ENV_VAR = "WING_PROVIDER_CONFIG"`; defaults in `_NAME_DEFAULTS` keyed `"anthropic"` / `"openai-compat"`.
- Ingest: `sample.sample_workbook(path, *, max_sheets=6, sample_rows=20) -> tuple[SheetSample(name, lines)]`; `suggest.propose_mapping(xlsx, provider) -> MappingProposal(sheet, header_row, columns: dict, headers: dict, problems: tuple)`; `mapping.RawMapping(source, sheet, header_row, columns, headers)`; `mapping.resolve_columns(raw, headers, last_column)`; `sheet.read_sheet(xlsx, sheet_name|None, header_row) -> read(.rows .headers .last_column .blank_rows)`; `build.build(rows, resolved, lookup, blank_rows=0, headers=...) -> result(.segments .comments...)`; `emit.render(show, result, proposals|None) -> str`; `guess.unresolved_terms(result) -> tuple[str]`; `guess.propose_term(term, context_lines, provider) -> Classification|None`; `classifier.cache.load()`, `cache.remember(term, "cuesheet", classification, directory=None)`; `classifier.normalize.clean(term)`; `classifier.llm.kill_switch_on()`.
- Real sheets committed: `tests/data/*.xlsx` (vivo, BIDV). `tests/test_g2b_acceptance.py` pins: BIDV proposal `header_row: 5, title: E`; vivo chooses sheet `Rundown`. **Read that test before Task 10** for the exact filenames and the fake-provider pattern used there and in `tests/test_ingest_wizard.py`.

---

### Task 1: Non-Qt scene view data (`ui/data.py`)

**Files:**
- Create: `wing_parser/ui/data.py`
- Test: `tests/test_ui_data.py`

**Interfaces:**
- Produces (used by Tasks 6–9):
  - `ChannelRow` frozen dataclass: `(number: int, name: str, kind: str, confidence: float, fader_dB: float, muted: bool)`
  - `summarize(scene) -> dict` with keys `source: str, version: str, counts: dict[str,int], live: int, named: int, anomalies: int`
  - `channel_rows(scene) -> tuple[ChannelRow, ...]` ordered by number
  - `channel_detail_rows(channel) -> list[tuple[str, str]]`
  - `routing_view(scene) -> tuple[list[tuple[str, str]], list[str]]` (summary pairs, unclassified strings)

- [ ] **Step 1: Write failing tests**

```python
"""Non-Qt scene views backing the new pages."""

from wing_parser.ui.data import (
    channel_detail_rows,
    channel_rows,
    routing_view,
    summarize,
)


def test_summarize_counts_a_real_scene(vu_path):
    from wing_parser import WingScene

    info = summarize(WingScene.load(vu_path))
    assert info["counts"]["channels"] > 0
    assert info["counts"]["mains"] >= 1
    assert isinstance(info["live"], int)
    assert info["named"] <= info["counts"]["channels"]
    assert isinstance(info["anomalies"], int)


def test_channel_rows_are_ordered_and_typed(vu_path):
    from wing_parser import WingScene

    rows = channel_rows(WingScene.load(vu_path))
    assert rows
    numbers = [row.number for row in rows]
    assert numbers == sorted(numbers)
    assert all(isinstance(row.kind, str) for row in rows)


def test_channel_detail_pairs_cover_the_cli_fields(vu_path):
    from wing_parser import WingScene

    scene = WingScene.load(vu_path)
    pairs = dict(channel_detail_rows(scene.channel(1)))
    assert "Fader" in pairs
    assert "Type" in pairs


def test_routing_view_pairs_and_unclassified(vu_path):
    from wing_parser import WingScene

    pairs, unclassified = routing_view(WingScene.load(vu_path))
    assert any(label == "Live channels" for label, _ in pairs)
    assert isinstance(unclassified, list)
```

- [ ] **Step 2: Run** `.venv\Scripts\python.exe -m pytest tests/test_ui_data.py -v` → FAIL (module missing)

- [ ] **Step 3: Implement** `wing_parser/ui/data.py`

```python
"""Scene facts shaped for tables. No Qt here.

The CLI renders the same facts as text (render.scene_overview /
render.channel_detail / render.routing); these functions are the
structured half so the desktop app never shells out to the CLI.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, is_dataclass

from wing_parser.cli.render import level


@dataclass(frozen=True)
class ChannelRow:
    number: int
    name: str
    kind: str
    confidence: float
    fader_dB: float
    muted: bool


def summarize(scene) -> dict:
    counts = {
        "channels": len(scene.channels()),
        "buses": len(scene.buses()),
        "mains": len(scene.mains()),
        "matrices": len(scene.matrices()),
    }
    return {
        "source": str(scene.source),
        "version": f"{scene.version.type_id} / {scene.version.label}",
        "counts": counts,
        "live": scene.routing.summary().live_channel_count,
        "named": len([ch for ch in scene.channels() if ch.name.strip()]),
        "anomalies": len(scene.anomalies),
    }


def channel_rows(scene) -> tuple[ChannelRow, ...]:
    return tuple(
        ChannelRow(
            number=ch.number,
            name=ch.name,
            kind=ch.source_type.kind,
            confidence=ch.source_type.confidence,
            fader_dB=ch.fader_dB,
            muted=ch.muted,
        )
        for ch in sorted(scene.channels(), key=lambda c: c.number)
    )


def channel_detail_rows(channel) -> list[tuple[str, str]]:
    """Label/value pairs mirroring render.channel_detail, line for line."""
    st = channel.source_type
    rows = [
        ("Name", repr(channel.name)),
        ("Type", f"{st.kind} (confidence {st.confidence:.2f}, {st.origin})"),
        ("Fader", level(channel.fader_dB)),
        ("Muted", str(channel.muted)),
        ("Chain", " -> ".join(channel.proc_chain) or "(none)"),
        ("Tap point", str(channel.tap_point)),
        ("Scene safe", str(channel.scene_safe)),
        ("DCAs", str(channel.dcas or "(none)")),
        ("Mute groups", str(channel.mute_groups or "(none)")),
        ("Polarity (effective)", str(channel.effective_polarity)),
        ("HPF", f"{'on' if channel.filter.low_cut_on else 'off'} "
                f"{channel.filter.low_cut_hz:.0f} Hz "
                f"{channel.filter.low_cut_slope} dB/oct"),
    ]
    source = channel.source
    rows.append(
        ("Source", "not patched" if source is None else
         f"{source.group}:{source.index}  gain {source.gain_dB:.1f} dB  "
         f"phantom={source.phantom}  polarity={source.polarity}")
    )
    eq = channel.eq
    if eq.bands is None:
        rows.append(("EQ", f"{eq.model} (no descriptor — bands unparsed)"))
    else:
        rows.append(("EQ", eq.model))
        for band in eq.bands:
            rows.append((
                f"EQ band {band.name}",
                f"{band.gain:.1f} dB  {band.freq:.1f} Hz  Q {band.q:.2f}",
            ))
    live_sends = [s for s in channel.sends if s.on]
    rows.append(("Sends", f"{len(live_sends)} active"))
    for send in live_sends:
        rows.append((f"Send -> {send.dest_kind} {send.dest}",
                     f"{level(send.level_dB)}  {send.mode}"))
    return rows


def routing_view(scene) -> tuple[list[tuple[str, str]], list[str]]:
    summary = scene.routing.summary()
    if is_dataclass(summary):
        raw = asdict(summary)
        pairs = [(k.replace("_", " ").capitalize(), v) for k, v in raw.items()]
    else:  # defensive: summary was not a dataclass
        pairs = [("Summary", str(summary))]
    pairs = [
        (label, level(value) if label == "Live channels" and not isinstance(value, int) else value)
        for label, value in pairs
    ]
    # Guarantee the stable label the test pins, whatever the field names do.
    live = summary.live_channel_count if hasattr(summary, "live_channel_count") else "?"
    pairs = [(label, value) for label, value in pairs if label != "Live channel count"]
    pairs.insert(0, ("Live channels", live))
    unclassified = [str(item) for item in scene.unclassified()]
    return pairs, unclassified
```

Trim the defensive branches if the real `summary()` makes them dead code —
read `wing_parser/query/routing.py` (or wherever `RoutingFacade.summary`
lives) first and keep only what reality needs.

- [ ] **Step 4: Run** `.venv\Scripts\python.exe -m pytest tests/test_ui_data.py -v` → PASS
- [ ] **Step 5:** `.venv\Scripts\python.exe -m pytest -q` → still 1271+ passed
- [ ] **Step 6: Commit** — `git add wing_parser/ui/data.py tests/test_ui_data.py` → `git commit -m "Add non-Qt scene view data for the new pages"`

---

### Task 2: Diff core (`cli/diffcore.py`)

**Files:**
- Create: `wing_parser/cli/diffcore.py`
- Test: `tests/test_diffcore.py`

**Interfaces:**
- Consumes: `WingScene.diff(other) -> tuple[Change(path, before, after, magnitude)]`
- Produces (Task 9): `DiffRow(path: str, before: str, after: str, magnitude: float | None)`, `diff_rows(before_scene, after_scene) -> tuple[DiffRow, ...]` naturally sorted by path.

- [ ] **Step 1: Failing tests**

```python
"""Structured diff rows for the Diff page."""

from wing_parser.cli.diffcore import diff_rows


def _scene(path):
    from wing_parser import WingScene

    return WingScene.load(path)


def test_a_mutation_yields_rows(vu_path, tmp_path):
    import json

    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"][0]["mix"]["fader"] = -13.0  # any visible change
    out = tmp_path / "mutated.snap"
    out.write_text(json.dumps(doc), encoding="utf-8")

    rows = diff_rows(_scene(vu_path), _scene(out))
    assert rows
    assert all(row.before != row.after for row in rows)
    paths = [row.path for row in rows]
    assert paths == sorted(paths)


def test_identical_scenes_yield_no_rows(vu_path):
    scene = _scene(vu_path)
    assert diff_rows(scene, scene) == ()
```

If the fixture's JSON path differs (no `doc["ae_data"]["ch"][0]["mix"]["fader"]`),
read how `tests/test_query_diff.py` mutates scenes and copy that mutation instead.

- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement**

```python
"""Diff rows for the GUI: scene.diff() shaped for a table.

render.changes keeps its text job for the CLI; this module adds the
structured twin so the Diff page needs no subprocess and no parsing.
"""

from __future__ import annotations

from dataclasses import dataclass

from wing_parser.cli.render import level


@dataclass(frozen=True)
class DiffRow:
    path: str
    before: str
    after: str
    magnitude: float | None


def _fmt(value) -> str:
    if isinstance(value, float):
        return level(value)
    return str(value)


def diff_rows(before_scene, after_scene) -> tuple[DiffRow, ...]:
    changes = before_scene.diff(after_scene)
    rows = tuple(
        DiffRow(
            path=change.path,
            before=_fmt(change.before),
            after=_fmt(change.after),
            magnitude=change.magnitude,
        )
        for change in changes
    )
    natural = lambda path: tuple(   # noqa: E731 - mirrors render._natural
        int(part) if part.isdigit() else part
        for part in __import__("re").split(r"(\d+)", path)
    )
    return tuple(sorted(rows, key=lambda row: natural(row.path)))
```

Replace the inline `__import__` with a normal `import re` at the top and a
module-level `_natural(path)` function copied from `render._natural`'s shape.

- [ ] **Step 4: Run** → PASS
- [ ] **Step 5:** full suite green
- [ ] **Step 6: Commit** — `git commit -m "Add structured diff rows for the Diff page"`

---

### Task 3: String table (`ui/texts.py`)

**Files:**
- Create: `wing_parser/ui/texts.py`
- Modify: repo `AGENTS.md` is NOT touched here (Task 4 owns it)
- Test: `tests/test_ui_texts.py`

**Interfaces:**
- Produces (Tasks 5–12): `TEXTS: dict[str, str]` and `text(key: str) -> str` that raises `KeyError` on a missing key (a typo'd key must be loud, not shown as "key").

- [ ] **Step 1: Failing test**

```python
"""Every UI string lives in one place for future language switching."""


def test_known_keys_resolve():
    from wing_parser.ui.texts import text

    assert text("app.title") == "wing"
    assert text("page.doctor") == "Doctor"
    assert text("page.overview") == "Overview"
    assert text("page.channels") == "Channels"
    assert text("page.routing") == "Routing"
    assert text("page.diff") == "Diff"
    assert text("page.import") == "Import"
    assert text("empty.open_hint")


def test_missing_key_is_loud():
    import pytest

    from wing_parser.ui.texts import text

    with pytest.raises(KeyError):
        text("no.such.key")
```

- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement** `texts.py` with `TEXTS` seeded with the keys above plus, as later tasks need them, their strings (each task adds only its own keys). `text(key)` is `return TEXTS[key]`.
- [ ] **Step 4: Run** → PASS · full suite green
- [ ] **Step 5: Commit** — `git commit -m "Add the single UI string table"`

---

### Task 4: Theme infrastructure (skill `pyside6-ui-quality`)

**Files:**
- Create: `wing_parser/ui/theme.py`, `wing_parser/ui/resources/theme.qss`, repo-root `AGENTS.md`
- Modify: `pyproject.toml` (`ui` extra)
- Test: `tests/test_ui_theme.py`

**Dependencies:** extend `[project.optional-dependencies] ui` to
`["PySide6>=6.11", "PySide6-Fluent-Widgets>=1.8", "qtawesome>=1.4"]`, then run
`.venv\Scripts\python.exe -m pip install -e ".[ui]"` and paste its tail into
the commit-notes of your final report.

**Interfaces:**
- Produces (Tasks 5–14): `resource_path(name: str) -> Path`, `load_stylesheet() -> str`, `apply(app) -> None` (applies qss + sets Fusion style + default font).

- [ ] **Step 1: Failing test**

```python
"""One stylesheet, tokens, and a bundle-safe resource lookup."""


def test_resource_path_resolves_in_dev():
    from pathlib import Path

    from wing_parser.ui.theme import resource_path

    path = resource_path("theme.qss")
    assert path.exists()
    assert path == Path(path)  # sanity: it is a real path object
    assert "resources" in str(path)


def test_stylesheet_carries_tokens():
    from wing_parser.ui.theme import load_stylesheet

    qss = load_stylesheet()
    assert "#background" in qss or "@" in qss  # token markers survive
    assert len(qss) > 200
```

- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement**

`theme.py`:

```python
"""Bundle-safe resources and the one stylesheet application point.

In a frozen build sys._MEIPASS is the bundle root and the spec maps
wing_parser/ui/resources to the SAME relative position, so one lookup
serves both. Dev root = parents[2] of this file (repo root).
"""

from __future__ import annotations

import sys
from pathlib import Path


def resource_path(name: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return root / "wing_parser" / "ui" / "resources" / name


def load_stylesheet() -> str:
    return resource_path("theme.qss").read_text(encoding="utf-8")


def apply(app) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(load_stylesheet())
```

`theme.qss` — hand-write ONLY the token block and a handful of table/label
polish rules (QFluentWidgets owns the heavy lifting; this file is the
override surface, not the whole look):

```css
/* Design tokens — the only place raw colors appear */
* {
  --background: #fafafa;
  --foreground: #1f1f1f;
  --accent: #0078d4;
}
QWidget { background: var(--background); color: var(--foreground); }
QTableView { alternate-background-color: #f3f3f3; gridline-color: #e0e0e0; }
QHeaderView::section { padding: 4px; border: none; font-weight: bold; }
```

Note: plain Qt qss does not support CSS variables — if `var(--background)`
does not take effect at runtime, substitute literal token values and KEEP the
token comment listing them (verify visually in Task 13's screenshots; adjust
there, not here, once QFluentWidgets is actually rendering).

Repo `AGENTS.md` (create):

```markdown
# Project agent rules

- UI styling: ONE `wing_parser/ui/resources/theme.qss` + the token block in
  it. Never call `setStyleSheet()` inside a widget. Icons come from
  `qtawesome`; never emoji. Follow the `pyside6-ui-quality` skill for any
  PySide6 work.
```

- [ ] **Step 4: Run** → PASS · full suite green (new deps installed must not break the no-extras machines: everything new sits behind the `ui` extra and inside ui-only modules)
- [ ] **Step 5: Commit** — stage `pyproject.toml`, `wing_parser/ui/theme.py`, `wing_parser/ui/resources/theme.qss`, `AGENTS.md`, `tests/test_ui_theme.py` → `git commit -m "Add the theme layer: tokens, one stylesheet, bundle-safe resources"`

---

### Task 5: Sidebar shell + DoctorPage extraction

**Files:**
- Create: `wing_parser/ui/doctor_page.py`, `wing_parser/ui/page_base.py`
- Modify: `wing_parser/ui/main_window.py` (rewrite body), `wing_parser/ui/texts.py` (+page names already added in Task 3)
- Test: `tests/test_ui_shell.py`

**Interfaces:**
- Produces:
  - `page_base.EmptyState(widget_parent_label: str)` → QWidget with centered icon+label+"Open a scene..." QPushButton exposing signal `open_requested`.
  - `DoctorPage(QWidget)` with `set_session(session)`, signals `selected(finding)`, `repaired()`; exposes `.findings_view`, `.detail_panel`, `.verdict_bar` (existing widgets, moved verbatim).
  - `MainWindow`: attribute `pages: dict[str, QWidget]`, method `switch_to(key: str)`, fans `set_session` out to every page on open. Keeps public attrs `findings_view/detail_panel/verdict_bar/session` delegating to the doctor page so existing tests pass unchanged.
  - Page registry order (sidebar): `doctor, overview, channels, routing, diff, import_`. Tasks 6–11 fill placeholders: until built, a page key maps to `EmptyState` with that page's name.

- [ ] **Step 1: Failing tests**

```python
"""The sidebar shell routes sessions to every page."""

import pytest

pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture
def window(qt_app, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.main_window import MainWindow

    return MainWindow(None)


def test_sidebar_lists_six_pages_in_order(window):
    from wing_parser.ui.main_window import PAGE_ORDER

    assert PAGE_ORDER == ["doctor", "overview", "channels", "routing",
                          "diff", "import_"]


def test_switching_changes_the_visible_page(window):
    window.switch_to("overview")
    assert window.stack.currentWidget() is window.pages["overview"]


def test_open_session_fans_out_to_every_page(window, vu_path):
    from wing_parser.ui.session import Session

    window.session = Session.open(vu_path)
    window._refresh()
    for key, page in window.pages.items():
        if hasattr(page, "set_session"):
            pass  # pages without sessions are EmptyState placeholders


def test_doctor_widgets_still_reachable(window):
    assert window.findings_view is window.pages["doctor"].findings_view
```

Extend `test_open_session_fans_out_to_every_page`: give DoctorPage a spy
(capture `set_session` call via monkeypatch) and assert it received the
session.

- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement.** Move `_build_body`'s contents (findings view + detail + verdict bar layout) verbatim into `DoctorPage.__init__`; move `_show_finding` logic there. Rewrite `MainWindow._build_body`:

```python
PAGE_ORDER = ["doctor", "overview", "channels", "routing", "diff", "import_"]

def _build_body(self):
    self.pages = {"doctor": DoctorPage()}
    for key in PAGE_ORDER[1:]:
        empty = EmptyState(text(key.removeprefix("page.").join([]) or key))
        empty.open_requested.connect(self.open_file)
        self.pages[key] = empty          # replaced by Tasks 6-11
    self.stack = QStackedWidget()
    for key in PAGE_ORDER:
        self.stack.addWidget(self.pages[key])
    self.sidebar = QListWidget()
    for key in PAGE_ORDER:
        self.sidebar.addItem(text(f"page.{key.removesuffix('_')}"))
    self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
    self.sidebar.setCurrentRow(0)
    body = QHBoxLayout()
    body.addWidget(self.sidebar)
    body.addWidget(self.stack, stretch=1)
    central = QWidget(); central.setLayout(body)
    self.setCentralWidget(central)
```

Clean up that draft: the `EmptyState` label should be `text(f"page.{key.rstrip('_')}")`;
icons via `qtawesome` (`qta.icon("fa5s.stethoscope")` etc.) set with
`QListWidgetItem.setIcon`. `_refresh` fans out:

```python
for page in self.pages.values():
    if hasattr(page, "set_session"):
        page.set_session(self.session)
```

and keeps updating the Changes dock exactly as today. Keep delegating
properties for `findings_view/detail_panel/verdict_bar` on MainWindow.

- [ ] **Step 4: Run** `pytest tests/test_ui_shell.py tests/test_ui_widgets.py -v` → PASS (old widget tests prove the doctor flow survived the move)
- [ ] **Step 5:** full suite green · **Commit** — `git commit -m "Rebuild the main window as a sidebar shell with the doctor flow as its first page"`

---

### Task 6: Overview page

**Files:**
- Create: `wing_parser/ui/overview_page.py`
- Modify: `wing_parser/ui/main_window.py` (replace placeholder), `texts.py`
- Test: `tests/test_ui_overview.py`

**Interfaces:**
- Consumes: `data.summarize`, `data.channel_rows`, `texts.text`
- Produces: `OverviewPage(QWidget)` with `set_session(session | None)`; shows counts cards + a named-channels table (Number/Name/Fader/Kind).

- [ ] **Step 1: Failing test**

```python
import pytest

pytest.importorskip("PySide6.QtWidgets")


def test_overview_shows_counts_after_open(qt_app, vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser import WingScene
    from wing_parser.ui.overview_page import OverviewPage
    from wing_parser.ui.session import Session

    page = OverviewPage()
    page.set_session(Session.open(vu_path))
    assert page.count_labels["channels"].text().isdigit()
    assert page.channels_model.rowCount() > 0


def test_overview_clears_without_a_session(qt_app, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.overview_page import OverviewPage

    page = OverviewPage()
    page.set_session(None)
    assert page.channels_model.rowCount() == 0
```

- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement.** Count cards = `QGroupBox` grid over `summarize()["counts"]` + live/named/anomalies; channels table = `QTableView` + `QStandardItemModel` fed from `channel_rows` (columns: Number, Name, Fader via `render.level`, Kind). `set_session(None)` clears both. Strings via `texts.py` (`overview.channels`, `overview.live`, …).
- [ ] **Step 4:** PASS + full suite · **Commit** — `git commit -m "Add the Overview page"`

---

### Task 7: Channels page with read-only detail

**Files:**
- Create: `wing_parser/ui/channels_page.py`
- Modify: `main_window.py`, `texts.py`
- Test: `tests/test_ui_channels.py`

**Interfaces:**
- Consumes: `data.channel_rows`, `data.channel_detail_rows`
- Produces: `ChannelsPage(QWidget)` with `set_session`; left = table (Number/Name/Kind/Confidence/Fader/Muted), right = read-only detail pane (label/value rows from `channel_detail_rows`, scrollable). Signal-free: internal selection drives the pane. Double-clicking a row whose finding exists is NOT wired here (doctor owns repairs).

- [ ] **Step 1: Failing test**

```python
import pytest

pytest.importorskip("PySide6.QtWidgets")


def test_selecting_a_row_fills_the_detail_pane(qt_app, vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.channels_page import ChannelsPage
    from wing_parser.ui.session import Session

    page = ChannelsPage()
    page.set_session(Session.open(vu_path))
    page.table.selectRow(0)
    number = page.rows[0].number
    assert f"{number}" in page.detail_title.text()


def test_empty_until_a_session_arrives(qt_app, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.channels_page import ChannelsPage

    page = ChannelsPage()
    page.set_session(None)
    assert page.table.model().rowCount() == 0
    assert page.detail_title.text() == ""
```

- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement** (keep ≤200 lines; split `channel_detail.py` pane widget if needed). Detail title format: `text("channels.title").format(number=..., name=...)`.
- [ ] **Step 4:** PASS + full suite · **Commit** — `git commit -m "Add the Channels page with a read-only channel detail pane"`

---

### Task 8: Routing page

**Files:**
- Create: `wing_parser/ui/routing_page.py`
- Modify: `main_window.py`, `texts.py`
- Test: `tests/test_ui_routing.py`

**Interfaces:**
- Consumes: `data.routing_view`
- Produces: `RoutingPage(QWidget)` with `set_session`; top = summary pairs table, bottom = "Unclassified" list.

- [ ] **Step 1: Failing test**

```python
import pytest

pytest.importorskip("PySide6.QtWidgets")


def test_summary_pairs_land_in_the_table(qt_app, vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.routing_page import RoutingPage
    from wing_parser.ui.session import Session

    page = RoutingPage()
    page.set_session(Session.open(vu_path))
    assert page.summary_model.rowCount() >= 1
    labels = [page.summary_model.item(row, 0).text()
              for row in range(page.summary_model.rowCount())]
    assert "Live channels" in labels


def test_unclassified_list_clears(qt_app, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.routing_page import RoutingPage

    page = RoutingPage()
    page.set_session(None)
    assert page.unclassified_list.count() == 0
```

- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement** (mirror Tasks 6–7 patterns; strings via texts).
- [ ] **Step 4:** PASS + full suite · **Commit** — `git commit -m "Add the Routing page"`

---

### Task 9: Diff page

**Files:**
- Create: `wing_parser/ui/diff_page.py`
- Modify: `main_window.py`, `texts.py`
- Test: `tests/test_ui_diff.py`

**Interfaces:**
- Consumes: `cli.diffcore.diff_rows`, `Session.scene` (left side reflects unsaved journal edits — that is the point)
- Produces: `DiffPage(QWidget)` with `set_session`; controls = "Compare with..." (QFileDialog `.snap`) + Clear; table = Path/Before/After/Magnitude; rows where `magnitude` is not None sort first (largest first), then natural by path. Errors (unreadable file) surface in a message box, never a traceback.

- [ ] **Step 1: Failing tests**

```python
import json

import pytest

pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture
def other_snap(vu_path, tmp_path):
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"][0]["mix"]["fader"] = -13.0
    out = tmp_path / "other.snap"
    out.write_text(json.dumps(doc), encoding="utf-8")
    return out


def test_comparing_two_files_lists_changes(qt_app, vu_path, other_snap,
                                           monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.diff_page import DiffPage
    from wing_parser.ui.session import Session

    page = DiffPage()
    page.set_session(Session.open(vu_path))
    page.compare_with(str(other_snap))       # public seam for the dialog
    assert page.model.rowCount() >= 1


def test_bad_other_file_is_an_error_not_a_crash(qt_app, vu_path, tmp_path,
                                                monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.diff_page import DiffPage
    from wing_parser.ui.session import Session

    page = DiffPage()
    page.set_session(Session.open(vu_path))
    bad = tmp_path / "bad.snap"
    bad.write_text("not json", encoding="utf-8")
    page.compare_with(str(bad))              # must not raise
    assert page.model.rowCount() == 0
    assert page.error_label.text() != ""
```

- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement.** `compare_with(path)` wraps `WingScene.load` in try/except `(OSError, ValueError)` → sets `error_label`, returns. Sorting: `sorted(rows, key=lambda r: (r.magnitude is None, -(r.magnitude or 0)))` then stable-natural by path within groups.
- [ ] **Step 4:** PASS + full suite · **Commit** — `git commit -m "Add the Diff page"`

---

### Task 10: Import controller (non-Qt)

**Files:**
- Create: `wing_parser/ui/import_controller.py`
- Test: `tests/test_import_controller.py`

**Interfaces:**
- Consumes: `sample_workbook`, `propose_mapping`, `RawMapping`, `resolve_columns`, `read_sheet`, `build.build`, `emit.render`, `guess.unresolved_terms`, `guess.propose_term`, `cache.remember`, `kill_switch_on`
- Produces (Task 11 consumes exactly these):
  - `sample(xlsx) -> tuple[SheetSample, ...]`
  - `proposal_for(xlsx, provider_factory) -> MappingProposal | None` — None on kill-switch or any `(ProviderError, ValueError, OSError, zipfile.BadZipFile)`; mirrors `wizard._propose_or_none` minus printing
  - `read_with(xlsx, sheet: str|None, header_row: int, columns: dict, headers: dict) -> tuple[read, resolved]` — builds `RawMapping(source=f"{Path(xlsx).stem} (gui)", ...)`, raises `(OSError, ValueError, sheet.MissingExtra)` untouched
  - `build_result(read, resolved)` — vocabulary from `cache.load()["cuesheet"]`, passes `blank_rows=read.blank_rows, headers=read.headers`
  - `preview_text(xlsx, result) -> str` — `emit.render(Path(xlsx).stem, result, None)`
  - `unresolved(result) -> tuple[str, ...]`
  - `guesses_for(terms, context_by_term, provider_factory) -> list[tuple[str, Classification | None]]` — loops `propose_term`, swallowing per-term exceptions as None entries (UI decides presentation); respects `kill_switch_on()` by returning `[]`
  - `context_for(terms, rows) -> dict[str, list[str]]` — port of `wizard._context_for` (copy, do not import the private)
  - `record_term(term, classification, directory=None)` — `cache.remember(term, "cuesheet", classification, directory=directory)`

- [ ] **Step 1: Failing tests.** Read `tests/test_ingest_wizard.py` and `tests/test_g2b_acceptance.py` FIRST; reuse their fake-provider class and the real BIDV/vivo xlsx paths verbatim. Then write:

```python
"""The GUI's import brain — every decision testable without Qt."""

from pathlib import Path

from wing_parser.ui import import_controller as ic

BIDV = Path("tests/data/BIDV TPHCM - KỊCH BẢN SK YEP 2025..xlsx")


def test_proposal_none_when_kill_switch_on(tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    assert ic.proposal_for(BIDV, None) is None


def test_read_with_resolves_the_real_bidv_sheet():
    read, resolved = ic.read_with(
        BIDV, "KB 8.1", 5,
        {"id": "A", "time": "B", "title": "E"},
        {"performers": "Thực hiện"},
    )
    assert resolved.columns["title"] == "E"      # pinned identically in
    assert read.rows                              # tests/test_g2b_acceptance.py


def test_unresolved_terms_parse_from_comments(monkeypatch, tmp_path):
    from wing_parser.showcontext.ingest import build as build_mod

    # Reuse the synthetic fixture style of tests/test_ingest_build.py:
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    read, resolved = ic.read_with(
        BIDV, "KB 8.1", 5,
        {"id": "A", "time": "B", "title": "E"},
        {"performers": "Thực hiện"},
    )
    result = ic.build_result(read, resolved)
    terms = ic.unresolved(result)
    assert all(isinstance(term, str) and term for term in terms)


def test_guesses_swallow_errors_and_record_only_on_explicit_call(
    tmp_path, knowledge_dir
):
    from wing_parser.classifier.matcher import Classification
    from wing_parser.ui import import_controller as ic

    class DeadProvider:
        def complete_json(self, system, user, schema):
            raise RuntimeError("offline")

    terms = ("ca trống",)
    guesses = ic.guesses_for(terms, {"ca trống": ["row 1: ca trống"]},
                             lambda: DeadProvider())
    assert guesses == [("ca trống", None)]       # error swallowed, not raised


def test_record_term_writes_through_cache(tmp_path):
    from wing_parser.classifier.matcher import Classification

    entry = Classification(kind="music.traditional", confidence=0.9,
                           origin="g2b-assisted")
    ic.record_term("ca trống", entry, directory=tmp_path)
    from wing_parser.classifier import cache

    assert cache.load(directory=tmp_path)["cuesheet"]["ca trống"].kind \
        == "music.traditional"
```

Notes for the implementer: `cache.load`/`cache.remember` accept a
`directory=` (verified in `guess.offer_terms` and conftest's isolated
knowledge dir); if the real signatures differ, match them — do not invent.
The `knowledge_dir` fixture above is just the session autouse fixture's
directory; drop it if unused. If `read.rows` on BIDV is empty because
`resolve_columns` needs headers text rather than letters for some field,
adjust per what `test_g2b_acceptance.py` proves works — its proposals are
the ground truth.

- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement** (~150 lines, pure functions, zero Qt imports)
- [ ] **Step 4:** PASS + full suite · **Commit** — `git commit -m "Add the non-Qt import controller driving the ingest pipeline"`

---

### Task 11: Import page (wizard)

**Files:**
- Create: `wing_parser/ui/import_page.py`
- Modify: `main_window.py`, `texts.py`
- Test: `tests/test_ui_import_page.py`

**Interfaces:**
- Consumes: ALL of Task 10's controller functions.
- Produces: `ImportPage(QWidget)` with `set_session` (accepted but unused — import is scene-independent) and four stacked steps inside the page:
  1. Pick: file picker (.xlsx) + sampler preview pane (`ic.sample`).
  2. Mapping: if `ic.proposal_for(...)` returned a proposal, prefill an editable grid (rows id/time/title → letter; performers/note/sound/lighting/led → header text); badge `text("import.verified")` when `proposal.problems` empty else `text("import.unverified")` + problem list shown. Without a proposal, empty grid + hint to fill manually. Back/Next buttons; Next calls `ic.read_with` and surfaces ValueError in a status label (never a crash).
  3. Terms: for each term from `ic.unresolved(build_result)`, a row with term, context lines, buttons Record/Skip. Record → `ic.record_term` and marks the row recorded. "Load guesses" button runs `ic.guesses_for` and prefills proposed kinds (still requiring explicit Record — the G2b invariant: nothing writes without the click).
  4. Preview & Save: read-only text pane (`ic.preview_text`), Save As… → write `encoding="utf-8"`, refuse silent overwrite via QFileDialog's native confirm.
- Long-running calls (`proposal_for`, `guesses_for`) run under `QApplication.setOverrideCursor` wait cursor + a status label; synchronous is accepted for wave 1 (YAGNI on threads), noted in the page docstring.
- All failures degrade to status-label text; the wizard NEVER tracebacks.

- [ ] **Step 1: Failing tests.** Monkeypatch `ic.proposal_for` / `ic.guesses_for` at the page-module boundary (`import_page.ic` is imported as a module):

```python
import pytest

pytest.importorskip("PySide6.QtWidgets")

BIDV = "tests/data/BIDV TPHCM - KỊCH BẢN SK YEP 2025..xlsx"


@pytest.fixture
def page(qt_app, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui import import_page

    return import_page.ImportPage()


def test_pick_step_advances_to_mapping(page):
    page.pick_file(BIDV)                     # public seam, no dialog
    assert page.step_area.currentIndex() == 1


def test_record_writes_vocabulary_only_on_click(page, tmp_path, monkeypatch):
    """The G2b invariant: nothing writes without the explicit click."""
    from wing_parser.ui import import_page

    recorded = []

    class FakeResult:
        segments = [type("S", (), {"comments": [
            "row 1: could not read performer 'ca trống'"]})()]
        # whatever attributes the term step reads; mirror BuiltSegment shape

    monkeypatch.setattr(import_page.ic, "unresolved",
                        lambda result: ("ca trống",))
    monkeypatch.setattr(import_page.ic, "guesses_for",
                        lambda terms, ctx, factory: [])
    page._directory = tmp_path                # where record_term writes
    page.show_terms_step(FakeResult())        # builds step 3 UI
    page.record_button_for("ca trống").click()
    assert page.term_row_state("ca trống") == "recorded"
    recorded.append("ca trống")               # see assertion below
    assert recorded == ["ca trống"]
```

`show_terms_step`, `record_button_for`, `term_row_state` are the page's
test seams — name them exactly this so the reviewer can find them. The
assertion that matters is behavioural: with NO click (delete the click line),
the vocabulary file must not exist; after the click, `tmp_path`'s
classifier.yaml contains the term. Write both assertions explicitly.

- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement** (~190 lines; extract `terms_step.py` if over)
- [ ] **Step 4:** PASS + full suite · **Commit** — `git commit -m "Add the Import page: mapping proposal, term guessing, preview and save"`

---

### Task 12: Settings dialog

**Files:**
- Create: `wing_parser/ui/settings_dialog.py`
- Modify: `main_window.py` (Tools menu), `texts.py`
- Test: `tests/test_ui_settings.py`

**Design decisions locked here:**
- Config lives at `config.knowledge_dir() / "provider.yaml"`. Saving writes it AND sets `os.environ["WING_PROVIDER_CONFIG"]` to that absolute path immediately, so the running process's next `provider.load_config(None)` picks it up (dev and frozen alike).
- Loading: show effective config from `provider.resolve(provider.load_config(None))`, masking `api_key` (show `••••` + last 4 chars when set).
- Fields: Provider combo (`anthropic` / `openai-compat`), Model, Base URL, API key (QLineEdit, EchoMode Password, placeholder explains the user brings their OWN key), `api_key_env` optional.
- `test_connection` is injectable: `SettingsDialog(probe=None)` where probe takes the written `ProviderConfig` and returns `(ok: bool, message: str)`; default probe builds a provider and pings `complete_json(provider, "You reply ok.", "ping", {"type": "object", "properties": {"ok": {"type": "string"}}, "required": ["ok"]})` inside try/except `(ProviderError, Exception)` → `(False, str(exc))`. Tests inject a fake probe; NO test touches the network.

- [ ] **Step 1: Failing tests**

```python
import os

import pytest

pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture
def knowledge(tmp_path, monkeypatch):
    from wing_parser import config

    monkeypatch.setenv(config.ENV_VAR, str(tmp_path))
    return tmp_path


def test_save_writes_yaml_and_pins_env(qt_app, knowledge, monkeypatch):
    from wing_parser.ui.settings_dialog import SettingsDialog

    dlg = SettingsDialog()
    dlg.fill(name="openai-compat", model="deepseek-chat",
             base_url="https://api.deepseek.com", api_key="sk-test-1234")
    dlg.save()
    text = (knowledge / "provider.yaml").read_text(encoding="utf-8")
    assert "api_key: sk-test-1234" in text
    assert os.environ["WING_PROVIDER_CONFIG"] == str(knowledge / "provider.yaml")


def test_probe_failure_is_reported_not_raised(qt_app, knowledge):
    from wing_parser.ui.settings_dialog import SettingsDialog

    def bad_probe(config):
        raise RuntimeError("no network here")

    dlg = SettingsDialog(probe=bad_probe)
    ok, message = dlg.run_probe()
    assert ok is False
    assert "no network here" in message


def test_existing_config_loads_masked(qt_app, knowledge):
    from wing_parser.ui.settings_dialog import SettingsDialog

    (knowledge / "provider.yaml").write_text(
        "provider: anthropic\nmodel: claude-opus-5\napi_key: sk-secret-abcd\n",
        encoding="utf-8",
    )
    dlg = SettingsDialog()
    assert "abcd" in dlg.key_display.text() and "secret" not in dlg.key_display.text()
```

- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement** (≤180 lines). YAML via ruamel `YAML()` dump (same as `wizard._dump_yaml`). Save restores previous env var on write failure.
- [ ] **Step 4:** PASS + full suite · **Commit** — `git commit -m "Add the Settings dialog: paste your own provider key, test the connection"`

Wire into `MainWindow._build_menus`: Tools → `text("menu.settings")` opening the dialog (modal exec), Help unchanged.

---

### Task 13: Screenshot loop (`--screenshot`)

**Files:**
- Modify: `wing_parser/ui/__main__.py`
- Test: `tests/test_ui_screenshot.py`

**Interfaces:**
- Produces: `wing-ui [--screenshot [DIR]] [file]` — builds the window (opening `file` first when given), switches to each page in `PAGE_ORDER`, grabs `widget.grab()` to `<DIR>/<page>.png`, exits 0 without entering the event loop. DIR defaults to `screenshots/`.

- [ ] **Step 1: Failing test**

```python
import subprocess
import sys


def test_screenshot_flag_writes_pngs(tmp_path, qt_app, monkeypatch, vu_path):
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.__main__ import main

    out = tmp_path / "shots"
    code = main(["--screenshot", str(out), str(vu_path)])
    assert code == 0
    names = {p.stem for p in out.glob("*.png")}
    assert {"doctor", "overview", "channels", "routing", "diff", "import_"} <= names
    assert all((out / f"{n}.png").stat().st_size > 1000
               for n in names)  # blank grabs are ~small; real frames are not
```

- [ ] **Step 2: Run** → FAIL
- [ ] **Step 3: Implement** in `main()`:

```python
parser.add_argument("--screenshot", nargs="?", const="screenshots",
                    metavar="DIR", help="grab one PNG per page and exit")
...
if args.screenshot:
    directory = Path(args.screenshot)
    directory.mkdir(parents=True, exist_ok=True)
    window.show()
    for row, key in enumerate(PAGE_ORDER):
        window.switch_to(key)
        QApplication.processEvents()
        window.grab().save(str(directory / f"{key}.png"))
    return 0
```

(`PAGE_ORDER` imported from main_window; grab the window, not the stack, so
the sidebar is visible for review.)
Then RUN it for real and LOOK at every PNG yourself (you have vision; if the
current runtime lacks image input, spawn a general subagent instructed to
view them). Fix layout crimes now: clipped labels, cramped tables, invisible
focus. This is the loop the `pyside6-ui-quality` skill mandates — repeat
screenshot→look→fix until every page is presentable, and note what you fixed.

- [ ] **Step 4:** PASS + full suite · **Commit** — `git commit -m "Add --screenshot so agents can see the UI they ship"`

---

### Task 14: Packaging + visual verification of the .exe

**Files:**
- Modify: `packaging/wing-ui.spec`
- Test: manual build + smoke (this task's verification IS the artifact)

**Steps (not TDD — the deliverable is a verified binary):**

- [ ] **Step 1: Spec updates.** In `DATAS` add
      `("../wing_parser/ui/resources", "wing_parser/ui/resources")`.
      Extend hiddenimports:
      `collect_submodules("wing_parser") + collect_submodules("qfluentwidgets") + ["qtawesome"]`
      (qtawesome bundles its own fonts and ships a PyInstaller hook; if fonts
      go missing in the exe, add its hook entry explicitly). Keep
      `PySide6.QtWebEngineCore` in EXCLUDES.
- [ ] **Step 2: Build** — `cd "D:\DEV CAVE EP3\PROJECT008-SOUNDTECH-ASSIST"; .venv\Scripts\pyinstaller packaging\wing-ui.spec --noconfirm` (run from packaging/ context as the spec expects: workdir `packaging`, command `.venv\..\..\` adjusted — read the spec header comment and follow it exactly). Paste the build tail.
- [ ] **Step 3: Smoke the exe** — `dist\wing-ui\wing-ui.exe --screenshot dist-shots examples\...` using any real `.snap` from `user-files/`. Expect exit 0 and six PNGs.
- [ ] **Step 4: LOOK at the exe's screenshots** (yourself or a vision subagent — same instruction as Task 13). Blank/unstyled frames mean the datas/MEIPASS wiring is wrong: fix, rebuild, re-shoot. Do not declare done on dev-run beauty alone.
- [ ] **Step 5: Interactive smoke you can hand ToanAZ:** launch `dist\wing-ui\wing-ui.exe` (no args), open a scene via the dialog, visit every page, open Settings. Record anything broken and fix before Step 6.
- [ ] **Step 6: Commit** — `git commit -m "Package the themed app: resources, fluent and icon hooks in the bundle"`

---

### Task 15: Sync the paper trail (rule 12 closeout)

**Files:**
- Modify: `docs/ROADMAP.md` (§3 table gains the GUI-parity row with the real test count; §1 diagram's edit/ui line updated; §4 wave-2 pointer), `memory/MEMORY.md` (entry: wave 1 shipped, what remains), create `docs/handoff/2026-08-XX-gui-parity-wave1-complete.md` (measured acceptance, exe location, pitfalls), `docs/user-manual/README.md` gains pointers to the new pages.

- [ ] **Step 1:** Update ROADMAP §3 + fix any statement the wave made false (grep for "CLI-only", "desktop app only covers").
- [ ] **Step 2:** Handoff lists: baseline vs final test numbers, the exact exe path, the six runnable things ToanAZ can try with expected results (rule 12 item 2), open items (wave 2 live console, i18n, Mac packaging, DeepSeek live smoke still pending his key — now testable IN the app via Settings).
- [ ] **Step 3:** Full suite one last time; paste counts into the handoff.
- [ ] **Step 4: Commit docs** — docs-only staging rules apply → `git commit -m "Sync the roadmap, manual and handoff after GUI parity wave 1"`

## Self-review notes

- Spec coverage: sidebar shell (T5), Overview (T6), Channels (T7), Routing (T8), Diff (T9), Import G2a+G2b (T10–11), Settings + own key + test connection (T12), texts/i18n-readiness (T3), theme/qss/icons/screenshot-loop/AGENTS rule (T4, T13), PyInstaller datas+hooks+exe-tested (T14), acceptance + paperwork (T13–15). Wave-2 scope excluded deliberately.
- Type consistency: `DiffRow`/`ChannelRow` names consistent across T1/T2/T6–9; controller names in T10 match their only consumer T11; `PAGE_ORDER` defined T5, reused T13.
- Known risk called out in-plan: qss lacks CSS variables (T4 note), QFluentWidgets bundling (T14), fixture-path drift for BIDV (T10 directs to the pinning test).
