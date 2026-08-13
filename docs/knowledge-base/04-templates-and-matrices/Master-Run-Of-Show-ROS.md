# Master Run of Show (ROS) — Template, Standards & Worked Examples

## Overview

This document is the canonical ROS template for all event types, plus three fully worked examples taken from real show shapes. It is a companion to `02-event-ops-framework/Core-Skills-Overview.md` §1, which covers ROS *theory* (variance math, recovery levers, department cue sheets). This document covers ROS *production*: the exact grid, what goes in each cell, who writes it, how cues are notated and called, and how revisions are controlled and distributed.

An ROS is not an agenda. An agenda says what happens. An ROS says **who executes what, on which cue, at which timecode, with which asset loaded**. One ROS, one show caller, one clock. If two documents disagree, the printed revision in the show caller's binder wins.

### How to use this file

| If you need to | Go to |
|----------------|-------|
| Understand the grid and fill it in | §1 |
| Write or call cues correctly | §2 |
| Assign the crew and know who owns which column | §3 |
| Budget buffer and transition padding | §4 |
| Copy a worked example — corporate keynote, 2 hr | §5 |
| Copy a worked example — product launch, 90 min | §6 |
| Copy a worked example — live concert, 3 hr | §7 |
| Name, lock, and distribute the document | §8 |

---

## 1. The ROS Template

### 1.1 Master Table Format

Every master ROS uses these eight columns, in this order, with no substitutions:

```
Time | Duration | Stage Activity | Visual Cue | Audio Cue | Lighting Cue | Owner | Notes
```

The grid is deliberately department-columnar rather than one-cue-per-row. A single row is one **moment** in the show, read horizontally so that every department sees its own action *and* the actions happening simultaneously beside it. This is what makes the master document callable: the show caller reads one row and knows the whole state of the stage.

Rows where a department has no action carry an em dash (`—`), never a blank. A blank cell is ambiguous — it reads as "not yet written". An em dash reads as "deliberately nothing", which is information.

### 1.2 Column Definitions

| # | Column | Format | Example | Written by | Definition & fill rule |
|---|--------|--------|---------|-----------|------------------------|
| 1 | **Time** | `T-MM:SS` pre-show, `T+H:MM:SS` show | `T-12:00`, `T+1:04:30` | Producer | Show-relative timecode. `T+00:00:00` is the first frame of show content (house-to-half, or downbeat), **not** doors. Show-relative survives a late start: if doors slip 8 minutes, every wall clock changes and every `T` value stays valid. Publish a single wall-clock anchor (`T+00:00:00 = 09:00:00`) in the header and let each station derive the rest. |
| 2 | **Duration** | `MM:SS` | `18:00` | Producer | Planned length of the row's activity. Feeds buffer math and the presenter countdown. `—` for instantaneous cues (a switcher take has no duration). Durations must sum, with buffers, to the contracted runtime — if they don't, the ROS is wrong, not the show. |
| 3 | **Stage Activity** | Plain language | "Dr. Sarah Chen keynote — AI platform roadmap" | Producer + Client | What the audience sees and hears, in language the client and talent can read without translation. Name real people with role: `Dr. Sarah Chen, CTO`. This is the only column shown on the client/talent agenda. |
| 4 | **Visual Cue** | `VID n GO` / `CAM` / `GFX` | `VID 12 GO — sizzle 02:30` | Video Director | Switcher takes, playback rolls, graphics in/out, projector shutters, LED wall content, IMAG source. Include asset filename or duration when a file rolls, so the operator can verify the right clip is armed. |
| 5 | **Audio Cue** | `SQ n GO` / channel ops | `SQ 8 GO — CH3 open, DCA2 up` | FOH Engineer | Playback starts, mute/unmute, DCA and scene moves, snapshot recalls, walk-in/walk-out music, stream bed. State the channel or DCA number, never "open her mic" — the console has numbers, use them. |
| 6 | **Lighting Cue** | `LX n GO` | `LX 24 GO — panel wash, 3s` | Lighting Designer | Console cue recall with fade time. Include the intent (`house to 30%`, `keynote special`) so a substitute operator can sanity-check the look against the row. Fade time is mandatory: `LX 24 GO` alone is under-specified. |
| 7 | **Owner** | Role + surname | `SM (Byrne)` | Producer | The single person accountable for the row completing. One name. Shared ownership means nobody owns it. The owner is not always the executor — the Stage Manager owns "talent in position" even though the talent walks. |
| 8 | **Notes** | Free text | "Hard stop — satellite window closes" | All | Edge cases, contingencies, RF channel, contract constraints, accessibility requirements, anything that changes a decision under pressure. First place to write what you learned in rehearsal. |

### 1.3 Fill Instructions & Build Order

Build the document in this order. Skipping ahead produces an ROS that looks finished and cannot be called.

1. **Skeleton (T-14 days).** Producer enters Time, Duration, Stage Activity only, from the client's agenda. Confirm the arithmetic closes against contracted runtime *before* any technical content is added.
2. **Buffer placement (T-14 days).** Insert buffer rows as first-class entries with IDs (`BUF-01`) per §4. Do this before technical cues, so buffers are structural rather than whatever space is left over.
3. **Department pass (T-7 days).** Video Director, FOH Engineer, and Lighting Designer each fill their own column. They do not edit each other's columns or the Time column. Conflicts surface to the Producer.
4. **Ownership pass (T-5 days).** Producer assigns one owner per row. Any row without an owner is deleted or escalated.
5. **Cue numbering lock (T-3 days).** Cue numbers are assigned in ascending order per department and frozen. From here, changes use point numbers (`LX 24.5`) rather than renumbering — see §2.4.
6. **Rehearsal markup (T-1 day).** Show caller annotates the printed master in pencil during rehearsal. Every pencil mark is reconciled into the document the same evening.
7. **FINAL lock and distribution (T-1 day, end of rehearsal).** Version stamped, printed, distributed per §8.

**Non-negotiable:** the ROS is written by the Producer and *called* by the Show Caller. If those are two people, the Show Caller has veto over any row they judge uncallable, and that veto is exercised during rehearsal, not during the show.

---

## 2. Cue Notation Standards

### 2.1 Prefixes

Cue IDs are spoken as **letter-group + number**, never as bare numbers. "Twelve, go" is how the wrong department fires.

| Prefix | Department | Typical action | Console / device |
|--------|-----------|----------------|------------------|
| `LX` | Lighting | Cue recall, house level, blackout | grandMA3, ETC Eos |
| `SQ` | Audio | Playback, mute/unmute, DCA, snapshot | DiGiCo Quantum, Behringer WING, QLab |
| `VID` | Video / playback | File roll, switcher take, graphics | ATEM 4 M/E, disguise, Playback Pro |
| `MIC` | RF / A2 | Mic handoff, fit, swap, RF standby | Shure Axient Digital, Wireless Workbench |
| `SM` | Stage Management | Talent standby, move, position | Comms only |
| `FLY` | Automation / rigging | Drape, riser, truss, reveal | Chain hoist desk, Kinesys |
| `SFX` | Pyro / atmospherics | CO2, confetti, haze, low fog | Le Maitre, MDG, Galaxis |
| `STR` | Stream | Scene change, slate, start/stop | vMix, OBS, Elemental |
| `TC` | Timecode | LTC start/stop, chase arm | Rosendahl mif4, Pro Tools |
| `BUF` | All | Buffer window entry | Comms only |

### 2.2 The Standby / GO Protocol

Two-phase, always. There is no single-phase cue in a professional show.

```
Caller:  "LX 12, SQ 5, VID 3 — standby."          ← 10-30 s before execution
LD:      "LX 12 standing by."                      ← each department confirms
A1:      "SQ 5 standing by."
V1:      "VID 3 standing by."
Caller:  "LX 12 GO. SQ 5 GO. VID 3 GO."            ← GO is the execution instant
```

Rules that are not stylistic preferences:

- **`GO` is the last word.** "GO on LX 12" fires early, because operators react to the word `GO`. Always `<CUE ID> GO`.
- **Standby is acknowledged, GO is not.** Acknowledging a GO puts speech on the channel during the execution window.
- **Never issue a GO to a department that has not confirmed standby.** Re-issue the standby instead.
- **Simultaneous cues are called in a fixed department order** — LX, SQ, VID — so operators learn the rhythm and hear their slot coming. Lighting leads because a light change is the least reversible and most visible if late.
- **One voice.** The show caller is the only person authorized to issue `GO`. Anyone else needing action asks the caller for it.
- **`HOLD`** stops the cue stack and freezes state. **`STANDBY CANCEL`** withdraws an armed standby without executing. Both are caller-only.

### 2.3 Numbering Scheme

Number ascending per department in show order, in gaps of one, from `1`. Do not number cues by segment (`LX 3.1` for segment 3) — segments get cut and renumbering cascades.

- **Point cues for insertions.** A cue added between `LX 24` and `LX 25` becomes `LX 24.5`. Two insertions: `24.3` and `24.6`. This keeps every previously printed sheet and every operator's memory valid.
- **Never reuse a number in one show file**, even for a deleted cue. A deleted cue is marked `LX 31 — DELETED rev 1.3` and left in the document. Silent deletion is how a department fires a cue that no longer exists.
- **Blocks of 100 per act** for multi-act shows: opener `LX 1-99`, headliner `LX 100+`. The number itself then tells the operator where they are.
- **Follow cues** (auto-executed after a parent, no separate GO) are marked `LX 45 → 46 auto 4s`. The caller does not call `46`; if they do, the operator has been trained to expect a cue that will not come.

### 2.4 Change Notation After Lock

Once cue numbers are frozen at T-3 days, all changes are notated in-line so a reader comparing two printed revisions can see history:

| Change | Notation | Example |
|--------|----------|---------|
| New cue | `[NEW rev x.y]` | `LX 24.5 GO — key up 1s [NEW rev 1.2]` |
| Deleted | `— DELETED rev x.y` struck through | `~~LX 31 GO~~ — DELETED rev 1.2` |
| Retimed | `[was MM:SS]` | `06:00 [was 04:30]` |
| Reassigned owner | `[was ROLE]` | `LD (Mbeki) [was V1]` |

---

## 3. Owner Role Definitions

The Owner column carries a role abbreviation plus surname: `SM (Byrne)`. Role first, because under pressure the role is what matters; surname second, because accountability attaches to a person.

