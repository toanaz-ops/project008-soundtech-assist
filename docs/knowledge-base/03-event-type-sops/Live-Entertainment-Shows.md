# Live Entertainment Shows — Standard Operating Procedure

## Event Profile

**Defining constraints:** Timecode is law; rigging is life-safety. Sound quality matters but is subordinated to start-time and show-critical continuity. Touring productions have carryover from prior shows; one-offs may have zero rehearsal time and full responsibility for show-call.

**Differences from Corporate/Conference events:**

| Dimension | Corporate/Conference | Live Entertainment |
|-----------|---------------------|-------------------|
| Primary risk | Speaker embarrassment | Equipment failure mid-song |
| Time sensitivity | Schedule overrun (annoying) | Missed cue (show stops) |
| Acceptance threshold | "Good enough" acceptable | Pro-tour-grade required |
| Tech rehearsal time | 30–60 min | 4–8 hours minimum |
| Liability profile | Brand damage | Injury / death on rigging |
| Cue authority | Stage manager | Show caller + MD + FOH |
| IEM priority | Rare | Standard for any act with own mixer |

**Crew baseline for a 1,500-cap live show:**
- A1 (FOH engineer), A2 (monitor world), A2.2 (monitor assist)
- LD (lighting designer), L2 (lighting board op)
- V1 (video director), V2 (video op), EIC (engineer-in-charge)
- SM (stage manager), PYRO (pyrotechnician, where applicable)
- MED (on-site medical), SEC (security lead), RIG (certified rigger)
- SFX (special effects), STR (backstage runner / talent handler)

---

## 1. SMPTE Timecode Sync

Timecode synchronises playback, lighting, video, and pyro to a single clock. When any element drifts, the show looks uncoordinated even if every individual system is technically working.

### 1.1 Master Clock Source

| Source type | Examples | Drift rate | When to use |
|-------------|----------|-----------|-------------|
| Dedicated TC generator | Rosendahl Nanosyncs HD, Ambient NanoLockit, Denecke Dcode | <1 frame per 6 hours | Touring / broadcast-grade |
| DAW as master | Ableton Live with TC Track, Pro Tools with Sync HD | 0 frames (locked to audio clock) | When DAW is the playback source |
| Console as master | DiGiCo with Orange Box, Avid Venue | Variable | Not recommended; clock stability untested |
| Camera as master | RED / ARRI with built-in TC | Acceptable for visual sync | Film-style shoots, not live shows |

**Rule:** Master clock must be either a dedicated generator or a DAW acting as one. Never derive show TC from a video switcher, lighting console, or FOH console — those are downstream consumers.

### 1.2 LTC Distribution

Linear Timecode (LTC) is the standard distribution format. It rides on balanced audio cable (XLR) and sounds like audio noise — never patch it through a normal audio channel.

**Distribution topology:**

```
Master Generator (e.g., Nanosyncs HD)
  ├─ OUT 1 → DAW (Ableton Live TC input)
  ├─ OUT 2 → FOH console (DiGiCo / Avid / WING via MTC-to-LTC interface)
  ├─ OUT 3 → Lighting console (MA3 / grandMA3, EOS, Hog)
  ├─ OUT 4 → Media server (disguise, Watchout, Pixera)
  ├─ OUT 5 → Backup DAW (parallel machine)
  └─ OUT 6 → Recording truck / broadcast feed
```

**If only one TC output is available:** use a passive or active distribution amp (Radial Engineering JS-2, Sescom TC DA-1) to fan out to all consumers. Never Y-cable TC — it causes level drops and ground loops.

### 1.3 Frame Rates

| Rate | Use | Notes |
|------|-----|-------|
| 29.97 DF | North American broadcast standard | Drop-frame compensates for 29.97 ≠ 30 fps |
| 30 NDF | Music production (US) | Non-drop, for audio-only work |
| 25 | PAL regions (Europe, much of Asia) | For tours playing Europe |
| 24 | Film / cinema | Rare for live shows; some video elements may use |

**Critical:** All systems must match the master's frame rate AND drop-frame flag. A 30 NDF master sent to a 29.97 DF consumer drifts ~1 frame every 33 seconds. Over a 3-hour show that's ~330 frames = 11 seconds of visible drift.

### 1.4 Sync Verification Protocol

**Pre-show (T-2h):** All systems show identical TC at the same wall-clock time. Verify by starting playback of a 10-second test song and checking every system's position counter at the end.

**During show:** Visual check every 30 minutes on the lighting console and media server (they have prominent TC displays). FOH and monitor world are typically listening only.

**Drift tolerance:** <1 frame over the show duration. If a system drifts 1+ frame, freewheel (let it coast) for 30 seconds to see if it self-corrects, then manually re-sync.

**Post-show:** Record the master TC offset of each system at show end. If any system drifted >1 frame, flag for the next show's setup.

### 1.5 Freewheel and Chase Mode

When TC is lost (cable unplugged, generator rebooted), each consumer should be in **Freewheel** mode (continue at last known rate) for at least 5 seconds before entering **Chase** mode (actively trying to re-lock). This prevents audio glitches from rapid re-lock attempts.

**Configuration per consumer:**
- DAW (Ableton): Preferences → MIDI/TC → "Freewheel before jam sync for 5 seconds"
- Lighting console (MA3): Setup → MIDI/TC → Freewheel 5s, Jam Sync on
- Media server (disguise): System → Sync → Freewheel 5s, Auto-chase enabled

### 1.6 Common Failures

- **Ground loop on TC distribution** — causes intermittent sync loss. Use isolated DAs (Radial JS-2 has transformers).
- **Wrong frame rate flag** — silent drift, no error message. Verify at first cue.
- **DAW loses TC when transport stopped** — re-arm on first frame of next song; configure DAW to hold TC across transport changes.

---

## 2. Playback Redundancy

Playback (backing tracks, click tracks, SFX, video sync) is the single most failure-prone element in a touring show. Redundancy is not optional.

### 2.1 Two-Machine Setup

| Machine | Role | Software (typical) | Notes |
|---------|------|-------------------|-------|
| Primary | Active playback | Ableton Live, QLab, Reaper | Sync to TC master, output via Dante/MADI/analog |
| Backup | Hot standby, mirrors primary | Same as primary, offset by 0 frames | Listens to same TC, plays in lockstep |

**Why hot standby vs cold backup:** If primary fails and backup is cold, you have 30-90 seconds to start it. If primary fails and backup is hot, the failover is <1 second (just a crossfade or relay switch). Live shows cannot survive 30 seconds of silence mid-song.

### 2.2 Watchdog / Auto-Failover

A **watchdog** is a process that monitors primary playback and triggers failover if audio stops.

**Hardware approach:** Radial Engineering SW8-USB or Behringer DI800P — auto-switches to backup if primary signal drops below threshold.

**Software approach:** Ableton Live + Companion + OSC. Ableton sends a heartbeat every second; Companion watches for missed beats; after 2 misses, fires an OSC command to switch the FOH console's playback input to backup.

**Trigger criteria:** No audio activity for >2 seconds on primary, OR heart beat missed >2 cycles.

### 2.3 Stem Organization

Separate stems onto independent outputs so the show can keep going if one stem fails.

