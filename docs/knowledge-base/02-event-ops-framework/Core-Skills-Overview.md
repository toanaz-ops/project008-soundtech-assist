# Core Skills Overview: Live Event Operations Framework

## Overview

Six operational disciplines determine whether a live event runs to plan or degrades into visible failure. Each is defined here with its equipment stack, step-by-step execution workflow, catalogued failure modes, and measurable success criteria. These skills are interdependent: a Run of Show is only executable if signal flow is deterministic, and crisis failover is only zero-latency if redundancy was commissioned during load-in.

### Skill Ownership & Blast Radius

| # | Skill | Primary Owner | Key Metric | Failure Blast Radius |
|---|-------|---------------|------------|----------------------|
| 1 | Master ROS Execution | Show Caller / Producer | Schedule variance ≤ ±2 min | Entire event timeline |
| 2 | AV/IT Signal Flow | Video Engineer / AV Lead | Zero unplanned black frames | All visual content |
| 3 | FOH Management | FOH Engineer (A1) | GBF ≥ 6 dB below feedback | All audience audio |
| 4 | Microphone Routing | A1 / A2 | Masking index, NOM discipline | Speech intelligibility |
| 5 | Stage Management | Stage Manager (SM) | Cue accuracy ≥ 98% | Talent flow, onstage errors |
| 6 | Live Crisis Protocol | Technical Director (TD) | MTTR by tier (see §6) | Event survivability |

**Reading note on §4:** the brief for this document proposed assigning microphones by source frequency content (low-frequency sources to omnidirectional, high-frequency to cardioid). That heuristic does not reflect professional practice and will degrade gain-before-feedback if applied literally. §4 documents the actual selection criteria and shows exactly where the frequency-first rule breaks. The legitimate frequency-domain work in live routing is spectral zone allocation and HPF discipline, which is covered in full.

---

## 1. Master Run of Show (ROS) Execution

### 1.1 Definition

The Run of Show is the single authoritative, time-indexed instruction set for an event. It differs from an agenda: an agenda states what happens, an ROS states who executes what, on which cue, at which timecode, with which asset loaded. The **show caller** owns the ROS during live execution and is the only voice authorized to issue `GO`. One ROS, one caller, one clock. Every department works from the same document revision.

Three artefacts derive from the master ROS:

| Artefact | Audience | Contains | Excludes |
|----------|----------|----------|----------|
| Master ROS | Show caller, TD, SM | All cues, all departments, buffers, contingencies | Nothing |
| Department cue sheet | A1, V1, L1, Stream | Only that department's cues + 2 cues of lead-in context | Other departments' internals |
| Client/talent agenda | Speakers, client leads | Segment titles, wall-clock times, stage positions | Cue IDs, technical detail |

### 1.2 Equipment & Tools

| Tool | Function | Deployment Notes |
|------|----------|------------------|
| Shoflo / Rundown Creator | Cloud ROS, live collaborative edit | Real-time sync to all stations; requires network uptime |
| Printed ROS (hard copy) | Offline authority | Mandatory. Network-independent. Revision-stamped, timestamped |
| Stage Timer Pro / Irisdown | Presenter countdown on confidence monitor | Drives speaker self-management |
| QLab / Ableton / Playback Pro | Cue-locked media playback | Timecode master when show is LTC-driven |
| LTC generator (Rosendahl mif4) | Timecode distribution | Only for fully pre-programmed segments |
| Comms (see §5.2) | Cue transmission | Show caller on dedicated channel |

### 1.3 ROS Column Schema

Every row is one cue or one segment. Minimum viable column set:

| Column | Format | Example | Why It Exists |
|--------|--------|---------|---------------|
| Cue ID | `PREFIX-###` | `V-045` | Unambiguous verbal reference over comms |
| Clock | `HH:MM:SS` (24h) | `09:42:00` | Wall-clock anchor for client and venue |
| Elapsed | `+MM:SS` | `+12:00` | Show-relative; survives late starts |
| Duration | `MM:SS` | `03:30` | Feeds buffer math |
| Segment | Text | "Keynote A walk-on" | Human context |
| Trigger | Enum | `Caller GO` / `LTC 01:12:00:00` / `Self` | Defines who initiates |
| Dept | Enum | `AUD / VID / LX / STR / SM` | Filters department sheets |
| Action | Imperative | "Fade CH1-3 to 0, unmute CH4" | Executable without interpretation |
| Notes | Text | "Speaker walks SL, hand-held" | Edge cases |

### 1.4 Minute-by-Minute Workflow (Corporate Keynote, 800-seat ballroom)

```
CLOCK     ELAPSED  DUR    CUE     DEPT  ACTION
────────────────────────────────────────────────────────────────────────────
08:30:00  -30:00   —      —       ALL   Doors. Walk-in music -35 dB LUFS-S,
                                        holding slide live, house LX 100%
08:55:00  -05:00   —      SM-001  SM    Talent to holding. Confirm 3 mics live
08:58:00  -02:00   02:00  V-010   VID   Roll 2-min countdown on IMAG + confidence
08:59:30  -00:30   —      A-010   AUD   Walk-in music fade start (30s ramp)
09:00:00  +00:00   00:20  L-010   LX    House to 30%, stage wash to 100%
09:00:00  +00:00   —      A-011   AUD   CH4 (Host, handheld) unmute, DCA1 up
09:00:20  +00:20   02:40  V-011   VID   Cut to Host camera (PGM 1). Lower-third IN
09:03:00  +03:00   00:15  SM-002  SM    Standby Keynote A in SL wing
09:03:00  +03:00   —      A-012   AUD   CH1 (Keynote A lectern) unmute, DCA2 up
09:03:15  +03:15   18:00  V-012   VID   Cut to PPT (Presenter laptop A), IMAG PIP
09:03:15  +03:15   —      T-001   VID   Start 18:00 presenter countdown timer
09:21:15  +21:15   —      SM-003  SM    Timer at 00:00 → SM visual 2-min warning
09:23:15  +23:15   —      BUF-01  ALL   ** 2:00 ELASTIC BUFFER **
09:25:15  +25:15   00:30  V-013   VID   Cut to Host camera, PPT to hold slide
09:25:15  +25:15   —      A-013   AUD   CH1 mute, CH4 unmute (crossfade 300ms)
```

Buffer rows (`BUF-nn`) are first-class ROS entries, not slack. They have IDs so the caller can announce "we are in BUF-01, burning 40 seconds" and every department understands the state.

### 1.5 Time Buffer Protocols

**Allocation rule:** budget 8% of total program runtime as distributed buffer, never as a single block at the end. A 4-hour (240 min) event carries ~19 min of buffer, placed at transition points where recovery is cheapest.

| Buffer Type | Size | Placement | Consumable By |
|-------------|------|-----------|---------------|
| Transition | 0:15–0:30 | Between every speaker change | Slow walk-ons, mic handoffs |
| Elastic | 1:00–3:00 | After each major segment | Speaker overrun, Q&A spill |
| Structural | 5:00–15:00 | Meal/coffee breaks | Major recovery, reboots, re-patch |
| Hard reserve | 5:00 | Immediately pre-close | Never touched except P0/P1 crisis |

**Burn-down tracking.** The caller maintains a running variance figure and announces it at every segment boundary:

```
variance = actual_elapsed − scheduled_elapsed
remaining_buffer = total_allocated_buffer − consumed
```

| Variance | State | Caller Action |
|----------|-------|---------------|
| −1:00 to +1:00 | GREEN | Announce "on time" at boundaries only |
| +1:00 to +5:00 | AMBER | Announce variance each segment; arm lever 1–2 |
| +5:00 to +10:00 | RED | Notify client lead; execute levers 2–4 |
| > +10:00 | CRITICAL | Client decision required on cut list (pre-agreed) |

**Recovery levers, ranked least-to-most visible.** Escalate in order; never skip to a high-visibility lever while a low one remains.

| # | Lever | Recovers | Audience Visibility |
|---|-------|----------|---------------------|
| 1 | Absorb transition buffers | 0:15–0:30 each | None |
| 2 | Tighten walk-ons; pre-set talent in wing | 0:20–0:45 each | None |
| 3 | Shorten Q&A by question count (not clock) | 1:00–4:00 | Low |
| 4 | Compress break by 5 min (announce early) | 5:00 | Medium |
| 5 | Cut pre-identified expendable segment | 5:00–15:00 | Medium |
| 6 | Reduce closing remarks to pre-written short version | 2:00–5:00 | Low |

**Pre-agreement requirement:** the cut list (lever 5) and the short-close script (lever 6) must be signed off by the client during rehearsal, in writing. Deciding what to cut while +12 minutes down is how events lose their close.

### 1.6 Visual & Audio Cue Handoffs

**Cue ID prefixes** — spoken as letter + number, never as bare numbers:

| Prefix | Department | Example Action |
|--------|-----------|----------------|
| `A-` | Audio | Mute/unmute, DCA move, playback start |
| `V-` | Video | Switcher take, source change, graphic in/out |
| `L-` | Lighting | Look recall, house level change |
| `SM-` | Stage Management | Talent move, standby, handoff |
| `STR-` | Stream | Scene change, stream start/stop, slate |
| `T-` | Timer | Countdown start/stop/reset |
| `BUF-` | All | Buffer window entry |

**Standby / GO protocol.** Two-phase, always. Standby is issued 10–30 s ahead; GO is the execution instant.

```
CALLER:  "Standby video 45, audio 13."
V1:      "Video 45 standing by."          ← acknowledgement mandatory
A1:      "Audio 13 standing by."
         ... (10-30 s) ...
CALLER:  "Video 45 ... GO."                ← operative word is LAST
```

The word `GO` is terminal in the sentence so operators never fire on a mid-sentence utterance. `GO` is reserved exclusively for execution — never used conversationally on comms. To cancel a standby: "Video 45, **hold**." To abandon: "Video 45, **clear**."

**Handoff medium selection:**

| Cue Type | Medium | Latency (human) | Use When |
|----------|--------|-----------------|----------|
| Technical execution | Comms verbal | 200–500 ms | Operator wearing headset |
| Talent entrance | Cue light (red→out) | 150–300 ms | Wing position, silence required |
| Talent timing | Confidence monitor timer | Self-paced | Presenter on stage |
| Talent urgent | IFB whisper | 300–800 ms | Presenter has earpiece |
| Talent fallback | SM hand signal | 500 ms–2 s | No IFB, sightline exists |
| Camera awareness | Tally light | < 100 ms | Multi-camera presenter |

