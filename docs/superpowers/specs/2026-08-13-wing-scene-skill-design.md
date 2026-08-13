# Wing Scene Parser — Phase 1 Design Spec

**Date:** 2026-08-13
**Status:** Approved for planning
**Scope:** Phase 1 only — read `.snap` scene files. No OSC, no mixer control, no audio analysis.

---

## 1. Purpose

Build a Python library that reads Behringer WING `.snap` scene files and answers questions about them, delivered three ways: a CLI, an MCP server, and five Claude Skills. On top of the parser sits an advisory module that flags likely misconfigurations — encoding both generic industry practice and ToanAZ's personal mixing judgement, refined over time through a human-curated feedback loop.

This is the foundation for later phases (OSC control, AI-assisted mix preparation). Those are explicitly out of scope here.

---

## 2. Evidence base

Every structural claim below was verified against the two real scene files in `user-files/`:

| File | Type | Size | Notes |
|---|---|---|---|
| `factory-scene.snap` | `snapshot.10` | 353 KB | Factory default, all faders at −144 |
| `example-Vu.snap` | `snapshot.11` | 922 KB | Real show scene, 34 named channels |

Supporting sources: `user-files/WING_Series_Manual_Knowledge_Base.md` (manual extract, firmware 3.1) and `docs/knowledge-base/` (11 files, 9,717 lines of live-audio operational knowledge).

### 2.1 Verified file structure

Both versions share an identical `ae_data` / `ce_data` payload — 13 and 9 top-level keys respectively, with byte-identical channel key sets. The two schema versions differ in exactly three places, all in the outer envelope:

| | `snapshot.10` | `snapshot.11` |
|---|---|---|
| Creator metadata keys | `creator_fw`, `creator_sn`, `creator_version`, `created` | `creator`, `creator_vers` |
| Globals blocks | `ae_globals`, `ce_globals` present | absent |
| `ae_data.cards` | `wlive` | `wlive`, `wmadi` |

Counts are fixed: 40 input channels, 8 aux, 16 bus, 4 main, 8 matrix, 16 DCA, 8 mute groups.

### 2.2 Field findings that shape the design

**`tags` is a mini-language.** Channels, buses, and auxes each carry a `tags` string using `#D<n>` for DCA membership and `#M<n>` for mute-group membership, comma-separated: `"#D8,#D10"`. Membership is stored on the member, not the group — the parser must build a reverse index to answer "who belongs to DCA 1".

**Scene Safe lives in the file.** `ce_data.safes` is a positional bitmap — one character per channel/bus/etc. This contradicts the earlier assumption that Scene Safe was console-global and unreadable until Phase 2. Scene-safe rules are checkable in Phase 1.

**Phantom, gain, and polarity are on the source, not the channel.** A channel points at its source via `in.conn` (`{grp: "A", in: 8}`); the electrical properties live at `io.in.A["8"]` (`{g: 5, vph: false, pol: false, …}`). Any rule about phantom power, preamp gain, or source polarity requires a join.

**Polarity exists at two levels.** `ch.in.set.inv` (channel) and `io.in.<grp>[n].pol` (source). Inverting both equals inverting neither.

**Automix is in `postins`.** `postins` carries `{on, mode: "AUTO_X"|"AUTO_Y", ins, w}` — the INS 2 slot, two groups X/Y, per-channel weight. This confirms the correction in `docs/knowledge-base/03-event-type-sops/Corporate-B2B-Events.md` §4.4 and contradicts the "8-channel automix groups" claim in `01-live-audio-ai/AI-Plugins-In-Live-Sound.md`. Use the Corporate version.

**`ptap` is a string, not an integer.** Observed value `"5"`, not `5`.

**EQ model distribution is narrow.** Across both files: 150 of 152 EQ blocks use `mdl: "STD"`; 2 use `"PULSAR"`. Dynamics: `COMP` and `CMB`. Gates: `GATE` only. The remaining nine EQ models documented in the manual never appear.

**Send tap points are per-send.** Each `ch.send[n]` carries `{on, lvl, pon, mode, plink, pan}` where `mode` is `"GRP"` / `"POST"` / `"TAP"`.

---

## 3. Architecture

