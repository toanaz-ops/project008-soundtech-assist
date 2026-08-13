# Handoff — Wing Scene Parser Project

**From session:** 2026-08-13 (Opus 5, 39% context used, ended at user request for handoff)
**To session:** next continuation
**Project root:** `Z:\My Drive\CLAUDE WORKS\DEV CAVE 2026\SOUNDTECH PLAYGROUND`

---

## 1. What This Project Is

The user wants to build a **Behringer Wing `.snap` scene-file parsing skill** for Claude, with the end-vision of a Claude-assisted live mixing workflow that can eventually drive a real Wing mixer via OSC. The work was started in `brainstorming` skill (Phase 4/5 — design sections mostly presented, spec not yet written).

The user has explicitly scoped the project to **decompose across multiple phases**. The current effort covers **Phase 1 only** (read `.snap` files; build a Python library + CLI + MCP server + 5 Claude Skills; output advisory rules). Phases 2–4 (OSC control, AI decision-making, voice input pipeline) are out-of-scope and must be deferred to separate spec cycles.

---

## 2. Current State on Disk

### Source files (`user-files/`)
```
example-Vu.snap                922 KB  — show scene file (active mix, 40 ch)
factory-scene.snap             353 KB  — factory default scene (all faders -∞)
WING_Series_Manual_Knowledge_Base.md   15 KB  — already-extracted manual summary (use this)
User-Manual_WING-series_2025-10-20.pdf  20 MB  — original PDF manual (only use when KB lacks detail)
mastering-engineer-1.0.0.tar.gz  5.6 KB — external skill we studied; NOT ours to install
WING-Edit.exe                  94 MB  — Windows installer, not relevant here
readme.txt                       110 B  — placeholder
```

### Knowledge base (`docs/knowledge-base/`) — 9,717 lines, 11 files
Built up as foundation for the Wing project and future reuse. Structure and contents:

| Path | Lines | Purpose |
|------|-------|---------|
| `README.md` | 220 | Master index with how-to-use and source attribution |
| `01-live-audio-ai/Behringer-WING-Integration.md` | 401 | USB/SoundGrid/Dante connectivity, measured latencies, failover rules |
| `01-live-audio-ai/AI-Plugins-In-Live-Sound.md` | 775 | 4 AI techs + key skills + plugin matrix |
| `02-event-ops-framework/Core-Skills-Overview.md` | 1,182 | FOH, ROS, crisis protocol |
| `02-event-ops-framework/Open-Source-Playbooks-Reference.md` | 986 | CNCF/DevOpsDays/Mozilla references |
| `03-event-type-sops/Corporate-B2B-Events.md` | 998 | Speaker ready room, dual-laptop redundancy |
| `03-event-type-sops/Tech-Expos-Hackathons.md` | 1,445 | 3-VLAN network, demo fallback |
| `03-event-type-sops/Live-Entertainment-Shows.md` | 767 | SMPTE TC, playback redundancy, rigging, IEM rules |
| `04-templates-and-matrices/Master-Run-Of-Show-ROS.md` | 748 | 3 full example ROSs (corporate/launch/concert) |
| `04-templates-and-matrices/Technical-Rider-Spec.md` | 1,699 | 3 example riders (Acme AGM/Vega Falls/Helios Cloud Summit) |
| `04-templates-and-matrices/Risk-Contingency-Matrix.md` | 496 | 55 scenarios + escalation chain |

**The knowledge base is the user's reuse asset — preserve it. Do not move, delete, or rewrite it without asking.**

### Git state
Repo is `git init`-ed but **there are no commits**. Working tree has the files listed but no history. If the next session wants to roll back, it cannot via git — backups, if any, are external.

---

## 3. Where We Are in the Brainstorming Skill

The brainstorming skill enforces a HARD-GATE: do NOT implement before the design doc is written, reviewed, and approved. The next session must respect this. Current status:

