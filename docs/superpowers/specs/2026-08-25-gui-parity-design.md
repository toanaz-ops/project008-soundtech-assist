# GUI parity for wing-ui — design

**Date:** 2026-08-25 · **Status:** approved in chat by ToanAZ 2026-08-25 ·
**Cycle:** Đợt 1 of 2 (file-based flows) · **Supersedes:** nothing

## Problem

The desktop app covers only the doctor flow (findings / repairs / verdicts).
Everything else shipped so far — analyze, channel detail, routing, diff,
assisted ingest (G2a+G2b), provider configuration — exists only as CLI.
Standing constraint from ToanAZ (2026-08-24): *UI-first — a feature without a
button in wing-ui does not exist.* This cycle brings every completed capability
behind buttons so he can test real results in the packaged app.

## Decisions made with ToanAZ

| Question | Decision |
|---|---|
| Scope | B: two waves. Wave 1 = Import + Analyze/Routing/Channels/Diff. Wave 2 = Live console (`net`). |
| Model assist in UI | Full G2b on UI, plus a Settings screen where each user pastes their own API key. |
| Language | English now; structure strings so a language switch can be added later. |
| Shell | Sidebar navigation (option 3), not tabs or separate windows. |
| Look & feel | Per `pyside6-ui-quality` skill: QFluentWidgets shell, one theme.qss + tokens, qtawesome icons, screenshot loop, PyInstaller datas discipline. |

## Architecture

```
MainWindow
├── Sidebar (QListWidget ~180px, qtawesome icons)
├── QStackedWidget
│   ├── DoctorPage    ← existing body moved verbatim (findings/detail/verdict)
│   ├── OverviewPage  ← summarize(scene)
│   ├── ChannelsPage  ← table + read-only channel detail
│   ├── RoutingPage   ← routing_map(scene)
│   ├── DiffPage      ← diffcore rows, right side = second .snap picker
│   └── ImportPage    ← 4-step ingest wizard
└── Changes dock (bottom, unchanged, app-wide)
```

- UI never shells out to the CLI. Computation is extracted into non-Qt modules
  that both CLI renderers and UI pages consume:
  - `summarize(scene)` extracted from `commands.analyze`
  - `routing_map(scene)` extracted from `commands.routing`
  - `cli/diffcore.py` holding `_diff_sides` logic as structured rows
- Pages receive `set_session(session)`; MainWindow calls all pages on open.
  No page holds its own scene copy. Empty state = "Open a scene..." prompt.
- All new user-facing strings go through `wing_parser/ui/texts.py` (one dict,
  English values today) for future language switching.

## Import wizard (ImportPage)

1. **Pick file** — `.xlsx`; show workbook sampler output (header sample) so the
   operator sees what the proposer saw.
2. **Mapping** — with a configured key: model proposal rendered as an editable
   table, each row labelled verified-by-checker or unverified (unverified rows
   visibly marked, matching the G2b rule). Without a key: pick an existing
   mapping file (pure G2a path).
3. **Vocabulary** — unresolved terms offered one at a time; written to
   vocabulary only on explicit Record click; skipped otherwise.
4. **Preview & save** — show-context JSON preview incl. sound/lighting/led
   fields → Save As `.yaml`.

Reuses `ingest/{sample,suggest,mapping,build,emit}.py`. The CLI wizard stays;
the UI is a second client of the same functions.

## Settings dialog

Menu Tools → Settings: provider (`anthropic` | `openai-compat`), base_url,
model, API key paste field → written to `provider.yaml` under the knowledge
config directory (never hardcoded). A "Test connection" button performs one
small real call and reports the actual result. Each end user brings their own
key.

## Theme & packaging

Per `pyside6-ui-quality`: QFluentWidgets shell components; single theme.qss +
token block; **no scattered setStyleSheet()** (rule also added to repo
AGENTS.md); qtawesome icons; `--screenshot [page]` debug flag that grabs PNGs
and exits. PyInstaller: add qss/fonts/icons to DATAS, read via a
`sys._MEIPASS` helper, add hidden-import hooks for QFluentWidgets and
qtawesome, verify the built exe visually — dev-run styling alone proves
nothing.

## Testing & acceptance

- New logic lives in non-Qt modules → plain pytest like the rest of the suite.
- pytest-qt offscreen tests for every new page incl. empty states.
- Every page screenshotted and visually reviewed before "done".
- Final acceptance: built `.exe` lets ToanAZ open a scene → browse
  Overview/Channels/Routing/Diff → import the real BIDV/vivo sheets from
  `tests/data/` → paste his key in Settings → import with AI assist.
- Suite stays green (1271 passed baseline) plus new tests.

## Out of scope this wave

Live console (`net`) pages — wave 2. Language switching (structure ready).
Mac build (source is portable; needs a Mac to package). E/F roadmap items.
