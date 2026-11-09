# Mixing knowledge library — design (2026-11-09)

Owner request (09/11/2026): a library of mixing knowledge that humans and
agents can browse, search, learn from, add to and edit, with revision
history; every entry cites reputable sources; many illustrations and
collected videos; the basis for the repo's automix. Decisions taken while
the owner is away are in `docs/proposals/2026-11-09-knowledge-library-decisions.md`.

## 1. Store

Schema and layout: `knowledge/library/SCHEMA.md` (the single source of truth;
this spec does not restate it). Taxonomy `topics.yaml`, publisher allow-list
`sources.yaml`, diagram manifest `diagrams.yaml`.

Layers — a shipped layer under a user layer (overlay, nothing is copied):
`wing_parser.config.shipped_library_dir()` is the repo `knowledge/library`
(in a frozen exe, the bundle copy, read-only). `config.library_dir(override=None)`
is the user layer: override → env `WING_LIBRARY_DIR` → frozen:
`USER_DEFAULT / "library"` → repo `knowledge/library` (a frozen exe never
resolves into the bundle temp dir). `LibraryStore(root, shipped_root=None)`
shows shipped entries ∪ user entries, the user copy winning by id; each
`LoadedEntry.layer` is `"shipped"` or `"user"`. With `shipped_root` None or
equal to `root` (dev run from the repo) there is one layer. `topics.yaml` /
`sources.yaml` come from the user root if present, else shipped; `media_file`
tries the user root, then shipped.

Writes (`save`, `retire`, `restore`) always go to the user layer and
`<root>/history/<id>.jsonl`; shipped files are never touched. The first user
save of a shipped entry checks `expected_revision` against the shipped
revision, writes revision shipped+1, and first logs the shipped snapshot as a
history line with `action: "shipped"` so the diff shows the user's change.

## 2. Python API (`wing_parser/library/`, no Qt)

| module | contents |
|---|---|
| `schema.py` | constants (enums, id regex), `load_topics(root)`, `load_publishers(root)` |
| `validate.py` | `Issue(level, code, field, message)`; `validate(entry: dict, *, topics, publishers, media_root) -> list[Issue]`. Codes: `missing-field`, `bad-id`, `bad-topic`, `unsourced`, `bad-source`, `unvetted-source` (warning), `bad-media`, `missing-media-file`, `bad-enum`, `bad-tags` |
| `store.py` | `LibraryStore(root)`: `entries(include_retired=False) -> list[LoadedEntry]` (entry dict + issues), `get(id)`, `save(entry, *, author, note, expected_revision=None) -> dict` (validates; raises `ValidationFailed(issues)` on any error, `RevisionConflict` if file revision ≠ expected; bumps revision, stamps `updated_at/by`, writes temp + `os.replace`, appends history), `retire(id, *, author, note)`, `restore(id, rev, *, author, note)`, `history(id) -> list[Revision]`, `diff(id, rev_a, rev_b) -> str` (unified diff of YAML dumps), `media_file(id, rel) -> Path` |
| `search.py` | `fold(text)` (reuse `showcontext.ingest.keywords.fold`), `search(entries, query="", *, topic=None, instrument=None, genre=None, technique=None, publisher=None) -> list` (all folded query tokens must match title/title_vi/summary/body/tags/source titles+publishers; ranked: title hits first), `facets(entries) -> dict[str, Counter]` |

Agents use the same API or the CLI — never write `entries/` or `history/`
by hand when a person may be editing (hand-written files are still loaded
and flagged, never silently dropped).

## 3. CLI — `wing library …`

`list [--topic --instrument --genre --technique --source] [--json]`,
`search QUERY [filters] [--json]`, `show ID [--json]`,
`validate [--strict]` (exit 1 on any error; `--strict` also on warnings),
`add FILE --author NAME [--note]`, `edit ID FILE --author NAME --note …`,
`history ID [--diff REV]`. Agents pass `--author agent:<name>`.

## 4. UI — ninth page **Library / Thư viện** (Ctrl+9)

- Left: search box + group-by combo (Topic / Instrument / Genre / Technique /
  Source) + tree (group → entries, counts) + "show retired" toggle.
- Right: entry view (`QTextBrowser`, Markdown): title, badges (confidence,
  status, `UNSOURCED` / `UNVETTED SOURCE` when flagged), summary, body,
  diagrams inline (PNG), image links with licence + attribution, videos as
  links (title · channel · timestamp) opening the system browser, and a
  numbered **Sources** list on every entry.