Five layers. Data flows upward; no layer reaches past its neighbour.

```
Delivery      CLI  ·  MCP server  ·  5 Claude Skills
                          │
Query         Python API — Channel, Bus, Routing, Diff, Advisory
                          │
Schema        common.yaml + versions.yaml  ·  descriptors/*.yaml
                          │
Core          loader → version detect → normalize → validate → dataclasses
                          │
Input         .snap file (stdlib json only)
```

Advisory hangs off the Query layer as a separate module with its own three-tier rule resolution (§6).

### 3.1 Core

Pure standard library. `json.load`, then:

- **Version detect** — branch on the top-level `type` field.
- **Normalize** — convert the `-144` sentinel to `-inf` at the data layer, not the presentation layer. String numeric keys (`"1"`…`"40"`) become integers. `ptap` string becomes an enum.
- **Validate** — check section counts and required keys; collect anomalies rather than raising, so a partially-malformed file still yields useful output.
- **Models** — frozen dataclasses. `Channel`, `Bus`, `Main`, `Matrix`, `Dca`, `MuteGroup`, `Source`, `Send`, `Eq`, `Gate`, `Dyn`, `Filter`.

### 3.2 Schema

Two files, not two full schemas. Because `ae_data`/`ce_data` are identical across versions (§2.1), duplicating a full schema per version would be ~95% copied content and a standing invitation to update one side and forget the other.

**`schema/common.yaml`** — the structural map shared by all versions: where each section lives, its expected count, and each field's type, unit, sentinel, and descriptor reference.

**`schema/versions.yaml`** — the delta only, roughly a dozen lines:

```yaml
snapshot.10:
  label: "Wing-Edit 3.2.x"
  meta_keys: [creator_fw, creator_sn, creator_model, creator_version, creator_name, created]
  has_globals: true
  cards: [wlive]
snapshot.11:
  label: "Wing-Edit 3.3.x"
  meta_keys: [creator, creator_vers, creator_model, creator_name]
  has_globals: false
  cards: [wlive, wmadi]
unknown_version: warn_and_parse_as_latest
```

Adding a future firmware means appending five lines here.

### 3.3 Descriptors

Semantic meaning as data, so it can be extended without touching Python. Distinct from schema: schema says *where the data is and whether it is well-formed*; descriptors say *what it means*.

| File | Contents |
|---|---|
| `channels.yaml` | Channel-section metadata |
| `buses.yaml` | Bus/main/matrix metadata |
| `proc.yaml` | Processing-block metadata |
| `proc_chain.yaml` | Decoder for the `proc` string (`"GEDI"` → Gate, EQ, Delay, Insert) |
| `eq_models.yaml` | Per-model band structure — see §3.4 |
| `tap_points.yaml` | `ptap` value → human name (INPUT, FILTER, TAP3, PRE_FDR, POST_FDR, POST_PROC) |
| `tags.yaml` | Grammar for the `tags` field (`#D<n>`, `#M<n>`, comma-separated) |
| `safes.yaml` | Positional-bitmap decoding for `ce_data.safes` |
| `io.yaml` | Source-group metadata (LCL, AUX, A, B, C, SC, USB, CRD, MOD, PLAY, AES, USR, OSC) |

### 3.4 EQ model handling

`eq_models.yaml` ships one complete entry: `STD` (WING EQ — low shelf, four parametric bands, high shelf, addressed as `lg/lf/lq`, `1g/1f/1q` … `4g/4f/4q`, `hg/hf/hq`).

Any other `mdl` value — `PULSAR`, `SOUL`, `GEQ`, and the rest — produces an `Eq` object with `bands = None`, `raw` populated with the untouched dict, and a `descriptor_missing` warning on the parse result. Advisory rules that need band data skip such channels rather than guessing.

This matters because `PULSAR` is a Pultec-style passive EQ whose parameters are boost/attenuate pairs, structurally unlike `STD`. Applying the `STD` band layout to it would silently produce wrong numbers on the two channels that use it.

### 3.5 Source resolution

`Channel.source` resolves `in.conn.{grp,in}` against `io.in.<grp>[n]` and exposes `.gain_dB`, `.phantom`, `.polarity`, `.mode`, `.name`. `Channel.alt_source` does the same for `in.conn.{altgrp,altin}`, returning `None` when `altgrp == "OFF"`.