**Audio/video sync at handoff.** A speaker change requires the mic transition to lead the video take slightly — audio-first prevents a visible mouth-moving-in-silence frame. Standard offset: unmute the incoming mic 200–300 ms before the switcher take.

### 1.7 Common Failure Modes

| Symptom | Root Cause | Detection | Fix / Prevention |
|---------|-----------|-----------|------------------|
| Two operators fire different cues on one GO | Duplicate cue numbers across departments | Cue collision during rehearsal | Enforce prefix scheme; validate IDs unique |
| Operator fires early | `GO` not sentence-final, or no standby phase | Premature take in rehearsal | Retrain: standby → ack → GO-last |
| Departments working from different plans | Uncontrolled ROS revisions | Version mismatch found mid-show | Revision + timestamp in footer; verbal confirm at pre-show |
| Cascading overrun, no recovery | Buffer placed only at event end | Variance > +10 min by mid-show | Distribute buffer per §1.5 |
| Caller loses timeline position | No elapsed clock, only wall-clock | Caller asks "where are we?" | Dual clock display: wall + elapsed |
| Client requests live reorder | No change-control path | Verbal request mid-show | Route all changes through single producer; caller may refuse |
| Speaker ignores countdown | Timer not in sightline, or no consequence | Overrun past 00:00 | Confidence monitor at eye line + escalation §6.6 |
| Talent misses entrance | Cue light unseen / SM not in position | Empty stage on take | SM physically walks talent to mark |

### 1.8 Success Metrics

| Metric | Definition | Target | Measurement Method |
|--------|-----------|--------|--------------------|
| Schedule variance at close | actual end − scheduled end | ≤ ±2 min | Wall clock vs ROS |
| Max intra-show variance | peak absolute variance | ≤ 5 min | Caller variance log per segment |
| Cue execution accuracy | correct cues / total cues | ≥ 98% | Post-show cue log review |
| Cue timing precision | mean deviation from intended frame | ≤ 500 ms | Recording timecode analysis |
| Buffer consumption | consumed / allocated | ≤ 70% | Burn-down log |
| Hard reserve intact | reserve untouched | Yes/No (target Yes) | Binary |
| Dead air events | gaps > 3 s with no audio/visual | 0 | Stream/recording review |
| Standby acknowledgement rate | acks / standbys issued | 100% | Comms recording |

---

## 2. AV/IT Signal Flow

### 2.1 Definition

Signal flow is the deterministic, documented path of every video and audio-embedded-in-video signal from source to destination, including every format conversion, scaling, and distribution point, with a measured latency budget and a defined failover path at each stage. "Deterministic" is the operative word: a signal path that renegotiates itself (EDID, HDCP) at an unpredictable moment is not commissioned, regardless of whether it currently works.

### 2.2 Equipment Stack

| Category | Representative Devices | Role in Chain |
|----------|----------------------|---------------|
| Production switcher | Blackmagic ATEM 2 M/E, Ross Carbonite, Barco E2/E3 | Program build, M/E, keying |
| Presentation scaler | Barco ScreenPro, Analog Way Aquilon, Roland V-800HD | Per-input scaling, seamless switch |
| Format converter | Blackmagic Mini Converter, AJA ROI / Hi5 / Ki Pro | HDMI↔SDI, ROI scaling |
| EDID manager | Gefen EDID Detective, Lightware EDID Manager | Force fixed source resolution |
| Distribution amp | Kramer VM-4H2, AJA HD5DA (SDI) | 1→N fan-out, reclocking |
| Matrix router | Blackmagic Videohub 40×40, Lightware MX2 | Any-to-any repatch without recabling |
| Extender | HDBaseT (Crestron DM), fiber (Lightware, Gefen) | Runs > 30 m |
| Media server | Playback Pro, QLab, Resolume, disguise | Content playback, IMAG blend |
| IP transport | NDI (full / HX), SDVoE, ST 2110 | Networked contribution |
| Test / measurement | Leader LV5600, Blackmagic SmartScope, pattern gen | Signal QC, WFM/vectorscope |
| Confidence displays | 1080p panels, Decimator MD-HX | Presenter and operator monitoring |

### 2.3 Reference Signal Flow — Dual-Redundant Presentation Path

```
 PRESENTER LAPTOP A ──HDMI──┐
 (forced 1080p59.94)        │
                            ▼
                    ┌───────────────┐
                    │ EDID MANAGER  │  Locks sink EDID → laptop never renegotiates
                    └───────┬───────┘
                            ▼
                    ┌───────────────┐
                    │ HDMI→SDI CONV │  Blackmagic Mini Converter, 3G-SDI out
                    └───────┬───────┘
                            ▼
                    ┌───────────────┐
                    │  SDI DA 1→4   │  Reclocking distribution amp
                    └─┬───┬───┬───┬─┘
          ┌───────────┘   │   │   └────────────────┐
          ▼               ▼   ▼                    ▼
   ┌────────────┐  ┌────────────┐          ┌─────────────┐
   │ SWITCHER A │  │ SWITCHER B │          │ MULTIVIEWER │
   │  (PRIMARY) │  │  (BACKUP)  │          │  (operator) │
   └──────┬─────┘  └──────┬─────┘          └─────────────┘
          │  PGM A        │  PGM B
          └───────┬───────┘
                  ▼
          ┌───────────────┐
          │ A/B SWITCH or │  Manual clean-switch fallback point
          │ MATRIX ROUTER │  ← single physical action = full switcher failover
          └───┬───┬───┬───┘
              │   │   └──────────────────┐
              ▼   ▼                      ▼
   ┌──────────────────┐        ┌──────────────────┐
   │ LED PROCESSOR /  │        │ CONFIDENCE +     │
   │ PROJECTOR (IMAG) │        │ STREAM ENCODER   │
   └──────────────────┘        └──────────────────┘
```

### 2.4 HDMI vs SDI Selection

| Property | HDMI | 3G-SDI | Operational Consequence |
|----------|------|--------|------------------------|
| Connector | Type A, friction-fit | BNC, locking | HDMI walks out under cable tug; SDI does not |
| Passive run limit | ~5 m reliable, 10–15 m marginal @1080p | ~100–120 m @ 3G, ~200 m @ HD-SDI | HDMI needs extension almost immediately |
| Long-haul method | Active optical, HDBaseT (100 m @1080p) | Coax direct, or fiber for > 150 m | SDI simpler infra past 15 m |
| EDID | Required handshake, sink-dependent | None | HDMI can fail on repatch; SDI cannot |
| HDCP | Enforced; blanks non-compliant paths | Not present in baseband SDI | HDMI content protection is a live-show risk |
| Embedded audio | Up to 8 ch (LPCM) | 16 ch (3G), 4 groups of 4 | Both adequate; SDI de-embed more robust |
| Reclocking / DA | Rare in cheap kit | Standard on SDI DAs | SDI fan-out is signal-safe |
| Hot-plug behaviour | Re-handshake, 1–5 s black | Instant relock (< 1 frame) | SDI survives repatch live |

**Standing rule:** convert every presenter HDMI source to SDI at the earliest practical point, then keep the entire infrastructure in SDI. HDMI exists only in the first and last metre of the chain.

**HDCP note:** if a presenter attempts to play protected content (streaming service, protected Blu-ray), the compliant path is a licensed HDCP-compliant chain end-to-end, or a client-supplied non-protected copy of the asset. Do not deploy HDCP-stripping devices — that is a circumvention of access control and carries legal exposure under the DMCA and equivalent statutes. Resolve it in pre-production by obtaining an unprotected file.

### 2.5 Confidence Monitor Feed Design

| Feed Type | Content | Fed To | Rationale |
|-----------|---------|--------|-----------|
| Presenter confidence | Current slide, full-screen, no overlays | Downstage floor monitors | Presenter must not see their own IMAG (self-distraction) |
| Presenter + timer | Slide with countdown overlay | Downstage monitor / lectern | Enables self-paced timing (§1.6) |
| Presenter notes | PowerPoint Presenter View (next slide + notes) | Lectern display only | Never on any audience-visible output |
| Clean PGM | Program without lower-thirds/bug | Stream, recording | Reusable asset, no burned-in graphics |
| Dirty PGM | Program with all keys | IMAG screens, multiview | What the room sees |
| Multiviewer | All sources + PGM + PVW | Operator positions | Fault detection at a glance |

**Physical placement:** presenter confidence monitors at 2 downstage positions (SL and SR of centre), tilted 15–20° up, top edge below sight line to audience so the presenter's head stays up. Timer occupies the lower third at ≥ 15% of screen height to be legible at 3–4 m.

**Critical isolation rule:** the Presenter View output must be on a physically separate output from any switcher input. The recurring failure is a presenter laptop mirroring rather than extending its display, putting notes on the main screen. Verify extend-mode with each laptop during rehearsal, and keep a hold slide armed on the switcher for instant cover.

### 2.6 Latency Budget

At 1080p59.94, one frame = **16.68 ms**. Latency accumulates per device and is not recoverable downstream — only compensable by delaying audio.

**Typical IMAG chain (camera → LED wall):**

| Stage | Device Class | Latency | Frames | Cumulative |
|-------|-------------|---------|--------|-----------|
| Camera acquisition | Broadcast/box camera | 8–17 ms | 0.5–1 | 17 ms |
| SDI transport (100 m coax) | Passive | < 0.001 ms | ~0 | 17 ms |
| Production switcher | ATEM / Carbonite, cut | 8–17 ms | 0.5–1 | 34 ms |
| Scaler / presentation processor | Analog Way, Barco | 17–33 ms | 1–2 | 67 ms |
| LED processor | Novastar, Brompton | 17–33 ms | 1–2 | 100 ms |
| LED panel driver | Panel electronics | ~0–17 ms | 0–1 | 100–117 ms |
| **Total video path** | | **50–117 ms** | **3–7** | |

**Alternative sinks:**