| Abbrev | Role | Owns on the ROS | Decision authority | Does NOT own |
|--------|------|-----------------|--------------------|--------------|
| `PROD` | **Producer** | The document itself, runtime, content order, client relationship | Cuts content, approves overrun, signs the cut list, releases each revision | Live cue calling. A producer calling cues has two jobs and does neither |
| `SC` | **Show Caller** | Live execution of the cue stack, the clock, variance | Sole authority to issue `GO`, `HOLD`, `STANDBY CANCEL`; escalates to PROD at RED | Content decisions |
| `SM` | **Stage Manager** | Everything upstage of the proscenium: talent position, standbys, walk-ons, handoffs, deck safety | Holds a walk-on if talent is not in position; enforces hard stops; stops the show for a safety hazard without asking | Cue calling (unless SM *is* the caller on a small show) |
| `A1` | **FOH Engineer** | The `Audio Cue` column, house mix, playback, all SQ cues | Mic mute at hard stop; failover to backup console/desk snapshot; PA level vs. venue limit | Monitor world, RF coordination |
| `A2` | **RF / Monitors** | Mic fitting, battery discipline, RF scan, IEM and wedge mixes, `MIC` cues | Swaps a suspect transmitter mid-show; reallocates a frequency | House mix |
| `LD` | **Lighting Designer / Director** | The `Lighting Cue` column, all looks, house levels, `LX` numbering | Look changes within an approved palette; busks unscripted content; house level for evacuation | Content order |
| `V1` | **Video Director** | The `Visual Cue` column, switcher, cameras, playback, LED/projection, `VID` numbering | Source selection, cut to backup playback, black frame vs. hold slide | Audio embedded in playback beds (that is A1) |
| `L1` | **Lighting Operator** | Executing LX cues at the console | Nothing independently — executes LD intent | Cue design |
| `TD` | **Technical Director** | Infrastructure: power, rigging, signal distribution, redundancy commissioning | Load-in/load-out sequence, structural and electrical sign-off, denies an unsafe request | Show content or cue calling |
| `STR` | **Stream Lead** | Encoders, bitrate, platform targets, recordings, `STR` cues | Failover to backup encoder, slate insertion, delays stream start | In-room experience |
| `DW` | **Demo Wrangler** | Presenter laptops, demo state, the stall clock (product launches, tech events) | Declares a demo dead and calls for the pre-record — see `03-event-type-sops/Tech-Expos-Hackathons.md` §1.4 | Anything outside demo scope |

### 3.1 Minimum Crew by Event Size

| Event | Combined roles | Never combine |
|-------|----------------|---------------|
| ≤150 seats, single presenter | SC+SM+PROD one person; A1+A2 one person | A1 with V1 |
| 150-800 seats, multi-speaker | SC+SM; A1+A2 if ≤8 RF channels | PROD with SC |
| 800+ seats, broadcast or stream | None | Any of SC, SM, A1, V1, LD |
| Concert, touring production | None | Any role. Add A2, SFX, backline |

**The rule behind the table:** combine roles that share a physical position and a sensory channel. A1 and A2 both listen, and can sit together. A1 and V1 monitor different senses in different places and cannot be one person above 150 seats.

---

## 4. Time Buffer Guidelines

### 4.1 Allocation Rule

Budget **8% of total program runtime as distributed buffer**, placed at transition points, never banked as one block at the end. A block at the end is not a buffer — it is a 100% probability of either finishing early or being useless, because you cannot spend end-of-show time on a problem that happened in the middle.

| Runtime | Total buffer @ 8% | Typical distribution |
|---------|-------------------|----------------------|
| 60 min | 4:45 | 6 × 0:20 transition + 1 × 2:30 elastic |
| 90 min | 7:15 | 8 × 0:30 transition + 1 × 2:00 elastic + 1:15 hard reserve |
| 120 min | 9:35 | 10 × 0:30 transition + 2 × 1:30 elastic + 1:30 hard reserve |
| 180 min (2 acts) | 14:30 | changeover absorbs 8:00 + 8 × 0:30 + 2:30 hard reserve |
| 240 min | 19:00 | breaks absorb 10:00 + 12 × 0:30 + 2:00 hard reserve |

### 4.2 Buffer Classes

| Class | Size | Placement | Consumable by | ID |
|-------|------|-----------|---------------|-----|
| **Transition** | 0:15–0:30 | Between every speaker or act change | Slow walk-ons, mic handoffs, laptop switches | `BUF-nn` |
| **Elastic** | 1:00–3:00 | After each major segment | Speaker overrun, Q&A spill | `BUF-nn` |
| **Structural** | 5:00–15:00 | Meal breaks, set changeovers | Major recovery, reboots, re-patch | `BUF-nn` |
| **Hard reserve** | 1:30–5:00 | Immediately pre-close | Never touched except P0/P1 crisis | `BUF-RSV` |

Buffer rows are **first-class ROS entries with IDs**, not slack between rows. They have IDs so the caller can announce "we are in BUF-04, burning 40 seconds" and every department instantly understands the state. A buffer with no ID is invisible and gets spent without anyone noticing.

### 4.3 Transition Padding by Activity

Measured minimums. These are the times an unhurried transition actually takes, not the times an optimistic producer writes down.

| Transition | Pad | Notes |
|-----------|-----|-------|
| Speaker to speaker, both pre-set in wing, handheld handoff | 0:15 | Requires SM pre-staging; the 0:15 is the walk |
| Speaker to speaker, lectern mic, no pre-set | 0:30 | |
| Speaker to speaker with lav fit | 2:00 | Never fit a lav live on clock — fit during a video roll |
| Presenter laptop switch (HDMI, no scaler) | 0:45 | Resolution renegotiation. Halves to 0:20 with a pre-set scaler and confirmed EDID |
| Presenter laptop switch (pre-set, confirmed at rehearsal) | 0:20 | |
| Solo to panel (4 chairs, mics pre-set) | 1:30 | Chairs and water pre-set upstage during prior video |
| Panel strike to solo | 1:00 | |
| Q&A mic runner to first question | 0:30 | Pre-position runners during the segment before |
| Band changeover, festival-style (shared backline) | 15:00 | |
| Band changeover, full swap (opener to headliner) | 25:00–30:00 | Includes line check |
| Video roll to live stage (reveal) | 0:00 | Zero pad — the film covers the move. This is the point of the film |

**Design principle:** the cheapest buffer is a video roll. Any transition that needs more than 30 seconds of stage work should have content covering it, and the ROS should place that content deliberately rather than discovering the need in rehearsal.

### 4.4 Variance Tracking

The caller announces a running variance figure at every segment boundary. Thresholds and recovery levers are defined in `02-event-ops-framework/Core-Skills-Overview.md` §1.5; the short form:

| Variance | State | Caller action |
|----------|-------|---------------|
| −1:00 to +1:00 | GREEN | Announce "on time" at boundaries only |
| +1:00 to +5:00 | AMBER | Announce variance each segment; arm levers 1-2 |
| +5:00 to +10:00 | RED | Notify PROD and client lead; execute levers 2-4 |
| > +10:00 | CRITICAL | Client decision on the pre-agreed cut list |

---

## 5. Worked Example A — Corporate Keynote (2 hours)

### 5.1 Show Header

| Field | Value |
|-------|-------|
| **Event** | Northwind Technologies — FY27 Strategy Summit, General Session |
| **Venue** | Grand Ballroom, Hyatt Regency Seattle — 800 seats, 12 m × 6 m stage, 4.2 m trim |
| **Date** | 2026-09-17 |
| **Runtime** | 2:00:00 · `T+00:00:00 = 09:00:00` · doors `T-30:00 = 08:30:00` |
| **Shape** | 3 speakers → panel (4) → audience Q&A → close |
| **Revision** | `ROS_NorthwindFY27_v2.1_2026-09-16_FINAL` |
| **Buffer** | 8:15 allocated (6.9%) — walk-out row additionally elastic |

### 5.2 Crew

| Role | Name | Position |
|------|------|----------|
| `PROD` | Marion Delacroix | Comms, house left |
| `SC` Show Caller | Aiko Tanaka | FOH riser, centre |
| `SM` Stage Manager | Declan Byrne | Stage left wing |
| `A1` FOH Engineer | Priya Raghunathan | FOH riser |
| `A2` RF / Monitors | Jonas Ekström | Stage right, RF world |
| `LD` | Fatima Mbeki | FOH riser |
| `V1` Video Director | Grant Sullivan | FOH riser |
| `TD` | Bill Ostrowski | Roaming |
| `STR` Stream Lead | Yuki Watanabe | Broadcast room |

### 5.3 Talent

| Name | Role | Mic | Position |
|------|------|-----|----------|
| Marcus Whitfield | Host / MC (external) | Shure Axient AD2 handheld, Beta 87A capsule — CH4 | Centre, then panel chair 1 |
| Elena Vasquez | Chief Executive Officer | Sennheiser e935 wired, lectern — CH1 | Lectern SL |
| Dr. Sarah Chen | Chief Technology Officer | Beta 87A wired, lectern — CH2 | Lectern SL, then centre for demo |
| Daniel Okonkwo | Chief Financial Officer | Beta 87A wired, lectern — CH3 | Lectern SL |
| Ravi Menon | VP Engineering (panellist) | Shure MX412 gooseneck — CH5 | Panel chair 2 |
| Dr. Helena Vogt | Chief Data Officer (panellist) | Shure MX412 gooseneck — CH6 | Panel chair 3 |
| Camille Auger | SVP People (panellist) | Shure MX412 gooseneck — CH7 | Panel chair 4 |

### 5.4 Key Equipment

| Dept | Equipment |
|------|-----------|
| Audio | Behringer WING (FOH) · L-Acoustics Kara II 8-per-side, SB18 subs · Shure Axient Digital AD4Q ×2 · Countryman B3 lav (CH8, backup, dry) · Waves Clarity VX + Sonible smart:EQ 4 on speaker channels via SuperRack Performer |
| Video | Blackmagic ATEM 4 M/E Constellation · Barco UDX-4K32 ×2, 9.7 m blended 16:9 · Sony HXC-FB80 ×2 (FOH long, SL cross) · Panasonic AW-UE150 robo (upstage wide) · Playback Pro ×2 mirrored (Mac Studio M2 Max) · Decimator scaler on presenter input |
| Lighting | grandMA3 light · Robe BMFL Blade ×8 (key) · Martin MAC Aura XB ×12 (wash) · ETC Source Four LED S3 ×6 (lectern/panel specials) · house dimmers via DMX gateway |
| Comms / Timer | Hollyland Solidcom C1 Pro ×6 (1.9 GHz DECT) · Stage Timer Pro on 2 × 24" confidence monitors |

### 5.5 Master ROS

| Time | Duration | Stage Activity | Visual Cue | Audio Cue | Lighting Cue | Owner | Notes |
|------|----------|----------------|------------|-----------|--------------|-------|-------|
| `T-30:00` | — | **Doors open.** Audience walk-in | `VID 1 GO` — holding slide "FY27 Strategy Summit" to screen + confidence | `SQ 1 GO` — walk-in playlist, −35 LUFS-S at mix position | `LX 1 GO` — house 100%, stage wash 40%, logo gobo | `SC` (Tanaka) | Caller confirms all 6 comms packs paired before doors |
| `T-27:00` | 02:00 | RF spectrum scan and lock | — | — | — | `A2` (Ekström) | Wireless Workbench sweep 470-608 MHz. Log AD2 handheld on 542.375. Abort doors if >2 hits in walk-in band |
| `T-22:00` | 04:00 | Vasquez, Chen, Okonkwo mic and lectern check | `VID 2 GO` — each presenter laptop to PGM, confirm EDID 1920×1080p60 | `SQ 2 GO` — CH1/2/3 open one at a time, ring out lectern position | `LX 2 GO` — lectern special at show level | `A1` (Raghunathan) | Clarity VX engaged, smart:EQ 4 in Learn on CH1-3. Chen speaks 30 s minimum for Learn to converge |
| `T-18:00` | 03:00 | Panel pre-set check — 4 stools, goosenecks, water | — | `SQ 3 GO` — CH5-7 open, gate threshold −60 dB verify | — | `SM` (Byrne) | Stools struck to upstage dark after check. Chair 1 (Whitfield) gets handheld, no gooseneck |
| `T-12:00` | — | Whitfield mic fit and level | — | `SQ 4 GO` — CH4 open, DCA1 assign | — | `A2` (Ekström) | Fresh AA cells at `T-12:00`, no exceptions. Spare AD2 on SR table, same capsule |
| `T-08:00` | — | All talent to holding room; Vasquez briefed on variance plan | — | — | — | `SM` (Byrne) | SM confirms Vasquez, Chen, Okonkwo physically present. Report to caller |
| `T-05:00` | — | Playback and stream armed | `VID 3 GO` — Playback Pro A + B mirrored, all 6 assets verified | `SQ 5 GO` — QLab standby, film beds pre-rolled | `LX 3 GO` — preset LX 10 in blind, confirm | `STR` (Watanabe) | Stream live to Northwind internal at `T-05:00`, slate card up |
| `T-02:00` | 02:00 | 2-minute countdown to screen and confidence monitors | `VID 4 GO` — countdown clock, IMAG + both confidence feeds | — | — | `V1` (Sullivan) | Stage Timer Pro. Confirm Vasquez can read confidence from lectern SL |
| `T-01:00` | — | Whitfield to SL wing, standby | — | — | — | `SM` (Byrne) | SM reports "host in position" — caller does not proceed without it |
| `T-00:30` | 00:30 | Walk-in music fade | — | `SQ 6 GO` — walk-in fade to −∞ over 30 s | — | `A1` (Raghunathan) | Fade must complete before LX 10. Music under a dark stage reads as a mistake |