`Channel.effective_polarity` is the XOR of `in.set.inv` and `source.polarity`.

---

## 4. Source-type classifier

### 4.1 Why it exists

Most useful advisory rules are conditional on what a channel *is*. The rule "every speech channel needs a high-pass filter" reads `flt.lc` directly from the file, but "is this a speech channel" is not in the file at all — it exists only in the name a human typed.

The classifier turns names into typed guesses with explicit uncertainty.

### 4.2 Real-world input

The 34 named channels in `example-Vu.snap` span the full difficulty range:

- **Clean keyword match:** `Kick In`, `Snare Top`, `Snare Bot`, `Tom 8`, `Floor 16`, `Hihat`, `OH`, `Bass`, `A.Guitar`, `E.Guitar 1`, `Key 1`, `Click`, `BOH Talk`
- **Needs a compound rule:** `Mic 1 VOX IEM1` (VOX = vocal; IEM1 = monitor destination), `LED PLAYBACK`, `M8 MC`
- **Not inferable:** `Mic 4`, `Mic 5`, `HS4`, `SPD`, `My Lap`
- **Non-English:** `M6 D.PHOI` — Vietnamese "dự phòng", a backup channel
- **Dirty data:** `FOH Tak` (typo for Talk); trailing spaces on `Kick In `, `A.Guitar `, `SPD `

A rigid matcher silently skips the most operationally important channel in that list — the backup.

### 4.3 Design

```
name → normalize (trim, casefold, collapse whitespace)
     → pattern match against classifier/patterns.yaml
     → confidence score
          c ≥ 0.8        → classified; conditional rules run normally
          0.4 ≤ c < 0.8  → classified with low confidence; findings are worded as
                           questions ("channel 6 appears to be a backup — if so, …")
          c < 0.4        → unknown; conditional rules skip this channel
```

Unclassified channels are collected into a separate report section — "N channels could not be classified; name them more descriptively or declare them manually" — rather than being silently dropped.

### 4.4 Buses are classified too

The same mechanism classifies buses, mains, and matrices by name, because several rules depend on a bus's *role* rather than its number. Roles: `monitor` (wedge or IEM), `fx`, `subgroup`, `record`, `stream`, `matrix_fill`, `unknown`.

The bus names in `example-Vu.snap` illustrate why this cannot be positional: `MON VOX`, `MON L`, `MON R`, `SIDEFILL`, and `HEADSET` are monitor-role buses scattered across positions 5–10, while `ROOM`, `HALL`, `DELAY`, `HAHA`, `DRUM FX`, and `BAND FX` are effects returns. Nothing in the file marks the distinction — only the names carry it.

Bus classification uses the same confidence thresholds, the same cache, and the same optional Claude fallback as channel classification. `classifier/patterns.yaml` holds both pattern sets.

### 4.5 Two things called "tap point"

Distinguish them, because rules depend on the difference:

- **`Channel.tap_point`** — the channel-level `ptap` field, which sets where `TAP`-mode sends draw their signal.
- **`Send.mode`** — per-send, one of `GRP` / `POST` / `TAP`, deciding whether that individual send is a subgroup feed, post-fader, or drawn from the channel's tap point.

Rules about monitor sends read `Send.mode`, not `Channel.tap_point`.

**Cache.** Every resolved classification, whatever its origin, is written to the user's overrides file with its source and confidence. Reruns read from cache. A given channel name costs at most one classification in its lifetime.

**Optional Claude fallback.** When the pattern matcher scores below threshold and an API key is available, the library calls the Anthropic API (Python `anthropic` SDK, `claude-opus-5`) with the channel name plus surrounding context, and caches the answer. This is the one place in the system where an LLM participates.

With no API key, no network, or the feature disabled, the classifier returns `unknown` and the app continues — see §8.

---

## 5. Query API