| Sink | Added Latency | Notes |
|------|--------------|-------|
| Projector (low-latency / gaming mode) | 17–33 ms | Verify mode is enabled; defaults are slower |
| Projector (default processing) | 50–100 ms | Frame interpolation must be disabled |
| Stream encoder (H.264, 2 s buffer) | 2000–6000 ms | Irrelevant to in-room sync |
| NDI full-bandwidth | 17–33 ms + network | Acceptable for in-room contribution |
| NDI HX (compressed) | 100–200 ms | Do not use in IMAG paths |
| SDVoE | < 1 line (~10 µs) | Effectively zero; use for long-haul IP |

**Audio-to-video sync.** Audio arrives at the audience far earlier than video unless delayed. Two effects combine:

```
Video path latency:        50-117 ms  (electronic, per table above)
Audio electronic latency:  ~2-5 ms    (console DSP + amp DSP)
Acoustic propagation:      2.9 ms/m   (343 m/s @ 20 °C)

Audience at 20 m from PA:  20 × 2.9 = 58 ms acoustic
Net offset at 20 m row:    (58 + 4) − 100 = −38 ms  → audio LEADS video by 38 ms
```

**Tolerance targets (EBU R37 operational window):** audio should not lead video by more than **40 ms**, and should not lag by more than **60 ms**. ITU-R BT.1359 detectability thresholds are wider (~45 ms lead / ~125 ms lag) but R37 is the working standard for production.

| Audience Distance | Acoustic Delay | Video Latency 100 ms | Net Offset | Within R37? | Action |
|-------------------|---------------|---------------------|-----------|-------------|--------|
| 5 m (front) | 14 ms | 100 ms | audio leads 82 ms | No | Delay audio 45–60 ms |
| 15 m (mid) | 43 ms | 100 ms | audio leads 53 ms | No | Delay audio 20–40 ms |
| 20 m | 58 ms | 100 ms | audio leads 38 ms | Marginal | Optional trim |
| 30 m (rear) | 87 ms | 100 ms | audio leads 9 ms | Yes | None |

**Practical resolution:** measure total video latency at commissioning with a clapper test against the recording, then apply a single master audio delay tuned for the **mid-house** reference position (typically 40–60% of room depth). Front rows will retain a small audio lead; this is the accepted compromise since no single delay satisfies all rows. Minimising video latency (fewer scalers, low-latency projector modes) is more effective than compensating a bloated chain.

### 2.7 Backup Switcher Topologies

| Topology | Cost | Failover Time | Failover Trigger | Best For |
|----------|------|--------------|------------------|----------|
| Cold spare (boxed) | Low | 15–40 min | Manual rebuild | Low-stakes internal events |
| Warm spare (racked, powered, unprogrammed) | Medium | 5–15 min | Manual patch + load | Standard corporate |
| Hot standby (mirrored program, A/B out) | High | < 1 s | One A/B switch action | Keynotes, broadcast, high-value |
| Dual redundant frames (auto-changeover) | Very high | < 1 frame | Automatic on signal loss | Broadcast, live TV |

**Hot standby build requirements:**

1. Both switchers receive **identical inputs** via reclocking DAs — never daisy-chain through the primary.
2. Both switchers run the **same programmed macros and same scene state**. The backup operator shadows every take.
3. Both program outputs land on a **clean A/B switch or matrix router crosspoint** immediately upstream of the display chain.
4. Failover is **one physical action** at a position the operator can reach without standing up.
5. Power: primary and backup on **separate UPS units on separate circuits**.
6. The backup path is tested under load during rehearsal, not assumed.

**Auto-changeover caveat:** automatic signal-loss detection catches total loss (no sync) but will not catch a corrupted-but-present signal — wrong source live, frozen frame, or misconfigured key. Those require human detection. Never rely solely on auto-changeover.

### 2.8 Build & Commissioning Workflow

| Phase | Step | Verification Gate |
|-------|------|-------------------|
| 1. Plan | Produce signal flow diagram with every device and cable ID | Diagram peer-reviewed before load-in |
| 2. Format lock | Set show format (1080p59.94 or 1080p50) on every device | No device in auto-detect |
| 3. Power | Distribute across circuits; UPS on switchers, servers, converters | Draw measured, ≤ 80% of circuit rating |
| 4. Cable | Label both ends of every cable with matching ID | 100% labelled |
| 5. Sources | Force each laptop via EDID manager; disable sleep/screensaver/notifications | Each laptop tested at native show res |
| 6. Signal QC | Pattern generator through full chain; WFM check levels, legal gamut | Legal 0–100 IRE, no illegal excursions |
| 7. Latency | Clapper/timecode test; measure total path latency | Value recorded; audio delay set |
| 8. Redundancy | Fail each single point deliberately; time the recovery | Meets RTO in §6.8 |
| 9. Confidence | Verify presenter view isolation on every laptop | No notes on PGM in any state |
| 10. Freeze | Lock configuration; snapshot switcher/scaler state to file + USB | Config backed up in 2 locations |

### 2.9 Common Failure Modes

| Symptom | Root Cause | Diagnostic | Fix / Prevention |
|---------|-----------|-----------|------------------|
| Black screen on laptop swap | EDID renegotiation on hot-plug | Check sink EDID at converter input | Insert EDID manager; force fixed EDID |
| Intermittent sparkles / dropouts | SDI cable length past 3G budget, or damaged coax | WFM eye pattern; swap cable | Reclock at midpoint, or fiber past 120 m |
| Image blanks only on protected content | HDCP path non-compliant | Test with unprotected clip | Obtain unprotected asset in pre-pro |
| Presenter notes on main screen | Laptop mirroring instead of extending | Check display arrangement | Force extend; hold slide armed |
| Wrong aspect / letterbox | Source not at show resolution; scaler set to stretch | Compare source res to show format | Force source res; set scaler to preserve AR |
| Audio present, video frozen | Scaler or LED processor locked up | Check processor status LEDs | Power-cycle processor; failover to backup path |
| Lip sync visibly wrong | Uncompensated video latency | Clapper test vs recording | Apply master audio delay (§2.6) |
| HDBaseT link drops randomly | Cat cable marginal, or PoH negotiation | Link LED, cable certifier | Re-terminate; use certified Cat6a; keep < 90 m |
| Colour shift between sources | Mixed RGB/YCbCr and level ranges | WFM on each input | Force one colour space; match levels |
| Multiviewer shows source, PGM black | Wrong crosspoint or key active over source | Check switcher key layers | Clear keys; verify router crosspoint |

### 2.10 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Unplanned black frames on PGM | 0 | Recording frame analysis |
| Total video path latency | ≤ 3 frames (50 ms) | Clapper/timecode test |
| Audio-video sync at mid-house | Within R37 window (−40/+60 ms) | Measured, then delay-compensated |
| Switcher failover time (hot standby) | < 1 s | Timed rehearsal drill |
| Cables labelled both ends | 100% | Physical audit |
| Devices in auto-detect mode | 0 | Configuration audit |
| Signal legality | 0–100 IRE, no illegal gamut | WFM/vectorscope at commissioning |
| Config backup locations | ≥ 2 | Verified restore test |
| Source hot-plug recovery | < 2 s | Deliberate unplug drill |

---

## 3. FOH Management

### 3.1 Definition

Front of House management is the operation of the audience-facing audio system: converting source levels into a mix that is intelligible, at a safe and appropriate level, with sufficient gain margin before feedback, while simultaneously servicing performer monitoring needs. The FOH engineer (A1) owns gain structure end-to-end — from preamp to amplifier input — because gain errors anywhere in that chain cannot be corrected downstream without cost in noise or headroom.

### 3.2 Equipment Stack

| Category | Devices | Function |
|----------|---------|----------|
| Console | Behringer WING, DiGiCo SD-series, Yamaha CL/QL, Allen & Heath dLive | Mix engine, DCA/bus structure, scenes |
| Stagebox / I/O | AES50 (WING), DiGiCo SD-Rack, Dante I/O | Remote preamps at stage |
| Measurement | Rational Acoustics Smaart v9, Open Sound Meter | Transfer function, RTA, delay finding |
| SPL logging | NTi XL2, 10EaZy, Class 1 SLM | Compliance logging (LAeq, LCpeak) |
| Remote control | WING-Co / OSC tablet, DiGiCo iPad app | Walk-the-room tuning, monitor mixing at stage |
| System processing | Lake LM44, Galileo Galan, amp-integrated DSP | Crossover, delay, room EQ, limiting |
| Reference | Calibrated headphones, known-source playback | Sanity check on mix translation |
| Comms | Talkback to SM/caller | Cue coordination |

### 3.3 Gain Staging Workflow

**Digital reference alignment.** In a typical broadcast/production-aligned digital console, **0 dBFS ≈ +24 dBu** at the analogue output, placing the nominal 0 dBu operating point at −24 dBFS. Verify the actual figure for the specific console against its manual rather than assuming — the alignment varies by manufacturer, and it determines every target below.

| Reference Point | dBFS | dBu (at +24 dBu = 0 dBFS) | Meaning |
|-----------------|------|---------------------------|---------|
| Digital clip | 0 | +24 | Hard ceiling; inter-sample peaks can exceed |
| Peak target (speech) | −12 to −10 | +12 to +14 | Working peak ceiling |
| Nominal average (speech) | −20 to −18 | +4 to +6 | Where the meter should sit |
| Analogue nominal | −24 | 0 | Traditional 0 VU equivalent |
| Noise floor (good preamp) | −100 to −90 | −76 to −66 | Determines usable dynamic range |

**Step-by-step, per channel:**

1. **Set physical position first.** Mic placement and capsule choice dominate everything downstream. Do not compensate placement errors with gain.
2. **Engage pad only if required.** Pad if the source drives the preamp into clip at minimum gain (typical for kick, snare, close-miked brass). A pad costs noise floor — do not use it prophylactically.
3. **Apply HPF before setting gain.** Removing sub-100 Hz stage rumble, HVAC, and handling noise changes the peak level materially. Setting gain first, then adding HPF, leaves the channel under-gained. Corner frequencies in §4.5.
4. **Set preamp gain to target.** Have the source produce its loudest realistic output — a speaker's most emphatic sentence, not a mic tap. Aim for **−18 dBFS average, −12 dBFS peaks**. This yields ~12 dB of transient headroom.
5. **Verify with the real source, not a proxy.** A soundcheck voice at conversational level under-reads a keynote delivery by 6–10 dB.
6. **Set dynamics after gain, never as a gain substitute.** Gate threshold typically −55 to −45 dBFS for lecterns; compression 2:1 to 3:1 with 3–6 dB gain reduction on peaks for speech.
7. **Check unity through every bus.** Channel → DCA → bus → matrix → output. Each stage at unity unless deliberately trimmed. Cumulative small boosts across four stages is how a system ends up 12 dB hot with no single obvious culprit.
8. **Confirm amplifier input sensitivity.** System DSP output should drive the amp to full power at console output peak, no earlier. If the amp clips before the console meters read −6 dBFS, the amp sensitivity is set too hot and every downstream limiter is being defeated.