| `T+00:00:00` | 00:20 | **SHOW START.** Opening title film | `VID 10 GO` — "Northwind FY27" title film, 0:20, out to black frame | `SQ 10 GO` — title film bed, house to show level | `LX 10 GO` — house to 25% over 3 s, stage to black | `SC` (Tanaka) | Hard anchor. Wall clock 09:00:00. Everything downstream is relative to this frame |
| `T+00:00:20` | 02:40 | Marcus Whitfield welcome, safety and housekeeping | `VID 11 GO` — cut CAM 1 (FOH long), lower-third "Marcus Whitfield / Host" 5 s | `SQ 11 GO` — CH4 unmute, DCA1 to 0 dB | `LX 11 GO` — host special + centre wash, 2 s | `SC` (Tanaka) | Whitfield walks on in the film tail — zero transition pad by design |
| `T+00:03:00` | 00:20 | Whitfield introduces Elena Vasquez, CEO | `VID 12 GO` — lower-third "Elena Vasquez / Chief Executive Officer" | — | `LX 12 GO` — cross-fade host special to lectern special, 3 s | `V1` (Sullivan) | Name pronunciation confirmed with Vasquez at rehearsal: *vah-SKETH* |
| `T+00:03:20` | 00:15 | `BUF-01` — Vasquez walk-on to lectern SL | — | `SQ 12 GO` — CH4 mute, CH1 unmute, DCA2 up (300 ms crossfade) | — | `SM` (Byrne) | Transition buffer. Vasquez pre-set in SL wing from `T+00:02:00` |
| `T+00:03:35` | 14:25 | **Elena Vasquez — CEO keynote:** FY27 strategy, market position | `VID 13 GO` — presenter laptop A to PGM, IMAG PIP top-right. Slides advance by presenter clicker | — | `LX 13 GO` — lectern key at 100%, audience wash 15% for camera | `PROD` (Delacroix) | 14:25 planned, 18:00 timer shown. Vasquez historically runs 2 min long — BUF-02 exists for exactly this |
| `T+00:18:00` | 01:00 | `BUF-02` — elastic | — | — | — | `SC` (Tanaka) | First variance announcement to all comms at end of this row |
| `T+00:19:00` | 02:00 | Platform sizzle film — covers Vasquez exit / Chen entrance | `VID 14 GO` — "Northwind Copilot" sizzle, 2:00, stereo bed | `SQ 13 GO` — film bed to −8 dBFS, CH1 mute at film start | `LX 14 GO` — stage to 10%, screen-safe, no spill | `V1` (Sullivan) | The film *is* the transition. Chen reaches lectern by 1:30 or SM calls a hold |
| `T+00:21:00` | 18:00 | **Dr. Sarah Chen — CTO keynote:** AI platform roadmap | `VID 15 GO` — presenter laptop B to PGM, IMAG PIP. `VID 15.5` lower-third "Dr. Sarah Chen / Chief Technology Officer" | `SQ 14 GO` — CH2 unmute, DCA2 up | `LX 15 GO` — lectern key restore, 2 s | `PROD` (Delacroix) | Chen advances her own slides. Clicker battery swapped at `T-22:00` |
| `T+00:39:00` | 06:00 | Chen live demo — Copilot agent workflow, from stage centre | `VID 16 GO` — demo laptop (Decimator scaled) full-screen, IMAG PIP off | `SQ 15 GO` — CH2 to handheld AD2 handoff, DCA2 hold. Demo audio CH9/10 armed | `LX 16 GO` — centre stage special, screen level down 10% | `DW` (Ostrowski) | **Stall clock 10 s.** Pre-record `copilot_demo_v4.mov` armed on Playback B. `TD` doubles as Demo Wrangler this show |
| `T+00:45:00` | 02:00 | Chen wrap-up; Whitfield rejoins for one question | `VID 17 GO` — cut CAM 2 (SL cross), two-shot | `SQ 16 GO` — CH4 unmute, DCA1 up. Both mics live | `LX 17 GO` — add host special to centre look, 2 s | `SC` (Tanaka) | Only scripted moment with two open handhelds — A1 watch gain-before-feedback at centre |
| `T+00:47:00` | 01:00 | `BUF-03` — elastic (demo overrun absorb) | — | — | — | `SC` (Tanaka) | If the demo consumed its full 10 s stall and recovered, this row is already spent |

| `T+00:48:00` | 00:30 | Whitfield introduces Daniel Okonkwo, CFO | `VID 18 GO` — lower-third "Daniel Okonkwo / Chief Financial Officer" | — | `LX 18 GO` — host special only, 2 s | `V1` (Sullivan) | |
| `T+00:48:30` | 00:15 | `BUF-04` — Okonkwo walk-on | — | `SQ 17 GO` — CH4 mute, CH3 unmute, DCA3 up | `LX 19 GO` — cross to lectern special, 3 s | `SM` (Byrne) | |
| `T+00:48:45` | 11:15 | **Daniel Okonkwo — CFO:** FY26 results, FY27 guidance | `VID 19 GO` — presenter laptop C to PGM, IMAG PIP | — | `LX 20 GO` — lectern key 100%, 2 s | `PROD` (Delacroix) | **Forward-looking statements slide must be on screen ≥5 s before guidance figures — legal requirement, confirmed with Northwind counsel.** Do not cut away early |
| `T+01:00:00` | 01:00 | `BUF-05` — elastic | — | — | — | `SC` (Tanaka) | Halfway variance report to PROD and client lead |
| `T+01:01:00` | 02:30 | Customer testimonial film — Meridian Health | `VID 20 GO` — "Meridian Health" film, 2:30, stereo bed | `SQ 18 GO` — film bed −8 dBFS, CH3 mute | `LX 21 GO` — stage to 10% screen-safe | `V1` (Sullivan) | **Panel set happens under this film:** 4 stools, 4 goosenecks pre-cabled, water. SM has 2:30 against a 1:30 requirement |
| `T+01:03:30` | 00:30 | Panellists to position; Whitfield to chair 1 | — | `SQ 19 GO` — CH5, CH6, CH7 unmute, DCA4 up. CH4 stays live for Whitfield | `LX 22 GO` — panel wash 4-chair, 3 s | `SM` (Byrne) | Menon chair 2, Vogt chair 3, Auger chair 4 — seated left to right from audience |
| `T+01:04:00` | 00:30 | Whitfield frames the panel, introduces panellists | `VID 21 GO` — cut CAM 3 (robo upstage wide), name-strap sequence 4× | — | — | `V1` (Sullivan) | |
| `T+01:04:30` | 12:00 | **Panel block 1** — AI governance and regulation | `VID 22 GO` — director's cut, CAM 1/2/3 live switching to whoever holds the floor | — | `LX 23 GO` — panel wash to 100%, 2 s | `V1` (Sullivan) | Vogt and Menon expected to dominate. V1 favours the speaking chair, 3 s minimum on any shot |
| `T+01:16:30` | 13:30 | **Panel block 2** — talent, hiring and scaling | — | `SQ 20 GO` — trim CH5-7 −2 dB (panel warms up and leans in) | — | `V1` (Sullivan) | Auger leads this block. Rehearsal note: Auger is soft-spoken, gooseneck is on the low side |
| `T+01:30:00` | 00:30 | Whitfield opens audience Q&A; runners take position | `VID 23 GO` — CAM 1 wide including audience, "Q&A" strap | `SQ 21 GO` — CH11, CH12 (roving AD2 handhelds) unmute, DCA5 up at −6 dB | `LX 24 GO` — audience wash to 35%, panel hold, 3 s | `SM` (Byrne) | Runners Kaito Mori (house left) and Alina Petrova (house right) pre-positioned from `T+01:28:00` |
| `T+01:30:30` | 08:00 | **Audience Q&A block 1** | `VID 24 GO` — cut to questioner on runner mic, return to panel on answer | — | — | `SC` (Tanaka) | A1 rides DCA5 — open only the mic in use. Two live roving mics in an 800-seat room is a feedback event |
| `T+01:38:30` | 01:00 | `BUF-06` — elastic | — | — | — | `SC` (Tanaka) | |
| `T+01:39:30` | 07:30 | **Audience Q&A block 2** | — | — | — | `SC` (Tanaka) | **Shorten by question count, not by clock** — cutting mid-answer is the most visible recovery lever there is |
| `T+01:47:00` | 01:00 | Whitfield closes Q&A, thanks panellists | `VID 25 GO` — CAM 3 wide, 4-shot | `SQ 22 GO` — CH5-7 mute, DCA4 to −∞ | `LX 25 GO` — audience wash out, panel hold, 3 s | `SC` (Tanaka) | |

| `T+01:48:00` | 00:45 | Panel exits SR; Whitfield to centre | `VID 26 GO` — CAM 1 tight on Whitfield, avoid the exit | — | `LX 26 GO` — panel wash out, centre special up, 3 s | `SM` (Byrne) | Stools struck after house-out only — never during walk-out music |
| `T+01:48:45` | 00:15 | `BUF-07` — Vasquez walk-on | — | `SQ 23 GO` — CH4 mute, CH1 unmute (Vasquez to lectern), DCA2 up | — | `SM` (Byrne) | |
| `T+01:49:00` | 03:00 | **Elena Vasquez — closing remarks and call to action** | `VID 27 GO` — presenter laptop A, single close slide. IMAG PIP | — | `LX 27 GO` — lectern key + full stage wash 60%, 3 s | `PROD` (Delacroix) | **Hard stop `T+01:52:00`.** Reception staff open doors on our house-up cue, not before |
| `T+01:52:00` | 01:00 | Whitfield close — reception and breakout logistics | `VID 28 GO` — "Networking Reception — Foyer, 11:15" info slide | `SQ 24 GO` — CH1 mute, CH4 unmute | `LX 28 GO` — restore centre special, 2 s | `SC` (Tanaka) | |
| `T+01:53:00` | 01:30 | Close film and walk-out | `VID 29 GO` — close film 1:30, out to logo hold | `SQ 25 GO` — close film bed, then walk-out playlist at −32 LUFS-S | `LX 29 GO` — stage to black over film, 4 s | `V1` (Sullivan) | `SQ 25` crossfades film bed into playlist — no gap. All talent mics muted at film start |
| `T+01:54:30` | 02:00 | House up; room clear to foyer | `VID 30 GO` — logo hold on screen, IMAG off | — | `LX 30 GO` — house to 100% over 5 s, stage wash 40% | `SM` (Byrne) | Do not strike anything while audience is in the room |
| `T+01:56:30` | 03:30 | `BUF-RSV` — hard reserve | — | — | — | `PROD` (Delacroix) | Untouched except P0/P1. Room contracted to 12:00 for strike |
| `T+02:00:00` | — | **SHOW COMPLETE.** Stream ends, recording verified | `VID 31 GO` — stream slate, PGM to black | `SQ 26 GO` — walk-out music out, console to safe scene | `LX 31 GO` — work light | `STR` (Watanabe) | Verify both ISO recordings before any teardown. No exceptions |