```python
scene = WingScene.load("example-Vu.snap")     # auto-detects version

ch = scene.channel(8)
ch.name                  # "M8 MC"
ch.fader_dB              # -7.9
ch.muted                 # False
ch.source.phantom        # False
ch.effective_polarity    # False
ch.eq.model              # "STD"
ch.eq.bands[2].freq      # 241.1
ch.proc_chain            # [GATE, EQ, DELAY, INSERT]
ch.tap_point             # POST_FDR
ch.dcas                  # []      (from tags)
ch.mute_groups           # []      (from tags)
ch.scene_safe            # False   (from ce_data.safes)
ch.source_type           # SourceType(kind="speech.mc", confidence=0.85)

scene.dca(1).members             # reverse index from tags
scene.routing.summary()          # orphans, alt-sources in use, outputs routed
scene.routing.sends_to(bus=8)    # every channel feeding bus 8, with tap point
scene_a.diff(scene_b)            # per-field changes with magnitudes
scene.advisory.run()             # list[Finding]
```

`Finding` carries: `rule_id`, `layer` (which of the three tiers decided it), `severity`, `target` (channel/bus/output), `message`, `evidence` (the field values that triggered it), and `confidence` (propagated from the classifier when a conditional rule fired).

---

## 6. Advisory module

### 6.1 Why three layers

Rules mined from the knowledge base are written as absolutes, because that is how training material teaches. Real shows have conditions the textbook never states, and treating a generic rule as truth turns the tool into a false-alarm generator.

Worked example. `docs/knowledge-base/02-event-ops-framework/Core-Skills-Overview.md` §3.4 states that all monitor sends must be pre-fader so FOH fader moves do not alter stage mixes, and calls post-fader monitor sends a common misconfiguration. ToanAZ's practice for a single shared band IEM mix is the opposite for most sources: guitar sends pre-fader, everything else post-fader, so the band hears the FOH balance while the guitarist keeps a stable guitar level. The exception is not a violation — it is a condition the generic rule omits.

### 6.2 Resolution order

```
base-rules/          Generic rules mined from docs/knowledge-base/. Shipped, not edited.
      ↓
toanaz/              Personal principles. Can disable base rules under stated conditions.
      ↓
shows/<name>.yaml    One-off exceptions for a specific show.
      ↓
   resolver → active rule set → findings (each tagged with its deciding layer)
```

### 6.3 Principle format

```yaml
- id: toanaz.iem-shared-band.guitar-prefader
  principle: "Shared band IEM: guitar sends pre-fader, all other sources post-fader"
  hardness: flexible            # hard | flexible
  applies_when:
    iem_mix_count: 1
    band_has_guitar: true
  supersedes: [G8]
  rationale: >
    The guitarist needs a stable guitar level regardless of FOH moves.
    Everything else should track the FOH balance so the band hears what
    the audience hears.
  source: ToanAZ, field practice
```

`hardness: hard` means the principle always applies. `hardness: flexible` means it applies only when `applies_when` matches. `supersedes` names the base rules it switches off while active.

### 6.4 Provenance is mandatory

Every finding records which layer produced it. Without that, a false positive is undiagnosable: the user cannot tell whether the base rule is too rigid or whether they simply have not declared their own principle yet — and the improvement loop breaks.

### 6.5 Base rules shipped in Phase 1

Three, chosen to exercise three different shapes of the rule schema. Each cites its knowledge-base source.

| ID | Rule | Needs classifier | Source | Behaviour on `example-Vu.snap` |
|---|---|---|---|---|
| **G8** | Sends to a monitor/IEM bus must be pre-fader | Yes — bus role | `Core-Skills-Overview.md` §3.4 step 2 | **Fires** — channel 8 (`M8 MC`) sends `mode: "POST"` to bus 8 (`MON VOX`) |
| **G7** | Every IEM bus must have a limiter engaged | Yes — bus role | `Technical-Rider-Spec.md` §4.1; `Core-Skills-Overview.md` §3.4 step 8 | **Fires** — bus 8 uses `dyn.mdl: "COMP"` at threshold −15, not a limiter |
| **E6** | A channel must not have both a gate and an active automix assignment | No | `AI-Plugins-In-Live-Sound.md` L383–385; `Corporate-B2B-Events.md` §4.4 | **Does not fire** — channel 8 has `gate.on: true` and `postins.mode: "AUTO_X"`, but `postins.on: false` |

