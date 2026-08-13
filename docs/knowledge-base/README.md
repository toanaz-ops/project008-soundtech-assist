# Live Event Engineering Knowledge Base

**Version:** 1.0.0
**Last Updated:** 2026-08-11
**Scope:** Behringer WING integration, AI-assisted live audio, event operations, technical specifications

---

## Purpose

This knowledge base consolidates domain expertise for **AI-augmented live event production**, spanning three disciplines:

1. **Live Audio Engineering** — Behringer WING console integration with real-time AI processing plugins
2. **Event Operations** — Run-of-show execution, crisis protocols, crew management
3. **Technical Specifications** — Riders, risk matrices, equipment standards

It serves as the authoritative reference for the WING Scene Parser project and future live-event tooling.

---

## Directory Structure

```
docs/knowledge-base/
├── README.md                          ← You are here
├── 01-live-audio-ai/
│   ├── Behringer-WING-Integration.md
│   └── AI-Plugins-In-Live-Sound.md
├── 02-event-ops-framework/
│   ├── Core-Skills-Overview.md
│   └── Open-Source-Playbooks-Reference.md
├── 03-event-type-sops/
│   ├── Corporate-B2B-Events.md
│   ├── Tech-Expos-Hackathons.md
│   └── Live-Entertainment-Shows.md
└── 04-templates-and-matrices/
    ├── Master-Run-Of-Show-ROS.md
    ├── Technical-Rider-Spec.md
    └── Risk-Contingency-Matrix.md
```

---

## 01 — Live Audio AI

### [Behringer-WING-Integration.md](01-live-audio-ai/Behringer-WING-Integration.md)

Three connectivity pathways for routing WING channels through AI processing hosts, with measured latency budgets and failover protocols.

| Method | Round-Trip Latency | IEM Safe? | Hardware Cost |
|--------|-------------------|-----------|---------------|
| Direct USB (48×48 built-in) | 5.2–22.1ms | No | $0 |
| Waves SoundGrid (WSG-AoIP) | 0.8–1.2ms | Yes | ~$2,842 |
| Dante (WING-DANTE card) | 4.2ms (PCIe) | Borderline | $495+ |

**Key contents:**
- Latency breakdown per buffer size (64/128/256/512 samples)
- Routing workflow: Direct Out → Card Out → Host VST → Card In → ALT Input
- User Button failover mapping (`/ch/{n}/in/set/srcauto`)
- **Critical rule:** Never route USB-processed channels to IEM mixes (comb filtering at 7.8ms)
- Host computer specs and OS tuning (Windows/macOS)
- Worked example: Corporate keynote with 3 speakers + 4 panel mics
- Soundcheck protocol (4 phases: baseline → AI learning → unmasking → feedback test)
- Failure-mode diagnostics table

### [AI-Plugins-In-Live-Sound.md](01-live-audio-ai/AI-Plugins-In-Live-Sound.md)

Four core AI technologies validated for live use, with training-data mechanisms, inference pipelines, and commercial plugin specifications.

| Technology | Representative Plugin | Latency | Gain/Improvement |
|-----------|----------------------|---------|------------------|
| Feedback & resonant peak detection | Waves X-FDBK | 0.8ms | +8 dB gain-before-feedback |
| Real-time frequency unmasking | Sonible smart:EQ 4 | 1.5ms | Spectral separation of colliding sources |
| Neural stage-bleed suppression | Waves Clarity VX | 64ms | 18–24 dB bleed reduction |
| Smart auto-gain & dynamic balancing | Dugan/WING Automix | <5ms | Consistent NOM across open mics |

**Key contents:**
- FFT analysis parameters and classifier thresholds per technology
- Measured A/B test results with blind listening panels
- Acoustic teaching moments (polar patterns, off-axis rejection math)
- CPU budget management and instance limits
- Engineer skill development: data interpretation, acoustic profiling, critical A/B auditing