**Gain structure diagram:**

```
 MIC ──► PAD ──► PREAMP ──► HPF ──► GATE ──► EQ ──► COMP ──► FADER ──► DCA ──► BUS ──► MATRIX ──► SYS DSP ──► AMP ──► PA
         │        │          │       │              │         │        │       │       │           │
      only if   set to    BEFORE   -55..-45      3-6 dB    unity    unity   unity   unity     sensitivity
       clipping  -18 dBFS   gain     dBFS          GR       ref      ref     ref     ref       matched
                  avg      staging                                                          to console peak
```

### 3.4 Monitor Mix Workflow

| Aspect | Wedges | IEM |
|--------|--------|-----|
| Feedback risk | High — open mic in front of loudspeaker | None from the monitor path itself |
| Available FOH gain | Reduced (wedge energy hits mics) | Unaffected |
| Stage SPL | 95–105 dB(A) at performer | 75–85 dB(A) typical |
| Latency tolerance | Acoustic, effectively zero | **< 2 ms** total; > 5 ms causes comb filtering with bone conduction |
| Mix count | Limited by wedge/amp count | One per performer, stereo possible |
| Ambience | Natural room bleed | Must be supplied via ambient mics |
| Failure mode | Feedback, ringing | Silence in ear (more startling), pack battery death |

**Workflow (mixed wedge/IEM corporate-band scenario):**

1. Build monitor mixes **before** the FOH mix. Performers cannot deliver a usable soundcheck through a bad monitor mix.
2. Set all monitor sends **pre-fader** so FOH fader moves do not alter stage mixes. Confirm the console's default — post-fader monitor sends are a common and disruptive misconfiguration.
3. Work one mix at a time, in the performer's position, using the tablet remote at stage. Mixing wedges from FOH is guesswork.
4. Start each mix with the performer's own primary source, then add only what they need for pitch and timing reference. Additive-only: never build a full mix and subtract.
5. **Ring out wedges** before the band plays: raise each wedge send until feedback begins, note the frequency on RTA, apply a narrow notch (Q 20–30, −6 to −12 dB), repeat for 2–3 modes maximum. Beyond 3 notches, the wedge is misplaced or the mic pattern is wrong — fix the physical cause. Then reduce the send by 6 dB to restore margin.
6. For IEM, supply **ambient mics** (a spaced pair at the downstage lip, or audience-facing) at low level. Without ambience, performers over-sing because they cannot hear the room.
7. Verify IEM latency: keep IEM-bound signal on the native console path. Do not route externally-processed returns (USB/network plugin paths above 2 ms) into IEM mixes.
8. Set a hard limiter on every IEM output — typically −6 to −10 dBFS ceiling — to protect hearing against patch errors and cable-drop transients. This is non-optional.
9. Log each mix to a scene, and keep a "safe" monitor scene that recalls known-good levels.

### 3.5 DCA Grouping Strategies

**DCA vs audio subgroup** — these are not interchangeable:

| Property | DCA (VCA) | Audio Subgroup |
|----------|-----------|----------------|
| Signal path | Control only; audio stays on channel path | Audio is summed into the group bus |
| Bus processing | Cannot process the sum | Can insert comp/EQ on the sum |
| Latency added | None | One bus stage |
| Channel can belong to | Multiple DCAs simultaneously | Typically one group (routing) |
| Use for | Fast level control of related channels | Bus compression, stem outputs |

Use DCAs for live level control; use subgroups only when you need to process or output a sum.

**Corporate panel (8 mics + playback):**

| DCA | Contents | Purpose |
|-----|----------|---------|
| 1 | Host handheld | Independent — the host is the recovery tool |
| 2 | Lectern mics (2) | Keynote position |
| 3 | Panel mics (4) | Single move to open/close the panel |
| 4 | Lavaliers (spares/roving) | Isolated so an open lav never rides with panel |
| 5 | Playback / VT audio | Video and music beds |
| 6 | Audience Q&A mics (2) | Killed by default, opened only during Q&A |

**Band / show (32+ inputs):**

| DCA | Contents | Notes |
|-----|----------|-------|
| 1 | Lead vocal | Always its own DCA; most frequent moves |
| 2 | Backing vocals | Grouped for blend |
| 3 | Drums (kit + overheads) | Includes room mics if used |
| 4 | Bass | Isolated for low-end balance |
| 5 | Guitars | Electric + acoustic |
| 6 | Keys / tracks | Includes any playback stems |
| 7 | Horns / strings | Section control |
| 8 | FX returns | Reverb/delay returns — critical for a fast dry-out |

**Rules of application:**

1. The most-adjusted source gets its own dedicated DCA. For speech events that is the host; for music, the lead vocal.
2. Any channel that could cause a crisis (open mic, audience mic) sits on a DCA the engineer can reach without looking.
3. **Spill control:** verify whether DCA fader moves affect monitor sends. Pre-fader monitor sends are immune, which is the desired behaviour.
4. Assign FX returns to a DCA so the mix can be made dry instantly — essential for a speech interruption during a music segment.
5. Keep DCA layout identical across all shows in a series. Muscle memory is a reliability feature.
6. Mark critical DCAs as scene-safe so a scene recall cannot silently reposition them.

### 3.6 SPL Targets & Exposure Management

| Event Type | Target LAeq (program) | Peak Ceiling LCpeak | Notes |
|-----------|----------------------|--------------------|-------|
| Corporate speech | 75–82 dB(A) | < 100 dB(C) | Intelligibility, not impact |
| Corporate with AV/music stings | 82–88 dB(A) | < 105 dB(C) | Music beds above speech level |
| Awards / gala with band | 90–96 dB(A) | < 110 dB(C) | Check venue contractual limit |
| Concert (contemporary) | 96–102 dB(A) | < 115 dB(C) | Venue/regulatory limit governs |

**Occupational exposure references** (crew-facing, not audience):

| Standard | Criterion Level | Exchange Rate | 8 h Limit | Implication for Crew |
|----------|----------------|---------------|-----------|---------------------|
| NIOSH (recommended) | 85 dB(A) | 3 dB | 85 dB(A) | 88 dB → 4 h; 91 dB → 2 h |
| OSHA (US enforceable PEL) | 90 dB(A) | 5 dB | 90 dB(A) | 95 dB → 4 h; 100 dB → 2 h |
| EU Directive 2003/10/EC | 80 / 85 / 87 dB(A) action & limit values | 3 dB | 87 dB(A) exposure limit | Hearing protection mandatory above upper action value |

Log LAeq continuously with a Class 1 meter at the mix position for any event with a contractual or regulatory limit; keep the log as evidence. Crew working multi-day shows above 85 dB(A) need hearing protection available and a documented exposure position.

### 3.7 Common Failure Modes

| Symptom | Root Cause | Diagnostic | Fix |
|---------|-----------|-----------|-----|
| Hiss audible in quiet passages | Under-gained preamp, compensated with downstream boost | Compare preamp meter to fader position | Re-gain at preamp; return downstream to unity |
| Distortion that persists with fader down | Preamp clipping (pre-fader) | Channel input meter, not output | Reduce preamp gain / engage pad |
| Feedback at low fader levels | Insufficient GBF: mic pattern, placement, or NOM | RTA to identify ring frequency; count open mics | Reduce NOM, reposition, correct pattern (§4) |
| Level jumps between speakers | Per-channel gain not matched | Compare average meter reading per source | Match all speech channels to −18 dBFS avg |
| Monitor mixes shift when FOH moves | Post-fader monitor sends | Check send tap point | Set sends pre-fader |
| Mix sounds thin in the room, fine in phones | Mixing on headphones; no room verification | Walk the room | Tune from mid-house position |
| Amp clips before console peaks | Amp sensitivity too hot | Compare console output to amp clip LED | Reduce amp input sensitivity |
| Scene recall changes critical levels | Channels not scene-safe | Recall a scene during rehearsal | Set scene-safe on hosts/DCAs |
| Comb filtering on a source | Two mics on one source, or delay mismatch | Solo each mic; polarity check | Mute one, or time-align |
| Sub-bass muddiness | No HPF on speech channels | Check HPF engagement per channel | Engage HPF per §4.5 |

### 3.8 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Gain before feedback margin | ≥ 6 dB below ring point at show level | Ring-out test, then reduce |
| Speech channel consistency | All within ±2 dB average | Console meters across sources |
| Program LAeq vs target | Within ±2 dB | Class 1 SLM log at mix position |
| LCpeak exceedances | 0 above ceiling | SLM peak-hold log |
| Feedback events during show | 0 | Recording review |
| Preamp clip events | 0 | Console clip-hold indicators |
| Monitor mix complaints post-soundcheck | 0 | Performer confirmation |
| IEM output limiter engaged | 100% of IEM buses | Configuration audit |
| STI / intelligibility (speech events) | STI ≥ 0.60 (good) | Smaart or dedicated STIPA meter |

---

## 4. Microphone Selection & Spectral Routing

### 4.1 Definition, and a Correction to the Common Heuristic

Microphone spectral routing is the practice of assigning capsules, polar patterns, positions, and per-channel filter settings so that (a) each source is captured with adequate isolation and gain margin, and (b) the combined channels occupy the spectrum without masking one another.

**The frequency-first heuristic is wrong.** The brief for this section proposed "low-frequency sources on omnidirectional, high-frequency sources on cardioid." That rule does not hold and will actively harm a live system if applied. Polar pattern is selected on the basis of **isolation requirement, gain-before-feedback requirement, and source-to-mic angular stability** — not on the source's frequency content. Counter-examples from standard practice:

