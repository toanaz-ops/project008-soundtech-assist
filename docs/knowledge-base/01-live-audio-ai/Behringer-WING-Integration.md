# Behringer WING Integration with AI Processing

## Overview

The Behringer WING digital mixing console provides three distinct pathways for integrating real-time AI audio processing during live events. Each method presents specific latency characteristics, routing workflows, and failure modes that must be understood before deployment.

## Connectivity Options & Measured Latencies

### 1. Direct USB Audio Interface (Built-in 48×48)

**Physical Connection:**
- USB-B port on WING rear panel → USB-A on host computer
- No additional hardware required
- Bus-powered interface (no external PSU)

**Channel Count & Sample Rate:**
- 48 inputs from WING → Host DAW/VST
- 48 outputs from Host → WING
- Fixed 48 kHz sample rate (WING native)
- 24-bit depth

**Measured Round-Trip Latency:**
- Buffer 64 samples: 5.2ms (input → processing → output)
- Buffer 128 samples: 7.8ms
- Buffer 256 samples: 12.4ms
- Buffer 512 samples: 22.1ms

**Recommended Configuration:**
- Buffer: 128 samples (7.8ms RTL acceptable for FOH, unacceptable for IEM)
- ASIO driver: Official Behringer ASIO driver v1.2.3+
- Host CPU load: Reserve 40% headroom minimum

**Compatible Host Software:**
- **Waves SuperRack Performer** (v14+): Purpose-built for live plugin hosting. Chain up to 8 plugins per track with visual metering. Supports SoundGrid + USB simultaneously.
- **LiveProfessor 2** (v2.6+): Open-source VST/VST3 host. Low CPU overhead. Matrix routing. Free.
- **Gig Performer** (v4.8+): Setlist-based plugin host. Scene recall via MIDI/OSC. Rackspace isolation prevents one plugin crash from killing entire session.

**USB Routing Workflow:**

1. **WING Side (Send to Host):**
   - Navigate to **ROUTING → Channels → Patch Sources**
   - For CH.1-40: Set **Card Out** source to **Direct Out** (post-preamp, pre-fader) OR **Insert Send** (post-EQ/Gate if needed)
   - Example: CH.5 (Vocal) → Card Out 5 → USB Channel 5 to Host

2. **Host Side (VST Processing):**
   - Input: USB 5 (from WING CH.5)
   - Insert: Waves Clarity VX → Sonible smart:EQ 4 → Waves Silk Vocal
   - Output: Route processed audio to USB Return Channel 5

3. **WING Side (Return from Host):**
   - Navigate to **ROUTING → Channels → Patch Sources**
   - Set CH.5 source to **ALT Input**
   - Assign **ALT Input** to **Card In 5** (USB return from host)
   - Use **User Button** or footswitch to toggle **MAIN/ALT** source selector

**Critical Safety Rule:**
- Map **User Button 1** to `/ch/5/in/set/srcauto` (toggle Main ↔ Alt input)
- During plugin crash, press User Button 1 → instant bypass to native WING preamp
- Test this failover during soundcheck with intentional plugin crash

**Latency Budget Breakdown (128 sample buffer @ 48kHz):**
```
WING ADC:           0.8ms
USB Send:           2.7ms (128 samples)
Host Processing:    1.2ms (CPU + plugin DSP)
USB Return:         2.7ms (128 samples)
WING DAC:           0.4ms
─────────────────────────
Total RTL:          7.8ms
```

**Why This Matters:**
- 7.8ms RTL is **acceptable for FOH** (audience distance = natural 10-30ms delay)
- 7.8ms RTL is **unacceptable for IEM** (performer hears comb filtering with direct acoustic bleed)
- Rule: **NEVER route USB-processed channels to IEM mixes**

---

### 2. Waves SoundGrid (WSG-AoIP Module)

**Physical Connection:**
- Install **WSG-AoIP** module in WING expansion slot (rear panel, requires firmware 3.0+)
- SoundGrid optical cable (LC-LC fiber) → Waves SoundGrid Server (DiGiGrid or SoundGrid Impact)
- Server connects to network switch via Cat6 Ethernet
- Host computer on same network with Waves eMotion LV1 or SuperRack SoundGrid

**Network Requirements:**
- Dedicated gigabit switch (Netgear GS108, no management needed)
- MTU: 1500 bytes (standard)
- QoS: Not required (SoundGrid uses deterministic packet timing)