The three exercise deliberately different paths. G8 and G7 both depend on bus-role classification (§4.4) and so also prove the classifier-dependency plumbing; G8 is additionally the rule ToanAZ's first personal principle will override, exercising `supersedes` from day one. E6 needs no classifier and is deliberately a rule that stays quiet — it proves the engine reads enable flags, not just configuration, and does not manufacture findings.

Because `MON VOX` classifies as a monitor bus on a clean `MON` keyword match, G8 and G7 fire at high confidence on this file. On a scene where the monitor bus were named something opaque, both would correctly fall silent rather than guess.

### 6.6 Rule format

```yaml
- id: G8
  title: "Monitor send is post-fader"
  severity: warning
  source: "docs/knowledge-base/02-event-ops-framework/Core-Skills-Overview.md §3.4 step 2"
  rationale: >
    Post-fader monitor sends mean a FOH fader move changes what the performer
    hears. The knowledge base calls this a common and disruptive
    misconfiguration.
  requires_classifier: true          # bus role, see §4.4
  when:
    for_each: channel.sends
    where:
      destination_bus.role: monitor
      mode: POST
  message: >
    Channel {channel.number} ({channel.name}) sends post-fader to
    {bus.number} ({bus.name}), which appears to be a monitor bus.
```

Where knowledge-base sources disagree, the chosen value and the reason are recorded in the rule. The agent survey found six such conflicts, including lectern gate threshold (−45 / −48 / −55 / −60 across four documents) and ring-out notch Q (8–10 / 8–12 / 20–30). Silently picking one leaves nobody able to reconstruct the decision later.

### 6.7 Rules deliberately excluded

Roughly ten candidate rules from the knowledge base require measurement that no scene file contains — gain staging at −18 dBFS, LUFS and LRA targets, RT60, real-world round-trip latency, NOM meter readings, crest factor. These are out of scope for Phase 1. Including them would create the impression the tool checks things it cannot see.

---

## 7. Feedback loop

There is no machine learning. The mechanism is Claude-assisted curation with the human holding every decision.

1. Advisory runs; each finding gets a stable ID.
2. ToanAZ marks findings via `wing feedback <id> --verdict correct|false-positive|irrelevant --note "..."`.
3. The verdict is appended to a JSONL log alongside the scene filename, timestamp, rule ID, deciding layer, and note.
4. Periodically, Claude reads the log plus the principle files and *proposes* YAML edits.
5. ToanAZ approves or rejects.

Step 4 runs conversationally in a Claude Code session in Phase 1 — no dedicated command. The log format is designed to be read directly.

The value of the log is pattern detection across time: seven rejections of G8, all in shows with exactly one IEM mix, is the signal that a conditional principle should be written.

---

## 8. Anthropic API integration

One integration point only: the classifier fallback in §4.3.

**Boundary.** The parser and the advisory engine are deterministic. The same `.snap` file must always produce the same findings. An LLM inside the rule-evaluation path would break that and destroy the user's ability to trust the output. Claude sits at the edge — turning an ambiguous input (a human-typed name) into structured data — and nowhere else.

**Offline is the default assumption.** This is a tool for live sound, used in venues where the network is unreliable or absent. With no API key, no connectivity, or the feature switched off:

- the classifier returns `unknown` for names the pattern matcher cannot resolve
- rules with `requires_classifier: true` skip those channels
- all `requires_classifier: false` rules run normally
- unclassified channels are listed in the report

Nothing errors and nothing blocks.

**Cost.** Because every classification is cached to YAML, a new show costs a handful of calls and then nothing. There is no per-parse API cost.

**Model.** `claude-opus-5` by default, overridable in config.

---

## 9. Knowledge and override file locations

Resolution order, first match wins:

```
1. $WING_KNOWLEDGE_DIR         environment variable — overrides everything
2. ./knowledge/toanaz/         in-repo default, version-controlled
3. ~/.config/wing-skill/       XDG convention, for system installs
4. ~/wing-skill/               mastering-engineer layout, backward compatible
```

The in-repo default is deliberate: these principles are a long-lived asset, and git history shows how ToanAZ's judgement evolved and allows rollback. Setting one environment variable moves the whole knowledge set elsewhere with no code change.