| Source | Dominant Frequency Range | Pattern Actually Used | Why |
|--------|-------------------------|----------------------|-----|
| Kick drum | 40–120 Hz (low) | Cardioid / supercardioid | Maximum isolation from snare and bass rig |
| Bass cabinet | 40–250 Hz (low) | Cardioid dynamic | Isolation on a loud stage |
| Cymbals / overheads | 3–16 kHz (high) | Often omnidirectional or cardioid pair | Omni gives flatter, more natural response and no proximity effect |
| Orchestral room / ambience | Full range | Omnidirectional | Natural tone, consistent off-axis response |
| Lavalier on a speaker | 100 Hz–8 kHz (speech) | Omnidirectional | Head turns constantly; omni keeps tone stable off-axis |
| Handheld vocal, loud stage | 100 Hz–12 kHz (speech) | Supercardioid / cardioid | Feedback rejection is the governing constraint |

Note that lavalier and handheld cover essentially the same frequency band yet take opposite patterns. The deciding factor is angular stability versus feedback margin, which is what the frequency rule cannot express.

**What is genuinely frequency-domain work in routing:** spectral zone allocation between simultaneous sources, HPF corner selection per source type, proximity-effect management, and off-axis high-frequency behaviour. Those are covered in §4.4–4.6.

### 4.2 Polar Pattern Reference

| Pattern | Directivity Factor (DF) | Distance Factor | Rear Rejection | Null Angle | GBF vs Omni | Accept. Angle (−3 dB) |
|---------|------------------------|-----------------|----------------|-----------|-------------|----------------------|
| Omnidirectional | 1.0 | 1.0 | 0 dB | none | 0 dB (reference) | 360° |
| Subcardioid | ~1.6 | ~1.3 | ~10 dB | none | ~+2 dB | ~170° |
| Cardioid | 3.0 | 1.7 | ~15–25 dB | 180° | ~+4.8 dB | ~131° |
| Supercardioid | 3.7 | 1.9 | ~12 dB (rear lobe) | 126° | ~+5.7 dB | ~115° |
| Hypercardioid | 4.0 | 2.0 | ~6 dB (rear lobe) | 110° | ~+6.0 dB | ~105° |
| Bidirectional (fig-8) | 3.0 | 1.7 | 0 dB (equal rear) | 90° | ~+4.8 dB | ~90° front + 90° rear |
| Shotgun (line/interference) | 6–12+ | 2.4–3.5 | high, frequency-dependent | multiple lobes | ~+8–11 dB | ~40–60° |

**Distance factor** is the multiple of working distance at which a directional mic achieves the same direct-to-reverberant ratio as an omni. A cardioid at 1.7 m matches an omni at 1.0 m.

**Null placement is the practical value of a directional pattern.** Aim the null at the dominant unwanted source:

```
CARDIOID                      SUPERCARDIOID                 HYPERCARDIOID
null at 180°                  nulls at ~126°                nulls at ~110°
                                                            
      SOURCE                        SOURCE                       SOURCE
        ▲                             ▲                            ▲
        │                             │                            │
    ┌───┴───┐                     ┌───┴───┐                    ┌───┴───┐
    │  MIC  │                     │  MIC  │                    │  MIC  │
    └───┬───┘                     └─┬───┬─┘                    └─┬───┬─┘
        │                     null ↙     ↘ null           null ↙     ↘ null
        ▼ null                  (126°)   (126°)             (110°)   (110°)
     WEDGE                       WEDGE   WEDGE               WEDGE   WEDGE
  directly behind            two wedges at ±126°        two wedges at ±110°
```

Placement consequence: a cardioid vocal mic wants **one** wedge directly behind it. A supercardioid wants **two** wedges at roughly ±126°, and will feed back from a wedge placed directly behind it because supercardioid has a rear lobe. Getting this wrong is one of the most common causes of unexplained monitor feedback.

### 4.3 Proximity Effect and Off-Axis Behaviour

Pressure-gradient (directional) microphones exhibit **proximity effect**: low-frequency output rises as the source approaches. Omnidirectional pressure microphones do not.

| Working Distance | Cardioid LF Boost (~100 Hz) | Practical Result |
|-----------------|----------------------------|------------------|
| 25 mm (1 in, lips-on) | +6 to +12 dB | Heavy, boomy; requires HPF/EQ compensation |
| 50 mm (2 in) | +4 to +8 dB | Warm, usable for most vocals |
| 150 mm (6 in) | +2 to +4 dB | Near-neutral |
| 300 mm (12 in) | ~+1 dB | Neutral |
| 600 mm (24 in) | ~0 dB | Reference / no effect |

Two operational consequences: a presenter whose distance varies by 25–150 mm produces a **6–10 dB swing in low-frequency content**, which no static EQ can track — this is why an HPF plus modest compression is standard on handhelds. And an inexperienced presenter holding a mic at chest height loses both level and the low-frequency support, sounding thin and distant.

**Off-axis high-frequency behaviour.** All directional patterns become progressively less directional at low frequencies and more directional (beaming) at high frequencies. A speaker who turns 45° off-axis loses primarily **high frequency**, not level — the result is a dull, unintelligible sound while the meter barely moves. This is the actual reason lavaliers are omnidirectional: an omni's off-axis response is far more consistent, so head rotation changes tone much less.

| Off-Axis Angle | Cardioid HF Loss (4–10 kHz) | Cardioid Level Loss (broadband) | Intelligibility Impact |
|---------------|----------------------------|-------------------------------|----------------------|
| 0° | 0 dB | 0 dB | Reference |
| 30° | −2 to −4 dB | −1 dB | Slight dulling |
| 45° | −4 to −8 dB | −2 to −3 dB | Noticeable consonant loss |
| 90° | −10 to −20 dB | −6 dB | Severe; consonants gone |
| 180° | −20 dB+ | −15 to −25 dB | Unusable |

### 4.4 Selection Decision Matrix

Select on the governing constraint, in this priority order: feedback margin → isolation → angular stability → tonal preference.

| Scenario | Governing Constraint | Pattern | Typical Model | Rationale |
|----------|---------------------|---------|---------------|-----------|
| Handheld vocal, wedges on stage | Feedback margin | Supercardioid | Shure Beta 58A, Sennheiser e935 | Max GBF; place wedges at ±126° |
| Handheld host, IEM-only stage | Isolation, moderate | Cardioid | Shure SM58, Beta 87A | No wedges; cardioid tone preferred |
| Lectern / podium speech | Rejection of PA + angular stability | Cardioid or supercardioid gooseneck | Shure MX412, DPA 4018 | Null aimed at nearest PA element |
| Lavalier on presenter | Angular stability (head turns) | Omnidirectional | Countryman B3, DPA 4060 | Consistent tone off-axis; accept lower GBF |
| Headworn on presenter | Angular stability + max gain | Omni or cardioid headworn | DPA 4066, Shure TH53 | Fixed distance solves proximity + GBF |
| Panel discussion, 4+ open mics | NOM management | Cardioid + automixer | MX412 / boundary + gain sharing | Reduce effective NOM (§4.6) |
| Audience Q&A, roving | Feedback in unpredictable positions | Supercardioid/hypercardioid | Beta 58A, EV RE3 | Operator points null at nearest speaker |
| Choir / ensemble, distant | Direct-to-reverberant ratio | Cardioid or hypercardioid, hung | Audix M1280, DPA 4011 | Distance factor extends usable reach |
| Room / ambience for IEM | Natural, consistent capture | Omnidirectional pair | DPA 4006, Earthworks M30 | Flat LF, no proximity effect |
| Kick drum | Isolation on loud stage | Cardioid / supercardioid | Beta 91A, AKG D112 | Low-frequency source, still directional |
| Drum overheads | Natural HF, phase coherence | Omni pair or cardioid pair | KM183 (omni), KM184 (cardioid) | High-frequency source, often omni |

### 4.5 HPF Corner Frequency Reference

The high-pass filter is the primary frequency-domain tool at input stage. Apply before gain staging (§3.3 step 3).

| Source | HPF Corner | Slope | Rationale |
|--------|-----------|-------|-----------|
| Lavalier (speech) | 100–120 Hz | 12–18 dB/oct | Clothing rustle, HVAC, footfall rumble |
| Headworn (speech) | 100–120 Hz | 12–18 dB/oct | Same, plus breath-blast reduction |
| Handheld vocal (speech) | 100–120 Hz | 12–18 dB/oct | Proximity-effect and handling-noise control |
| Lectern gooseneck | 100–150 Hz | 18–24 dB/oct | Structure-borne rumble through lectern body |
| Handheld vocal (singing, male) | 70–90 Hz | 12 dB/oct | Preserve fundamentals (~85 Hz+) |
| Handheld vocal (singing, female) | 90–110 Hz | 12 dB/oct | Fundamentals ~165 Hz+ |
| Acoustic guitar (DI/mic) | 70–80 Hz | 12 dB/oct | Below body resonance |
| Electric guitar | 80–100 Hz | 12 dB/oct | Leave space for bass |
| Piano | 30–40 Hz | 12 dB/oct | Preserve low fundamentals |
| Snare | 100–150 Hz | 12–18 dB/oct | Reject kick bleed |
| Overheads / cymbals | 200–400 Hz | 12–18 dB/oct | Reject kick and tom bleed |
| Kick / bass | Off, or 30 Hz | 12 dB/oct | Protect sub drivers from DC/subsonic only |
| Audience / ambience mics | 120–200 Hz | 18 dB/oct | Reject HVAC and low-frequency room noise |

**Non-negotiable rule:** every speech channel gets an HPF. A lectern mic with no HPF, in a room with typical HVAC, wastes 6–10 dB of usable headroom on inaudible rumble and reduces gain before feedback for no benefit.

### 4.6 NOM Management and Spectral Zone Allocation

**Number of Open Microphones (NOM) law:** each doubling of open mics costs approximately **3 dB** of gain before feedback.

| Open Mics | GBF Penalty | Cumulative Effect |
|-----------|------------|-------------------|
| 1 | 0 dB | Reference |
| 2 | −3 dB | |
| 4 | −6 dB | Panel discussion territory |
| 8 | −9 dB | Full panel + Q&A; unmanageable without automix |
| 16 | −12 dB | Requires gain-sharing automix |

A supercardioid's +5.7 dB advantage over omni is entirely consumed by going from 1 to 4 open mics. **NOM discipline outranks pattern selection.**

**Gain-sharing automix workflow:**