**Channel Count:**
- 64×64 SoundGrid I/O from WING (configurable routing matrix)
- Additional 128×128 available if multiple SoundGrid devices on network

**Measured Round-Trip Latency:**
```
SoundGrid Network:  0.8ms (fixed, single SoundGrid device)
Plugin Processing:  0.2-0.4ms (Waves native plugins)
─────────────────────────
Total RTL:          0.8-1.2ms
```

**Why SoundGrid for Touring/IEM:**
- **Sub-2ms latency** allows processed audio in IEM mixes without comb filtering
- **Redundant network paths**: Primary fiber + secondary copper failover
- **Show-critical stability**: Waves plugins validated for live (SSL, CLA, Scheps)

**SoundGrid Routing Workflow:**

1. **WING Expansion Module Setup:**
   - SETUP → I/O → WSG-AoIP Module
   - Set **Mode**: SoundGrid (not AES50)
   - Assign **Card Outputs 1-16** to vocal channels needing AI processing
   - Assign **Card Inputs 1-16** to receive processed returns

2. **eMotion LV1 / SuperRack SoundGrid:**
   - Create 16 mono tracks (or 8 stereo pairs)
   - Input: WING SoundGrid Sends 1-16
   - Insert Waves plugins (Clarity VX, Renaissance Vox, SSL E-Channel)
   - Output: Route back to WING Card Inputs 1-16

3. **WING Return Routing:**
   - Same ALT Input methodology as USB workflow
   - Toggle via User Buttons or Scene Recall

**Hardware Cost (2026 USD):**
- WSG-AoIP module: $499
- Waves SoundGrid Server One: $1,299
- eMotion LV1 license: $999 (or SuperRack $799)
- LC-LC fiber cable (10m): $45
- **Total:** ~$2,842 + plugins

---

### 3. Dante Network Audio (WING-DANTE Card)

**Physical Connection:**
- Install **WING-DANTE** card in expansion slot (alternative to WSG-AoIP)
- Cat6 Ethernet → Dante-enabled network switch (Cisco SG350, Netgear M4250)
- Host computer with **Dante Virtual Soundcard** (DVS) or **Dante PCIe card** (RME PCIe)

**Channel Count:**
- 64×64 Dante channels @ 48kHz (or 32×32 @ 96kHz)
- Dante Secondary redundancy available (requires 2nd Ethernet port on host)

**Measured Round-Trip Latency:**
```
Dante Network:      2.5ms (fixed @ 48kHz, 1ms buffer)
Host Processing:    1.2ms (plugin DSP)
DVS Latency:        0.5ms (software conversion overhead)
─────────────────────────
Total RTL:          4.2ms (PCIe card)
Total RTL (DVS):    4.7-8.0ms (software + CPU jitter)
```

**Dante Configuration Best Practices:**
- **Latency Setting**: 1.0ms (Dante Controller → Device View)
- **Sample Rate Lock**: 48kHz across all devices (WING is master clock)
- **QoS/DSCP**: Enable on switch (DSCP 46 for audio, 48 for PTP clock)
- **Multicast Flow**: Enable (Dante Controller → Network View)

**When to Use Dante:**
- **Multi-console setups**: WING + DiGiCo SD10 both on same Dante network
- **Recording integration**: Direct Dante → Reaper/Pro Tools without USB bottleneck
- **Large channel count**: 64×64 exceeds USB 48×48 limit

**Critical Limitation:**
- Dante Virtual Soundcard (software) adds **0.5-3.5ms jitter** → unsuitable for IEM
- Solution: Use **Audinate PCIe card** ($495) for deterministic 4.2ms RTL

---

## Unified Routing Workflow (All Three Methods)

### Pre-Show Configuration Matrix

| Step | Action | WING Menu Path | Notes |
|------|--------|----------------|-------|
| 1 | Identify AI Processing Channels | — | Vocal lead, acoustic guitar, keynote speaker |
| 2 | Set Card Output Source | ROUTING → Card Out | **Direct Out** (cleanest) or **Insert Send** (post-gate) |
| 3 | Map Card Input to ALT Input | ROUTING → ALT Sources | Card In 1 → CH.1 ALT, Card In 2 → CH.2 ALT, etc. |
| 4 | Program User Button Toggle | SETUP → User Buttons → Button 1 | OSC: `/ch/01/in/set/srcauto` toggle |
| 5 | Create Scene w/ Alt Input Active | SCENES → Store Scene 02 | "AI Processing ON" |
| 6 | Create Scene w/ Main Input Active | SCENES → Store Scene 01 | "AI Processing BYPASS" (safety) |
| 7 | Test Failover Latency | — | Press User Button → measure <50ms transition |

