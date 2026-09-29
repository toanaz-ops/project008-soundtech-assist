# UI bilingual (English / Tiếng Việt) — design

**Status:** built on `feat/ui-bilingual` (2026-09-29); ci_local DAT 2169
tests / 0 fail / 3 skip. Review fixes: Settings probe goes through
`provider.ping_raw` so AI errors reach the translated path; stray English
literals (verdict bar, detail panel, findings headers) moved into
`texts_moved*.py`. Still English by design: `data.py` Channels/Routing
detail labels (B6). **Merged** PR #13 + polish PR #14 (`2830af6`); exe
rebuilt from `main` 2026-09-29, shots `dist-shots/exe-en`, `exe-vi`.
**Source:** ToanAZ 2026-09-29 — "Bao gồm hỗ trợ song ngữ anh/việt". This
overturns wave-4 decision **W1** ("New UI strings are English… a Vietnamese
string table is its own wave") — this is that wave.

## 1. What the user gets

- **Settings ▸ Language**: `English` / `Tiếng Việt`. Default English.
  Persisted in `ui-state.json` (`"language": "en" | "vi"`, `normalize()`
  drops anything else back to `"en"`).
- The choice **applies on the next start** of wing-ui. On change the dialog
  shows one line (in both languages): "Restart wing to apply the new
  language. / Khởi động lại wing để áp dụng ngôn ngữ mới."
- `wing-ui --lang vi|en` overrides the saved choice for one run (used by
  `--screenshot` so both languages can be shot from the exe).

## 2. Decisions (orchestrator, per ToanAZ's no-asking rule)

| # | Decision | Why | If overturned |
|---|----------|-----|---------------|
| B1 | Restart-to-apply, not live retranslation | 304 `text()` call sites set text once at build time; live switching means a retranslate hook in every widget — large, fragile, no show-time value (language is chosen once) | Add `retranslate()` per page; its own wave |
| B2 | Mixer/audio nouns stay English in Vietnamese UI: Channel/Bus/Main/Matrix/DCA/Fader/Mute/Send/Insert/EQ/Gate/Comp/Scene/Snap/OSC/Doctor-page names stay as on the WING desk and in WING-Edit | Vietnamese sound engineers read these in English on the desk every day; translating them makes the app disagree with the console | Edit the VI tables only — no code change |
| B3 | Page tab names translated except proper nouns (Doctor, Console stay) | Same as B2 | Edit VI table |
| B4 | Missing VI key at runtime falls back to English, never raises; a **parity test** makes a missing key a test failure | Show-time robustness + CI catches it | — |
| B5 | Format placeholders (`{file}`, `{seconds}`…) must be identical per key in both languages — tested | A mismatched placeholder is a KeyError at runtime | — |
| B6 | Domain output (Doctor findings/repair prose, classifier reasons, CLI) stays English | It comes from the analysis layer and the CLI, not the UI string table; separate scope | Its own wave |
| B7 | Qt's built-in dialog buttons (QMessageBox Yes/No, QFileDialog) stay OS/Qt default | Qt ships no reliable `qtbase_vi.qm`; our own buttons are translated | Bundle a translator |
| B8 | AI error classes (`provider_errors`) shown in the UI are translated via `ai_error.<code>` keys; `provider_errors._MESSAGES` stays English for the CLI; `OTHER` keeps the provider's own message | UI-only change, CLI unchanged | — |
| B9 | Vendored fonts must render every character used in the VI tables — tested with the real font files | D-51 showed a missing glyph renders as a box | Vendor a font with coverage |

## 3. Shape

- `wing_parser/ui/texts.py` keeps `text(key)` as the single accessor; adds
  `set_language(code)`, `current_language()`, `LANGUAGES = ("en", "vi")`.
- Vietnamese tables: `texts_vi.py`, `texts_console_vi.py`,
  `texts_import_vi.py`, `texts_write_vi.py` (each ≤ 200 lines, mirroring the
  English split).
- Import-time constants built from `text()` (`detail_panel.NO_REPAIR`,
  `diff_page.FILTER`, `import_page.FILTER/SAVE_FILTER`, `menus.FILTER`) become
  lookups at use time, so the language chosen at startup reaches them.
- `__main__.main()` resolves language (`--lang` > `ui-state.json` > `en`) and
  calls `set_language` before importing/building any window.
- Settings row lives in its own small module (settings_dialog.py is at 198/200).

## 4. Acceptance

- Parity test: identical key sets and placeholder sets, EN vs VI, all tables.
- Qt test: build the real `MainWindow` with language `vi`, assert visible
  page tabs / menu / a Settings label are the Vietnamese strings; drive the
  Settings Language combo, assert `ui-state.json` gets `"vi"` and the restart
  note shows.
- Font test: every char in every VI string is supported by each vendored UI
  font that renders body text.
- Suite via `scripts/ci_local.py` → DAT. Exe rebuilt from `main`, screenshots
  `dist-shots/bi-en-*.png` and `bi-vi-*.png`.

## 5. Out of scope

B6, B7. Vietnamese Doctor findings prose is a candidate next wave.