1. Assign all continuously-open speech mics (panel, lectern, roundtable) to one automix group.
2. Use gain-sharing (Dugan-style) rather than gating — gating chops consonant onsets and produces audible pumping on overlapping speech.
3. Set the group weight so each mic's contribution scales with its share of total energy; the sum of gains stays constant, holding effective NOM near 1.
4. Exclude from the automix group: host handheld, music playback, any performance mic. Automix on a music channel produces unpredictable level.
5. Verify with all participants speaking simultaneously, then with one speaking and three silent — the silent three should attenuate measurably.
6. Retain manual override: the engineer must be able to force a channel open or closed regardless of automix state.

**Spectral zone allocation** — the legitimate frequency-domain routing task. With multiple simultaneous speech sources, masking occurs when two voices compete in the same critical band. Allocate deliberately:

| Zone | Range | Contains | Live Handling |
|------|-------|----------|---------------|
| Sub / rumble | < 100 Hz | HVAC, footfall, handling | HPF out on all speech |
| Low fundamental | 100–250 Hz | Voice fundamentals (male 85–180, female 165–255 Hz) | Preserve; cut only where muddy (broad −2 to −3 dB @ 200–250 Hz) |
| Low-mid mud | 250–500 Hz | Chest resonance, proximity buildup, boxiness | Most common corrective cut; narrow, per-voice |
| Mid | 500 Hz–2 kHz | Vowel intelligibility, body | Protect. Cuts here make voices thin |
| Presence | 2–5 kHz | Consonant articulation, intelligibility core | Protect; also the primary feedback zone |
| Sibilance | 5–9 kHz | S/T/SH sounds | De-ess per voice, not broadly |
| Air | 9–20 kHz | Openness | Low priority for speech; roll off if noisy |

**Anti-masking procedure for multiple simultaneous voices:** identify each speaker's strongest resonant region during soundcheck via RTA, then apply a narrow complementary cut in that region on the *other* channels. Two male voices with fundamentals near 120 Hz will mask each other; a 2–3 dB cut at 200–250 Hz on the secondary voice restores separation without making either sound processed. Do not solve masking with boosts — boosting reduces headroom and gain before feedback.

### 4.7 Common Failure Modes

| Symptom | Root Cause | Diagnostic | Fix |
|---------|-----------|-----------|-----|
| Supercardioid feeds back from wedge behind it | Rear lobe — null is at ±126°, not 180° | Note feedback source position | Move wedge to ±126°, or switch to cardioid |
| Panel feeds back at moderate level | NOM too high (4–8 open mics) | Count open channels | Gain-sharing automix; close unused mics |
| Speaker sounds dull and distant | Off-axis HF loss from head turn | Watch presenter angle vs mic | Reposition; switch lav to omni; use headworn |
| Presenter level swings 8–10 dB | Variable handheld distance + proximity effect | Watch working distance | HPF + 3:1 compression; coach distance |
| Lavalier sounds boomy on one presenter | Placement under a lapel forming a cavity | Compare to open placement | Reposition; HPF 120 Hz |
| Clothing rustle on lav | Cable not strain-relieved; fabric contact | Listen during movement | Loop cable, tape strain relief, avoid silk/synthetics |
| Two voices unintelligible together | Spectral masking in same critical band | RTA both voices | Complementary narrow cuts (§4.6) |
| Automix pumps on overlapping speech | Gate-based automix, not gain-sharing | Listen to consonant onsets | Switch to gain-sharing algorithm |
| Q&A mic feeds back instantly | Audience member points mic at PA | Observe mic orientation | Supercardioid + operator coaching; DCA killed by default |
| Wireless dropouts | RF coordination / antenna placement | Scan; check RSSI | Coordinate frequencies; diversity antennas in line of sight |

### 4.8 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Gain before feedback margin | ≥ 6 dB at show level | Ring-out then back off |
| Effective NOM with automix active | ≤ 2 | Console automix meter / gain-share display |
| Off-axis tonal consistency (lav) | ≤ 4 dB HF variation across ±45° | Swept measurement or A/B listening |
| Channel-to-channel speech level match | ±2 dB | Console meters |
| HPF engaged on speech channels | 100% | Configuration audit |
| Masking-related complaints | 0 | Client/stream feedback |
| Sibilance excursions | Controlled, no de-esser above 6 dB GR | De-esser metering |
| Wireless dropout events | 0 | Receiver RF/AF log |

---

## 5. Stage Management

### 5.1 Definition

Stage management is the control of everything on and immediately adjacent to the stage: talent readiness and movement, physical cue delivery, equipment handoffs, and the flow of people from arrival to performance to exit. The Stage Manager (SM) is the show caller's physical agent at the stage and, in many corporate structures, is also the caller. The SM owns the space between the green room door and the stage mark.

The SM's authority is procedural, not artistic: the SM does not decide content, but does decide who is standing where and when, and can hold a cue if talent is not in position.

### 5.2 Equipment Stack

| Category | Devices | Notes |
|----------|---------|-------|
| Wired partyline comms | Clear-Com Encore (2-wire), RTS TW | DC power + audio on shared pair; simple, robust |
| 4-wire / matrix comms | Clear-Com Eclipse HX, RTS ADAM | Separate send/receive; multi-channel routing |
| Digital wireless comms | Clear-Com Bolero, Riedel Bolero, FreeSpeak II (DECT 1.9 GHz) | Full-duplex; Bolero supports more packs per antenna than FreeSpeak II |
| IFB | Clear-Com IFB, Sennheiser/Shure IEM as IFB, Comtek | One-way to talent earpiece; program + interrupt |
| Cue lights | DMX-driven cue light systems, Clear-Com CLS | Red/green per station |
| Tally | Switcher GPI/tally to camera and presenter | Camera-live indication |
| Timers | Stage Timer Pro, Irisdown, DSAN Limitimer | Presenter-facing countdown |
| Paperwork | Printed ROS, blocking plan, contact sheet | Network-independent |
| Physical kit | Glow tape, spike tape, torch (red filter), water, wireless spares | Standard SM kit |

**Comms channel plan (typical corporate show):**

| Channel | Members | Traffic |
|---------|---------|---------|
| 1 — Show / Program | Caller, TD, A1, V1, L1, SM, Stream | Cues only. Disciplined. No conversation |
| 2 — Video | V1, camera ops, graphics, media server | Shot calls, source prep |
| 3 — Audio | A1, A2, RF tech | Mic swaps, RF status, gain checks |
| 4 — Stage / Talent | SM, ASMs, dressers, runners | Talent movement |
| 5 — Production | Producer, client liaison, venue | Non-technical decisions |
| IFB-A | Host earpiece | One-way from caller/SM |
| IFB-B | Keynote earpiece (if fitted) | One-way, used sparingly |

**Discipline rule:** channel 1 carries cues only. Any diagnostic conversation moves to a department channel immediately. A caller who cannot be heard because two engineers are debugging on the show channel is a preventable failure.

### 5.3 Cueing Protocol

**Cue light convention.** The dominant theatrical convention is **light ON = standby, light OFF = GO**. This is deliberate: a failed lamp or lost power reads as a missing standby rather than a false GO, and the operator sees the failure before it matters.

| State | Red | Green | Meaning |
|-------|-----|-------|---------|
| Dark | off | off | Nothing pending |
| Standby | **on** | off | Prepare; do not move |
| GO | off | **on** (or red extinguished) | Execute now |
| Hold | red flashing | off | Standby cancelled, remain in position |

Because conventions vary by house and by system, the SM briefs the specific convention in use at the pre-show meeting and confirms each talent position understands it. Confirmed comprehension outranks convention purity.

**IFB discipline.** IFB goes into a presenter's ear while they are speaking to an audience. Every word costs the presenter cognitive load.

| Rule | Detail |
|------|--------|
| Single voice | Only the caller or SM speaks on IFB, never both, never an engineer |
| Brevity | Maximum 5–7 words. "Two minutes." "Wrap up." "Move to your left." |
| Timing | Speak in the presenter's natural pause, never over their sentence |
| Frequency | Maximum ~1 interrupt per 5 minutes unless crisis |
| Confirmation | Establish a physical acknowledgement in rehearsal (touch of the ear, small nod) |
| Never | Do not use IFB for reassurance, commentary, or corrections that cannot be acted on |

**Hand signals** — the no-comms fallback, briefed and rehearsed with talent:

| Signal | Meaning |
|--------|---------|
| Flat palm raised, still | Hold / stand by |
| Palm sweeping toward SM | Come to me / exit |
| Index finger raised | 1 minute remaining |
| Two fingers | 2 minutes remaining |
| Rolling fists | Wrap up / speed up |
| Palms pushing down | Slow down |
| Flat hand across throat | Stop now (used only for genuine stop) |
| Cupped hand to ear | Cannot hear you / mic problem |
| Circled thumb-forefinger | All good / acknowledged |

**Standby lead times by cue type:**

| Cue Type | Standby Lead | Reason |
|----------|-------------|--------|
| Technical (switcher, audio) | 10–15 s | Operator hand already on control |
| Talent entrance from wing | 30–60 s | Physical movement to position |
| Talent from green room | 5–8 min | Walk time + mic check + holding |
| Costume/prop change | Per rehearsal | Measured, not estimated |
| Video roll with pre-roll | Pre-roll duration + 5 s | Server needs cue-up time |

### 5.4 Backstage Flow

```
 ARRIVAL ──► REGISTRATION ──► GREEN ROOM ──► MIC FIT ──► HOLDING ──► WING ──► STAGE
   T-90m        T-85m           T-80m         T-25m       T-8m      T-2m     T-0
                                  │              │           │         │
                              refreshments   A2 fits lav  final ROS  cue light
                              client mtgs    RF check     brief      standby
                              rehearsal      battery log  water      
                              on monitor                   
                                                              
 STAGE ──► EXIT WING ──► DE-MIC ──► GREEN ROOM / AUDIENCE
  T+0        T+1m         T+2m           T+5m
                            │
                     A2 recovers pack,
                     logs battery, sanitises
```

**Green room timing standard (per speaker):**

| Milestone | Time Before Stage | Owner | Action | Gate |
|-----------|------------------|-------|--------|------|
| Arrival confirmed | −90 min | Runner / registration | Tick contact sheet; notify SM | SM knows talent is in building |
| Green room settle | −80 min | Runner | Water, agenda, seat with view of monitor | Talent oriented |
| Content check | −60 min | AV / producer | Confirm deck on server, correct version | Deck matches ROS asset ID |
| Mic fit | −25 min | A2 | Fit lav/headworn, fresh battery, RF check | Level confirmed at console |
| Tech brief | −20 min | SM | Walk-on route, mark position, timer location, IFB test | Talent repeats route back |
| Holding | −8 min | SM / ASM | Move to holding position offstage | Talent within 30 s of wing |
| Wing | −2 min | SM | Final position, mic unmuted check, water taken | Cue light standby visible |
| Stage | 0 | SM | Release on GO | Talent on mark |