| Checklist item | Status | Notes |
|----------------|--------|-------|
| 1. Explore project context | ✓ done | `.snap` files analysed; two-version schema (snapshot.10 / snapshot.11) confirmed |
| 2. Ask clarifying questions | ✓ done | 5 AskUserQuestion calls; answers recorded below in §4 |
| 3. Propose 2-3 approaches | ✓ done | A (structural), B (semantic baked-in), C (Hybrid). **User chose C.** |
| 4. Present design sections | ⚠ partial | Phases 1–5 of design presented; user did not formally approve before pivoting to knowledge-base building. Re-confirm approval when resuming. |
| 5. Write design doc | ✗ NOT DONE | **This is the next concrete deliverable.** |
| 6. Spec self-review + user review | ✗ pending | |
| 7. Invoke writing-plans skill | ✗ pending | **Only skill to invoke next.** Do not skip to implementation. |

**The terminal state of brainstorming is invoking writing-plans. Nothing else.**

---

## 4. Locked Design Decisions (from clarifying questions)

These answers are final. Do not re-litigate them with the user.

1. **End-vision:** "Claude mix live show dựa trên voice chat, lyrics, bài hát" — but **decomposed**. Phase 1 = scene file parser only.
2. **Phase 1 scope:** "Chỉ scene file parser (foundation)" — read `.snap`, no OSC, no real-time mixer control.
3. **Claude interface:** "Cả skill + MCP + CLI" — three delivery layers all wrap the same Python library.
4. **API surface:** Channel summary, full dump, scene diff, routing summary, advisory. **Plus** "truy vấn và phân tích, dựa vào hiểu biết về mixing (học từ các repo đang có trên mạng) và ToanAZ dạy." — advisory must be extensible with user's mixing knowledge.
5. **Architecture:** **Hybrid (Approach C)** — schema descriptors as YAML data (not Python code), advisory module as YAML rules (not Python code), pure structural parser as the core. User-extensible without code changes.

---

## 5. Premise Corrections to Preserve

Two corrections were made during this session that the next session must NOT undo. They came from agent analysis of the user's source materials:

### 5.1 Dugan automix is NOT AI
The user-provided text described "Smart Auto-Gain & Dynamic Balancing" as an AI technology. The Dugan automix algorithm (1989) is **deterministic gain-sharing** — pure math, no ML. Modern products marketed as "AI automix" (Shure IntelliMix, Yamaha ADECIA, Q-SYS) use ML only for voice-activity detection and hand off to conventional Dugan for the gain math.

**Implication for our parser:** the advisory rule pack should not claim "AI automix" exists where it doesn't. Stick to "automix available" and let the user know which type (Dugan / native Dugan / not available).

### 5.2 Polar pattern is NOT chosen by frequency range
The user's microphone section in the brainstorm originally implied "low-freq → omni, high-freq → cardioid." This is wrong. Counter-examples:

- Kick and bass cab (lowest frequency sources) use **cardioid** for isolation
- Drum overheads and orchestral ambience (highest frequency sources) often use **omni** for flat response and no proximity effect
- Lavalier and handheld cover the same speech band but take opposite patterns for different reasons

The Core-Skills-Overview.md was already rewritten by an agent to flag this. **Do not reintroduce the mistake** when describing mic spectral routing.

---

## 6. Design Sections Already Presented

Phases 1–5 of the design were drafted in conversation. The full content lives in the conversation transcript (387k tokens — too large to inline here), but the headings and key parameters are:

### Phase 1 — Architecture overview
5 layers: Delivery (CLI + MCP + Skills) → Query (Python API) → Schema (YAML descriptors) → Core Parser (stdlib JSON only) → Advisory (YAML rules, separate)

### Phase 2 — Schema descriptors
YAML descriptors under `wing_parser/descriptors/` — `channels.yaml`, `buses.yaml`, `proc.yaml`, `eq_models.yaml`, `proc_chain.yaml`, `tap_points.yaml`, `io.yaml`. Hot-reload on restart.

### Phase 3 — EQ model awareness (NEW, discovered from `WING_Series_Manual_Knowledge_Base.md`)
EQ `mdl` field selects model; band count varies:
- WING EQ (6-band parametric) — `STD`
- GEQ (31-band graphic)
- SOUL Analog (4-band) — `SOUL`
- Even 88-Formant (4-band)
- Even 84 (3-band)
- Mach EQ4 (6-band with AIR FREQ)

**Parser must NOT assume 6-band always.** Switch band count on `eq.mdl`.