Directory contents:

```
knowledge/toanaz/
├── principles.yaml        # personal mixing principles
├── classifier.yaml        # name → source-type overrides and cached classifications
├── feedback.jsonl         # append-only verdict log
└── shows/
    └── <show-name>.yaml   # one-off per-show exceptions
```

---

## 10. Firmware coverage

Guaranteed: `snapshot.10` (Wing-Edit 3.2.x) and `snapshot.11` (Wing-Edit 3.3.x), both with real sample files.

Unknown versions: warn, then attempt to parse using the newest known schema. Because the `ae_data` payload has been stable across the two observed versions, this is likely to work; the warning makes clear the result is unverified. Refusing outright would block the user the day Behringer ships new firmware.

Firmware 3.0–3.1 is not claimed. No sample files exist to verify against, and writing version-handling code from guesswork would be untested code masquerading as support.

---

## 11. Delivery layers

### 11.1 CLI

```
wing analyze  <file>                     overview + advisory findings
wing channel  <file> <n>                 full detail for one channel
wing diff     <file-a> <file-b>          per-field changes
wing routing  <file>                     routing map, orphans, tap points
wing doctor   <file>                     advisory only, grouped by severity
wing feedback <finding-id> --verdict ... record a verdict
```

### 11.2 MCP server

FastMCP over stdio. Five tools, one per query type: `wing_analyze`, `wing_channel`, `wing_diff`, `wing_routing`, `wing_doctor`.

Five separate tools rather than one tool with an `action` parameter: each carries its own description, so Claude selects by reading what the tool does instead of guessing a parameter value.

### 11.3 Claude Skills

Five skills under `skills/`, mirroring the CLI commands, each with a `SKILL.md` describing when to trigger and how to interpret the output.

---

## 12. Project layout

The existing repository root is the project root — `docs/knowledge-base/` and `docs/superpowers/specs/` already live there and do not move. Everything below is created alongside them.

```
<repo root>
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── LICENSE                              # MIT
├── wing_parser/
│   ├── __init__.py
│   ├── core/
│   │   ├── loader.py                    # load + version detect
│   │   ├── normalizer.py                # -144 → -inf, key coercion
│   │   ├── validator.py
│   │   └── models.py                    # dataclasses
│   ├── query/
│   │   ├── channel.py
│   │   ├── source.py                    # channel → source resolution
│   │   ├── routing.py
│   │   ├── diff.py
│   │   └── advisory.py
│   ├── classifier/
│   │   ├── matcher.py                   # pattern + confidence
│   │   ├── patterns.yaml
│   │   ├── cache.py
│   │   └── llm.py                       # optional Anthropic fallback
│   ├── schema/
│   │   ├── common.yaml
│   │   └── versions.yaml
│   ├── descriptors/
│   │   ├── channels.yaml
│   │   ├── buses.yaml
│   │   ├── proc.yaml
│   │   ├── proc_chain.yaml
│   │   ├── eq_models.yaml
│   │   ├── tap_points.yaml
│   │   ├── tags.yaml
│   │   ├── safes.yaml
│   │   └── io.yaml
│   ├── advisory/
│   │   ├── resolver.py                  # three-layer resolution
│   │   ├── feedback.py                  # JSONL log
│   │   └── base-rules/
│   │       ├── monitors.yaml            # G8, G7
│   │       └── dynamics.yaml            # E6
│   ├── cli.py
│   └── mcp_server.py
├── knowledge/
│   └── toanaz/                          # see §9
├── skills/
│   ├── wing-analyze/SKILL.md
│   ├── wing-channel/SKILL.md
│   ├── wing-diff/SKILL.md
│   ├── wing-routing/SKILL.md
│   └── wing-doctor/SKILL.md
├── tests/
│   ├── test_core.py
│   ├── test_query.py
│   ├── test_classifier.py
│   ├── test_advisory.py
│   └── fixtures/
│       ├── factory.snap
│       ├── show-vu.snap
│       └── synthetic/
│           ├── empty.snap
│           ├── all-comp.snap
│           └── bad-version.snap
├── docs/
│   ├── superpowers/specs/
│   └── knowledge-base/                  # existing, do not move
└── examples/
    ├── analyze_vu.py
    ├── diff_factory_vs_vu.py
    └── advisory_check.py
```