---

## 02 — Event Operations Framework

### [Core-Skills-Overview.md](02-event-ops-framework/Core-Skills-Overview.md)

The six competencies that define a principal live event engineer.

**Covers:**
- Master Run of Show minute-by-minute execution
- AV/IT signal flow (HDMI/SDI routing, confidence monitors, backup switchers)
- FOH management (gain staging, monitor workflow, DCA grouping)
- Microphone spectral routing (polar patterns, frequency-based assignment)
- Stage management (cueing protocol, backstage flow, green room timing)
- Live crisis protocol (zero-latency failovers for audio/video loss, speaker overruns, emergencies)

### [Open-Source-Playbooks-Reference.md](02-event-ops-framework/Open-Source-Playbooks-Reference.md)

Battle-tested community playbooks, with direct references to source repositories.

| Source | Repository | Primary Value |
|--------|-----------|---------------|
| CNCF Event Playbook | `cncf/foundation` | KubeCon-scale specs, speaker management, venue requirements |
| Awesome Event Organizing | `python-organizers/awesome-organizing` | Checklists, budget templates |
| DevOpsDays Guidelines | `devopsdays/devopsdays-web` | Team structure (Logistics/Program/Sponsors), timeline templates |
| Mozilla Event Checklist | Mozilla wiki | Risk management, accessibility, attendee experience |

---

## 03 — Event Type SOPs

Standard operating procedures differentiated by event class. Each SOP includes equipment specifications, step-by-step workflows, and event-specific failure modes.

### [Corporate-B2B-Events.md](03-event-type-sops/Corporate-B2B-Events.md)

**Defining constraints:** Presentation reliability over sonic perfection; speakers are non-technical.

- Speaker Ready Room protocol (60-minute buffer, slide/codec/font verification)
- Dual-laptop redundancy via Barco Pulse or Roland V-8HD switcher, Master Clicker with dual receivers
- Projector lumen requirements by room capacity
- Lectern and lavalier microphone selection, wireless frequency coordination
- Speaker overrun handling and cue light protocol

### [Tech-Expos-Hackathons.md](03-event-type-sops/Tech-Expos-Hackathons.md)

**Defining constraints:** Live demos fail 30–40% of the time; network is the critical path.

- Live Demo Protocol with mandatory pre-recorded 1080p fallback (OBS capture specs)
- Three-VLAN network segmentation: AV/Stream, Speaker Demo, Public Wi-Fi (with switch CLI examples)
- Wi-Fi density calculations for 200/500/1000 participants
- Multi-camera streaming infrastructure and backup recording
- Sponsor booth power and network provisioning

### [Live-Entertainment-Shows.md](03-event-type-sops/Live-Entertainment-Shows.md)

**Defining constraints:** Timecode is law; rigging is life-safety.

- SMPTE timecode sync architecture across FOH/DAW/lighting/visuals (LTC distribution, frame rates, drift tolerance)
- Playback redundancy with MIDI/OSC watchdog failover
- Rigging safety (WLL 10:1 safety factor, truss load tables, motor specs, certified rigger sign-off)
- Backstage access control (credential tiers, checkpoints, escort protocols)
- Monitor world: IEM frequency coordination, wedge placement, personal mixers
- Show cue protocol and comms channel assignments

---

## 04 — Templates and Matrices

Fill-in-ready documents for production use.

### [Master-Run-Of-Show-ROS.md](04-templates-and-matrices/Master-Run-Of-Show-ROS.md)

Minute-by-minute execution document.

**Table schema:** `Time | Duration | Stage Activity | Visual Cue | Audio Cue | Lighting Cue | Owner | Notes`

**Includes three fully worked examples:** corporate keynote (2hr), product launch (90min), live concert (3hr) — plus cue notation standards, time buffer guidelines, owner role definitions, and version control conventions.

### [Technical-Rider-Spec.md](04-templates-and-matrices/Technical-Rider-Spec.md)