- Buttons: **New entry**, **Edit**, **History**, **Retire**.
- Edit dialog: every schema field; sources table (add/remove rows) — Save
  stays disabled until ≥1 complete source and no validation errors; warnings
  shown but not blocking; author field pre-filled with the OS user and
  remembered in `ui-state.json`; change note required on edit.
- History dialog: revision list (rev · when · who · note), diff of the
  selected revision against its predecessor, **Restore this version**
  (creates a new revision, never rewrites history).
- Files ≤200 lines each (house-style test); strings in
  `texts_library.py` / `texts_library_vi.py`; no Qt worker threads (the store
  is small, loaded synchronously).

## 5. Media

`scripts/library_diagrams.py` (dev tool, not shipped) renders
`knowledge/library/diagrams.yaml` to `media/<entry>/<file>.svg` (pure-Python
SVG writer, maths from RBJ biquad formulas) and `.png` (QtSvg at dev time).
The app shows the PNG via Qt — no matplotlib, no QtSvg at runtime.
Kinds: `eq_curve`, `band_chart`, `transfer_curve`, `envelope`,
`polar_pattern`, `signal_flow`, `xy_plot`. External images and videos are
links only (see SCHEMA.md).

## 6. Packaging

`packaging/wing-ui.spec` DATAS gains `("../knowledge/library", "knowledge/library")`;
the build check greps `build/wing-ui/Analysis-00.toc` for `knowledge\library`.

## 6b. Online: artifact + VPS web app (owner request 09/11, ~22:50)

Owner: read it online anywhere (artifact) and on the VPS behind the PRJ012
login; owner full rights; company-staff accounts view only; every other
account sees nothing. Contract agreed with PRJ012 DEV01 the same night:

- **One single-page web app** `wing_parser/library/web/` (static `index.html`
  + JS + CSS, Sodium Rack theme tokens) used in two modes:
  - **Export mode** (`wing library export-web OUT_DIR`): data embedded as
    JSON, read-only, media copied next to it → published as a private
    claude.ai artifact (republished on every library change).
  - **Server mode**: `wing-library-web` (FastAPI + uvicorn, optional extra
    `library-web`), bound to `127.0.0.1:<port>`, served by PRJ012's nginx at
    `https://master.azsoundtech.com/library/`, `GET /library/healthz`.
- **Auth (PRJ012 route b)**: the PRJ012 web keeps the Supabase session in
  `localStorage["sb-abnbrulpqpyfisahdwen-auth-token"]` (JSON: `access_token`,
  `expires_at` epoch s) on the same origin. The library JS reads it and sends
  `Authorization: Bearer <access_token>` on every API call (including media,
  fetched as blobs). Missing/expired token or 401 → redirect to
  `https://master.azsoundtech.com/login?next=<path>`. The HTML shell holds no
  library content. The server forwards the header to PRJ012
  `GET /api/v1/me/permissions?codes=knowledge_library.view,knowledge_library.edit`
  → `{"permissions": {code: bool}}` (401 → 401; 404 `not_linked` → no view)
  and `GET /api/v1/me` → `member_id, display_name, is_owner`; cached ≤ 60 s
  per token. No view → 403 on every data route; edit routes need
  `knowledge_library.edit`. The server never verifies JWTs itself and never
  reads PRJ012's `.env`. PRJ012 base URL is configuration
  (`WING_LIBRARY_AUTH_BASE`).
- **Data on the VPS**: shipped layer = the deployed P008 checkout's
  `knowledge/library`; user layer = a docker volume (`WING_LIBRARY_DIR`).
  Web edits write the user layer with history; author =
  `"<display_name> (prj012:<member_id>)"`. Bringing web edits back into the
  repo is an agent-run export → PR (not automatic).
- PRJ012 owns: the two permission codes (`knowledge_library.view`,
  `knowledge_library.edit`, default closed, owner always allowed), the
  endpoint, `?next=` on /login, and the nginx location. These wait on the
  owner's direct confirmation in the PRJ012 session.

## 7. Tests

Schema validation (each code), source-required block on save, unvetted
warning, edit → history → diff → restore round trip, revision conflict,
retire hides, seeding (copies missing, never overwrites), search + facets
with Vietnamese folding, CLI exit codes, every shipped entry validates with
zero errors (repo test), UI smoke (page builds, search filters tree, edit
dialog blocks save without source, history dialog shows diff), EN/VI text
parity.