### Phase 4 — proc chain decoder
`proc: "GEDI"` is an encoded string of active processing blocks (G=Gate, E=EQ, D=Delay, I=Insert). Decode via YAML map at `descriptors/proc_chain.yaml`.

### Phase 5 — Query layer API (Python)
- `WingScene.load(path)` → auto-detects snapshot.10 / snapshot.11
- `scene.get_channel(5)` → `Channel` with `.fader_dB`, `.proc_chain`, `.eq.bands`, `.sends`, `.icon_label`, etc.
- `scene.routing.summary()` → orphans, alt-sources-used, outputs-routed
- `scene_a.diff(scene_b)` → per-channel changes with magnitudes
- `scene.advisory.run("diagnostic")` → list of `Finding` objects

### Phase 5 add-on — Override system (from mastering-engineer skill study)
User-level overrides at `~/wing-skill/overrides/mixing-presets.yaml` apply per-show or per-genre. Base rules → override rules (override wins). User edits YAML; no Python changes needed.

### Phase 6 — Delivery layer (5 Claude Skills, 5 MCP tools, 5 CLI commands)
See §10 for the directory layout.

---

## 7. Critical Design Constraints

These are not suggestions. They are constraints that came out of the research and must be preserved.

### 7.1 The IEM comb-filtering rule
`docs/knowledge-base/01-live-audio-ai/Behringer-WING-Integration.md` and `docs/knowledge-base/03-event-type-sops/Live-Entertainment-Shows.md` both enforce:
- **Never route USB/SoundGrid-processed audio to IEM mixes** if RTL > 2 ms
- Only SoundGrid (0.8–1.2 ms) is IEM-safe by default
- 7.8 ms USB RTL causes comb filtering at 128 Hz / 384 Hz / 640 Hz — vocal sounds "underwater"

The parser's advisory module should have a rule that flags any scene where `card_in` is routed to a bus that also feeds an IEM mix.

### 7.2 IEM-specific bus protection
Phase 2 will need a "Scene Safe" mechanism on IEM buses. Phase 1 parser should at least be able to *identify* IEM bus routes so Phase 2 can mark them safe.

### 7.3 Snapshot version awareness
Two schema versions exist in the wild:
- `snapshot.10` (Wing-Edit 3.2.1) — older firmware
- `snapshot.11` (Wing-Edit 3.3.3) — newer, has 2 cards keys vs 1, more config fields

Parser must branch on `type` field at load time. Never assume one schema.

### 7.4 -144 sentinel
The numeric `-144` represents −∞ dB (muted/off). Parser must convert at the data layer, not the presentation layer. Internal API uses `fader_dB: -10.0` (real float), not the sentinel.

### 7.5 OSC path conventions (for Phase 2)
Extracted from `bitfocus/companion-module-behringer-wing`:
- Read-only fields prefixed with `$` (`$solo`, `$name`, `$vph`)
- Matrix sends use `/send/MX{n}` (not `/send/{n}`)
- Tap points are integers 1–6 (map via YAML: INPUT, FILTER, TAP3, PRE_FDR, POST_FDR, POST_PROC)
- Processing chain is encoded string in `proc` field

---

## 8. What Phase 1 Delivers

Per user approval, Phase 1 in-scope:

| Deliverable | Path | Notes |
|-------------|------|-------|
| Python library | `wing_parser/` | Core + Query + Advisory |
| CLI | `wing_parser/cli.py` | 5 commands: analyze, channel, diff, routing, doctor |
| MCP server | `wing_parser/mcp_server.py` | 5 tools (FastMCP, stdio) |
| Claude Skills (5) | `skills/wing-{analyze,channel,diff,routing,doctor}/SKILL.md` | Mirror ableton-skills pattern |
| Schema YAML | `wing_parser/schema/snapshot.{10,11}.yaml` + `common.yaml` | Version-aware |
| Descriptors | `wing_parser/descriptors/*.yaml` | 7+ files |
| Advisory rules | `wing_parser/advisory/rules/diagnostic.yaml` | Problem-solution structure |
| Override system | User's `~/wing-skill/overrides/` | Loaded on top of base rules |
| Tests | `tests/` with 2 fixtures + 3 synthetic | pytest |
| Example scripts | `examples/` | 3 scripts |