**Non-negotiable gates.** The SM does not release talent to stage without: mic confirmed live at the console (verbal confirm from A1), correct deck confirmed loaded (verbal confirm from V1), and talent physically in the wing. Any missing item means the SM holds and informs the caller, who burns buffer (§1.5) rather than putting an unmiked speaker on stage.

**Battery policy.** Fresh cells at every fit — never a partial. Log serial/pack ID, fit time, and expected runtime. For any transmitter live longer than 3 hours, schedule a change during a break. RF techs monitor pack voltage at the receiver; the pack that dies mid-keynote was visible on the meter five minutes earlier.

**Multi-speaker mic pool.** With more speakers than transmitters, the handoff is the risk point:

| Step | Action | Verification |
|------|--------|-------------|
| 1 | Outgoing speaker exits to designated de-mic position | SM escorts; never let talent wander with a live pack |
| 2 | A2 mutes channel at console **before** removing pack | A1 confirms channel muted |
| 3 | Pack removed, capsule sanitised, battery checked/replaced | Battery log updated |
| 4 | Pack fitted to next speaker | Physical fit confirmed |
| 5 | RF and level check in holding, channel still muted | A1 confirms level at console |
| 6 | Channel unmuted only at wing standby | A1 verbal confirm to SM |

### 5.5 Common Failure Modes

| Symptom | Root Cause | Detection | Fix / Prevention |
|---------|-----------|-----------|------------------|
| Empty stage on take | Talent not in wing; no gate enforced | Caller sees empty frame | SM holds cue; enforce §5.4 gates |
| Speaker walks on unmiked | Mic not confirmed live before release | Silence on first words | Verbal A1 confirm mandatory gate |
| Hot mic in green room / restroom | Channel unmuted during handoff | Private audio in PA or stream | Mute before fit, unmute at wing only |
| Talent misses cue light | Light out of sight line from actual standing position | Rehearsal walk-through | Position light where talent will stand, not where convenient |
| Presenter startled by IFB | No IFB test; unexpected voice in ear | Visible flinch on camera | Test IFB in rehearsal; establish acknowledgement |
| Two voices on IFB | Multiple people keyed to talent channel | Presenter confusion | Lock IFB to single source |
| Cue channel unusable | Debugging on show channel | Caller repeating cues | Move diagnostics to dept channel |
| Wrong deck on screen | Version not confirmed at −60 min | Presenter says "that's not my slide" | Asset ID in ROS; V1 confirms version |
| Talent late from green room | Insufficient walk-time allowance | Missed holding milestone | 5–8 min lead for green-room-to-wing |
| Pack dies mid-session | Partial battery reused | Level drops, RF meter falls | Fresh cells always; log and monitor voltage |

### 5.6 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Talent in wing at standby | 100% | SM checklist per speaker |
| Mic-live confirmations before release | 100% | Comms log / checklist |
| Hot mic incidents | 0 | Recording and stream review |
| Missed entrances | 0 | Cue log |
| Cue acknowledgement rate | 100% | Comms recording |
| IFB interrupts per speaker | ≤ 1 per 5 min | IFB log |
| Battery-related dropouts | 0 | RF log + battery log |
| Green room milestone adherence | ≥ 95% of gates on time | SM checklist timestamps |
| Talent-reported briefing clarity | No surprises reported | Post-show debrief |

---

## 6. Live Crisis Protocol

### 6.1 Definition

Crisis protocol is the pre-built, pre-tested set of decisions and mechanisms that convert a failure into a recoverable event without requiring novel thinking under pressure. Its measure is **time to restore**, and its precondition is that every failover path was commissioned and drilled before doors. A redundancy that has never been exercised is not redundancy — it is an assumption.

Two rules govern everything below. First, **life safety overrides show continuity, always and without consultation.** Second, **one voice directs a crisis response** — normally the TD for technical events, the venue's designated authority for life-safety events.

### 6.2 Severity Tiers

| Tier | Definition | Decision Authority | Max Decision Time | Examples |
|------|-----------|-------------------|-------------------|----------|
| **P0** | Life safety | Venue safety officer / emergency services | Immediate, no consultation | Fire alarm, medical emergency, structural, security threat |
| **P1** | Show-stopping technical | Technical Director | < 10 s | Total audio loss, total video loss, power failure |
| **P2** | Visible degradation | Department head (A1/V1) | < 30 s | Single mic dead, one screen down, single camera loss |
| **P3** | Schedule / content | Show caller + producer | < 2 min | Speaker overrun, missing deck, talent no-show |

### 6.3 Redundancy Inventory (commissioned pre-show)

| Subsystem | Primary | Failover Mechanism | Failover Action | RTO |
|-----------|---------|-------------------|-----------------|-----|
| Speech audio | Lectern/lav mic | Pre-gained backup mic on adjacent channel, faded down | Raise backup fader | < 2 s |
| Console | Main console | Mic splitter to backup console, or dual-console on network | Repatch amp input / switch source | 30–120 s |
| PA drive | Primary DSP path | Analogue/secondary path to amps | Switch DSP input source | 5–15 s |
| Video program | Switcher A | Hot standby switcher B via A/B (§2.7) | One A/B switch action | < 1 s |
| Playback | Media server A | Mirrored server B, same timeline | Take server B on switcher | < 2 s |
| Slides | Presenter laptop | Copy of deck on show laptop + PDF on USB | Switch source, resume from slide N | 10–30 s |
| Power | House mains | UPS on all control positions; generator if contracted | Automatic (UPS), manual (gen) | 0 s (UPS) |
| Comms | Wireless packs | Wired partyline positions + mobile phone tree | Move to wired position | 30–60 s |
| Lighting | Console look | Manual house-light preset at venue panel | Venue tech triggers preset | 5–10 s |
| Stream | Primary encoder/bond | Secondary encoder on separate ISP/bonded cellular | Switch ingest | 30–60 s |

**UPS runtime sizing.** Runtime is a function of load against battery capacity, and manufacturer VA ratings assume worst-case load:

```
Example: 1500 VA / 900 W UPS
  Measured load: 300 W (console + switcher + converters)
  Load ratio: 300 / 900 = 33%
  Typical runtime at 33% load: 12-20 min (check the unit's runtime chart)

Sizing rule: target >= 10 min runtime at measured load.
  10 min covers: generator start, or an orderly show hold, or
  transfer to a second circuit. It does not cover "wait it out."
```

Do not put amplifiers or lighting dimmers on control UPS units — their draw collapses runtime. Protect control and signal chain only.

### 6.4 Runbook — Total Audio Loss (P1)

| T+ | Actor | Action |
|----|-------|--------|
| 0 s | A1 | Detect: meters vs PA. Determine if loss is console-side or downstream |
| 2 s | A1 | Announce on comms: "Audio down, console/downstream" — state which |
| 3 s | A1 | Check headphone monitor at console: audio present = downstream fault; absent = console fault |
| 5 s | A1 | Downstream fault → switch DSP input to secondary path |
| 5 s | A1 | Console fault → recall last known-good scene; check master mute/DCA state |
| 10 s | TD | If not restored, declare failover to backup console/path |
| 10 s | SM/Caller | Signal presenter to pause via IFB or hand signal — do not let them keep speaking into a dead PA |
| 15 s | Caller | If > 15 s expected, host to stage with a working mic; hold slide + music bed if no host available |
| 30 s | A2 | Deploy wired handheld to lectern as absolute fallback (pre-run cable, pre-gained channel) |
| 60 s | TD | Restored or in hold. Inform producer of cause and confidence level |
| Post | TD | Log: time, cause, restore time, and whether a drilled path was used |

**Pre-conditions that make this work:** a pre-run wired handheld on a pre-gained channel, a known-good scene stored and scene-safe, a secondary DSP path physically patched, and A1 having practiced the headphone-monitor diagnostic. Without them, this runbook is a wish list.

### 6.5 Runbook — Video / Presentation Loss (P1/P2)

| T+ | Actor | Action |
|----|-------|--------|
| 0 s | V1 | Detect via multiviewer: identify last good stage in chain |
| 2 s | V1 | Announce: "Video down at [source / switcher / processor / display]" |
| 3 s | V1 | Cut to hold slide or logo — **never leave black on screen** |
| 5 s | V1 | Source fault → take mirrored server B or show-laptop copy of deck |
| 5 s | V1 | Switcher fault → A/B to hot standby (§2.7) |
| 8 s | V1 | Processor/display fault → route around via matrix to secondary display path |
| 10 s | Caller | Notify presenter via IFB: "Slides down, keep talking" — most presenters can continue |
| 15 s | SM | If presenter is dependent on slides, host bridges or move to Q&A early |
| 30 s | V1 | Resume from the correct slide number, not slide 1. Presenter states the number if needed |
| 60 s | TD | Declare recovered or move to contingency segment |
| Post | TD | Log cause; verify hold-slide availability restored for next segment |

**Recovery detail that matters:** resuming a 60-slide deck from slide 1 in front of an audience is a second, more visible failure. The show laptop must be able to jump to an arbitrary slide immediately, and the operator must know the current slide number — which means the multiviewer or the ROS tracks it.

### 6.6 Runbook — Speaker Overrun (P3)

Graduated escalation. Each step is more visible than the last; do not skip steps, and do not begin at step 5.

| Step | T+ from 00:00 | Actor | Action | Visibility |
|------|--------------|-------|--------|-----------|
| 1 | −2:00 | VID | Timer shows 2:00 remaining (already running) | None |
| 2 | 00:00 | VID | Timer at zero, begins counting up in red | None |
| 3 | +0:30 | SM | Hand signal from wing: "wrap up" (rolling fists) | Low |
| 4 | +1:00 | Caller | IFB: "Please wrap up." Five words, in a pause | None to audience |
| 5 | +2:00 | SM | SM steps into presenter's sight line at edge of stage | Low |
| 6 | +3:00 | Caller | IFB: "We need to move on now." | None to audience |
| 7 | +4:00 | AUD | Walk-off music bed enters at low level, rising | Medium — unambiguous social cue |
| 8 | +5:00 | SM | Host walks on to thank the speaker and transition | Medium |
| 9 | +6:00 | AUD | Presenter mic faded (not muted) as host takes over | Medium |