| Stem | Output | What happens if it fails |
|------|--------|-------------------------|
| Click (drummer only) | WING IEM bus, drummer's mix only | Drummer loses click; show continues |
| Backing tracks (keys/synths) | Main L/R | Show drops those parts; live musicians cover |
| Vocal effects (doubles, harmonies) | Backup vocalist IEM mix | BVs hear dry vocal; show continues |
| SFX (lasers, explosions, risers) | FX bus → Main L/R | SFX missing; video cues still fire |
| Video sync audio | Video playback machine | Video freezes; audio continues |

**Stem count budget:** Minimum 4 (click, tracks, vocals, SFX), typical 8, maximum 16 (for large tours with separate instruments per stem).

### 2.4 Recording Layer

Every playback show should also be recording to capture the live mix alongside playback for post-show analysis.

**Two independent recorders:** Reaper on a separate machine capturing Main L/R + click + individual stems to a local SSD + cloud sync. If primary playback fails and backup takes over, recording continues because both recorders are downstream of the playback switch.

**Naming convention:** `YYYY-MM-DD_VenueCity_Song01_Take01.wav` — keeps multi-show archive sortable.

### 2.5 Pre-Show Verification

**T-4h:** Both machines play same 30-second test song, both record at sample-accurate sync. Verify on each:
- TC matches master within 0 frames at end of song
- All stems play on correct outputs
- Recording captures all stems
- Backup failover triggers correctly when primary is muted

**T-30min:** Same test with show song. Verify click triggers drummer's IEM at correct volume, backing tracks trigger FOH at correct volume, SFX fire visual cues on lighting console via OSC/MTC.

**T-5min:** Final test with full show. Standby musician confirms click audible; SM confirms video cues firing; FOH confirms track level matches previous show.

### 3.1 Why This Section Has a Different Tone

Everything else in this SOP is about keeping the show running. This section is about keeping it from killing anyone. Truss, motors, and the loads hung from them are governed by physics first and contract second, and physics does not accept "we'll fix it on the next tour." The person who signs the load plot takes personal criminal liability in most US jurisdictions, in addition to civil exposure; that signature is the reason this section exists in this detail.

### 3.2 Load Calculations — Point Load vs Distributed Load

Every rigged item resolves into one of two load types, and the rig must be analysed separately for each. The arithmetic is secondary; the discipline is to never confuse the two.

| Load type | Definition | Examples | Analysis |
|-----------|-----------|----------|----------|
| **Point load (static)** | A single attachment transferring a discrete mass at a single point along the truss | Single CM Lodestar on a truss pickup, single ground-stack speaker hung, lighting fixture on a clamp | Treat as a concentrated vertical force; check local truss capacity at that pickup, not the global UDL |
| **Point load (dynamic)** | A point load with motion — a moving scenic, a winched video panel, a performer winch | Tracked video wall, performer flying rig, automation winch load | Multiply static by 1.5 minimum dynamic factor; verify hoist has dynamic-rated brake; verify E-stop decel ≤ 0.5 g |
| **Distributed load (UDL)** | Mass spread uniformly along a span | LED wall on multiple points, line array flown on a pre-rigged frame, lighting bar with even fixture spacing | Treat as mass / span (kg/m or lb/ft); check global truss capacity table for that span |

The error mode that destroys shows: a 150 kg line array hung from a frame pre-rigged for a 60 kg/m UDL passes the point-load check at the pickup (150 kg < pickup WLL), and would fail the span check (60 kg/m × 9 m = 540 kg vs array + frame + cabling = ~720 kg). Both checks must pass, every time, with margin.

**Combined load formula for a single pickup:

```
P_total = (1.0 × P_static) + (1.5 × P_dynamic) + (1.0 × P_UDL_local)

where:
  P_static       = mass of all permanently rigged items at the pickup (kg)
  P_dynamic      = mass of any moving scenic / automation at the pickup (kg)
  P_UDL_local    = tributary UDL contribution from distributed items at the pickup (kg)
```

Every term multiplied by gravity (9.81 m/s²) for the structural calc; motors and shackles are rated in kg-force, so in practice the terms are used as kg directly. Be explicit in the load plot about which convention is in use; the difference between kg-mass and kg-force in a high-gravity venue (mountain elevation, rotating stage at radius) is small but not zero.

### 3.3 WLL Safety Factor — 10:1, and Why It Is Not 5:1

The Working Load Limit (WLL) is the maximum *intended* load. The **Minimum Breaking Load (MBL)** of the hardware is the load at which the part catastrophically fails. The ratio MBL:WLL is the safety factor, and for entertainment rigging the industry standard is **10:1** — for example, a Crosby G-2130 1" screw-pin shackle rated WLL 4.54 t (10,000 lb) has a typical MBL of 47.6 t (105,000 lb).

| Factor | Where it appears | Why |
|--------|------------------|-----|
| **10:1** on primary structure (truss, motors, primary steel) | All overhead rigging | Entertainment-industry consensus (ESTA, ANSI E1.21, PLASA); aligns with most manufacturer datasheets |
| **5:1** on secondary steel (ground-support bases, bumpers, soft-shackle backups) | Some venues, some ground-rig | Allowed by code for certain structural items; never for primary overhead |
| **3:1** on rope and webbing for non-life-safety (set dressing, banners) | Decorative only | ANSI/CSA allowances for non-life-safety textile |
| **1:1** on rated cable and wire rope | Where manufacturer publishes the WLL already at 5:1 | Use the published WLL; do not re-derive |

A 10:1 factor is not arbitrary. It absorbs four compounding uncertainties: unknown dynamic load (a chain motor start under load can shock at 1.3–1.8× static), material fatigue accumulation over the rigging's service life, environmental derating (corrosion, temperature, abrasion), and the consequence-of-failure asymmetry (failure above people is unforgiving). Dropping to 5:1 halves the margin and doubles the probability of an incident over a tour's accumulated cycles.

**Derating rules that must be applied to the published WLL before it appears on the load plot:**

| Condition | Derate published WLL by |
|-----------|--------------------------|
| Outdoor / weather exposure (rain, salt air) | 25% |
| Visible surface damage (nicks, gouges, bent bow) | Remove from service |
| Missing / unreadable stamp on shackle, pin, or wire rope termination | Remove from service |
| Use above 80% of published WLL on a continuous tour | Document and rotate hardware quarterly |
| Vertical pull angle > 30° off-axis (horizontal forces on hardware rated for vertical) | Apply vector derate: WLL_eff = WLL × cos(θ) |

### 3.4 Global Truss F34 12" Box Truss — Capacity Table