**Contingency rows (pre-agreed with client, not in running order):**

| Trigger | Action | Owner |
|---------|--------|-------|
| Chen demo stalls >10 s | `VID 16.5 GO` — cut to `copilot_demo_v4.mov`, Chen narrates live over it | `DW` (Ostrowski) |
| Variance >+10:00 at `T+01:30:00` | Cut Q&A block 2 entirely (lever 5, pre-signed) | `PROD` (Delacroix) |
| Lectern mic failure | `SQ 12.5 GO` — CH8 Countryman B3 lav, dry, DCA2 | `A1` (Raghunathan) |
| Projector failure, single | `VID 13.5 GO` — reformat to single-projector 4:3 centre, IMAG PIP off | `V1` (Sullivan) |

---

## 6. Worked Example B — Product Launch (90 minutes)

### 6.1 Show Header

| Field | Value |
|-------|-------|
| **Event** | Helix Robotics — ORBIT-2 Launch |
| **Venue** | The Vaults, Shoreditch, London — 400 seats, thrust stage, 12 m LED wall upstage |
| **Date** | 2026-10-08 |
| **Runtime** | 1:30:00 · `T+00:00:00 = 10:00:00` · doors `T-30:00 = 09:30:00` |
| **Shape** | Film reveal → physical reveal → live robot demo → partner segment → press Q&A |
| **Revision** | `ROS_HelixORBIT2_v3.0_2026-10-07_FINAL` |
| **Buffer** | 6:35 allocated (7.3%), of which 2:00 is demo-specific |
| **Embargo** | **Press embargo lifts `T+00:15:05`** — the frame the reveal film ends. Nothing before that time may be published |

### 6.2 Crew

| Role | Name | Position |
|------|------|----------|
| `PROD` | Rebecca Lin | House left, client-side |
| `SC` Show Caller | Omar Haddad | FOH riser |
| `SM` Stage Manager | Greta Halvorsen | Stage right |
| `A1` FOH Engineer | Stefan Kowalczyk | FOH riser |
| `A2` RF / Comms | Nina Abiodun | Stage right |
| `LD` | Fiona Mbeki | FOH riser |
| `V1` Video Director | Alan Prescott | FOH riser |
| `DW` Demo Wrangler | Raj Anand | Upstage right, robot pen |
| `STR` Stream Lead | Chloé Dubois | Broadcast truck |
| `TD` | Wes Doherty | Roaming |

### 6.3 Talent

| Name | Role | Mic | Notes |
|------|------|-----|-------|
| Nadia Farouk | Chief Executive Officer, Helix Robotics | DPA 4066 headset, AD1 body pack — CH1 | Primary voice, 4 appearances |
| Isabelle Roy | Chief Design Officer | DPA 4066 headset — CH2 | Design narrative segment |
| Kenji Nakamura | VP Engineering | DPA 4066 headset — CH3 | Runs the live demo |
| Dr. Amara Osei | Director of Logistics Tech, Kestrel Freight (launch partner) | Sennheiser SKM 6000 handheld — CH4 | External partner, single segment |
| Tom Whitaker | VP Communications | AD2 handheld — CH5 | Moderates press Q&A only |
| Priya Nair · Martin Køhler · Grace Adebayo · Yuki Tanabe | Press pool, front two rows | 2 × AD2 roving — CH6, CH7 | Pre-selected first four questions |

### 6.4 Key Equipment

| Dept | Equipment |
|------|-----------|
| Audio | DiGiCo Quantum225 · L-Acoustics Kara II 6-per-side + KS21 subs · Shure Axient Digital AD4Q · Sennheiser EM 6000 ×2 · QLab 5 for all beds |
| Video | ROE Visual CB5 LED, 12 m × 3.5 m, Brompton Tessera SX40 · **disguise gx 2c main + gx 2c backup, frame-locked and mirrored** · ATEM 4 M/E · Sony FX9 ×3 (incl. 1 low-angle robot cam) · Panasonic AW-UE150 robo · Decimator on demo laptop |
| Lighting | grandMA3 light · Robe BMFL Blade ×10 · Martin MAC Aura XB ×16 · GLP JDC1 strobe ×6 · Astera Titan tube ×12 (reveal riser edge) · MDG Atmosphere haze |
| Automation | Kinesys Elevation 1+ — 3 m × 3 m reveal riser + Kabuki drape release (dual-redundant solenoid) |
| Demo | ORBIT-2 hero unit + ORBIT-2 spare (identical firmware 2.4.1) · 40 kg payload crate · 4-step demo staircase · private 5 GHz demo SSID, no WAN dependency |

### 6.5 Master ROS

| Time | Duration | Stage Activity | Visual Cue | Audio Cue | Lighting Cue | Owner | Notes |
|------|----------|----------------|------------|-----------|--------------|-------|-------|
| `T-30:00` | — | **Doors.** Press check-in, seat assignment | `VID 1 GO` — ORBIT-2 teaser loop (silhouette only, no reveal), LED wall | `SQ 1 GO` — walk-in bed, −34 LUFS-S | `LX 1 GO` — house 80%, blue architectural wash, haze at 15% | `SC` (Haddad) | Haze must settle 20 min before beam looks read correctly. Started at `T-50:00` |
| `T-28:00` | 05:00 | **ORBIT-2 hero and spare power-on, full self-test** | — | — | — | `DW` (Anand) | Both units to 100% charge, firmware 2.4.1 confirmed on both. Walk cycle, payload lift and stair sequence each run once on the spare. **Hero unit is not test-run — it is preserved** |
| `T-22:00` | 04:00 | Farouk, Roy, Nakamura headset fit and level | — | `SQ 2 GO` — CH1, CH2, CH3 open in sequence, ring out at each mark | `LX 2 GO` — show-level key at centre and riser | `A2` (Abiodun) | DPA 4066 boom set right-cheek on all three so camera left is clean. Tape logged and photographed for re-fit |
| `T-18:00` | 03:00 | Reveal mechanism dry-run — riser and drape | `VID 2 GO` — riser-edge Astera tubes at 100%, confirm sightline from row 1 | — | `LX 3 GO` — reveal look at 100%, confirm no drape shadow | `TD` (Doherty) | **Drape release tested twice. Both solenoids fire independently.** Riser at 1.2 m final trim. Kabuki reset by `T-14:00` |
| `T-14:00` | 02:00 | Playback redundancy check | `VID 3 GO` — disguise main and backup both to PGM in turn, frame-lock confirmed, all 5 films verified end-to-end | `SQ 3 GO` — all film beds pre-rolled and level-matched | — | `V1` (Prescott) | Backup gx 2c must be timecode-matched, not just loaded. Verify by switching mid-film |
| `T-10:00` | — | Talent to holding; Farouk briefed on embargo timing | — | — | — | `SM` (Halvorsen) | Farouk must not state the product name before the film ends — legal and embargo |
| `T-06:00` | — | Hero unit to upstage mark, under drape | — | — | `LX 4 GO` — riser area to black, spill checked from row 1 and press pool | `DW` (Anand) | Hero unit powered, idle, motors enabled, on the mark. Anand stays within 2 m until `T+00:19:25` |
| `T-04:00` | — | Press embargo reminder from podium | — | `SQ 4 GO` — CH5 open for Whitaker announcement, then mute | — | `PROD` (Lin) | Whitaker reads the embargo statement live. Scripted, approved by legal |
| `T-02:00` | 02:00 | Countdown on LED wall | `VID 4 GO` — 2:00 countdown, full wall | — | — | `V1` (Prescott) | |
| `T-00:20` | 00:20 | Music out, house to black | — | `SQ 5 GO` — walk-in bed out over 15 s | `LX 5 GO` — house to 0% over 15 s, haze look holds | `SC` (Haddad) | Full blackout before `T+00:00:00`. The dark is the beat before the film |
| `T+00:00:00` | 01:30 | **SHOW START.** Opening film "Ten Years of Motion" | `VID 10 GO` — opening film, full 12 m wall, 1:30 | `SQ 10 GO` — film bed to −6 dBFS, subs engaged for the low end at 0:48 | `LX 10 GO` — blackout hold, wall is the only source | `SC` (Haddad) | Wall clock 10:00:00. Farouk moves to her mark in the dark at 1:10 — SM has an IR line of sight |
| `T+00:01:30` | 00:15 | Farouk walk-on (film tail covers) | `VID 11 GO` — wall to Helix mark, cut CAM 1 to IMAG side panels | `SQ 11 GO` — CH1 unmute, DCA1 to 0 dB | `LX 11 GO` — centre key up over 2 s | `SM` (Halvorsen) | |
| `T+00:01:45` | 04:00 | **Nadia Farouk — opening:** the problem in warehouse logistics | `VID 12 GO` — supporting graphics on wall, cued by presenter clicker | — | — | `PROD` (Lin) | No product name and no silhouette reveal in this segment. Confirmed at rehearsal |
| `T+00:05:45` | 00:20 | Farouk introduces Isabelle Roy | `VID 13 GO` — name card "Isabelle Roy / Chief Design Officer" | `SQ 12 GO` — CH2 unmute, DCA2 up. CH1 stays open (Farouk remains on stage) | `LX 12 GO` — add stage-left key, 2 s | `V1` (Prescott) | |
| `T+00:06:05` | 06:00 | **Isabelle Roy — design narrative:** form, materials, the human factor | `VID 14 GO` — design boards to wall, slow pans. Clicker-advanced | `SQ 13 GO` — CH1 mute (Farouk steps off), DCA1 to −∞ | `LX 13 GO` — isolate stage-left key, 3 s | `PROD` (Lin) | |