---

## 13. Success criteria

Phase 1 is complete when all of the following hold:

- [ ] Both `factory-scene.snap` and `example-Vu.snap` load without error
- [ ] `snapshot.10` and `snapshot.11` are both detected correctly; an unknown `type` warns and still parses
- [ ] `Channel.source.phantom` resolves correctly through `in.conn` → `io.in.<grp>[n]`
- [ ] `Channel.dcas` and `Channel.mute_groups` are correctly derived from the `tags` grammar; `scene.dca(1).members` returns the reverse index
- [ ] `Channel.scene_safe` reads correctly from the `ce_data.safes` bitmap
- [ ] A channel with `eq.mdl: "PULSAR"` yields `bands = None`, populated `raw`, and a `descriptor_missing` warning — no fabricated band values
- [ ] All five query types return valid output on both files
- [ ] The classifier assigns confidence to every named channel and lists the unclassifiable ones separately
- [ ] The classifier assigns `role: monitor` to buses 8/9/10 (`MON VOX`, `MON L`, `MON R`) and `role: fx` to buses 11–16
- [ ] With no API key set, the whole pipeline runs; the pattern matcher alone still resolves `MON VOX`, so **G8 and G7 still fire**. Only names the pattern matcher cannot resolve degrade to `unknown`
- [ ] Rule **G8** fires on `example-Vu.snap` channel 8 → bus 8, and the finding records its deciding layer
- [ ] Rule **G7** fires on bus 8
- [ ] Rule **E6** does **not** fire on channel 8, because `postins.on` is false
- [ ] A `toanaz/principles.yaml` entry with `supersedes: [G8]` and a matching `applies_when` suppresses the G8 finding, and the report says why
- [ ] `wing feedback` appends a well-formed record to `feedback.jsonl`
- [ ] All five CLI commands run standalone
- [ ] All five MCP tools are callable from a Claude Code session
- [ ] All five Skills trigger by slash command and by natural language
- [ ] `pytest` passes with ≥80% line coverage on `wing_parser/core/`

---

## 14. Out of scope for Phase 1

Deferred to later specs:

- OSC connection to a live mixer, in either direction
- Writing changes back to the console
- Audio analysis of any kind (LUFS, LRA, RT60, SPL, real-world latency measurement)
- Voice, lyric, or cue-sheet input pipelines
- The AI mix-decision layer

### 14.1 Note on the eventual auto-mix layer

Recorded here because it constrains later design, not because it is in scope.

Automatic mixing decomposes into two tiers with incompatible timing requirements. The **decision tier** — "this song needs the vocal 2 dB up; open the guitar bus at the solo" — is reasoning work at song or cue granularity, where an API round trip of several seconds is acceptable. The **real-time tier** — riding a fader through a phrase, sharing gain across six open microphones — needs sub-100 ms response, which no network round trip can deliver.

The console already solves the real-time tier. Dugan-style automix has been deterministic gain-sharing mathematics since 1989; it is not, and does not need to be, machine learning. The right architecture puts Claude in the decision tier and leaves execution to the console's own DSP — which is also how a human engineer works: prepare deliberately, then ride by reflex.

Phase 1 supports this by making the scene *understood* — classified, cached, and annotated with the user's own principles — so a later decision tier reads structured knowledge instead of re-deriving it from raw JSON on every cue.

---

## 15. Corrections carried forward

Two premise corrections from earlier work that must not be reintroduced:

**Dugan automix is not AI.** The algorithm is deterministic gain-sharing. Products marketed as "AI automix" use machine learning only for voice-activity detection and hand the gain mathematics to a conventional Dugan implementation. Advisory messages should say "automix available" and name the type, never claim AI where there is none.

**Polar pattern is not selected by frequency range.** Kick drums and bass cabinets are the lowest-frequency sources and use cardioid for isolation; drum overheads and orchestral ambience are the highest and often use omni for flat response and no proximity effect. Lavalier and handheld microphones cover the same speech band with opposite patterns for unrelated reasons. Do not reintroduce a frequency-to-pattern mapping anywhere in the descriptors or advisory text.