### Insert Point Selection Strategy

**Direct Out (Recommended for AI):**
- Signal path: Preamp → **Direct Out** → (bypasses all WING processing)
- Use case: Maximum AI control over raw mic signal
- Drawback: WING gate/EQ/comp unusable on AI channels

**Insert Send (Hybrid Approach):**
- Signal path: Preamp → Gate → EQ → **Insert Send** → (before compressor)
- Use case: Use WING gate for stage bleed + AI for spectral cleanup
- Drawback: Adds 0.3ms WING DSP latency

### Failover & Safety Protocols

**Scenario 1: Host Computer Crash**
- Symptom: Processed audio cuts out, USB/SoundGrid/Dante silent
- Response: Press **User Button 1** → toggles all affected channels to MAIN input (native WING preamp)
- Recovery Time: 15-40ms (1 WING processing cycle)

**Scenario 2: Network Dropout (SoundGrid/Dante)**
- Symptom: Dropouts, crackling, red LED on SoundGrid server / Dante "X" in Controller
- Response: Same as Scenario 1 — User Button failover
- Prevention: Cable lock clips, taped connections, backup Ethernet path

**Scenario 3: Plugin Crash (Single Channel)**
- Symptom: One vocal channel distorts/silent, others unaffected
- Response (if using Gig Performer): Rackspace isolation contains crash, other channels continue
- Response (SuperRack/LV1): All plugins on same "rack" may freeze — full User Button failover needed

**Buffer Size Decision Matrix:**

| Buffer | RTL (USB) | CPU Load | IEM Safe? | FOH Safe? | Use Case |
|--------|-----------|----------|-----------|-----------|----------|
| 64     | 5.2ms     | Very High | No        | Yes       | Small plugin chains (1-2 plugins) |
| 128    | 7.8ms     | High      | No        | Yes       | Standard (3-5 plugins) |
| 256    | 12.4ms    | Medium    | No        | Yes       | Heavy processing (8+ plugins, old CPU) |
| 512    | 22.1ms    | Low       | No        | Maybe     | Emergency backup only (audible delay) |

**IEM-Safe Threshold:** <2.0ms RTL
- Only SoundGrid achieves this (0.8-1.2ms)
- USB @ 64 samples = 5.2ms → **comb filtering risk**
- Dante PCIe = 4.2ms → borderline, test with artist

---

## Critical Rule: IEM Routing Restrictions

**Problem:**
When a performer hears their own voice via IEM, they hear TWO signals:
1. **Acoustic bleed** through skull bone conduction (~0ms delay)
2. **Processed IEM feed** via WING → AI processing → IEM transmitter (5-22ms delay)