| `T+00:12:05` | 00:30 | `BUF-01` — Roy exits, Farouk returns to centre mark | — | `SQ 14 GO` — CH2 mute, CH1 unmute | `LX 14 GO` — return to centre key only, 2 s | `SM` (Halvorsen) | |
| `T+00:12:35` | 02:30 | **REVEAL FILM** — "ORBIT-2" | `VID 15 GO` — reveal film, full wall, 2:30. **Backup gx 2c chase-armed and confirmed before GO** | `SQ 15 GO` — film bed to −4 dBFS, full-range with subs. All talent mics muted | `LX 15 GO` — full blackout, wall only, 1 s | `V1` (Prescott) | Highest-consequence cue of the show. If main playback faults, `VID 15.5 GO` cuts to backup — **V1 has standing authority, no caller confirmation needed** |
| `T+00:15:05` | 01:00 | **PHYSICAL REVEAL** — riser rises, Kabuki drops, ORBIT-2 revealed. **Embargo lifts on this frame** | `VID 16 GO` — wall to slow product loop, cut CAM 3 (low-angle robot cam) to IMAG | `SQ 16 GO` — reveal sting, then bed under at −18 dBFS | `LX 16 GO` — riser Astera tubes + BMFL beam pack up over 1.5 s; JDC1 strobe accent at 0:02 | `TD` (Doherty) | `FLY 1 GO` riser to 1.2 m, then `FLY 2 GO` Kabuki release at riser top. **Two separate cues — never one.** Anand confirms hero unit upright and idle before `LX 16` |
| `T+00:16:05` | 03:00 | **Nadia Farouk — spec headline:** payload, runtime, autonomy | `VID 17 GO` — spec graphics to wall, clicker-advanced | `SQ 17 GO` — CH1 unmute, bed under at −24 dBFS | `LX 17 GO` — restore centre key, hold product light on riser, 2 s | `PROD` (Lin) | Product stays lit for the rest of the show. Never let the hero unit fall dark |
| `T+00:19:05` | 00:20 | Farouk introduces Kenji Nakamura; Anand hands off | `VID 18 GO` — name card "Kenji Nakamura / VP Engineering" | `SQ 18 GO` — CH3 unmute, DCA3 up | `LX 18 GO` — widen to full stage, 2 s | `SM` (Halvorsen) | |
| `T+00:19:25` | 05:00 | **LIVE DEMO 1** — walk cycle, obstacle avoidance, voice command | `VID 19 GO` — CAM 3 low-angle as primary, CAM 1 wide as cutaway, wall to live IMAG | `SQ 19 GO` — CH3 hold. **Demo unit audio not mic'd** — servo noise is unflattering through a PA | `LX 19 GO` — demo floor wash 100%, no beams into robot sensors, 2 s | `DW` (Anand) | **Stall clock 10 s.** `orbit2_demo_A.mov` armed. Beams kept off the LiDAR plane — this was found in rehearsal, do not re-aim |
| `T+00:24:25` | 06:00 | **LIVE DEMO 2** — 40 kg payload lift, 4-step stair climb | `VID 20 GO` — CAM 3 tight on payload, cut CAM 2 for stair profile | — | `LX 20 GO` — add stair-area key, 2 s | `DW` (Anand) | Stair climb is the least reliable step (rehearsal: 2 faults in 9 runs). `orbit2_demo_B.mov` armed and cued to the stair sequence specifically |
| `T+00:30:25` | 02:00 | `BUF-02` — **demo contingency buffer** | — | — | — | `SC` (Haddad) | Exists solely for demo recovery. If both demos ran clean, burn it here and bank the variance — do not stretch the next segment |
| `T+00:32:25` | 03:00 | Farouk — pricing, configurations, availability | `VID 21 GO` — pricing graphic. **Hold minimum 20 s, press are photographing it** | `SQ 20 GO` — CH3 mute, CH1 unmute | `LX 21 GO` — centre key restore, 2 s | `PROD` (Lin) | Do not cut away from the pricing slide early. Every outlet needs the shot |
| `T+00:35:25` | 02:00 | Partner film — Kestrel Freight pilot deployment | `VID 22 GO` — partner film, 2:00 | `SQ 21 GO` — film bed, CH1 mute | `LX 22 GO` — stage to 20%, product light holds | `V1` (Prescott) | Osei walks to her mark under the film |
| `T+00:37:25` | 05:00 | **Dr. Amara Osei (Kestrel Freight)** — operator perspective, in conversation with Farouk | `VID 23 GO` — two-shot CAM 1, name card "Dr. Amara Osei / Kestrel Freight" | `SQ 22 GO` — CH4 unmute (handheld), CH1 unmute, DCA4 up | `LX 23 GO` — two-person centre look, 3 s | `SM` (Halvorsen) | External speaker, no rehearsal beyond a walk-through. A1 rides CH4 conservatively |
| `T+00:42:25` | 01:00 | `BUF-03` — elastic; Osei exits | — | `SQ 23 GO` — CH4 mute, DCA4 to −∞ | — | `SC` (Haddad) | Unrehearsed guest, most likely overrun point in the show |
| `T+00:43:25` | 03:00 | **Nadia Farouk — closing:** vision and next milestone | `VID 24 GO` — closing graphic sequence | — | `LX 24 GO` — isolate centre, product light up 10%, 2 s | `PROD` (Lin) | |
| `T+00:46:25` | 02:00 | Stage reset for press Q&A — 3 stools, low table, water | `VID 25 GO` — wall to ORBIT-2 product loop, IMAG off | `SQ 24 GO` — CH1 mute. Bed up to −26 dBFS to cover the set change | `LX 25 GO` — Q&A look: 3-stool wash, press-pool wash 40%, 3 s | `SM` (Halvorsen) | Farouk, Nakamura and Whitaker take stools. Hero unit stays on the riser, lit, in shot |

| `T+00:48:25` | 01:00 | Tom Whitaker opens press Q&A, states the ground rules | `VID 26 GO` — cut CAM 1, "Press Q&A" strap | `SQ 25 GO` — CH5 unmute, CH6/CH7 (roving) unmute at −6 dB, DCA5 up | — | `SC` (Haddad) | One question plus one follow-up per outlet. Whitaker enforces, not the caller |
| `T+00:49:25` | 12:00 | **Press Q&A block 1** — first four questions pre-selected | `VID 27 GO` — cut to questioner on the live roving mic, return to answering panellist | — | — | `SC` (Haddad) | Order: Nair, Køhler, Adebayo, Tanabe. Runners Sam Ferreira (HL) and Beatriz Costa (HR). A1 opens only the mic in use |
| `T+01:01:25` | 01:00 | `BUF-04` — elastic | — | — | — | `SC` (Haddad) | |
| `T+01:02:25` | 12:00 | **Press Q&A block 2** — open floor | — | — | — | `SC` (Haddad) | Shorten by question count if variance is AMBER or worse. Whitaker has the short-close script |
| `T+01:14:25` | 02:00 | Final question; Whitaker wraps; Farouk one-line close | `VID 28 GO` — CAM 1 wide 3-shot, then push to product on riser | `SQ 26 GO` — CH6, CH7 mute, DCA5 to −∞ | `LX 26 GO` — press wash out, stage hold, 3 s | `SC` (Haddad) | |
| `T+01:16:25` | 01:30 | Close film and logo hold | `VID 29 GO` — close film 1:30, out to Helix logo hold on wall | `SQ 27 GO` — all talent mics muted, close bed, then walk-out playlist at −30 LUFS-S | `LX 27 GO` — stage to 30%, product light holds at 100%, 4 s | `V1` (Prescott) | |
| `T+01:17:55` | 10:00 | **House up. Hands-on area opens**, press one-to-ones begin | `VID 30 GO` — product loop on wall, IMAG off | `SQ 28 GO` — walk-out playlist at −30 LUFS-S, hold for the full window | `LX 28 GO` — house 100%, hands-on area key 100%, riser hold | `PROD` (Lin) | Spare ORBIT-2 goes to hands-on. **Hero unit stays on the riser and is not touched by press** — Anand posted at the riser |
| `T+01:27:55` | 02:05 | `BUF-RSV` — hard reserve | — | — | — | `PROD` (Lin) | |
| `T+01:30:00` | — | **SHOW COMPLETE.** Stream ends, recordings verified | `VID 31 GO` — stream slate, PGM to black | `SQ 29 GO` — music out, console to safe scene | `LX 29 GO` — work light | `STR` (Dubois) | Verify all ISOs and the clean product-loop record before strike. Both robots powered down and logged by Anand |

**Contingency rows:**

| Trigger | Action | Owner |
|---------|--------|-------|
| Reveal film playback fault | `VID 15.5 GO` — cut to backup gx 2c at frame. Standing authority, no confirmation | `V1` (Prescott) |
| Kabuki fails to release | `FLY 2.5 GO` — manual release, SR fly rail. Farouk holds with pre-scripted 15 s line | `TD` (Doherty) |
| Hero unit fault before demo | `DW` swaps to spare unit during `VID 22` partner film window (2:00 available) | `DW` (Anand) |
| Demo stalls >10 s | `VID 19.5` / `VID 20.5 GO` — cut to `orbit2_demo_A/B.mov`, Nakamura narrates live | `DW` (Anand) |
| Press Q&A hostile or off-embargo | Whitaker closes the floor; go early to `VID 29` close film | `PROD` (Lin) |

---

## 7. Worked Example C — Live Concert (3 hours)

### 7.1 Show Header

| Field | Value |
|-------|-------|
| **Event** | The Midnight Echoes — *Cathedral Pines* Tour, Glasgow |
| **Venue** | The Aurora, Glasgow — 2,400 cap (1,400 seated stalls + balcony, 1,000 GA standing), 14 m × 9 m stage, 8.2 m trim, house L-Acoustics K2 |
| **Date** | 2026-11-14 |
| **Runtime** | 3:00:00 · `T+00:00:00 = 19:30:00` (opener downbeat) · doors `T-60:00 = 18:30:00` |
| **Shape** | Soundcheck → doors → opener (40 min) → changeover (25 min) → main set (100 min) → encore call + encore (15 min) → walkout |
| **Revision** | `ROS_MidnightEchoesGLA_v2.4_2026-11-13_FINAL` |
| **Buffer** | 12:00 allocated (6.7%) — changeover absorbs 8:00, plus 8 × 0:30 transitions and 0:30 hard reserve |

### 7.2 Crew

| Role | Name | Position |
|------|------|----------|
| `PROD` Tour Producer | Henrik Ljungberg | FOH riser, client-side (label) |
| `SC` Show Caller | Tomás Herrera | FOH riser, centre |
| `SM` Stage Manager | Aoife O'Sullivan | Stage left wing |
| `A1` FOH Engineer | Marcus Doyle | FOH riser, house left |
| `A1.2` FOH Tech | Rosa Cisneros | FOH riser, patching and ProTools record |
| `A2` Monitor Engineer | Yuto Hara | Monitors world, stage right |
| `A2.2` RF Tech | Pavel Kuznetsov | RF world, antenna distro |
| `LD` Lighting Director | Esme Whitlock | FOH riser |
| `L1` Lighting Op | Bruno Tagliaferri | FOH riser, console |
| `V1` Video Director | Dani Larsson | FOH riser |
| `STR` Stream Lead | Conall McBride | Truck |
| `TD` Tech Director / Backline | Imani Okafor | Roaming, backline world |
| `SFX` SFX / Atmospherics | Caleb Northrop | Upstage right, CO2 and confetti |
| `PYRO` Pyrotechnician | Lorraine Mbatha | FOH position, firing script |
| `MED` Medical / Welfare | Paramedic on duty (Ambulance UK) | House left rear, dedicated first-aid room |

### 7.3 Artists

**Headliner — The Midnight Echoes** (indie rock, Glasgow)

| Name | Role | Mic / Rig | IEM mix |
|------|------|-----------|---------|
| Ronan Aitcheson | Lead vocal, acoustic guitar, keys | Shure AD2/KSM9 HS handheld (CH1) + DPA 4099 acoustic pickup | Mix 1, stereo, vocal heavy |
| Margaux Reeve | Lead guitar, vocal | Shure AD1 bodypack, Sennheiser e906 on cab (CH11/12) + XLR DI | Mix 2 |
| Dmitri Sokolov | Bass, synth bass, vocal | Shure AD1, DI on bass (CH13), XLR synth DI (CH14) | Mix 3 |
| Lior Aviv | Drums, percussion | Shure AD1 (CH15), trigger brain MIDI to LX via OSC | Mix 4, sub heavy |
| Tamsin Whitfield | Keys, Rhodes, accordion, vocal | Shure AD1, stereo DI keys L/R (CH16/17), accordion mic (CH18) | Mix 5 |
| Ingrid Mostrom | Violin, viola, vocal | DPA 4099 (violin CH19), DPA 4099 (viola CH20), vocal (CH21) | Mix 6 |

