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
| AM-35 | Fable review fixes. Masking: when a masking pair applies the strip keeps its first own cut and takes the masking cut as the second (before, the own second cut always filled the slot and the masking cut was dead). Headroom guard: faders are interpolated by strength first, then the trim is solved on the interpolated values, and its limit is max(ceiling, the scene's own main sum) so strength 0 moves nothing and a hot scene is never trimmed below where it started. | Trim the full-strength targets, then interpolate (old); always trim to the ceiling. | The old order over-trimmed at strength < 1 and the old limit pulled a hot scene down at strength 0. |
| AM-36 | Gate attack is written on a 1 ms step (round half up, so the 0-1 ms range gives 1 ms). Snare bottom gets no compressor (HPF and fader only, per spec). | Keep 0.5 ms. | The WING gate attack leaf resolves to 1 ms. |
| AM-37 | A channel whose classifier kind is unknown, or that has no automix profile, gets no Skipped row; Skipped keeps low classifier confidence and model guards. | List every untouched channel. | The tab was dominated by rows the operator cannot act on. |
| AM-38 | Console-pulled documents carry 0/1 for switches. Leaf checks use `is_on` / `is_number` (a bool is never a number); a bool target written over an int leaf is written as int, so an int document stays an int document and a file document stays bool. | Always write bool; convert the document first. | Writing True over a console int would change the leaf type under the document. |
| AM-39 | Honesty of numbers: a record may carry `db_confidence` (or `ceiling_confidence` in headroom) that weakens only its dB/Q. Masking dB/Q, every numeric FX send range, the headroom ceiling and the tom gate timings, tom and bass HPF are `eng_default`; the corporate-preset 3 kHz +2 dB on speech.mc is attributed to kb_corp only; edm and jazz reverb and the kick/snare gate no longer cite sources that state no numbers. Residual: genre fader offsets stay low (anchored on F1 for kick/snare/bass/drums only; the rest is judgement). An owner override drops stale `*_confidence` keys. | Keep the research tags. | Spec section 3: a source id only where the source states the value. |
| AM-40 | Reverb models BPLATE, V-PLATE, VSS3 map to vocal_plate and CHAMBER, AMBI, V-ROOM to short_room; their parameter keys and ranges are unverified (`unverified_models` in fx.yaml): only the leaves found are patched, a missing leaf is silent, and a bus where none are found is one Skipped row. | Wait for the Effects Guide. | pointer.read skips missing keys already; no value is invented. |
| AM-41 | The Automix dialog lists owner-layer warnings in a Warnings tab (count in the summary); stage boxes re-tick from the genre's default stages on genre change (`GENRE_STAGES`, pinned to genres.yaml by test); Apply goes through `Session.record_many` (one re-derive, wait cursor, still one undo step per change). Owner-layer paths that cross a list or scalar are warnings, never exceptions. | Re-derive per change. | Apply froze the UI on large proposals. |
| AM-42 | Full auto reuses the existing write path only: `live_write.send` per leaf under the gate's arm (`write_arm_dialog.arm_now`), each real write recorded with `changes_panel.record_sent` (Sent ledger, Revert all, write log, show code from the arm, `because="automix-live:<genre>:<stage>"`). No second write door; `test_ui_live_is_read_only.py` is unchanged. | A dedicated automix writer. | Owner: reuse what already sends fader moves. |
| AM-43 | Settings mode `full_auto` ("Full auto (live desk)"). The Automix dialog then shows a Full auto... button that opens a non-modal panel (`ui/automix_live.py`); Draft keeps working. Start needs a Console connection and an open/pulled scene, the explicit "FULL AUTO: the app will change this desk continuously until Stop" tick, and, when Simulate is off, the normal arm dialog. | A fourth Tools menu entry. | One entry, mode-gated. |
| AM-44 | Simulate (no writes) is ON by default; only a user click on it asks "write to the real desk?". In simulate the loop runs on live reads and `write_leaf` only records "would write" rows; they are overlaid on the next read so the loop converges visibly and is not mistaken for an operator touch (AM-19). Simulate needs no arm. | Default OFF. | Coordinator safety rule: real-desk writes only when the operator explicitly arms. |
| AM-45 | Apply level (Manual/Delayed/Immediate) is ignored by the loop: pressing Start is its own explicit consent, logged as ordinary repair-kind rows with the automix `because`. | Force Immediate. | A per-write countdown would defeat continuous operation. |
| AM-46 | Loop judgement calls (live_loop / live_limits): write order fader > eq > hpf > comp > gate > sends > fx > inserts; steps 1.5 dB fader, 1 dB EQ gain, 2 dB send and threshold, 20 % of the value (min 1.0) for frequencies and times, 1.0 otherwise, discrete leaves in one step; at most 10 writes per tick, tick 2 s; operator-lock tolerance 0.25 (desk re-quantisation); 3 consecutive failing ticks end the run as failed. | Per-parameter step table. | Audible moves first, small steps, tolerance above the desk's quantisation. |
| AM-47 | One writer (W10): while the loop runs the Doctor level/arm controls and the journal's Send rows are disabled. The panel stops itself when the gate stops being ready (disconnect, lost, disarm) or `DeskChanged` is raised, via a `threading.Event` the worker checks before every write; Esc and closing the panel also stop. A stop leaves the desk as it is. | Revert on stop. | A silent revert mid-show is worse than leaving the last values. |
| AM-48 | Revert automix (after Stop): each touched path is written back once to its pre-automix desk value (first desk_before), last touched first, sequential through `live_write.send` on one worker call, and recorded on the ledger's `reverted` signal so the log shows kind `revert`. Needs the gate still ready. The session journal is not edited (live automix writes are not file edits). | Ledger Revert all only. | Ledger revert goes through a modal countdown per row; this is one explicit action. |
| AM-49 | Per-tick read: one `get_many` over the leaves of the latest proposal (seeded from a propose on the base scene on tick 1), overlaid on a private deep copy of the pulled scene's document; values normalised with `live_write.scene_value`. A silent desk is an error tick. `workers.TIMEOUTS["tick"] = 60`. | Full snapshot each tick. | ~10 s per full pull. |
| AM-50 | Experimental meters stay hidden in the UI: no verified transport, so no checkbox is shown and no socket is opened by the panel. `net/meters.py` stays unit-tested only (HW-192). | Show a disabled checkbox. | An unwired control invites a wrong belief. |

## Round-2 questions for ToanAZ (one Decision Box card)

1. Keep Full auto's limits (AM-18) or change tick/steps?
2. Genre list and bolero/cải lương profile (AM-4) — what is different in your bolero mix?
3. Your fader offsets vs lead vocal per genre (replaces `balance.yaml` defaults).
4. HPF/EQ/comp numbers: answer HW-191.Q1–Q6, they land in `knowledge/toanaz/automix.yaml`.
5. Should automix ever load FX models into empty slots (AM-14) or assign insert FX (AM-16)?
6. Meters: test the experimental reader at the HW-192 desk session (AM-22).