**Authority requirement.** Steps 7–9 shorten a client's speaker. That authority must be granted in writing during pre-production, naming who may trigger it and at what threshold. Without pre-agreement, the caller escalates to the producer at step 6 and the producer decides. Fading a paying client's CEO off the PA without prior agreement is a commercial incident, not a technical one.

Fading rather than muting is deliberate: a fade reads as a transition, a hard mute reads as a fault.

### 6.7 Runbook — Fire Alarm (P0)

**The alarm cannot be overridden, delayed, or investigated first.** Life safety systems take absolute precedence over show continuity. Venue emergency procedures and the venue's designated authority govern; production follows.

| T+ | Actor | Action |
|----|-------|--------|
| 0 s | Alarm | Life-safety system activates. Voice evacuation system takes PA priority where fitted |
| 0 s | A1 | Mute program audio and all playback immediately. Do not compete with the alarm |
| 2 s | LX | House lights to 100%. Egress lighting is on life-safety circuits and is already live |
| 3 s | VID | Cut screens to evacuation graphic if pre-built, otherwise blank. Never leave content running |
| 5 s | SM | Escort talent off stage to nearest designated exit. Talent leave everything |
| 5 s | Caller | Cease all show cues. Announce on comms: "Show is stopped, evacuation" |
| 10 s | Producer/venue | Venue-scripted evacuation announcement, if the venue directs a live announcement |
| 15 s | Crew | Crew take assigned marshalling roles per venue briefing; assist directing to exits |
| 30 s | All | Evacuate. Equipment is abandoned. Nobody re-enters for gear |
| At assembly | SM / producer | Roll call: talent, crew, contractors against contact sheet |
| — | TD | Report headcount status to venue authority |
| Re-entry | Venue only | **Only** the venue/fire authority authorises re-entry. Production never makes this call |

**Standard evacuation announcement pattern** (use the venue's exact script if provided): state that an alarm has sounded, direct people to leave by the nearest exit, tell them to leave belongings, name the assembly point, and state that staff will direct them. Do not speculate on cause, do not say "false alarm", do not tell people to remain seated.

**Pre-show requirements:** attend the venue safety briefing, know every exit from the stage and the room, know the assembly point, know the crowd-management staffing the venue provides (assembly occupancies commonly require trained crowd managers at roughly 1 per 250 occupants under NFPA 101, but the venue's authority having jurisdiction sets the actual figure), and have the contact sheet printed for roll call.

### 6.8 Runbook — Medical Emergency (P0)

| T+ | Actor | Action |
|----|-------|--------|
| 0 s | Nearest crew | Reach the person. Do not move them unless they are in immediate danger |
| 5 s | Single designated caller | Call emergency services (911 / 112 / local) **and** venue medical. One caller only — multiple calls delay dispatch |
| 5 s | Crew | Send someone for the AED and for the venue's first aider. Know the AED location before doors |
| 10 s | TD | Decide: pause or continue. **Default is pause** if the incident is visible to the audience |
| 10 s | STR | Cut the stream immediately to slate. Non-negotiable — no medical incident goes to a public feed |
| 15 s | VID | Cut screens to hold slide. Cameras off the incident, no exceptions |
| 15 s | LX | House lights to 50–70% — enough for responders to work, not a full startle |
| 20 s | AUD | Low-level music bed; mute stage mics |
| 30 s | Host / producer | Brief announcement: acknowledge a short pause, ask people to remain seated, keep aisles clear |
| Ongoing | SM | Clear a path from the incident to the nearest vehicle access. Hold that path open |
| Ongoing | Crew | Keep a corridor clear. Move audience away without creating a crush |
| On arrival | Designated crew | Meet responders at the door and lead them directly to the casualty |
| After | Producer + client | Decide on resumption jointly. Resume only when the space is clear and calm |
| Post | Producer | Written incident record: time, actions, responders, witnesses. No public statement |

**Announcement content rule:** never state or speculate on the nature of a medical condition. Acknowledge the pause, request calm, and give a next step. Privacy and dignity are part of the response.

**Pre-show requirements:** AED locations known and written on the crisis card, venue first-aid provision confirmed, nearest emergency department known, vehicle access route identified, and one named person per shift designated as the emergency caller.

### 6.9 Crisis Card (printed, at every operator position)

```
┌──────────────────────────────────────────────────────────────────────┐
│ CRISIS CARD — [EVENT NAME] — [DATE] — REV [n]                        │
├──────────────────────────────────────────────────────────────────────┤
│ TD: [name] [mobile]        Caller: [name] [mobile]                   │
│ SM: [name] [mobile]        Producer: [name] [mobile]                 │
│ Venue duty manager: [name] [mobile]   Venue security: [ext]          │
│ Emergency services: [911/112]   Venue medical: [ext]                 │
├──────────────────────────────────────────────────────────────────────┤
│ AED LOCATIONS: [1] ................  [2] ................            │
│ FIRE EXITS FROM STAGE: SL ..........  SR ..........                  │
│ ASSEMBLY POINT: ....................................                 │
│ VEHICLE ACCESS FOR AMBULANCE: ......................                 │
├──────────────────────────────────────────────────────────────────────┤
│ P0 LIFE SAFETY   → Stop show. Mute PA. House lights 100%. Cut stream.│
│                    Follow venue authority. Never authorise re-entry. │
│ P1 AUDIO LOSS    → §6.4  Backup fader → secondary DSP → wired h/h    │
│ P1 VIDEO LOSS    → §6.5  Hold slide → server B → A/B standby         │
│ P2 SINGLE FAULT  → Dept head resolves. Inform caller. No show stop.  │
│ P3 OVERRUN       → §6.6  Timer → signal → IFB → SM → music → host    │
├──────────────────────────────────────────────────────────────────────┤
│ RULE 1: Life safety beats show continuity. Always.                   │
│ RULE 2: One voice directs. TD for technical, venue for life safety.  │
│ RULE 3: Never leave black screens or dead air. Hold slide + bed.     │
│ RULE 4: Cut the stream before diagnosing anything visible.           │
└──────────────────────────────────────────────────────────────────────┘
```

### 6.10 Pre-Show Drill Schedule

Failover paths are verified by deliberate failure during rehearsal, not by inspection.

| Drill | Method | Pass Criterion | When |
|-------|--------|---------------|------|
| Mic failure | A2 mutes primary mid-sentence without warning A1 | Backup up within 2 s | Rehearsal |
| Console failure | Power down primary (or simulate) | Backup path audible within RTO | Load-in, not rehearsal |
| Switcher failure | Pull PGM output of switcher A | A/B executed < 1 s, no black | Rehearsal |
| Source hot-plug | Unplug and replug presenter laptop | Recovery < 2 s, no EDID renegotiation | Commissioning |
| Playback failure | Kill server A mid-clip | Server B takes within 2 s | Rehearsal |
| Power failure | Open the breaker on one circuit | UPS holds; nothing on that circuit is show-critical unprotected | Load-in |
| Comms failure | Remove SM's wireless pack | SM at wired position within 60 s | Rehearsal |
| Overrun | Rehearse steps 1–9 of §6.6 with a stand-in | Every actor knows their step | Rehearsal |
| Evacuation | Walk the route with all crew; confirm exits and assembly | Every crew member can name their exit and role | Pre-doors briefing |
| Crisis card | Verbal quiz: "where is the nearest AED?" | Correct answer from every operator | Pre-doors briefing |

### 6.11 Common Failure Modes

| Symptom | Root Cause | Prevention |
|---------|-----------|-----------|
| Backup path also dead | Both paths on one circuit / one device / one cable route | Separate circuits, separate physical routes, separate UPS |
| Failover takes minutes | Backup unpowered, unprogrammed, or unpatched | Hot standby per §2.7; power and program it |
| Everyone talks at once during crisis | No single directing voice | Name the TD on the crisis card; enforce one voice |
| Crew freeze | Never drilled; first exposure is the live failure | §6.10 drills |
| Medical incident goes out on stream | No stream-cut reflex | Rule 4 on crisis card; drill the cut |
| Black screen during recovery | No hold slide armed | Hold slide permanently armed on a switcher input |
| Dead air during recovery | No music bed ready | Bed loaded on a DCA, ready at all times |
| Resumed on wrong slide | Slide number not tracked | Multiviewer or ROS tracks current slide |
| Nobody knows where the AED is | Not briefed, not on card | Crisis card + verbal quiz |
| Crew re-enter after evacuation for gear | No explicit prohibition briefed | State it in the safety briefing: gear is abandoned |
| Client surprised by a shortened speaker | No pre-agreed authority | Written sign-off on §6.6 steps 7–9 |

### 6.12 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Mean time to detect (MTTD), P1 | < 5 s | Drill timing + show log |
| Mean time to restore (MTTR), P1 | < 30 s | Drill timing + show log |
| RTO — speech audio | < 2 s | Timed drill |
| RTO — video program (hot standby) | < 1 s | Timed drill |
| RTO — presentation content | < 30 s | Timed drill |
| RTO — stream | < 60 s | Timed drill |
| Drills completed before doors | 100% of §6.10 list | Drill checklist |
| Audience-visible failure duration | < 10 s per event | Recording review |
| Dead air / black screen total | 0 s | Recording review |
| Stream cut latency on P0 | < 10 s | Stream archive review |
| Crisis card at every operator position | 100% | Physical audit |
| Post-incident hot wash held | Within 24 h of any P0/P1 | Documented log |

### 6.13 Post-Incident Procedure

1. **Stabilise first.** No analysis while the show is running. The only in-show record is a timestamped note.
2. **Hot wash within 24 hours** while memory is accurate. Attendees: TD, affected department heads, SM, producer.
3. **Record facts, not blame:** what was detected, when, by whom, what action was taken, what the actual restore time was, and whether the drilled path was used or improvised.
4. **Identify the precondition that failed** — almost always a commissioning or drill gap rather than an operator error.
5. **Update this document and the crisis card.** An incident that does not change the runbook will recur.
6. **For P0 events:** written incident report to the client and venue, factual only, no speculation on cause or medical detail. Insurance and legal review before any external statement.


