**Opener — Sable & the Vesper Lights** (folk-Americana, Leeds)

| Name | Role | Mic / Rig | IEM mix |
|------|------|-----------|---------|
| Sable Henson | Lead vocal, guitar | Shure AD2/KSM9 HS handheld (CH31) + DPA 4099 | Mix 7 |
| Jonas Henson | Upright bass, vocal | DI bass (CH32), vocal mic (CH33) | Mix 8 |
| Marisol Henson | Violin, vocal | DPA 4099 (CH34), vocal (CH35) | Mix 9 |
| Wynn Kearns | Pedal steel, lap steel, vocal | DI steel L/R (CH36/37), vocal (CH38) | Mix 10 |

**Touring crew for opener:** FOH mixes from their own Avid Venue S6L-32D (consigned), supplied by production. Monitor world from ours. Their console patched into our stage rack via dual Cat6 snake + Dante.

### 7.4 Set Lists

**Sable & the Vesper Lights — 40 min, 7 songs**

| # | Song | Length | Key cue / notes |
|---|------|--------|-----------------|
| 1 | Salt and Honey | 4:20 | Opener, solo vocal + guitar, builds to full band at 1:30 |
| 2 | Wildflower Sermon | 5:10 | Marisol lead vocal bridge |
| 3 | Lantern Song | 4:00 | Single, released spring 2026 |
| 4 | Old Roads | 5:40 | Acoustic interlude mid-song, band strips back |
| 5 | Foxglove Hill | 4:30 | Tamsin guest sit-in (Midnight Echoes member crossover, pre-rehearsed) |
| 6 | The Telling | 6:20 | Long outro, vocal over drone |
| 7 | Marrow and Bone | 5:00 | Set closer, big finish |

Total music: ~34:40. Transitions absorbed in song lengths and applause walks.

**The Midnight Echoes — main set 100 min, 16 songs**

| # | Song | Length | Notes |
|---|------|--------|-------|
| 1 | Aurora Burning | 5:30 | Show opener, CO2 jets on the downbeat |
| 2 | Foxgloves | 4:50 | |
| 3 | Glass Houses | 4:20 | Lead single from *Cathedral Pines* |
| 4 | Half-Light Avenue | 5:10 | |
| 5 | The Undertow | 6:00 | First synth feature |
| 6 | Wolf Hour | 5:40 | Lyric lights up |
| 7 | Northern Drift | 4:50 | Tamsin accordion feature |
| 8 | Cathedral Pines | 7:10 | Title track, longest song, no talk-over |
| 9 | Lowtide | 5:20 | |
| 10 | Harbour Lights | 4:30 | |
| 11 | Lacuna | 6:10 | Drum feature, Lior intro |
| 12 | Twin Stars | 4:50 | |
| 13 | Driftwood | 5:20 | Acoustic interlude centre-stage |
| 14 | Quiet Country | 4:40 | |
| 15 | Rivermouth | 6:30 | |
| 16 | Saturn Return | 7:00 | Set closer, full effects, confetti drop |

Encore — 15 min

| # | Song | Length | Notes |
|---|------|--------|-------|
| E1 | The Long Way Home | 5:30 | Pre-arranged first encore |
| E2 | Emberlight | 4:30 | Acoustic, duo with Margaux |
| E3 | Aurora Burning (reprise) | 5:00 | Closing, full band, pyro topper |

### 7.5 Key Equipment

| Dept | Equipment |
|------|-----------|
| Audio (FOH) | DiGiCo Quantum338 at FOH · Avid Venue S6L-32D at FOH (opener console, patched into stage rack) · L-Acoustics K2 house (per venue spec, 12-per-side) + KS28 subs (12 cardioid) + X8 front-fills · Lake LM44 system drive · Meyer Sound Galaxy 816 for opener drive on guest rig · Dante primary, MADI backup, analogue patch as last-resort |
| Audio (Monitors) | DiGiCo SD12 at monitors · 12 × Sennheiser G4 IEM mixes · 4 × Adamson M15 wedges (cue wedges for Sable Henson, Ronan, Margaux, Tamsin) · Shure PSM 1000 as fallback IEMs |
| RF | Shure Axient Digital AD4Q ×4 (8 channels per) · AD610 network showlink · Wireless Workbench 6.7 · passive splitter/distro (RF Venue CP Beam antenna, helical) · 16 × AD2 handhelds, 22 × AD1 beltpacks · FCC clean scan required 90 min before doors |
| Lighting | grandMA3 full-size (CRV) · 8 × Robe BMFL Blade (key) · 16 × Robe Esprite (wash) · 24 × Martin MAC Aura PXL · 12 × GLP JDC1 (strobe) · 6 × Ayrton Domino LT (audience blinder, audience-facing) · 8 × Robe Spiider (beam) · MDG Atmosphere ATMe + Me1 hazers (3 units) · Look Solutions Unique 2.1 hazers (2 units, redundancy) |
| Video | ROE Visual Black Quartz 4.6 mm LED, 14 m × 5 m main wall, Brompton Tessera SX40 · disguise gx 2c (main + backup, frame-locked, 25 GB content payload) · ATEM 4 M/E Constellation · 2 × Sony HXC-FB80 (FOH long, FOH short) · 1 × Sony FX9 (low-angle stage cam) · Panasonic AW-UE150 ×2 (robo SL/SR) · AJA FS-HDR for IMAG colour match |
| Automation | Kinesys Elevation 1+ (8 axes) — drum riser on lift, B-stage runways (no movement this show but rigged for), Kabuki drape drop on encore |
| SFX / Pyro | Le Maitre MVS haze (cross-rent redundancy with MDG) · 2 × Magic FX CO2 jet blasters (SL + SR) · confetti cannons — 6 × Magic FX CO2 confetti blasters pre-rigged for set closer + encore closer · Galaxis PYROTEC 36-channel firing module · Le Maitre Neuron radio remote (e-stop) |
| Comms | Clear-Com FreeSpeak II (1.9 GHz DECT + 2.4 GHz) — 14 packs · Riedel Bolero for tour core (PROD, SC, A1, LD, V1, SM) · ASL Intercom for guest opener crew (4 packs) |
| Recording | Avid Pro Tools Ultimate, 64 in / 64 out, mirrored drives · multitrack record all 64 channels from FOH split (post-Y-split, no mic-level pass) · ISO cameras to AJA Ki Pro GO 12-channel |

### 7.6 Master ROS

