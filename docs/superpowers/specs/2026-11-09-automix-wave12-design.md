# GUI 12 — Automix: genre-driven channel-strip proposal (draft) and full-auto live mode

Date 2026-11-09. Status: design authority for wave 12. Owner requests (ToanAZ, 2026-11-09, verbatim in
`docs/decisions/2026-11-09-automix-decisions.md` §0). Every judgement call made without the owner is
numbered `AM-n` in that decision log; this spec cites the number instead of re-arguing it.

## 1. What it does

The operator picks a **genre** and a few **options**. The app reads the loaded scene and proposes, per
input channel, everything a channel strip needs:

| Stage key | What | Patched leaves (`ae_data.` + …) |
|---|---|---|
| `hpf` | high-pass | `ch.N.flt.lc`, `lcf`, `lcs` |
| `eq` | 4-band parametric + shelves | `ch.N.eq.on`, `{l,1,2,3,4,h}{g,f,q}` (STD only) |
| `gate` | drum gates | `ch.N.gate.on/thr/range/att/hld/rel` (GATE only) |
| `comp` | compressor | `ch.N.dyn.on/thr/ratio/knee/att/rel/gain` (COMP only) |
| `fader` | balance | `ch.N.fdr` |
| `fx` | reverb/delay slot params | `fx.K.dcy/pdel/lc/hc` (reverb), `fx.K.time/feed/lc/hc` (ST-DL) |
| `sends` | FX sends | `ch.N.send.B.on/lvl/mode` |
| `inserts` | WING automix group (speech) | `ch.N.postins.on/mode/w` |

Three **modes** (Settings ▸ Automix, persisted in `ui-state.json` key `automix_mode`):

- **Disabled** — the Tools entry is hidden; the `wing_parser.automix` package is never imported (saves
  resources; AM-20).
- **Draft only** (default) — Tools ▸ Automix… builds a proposal, shows it with "why" + sources, and can
  apply it to the **session journal** (same path as Doctor repairs) so the operator saves it with the
  existing Save as… to a NEW `.snap`. Nothing reaches a desk.
- **Full auto** (phase 2, §7) — after arming, the engine writes to the live desk continuously, one leaf per
  write, through `ui/live_write.py`, until stopped.

## 2. Phases

1. **Phase 1 (PR A):** knowledge data + human notes, engine (`wing_parser/automix/`), Draft-only UI,
   Settings mode (Disabled / Draft only), tests. Fable review, merge, exe rebuild.
2. **Phase 2 (PR B):** Full auto live loop + Settings option, experimental meter reader (off by default),
   tests with injected fakes. Fable review, merge, exe rebuild.
3. **Deferred:** LLM refinement of a proposal (AM-21).

## 3. Knowledge (structured data + human notes)

Machine data, shipped in the package (bundled in the exe; add to `pyproject` package-data and
`packaging/wing-ui.spec` datas): `wing_parser/automix/data/`

| File | Content |
|---|---|
| `sources.yaml` | `sources: {<id>: {cite, url, kind, accessed: 2026-11-09, opened: true/false}}` |
| `eq_targets.yaml` | per source_type: `hpf {hz, slope}`, `cuts [{hz, db, q, why}]`, `boosts [...]`, `src`, `confidence` |
| `masking.yaml` | pairs `{owner, yield, hz, db, q, why, src, confidence}` |
| `dynamics.yaml` | `comp` and `gate` per source_type + `genre_deltas` |
| `balance.yaml` | `anchor`, per-genre fader offsets re lead vocal, `venue` deltas, headroom model |
| `fx.yaml` | per-genre reverb/delay params, wetness offsets, per-source send levels, WING model → role map, observed param ranges |
| `genres.yaml` | genre ids (`pop rock ballad jazz edm bolero speech`), labels EN/VI, which stages default on |
| `bounds.yaml` | hard safety bounds (§6) |

Every numeric value carries `src: [ids]` and `confidence: high|medium|low|eng_default`. `eng_default`
is a literal tag meaning "engineering convention, no source states this number" — it is never upgraded
silently (AM-2). Loader validation fails on a value with neither `src` nor `eng_default`.

Human notes: `docs/knowledge-base/05-mixing-targets/` (`README.md`, `eq.md`, `balance-and-dynamics.md`,
`effects.md`, `wing-fx-and-meters.md`) — own words, sources summarised, URLs listed; disagreements and
unverified items kept visible.