Phase 1 OUT-of-scope (defer to later cycles):
- OSC connection to real mixer
- Audio analysis (LUFS/LRA measurement — needs audio input)
- Write back to mixer
- Voice/lyric input pipeline
- AI decision-making for live mixing

---

## 9. Success Criteria for Phase 1

The user will consider Phase 1 complete when:

- [ ] Loads both `factory-scene.snap` and `example-Vu.snap` without error
- [ ] 5 query types all return valid output
- [ ] CLI commands work standalone
- [ ] MCP tools callable from Claude Code session
- [ ] 5 Skills trigger via slash command or natural language
- [ ] Advisory diagnostic rule runs correctly against example-Vu (should flag EQ cut -9.4 dB @ 242 Hz as potentially too deep for vocal)
- [ ] Tests pass with ≥80% coverage on `core/`

---

## 10. Project Directory Layout (proposed)

```
wing-skill/
├── pyproject.toml                    # Poetry/uv-managed
├── README.md
├── CHANGELOG.md
├── LICENSE                           # MIT
├── wing_parser/
│   ├── __init__.py
│   ├── core/
│   │   ├── loader.py                 # load + version detect
│   │   ├── normalizer.py             # -144 → -∞, str keys → int
│   │   ├── validator.py
│   │   └── models.py                 # dataclasses
│   ├── query/
│   │   ├── channel.py
│   │   ├── routing.py
│   │   ├── diff.py
│   │   └── advisory.py
│   ├── schema/
│   │   ├── snapshot.10.yaml
│   │   ├── snapshot.11.yaml
│   │   └── common.yaml
│   ├── descriptors/
│   │   ├── channels.yaml
│   │   ├── buses.yaml
│   │   ├── proc.yaml
│   │   ├── eq_models.yaml            # NEW — per-model band structures
│   │   ├── proc_chain.yaml           # NEW — "GEDI" decoder
│   │   ├── tap_points.yaml           # NEW — ptap int → human
│   │   └── io.yaml
│   ├── advisory/
│   │   └── rules/
│   │       └── diagnostic.yaml       # problem-solution structure
│   └── mcp_server.py
├── skills/                           # For ~/.claude/skills/wing/
│   ├── wing-analyze/SKILL.md
│   ├── wing-channel/SKILL.md
│   ├── wing-diff/SKILL.md
│   ├── wing-routing/SKILL.md
│   └── wing-doctor/SKILL.md
├── tests/
│   ├── test_parser.py
│   ├── test_query.py
│   ├── test_advisory.py
│   └── fixtures/
│       ├── factory.snap
│       ├── show-vu.snap
│       └── synthetic/
│           ├── empty.snap
│           ├── all-comp.snap
│           └── bad-version.snap
├── docs/
│   ├── superpowers/
│   │   └── specs/
│   │       └── 2026-08-13-wing-scene-skill-design.md   # NEXT DELIVERABLE
│   └── knowledge-base/               # already exists, do not move
└── examples/
    ├── analyze_vu.py
    ├── diff_factory_vs_vu.py
    └── advisory_check.py
```

---

## 11. Where to Resume — Concrete Next Steps

**Step 1: Re-confirm with the user.** The next session should ask: "Last session we presented 5 design phases for the Wing scene parser. You pivoted to building a knowledge base before approving the design. Would you like to (a) approve the design and write the spec now, (b) revise the design based on what you learned from the knowledge base, or (c) continue adding to the knowledge base?" **Do not assume approval.**

**Step 2: If approved, write the spec.** Save to `docs/superpowers/specs/2026-08-13-wing-scene-skill-design.md`. The spec should:
- Restate the 5-layer architecture
- Document the Hybrid (data-driven descriptors) decision with rationale
- Include the advisory rule YAML schema (problem-solution structure from mastering-engineer skill)
- Define success criteria (from §9 above)
- Explicitly list what is in-scope and out-of-scope for Phase 1

**Step 3: Spec self-review.** Run a fresh-eyes review for placeholders, contradictions, ambiguity, scope. Fix inline.

**Step 4: User review.** Ask the user to read the spec and approve before proceeding.

