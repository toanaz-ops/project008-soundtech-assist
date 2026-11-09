# Automix (GUI 12) — decision log for ToanAZ's round-2 review

Made by the automix session on 2026-11-09 while the owner was away ("Tự lên plan và làm cho tới khi
xong không hỏi không chờ human … để lại các quyết định tự quyết cho người review, bổ sung, sửa đổi sau
nếu cần trong round 2"). Each entry: what was chosen, the alternatives, why. Change any of them by
editing the data files or telling the next session the AM number.

**Read this first:** almost every number in `wing_parser/automix/data/` is a textbook or engineering
default (`confidence: low` or `eng_default`), not your taste. The only measured numbers are relative
loudness from De Man et al. 2014. Your answers to HW-191.Q1–Q6 go into `knowledge/toanaz/automix.yaml`
and override them.

## §0. Owner instructions this log implements (verbatim)

1. (via parent session) Automix: pick genre + options → auto EQ, auto fader balance, auto FX + sends.
2. 2026-11-09: "Có nút kích hoạt AI FULL ACCESS: cho phép AGENT/LLM/mạng neron tự mix tự thay đổi trên bàn
   trong suốt quá trình kích hoạt luôn chứ ko phải bản draft gì cả."
3. 2026-11-09: "Ngoài 1 2 3 thì tất cả những gì 1 channel strip cần thì đều được AI lái hết, bao gồm gate,
   compressor, plugin insert. Có nút kích hoạt cho phép enable tính năng auto nào: 3 chế độ - draft
   only/full auto access/disable (để tiết kiệm tài nguyên)."
4. 2026-11-09: "Không chạy test quá nhiều …" — tests limited to one golden, one invariant, one knowledge,
   one UI smoke per phase (spec §9).

## Decisions

| # | Decision | Alternatives | Why |
|---|---|---|---|
| AM-1 | Full auto writes to the live desk (phase 2). Supersedes the parent brief's "draft only, never push live". | Draft only forever. | Instruction 2 is the owner's own, later and explicit. Safety kept by reusing wave 3 arming, one-leaf writes, write log, Revert all. |
| AM-2 | Every number carries `src` + `confidence`; `eng_default` is a literal tag, never upgraded. | Ship numbers without provenance. | ROADMAP "Never fabricate"; research found few hard numbers (only De Man 2014 loudness). |
| AM-3 | Presets live in the shipped base layer; owner overrides in `<knowledge_dir>/automix.yaml` with `source:` = ToanAZ + ISO date. | Put presets in `principles.yaml`. | Owner layers require owner `source:` (PR #43); textbook values cannot carry it. |
| AM-4 | Genres: pop, rock, ballad, jazz, edm, bolero, speech. | Fewer (4) or many sub-genres. | Covers his show mix (concerts, corporate, bolero/cải lương scene files). Bolero = ballad-derived, no source found. |
| AM-5 | Machine data in `wing_parser/automix/data/`, human notes in `docs/knowledge-base/05-mixing-targets/`. KB-UI lane imports later. | Write into the KB lane's `wing_parser/library/`. | Two lanes writing one dir in parallel branches collides. |
| AM-6 | Default mode **Draft only**. | Disabled default; Full auto default. | Safe and useful out of the box; full auto needs a deliberate choice. |
| AM-7 | Only classifier confidence ≥ 0.8 (HIGH) is acted on; lower → Skipped row. | Act on LOW (0.4) too. | A wrong source type gives a wrong EQ; the skip list tells him which names to fix. |
| AM-8 | Lead vocal = lowest-numbered `speech.vocal` channel unless picked in the dialog. | Name keyword "lead"; loudest fader. | Classifier has no lead/backing split; lowest number matches common input-list order. |
| AM-9 | When research and an existing Doctor base rule disagree (hi-hat HPF 300 vs PB2 160-250), the base rule window wins. Invariant: automix adds no Doctor finding. | Follow research typicals. | Tool must not contradict itself; base rules already cite sources. |
| AM-10 | EQ/gate/comp only for models STD/GATE/COMP; other models (76LA, CMB, PULSAR…) → Skipped. | Map params across models. | Different key sets; guessing writes wrong values (descriptors/eq_models.py precedent). |
| AM-11 | No gates for jazz, ballad, bolero. | Gate every drum mic. | Natural dynamics/brush work; gates chop ghost notes. Low confidence. |
| AM-12 | Small venue: electric guitar and drums −3 dB (stage volume). | No venue effect. | Qualitative live-sound practice; eng_default. |
| AM-13 | FX roles by WING model: PLATE vocal, ROOM short/drums, HALL/CONCERT long, ST-DL delay. | By bus name. | Bus names vary ("VOX SHORT", "SNARE VERB"); model is reliable. |
| AM-14 | Empty FX slot / missing role → Suggestion only (never load a model). | Change `fx.k.mdl`. | Changing mdl does not create param keys; would produce an invalid scene. |
| AM-15 | Sends to FX set POST when PRE; GRP untouched; only on/lvl/mode patched. | Leave mode. | SOS R2: FX sends post-fader so reverb follows the fader. |
| AM-16 | "Plugin insert" v1 = WING automix group AUTO_X for speech channels with a free post-insert. Loading/assigning other insert FX: not in v1. | Assign any loaded FX as insert. | Only insert action with a documented, safe meaning offline. |
| AM-17 | Ratio capped at 8:1; EQ −6..+3 dB, Q 0.7..4; faders ≤ 0 (lead ≤ +5); sends ≤ 0. | Wider. | Feedback/clipping safety; live preference for cuts over boosts. |
| AM-18 | Full auto: tick 2 s, ≤10 writes/tick, fader step ≤1.5 dB/tick, EQ ≤1 dB. | Faster. | No documented WING OSC write rate; conservative self-throttle. |
| AM-19 | A leaf the operator changes during full auto is locked for the session. | Fight the operator. | "cần song song không đá nhau" — coexist with the human and WING-Edit. |
| AM-20 | Disabled mode never imports the automix package. | Always loaded. | Owner asked for a resource-saving off switch. |
| AM-21 | LLM refinement and a neural model deferred; the "AI" in v1 is the cited rule engine. | Call an LLM each tick. | Offline-first constraint, latency, and no way to verify an LLM's moves; provider hook can come later. |
| AM-22 | Meters (native protocol ch. 3) built as experimental, off by default. | Skip meters; on by default. | Transport/stride unverified (Maillot doc garbled); acceptance is HW-192. |
| AM-23 | Comp threshold derived from an assumed −12 dBFS peak; gate thr −40 dB. | Leave thr untouched. | Without meters there is no signal level; values marked eng_default; meters (AM-22) can refine. |
| AM-24 | A fader at -inf (-144) is never moved and is listed as Skipped; speech inserts skip channels whose gate is on; the `cfg.amix.x` hint appears only when group X is off. | Raise silent faders to the target; turn the gate off. | Rest scenes keep unused strips silent; Doctor E6 (gate + automix) must not fire; avoids noise. |
| AM-25 | Doctor base-rule windows (PB2-PB5, PC1, PC6) live in `eq_targets.yaml` `doctor_windows` and clamp HPF after strength; speech ratio capped at 4:1 (PC5); speech.mc EQ (300 Hz -3 dB Q1.4, 3 kHz +2 dB) and AUTO_X weight +4 reproduce PC2/PC3/PC7. | Ignore the Doctor. | Invariant: no new Doctor finding after applying a proposal. |
| AM-26 | Reverb role pick: ROOM takes the short end of the genre decay/pre-delay range, PLATE the middle, HALL/CONCERT the long end. | Same value for every reverb. | Gives a short drum room and a long hall from one genre row; eng_default. |
| AM-27 | Research send rows of the form `off..X` are resolved to off. | Use X or the midpoint. | Conservative; owner can override per source. |
| AM-28 | `bus_assign` in `fx.yaml`: PLATE feeds vocals/guitars/keys, ROOM feeds drums, HALL feeds vocals/acoustic/keys at -6 dB under the reverb level, delay feeds vocals/guitars. Sources without a send-level row get no send. | Feed everything equally. | Avoids doubling the wet signal and sends to strips with no researched level. |
| AM-29 | Headroom trim is solved in closed form over the proposed faders (others fixed), rounded up to 0.1 dB plus a 0.1 dB margin, capped at 24 dB. | Iterate. | Exact enough for 0.1 dB fader resolution; cap prevents runaway when un-proposed channels dominate. |
| AM-30 | Owner layer file format: `overrides: [{file, path: [keys...], value: {fields}, source}]`; a honoured entry merges `value` into the record at `path` and stamps `src: [toanaz_n]`, `confidence: high`. | Whole-file replacement; free-form keys. | Reuses the table validator, so an invalid override is ignored with a warning instead of corrupting a table. |
| AM-31 | EQ details: shelf written only when `heq` is SHV; a masking cut is added only if a cut band (1-2) is free and the frequency is more than 1/3 octave from the strip's own cuts; Q interpolates linearly, ratio/bools switch at strength 0.5; `eq.on` set only if a proposed gain is non-zero. | Overwrite all four bands. | Keeps existing user bands where the data has nothing to say. |
| AM-32 | UI phase 1: the lead-vocal picker is left out of the dialog; the engine heuristic (AM-8) picks the lead. | A combo of speech.vocal channels feeding `lead_channels`. | Keeps the first dialog small; the option already exists in the engine so it can be added without an engine change. |
| AM-33 | The UI repeats the genre/venue/stage tuples in `ui/automix_controls.py` instead of importing them, so menu construction never loads `wing_parser.automix` (AM-20); `tests/test_ui_automix.py` pins them to the engine constants and checks in a subprocess that building the main window leaves the engine unloaded. | Import `GENRES` from the engine. | An import at module level would load the engine even with the mode Disabled. |
| AM-34 | Setting `automix_mode` lives in ui-state.json (`disabled` or `draft`); an unknown or `full_auto` value reads back as `draft` until phase 2 adds the entry. The menu entry is hidden when Disabled and enabled only while a scene is loaded. | Separate config file; showing the entry greyed out. | Same store and same pattern as language; hiding matches "Disabled". |

## Round-2 questions for ToanAZ (one Decision Box card)

1. Keep Full auto's limits (AM-18) or change tick/steps?
2. Genre list and bolero/cải lương profile (AM-4) — what is different in your bolero mix?
3. Your fader offsets vs lead vocal per genre (replaces `balance.yaml` defaults).
4. HPF/EQ/comp numbers: answer HW-191.Q1–Q6, they land in `knowledge/toanaz/automix.yaml`.
5. Should automix ever load FX models into empty slots (AM-14) or assign insert FX (AM-16)?
6. Meters: test the experimental reader at the HW-192 desk session (AM-22).