Owner override layer: `<knowledge_dir>/automix.yaml` (ships absent; `knowledge/toanaz/automix.yaml`
created empty with a header). Same keys as the data files; an entry is honoured only if its `source:`
contains `ToanAZ` and an ISO date (same rule as the `toanaz` advisory layer, PR #43); otherwise it is
ignored and listed as a load warning. This is where HW-191 answers land (AM-3).

## 4. Engine API (`wing_parser/automix/`, deterministic, no Qt, no network)

```python
GENRES = ("pop", "rock", "ballad", "jazz", "edm", "bolero", "speech")
STAGES = ("hpf", "eq", "gate", "comp", "fader", "fx", "sends", "inserts")

@dataclass(frozen=True)
class AutomixOptions:
    genre: str
    bpm: float = 120.0                  # delay time / tempo pre-delay
    venue: str = "medium"               # small | medium | large
    strength: float = 1.0               # 0..1, how far from current toward target
    stages: frozenset[str] = frozenset(STAGES)
    min_confidence: float = 0.8         # classifier HIGH; below -> skipped row
    lead_channels: tuple[int, ...] = () # empty -> heuristic (AM-8)

@dataclass(frozen=True)
class Change:
    path: str            # full pointer path, "ae_data.ch.5.eq.1g"
    before: Any
    after: Any
    stage: str
    target: str          # "ch.5" / "fx.2"
    label: str           # human short label, English (UI translates stage names)
    why: str             # one sentence, English
    sources: tuple[str, ...]
    confidence: str

@dataclass(frozen=True)
class Suggestion:        # cannot be expressed as a Patch (e.g. load PLATE into empty slot)
    stage: str; target: str; text: str; sources: tuple[str, ...]

@dataclass(frozen=True)
class Skipped:
    target: str; reason: str   # "low classifier confidence 0.4", "dyn model 76LA not COMP", ...

@dataclass(frozen=True)
class Proposal:
    options: AutomixOptions
    changes: tuple[Change, ...]
    suggestions: tuple[Suggestion, ...]
    skipped: tuple[Skipped, ...]
    headroom_trim_db: float    # uniform fader trim applied by the headroom guard (0 if none)

def propose(scene: WingScene, document: dict, options: AutomixOptions,
            knowledge_dir: Path | None = None) -> Proposal
def to_patches(proposal: Proposal) -> list[Patch]   # because="automix:<genre>:<stage>"
```

`propose` is pure: same inputs → same proposal (golden tests rely on it). `before` is read with
`pointer.read(document, path)`; a missing key → `Skipped`, never a Change. A Change whose `after == before`
(after rounding to the leaf's resolution) is dropped.

Module split (≤200 lines each, by layer): `knowledge.py` (load + validate data and owner layer),
`options.py`, `select.py` (channel selection, lead heuristic, FX bus discovery), `stages_filter_eq.py`,
`stages_dynamics.py`, `stages_balance.py`, `stages_fx.py`, `bounds.py` (clamp + forbidden paths),
`engine.py` (`propose`, `to_patches`), `interp.py` (strength interpolation).

## 5. Stage rules

**Channel selection.** Every `ch.N` with a non-empty name. Classifier kind with confidence ≥
`min_confidence` is used; below → `Skipped` (AM-7). Kinds never touched: `utility.click talkback timecode
spare ambient remote_caller fx_return`, `unknown*`, `drums.pad`. Sub-kinds fall back to their family
(`drums.kick.in` → `drums.kick`, `drums.snare.top` → `drums.snare`, `instrument.guitar` → electric,
`speech.handheld|headset|lav|lectern|panel|qa` → `speech.mc`). `drums.snare.bottom`: HPF + fader only.

**Lead vocal (AM-8).** Classifier has no lead/backing split. Lead = `options.lead_channels` if set, else
the lowest-numbered `speech.vocal` channel; other `speech.vocal` channels are backing. Genre `speech`: every
speech kind is lead-level.

**HPF.** `lc=True`, `lcf` = data typical, `lcs="12"` (Core-Skills-Overview L686 12-18 dB/oct). Where a
Doctor base rule states a window for the same source (PB2 hi-hat 160-250, PB3 ride 200-300, PB4 overhead
160-450, PB5 kick/bass ≤45), the target is clamped into that window — existing cited rules win (AM-9).
Invariant: applying a full proposal adds **no new Doctor finding** on the golden scenes.

**EQ (STD only, AM-10).** Model ≠ `STD` → `Skipped`. Bands: up to two cuts into bands 1–2, up to two boosts
into bands 3–4, "shelf" items into the high shelf (`hg/hf/hq`, `heq` untouched). Frequency = data value
(geometric centre of a range); gain default cut −3 dB / boost +2 dB when the source gives no number
(`eng_default`); Q 2.0 for cuts, 1.0 for boosts. Masking pass: for each pair present in the scene, the
`yield` source gets a complementary cut at the pair frequency if it has a free band. `eq.on=True` only if
at least one band gain is non-zero. Genre tilt from `genres.yaml` adjusts gains (e.g. rock +1 dB presence,
jazz halves all boosts).

**Gate (GATE only).** `drums.kick`, `drums.snare`, `drums.tom` only; genres `jazz`, `ballad`, `bolero`
leave gates untouched (AM-11). `thr=-40` (eng_default: no meters offline), range/att/hld/rel = midpoints of
`dynamics.yaml`.

**Comp (COMP only).** Per source from `dynamics.yaml` + genre delta. `ratio` snapped to the WING list
`[1.1 … 100]`; `knee=2`; `att`, `rel` midpoints; `thr = clamp(peak_est − gr·ratio/(ratio−1), −40, −5)`
with `peak_est=−12 dBFS` (eng_default) and `gr` the range midpoint; `gain = clamp(gr/2, 0, 6)`. Never on
`utility.playback`.

**Fader.** Anchor = lead fader clamped to −10..0 dB if lead exists and is not −inf, else −5 dB
(eng_default). Target = anchor + genre offset (`balance.yaml`; De Man et al. 2014 relative loudness for
kick/snare/bass/drums, the rest eng_default) + venue delta (small: electric guitar and drums −3 dB, stage
volume, AM-12). Headroom guard: estimated main sum `10·log10(Σ 10^((−18 + fdr)/10))` over channels with a
main send on must be ≤ −3 dBFS; otherwise every proposed fader is trimmed by the same amount
(`headroom_trim_db`). Main / matrix / bus faders never touched.

**FX (AM-13/14).** FX buses are found by `bus.B.preins|postins` with `on` and `ins == "FXk"`, then
`fx.k.mdl`: `PLATE` → role `vocal_plate`, `ROOM` → `short_room`, `HALL|CONCERT` → `long_hall`, `ST-DL` →
`delay`. Patch only existing keys of those models; values clamped to genre range ∩ `bounds.yaml` observed
ranges. Delay `time` = note value at `bpm` (1/4, dotted 1/8 …), `feed` = genre midpoint. A genre with no
slot of a needed role → `Suggestion` ("load PLATE into an empty slot 1–8 and insert it on a free bus"),
never a Change (pointer cannot create keys).

**Sends.** For each selected channel × discovered FX bus: target = `fx.yaml` per-source level for that
role + genre wetness offset, clamped ≤ 0 dB; "off" → `lvl=-144` and leave `on` as is. When the target is
on: `on=True`, and `mode` PRE → POST (R2: FX sends post-fader); `GRP` left alone (AM-15). Only `on/lvl/mode`.

**Inserts (AM-16).** Genre `speech` only: speech-kind channels whose `postins.ins == "NONE"` get
`postins.mode="AUTO_X"`, `postins.on=True`, `w=0` (WING gain-sharing automix, Maillot p.45). If the scene
has a `cfg.amix.x` leaf it is a Suggestion (global config, not a strip). Other genres: no insert changes;
assigning already-loaded channel-type FX is out of scope in v1.

**Strength.** dB values interpolate linearly `before + s·(target−before)`; frequencies geometrically;
discrete values (bools, enums, ratio list) switch when `s ≥ 0.5`.

## 6. Safety bounds (`bounds.yaml`, enforced in `bounds.py`, tested as invariants)

- EQ gain −6..+3 dB, Q 0.7..4, f 20..20000; HPF 20..400 Hz.
- Channel fader ≤ 0 dB (lead ≤ +5), ≥ −60 unless −inf before; sends ≤ 0 dB.
- Comp thr −40..−5, ratio ∈ WING list ≤ 8 (AM-17), gain 0..6; gate thr −80..−20, range 3..60.
- Reverb dcy 0.2..5 s, pdel 0..200 ms, lc 20..400, hc 2000..20000; delay time 20..2000 ms, feed 0..60.
- **Forbidden leaves** (no Change may target): `*.mute`, `*.pan`, `*.wid`, `ch.N.in.*` (polarity,
  phantom, source), `*.main.*`, `main.*`, `mtx.*`, `bus.*` (except via `fx.*`), `dca.*`, `cfg.*`, `ch.N.peq.*`,
  `send.*.pon|plink|ind|pan`, `eq.mdl`, `dyn.mdl`, `gate.mdl`, `fx.*.mdl`, `fx.*.fxmix`.

## 7. Full auto (phase 2)

Owner instruction supersedes the parent brief's "never push to a live console" (AM-1). Safety comes from
reusing wave 3 wholesale:

- **Arm** per connection: fresh identity, "desk not running a show" tick replaced by an explicit
  **FULL AUTO** tick, typed desk name, show code (wave 5). Disarm on Stop, Esc, disconnect, `DeskChanged`
  (serial differs), mode switched away, app close.
- **One door:** the loop calls `ui/live_write.send` per leaf; it never imports `wing_parser.net.write`
  (`test_ui_live_is_read_only.py` unchanged). Every write goes to the write log (wave 5) with
  `because="automix-live:<genre>:<stage>"`.
- **Loop** (`wing_parser/automix/live_loop.py`, pure, injected `read_leaf`, `write_leaf`, `clock`): every
  tick (default 2 s) read the leaves the proposal touches, re-run `propose` on the live state, diff,
  then apply at most `max_writes_per_tick` (default 10 → ≤5 writes/s, AM-18) with per-tick step limits
  (fader 1.5 dB, EQ gain 1 dB, send 2 dB, thresholds 2 dB).
- **Operator override:** if a leaf's desk value differs from what the loop last wrote, the operator touched
  it; the leaf is locked for the session and listed in the UI (coexist with WING-Edit / the human, AM-19).
- **Revert all:** reverse-order, sequential, through the existing ledger.
- **Meters (experimental, off):** `wing_parser/net/meters.py` native-protocol reader per Maillot
  "WING Remote Protocols" ch. 3 (socket injected; unit tests feed byte strings). Unverified transport and
  layout → disabled unless the operator ticks "experimental meters"; when on, gate thresholds and fader
  rides may use meter data. Acceptance belongs to HW-192.

## 8. UI (phase 1)

- `ui/settings_automix.py`: Settings section, combo Disabled / Draft only (phase 2 adds Full auto), saved
  via `state_store` like language, applies immediately to the menu.
- `ui/automix_dialog.py` + `ui/automix_tables.py`: Tools ▸ Automix… (only when mode ≠ Disabled and a scene
  is loaded). Genre combo, BPM spin, venue combo, strength slider, eight stage checkboxes, **Propose**.
  Tabs: Changes (Channel, Source, Stage, Parameter, Before, After, Conf.), Suggestions, Skipped. Selecting a
  row shows "why" + source citations. **Apply to scene (draft)** records every Change through
  `Session.record_value(path, after, label, because)`, refreshes Doctor; the operator then uses Save as….
- Strings: new pair `texts_automix.py` / `texts_automix_vi.py`, registered in `texts.py`,
  `texts_vi_all.py`, `tests/test_ui_bilingual.py` (`_pairs()` + `merged`). Genre names VI: Pop, Rock,
  Ballad, Jazz, EDM, Bolero, Hội nghị / lời nói.

## 9. Tests (restraint requested by the owner)

1. `test_automix_golden.py` — one parametrised test: 4 genres × 2 scenes (LIVE.snap with FX buses,
   OCHESTRA.snap without) → snapshot of (path, after) pairs + suggestion/skip counts in
   `tests/data/automix_golden/*.json`; regenerate with an env flag. Plus `speech`, `jazz`, `edm` on
   GIAQUY/CAI LUONG in the same parametrisation (76LA dyn, CMB gate → Skipped, not Change).
2. `test_automix_invariants.py` — over all genres × all user-files scenes: every Change path
   `pointer.read`-able, not forbidden, value in bounds; headroom ≤ −3 dBFS; `to_patches` applies cleanly
   via `writer.applied`; no new Doctor finding after applying.
3. `test_automix_knowledge.py` — every value has `src` ids that resolve or `eng_default`; owner layer
   rejects an entry without `ToanAZ` + date.
4. `test_ui_automix.py` — one smoke: dialog proposes on a scene, Apply records patches in the session.
   Existing texts/house-style/read-only tests cover the rest.
Phase 2 adds `test_automix_live_loop.py` (fake desk: rate limit, step limit, override lock, disarm) and
`test_net_meters.py` (byte parsing).

## 10. Out of scope

Training a neural network; changing FX models or routing; monitor/IEM mixes; bus/main processing; LLM
refinement (deferred, AM-21); per-song scenes/cues.