**Step 5: Invoke writing-plans skill.** This is the only correct next skill. Do not jump to implementation.

---

## 12. Open Questions for User

If the user wants to refine the design before spec is written, these are the unresolved decisions:

1. **Wing firmware version coverage:** Should Phase 1 cover only firmware 3.3.x, or also 3.2.x (snapshot.10) and earlier? Both example files cover 3.2 and 3.3; we have not tested 3.0–3.1.
2. **EQ model descriptors depth:** For 10+ EQ models, do we ship full per-model band structures (larger YAML) or just `WING EQ (6-band)` and leave others to user expansion?
3. **Advisory rule pack scope:** Phase 1 ships with how many baseline rules? Options: 5 (smoke test), 15 (covers most channel types), 30+ (covers genres). User extensible either way.
4. **MCP tool granularity:** 5 tools (one per query type) or 1 mega-tool with action parameter? Lean toward 5 for clarity.
5. **Override directory location:** `~/wing-skill/overrides/` (per-mastering-engineer pattern) or XDG-standard `~/.config/wing-skill/overrides/`? User preference.
6. **Test framework:** pytest (standard), unittest (stdlib only), or something else?

---

## 13. Things That Went Wrong (so next session doesn't repeat them)

### 13.1 Premise fabrication
In the original brainstorm, I introduced the "frequency-based mic pattern selection" rule. It was wrong and would have shipped into the knowledge base if an agent hadn't caught it. **Lesson:** When generating rules from first principles during brainstorm, flag them as "to be validated against industry sources" rather than presenting them as fact.

### 13.2 Parallel agent overwrite
One sub-agent writing the Live-Entertainment SOP **overwrote** the 411 lines already written instead of appending. The file had no git history, so recovery meant re-creating §1-§2 from memory. **Lesson:** Before dispatching agents to write into the same directory, give each one an explicit `<!-- CURSOR -->` insertion marker and verify with `tail -3` before AND after. Better: split the file into separate docs from the start.

### 13.3 Quota failure mid-session
6 of 7 agents failed with 403 quota errors in the middle of writing. **Lesson:** When dispatching expensive work in parallel, ensure sufficient quota first. Quote budget visible in `/context`. Check before launching.

### 13.4 Stub skill installation rejected
The user's mcpmarket install link (`mastering-engineer` skill from MCP Market) was either expired or invalid. I extracted the skill from a tar.gz archive the user uploaded manually instead. **Lesson:** Don't trust install links blindly; the user may have a backup.

### 13.5 WebSearch noise
WebSearch returns mostly noise for specific technical queries. WebFetch on known repos (`raw.githubusercontent.com`) was much more reliable. **Lesson:** For technical extraction, fetch raw files directly rather than rely on search engine summaries.

---

## 14. Quick-Reference Cheat Sheet for Next Session

**Project:** Behringer Wing `.snap` scene parser, Phase 1 only
**Approach:** Hybrid — pure Python parser + YAML descriptors + YAML advisory rules
**Deliverables:** Python library + CLI + MCP server + 5 Claude Skills
**Knowledge base:** 11 files, 9,717 lines, in `docs/knowledge-base/` — preserve, do not move
**Spec location (next deliverable):** `docs/superpowers/specs/2026-08-13-wing-scene-skill-design.md`
**Next skill to invoke:** `superpowers:writing-plans` (only after spec approved)
**Lock and load:** The brainstorming skill's HARD-GATE forbids implementation before spec approval. Respect it.

**Hard constraints (don't violate):**
1. Phase 1 scope = scene file reading only; no OSC, no real-time control
2. Hybrid approach = descriptors/advisory as data, not Python code
3. IEM comb-filtering rule applies (no AI/USB-processed audio to IEM)
4. EQ band count varies by `eq.mdl` — don't hardcode 6
5. `proc: "GEDI"` is encoded — decode via YAML, don't regex-split

**Talk to the user in Vietnamese** unless they switch languages. They appreciate detailed, technical responses and have explicitly asked for maximum detail in writing. They will spot and correct errors. They expect corrections to be flagged honestly.

---

**End of handoff. Save the user's time by reading this first when you wake up.**