The workhorse truss on most touring rigs is Global Truss F34 (12" / 290 mm square) in 12" (290 mm) box profile. The published capacities below are for simply-supported spans under uniform load, with ends free to rotate, lateral bracing at the top chord at ≤ 1 m centres, and the load applied at the bottom chord. Confirm against the current Global Truss datasheet — these figures are for planning only and are marked **[verify]** against the load table shipped with the hardware. **[verify Global Truss F34 12" published capacities; figures below are typical mid-range values]**

| Span (m) | UDL (kg/m) | Total UDL (kg) | Centre point load (kg) | Third-point loads, 2 × (kg) | Quarter-point loads, 3 × (kg) | Notes |
|----------|------------|----------------|------------------------|------------------------------|----------------------------------|-------|
| **4** | 450 | 1800 | 1500 | 750 ea | 500 ea | Most forgiving span; safe for almost any standard rig |
| **6** | 250 | 1500 | 1100 | 550 ea | 366 ea | Typical lighting bar span in mid-size venues |
| **8** | 150 | 1200 | 800 | 400 ea | 266 ea | Maximum comfortable span for a single-bar lighting trim |
| **10** | 90 | 900 | 600 | 300 ea | 200 ea | Span limit for many specs without centre support |
| **12** | 55 | 660 | 450 | 225 ea | 150 ea | Anything past this needs a centre hang, mid-span support, or a heavier truss (F44 / F45 / F54) |

**Reading the table:** the UDL column is the maximum mass per metre of span, *including truss self-weight*. The third-point and quarter-point columns are for rigging where the load is concentrated at those locations — typical for a line array hung from a frame at the third points, or a lighting bar pre-rigged at the quarters.

**Deflection rule of thumb:** even when the load passes the capacity check, the deflection at mid-span should not exceed **L/100** (span / 100). At 10 m span that is 100 mm; at 12 m, 120 mm. Beyond that the visible sag of a lighting bar reads as a problem to the audience even though the structure is sound, and line array inter-element angles shift enough to disturb coverage.

**Span and pickup placement are inseparable.** A 10 m span with pickups at the ends (0 m and 10 m) is not the same load case as the same 10 m span with pickups 0.5 m in from each end — the cantilever overhang reduces the allowable UDL by approximately the square of the overhang ratio. For every metre of overhang past the pickup, subtract roughly 10–15% from the allowable UDL. Pickup placement is a design decision, not a rigging convenience.

### 3.5 Motors — CM Lodestar 1-Ton and the Motion Labs Control Desk

The entertainment-industry standard chain hoist is the **CM Lodestar** (Columbus McKinnon). The 1-ton (2,000 lb / 907 kg) single-reeved model is the workhorse of touring rigs.

| Parameter | Specification |
|-----------|--------------|
| Capacity (single reeve) | 907 kg (2,000 lb) |
| Capacity (double reeve) | 1,814 kg (4,000 lb) — uses a 2-part block at the load |
| Lift | 15 m (50 ft) standard; 30 m available |
| Lift speed | 4 m/min (13 ft/min) under full load |
| Power | 208–230 V 3-phase, 50/60 Hz; also 110 V single-phase variant (slower) |
| Control voltage | 24 VDC across collector ring (safe for cable change-overs) |
| Chain | Grade 80 alloy, 8 mm pocket wheel |
| Brake | Self-engaging, load-side; second brake on motor shaft |
| Limit switches | Upper and lower, factory-set; field-adjustable with calibrated gauge |
| Body weight | ~63 kg (139 lb) |
| Duty cycle | 50% per hour under full load; intermittent per ANSI E1.6 |

The control desk is **Motion Labs** (the de-facto touring standard). The Motion Labs desk provides 24 VDC to the motor's collector ring; reversing polarity reverses direction; removing voltage stops the motor with the self-engaging brake. The desk provides a neutral at centre, two directions (up/down) on a joystick or pushbutton, and a series of indicator LEDs. For multi-motor hoists, Motion Labs also produces 4-, 8-, and 12-channel desks and the 24-channel touring desks with patch-group programming.

**Critical electrical practice.**

- **Never bypass the limit switches.** They are the last mechanical defence against a load being driven into the truss or the floor. If a limit is suspected of failure, the motor is removed from service until inspected.
- **Always run the motor to its upper limit under no load at the start of load-in** to verify brake engagement and direction (a 3-phase motor wired with two phases swapped will run backwards and grind the limit cam in the wrong direction).
- **Verify the chain container is correctly seated** before the first lift. A misseated container allows the chain to pile and bind, overheating the motor.
- **Do not dead-hang a motor.** A chain hoist is rated for the chain pulling through the body, not for the body hanging statically on the load hook above it for hours. For pre-rigged trims that stay up all day, use a steel-beam clamp on the parent steel and a separate rigging steel down to the truss pickup.

### 3.6 Pre-Rigging Inspection Checklist

Every item that goes overhead is inspected before it is hung, and the inspection is logged. The checklist below is the minimum; any item that fails any step is tagged out and removed from service, not "fixed later."

**Shackles (Crosby G-2130 / G-213 / equivalent screw-pin or bolt-type):**

| # | Check | Pass |
|---|-------|------|
| 1 | Body stamp legible: WLL, manufacturer, grade | Yes / No |
| 2 | Bow and pin free of nicks, gouges, bends, cracks | Yes / No |
| 3 | Screw pin threads clean, undamaged, full length | Yes / No |
| 4 | Pin fully seats and locks (cotter pin or captive nut where required) | Yes / No |
| 5 | Marked with current inspection colour / month tag | Yes / No |
| 6 | Free rotation on the pin (no seizing) | Yes / No |

**Wire rope (galvanized 6×19 or 6×37 IWRC):**

| # | Check | Pass |
|---|-------|------|
| 1 | Diameter ≥ published nominal (no more than 10% reduction from nominal) | Yes / No |
| 2 | No broken wires exceeding: 3 in one strand in one rope lay, or 9 randomly distributed in one rope lay | Yes / No |
| 3 | No kinks, birdcaging, popped core, or heat damage | Yes / No |
| 4 | Thimbles in all eye terminations | Yes / No |
| 5 | Clips (if used) correctly spaced, torqued, and oriented (U-bolt on dead end) | Yes / No |
| 6 | Termination (swaged, spliced, or clipped) inspected and stamped | Yes / No |

**Truss pins ( conical or half-conical, often supplied with the truss):**

| # | Check | Pass |
|---|-------|------|
| 1 | Correct diameter and profile for the truss series (F34 / F44 / F45 / F54 are not interchangeable) | Yes / No |
| 2 | R-clip or spring-clip fully engaged on every pin | Yes / No |
| 3 | Pin free of bending, mushrooming, scoring | Yes / No |
| 4 | Truss ends clean, spigots aligned, no damaged or bent chords | Yes / No |

**General hardware (slings, steel, spansets, beam clamps):**

| # | Check | Pass |
|---|-------|------|
| 1 | Polyester round-sling cover intact, no cuts, burns, or chemical damage | Yes / No |
| 2 | Steel wire-rope sling ferrules intact, no broken wires at termination | Yes / No |
| 3 | Beam clamp jaw width fits the beam; set screw fully engaged on flange | Yes / No |
| 4 | All gear stamped with WLL and current inspection tag | Yes / No |

The inspection log entry format (per hardware item):

```
DATE       TIME   ITEM              ID/STAMP   INSPECTOR   RESULT
2026-08-11 09:15  Crosby G-2130 1"  AX-4471    J.M.         PASS
2026-08-11 09:15  Truss pin F34     TP-2218    J.M.         PASS
2026-08-11 09:16  Round sling 2t    RS-1044    J.M.         PASS / fail: cut on cover, TAG OUT
```

### 3.7 Certified Rigger Sign-Off Protocol (ETCP Arena Rigger)

The person who signs the load plot accepts legal liability for every item in it. The certification that demonstrates the minimum competency is the **Entertainment Technician Certification Program (ETCP) Arena Rigger** credential, issued by the Entertainment Services and Technology Association (ESTA). The credential requires 1,000+ hours of logged rigging work under a certified rigger, a written examination, and ongoing continuing-education credits to maintain.

| Role | Certification requirement | Authority |
|------|---------------------------|-----------|
| Head Rigger | **ETCP Arena Rigger** (current) | Sole sign-off on the load plot; sole authority to fly or refuse to fly |
| Rigging crew | ETCP Arena Rigger or equivalent; supervised otherwise | Can hang under the direction of a Head Rigger |
| Lift Director (automation) | ETCP + manufacturer course for the specific automation system | Authority over automated / moving elements |
| Production / Tour Manager | Not a substitute for ETCP | Cannot override a rigger's stop-authority |

**The sign-off chain:**

1. **Load plot drafted** — by the Head Rigger, in pre-production, from the venue rigging plot and the show's equipment list. Units in kg, every pickup numbered, every load quantified, every span checked.
2. **Pre-rig inspection logged** — every hardware item above. Log filed with the show.
3. **Pre-rig walk** — at load-in start, the Head Rigger walks the venue with the venue's master rigger (where applicable), confirms house steel, motor hangs, and trim heights.
4. **Flying each trim** — the rigger commands each lift verbally ("Motor 7, take up slack… take up… hold"); a second rigger or designated spotter watches the trim and calls clear.
5. **Sign-off** — on completion of every trim, the Head Rigger signs the trim card for that rig point. Sign-off is per trim, not per show — a trim card must exist for every pickup.
6. **End-of-show sign-off** — same as 5, repeated at load-out. Any deviation (a load added during the show, a motor repositioned) requires an updated trim card and a new sign-off.

**No-go authority.** The Head Rigger has *sole* authority to refuse any lift, any trim height, any load addition, any hardware substitution. This is not advisory. Production cannot override the rigger. The rigger cannot be overruled by the tour manager. Insurance is void if the chain of sign-off is broken.

### 3.8 Worked Example — Working Load Calculation

A 12 m × 0.5 m pre-rigged lighting bar carries an even line of 12 LED moving lights at 28 kg each, plus cabling, clamps, and the bar itself at 60 kg total. It is trimmed at 8.0 m AGL on two motors at 1.0 m in from each end. Determine whether the trim is safe on F34 12" truss with a 10:1 safety factor on hardware.

**Step 1 — Total static load.**

```
Fixtures: 12 × 28 kg     = 336 kg
Bar + clamps + cabling   =  60 kg
Total static             = 396 kg
```

**Step 2 — UDL check at 12 m span.**

```
UDL_actual = 396 kg / 12 m = 33 kg/m
UDL_allowable (12 m, F34)  ≈ 55 kg/m  (per §3.4 table)
Margin = (55 - 33) / 55   = 40% margin on span UDL
```

The span passes with substantial margin — no derating required.

**Step 3 — Point-load check at motor pickups.**

The bar is hung at 1.0 m in from each end. Each pickup carries:

```
Static per pickup = 396 / 2 = 198 kg
Allowable per motor pickup (1-ton Lodestar) = 907 kg WLL
Effective WLL (10:1) hardware factor already in the 907 kg figure; do not reapply
Margin per pickup = (907 - 198) / 907 = 78% margin
```

Passes. The 1-ton Lodestar at each pickup has a 78% margin against the static load.

**Step 4 — Pickup overhang derate.**

The motor hangs the bar at 1.0 m in from each end; the bar extends 1.0 m past each pickup as cantilever. Per §3.4 rule of thumb (10–15% UDL reduction per metre of overhang), the derate is ~12%:

```
UDL_allowable_eff = 55 × (1 - 0.12) = 48.4 kg/m
UDL_actual = 33 kg/m
Margin = (48.4 - 33) / 48.4 = 32% margin
```

Passes — still has 32% margin after overhang derate, with the original 78% motor margin as further safety.

**Step 5 — Deflection check.**

```
Allowable deflection = L/100 = 12 m / 100 = 120 mm
Estimated deflection at 33 kg/m on F34 12" ≈ 65 mm (per manufacturer's load table)
Margin = (120 - 65) / 120 = 46% margin on deflection
```

Passes. The trim is visibly straight at load-in.

**Step 6 — Sign-off.**

```
TRIM CARD — Rig Point 1 / Rig Point 2
Date: 2026-08-11
Trim: Pre-rigged lighting bar, F34 12" truss, 12 m span
Static load: 396 kg (336 fixtures + 60 bar/clamp/cable)
Motors: 2 × CM Lodestar 1-ton at 1.0 m in from each end
UDL: 33 kg/m vs allowable 48.4 kg/m (derated), 32% margin
Pickup: 198 kg per motor vs 907 kg WLL, 78% margin
Deflection: 65 mm vs allowable 120 mm, 46% margin
Safety factor: 10:1 throughout, no derating conditions active
Head Rigger: ________________  ETCP #AR-____  Date: __________
```

---

## 4. Backstage Access Control

### 4.1 Why This Section Is Operational, Not Bureaucratic

The credential system is the only part of the show that a determined unauthorised person will test in person. A wristband is not a sticker; it is a moment where security has the explicit authority — and the duty — to stop someone. The system below assumes that authority will be exercised, by people who have been briefed on how to exercise it, in front of an artist management team that has contractual reasons to test it.

### 4.2 Credential Tiers

Five tiers, ordered by access. Each tier has a colour-coded wristband and a lanyard combination; neither alone is sufficient. A wristband without the matching lanyard photo credential is incomplete and must be refused at any checkpoint.

| Tier | Wristband colour | Hex | Lanyard | Access granted | Issued by |
|------|------------------|------|---------|-----------------|-----------|
| **All Access** | Black with gold stripe | #1A1A1A + #D4AF37 | Gold clip | Everywhere except the artist's dressing room when door is closed, on-stage left wings during performance, and any area designated "Lock Out" by SM | Tour Manager + Head of Security, both signatures required |
| **Backstage** | Solid red | #C8102E | Red clip | All backstage corridors, FOH, monitor world, dressing room common areas, hospitality, catering | Security Lead, against photo ID on the guest list |
| **Stage** | Solid yellow | #FFD500 | Yellow clip | Backstage + on-stage during non-performance; cleared wings during performance; deck during changeovers | Stage Manager + Department Head (L1, A1, A2, V1, Rigger) |
| **Crew** | Solid green | #2E7D32 | Green clip | Department-specific work area only; e.g., a lighting crew member's green band allows stage, FOH area, and their truck, but not artist areas | Department Head only |
| **Media** | Solid white with black diagonal stripe | #FFFFFF + #000000 | White clip | Press riser, photo pit (if designated), designated interview areas, hospitality during specified window; never on stage, never in dressing rooms | Publicist / Press Officer, against press credential and photo ID |

**Tier ordering rationale.** A Backstage band gives a person no authority to be on stage or in a dressing room unaccompanied; a Stage band gives them access to the deck during changeovers but not to artist private areas. The tier that touches the artist most intimately is All Access, and it requires two signatures specifically because a single signatory can be coerced or careless — two signatures is a friction point designed to be hard to circumvent without collusion.

### 4.3 The Five Checkpoints and Pass-Down Protocol

There are five named checkpoints. Each has a station, a posted checklist, and a designated lead. Pass-down is the procedure by which one checkpoint hands its briefing to the next shift; it is not optional and it is documented.

| # | Checkpoint | Location | Lead | Authority | What they check |
|---|------------|----------|------|-----------|------------------|
| 1 | **Perimeter / Door** | Single backstage entry from the public area | Security Lead | First refusal; calls Head of Security for unresolved matches | Wristband + lanyard match; photo ID check at random intervals |
| 2 | **Credential Office** | Adjacent to Checkpoint 1 | Security Lead | Issue, replace, revoke credentials; maintain live guest list | ID verification; band issuance per guest list; band collection on exit/revocation |
| 3 | **Tour Bus / Hospitality Entry** | Between tour bus area and backstage building | Tour Manager designate | Artist-protection boundary | All Access + matching tour management escort |
| 4 | **Stage Door** | Single stage-entry door, stage-left | Stage Manager or deputy | Performance-time lock-down; SM holds the only spare key during performance | Stage band or All Access only; backstage band during changeover with SM permission |
| 5 | **Pit / Photo Position** | Between FOH and the stage, in the audience area | Publicist + Security Lead | Issued to media only during the published window | Media band + press credential + photo ID; timing window |

**Pass-down protocol — end of each shift:**

1. Outgoing lead briefs incoming lead at the post, in person, for at least 10 minutes. Briefing covers: the guest list status (who is on-site, who is expected, who has been refused and why), any incidents since last pass-down, any artist-management instructions in force, any medical or safety flags.
2. Outgoing lead signs the pass-down log: time, name, briefing content confirmed, signature.
3. Incoming lead counter-signs: time, name, accepted, signature.
4. A copy of the log is filed with Security Lead and with Tour Manager at end of day.

A pass-down that is missed is a post that is unstaffed for that interval, which is a policy violation; documented pass-downs are also the audit trail for any incident.

### 4.4 Guest List Management

The guest list is the master authority on who is allowed past Checkpoint 1. It is **owned by the Tour Manager** end to end — no department can add a name unilaterally, no production assistant can amend it under pressure.

**Guest list entry format (live document, updated in real time):**

```
GUEST LIST — Show Date 2026-08-11 — Venue [name]
Issue time: 14:00    Revocation cutoff: 21:30 (90 min before doors)
Posted to: Security Lead, Credential Office, Checkpoint 1 lead, Tour Manager
┌────┬──────────────┬────────────┬─────────┬──────────┬─────────┬───────────┐
│ #  │ Name         │ Affiliation│ Tier    │ Escort   │ Arrival │ Notes     │
├────┼──────────────┼────────────┼─────────┼──────────┼─────────┼───────────┤
│ 1  │ J. Park      │ Local PD   │ Backstg │ None     │ 18:30   │ Walk-in   │
│ 2  │ R. Singh     │ Family     │ AllAcc  │ T.M.     │ 19:00   │ Escort req│
│ 3  │ C. Yu        │ Mgmt label │ AllAcc  │ Self     │ 17:00   │ —         │
│ 4  │ M. Hassan    │ Press      │ Media   │ Publicist│ 19:30   │ Window    │
└────┴──────────────┴────────────┴─────────┴──────────┴─────────┴───────────┘
```

**Escort requirement.** Any guest marked "Escort" in the list must be met at Checkpoint 1 by the named escort and accompanied at all times. The escort is the All Access holder who assumes responsibility for the guest's behaviour while on-site. A guest who separates from the escort in any backstage area is the escort's responsibility to recover; a guest found unescorted is escorted back to Checkpoint 1 immediately and the incident is logged.

**Late additions** require Tour Manager signature and Security Lead counter-signature, both at the time of addition. Verbal additions by phone are not honoured; the addition is not valid until both signatures are on the list. This rule exists specifically because phone additions are the failure mode by which unauthorised names enter the venue.

**Hard cutoff.** No additions to the guest list after the published cutoff time (typically 90 min before doors). Names received after the cutoff are queued for the next show.

### 4.5 Working With Artist Management Teams

The relationship with the artist's management (often the Tour Manager, sometimes a designated Artist Liaison) is contractual and personal. The technical team's authority over the show is complete; the management team's authority over who touches the artist is also complete. Where the two intersect, the management wins on personnel and the technical team wins on safety.

| Decision | Authority | Constraint |
|----------|-----------|------------|
| Who is on the guest list | Artist management / Tour Manager | Hard cutoff enforced by Security Lead |
| Who escorts a guest past Checkpoint 3 | Artist management | Escort must hold All Access and be named in the list |
| Who enters the dressing room when door is closed | Artist only | No exceptions, including All Access holders |
| Who approaches the artist in any backstage area | Artist + management only | Stage band holders in work areas, never unsolicited approach |
| Photographic / video capture of the artist | Management + Publicist | Per artist contract; never assumed |
| Behaviour of guest in backstage area | Escort (the All Access holder) | Escort is accountable to Security Lead for any incident |
| Safety-relevant access (e.g., a pyro-area check involving an artist) | Technical team | Cannot be overridden by management |

**The pattern that produces incidents.** A guest arrives with implicit artist approval — "the artist said it was OK" — and bypasses the formal guest list because no one wants to refuse the artist's word. The mitigation is unromantic but real: *the formal list is the only authority*. A guest without a list entry is refused at the door regardless of who vouched for them; the post then calls the Tour Manager to either add the name formally or confirm the refusal. This both protects the post from pressure and protects the artist from an unvetted presence.

---

## 5. Monitor World — IEM Setup

### 5.1 Why Monitor World Is a Separate Department

The artist's IEM mix is the only sound the artist hears. The monitor engineer's job is to make that mix correct, and correctness has a definition: the artist can perform the show to the artist's own standard. The failure mode is not "no sound"; the failure mode is "the artist stops the show." The mix is, in the artist's perception, the show.

### 5.2 Wireless IEM System — Shure PSM 1000 (G4 variant)

The touring standard for wireless IEM in 2026 is the **Shure PSM 1000** system, currently shipping in the G4 (4th-generation) variant. The system has the transmitter (P10T), the diversity receiver bodypack (P10R+), and the antenna distribution system (PA421A or PA821A).

| Parameter | Specification | Show relevance |
|-----------|--------------|----------------|
| RF band | G4: 470–636 MHz (region-dependent) **[verify against local regulator]** | Coordinate before purchase; bands differ US/EU |
| Tuning bandwidth | Up to 80 MHz per band | Wide window for frequency coordination |
| Modulation | Shure proprietary, digital | Audio cannot be mistaken for analogue; rejects intermod |
| Channel count | Up to 60 compatible per band, region-dependent | Headcount ceiling for the rig |
| Audio frequency response | 35 Hz – 15 kHz | Sufficient for full-range IEM, bass-light by audiophile standards |
| Dynamic range | > 110 dB A-weighted | Headroom for peaks without compression artefacts |
| Latency, end-to-end | **1.6 ms analogue-in to bodypack-out** | Critical for the IEM rule in §5.8 |
| Transmitter input | Combo XLR/TRS, line level, +24 dBu max | Take a post-fader send from monitor console |
| Bodypack output | 3.5 mm TRS, ~ 75 mW into 32 Ω | Sufficient for most custom moulds and high-driver universals |
| Antenna | Diversity, paddle or active directional | Diversity is required, not optional |
| Encryption | AES-256, optional | Use it for any show where the mix content is confidential |
| Power | Transmitter 100–240 VAC; bodypack runs ~4–6 h on 2 × AA lithium | Battery management is a department unto itself |

### 5.3 Frequency Coordination via Wireless Workbench 6 (WWB6)

Every wireless audio device on a show (mics, IEMs, comms) is a transmitter. Every transmitter is a potential interferer with every other. Coordination is the process of assigning clean frequencies to every device before they go live, with margin for intermodulation products.

**Shure Wireless Workbench 6 (WWB6)** is the industry-standard coordination tool. The workflow:

1. **Inventory all wireless devices** — model, band, serial, channel count. Pull from the show's RF plot.
2. **Scan the venue** — at load-in, with WWB6 on a laptop connected to a Shure Spectrum Manager (or equivalent scanner), run a continuous scan of the show's band for ≥ 30 minutes, including during dimmer check and LED wall energise. Capture every active carrier, including TV, public safety, and any in-house wireless.
3. **Calculate** — WWB6 computes a list of compatible frequencies that maximise the intermod spacing to all known carriers. Typical minimum spacing: ≥ 200 kHz from any TV carrier, ≥ 100 kHz from any other wireless, ≥ 25 kHz of intermod headroom.
4. **Deploy** — programme each transmitter with the assigned frequency. Confirm at the receiver that RF level is in the "strong" zone of the bodypack meter (typically > −60 dBm).
5. **Re-coordinate during the show** — any new carrier that appears (a walkie-talkie from another crew, a TV channel that came back online during a broadcast) requires an immediate re-coord. The RF Coordinator has authority to switch any transmitter to a clean frequency mid-show on instruction from the A2; this is why a hot spare set of frequencies is always calculated and held.

The coordination result file lives with the RF Coordinator and is shared with A1, A2, and the broadcast EIC if applicable.

### 5.4 Wedge Monitor Placement — Geometry Math

When wedges are used (backline, drummer click, talkback, or in addition to IEMs), the placement is geometry, not art. The relationship between the wedge and the microphone that captures the same performer's voice is the single biggest determinant of feedback margin.

**The 3-to-1 rule:** the distance from the wedge to the performer must be **at least 3× the distance from the microphone to the performer's mouth.** For a mic at 10 cm from the mouth, the wedge must be at least 30 cm further from the mouth on the same side.

**The off-axis rule:** the wedge axis must be **135° off-axis from the mic's primary rejection axis.** Practically: the wedge points at the performer's ear from the side; the mic rejects sound arriving from behind. Place the wedge at roughly 45° to the mic's forward axis, on the opposite side from the front of the mic.

**Distance:** with the performer at the mic, the wedge-to-ear distance should be ~**3 m (10 ft)** for a 12" two-way wedge, or **2 m (6.5 ft)** for a 10" coax. Greater distance = more gain-before-feedback; closer = more level at the ear with less power into the room. The exact distance trades SPL at the ear against spill into the house mic.

| Wedge type | Distance from performer | Angle off mic axis | Max SPL at ear (typical) |
|------------|------------------------|---------------------|---------------------------|
| 12" two-way (e.g., Clair 12AM, d&b M2) | 2.5–3.5 m | 135° off mic | 100–105 dB SPL |
| 10" coax (e.g., Yamaha SM10V) | 2.0–2.5 m | 135° off mic | 95–100 dB SPL |
| 15" drum fill | 1.0–1.5 m (drummer only) | Per drummer preference | 100–110 dB SPL |

**The geometry that produces the worst-case feedback:** mic directly in front of the wedge axis, wedge 1 m from the mic. This is the textbook failure case and is also how wedges are positioned on a stage by someone who has not read the manual. The 3-to-1 rule eliminates it.

### 5.5 Ring-Out EQ Procedure

Every wedge mic, on every show, is "rung out" — the EQ is adjusted to notch out the room's primary feedback frequencies so that more gain is available before feedback. The procedure is the same regardless of console; the goal is the same regardless of room.

**Procedure:**

1. **Place mic and wedge** as per §5.4. Performer not present. PFL off. Channel muted.
2. **Bring fader up slowly** — from −∞, in 3 dB steps, at 1-second intervals. The room will feed back; the first 3–5 frequencies to howl are the room modes you must notch.
3. **Identify the first feedback frequency** — use the channel's RTA (most digital consoles have one per channel in 2026; if not, use a separate analyser mic and FFT), or identify by ear and confirm with a measurement mic.
4. **Apply a narrow notch** — Q ≈ 8–10, depth 6–12 dB at the exact feedback frequency. Bring fader up another 3 dB.
5. **Repeat** — the next feedback frequency will be 1–3 dB louder than the first was. Notch it. Bring the fader up another 3 dB.
6. **Continue** until the next feedback frequency is reached at a level that is unacceptable for the performer's mix, or until 3–5 notches have been applied. Five is the typical maximum — beyond that, more notches are indicative of a placement problem, not an EQ problem.

**Acceptance criterion:** the wedge can deliver the performer's required SPL with ≥ 6 dB of gain-before-feedback margin above the ring-out position. Anything less is not safe to leave unattended.

**Critical:** the ring-out is *per mic, per wedge, per position*. Moving a mic 30 cm changes the frequencies. Moving the wedge changes the frequencies. Re-ring after any move.

### 5.6 Personal Mixers — Aviom A360, Behringer P16-M, Midas DL32

Personal monitor mixers let each performer dial their own IEM or wedge mix from a remote location. The choice of system is a touring-decision that touches compatibility, sound quality, and workflow.

| System | Connectivity | Mixers per system | Strength | Weakness |
|--------|--------------|-------------------|----------|----------|
| **Aviom A360** | A-Net (Cat-5e, proprietary) | 64 per ring | Reference standard for personal mixing; analogue-feeling knobs; per-channel EQ, pan, reverb; 16 stereo channels | A-Net is proprietary; cannot mix with non-Aviom consoles without the AN-16/i v.2 input module |
| **Behringer P16-M** | Ultranet (Cat-5e, Behringer proprietary) | 16 per system | Lowest cost; integrates natively with X32 / WING consoles via Ultranet | Ultranet is proprietary to Behringer/Midas; lower build quality; 16 channels can be limiting on complex shows |
| **Midas DL32** | AES50 (HyperMac) + Ultranet output | 16 ULTRANET P16-M outputs per console | Integrates with Midas / Behringer digital console ecosystem; 32 mic preamps on the stage box | Same P16-M mixer limitations on the personal side; large ecosystem lock-in |

**For the show standard in this document — A2 at a WING console — Ultranet to P16-M is the default topology.** The P16-M runs at the artist's position over a single Cat-5e; power is supplied over the same cable. Each artist has 16 channels of personal mix control with EQ, pan, and a master reverb. For shows that need 16+ channels per artist, the Aviom A360 is the upgrade path; it requires an AN-16/i v.2 input module connected to the console's analogue or AES outputs.

### 5.7 IEM Routing — The Show-Floor Rule

> **CRITICAL RULE — IEM MUST USE NATIVE WING PREAMP PATH ONLY. NEVER ROUTE AI/USB-PROCESSED AUDIO TO IEM MIXES.**

**The 7.8 ms comb-filtering problem.** When the same source is summed into a mix from two paths that differ in latency by **7.8 ms** (or any integer multiple of the fundamental), a comb-filter response is produced: deep notches at odd multiples of the inverse delay and peaks at even multiples. 7.8 ms corresponds to ~129 Hz and its harmonics — exactly the vocal fundamental and low-order harmonics. The audible result is a hollowed, phasey, "underwater" vocal that no amount of EQ fixes, because the artefact is the timing.

Where 7.8 ms comes from: in this rig, AI/USB processing on the WING inserts roughly 7.8 ms of additional latency into the channel (FFT block size, plugin graph traversal, USB buffering). The native preamp path is < 1 ms. Summing both into the same IEM mix sums two copies of the same source ~7.8 ms apart, producing the comb filter.

**The rule restated as an action:**

1. IEM mixes are sourced from **WING preamp input → direct output → monitor console IEM bus**, with all AI/USB inserts **bypassed** on the IEM-feed channel.
2. FOH mixes *may* use AI/USB processing — the audience does not hear the comb filter because there is only one path to the PA.
3. If the same console channel feeds both FOH (with AI/USB) and IEM (without), the IEM tap is taken from the **pre-insert send**, not the post-fader channel output. The WING allows this routing; the monitor engineer must verify it on every channel that is sent to IEM.
4. If a touring act arrives with a backing-track channel, the IEM send of that channel is also pre-insert, never from the AI-processed path. The drummer's click and the artist's vocal must both be latency-clean in the IEM.

This rule originates in `01-live-audio-ai/Behringer-WING-Integration.md` ("Critical Rule: IEM Routing Restrictions") and `01-live-audio-ai/AI-Plugins-In-Live-Sound.md` Core Tech 3. It is restated here because the show-floor enforcement is the A2's responsibility, and the A2's first read of this rule is often this section.

### 5.8 Worked Example — 6-Piece Band IEM Setup

A 6-piece touring band: lead vocal, backing vocal / rhythm guitar, bass, drums, keys, percussion. All on IEM, no wedges except a drum sub wedge for the drummer's click + bass feel.

**Step 1 — Channel inventory and mix bus assignment.**

| # | Source | Mic / DI | IEM mix routing (all pre-insert) |
|---|--------|----------|-----------------------------------|
| 1 | Lead vocal | Shure KSM9 (wireless) | All 6 IEM mixes |
| 2 | Backing vocal / rhythm gtr | Shure SM58 (wireless) + DI | All 6 IEM mixes |
| 3 | Bass | DI (Radial J48) | All 6 IEM mixes |
| 4 | Drum OH L | Neumann KM184 | Drummer + keys + BV |
| 5 | Drum OH R | Neumann KM184 | Drummer + keys + BV |
| 6 | Drum kick | Beta 52 | Drummer + bass |
| 7 | Drum snare | SM57 | Drummer |
| 8 | Keys L | DI | Keys + BV + LD |
| 9 | Keys R | DI | Keys + BV + LD |
| 10 | Percussion | SM81 / DI | LD + BV + drummer |
| 11 | Click track | Playback iface → WING input 11 | Drummer only |
| 12 | Backing tracks L | Playback iface → WING input 12 | All 6 mixes |
| 13 | Backing tracks R | Playback iface → WING input 13 | All 6 mixes |
| 14 | Talkback mic | SM58 at monitor world | A2 to any/all mixes |

**Step 2 — RF coordination. **

13 wireless channels in the show (12 performer wireless + talkback). WWB6 coordination run yields 13 clean frequencies with ≥ 200 kHz spacing from the local TV carrier scan. Hot-spare set of 6 frequencies calculated and held in reserve.

**Step 3 — Personal mixer assignment.**

| Performer | Mixer | Mix bus | Notes |
|-----------|-------|---------|-------|
| Lead singer | A360 #1 | IEM-1 | Most clicks of buttons; full Aviom flexibility |
| BV / rhythm | P16-M #2 | IEM-2 | Simpler needs |
| Bassist | P16-M #3 | IEM-3 | Mostly bass, kick, click |
| Drummer | P16-M #4 | IEM-4 + wedge 1 | IEM for mix, wedge for click weight |
| Keys | P16-M #5 | IEM-5 | — |
| Percussion | P16-M #6 | IEM-6 | — |

**Step 4 — Verify pre-insert routing on every channel.**

For channels 1–10, the IEM bus send is tapped from the WING pre-insert direct output, not the post-fader channel. Verify on the WING routing page that the insert is engaged on the FOH path and **disengaged** on the IEM path. This is the §5.7 rule, verified per-channel, per-mix.

**Step 5 — Set initial IEM levels, then refine in soundcheck.**

Start every IEM mix with all sources centred, all faders at −10 dB, master at 0 dB. Bring each source up one at a time on the performer's signal, until each performer has what they need. Lead vocal is almost always the loudest single source in any mix; reverb (typically a hall or plate) on the lead vocal at −12 to −18 dB send. Click track audible to drummer and bassist only, typically 6–10 dB above the drummer's threshold for not noticing it.

**Step 6 — Document and walk through.**

The final mix settings are written down (or screen-captured) per performer per song, because an artist will ask for "what was that on song 3, second chorus, the BV was louder" and the answer must be in the file. The IEM mix snapshot lives with the show file for the tour.

**Summary table — IEM rig at a glance:**

| Subsystem | Choice | Reason |
|-----------|--------|--------|
| Wireless IEM | Shure PSM 1000 G4 | Touring standard, AES-256 encryption option, low latency |
| RF coordination | Shure WWB6 | Industry standard, scan + calculate + deploy |
| Console | Behringer WING (per show context) | Integrates with P16-M via Ultranet |
| Personal mixers | Aviom A360 for LD, P16-M for rest | Headliner gets the better tool, side-musics get cost-effective reliability |
| IEM routing rule | Pre-insert tap on every IEM bus send | Avoids 7.8 ms comb-filter artefact from AI/USB inserts |
| Wedges | Drummer's 12" two-way, click + bass | Geometry: 3 m off-axis 135° from kick mic |
| Talkback | SM58 at monitor world, all-mix override | A2 can address any artist from A2 position |

---

## 6. Show Cue Protocol

Show cues coordinate action across departments. The cue sheet is the single source of truth — every department reads from the same document, every cue has a number, and the show caller fires cues in order.

### 6.1 Cue Sheet Format

| Column | Content | Example |
|--------|---------|---------|
| Cue # | Unique sequential number per department | LX 12, SQ 5, VID 3, PYRO 2 |
| Department | Prefix identifying who executes | LX = Lighting, SQ = Sound, VID = Video, PYRO = Pyro, SFX = Special Effects |
| Page # | Position in the calling script | P 4 / 17 |
| Trigger | What fires the cue (TC time, lyric, action) | "TC 01:23:15:00", "End of song 3" |
| Description | What the cue does (one line) | "House to 0, spots up on lead singer" |
| Standby | How many seconds before GO the standby is called | "LX 12 standby... 5... 4... GO" |
| Backup | Plan B if cue misses | "Manual GO from board op if no response" |
| Owner | Who confirms execution | LD on comms confirms LX cues fire |

### 6.2 Numbering Convention

**Block numbering by department, sequential within show:**
- LX 1–99: Lighting cues act 1
- LX 100–199: Lighting cues act 2
- SQ 1–99: Sound cues (track starts, mic on/off)
- VID 1–99: Video cues (roll clip, switch camera)
- PYRO 1–9: Pyrotechnic cues (each one is a permit, one chance only)

**Why block-of-100:** Easy to read on comms ("LX 47 GO") without ambiguity. Cue numbers don't repeat between acts because the prefix alone doesn't disambiguate.

### 6.3 Comms Channel Assignments

Comms are the show's nervous system. Standard touring rig uses **Clear-Com FreeSpeak II** digital wireless with beltpacks.

| Channel | Users | Purpose |
|---------|-------|---------|
| 1 — Production | SM, Producer, Director | All-department coordination |
| 2 — Audio | A1, A2, A2.2 | FOH ↔ Monitor ↔ Playback |
| 3 — Lighting | LD, L2, Board Op | Lighting dept internal |
| 4 — Video | V1, V2, Camera Ops | Video dept internal |
| 5 — Stage | SM, A2 (stage side), STR, Talent | Stage talent coordination |
| 6 — Pyro | PYRO, RIG, SM | Pyro safety net (always-on) |
| 7 — Security | SEC, venue security | Medical, security, evacuation |

**Protocol:** Channel is open during the show. "GO" confirms execution. "Standby" gives 5-second warning. "Hold" stops the cue mid-flight.

### 6.4 Standby / GO Procedure

**Standby** is called once, 5 seconds before the cue. Departments prepare.

**GO** is called at the exact trigger point. Department executes.

**Hold** stops the cue. Used when:
- Talent is in wrong position
- Previous cue didn't complete
- Safety concern (someone in pyro zone)
- Audience member issue (flash photo during black-out)

**Confirmation:** Each department confirms back on comms after executing ("LX 12 GO confirmed"). If no confirmation in 2 seconds, SM asks for status.

### 6.5 Pre-Show Comms Check

**T-2h:** All beltpacks powered, batteries >75%, channels assigned.

**T-30min:** SM calls each department by name, department confirms receipt. Test "standby" + "GO" round-trip.

**T-5min:** SM confirms standby with A1, V1, LD, PYRO one last time. Show is "hot" — no further changes accepted.

---

## 7. Failure Modes — Live Entertainment

| # | Scenario | Probability | Impact | Plan B Protocol | Decision Maker | Recovery Time |
|---|---------|------------|--------|-----------------|----------------|---------------|
| 1 | TC master generator fails | Low (1%) | All sync lost, audio/lighting/video drift | Backup generator (LTC source from DAW); manually re-jam each system | A1 + SM | 30–60 sec |
| 2 | Primary playback machine crashes | Medium (5% per show) | Backing tracks stop | Watchdog auto-switches to backup within 2 sec | A1 | <2 sec |
| 3 | Backup playback machine also fails | Very low (<1%) | No playback | FOH engineer manually plays click + covers tracks live; musicians continue with reduced arrangements | A1 + MD | 5–10 sec to acknowledge, then show continues without tracks |
| 4 | IEM transmitter fails mid-song | Low (2% per artist) | That artist's IEM drops | Spare transmitter pre-rigged on same freq; beltpack scan-and-lock; or hard-wire to wedge | A2 | 15–30 sec |
| 5 | FOH console crash | Very low (<1% per show) | Total PA loss | Backup console pre-rigged, hot-swap from FOH to backup | A1 + SM | 30–60 sec |
| 6 | Wedge feedback run-away | Medium (5%) | Howl from wedge, distorts PA | Ring-out EQ procedure; reduce wedge level 6 dB; or kill wedge and route artist to IEM | A2 | 10–20 sec |
| 7 | Monitor world console crash | Very low (<1%) | All IEMs/wedges drop | Backup console pre-rigged at monitor world | A2 | 30–60 sec |
| 8 | LED wall tile failure | Low (2%) | Visible black panel | Backup tiles pre-staged (not swapped mid-show); redirect cameras to avoid dead panel | V1 | Show continues with defect |
| 9 | Media server crash | Low (2%) | Video freezes or goes black | Backup server (disguise gx 2c main + backup standard practice); auto-failover within 3 sec | V1 | <3 sec |
| 10 | Pyrotechnic cue misfires (premature) | Very low (<1% per cue) | Pyro fires at wrong moment | E-stop from PYRO via dedicated kill switch; SM calls "hold" on subsequent cues | PYRO + SM | <1 sec to e-stop |
| 11 | Pyrotechnic cue fails (no fire) | Low (3%) | Expected effect missing | Visual cue already happened, lighting covers; backup pyro charge for next song if critical | LD | Show continues |
| 12 | Performer injury on stage | Low (1% per show) | Show pauses for medical | MED responds within 15 sec; show pauses or continues with reduced set | MED + SM | 15–60 sec to assess |
| 13 | Audience medical emergency | Medium (varies) | Section cleared, show pauses | MED + SEC coordinate; show pauses for 5–10 min or continues with section dark | MED + Producer | 5–10 min |
| 14 | Fire alarm | Very low (<1%) | Mandatory evacuation | Stop show, EVACUATE, do not override | Venue Fire Authority | Immediate |
| 15 | Power loss (single circuit) | Medium (3%) | Affected equipment drops | Switch to backup circuit (transfer switch); UPS bridges the gap | R1 + EIC | <1 sec (UPS) |
| 16 | Total power loss (venue) | Very low (<1%) | Everything stops | House lights on UPS, evacuate calmly via emergency lighting; restart generator or wait for utility | Venue Management | 2–10 min |
| 17 | Network failure (Dante / Art-Net) | Low (2%) | Digital snakes or lighting network drop | Backup analog snake run in parallel; lighting triggers from console internal cue list (no network needed) | A1 + LD | 30–60 sec |
| 18 | Comms failure (single channel) | Low (3%) | Department goes silent | Move to backup channel (pre-assigned); use hand signals if necessary | SM | 30 sec to switch |
| 19 | RF interference on wireless mics | Medium (5%) | Static / dropouts / dead mic | Switch to backup freq (pre-coordinated); reduce number of simultaneous channels | A1 | 5–15 sec |
| 20 | Lighting console crash | Very low (<1%) | Lights freeze or go dark | Backup console (grandMA3 main + onPC backup); manual submasters can hold last look | LD | 15–30 sec |

### 7.1 Tier-1 Failure Response Protocol

For any failure that affects the audience experience, follow this protocol:

1. **Acknowledge** (0–5 sec): Department identifies the problem on comms
2. **Stabilize** (5–15 sec): Apply immediate Plan B to stop bleeding (mute bad channel, trigger backup, etc.)
3. **Diagnose** (15–60 sec): Determine root cause while show continues
4. **Communicate** (continuous): SM updates all departments on status
5. **Resolve** (60 sec+): Apply permanent fix (swap gear, change routing, etc.)
6. **Document** (post-show): Log incident in post-show report

### 7.2 The "Never Override" List

These scenarios have NO Plan B in the production's authority:

- **Fire alarm** — venue/fire authority decides re-entry
- **Building structural issue** — venue management decides
- **Credible security threat** — law enforcement decides
- **Performer medical emergency** — medical professionals decide

Production team supports, but does not override the authority having jurisdiction.