Complete technical requirements document.

**Eleven table sections:** stage map, input list, output list, monitor requirements, LED/video specs, lighting specs, power requirements (with load calculations), rigging, backline, crew, load-in/out schedule.

**Includes three example riders:** corporate (16ch), rock band (32ch, full PA + IEM + LED wall), conference (24ch, 3 breakout rooms).

### [Risk-Contingency-Matrix.md](04-templates-and-matrices/Risk-Contingency-Matrix.md)

Pre-planned responses to 40+ failure scenarios.

**Table schema:** `Scenario | Probability | Impact | Risk Score | Plan B Protocol | Decision Maker | Recovery Time`

**Categories:** audio failures, video failures, network failures, power failures, human factors, venue issues, weather, security, legal/compliance. Plus escalation chain, pre-show risk assessment checklist, and post-incident report template.

---

## How to Use This Knowledge Base

### For Project Development

The WING Scene Parser project draws on this knowledge base in three ways:

1. **Schema descriptors** (`wing_parser/descriptors/`) reference the OSC paths and parameter semantics documented in `01-live-audio-ai/Behringer-WING-Integration.md`
2. **Advisory rules** (`wing_parser/advisory/rules/`) encode the mixing best practices and diagnostic thresholds from `01-live-audio-ai/AI-Plugins-In-Live-Sound.md` and `02-event-ops-framework/Core-Skills-Overview.md`
3. **Event context** for scene analysis draws on the SOPs in `03-event-type-sops/` — a corporate keynote scene should be evaluated against different criteria than a rock concert scene

### For Live Production

| Situation | Start Here |
|-----------|-----------|
| Setting up AI processing on WING for the first time | `01-live-audio-ai/Behringer-WING-Integration.md` → Connectivity Options |
| Choosing which AI plugin to deploy | `01-live-audio-ai/AI-Plugins-In-Live-Sound.md` → Plugin Comparison Matrix |
| Planning a new event | `03-event-type-sops/` → matching event type, then `04-templates-and-matrices/` |
| Building a technical rider | `04-templates-and-matrices/Technical-Rider-Spec.md` → closest example rider |
| Pre-show preparation | `04-templates-and-matrices/Risk-Contingency-Matrix.md` → Pre-Show Risk Assessment Checklist |
| Something broke mid-show | `04-templates-and-matrices/Risk-Contingency-Matrix.md` → Master Risk Table |

### Maintenance

- **Firmware changes:** When Behringer releases WING firmware updates, verify OSC paths in `Behringer-WING-Integration.md` against the changelog at [wing-docs.com](https://wing-docs.com/)
- **Plugin updates:** Re-measure latency figures in `AI-Plugins-In-Live-Sound.md` after major plugin version bumps — vendors change buffer strategies between releases
- **Equipment substitutions:** Model numbers in the rider templates reflect 2026 availability; verify current equivalents before quoting

---

## Source Attribution

Technical content derives from:

- **Behringer WING User Manual** (firmware 3.1, October 2025) and community documentation at [wing-docs.com](https://wing-docs.com/)
- **OSC command reference** extracted from [bitfocus/companion-module-behringer-wing](https://github.com/bitfocus/companion-module-behringer-wing) (`src/commands/`)
- **AILive Mixer** (Zurale et al., ICASSP 2026, [arXiv:2603.15995](https://arxiv.org/abs/2603.15995)) — multi-rate architecture for zero-latency automatic mixing
- **iZotope mastering guidance** — [Mastering for Streaming Platforms](https://www.izotope.com/en/learn/mastering-for-streaming-platforms.html) (LUFS/dBTP/LRA standards)
- **Plugin vendor documentation** — Waves, Sonible, Audinate technical specifications
- **Open-source event playbooks** — CNCF, DevOpsDays, python-organizers, Mozilla

Where figures are measured rather than published, the measurement conditions are stated inline.