| Time | Duration | Stage Activity | Visual Cue | Audio Cue | Lighting Cue | Owner | Notes |
|------|----------|----------------|------------|-----------|--------------|-------|-------|
| `T-180:00` | — | **Load-in begins.** Truck arrives | — | — | — | `TD` (Okafor) | Stage plot walked before any case opens. Rigging plot on FOH riser |
| `T-150:00` | 60:00 | Rigging, lighting hang, LED build | — | — | — | `TD` (Okafor) | All hoist chains logged, secondary safeties on every fixture |
| `T-90:00` | 60:00 | Line check, focus, soundcheck prep | — | — | — | `A1` (Doyle) | FOH split confirmed. Sub array time-aligned to row 5 |
| `T-60:00` | — | **Doors.** RF scan completed, locked, logged | `VID 1 GO` — tour opener IMAG loop on house screens | `SQ 1 GO` — playlist "Aurora — doors", −28 LUFS-S | `LX 1 GO` — house full, stage wash 30%, architectural blue | `SC` (Herrera) | RF scan must be done by `T-75:00`. If scan fails, abort doors per venue safety plan |
| `T-58:00` | 02:00 | `BUF-01` — opener front-of-house soundcheck | — | `SQ 2 GO` — Sable & the Vesper Lights' own console line check via Dante | — | `A1` (Doyle) | Sable's FOH engineer at our S6L. All 4 opener mics verified |
| `T-50:00` | 30:00 | **Opener soundcheck** — Sable & the Vesper Lights, full set | — | — | — | `PROD` (Ljungberg) | Full run. Margaux + Tamsin guest sit-in for "Foxglove Hill" rehearsed with opener |
| `T-20:00` | 30:00 | **Headliner soundcheck** — Midnight Echoes, partial set | `VID 2 GO` — content rolls called, all cues triggered, timecode sync verified | `SQ 3 GO` — full band line check, click + tracks, ears and wedges balanced | `LX 2 GO` — LX programmer present, timecode MIDI + OSC verified, all looks fired | `PROD` (Ljungberg) | Soundcheck ends with full "Aurora Burning" + "Cathedral Pines" + "Saturn Return" run. No encore soundcheck — those are pre-set only |
| `T-15:00` | — | Confetti pre-rig check | — | — | — | `PYRO` (Mbatha) | Both confetti blasters charged, firing script locked in Galaxis, dead-man verified |
| `T-10:00` | — | Pyro walk-through with SFX, SM, security | — | — | — | `TD` (Okafor) | All firing cues walked physically on stage. Fire warden sign-off |
| `T-05:00` | — | House to half, walk-in music | `VID 3 GO` — IMAG off, merch QR on screens, opener logo hold | `SQ 4 GO` — playlist "Aurora — walk-in", −26 LUFS-S | `LX 3 GO` — house to 65%, stage wash 20% | `SC` (Herrera) | |
| `T-02:00` | 02:00 | House to quarter | — | `SQ 5 GO` — playlist down to −30 LUFS-S | `LX 4 GO` — house to 30% over 5 s | `SC` (Herrera) | House lights down signals "show soon" — audience settles |
| `T-00:30` | 00:30 | Walk-in music out | — | `SQ 6 GO` — music fade to silence over 15 s | `LX 5 GO` — stage wash 20% hold | `A1` (Doyle) | |
| `T-00:15` | 00:15 | House to blackout | — | — | `LX 6 GO` — house to 0% over 8 s | `SC` (Herrera) | 15 s of dark = opener intro film beat |
| `T+00:00:00` | 02:00 | **SHOW START.** Opener intro film — Sable & the Vesper Lights mark | `VID 10 GO` — opener brand film, full 14 m wall, 2:00 | `SQ 10 GO` — bed to −6 dBFS, sub-light | `LX 10 GO` — blackout hold, wall only | `SC` (Herrera) | Hard anchor. Wall clock 19:30:00. Band moves to marks in the dark |
| `T+00:02:00` | 00:20 | Sable Henson walk-on | `VID 11 GO` — wall to opener stage backdrop, cut CAM 1 wide | `SQ 11 GO` — CH31 unmute, IEM mix 7 up | `LX 11 GO` — centre key up over 3 s, soft warm wash | `SM` (O'Sullivan) | Solo vocal + guitar first. Band members already seated at marks |
| `T+00:02:20` | 04:20 | "Salt and Honey" | `VID 12 GO` — CAM 1 wide, slow push to medium | `SQ 12 GO` — full band up at 1:30, monitor world sends bus change | `LX 12 GO` — full stage wash 60%, keylight on Sable, 4 s | `PROD` (Ljungberg) | Opener rises to full band 1:30 in. A1 rides the build |
| `T+00:06:40` | 05:10 | "Wildflower Sermon" | `VID 13 GO` — director's cut, CAM 1/2 alternating | `SQ 13 GO` — Marisol lead vocal to mix, reverb send +20% | `LX 13 GO` — Marisol keylight up at lead vocal entry, 2 s | `PROD` (Ljungberg) | |
| `T+00:11:50` | 04:00 | "Lantern Song" | `VID 14 GO` — single art on IMAG side panels at first chorus | `SQ 14 GO` — backing vocal layer open, CH33 up | `LX 14 GO` — audience warm wash 40% on chorus | `PROD` (Ljungberg) | Released single, audience sing-along expected |
| `T+00:15:50` | 05:40 | "Old Roads" — acoustic interlude | `VID 15 GO` — CAM 2 tight on Sable, ACOUSTIC camera mode | `SQ 15 GO` — band strips back, channels 32/34/36 mute briefly at 1:30, DCA7 to −∞, reopen at 3:00 | `LX 15 GO` — strip back to single keylight + amber side wash, 5 s | `PROD` (Ljungberg) | Quietest moment of the opener |
| `T+00:21:30` | 04:30 | "Foxglove Hill" — Tamsin crossover | `VID 16 GO` — CAM 1 wide, name-strap "Tamsin Whitfield (Midnight Echoes)" 3 s | `SQ 16 GO` — Tamsin's channels pre-set (CH16/17/18 unmuted), IEM mix 5 to foldback | `LX 16 GO` — Tamsin keylight up at 0:30 entry, 2 s | `PROD` (Ljungberg) | Pre-rehearsed with opener. Tamsin knows the song from session |
| `T+00:26:00` | 06:20 | "The Telling" | `VID 17 GO` — CAM 3 low-angle on Sable's guitar, slow orbits | `SQ 17 GO` — long outro, drone layer pre-armed | `LX 17 GO` — slow build audience wash 20%→60% over the outro, 30 s | `PROD` (Ljungberg) | Drone outro is the opener's emotional close before the build |
| `T+00:32:20` | 05:00 | "Marrow and Bone" — set closer | `VID 18 GO` — CAM 1 wide, full band | `SQ 18 GO` — final hit, all hands up to show level | `LX 18 GO` — audience blinder full at final downbeat (LX 18), 1 s | `PROD` (Ljungberg) | First confetti of the night is the opener's closer — `SFX 1 GO` |
| `T+00:37:20` | 02:40 | Opener bow, exit | `VID 19 GO` — CAM 1 wide 4-shot | `SQ 19 GO` — applause bed at −24 LUFS-S under band wave | `LX 19 GO` — house to 60%, stage wash 80%, 4 s | `SM` (O'Sullivan) | 4 members exit SR in order — bass, drums, violin, then Sable + Wynn. SM has them pre-staged at `T+00:35:00` |
| `T+00:40:00` | — | **INTERMISSION.** Changeover to headliner | — | — | — | `TD` (Okafor) | Stage clear. Opener gear struck to SL quick-change position |

| `T+00:40:00` | 25:00 | **CHANGEOVER** — full set strip and rebuild | `VID 20 GO` — intermission slate (countdown clock + tour sponsor loop), 25:00 total | `SQ 20 GO` — changeover playlist "Aurora — intermission", −28 LUFS-S | `LX 20 GO` — house 50%, stage wash 30%, no change | `TD` (Okafor) | **Changeover absorbs 8:00 of planned buffer.** 25:00 total includes 8:00 of buffer against the 17:00 actual rebuild. See §4 |
| `T+00:40:00` | 05:00 | **Phase 1** — Opener gear to SL | — | — | — | `TD` (Okafor) | Opener crew strikes their own gear. Their FOH engineer unplugs from our stage rack |
| `T+00:45:00` | 15:00 | **Phase 2** — Midnight Echoes risers, drums, keys to marks | — | — | — | `TD` (Okafor) | Drum riser already in position. Tamsin Rhodes centre stage. Dmitri and Margaux amps |
| `T+00:60:00` | 04:00 | **Phase 3** — Headline soundcheck (line + IEMs, no music) | — | `SQ 21 GO` — headliner IEMs (mixes 1-6) up, all AD1 packs verified | — | `A2` (Hara) | **Ronan is on standby at the B-stage, vocal check done.** House is still half-light |
| `T+00:64:00` | 01:00 | **Phase 4** — SFX / pyro verification | — | — | — | `PYRO` (Mbatha) | CO2 jets armed for `LX 100`. Confetti cannons confirmed for `LX 116` and `LX 130` |
| `T+00:65:00` | 00:15 | House to blackout, headliner intro film | `VID 100 GO` — Midnight Echoes brand film, 1:00, full wall | `SQ 100 GO` — silence hold, then bass swell at 0:55 | `LX 100 GO` — full blackout over 8 s | `SC` (Herrera) | Band already in position. This is the headliner breath |
| `T+01:06:00` | 00:15 | Band intro walk-on | `VID 101 GO` — wall to set backdrop, IMAG live | `SQ 101 GO` — CH1 unmute at centre mark | `LX 101 GO` — centre key up at 0:08 (Ronan walks on the downbeat) | `SM` (O'Sullivan) | Ronan walks from SR. Band already at marks |
| `T+01:06:15` | 05:30 | "Aurora Burning" — show opener | `VID 102 GO` — director's cut, CAM 1/2/3 sequence, wall to timecode-locked content | `SQ 102 GO` — band up at 0:30, CO2 jets `SFX 2 GO` at first downbeat | `LX 102 GO` — full stage wash 100%, `LX 103` strobe accent at 1:00 chorus, `LX 104` blinder on chorus hits | `PROD` (Ljungberg) | **Highest-energy moment in show so far. Audience on their feet from song 1.** SM stationed at SR for crowd-surf risk |
| `T+01:11:45` | 04:50 | "Foxgloves" | `VID 105 GO` — CAM 2 medium on Margaux, cuts to Ronan chorus | `SQ 103 GO` — Margaux guitar up +3 dB for lead, backing vocal bus up | `LX 105 GO` — strobe accents on chorus, audience wash 50% | `PROD` (Ljungberg) | |
| `T+01:16:35` | 04:20 | "Glass Houses" — lead single | `VID 106 GO` — single art card at chorus 1, CAM 1 wide for sing-along | `SQ 104 GO` — backing vocal bus +6 dB (audience support) | `LX 106 GO` — audience blinder at every chorus hit | `PROD` (Ljungberg) | Biggest audience sing-along. A1 pre-warned |
| `T+01:20:55` | 05:10 | "Half-Light Avenue" | `VID 107 GO` — CAM 3 low-angle, slow orbits | — | `LX 107 GO` — moody palette, deep blue + magenta, 4 s | `PROD` (Ljungberg) | Tempo drops here, first mid-set breath |
| `T+01:26:05` | 06:00 | "The Undertow" — first synth feature | `VID 108 GO` — abstract content on wall, timecode-locked | `SQ 105 GO` — Dmitri synth bass layer in, Lior adds sub | `LX 108 GO` — synth-wave palette, beam work, 4 s | `PROD` (Ljungberg) | First song where LED content takes the visual lead |
| `T+01:32:05` | 05:40 | "Wolf Hour" — lyric lights up | `VID 109 GO` — lyric graphics lower-third across IMAG, 5 lines of lyric scroll | `SQ 106 GO` — vocal bus isolated for clarity | `LX 109 GO` — Ronan keylight only, deep red backlight | `PROD` (Ljungberg) | Band goes visually minimal. Song carries it |
| `T+01:37:45` | 04:50 | "Northern Drift" — Tamsin accordion feature | `VID 110 GO` — CAM 1 wide, push to Tamsin 2-shot with Ronan | `SQ 107 GO` — Tamsin's accordion mic (CH18) up +4 dB, accordion reverb send +10% | `LX 110 GO` — Tamsin keylight on entry, 2 s | `PROD` (Ljungberg) | |
| `T+01:42:35` | 07:10 | "Cathedral Pines" — title track | `VID 111 GO` — full wall content cycle, 12 unique frames | `SQ 108 GO` — full band + Ingrid violin feature at 3:00 | `LX 111 GO` — palette cycle through 6 looks, one per minute | `PROD` (Ljungberg) | Longest song. No talk-over from MC. Set is unbroken |
| `T+01:49:45` | 05:20 | "Lowtide" | `VID 112 GO` — CAM 2 medium on Ronan, slow cuts | — | `LX 112 GO` — palette settle to deep teal, beam accents | `PROD` (Ljungberg) | |
| `T+01:55:05` | 04:30 | "Harbour Lights" | `VID 113 GO` — CAM 1 wide | `SQ 109 GO` — Ingrid vocal (CH21) up for harmonies | `LX 113 GO` — warm amber wash, gentle | `PROD` (Ljungberg) | |
| `T+01:59:35` | 06:10 | "Lacuna" — drum feature | `VID 114 GO` — overhead drum cam from lighting truss, full kit shot | `SQ 110 GO` — Lior click + tracks, sub-heavy mix, kick +6 dB | `LX 114 GO` — overhead blinder at every fill, palette white-red-white | `PROD` (Ljungberg) | Lior's spotlight moment. V1 fires the overhead cam live from the truss |
| `T+02:05:45` | 04:50 | "Twin Stars" | `VID 115 GO` — director's cut | — | `LX 115 GO` — return to standard palette | `PROD` (Ljungberg) | |
| `T+02:10:35` | 05:20 | "Driftwood" — acoustic centre-stage | `VID 116 GO` — CAM 2 tight on Ronan, ACOUSTIC mode | `SQ 111 GO` — full band strips, only Ronan + Margaux acoustic + Ingrid violin | `LX 116 GO` — strip to single keylight + amber side, 5 s | `PROD` (Ljungberg) | Quietest moment of the headliner set |
| `T+02:15:55` | 04:40 | "Quiet Country" | `VID 117 GO` — IMAG returns, director's cut | — | `LX 117 GO` — gentle build, palette warm | `PROD` (Ljungberg) | Acoustic interlude ends |
| `T+02:20:35` | 06:30 | "Rivermouth" | `VID 118 GO` — full wall content, IMAG full screen for chorus | `SQ 112 GO` — band up, mix bus normal | `LX 118 GO` — full stage wash, audience blinder on chorus | `PROD` (Ljungberg) | |
| `T+02:27:05` | 07:00 | "Saturn Return" — set closer | `VID 119 GO` — timecode content, all cues synced | `SQ 113 GO` — full band, all hands | `LX 119 GO` — build palette, `LX 120` strobe + blinder + CO2 jets + confetti — all on the final downbeat | `PROD` (Ljungberg) | **`SFX 3 GO` (confetti SL + SR) at final downbeat. `SFX 4 GO` (CO2 jets SL + SR) at penultimate bar.** Stage clears to band wave |
| `T+02:34:05` | 01:00 | Band wave, exit to encores | `VID 121 GO` — CAM 1 wide, IMAG live | `SQ 114 GO` — applause bed under | `LX 121 GO` — house to 40%, stage wash 30%, encore cue | `SM` (O'Sullivan) | Band clears stage to encores position. House lights stay low |
| `T+02:35:05` | 04:00 | **ENCORE CALL** — house lights up, band returns | — | `SQ 115 GO` — applause playlist at −18 LUFS-S, full-volume audience bed | `LX 122 GO` — house to 100%, audience blinder double-tap | `SM` (O'Sullivan) | Standard encore call. House up tells the audience the band is coming back. Claps continue until band walks on |
| `T+02:39:05` | 00:15 | Band returns to marks | `VID 122 GO` — IMAG live, "ENCORE" strap | `SQ 116 GO` — applause bed out | `LX 123 GO` — house down to 30% over 5 s | `SM` (O'Sullivan) | |
| `T+02:39:20` | 05:30 | "The Long Way Home" — encore 1 | `VID 123 GO` — director's cut | `SQ 117 GO` — full band | `LX 124 GO` — warm palette, audience wash 60% | `PROD` (Ljungberg) | |
| `T+02:44:50` | 04:30 | "Emberlight" — duo with Margaux | `VID 124 GO` — CAM 2 tight on Ronan + Margaux, ACOUSTIC mode | `SQ 118 GO` — Margaux acoustic pickup (CH11) up, full band strips | `LX 125 GO` — strip to two keylights, intimate palette, 3 s | `PROD` (Ljungberg) | Duo. Audience phones-up expected. Pyro charged but not firing |
| `T+02:49:20` | 05:00 | **"Aurora Burning" (reprise)** — closing, full pyro | `VID 125 GO` — wall to opener film callback, director's cut | `SQ 119 GO` — full band, all hands | `LX 126 GO` — full stage, palette cycle. **At final downbeat: `LX 127` blinder, `SFX 5` confetti top-off, `SFX 6` CO2 jet final, `LX 128` strobe full** | `PROD` (Ljungberg) | **Show finale. Maximum effect. Pyro officer gives silent "GO" hand signal to PROD at the top of the song.** |
| `T+02:54:20` | 01:30 | Band wave, walk-off | `VID 126 GO` — CAM 1 wide | `SQ 120 GO` — applause bed, bed up to show level | `LX 129 GO` — house to 60%, audience blinder slow pulse | `SM` (O'Sullivan) | Band walks off in order: Margaux, Dmitri, Lior, Ingrid, Tamsin, Ronan last |
| `T+02:55:50` | — | **WALK-OUT.** Stage clear, venue to half | `VID 127 GO` — house screens to merch QR + tour dates | `SQ 121 GO` — walk-out playlist "Aurora — out", −28 LUFS-S | `LX 130 GO` — house to 50%, stage wash 30% | `SC` (Herrera) | Stage strike does not begin until house is empty |
| `T+02:55:50` | 04:10 | `BUF-02` — pre-strike hold, house clear | — | `SQ 122 GO` — playlist hold | `LX 131 GO` — house hold | `SC` (Herrera) | Audience file-out takes 3-5 min. Do not strike anything in front of audience |
| `T+03:00:00` | — | **SHOW COMPLETE.** Stream ends, multitrack record verified | `VID 128 GO` — stream slate, PGM to black | `SQ 123 GO` — walk-out music out, console to safe scene | `LX 132 GO` — work light, all haze off | `STR` (McBride) | Verify all 64-channel ProTools record, all ISO records, and the audience-facing stereo record before strike. Multitrack copy uploaded to tour Dropbox within 60 min |

**Contingency rows:**

| Trigger | Action | Owner |
|---------|--------|-------|
| RF interference, single channel | `MIC n.5` — reallocate AD1 to clean frequency from WWB scan pool, hot-swap transmitter | `A2.2` (Kuznetsov) |
| Headliner mic failure (Ronan) | `MIC 1.5` — spare AD2/KSM9 in SR rack, hand to SM, swap mid-song if visible drop | `A2` (Hara) |
| IEM failure, any band member | `MIC n.6` — fallback to PSM 1000 receiver pack on the same mix | `A2` (Hara) |
| CO2 jet misfire during opener | `SFX 2` and `SFX 6` aborted, no action — jets are not load-bearing in the show | `PYRO` (Mbatha) |
| Confetti cannon fails at set closer | `LX 120` proceeds without confetti — visual is bonus, not required | `PYRO` (Mbatha) |
| FOH console fault | `A1` switches to backup DiGiCo SD12 in FOH rack (pre-patched, hot-standby from `T-60:00`) | `A1` (Doyle) |
| Monitor console fault | `A2` switches to Avid S6L-32D already on stage for opener, re-patched in 90 s | `A2` (Hara) |
| LED wall single-panel failure | `VID n` continues, V1 reframes to exclude dead panel — pre-known acceptable zone | `V1` (Larsson) |
| LED wall controller fault | `VID n` cuts to IMAG-only mode, full 4-camera director cut | `V1` (Larsson) |
| Power loss to stage | `LX 133 GO` — emergency work light on house UPS, all PA to muted, show stops, evacuation procedure per venue plan | `TD` (Okafor) |
| Medical emergency in GA pit | `SC` announces "house to half", security to pit, medical team in. Show pauses, does not abort unless `MED` declares | `SC` (Herrera) + `MED` |
| Variance >+8:00 by song 5 | Cut "Wolf Hour" and "Northern Drift" — both are skippable, no lyrical callback | `PROD` (Ljungberg) |
| Variance >+12:00 by song 12 | Cut encore 2 ("Emberlight") — keep only "The Long Way Home" and the reprise | `PROD` (Ljungberg) |

---

## 8. Version Control Protocol

### 8.1 Filename Convention

Every ROS file follows this pattern, with no exceptions:

```
ROS_<EventCode>_<VenueCode>_v<X.Y>_<YYYY-MM-DD>_<StatusTag>.<ext>
```

| Token | Rule | Example |
|-------|------|---------|
| `<EventCode>` | 6-12 chars, alphanumeric, no spaces. Client abbreviation + event type | `NorthwindFY27`, `HelixORBIT2`, `MidnightEchoesGLA` |
| `<VenueCode>` | 3-5 char IATA-style or internal venue code | `SEA`, `SHOR`, `GLA` |
| `<X.Y>` | Revision number. `X` = major (content restructure), `Y` = minor (cue/duration edits) | `v1.0`, `v2.1`, `v3.0` |
| `<YYYY-MM-DD>` | Date of issue, ISO 8601 | `2026-09-16` |
| `<StatusTag>` | One of `DRAFT`, `INREVIEW`, `FINAL`, `VOID`, `SUPERSEDED` | `FINAL` |
| `<ext>` | `.md`, `.pdf`, `.docx`, or `.xlsx` | `.pdf` is the printed master |

Worked examples (matching §5 and §6 headers):

- `ROS_NorthwindFY27_SEA_v2.1_2026-09-16_FINAL.pdf` — printed master at the show caller's binder
- `ROS_HelixORBIT2_SHOR_v3.0_2026-10-07_FINAL.pdf` — printed master
- `ROS_MidnightEchoesGLA_GLA_v2.4_2026-11-13_FINAL.pdf` — printed master

Working files (Markdown source, not yet promoted):

- `ROS_NorthwindFY27_SEA_v2.1_2026-09-16_INREVIEW.md`

Old files are never deleted. They are renamed `SUPERSEDED` and stored in `docs/knowledge-base/04-templates-and-matrices/archive/`.

### 8.2 Revision Numbering

| Change scope | Bump | Notes |
|--------------|------|-------|
| Spelling fix, single-cue typo, contact detail | Minor (`v1.0` → `v1.1`) | Producer + show caller sign-off |
| Cue addition, deletion, retiming, owner reassignment | Minor (`v1.1` → `v1.2`) | Show caller sign-off |
| Restructure of a segment, runtime re-budget, venue change | Major (`v1.x` → `v2.0`) | Producer + client lead sign-off |
| Cancellation or re-format (e.g., keynote → fireside chat) | Major (`v2.x` → `v3.0`) | Producer + client lead + show caller sign-off |

**Rule:** every bump produces a new file with a new date stamp. Do not edit a file in place and bump only the header — the file's mtime must match the date stamp or the version control story collapses.

### 8.3 Status Tags

| Status | Meaning | Distribution | Authority |
|--------|---------|--------------|-----------|
| `DRAFT` | Working document, not for crew | Producer only | Producer |
| `INREVIEW` | Department heads reviewing their columns | Department leads (A1, LD, V1, SM, PROD) | Producer |
| `FINAL` | Rehearsals completed, locked, distributed | All crew + client + venue | Producer + show caller |
| `VOID` | Document cancelled (event postponed, replaced) | Distributed only to confirm cancellation | Producer |
| `SUPERSEDED` | Replaced by a newer revision | Replaced; old file moved to archive | Producer |

A document in `FINAL` is the only state that ships. `DRAFT` and `INREVIEW` documents are never in the show caller's binder during the show.

### 8.4 Distribution

| Recipient | Format | State at delivery | Notes |
|-----------|--------|-------------------|-------|
| Show caller | Printed, binder-bound, with plastic sleeves | `FINAL` only | The reference of last resort. If two documents disagree, this wins |
| Producer | PDF + Markdown source | `FINAL` + latest | Owns the source file |
| Department heads (A1, A2, V1, LD, SM, TD, STR) | PDF, single-department extract optional | `FINAL` + latest | Extract shows their column plus Stage Activity for context |
| Client / talent | PDF, sanitised — strips Owner column, strips internal Notes | `FINAL` (sanitised variant `*_client.pdf`) | Never the master |
| Venue ops / FOH manager | PDF | `FINAL` | Per venue contract |
| Stream / broadcast partner | PDF + M3U of stream beds | `FINAL` + bed list | Stream lead confirms receipt at T-3 days |

**Distribution channel:** encrypted file share with read receipts. Email is not the distribution channel for `FINAL`. The exception is a single confirming email at T-7 days that says "the FINAL document is in the share" with the link — the email is the receipt, not the document.

### 8.5 Lock and Release

| Phase | Time | State | Action |
|-------|------|-------|--------|
| Open editing | T-14 to T-7 | `DRAFT` | Producer + department heads |
| Department sign-off | T-7 to T-3 | `INREVIEW` | Each department head signs their column |
| Cue lock | T-3 | `INREVIEW` (numbered) | Cue numbers frozen. All changes become point cues or in-line annotations |
| Rehearsal mark-up | T-1 | `INREVIEW` (annotated) | Show caller marks up the printed master in pencil |
| FINAL lock | T-1 (end of rehearsal) | `FINAL` | Producer produces FINAL PDF, show caller counter-signs |
| Show day | T+0 | `FINAL` (binder) | No further changes. Pencil annotations are reconciled within the FINAL — they do not produce a new revision during the show |
| Post-show | T+1 | `SUPERSEDED` if revised for tour, else archived | Tour events may get a tour-final revision before archive |

**Rule:** during the show, the binder never opens for a write. Pencil annotations stay in the binder as the caller's record; the source file is updated within 24 hours of strike.

### 8.6 Change Log

Every `INREVIEW` and `FINAL` revision ships with a change log appended. Format:

```
## Change Log

| Version | Date | Changed by | Change |
|---------|------|-----------|--------|
| v1.0 | 2026-08-25 | Lin | Initial skeleton from client agenda |
| v1.1 | 2026-08-28 | Doyle | SQ 8–13 updated with new bed filenames |
| v1.2 | 2026-09-02 | Mbeki | LX 16 added — centre stage special for demo |
| v1.3 | 2026-09-08 | Tanaka | BUF-05 retimed from 0:30 to 1:00 |
| v2.0 | 2026-09-10 | Lin | Major — panel restructured, runtime re-budgeted |
| v2.1 | 2026-09-16 | Tanaka | FINAL. Pencil marks from dress rehearsal reconciled |
```

The change log is the audit trail. When a cue fails in the show and the question is "when did this change and who approved it", the change log answers in under a minute. If the change log is missing from a `FINAL`, the document is not `FINAL` — return it to `INREVIEW`.

### 8.7 Audit at Hand-Over

When a show caller hands over to a relief caller (multi-day events, festival splits), the hand-over includes:

1. Current `FINAL` revision read aloud, page by page. No skim-reading.
2. Variance status, current state (GREEN/AMBER/RED), and recovery levers already armed.
3. Change log for the last 24 hours reviewed together.
4. Pencil annotations from the prior session reconciled into the source file before hand-over.

Hand-over without these four steps is not a hand-over. The incoming caller inherits all authority and all liability; the show does not pause for a missing hand-over.

<!-- APPEND -->