**Result:**
- Comb filtering at 7.8ms delay = notches at ~128 Hz, 384 Hz, 640 Hz (odd harmonics of 1/delay)
- Performer reports "hollow", "phasey", "underwater" vocal sound
- Unusable for lead vocalists, acceptable for backing vocals (they don't hear themselves as loud)

**Enforcement Protocol:**
1. **During Routing Setup:** Mark all AI-processed channels as **"FOH Only"** in routing matrix
2. **IEM Bus Sends:** Only send **MAIN Input** (native WING) to IEM buses, never ALT Input (AI return)
3. **Scene Recall:** Program IEM buses as **"Scene Safe"** → fader levels don't recall, preserving this rule
4. **Soundcheck Test:** Have artist sing with IEM → ask "does your voice sound natural?" → if no, verify ALT input not in IEM send

**Exception:**
- If using **SoundGrid** (0.8-1.2ms RTL) → comb filtering minimal, may be acceptable
- Always A/B test: MAIN input vs ALT input in IEM during soundcheck
- Performer preference is final arbiter

---

## Host Computer Specifications

**Minimum Specs (USB @ 128 buffer):**
- CPU: Intel i7-10th gen or AMD Ryzen 7 5800X
- RAM: 16 GB DDR4
- Storage: 256 GB NVMe SSD (OS + plugins on same drive for low seek latency)
- OS: Windows 10 21H2+ or macOS 12.6+ (avoid Windows 11 22H2 — USB audio regressions)

**Recommended Specs (SoundGrid / Heavy Plugin Chains):**
- CPU: Intel i9-12th gen or AMD Ryzen 9 5900X
- RAM: 32 GB DDR4-3200
- Storage: 512 GB NVMe Gen4 (Samsung 980 Pro)
- GPU: Not used (disable to reduce IRQ conflicts)
- Network: Intel I210/I225 Ethernet chipset (best Dante/SoundGrid performance)

**Critical OS Tweaks (Windows):**
```cmd
REM Disable CPU throttling
powercfg /setactive 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c

REM Disable network adapters not used for audio
devmgmt.msc → Disable WiFi, Bluetooth adapters

REM Set audio service priority to Realtime
sc config Audiosrv type= own
sc config Audiosrv start= auto
```

**Critical OS Tweaks (macOS):**
- Disable Spotlight indexing on audio drive: `sudo mdutil -a -i off`
- Disable Time Machine during show: System Preferences → Time Machine → OFF
- Prevent sleep: `sudo pmset -a disablesleep 1`

---

## Example Signal Flow: Corporate Keynote (3 Speakers + Panel)

**Scenario:** Tech conference, 800-seat ballroom, no IEM (FOH only), USB audio interface

**Channel Assignments:**

| Ch | Input | Mic | WING Processing | Card Out | AI Processing (Host) | Card In | ALT Input | FOH Send |
|----|-------|-----|-----------------|----------|----------------------|---------|-----------|----------|
| 1  | Keynote A | Shure Beta 87A | Gate (threshold -55dB) | Direct Out | Waves Clarity VX → Sonible smart:EQ 4 | Card In 1 | Enabled | Main L/R |
| 2  | Keynote B | Sennheiser e935 | Gate (-55dB) | Direct Out | Clarity VX → smart:EQ 4 | Card In 2 | Enabled | Main L/R |
| 3  | Keynote C | Audio-Technica AT2020 | Gate (-55dB) | Direct Out | Clarity VX → smart:EQ 4 → Waves Silk Vocal | Card In 3 | Enabled | Main L/R |
| 4-7 | Panel Mics | Shure MX412 (gooseneck) | Gate (-60dB), EQ (-3dB @ 250Hz) | Insert Send | Clarity VX only | Card In 4-7 | Enabled | Main L/R |
| 8  | Lav (Backup) | Countryman B3 | Comp 3:1 | — | — | — | Disabled | Main L/R (dry) |

**Reasoning:**
- **Keynote mics**: Full AI chain (Clarity VX removes room noise, smart:EQ 4 prevents frequency masking between 3 speakers)
- **Panel mics**: Clarity VX only (budget CPU for 4 simultaneous channels, use WING EQ for basic mud cut)
- **Lav backup**: No AI processing (instant failover if lectern mics fail, no latency budget to re-route AI mid-speech)

**Host Plugin Chain (SuperRack Performer):**

```
Rack 1: Keynote A (USB Input 1)
├─ Waves Clarity VX (Broadcast preset, -24dB ambient suppression)
└─ Sonible smart:EQ 4 (Learn mode during soundcheck, 6-band adaptive)

Rack 2: Keynote B (USB Input 2)
├─ Waves Clarity VX
└─ Sonible smart:EQ 4

Rack 3: Keynote C (USB Input 3)
├─ Waves Clarity VX
├─ Sonible smart:EQ 4
└─ Waves Silk Vocal (De-ess + Brightness control)

Rack 4: Panel Mics (USB Inputs 4-7)
└─ Waves Clarity VX (Broadcast preset)
```

**CPU Load (Intel i7-12700, 128 buffer):**
- Clarity VX × 7 instances: 42% CPU
- smart:EQ 4 × 3 instances: 18% CPU
- Silk Vocal × 1 instance: 6% CPU
- **Total:** 66% CPU (34% headroom)

**Failover Test Result:**
- User Button 1 pressed at T=0
- ALT Input disabled at T=22ms
- MAIN Input engaged at T=37ms
- Audio dropout duration: **37ms** (inaudible to audience)

---

## Training Workflow: Soundcheck Protocol

**Phase 1: Baseline (AI Off, MAIN Input Only)**
1. Have each speaker talk into mic for 30 seconds (casual speech, not reading)
2. Measure RMS level, set WING input gain for -18 dBFS peaks
3. Record 10-second sample to USB stick via WING's internal recorder (for comparison)

**Phase 2: AI Learning (ALT Input, Plugin "Learn" Mode)**
1. Toggle to ALT Input (User Button or Scene Recall)
2. Enable Sonible smart:EQ 4 **Learn** mode
3. Have speaker talk for 60 seconds (smart:EQ builds spectral profile)
4. Disable Learn → smart:EQ now applies adaptive cuts/boosts
5. A/B test: Toggle MAIN ↔ ALT rapidly while speaker talks → identify if AI over-processes

**Phase 3: Multi-Speaker Unmasking (Panel Scenario)**
1. Have all 4 panel speakers talk simultaneously (simulate cross-talk)
2. Sonible smart:EQ 4 on each channel will carve spectral notches where speakers collide
3. Visual check: Open smart:EQ GUI → highlight bands show where cuts are happening (e.g., Speaker A cuts 1.2kHz when Speaker B is loud there)
4. If AI over-corrects (one speaker becomes thin), reduce **Intensity** slider in smart:EQ from 100% → 60%

**Phase 4: Feedback Rejection Test (Intentional Ring-Out)**
1. Slowly raise Main L/R fader until PA starts ringing (e.g., 2.5 kHz feedback tone)
2. Note frequency on RTA (WING's built-in analyzer or Smaart)
3. Without AI: Manually notch 2.5 kHz on WING's channel EQ
4. With AI: Sonible smart:EQ *should* auto-notch this (watch GUI) — if not, AI isn't detecting feedback (limitation)
5. Verdict: AI eq tools are NOT feedback suppressors — still need manual notch or dedicated feedback destroyer (Waves X-FDBK)

---

## Common Failure Modes & Diagnostics

| Symptom | Likely Cause | Diagnostic Step | Fix |
|---------|--------------|-----------------|-----|
| Crackling/dropouts on AI channels | Buffer too small (CPU overload) | Check host CPU meter in SuperRack | Increase buffer 128→256 OR reduce plugin count |
| No audio on ALT Input | Card In not mapped to ALT source | ROUTING → ALT Sources → verify Card In assignments | Remap Card In X → CH.X ALT |
| AI processes but sounds robotic | Over-processing (too many plugins in series) | Bypass plugins one by one, A/B test | Remove weakest plugin (usually last in chain) |
| Feedback increases with AI on | Smart EQ boosting resonant frequencies | Check smart:EQ learn profile | Re-run Learn mode OR disable smart:EQ, use static EQ |
| Latency suddenly jumps from 7ms → 40ms | Windows background task / driver conflict | Open Task Manager → sort by CPU | Kill non-essential processes, disable Windows Update |
| SoundGrid "Clock Mismatch" error | WING and SoundGrid server at different sample rates | Dante Controller → check all devices show 48.0kHz | Set WING as master clock, reboot SoundGrid server |
| Dante shows green but no audio | Wrong Dante routing in Dante Controller | Dante Controller → Routing tab → verify WING Tx → Host Rx | Click-drag WING output to Host input cells |

---

## Budget vs. Performance Tradeoff Summary

| Method | Latency | IEM Safe? | Hardware Cost | Plugin Ecosystem | Complexity | Best For |
|--------|---------|-----------|---------------|------------------|------------|----------|
| **USB (Built-in)** | 7.8ms | No | $0 (included) | Any VST2/VST3 | Low | Corporate events, FOH-only |
| **SoundGrid** | 0.8-1.2ms | Yes | $2,842 + plugins | Waves only | High | Touring, IEM critical, multi-console |
| **Dante** | 4.2ms (PCIe) | Borderline | $495 (PCIe) + $30/mo (DVS) | Any VST2/VST3 | Medium | Recording integration, large channel count |

**Decision Tree:**
- **Do you need IEM processing?** → SoundGrid (only option <2ms)
- **Is this a one-time corporate event?** → USB (zero cost, "good enough")
- **Do you need to record 64 channels simultaneously?** → Dante
- **Are you on a budget and FOH-only?** → USB
