# Knowledge library — decisions taken while the owner was away (2026-11-09)

Owner (09/11): build a mixing knowledge library UI; decide without asking,
record every decision for review. Each line: what was chosen, why, how to
undo. Real open questions are on the Decision Box (codes at the bottom).

| # | Decision | Why | Undo / cost to change |
|---|---|---|---|
| L1 | The library is a **ninth page of `wing-ui`** (Library / Thư viện, Ctrl+9), not a local web view. | UI-first rule: features exist only as buttons in the desktop app; one exe, same theme, no server. | A web view could read the same store later; the store has no Qt dependency. |
| L2 | Store = **one YAML file per entry** in `knowledge/library/entries/`, history as **append-only JSONL** per entry, taxonomy and publisher allow-list as YAML. Not SQLite. | Git-diffable, reviewable in PRs, readable by agents and automix with no driver; matches the rest of `knowledge/`. | A loader change only; entries are plain data. |
| L3 | Two layers (suggested by the automix lane): **shipped** = repo `knowledge/library/`, bundled into the exe, read-only there; **user** = `~/.config/wing-skill/library/` (`config.library_dir()`, `WING_LIBRARY_DIR` overrides). Readers see shipped ∪ user, user wins by id; saves and history go to the user layer only. | The bundle dir is deleted on exit (same trap `config.py` documents); a copy-once seed would freeze old entries forever, the overlay lets a new exe bring updated shipped entries. | An edited shipped entry stops receiving updates from new exes (the user's version wins) — visible as layer "user" on the entry. |
| L4 | `docs/knowledge-base/*.md` is **not imported** as library entries. | 8 of its 10 files have no external citation; importing them would create entries the source rule rejects. Base rules keep citing it as before. | Research agents re-sourced the same ground from reputable publishers. |
| L5 | **No source → save is blocked** (UI and CLI). Hand-edited files without a source still load but carry an `UNSOURCED` flag. A publisher missing from `sources.yaml` is a **warning** (`UNVETTED SOURCE`), not a block. | Owner: every entry cites a reputable source; flag or block unsourced. A hard block on unknown publishers would stop the owner citing a good source the list lacks. | Make `unvetted-source` an error: one line in `validate.py`. |
| L6 | Publisher allow-list (`sources.yaml`) seeded with 31 publishers: AES/JAES, Sound On Sound, iZotope, FabFilter, Waves, Sonnox, Focal Press, Senior, Owsinski, Behringer/Music Tribe, Shure, Sennheiser, DPA, Audio-Technica, Rane, Dugan, Meyer, d&b, L-Acoustics, Yamaha, Rational Acoustics, ITU, EBU, WHO, IEC, QMUL, UA, SoundGirls, ProSoundWeb, Mix. | Matches the brief's list plus manufacturers/standards bodies cited in live sound. | Owner edits the file (each line has a reason). |
| L7 | Illustrations are **diagrams generated in-repo** (`scripts/library_diagrams.py`, pure-Python SVG, PNG rendered with QtSvg at dev time, CC0). No matplotlib at runtime. | Exact, licence-clean, numbers traceable to the entry's sources or to filter maths; no exe bloat. | — |
| L8 | External images (Wikimedia Commons) and videos (YouTube etc.) are stored **as links** with title/channel/timestamp or licence/attribution; nothing downloaded or re-hosted. | Brief forbids re-hosting video; downloading files needs explicit permission; links keep attribution with the original. | Re-hosting CC images is possible later (licence fields already stored) — see Decision Box. |
| L9 | Entry body is **English**, with `title_vi`; UI chrome is bilingual (EN/VI tables like the rest of the app). | Sources are English; translating ~50 technical bodies by machine risks wrong terms. | Add `body_vi` (schema-compatible optional key) — see Decision Box. |
| L10 | No hard delete: an entry is **retired** (hidden by default, history kept). **Restore** of an old version writes a new revision; history is never rewritten. | Revision history must show who changed what and when. | — |
| L11 | Author of a change: OS user name pre-filled and editable in the edit form (remembered); agents write `agent:<name>`. | The desktop app has no login. | — |
| L12 | Agent-written entries land as `status: draft`; the owner (or a reviewer) moves them to `reviewed`. | Agent research is not owner judgement; automix can choose to read only `reviewed`. | — |
| L13 | Research agents wrote YAML into a **staging folder outside the repo**; the coordinator validated with `wing library validate` and copied. | Keeps 50+ entries out of the coordinator's context; agents never wrote the repo. Deviation from "read-only research agents": write was limited to that folder. | — |
| L14 | Schema agreed with the automix session (`p008-automix`) by message 2026-11-09: `rule` = mapping with automix's `kind` list (automix owns per-kind params validation); shared genre tag ids; automix keeps its machine data in `wing_parser/automix/data/` and this lane converts its research (with its source URLs) into library entries. Neither lane edits the other's package. | One store, no forked format, no two writers in one directory. | Changes are agreed by message and land in `SCHEMA.md` + `schema.py` together. |
| L15 | Coding sub-agents run on **sonnet**: the repo's spawn gate refuses opus/fable for implementation. | Hook rule. | — |

## Open questions on the Decision Box

Posted 2026-11-09 to the Decision Box (group "PROJECT008 Soundtech Assist"):

- **HW-204.Q1** — entry bodies English only, or add `body_vi` (agent-translated, flagged unreviewed)? Recommend B; interim A (L9).
- **HW-204.Q2** — may automix use `draft` entries for suggestions? Recommend B (suggest, labelled "unreviewed source"; desk writes still only via Repair); interim: entries stay draft (L12).
- **HW-204.Q3** — how web edits on the VPS come back to the repo. Recommend A (agent export → PR, periodic or on request); interim A documented in `deploy/library-web/README.md`.
- **HW-204.Q4** — external images/videos as links or local copies? Recommend A (links); interim A (L8).

Owned by PRJ012 (asked of the owner directly in the PRJ012 session by PRJ012 DEV01, 2026-11-09): the permission codes `knowledge_library.view` / `knowledge_library.edit`, the `GET /api/v1/me/permissions` endpoint, and `/login?next=`.

## Later decisions

| # | Decision | Why | Undo / cost to change |
|---|---|---|---|
| L16 | Online access (owner request 09/11 ~22:50): same single-page app as a private claude.ai artifact (read-only export) and as `wing-library-web` on the VPS at `master.azsoundtech.com/library/` behind PRJ012 login (route b: browser sends the PRJ012 Supabase token, server asks PRJ012 for permission codes, never verifies JWTs itself). | Agreed with PRJ012 DEV01; one origin = one login session; P008 owns no users. | Container can be stopped; nginx location removed by PRJ012. |
| L17 | Web edit author = `"<display_name> (prj012:<member_id>)"` from PRJ012 `/api/v1/me`, set by the server, never by the browser. | History must say who changed what; the client cannot be trusted. | — |
