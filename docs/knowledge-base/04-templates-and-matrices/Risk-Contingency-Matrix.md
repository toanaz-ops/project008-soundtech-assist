# Risk & Contingency Matrix

## Scope & How To Read This Document

This is the operational risk register for live event delivery. Every row states what fails, how often it actually fails, what the audience experiences, the executable recovery, who decides, and how long the hole is. It is written to be usable at 09:41 with a dark screen and a client walking toward you, not as a compliance artefact.

**Exposure unit.** Every probability in §2 is the chance of **at least one occurrence per show-day**, not per hour and not per lifetime. This matters: a 2% per-show-day scenario reaches **55% likelihood across a 40-show season** (`1 − 0.98^40`). Low daily probability is not an argument against a written protocol.

**Reference event.** Figures are calibrated to a single-day, 300–1,500 attendee corporate or tech conference in a fixed indoor venue: 8-hour show day, one main stage, IMAG plus live stream, 12–24 wireless channels, dual-redundant video path per `Core-Skills-Overview.md §2.3`, crew of 6–12. Weather rows (§2.7) assume an outdoor or marquee variant. Re-baseline the percentages for your venue, your gear age, and your crew — a 9-year-old lamp projector fleet and a laser fleet do not share a risk profile.

**Figure provenance.** Three classes of number appear, and they are not equally hard:

| Class | Marked | Basis | Examples |
|-------|--------|-------|----------|
| Published standard / physical constant | `[STD]` | Codified guidance or measured physics | Lightning 30/30 rule, AED survival decay, Li-ion cold derate, temporary-structure wind thresholds |
| Vendor / field-instrumented | `[FLD]` | Manufacturer MTBF, platform behaviour, incident logs from comparable shows | Live-demo fault rate, Content ID match rate, console boot times |
| Operator baseline | `[OPS]` | Planning estimate from accumulated show experience; the honest label for "we budget for this" | Breaker trips, presenter no-shows, access disputes |

`[OPS]` figures are planning baselines, not measurements. Treat them as the starting prior and overwrite them with your own incident data from §5 after ten shows. That feedback loop is the point of the post-incident report.

---

## 1. Risk Scoring Model

### 1.1 Probability Bands (P)

| P | Label | Per-show-day chance | Season view (40 shows) | Planning meaning |
|---|-------|--------------------|------------------------|------------------|
| 1 | Rare | < 1% | up to ~33% | Will happen eventually to someone on the team |
| 2 | Unlikely | 1–5% | 33–87% | Will happen this season |
| 3 | Possible | 5–15% | > 87% | Will happen this quarter |
| 4 | Likely | 15–40% | Effectively certain | Will happen this month |
| 5 | Near-certain | > 40% | Certain | Plan the show assuming it happens |

### 1.2 Severity Bands (S)

| S | Label | Audience experience | Commercial / legal exposure |
|---|-------|--------------------|------------------------------|
| 1 | Negligible | Nothing visible. Absorbed inside ops | None |
| 2 | Minor | Attentive audience notices. < 30 s degradation, no content lost | None |
| 3 | Moderate | Clearly visible or audible. Segment degraded, content interrupted | Client comment, no claim |
| 4 | Major | Segment lost or show stopped. Stream or recording compromised | Deliverable failure, partial refund risk |
| 5 | Catastrophic | Event terminated, or injury / life-safety event | Liability, HSE reporting, contract termination |

Severity is scored **as the scenario would land with no mitigation in place**. Scoring the mitigated outcome hides the reason the mitigation exists and lets someone delete it during a budget cut.

### 1.3 Risk Score

```
Risk Score = P × S          range 1–25
```

| Score | Band | Required posture before doors open |
|-------|------|-----------------------------------|
| 1–4 | **LOW** | Accept. Named in the matrix, no standing protocol required |
| 5–9 | **MEDIUM** | Written Plan B (this document). Owner briefed verbally at pre-show |
| 10–14 | **HIGH** | Redundancy physically present, powered, and patched. Failover executed once during tech rehearsal with a stopwatch |
| 15–19 | **SEVERE** | N+1 engineered into the design. Drilled to a target time. Residual risk stated to the client in writing |
| 20–25 | **CRITICAL** | Do not proceed. Re-engineer the design, change the venue, or decline the scope |

### 1.4 The Severity-5 Override

A rare catastrophe scores low on `P × S`. Lightning at P2 × S5 = 10, which sits in the same band as a media server crash. Expected-value maths is the wrong tool for life safety.

> **Rule.** Any scenario at **S5** carries a written protocol, a named decision maker, and a pre-show verbal brief regardless of its risk score. S5 rows are never closed with "accepted".

The score drives **how much engineering and money** you spend. It never drives **whether a life-safety protocol exists**.

### 1.5 Scoring Worked Example

Presenter laptop fault during a live demo. Field-instrumented laptop-side fault rate is 4–7% per demo (`Tech-Expos-Hackathons.md §1.1`). Across 6 demo segments in a show day, at least one fault is `1 − 0.945^6 ≈ 29%` → **P4**. Unmitigated it puts a Windows Update screen on a 6 m IMAG wall and kills the segment → **S4**. Score **16 SEVERE**, which is exactly why the pre-recorded fallback in that SOP is contractual rather than advisory. With the fallback the residual is S2 (a 2 s cut to hold slide) → score 8, MEDIUM. That delta is the entire argument for the policy.

---

## 2. Master Contingency Matrix

Columns are constant across all nine domains. `Impact` carries the severity band and its consequence. `Recovery Time` states the mitigated figure first, then the unmitigated figure, because the gap between them is what redundancy buys. IDs are stable references for the escalation chain (§3) and incident reports (§5).

### 2.1 Audio

| ID | Scenario | Prob % (P) | Impact (S) | Score | Plan B Protocol | Decision Maker | Recovery Time |
|----|----------|-----------|-----------|-------|-----------------|----------------|---------------|
| A-01 | Digital console total crash / spontaneous reboot (Behringer WING, X32, DiGiCo SD-series) | 2% `[FLD]` (P2) | **S5** — all reinforcement, all IEM, and the stream bed die together | **10 HIGH** | 1) A1 calls "AUDIO DOWN" on comms; caller pushes hold slide, house LX to 60%. 2) A2 swings stage-box **AES50 B** to the hot-spare console already running the mirrored show file. 3) Flip the manual XLR A/B panel at the drive-rack inputs to spare L/R + stream feed. 4) Primary goes down cold and is re-verified in full before any swap back — never swap back mid-segment | A1; auto-escalates to TD at 30 s | **8–15 s** (hot spare on AES50 B) / 55–75 s WING cold boot to audio pass |
| A-02 | Console PSU failure, single-PSU frame | 1% `[FLD]` (P1) | **S5** — identical to A-01, and not repairable at FOH | 5 MEDIUM *(S5 override applies)* | 1) Confirm PSU vs mains by checking other gear on the same strip. 2) If the frame is dead, execute A-01 steps 1–3. 3) Specify redundant-PSU frames (SD10) for any show that cannot carry a hot spare. 4) Frame is quarantined post-show, not returned to hire stock | A1 | **8–15 s** (failover) / no on-site repair |
| A-03 | Amplifier or powered-box channel failure (Lab.gruppen PLM 20K44, L-Acoustics LA12X, QSC PowerLight, RCF HDL) | 3% `[FLD]` (P2) | **S3** — one hang or zone drops, coverage goes asymmetric, stereo image collapses to one side | 6 MEDIUM | 1) Confirm the fault is at the amp, not the console — check amp meters and swap the input cable. 2) Repatch the hang to the spare amp channel already looped into the drive rack. 3) Recall the matching box preset in LA Network Manager / Lake Controller — never run a hang on another box's preset. 4) No spare channel: mute the failed hang, recentre imaging, accept the coverage loss rather than run it wrong | A1 (system tech if rostered) | **60–180 s** (spare channel + preset recall) / 15–30 min (amp swap) |
| A-04 | Wireless mic RF dropout / audible hit (Shure ULXD, QLXD, Sennheiser EW-DX) | 20% `[OPS]` congested urban/expo RF; ~5% on a scanned, filtered, coordinated system (P4) | **S2** — momentary garble or a 200–800 ms mute mid-sentence | 8 MEDIUM | 1) A2 monitors RF meters in Wireless Workbench / WSM, not just audio. 2) On repeat hits, A1 crossfades to the spare handheld already live in a muted DCA; SM hands it over at the next natural pause. 3) A2 re-scans and moves the failed channel within the same coordinated group before returning it to service. 4) Check antenna placement and body-blocking before blaming the band | A1 | **Instant** (parallel spare open in DCA) / 15–30 s (physical handoff) |
| A-05 | Wireless transmitter battery death mid-segment | 4% with a logged battery protocol, 20%+ without `[OPS]` (P2→P4) | **S3** — mic dies mid-sentence, on camera, in the recording | 12 HIGH (unmanaged) | 1) Fresh Shure SB900B / Sennheiser BA cells at the top of every session block, logged on the RF sheet. Never "it still shows three bars". 2) A2 tracks runtime telemetry in minutes and flags anything under 45 min. 3) On death, unmute the pre-gain-staged lectern gooseneck or SM walks in the spare handheld. 4) All swaps happen at segment boundaries, never live | A2 | **5–10 s** (lectern mic already staged) / 20–40 s (handoff) |
| A-06 | Feedback runaway | 6% brief ring, 1.5% sustained `[OPS]` (P3) | **S3** — painful for the room, reputational, and at sustained SPL a hearing-risk and stream-limiter event | 9 MEDIUM | 1) DCA or master down 10–15 dB inside 2 s. **Level first. Never hunt the frequency while it rings.** 2) Identify the open mic — NOM discipline: if it should not be open, mute it. 3) Narrow PEQ notch, Q 8–12, 3–6 dB cut, verified against the RTA. 4) Restore level, then re-establish ≥6 dB GBF margin. 5) If a presenter walked a handheld into a wedge, kill the wedge, not the mic | A1 alone, no consultation | **1–2 s** to silence, 10–30 s to full level |
| A-07 | IEM transmitter failure (Shure PSM1000, Sennheiser 2000 IEM) | 2% `[FLD]` (P2) | **S3** — presenter loses IFB, or band loses click and the MD loses the show | 6 MEDIUM | 1) Spare transmitter pre-tuned to a coordinated backup frequency with its matrix send already patched. 2) Performer switches the pack to the backup group on a hand signal from A2. 3) No spare: unmute the pre-rigged sidefill wedge on its own mix. 4) Click-critical acts never run IEM without a wedge fallback patched and level-checked | A2, informs A1 | **30–60 s** |
| A-08 | FOH position power loss (the single 16 A circuit feeding the FOH rack) | 3% `[OPS]` (P2) | **S5** — console, comms base, and stream encoder die simultaneously | **10 HIGH** | 1) Line-interactive rack UPS (APC SMT1500RM2U) feeding console, comms base, and encoder — at ~400 W draw that is a 12–18 min *shutdown window*, not a show. 2) On mains loss the UPS carries with zero audio interruption; A1 announces "FOH ON UPS" and calls the runtime clock aloud every 2 min. 3) ME traces to the panel, restores, or moves FOH to another phase. 4) At 5 min remaining with no restoration, TD calls a controlled hold rather than an uncontrolled console death | TD, on A1's report | **0 s** interruption (UPS) / 60–120 s mains + 55–75 s console boot |
| A-09 | Stage-box snake link loss — AES50 or Dante primary cut, crushed, or unseated | 3% `[OPS]` (P2) | **S4** — every stage input gone while FOH still looks healthy, which burns diagnostic minutes | 8 MEDIUM | 1) Run AES50 B / Dante secondary on a **physically separate cable path** — different route, different tray, never cable-tied to the primary. 2) Console continues on the redundant link; A1 confirms on the AES50 status page. 3) A2 walks the primary run — most faults are at a connector or under a wheeled road case. 4) Pre-terminated spare Cat6 drum staged at the SL corner | A1 | **< 1 s** (redundant link) / 3–8 min (re-run spare) |

### 2.2 Video

| ID | Scenario | Prob % (P) | Impact (S) | Score | Plan B Protocol | Decision Maker | Recovery Time |
|----|----------|-----------|-----------|-------|-----------------|----------------|---------------|
| V-01 | Projector lamp failure (UHP lamp-based Panasonic PT-DZ21K, Christie Boxer) | 2% under 50% rated lamp life; **10% past 80% of rated life** `[FLD]` (P2→P3) | **S4** — one screen or a blended edge goes dark; on a single-screen room, all content | 8 MEDIUM → **12 HIGH** near end of life | 1) Dual-lamp projectors run in **redundant mode, not economy** — auto-switch to lamp B is under 10 s. 2) On total loss, V1 reframes content to the surviving screen and IMAG folds to single-screen; caller informs the presenter via IFB before they notice. 3) Lamp swap requires a **5–8 min forced cool-down** — it cannot be hot-swapped, so it is a break job, never a mid-segment job. 4) Specify laser-phosphor (PT-RZ21K, Barco UDX-4K32) and this row drops to P1 | V1 | **< 10 s** (dual-lamp auto-switch) / 15–25 min (swap incl. cool-down) |
| V-02 | Presenter laptop crash, forced OS update, or thermal throttle | 29% across 6 demo segments `[FLD]` (P4) | **S4** — update screen or crash dialogue on the main wall, segment content lost | **16 SEVERE** | 1) Hold slide armed on a dedicated switcher input at all times; V1 cuts within 2 s of any unexpected frame. 2) Show laptop carries every deck delivered at T-24 h — cut to the show copy and drive slides from FOH on the presenter's verbal cue. 3) Pre-recorded demo capture (`Tech-Expos-Hackathons.md §1.2`) rolls from the media server. 4) Presenter laptops run on mains with sleep, screensaver, notifications, and auto-update disabled — verified in rehearsal, not asked about | V1, Demo Wrangler for demo content | **< 2 s** to hold slide, 20–45 s to backup deck live |
| V-03 | HDMI signal loss — EDID renegotiation, HDCP blanking, or a walked-out connector | 12% `[OPS]` (P3) | **S3** — 1–5 s of black or a permanent blank on protected content | 9 MEDIUM | 1) EDID manager (Gefen EDID Detective Plus, Lightware) locks the sink profile so laptops never renegotiate. 2) Convert to SDI in the first metre and keep HDMI out of the infrastructure entirely. 3) On black, V1 cuts to hold slide first and diagnoses second. 4) HDCP blanking is resolved in pre-production by obtaining an unprotected asset — **no stripping devices**, per `Core-Skills-Overview.md §2.4` | V1 | **1–5 s** (re-handshake) / < 2 s to hold slide |
| V-04 | LED wall tile or receiving-card failure (Absen PL2.5, ROE Black Pearl BP2 on Novastar MCTRL4K or Brompton Tessera SX40) | 3% `[FLD]` (P2) | **S3** — a dead block or a dark column mid-content | 6 MEDIUM | 1) Wire every data run as a **redundant loop** so a mid-run card failure back-feeds from the far end automatically. 2) Single dead tile: reframe content inboard of the fault if the design allows, or accept it until the next break. 3) Hot-swap the tile at the break — 2 spare tiles per 50 m² on site, minimum. 4) Whole-wall black is almost always the processor or its feed, not the wall: check MCTRL4K input lock before touching a tile | V1 with LED tech | **< 1 s** (loop redundancy) / 3–8 min (tile hot-swap at break) |
| V-05 | Media server crash (disguise gx 2c, Resolume Arena, Playback Pro, QLab 5) | 3% `[FLD]` (P2) | **S4** — all playback, all stings, and any timecode-locked content stops | 8 MEDIUM | 1) Mirrored understudy machine on the same timecode with an identical project, output already wired to a switcher input. 2) V1 takes the understudy input; caller announces the cue position so the operator can re-cue accurately. 3) Cold restart only if no understudy: 60–180 s, and the caller fills with the host on camera. 4) Never run playback from the same machine as the switcher control surface | V1 | **5–15 s** (understudy take) / 60–180 s (cold restart) |
| V-06 | Production switcher failure (ATEM 2 M/E Constellation, Ross Carbonite Ultra, Barco E2) | 1% `[FLD]` (P1) | **S5** — every screen, IMAG, and the stream go to black together | 5 MEDIUM *(S5 override applies)* | 1) Backup switcher runs the same sources live from the SDI DA fan-out, its PGM already at the A/B switch. 2) **One physical action** at the A/B switch or Videohub moves the whole show to switcher B — this is the entire reason the design in `Core-Skills-Overview.md §2.3` exists. 3) Failover is executed with a stopwatch during tech rehearsal, not assumed. 4) Backup switcher keeps a hold slide on PGM whenever it is not in use | V1, TD informed | **5–10 s** (A/B failover) / show-stopping without it |
| V-07 | Stream encoder crash or RTMP session drop (Teradek VidiU X, Blackmagic Web Presenter 4K, OBS/vMix host) | 5% `[OPS]` (P3) | **S3** — remote audience loses the show; in-room unaffected; VOD asset damaged | 9 MEDIUM | 1) Second encoder fed from the same clean PGM, pre-authenticated to the platform's **backup ingest URL** — most platforms accept primary and backup simultaneously. 2) Stream Operator switches ingest, posts a holding card and a chat message. 3) Local ISO recording (Hyperdeck or on-board card) runs continuously so the VOD survives even a total stream loss. 4) Restart the failed encoder only after the backup is confirmed live on the platform dashboard | Stream Operator | **10–30 s** (backup ingest) / 30–90 s (encoder restart) |

### 2.3 Network & Data

| ID | Scenario | Prob % (P) | Impact (S) | Score | Plan B Protocol | Decision Maker | Recovery Time |
|----|----------|-----------|-----------|-------|-----------------|----------------|---------------|
| N-01 | Venue WAN / primary internet circuit down | 8% `[OPS]` for at least a brief outage (P3) | **S4** — stream drops, cloud ROS unreachable, any cloud-dependent demo dies | **12 HIGH** | 1) Bonded failover on a Peplink Balance 20X with SpeedFusion, or Teradek Bond — 2 carriers on **different networks**, verified by IMEI, not by logo. 2) Failover is automatic and sub-30 s; Stream Operator confirms bitrate stability before announcing recovery. 3) Printed ROS carries the show regardless of cloud state (`Core-Skills-Overview.md §1.2`). 4) Cloud-dependent demos revert to the pre-recorded capture without discussion | Network Lead (NOC) | **10–30 s** (automatic bonded failover) / 20 min–hours on venue IT |
| N-02 | Dante network loss — switch failure, PTP clock re-election, or QoS misconfiguration | 3% `[FLD]` (P2) | **S5** — every networked audio path drops at once; a clock war produces intermittent ticks that are worse to diagnose than silence | **10 HIGH** | 1) Run Dante **secondary** on a physically separate switch and separate cable route. 2) Switch config is non-negotiable: DSCP 46/EF for PTP, IGMP snooping with an active querier, **Energy Efficient Ethernet disabled** — EEE alone will destroy PTP stability on a Cisco SG350 or Netgear M4250. 3) One preferred master clock set explicitly in Dante Controller, one backup, everything else follower. 4) Spare pre-configured switch on the shelf with its config saved to USB | A1 with Network Lead | **< 1 s** (secondary) / 2–10 s clock re-election / 3–10 min switch swap |
| N-03 | Wi-Fi saturation and 2.4 GHz channel collapse | 40%+ at a tech expo on unengineered WLAN `[OPS]` (P5) | **S3** attendee-facing, **S4** if any stage demo depends on it | **15 SEVERE** | 1) Engineer at **3 devices per attendee**, not 1 (`Tech-Expos-Hackathons.md`). 2) Kill 2.4 GHz for all staff and production SSIDs; 5/6 GHz only, 20 MHz channels, min-RSSI and band steering on (Ruckus R750, Cisco 9130). 3) Every stage demo runs on a **wired VLAN**, never on attendee Wi-Fi — this is a design rule, not a contingency. 4) Live remediation is rate-limiting and per-client caps; expect 5–15 min for changes to take effect across clients | Network Lead | **5–15 min** (rate-limit / channel changes) — largely unrecoverable on the day |
| N-04 | DHCP scope exhaustion | 15% at device-dense events scoped at 1 IP per head `[OPS]` (P4) | **S3** — new clients get no address; presenters and staff arriving late are locked out | **12 HIGH** | 1) Scope a `/22` (1,022 usable) minimum for a 500-pax tech event and check utilisation hourly. 2) On exhaustion, drop lease time from 8 h to **30–60 min** and extend the scope; recovery is not instant because existing leases must age out. 3) Production, Dante, and demo VLANs use **static addressing** so attendee churn can never starve them. 4) Reserve a small static block for presenter laptops | Network Lead | **3–10 min** (scope resize) + up to one lease interval for clients |
| N-05 | Comms system failure — DECT intercom base fault or headset battery death (Hollyland Solidcom C1 Pro) | 4% `[OPS]` (P2) | **S3** — the caller loses the cue path, which stops cueing even though every device still works | 6 MEDIUM | 1) Motorola CP100d UHF handhelds pre-tuned on the crew channel, one per position, powered and volume-set. 2) Caller switches to handheld and announces "COMMS ON RADIO — acknowledge by name" to confirm each position. 3) Spare charged headsets at FOH; batteries changed at every break, not when they die. 4) Line-of-sight hand signals for SM-to-caller as the final layer | Show Caller | **30–60 s** (switch to UHF) |
| N-06 | Broadcast storm or switching loop on a shared production VLAN | 2% `[OPS]` (P2) | **S4** — control network, Dante, and stream all degrade at once with no obvious single cause | 8 MEDIUM | 1) RSTP enabled with BPDU guard on all access ports, plus storm control at 5% broadcast — configured at build, not after. 2) On symptoms, Network Lead isolates by unplugging uplinks one at a time from the far end inward. 3) Never patch two ports of the same switch together to "extend" a run, and never let a sponsor plug their own switch into a production port. 4) Colour-coded and labelled patching so a wrong port is visible | Network Lead | **2–30 s** (RSTP self-heal) / 5–20 min (manual isolation) |

### 2.4 Power

| ID | Scenario | Prob % (P) | Impact (S) | Score | Plan B Protocol | Decision Maker | Recovery Time |
|----|----------|-----------|-----------|-------|-----------------|----------------|---------------|
| P-01 | Branch circuit breaker trip (16 A / 20 A overloaded, or inrush on power-up) | 12% `[OPS]` (P3) | **S4** — depends entirely on what shared that circuit, which is why the load schedule exists | **12 HIGH** | 1) Load every circuit to **80% continuous maximum** — 12.8 A on a 16 A, 16 A on a 20 A. Measure with a clamp meter at load-in; do not add nameplate figures and hope. 2) Written load schedule names every circuit, its breaker, its panel, and its devices. 3) On trip, ME goes straight to the identified panel — no hunting. Reset once. **A second trip is a fault, not an overload: stop and investigate.** 4) Stagger power-up of LED processors and amps to spread inrush | Master Electrician (ME) | **60–180 s** (reset + device boot) |
| P-02 | Generator failure or fuel exhaustion (outdoor / marquee) | 4% `[OPS]` single-set (P2) | **S5** — total site power loss, event stops | **10 HIGH** | 1) N+1 sets with an automatic transfer switch; ATS pickup is 10–30 s and that gap is exactly what the UPS layer covers. 2) Fuel for **full runtime + 50% reserve**, dipped and logged at load-in and at every break. 3) Load the set to 50–75% of rating — chronic under-loading causes wet stacking and its own failures. 4) Load-bank test before doors, not a no-load idle test. 5) Single-set shows carry a documented graceful-shutdown order | ME, escalates to TD | **10–30 s** (ATS to second set) / 5–20 min restart / 20–60 min refuel |
| P-03 | UPS depletion during an extended mains outage | 2% standalone `[OPS]`, high once an outage passes 10 min (P2) | **S5** — the protected core dies, and it dies without warning if nobody watched the runtime | **10 HIGH** | 1) UPS is a **shutdown window, not a power source**. Publish the real number: an APC SMT1500RM2U at ~400 W gives 12–18 min. 2) Runtime is called aloud every 2 min from the moment of transfer. 3) At 5 min remaining with no restoration path, TD calls a controlled hold and the graceful shutdown order runs — save show files first. 4) Never hang LED walls, moving lights, or amps off the UPS layer; console, comms, encoder, and the primary media server only | TD, on ME's runtime report | **0 s** interruption while charged; then hard down until mains or generator returns |
| P-04 | Brownout / voltage sag (long feeder, HVAC compressor start, site-wide load step) | 8% `[OPS]` (P3) | **S3** — switch-mode PSUs drop out below roughly 180 V and digital gear silently reboots mid-show | 9 MEDIUM | 1) Line-interactive UPS with AVR on the critical rack rides sags without transferring to battery. 2) Log voltage at the distro during load-in **while the HVAC cycles** — a reading taken in a quiet empty room proves nothing. 3) Move critical racks off any feeder shared with HVAC or kitchen plant. 4) Treat repeated sags as a venue infrastructure escalation, not a gear problem | ME | **60–180 s** per rebooted device (cascading) |
| P-05 | RCD / GFCI nuisance trip (outdoor, damp, long runs, high device count) | 8% outdoor `[OPS]` (P3) | **S4** — a whole leg drops, often repeatedly, and it reads as a mystery | **12 HIGH** | 1) Understand the mechanism: every switch-mode PSU leaks ~0.5–3.5 mA to earth, so **20 devices can sum past a 30 mA RCD with no actual fault**. 2) Split loads across multiple RCDs so leakage never accumulates on one device; time-delayed 100/300 mA upstream with 30 mA downstream. 3) On trip, halve the load and re-energise to bisect toward the offending leg. 4) Wet weather: elevate all connections off the ground, IP-rated couplers, drip loops. **Never defeat an RCD** | ME | **2–8 min** (bisect and isolate) |
| P-06 | Phase or neutral loss on a 3-phase distro (63/125 A CEE or Powerlock feed) | 1.5% `[OPS]` (P2) | **S5** — one third of the site dies; a **lost neutral** puts up to 400 V across 230 V equipment and destroys it | **10 HIGH** | 1) Verify phase rotation, voltage on all legs, and neutral integrity with a multimeter at every connection before energising anything. 2) Balance loads across phases within 20% and record the figures. 3) On suspected neutral loss, **kill the feed immediately** — do not power-cycle equipment to test it. 4) Only the venue's competent electrician touches the incoming feed; this is a qualified-person boundary | ME, with venue electrician | **10–30 min** (venue electrician) / equipment damage may be permanent |

### 2.5 Human Factors

| ID | Scenario | Prob % (P) | Impact (S) | Score | Plan B Protocol | Decision Maker | Recovery Time |
|----|----------|-----------|-----------|-------|-----------------|----------------|---------------|
| H-01 | Speaker no-show (missed flight, illness, diary error) | 6% per multi-speaker event `[OPS]` (P3) | **S4** — a hole in the running order with an audience already seated | **12 HIGH** | 1) Producer confirms physical arrival at T-60 min per speaker, not "they said they're coming". 2) On no-show, execute the pre-agreed reflow in priority order: pull the following segment forward → expand the panel → host-led Q&A from pre-written questions → pull the break forward. 3) Every option is decided and scripted at rehearsal, so the live decision is a selection, not an invention. 4) Caller announces the new cue positions to all departments before the reflow starts | Producer, with Client Lead | **5–15 min** (reflow, mostly absorbed into buffers) |
| H-02 | Speaker overrun | 70% of events see at least one `[OPS]` (P5) | **S2** isolated; **S4** once it compounds and eats the close | **10 HIGH** | 1) Confidence-monitor countdown at eye line, ≥15% of screen height (`Core-Skills-Overview.md §1.6`). 2) Escalate on the published ladder: timer at 00:00 → SM 2-min visual → SM 30-s visual → IFB whisper → host walks on. 3) Recovery levers 1–6 in ROS order, least-visible first, never skipping. 4) Hard reserve is never spent on an overrun. 5) The host walk-on is agreed **with the speaker** in advance, which is what makes it usable | Show Caller; SM executes | **1–15 min** recovered via buffers and levers |
| H-03 | Tech-unfamiliar presenter — mirrors instead of extends, exposes notes, cannot advance slides, brings the wrong dongle | 30% `[OPS]` (P4) | **S3** — presenter notes or a desktop on the main wall, or dead air while they fight the laptop | **12 HIGH** | 1) Mandatory 5-min tech check per presenter at rehearsal: extend mode verified (`Win+P` → Extend / macOS Displays → uncheck Mirror), notifications and Focus Assist off, screensaver and sleep disabled. 2) Hold slide armed for instant cover of any desktop exposure. 3) Show laptop holds every deck as delivered — default to driving slides from FOH on verbal cue. 4) Dongle kit at the lectern: USB-C, Mini DisplayPort, HDMI, and a spare of each | V1, with SM at the lectern | **20–60 s** live intervention; near-zero if caught at rehearsal |
| H-04 | Crew injury (manual handling, ladder or height work, cases, hand tools) | 2% minor reportable, < 0.5% serious `[OPS]`; concentrated in load-in and load-out (P2) | **S5** — injury, plus a legally reportable event and a stopped work zone | **10 HIGH** | 1) Stop work in the affected zone immediately; first aider attends, TD is informed on the crew channel. 2) Call emergency services for anything involving the head, spine, an unmanaged fracture, or loss of consciousness — do not move the casualty. 3) Preserve the scene and photograph it before clearing. 4) Log it that day: RIDDOR (UK) for over-7-day incapacitation, OSHA 300 (US) for recordables. 5) Prevention: two-person lift above 25 kg, no lone height work, toolbox talk at every call | TD, with the venue's Duty Manager | Zone stopped **20–60 min**; show continues only if the zone is show-critical-clear |
| H-05 | Key operator incapacitated mid-show (illness, family emergency) | 1.5% `[OPS]` (P2) | **S4** — a position goes unstaffed while the show is running | 8 MEDIUM | 1) Every position has a named cross-trained deputy on the crew list, and the deputy has actually sat at that position during rehearsal. 2) Show files, scene lists, patch sheets, and cue stacks are documented so a deputy can drive them cold — undocumented setups are the real failure here. 3) Caller simplifies the cue stack for the remainder: fewer takes, longer holds. 4) TD reallocates from the least show-critical position | TD | **2–10 min** (deputy takes position) |
| H-06 | Late content delivery or a last-minute deck change | 50% `[OPS]` (P5) | **S2** — unverified content goes live, which is how fonts reflow and embedded video fails on air | **10 HIGH** | 1) Hard cutoff at T-24 h in the presenter agreement; anything later is presented from the last verified version. 2) Any accepted late change is opened, played end to end, and font/media-checked on the show machine before it is armed. 3) Version-stamp filenames `Speaker_Segment_v3_FINAL-2026-08-11`; the operator loads only from the controlled folder. 4) Embedded video and web links are tested individually, never assumed | V1, with Producer on scope | **5–20 min** per deck to re-cue and verify |

### 2.6 Venue & Facility

| ID | Scenario | Prob % (P) | Impact (S) | Score | Plan B Protocol | Decision Maker | Recovery Time |
|----|----------|-----------|-----------|-------|-----------------|----------------|---------------|
| VN-01 | Fire alarm activation, including a **haze-triggered false alarm** | 4% overall; 2–5% specifically from haze where detectors were not isolated `[OPS]` (P2) | **S5** — full evacuation, show stopped, and a possible fire-service charge for a false alarm | **10 HIGH** | 1) Water-based haze (MDG Atmosphere APS, DF-50) sets off optical and aspirating (VESDA) detectors. Detector isolation is agreed **in writing** with the venue fire officer, with a fire watch posted, and **reinstated at the end of the show** — the reinstatement is the step people forget. 2) On activation, the venue's evacuation procedure takes precedence over everything: A1 kills programme audio, LX to full house, V1 posts the evacuation slide. 3) Caller reads the pre-scripted evacuation announcement. 4) Crew sweep their zones and report to the assembly point by name | **Venue Duty Manager / Fire Safety Manager** — not the TD | Evacuation **3–8 min**; re-entry 20–60 min after fire-service clearance; restart 15–30 min |
| VN-02 | HVAC failure / room over-temperature | 4% `[OPS]` (P2) | **S3** — audience discomfort, amp thermal limiting, LED wall derate, laptop throttling | 6 MEDIUM | 1) Monitor rack and amp temperatures, not just room temperature — amps limit long before the audience complains. 2) Improve airflow at the amp racks first: open case lids, add spot fans, relieve any downstage skirting that blocks intake. 3) Producer negotiates shortened segments and earlier breaks with the client. 4) Portable cooling and door management via the venue; genuine recovery is 20–60 min and partial | Venue Duty Manager, with Producer | **20–60 min**, partial recovery only |
| VN-03 | Water leak or roof ingress over equipment | 2% `[OPS]` (P2) | **S5** — live electrical hazard first, equipment loss second | **10 HIGH** | 1) **De-energise the affected leg before touching anything.** Water plus a powered distro is a life-safety situation, not an equipment problem. 2) Poly sheeting over gear, catch buckets, and cordon the wet area from the public. 3) Relocate the affected position; do not re-energise until the ME has inspected and the area is dry. 4) Photograph everything for the insurance claim before moving equipment | ME for isolation; TD for relocation | Isolation **< 60 s**; relocation 10–40 min |
| VN-04 | Site access denied — dock unavailable, security has no crew list, credentials not issued | 8% `[OPS]` (P3) | **S3** — pure schedule damage, compresses everything downstream toward doors | 9 MEDIUM | 1) Access pack confirmed at T-7 days: named crew list, vehicle registrations, dock slot, insurance certificate, and the on-site contact's mobile number. 2) On refusal, Producer escalates to the venue's booking contact and the client's venue liaison simultaneously — not sequentially. 3) Crew begins any work that does not need the room: RF coordination, laptop prep, cable prep in the vehicle. 4) TD recalculates the load-in critical path and reports the new doors risk immediately | Producer | **20–90 min** |
| VN-05 | Noise complaint or venue SPL limit enforcement | 15% for amplified events near residential or under a house limiter `[OPS]` (P4) | **S3** — forced level reduction, or a house limiter cutting power to the PA mid-show | **12 HIGH** | 1) Know the limit and its metric **before** the show: `dBA` vs `dBC`, instantaneous vs 15-min `LAeq`, and where the venue's microphone is. 2) Log SPL continuously at the measurement position with an NTi XL2 or equivalent, and hold 2–3 dB below the trip point. 3) On enforcement, trim masters 3–6 dB and pull LF first — low frequency is what travels to a complainant and what the complaint is almost always about. 4) Cardioid or end-fire sub arrays reduce rearward and off-site spill by 10–15 dB | A1, with Producer on the client conversation | **2–5 min** (trim and limiter reset) |
| VN-06 | Rigging point refusal or a load limit discovered on site | 5% `[OPS]` (P3) | **S4** — the hang design becomes unusable hours before doors | **12 HIGH** | 1) Venue rigging plot, point loads, and structural sign-off obtained at **T-14 days**. If the venue cannot produce load data, design ground-support from the start. 2) On refusal, pivot to ground support (Prolyte, Tomcat) — which is why the tower and base plates travel on any show with a marginal rigging position. 3) Reduce the hang: fewer boxes, lower trim, re-aim for coverage from a ground stack. 4) Never negotiate a point up to a load the venue will not certify | Rigging Lead, with TD | **1–4 h** (ground-support pivot); not recoverable inside a same-day load-in |
| VN-07 | Venue power delivered below specification (no 3-phase where promised, wrong connector, insufficient capacity) | 4% `[OPS]` (P2) | **S4** — the whole power design has to be rebuilt on site | 8 MEDIUM | 1) Photograph the actual panel, connectors, and breaker ratings during the site visit — a spec sheet is not evidence. 2) Carry an adapter set for the region's common connectors plus a tails-to-CEE spider. 3) Shortfall: shed non-essential load in the pre-agreed order (uplighting, booth power, charging stations) before touching show-critical systems. 4) Generator hire is a 1–3 h option and only if vehicle access allows | ME, with TD on load shedding | **1–3 h** (generator or reconfiguration) |

### 2.7 Weather & Environment (outdoor / marquee)

| ID | Scenario | Prob % (P) | Impact (S) | Score | Plan B Protocol | Decision Maker | Recovery Time |
|----|----------|-----------|-----------|-------|-----------------|----------------|---------------|
| WX-01 | Rain onset over unprotected stage or FOH | 30% temperate summer outdoor without full cover `[OPS]` (P4) | **S4** — electrical hazard, equipment loss, and RCD trips (see P-05) | **16 SEVERE** | 1) Covers pre-staged **at the position**, not in a truck: console cover, poly for amp racks, Rycote or ProPack covers for mics, umbrellas over the FOH desk. 2) Every connection elevated off the ground with drip loops; IP-rated couplers on all outdoor mains. 3) On onset, ME confirms RCD protection is intact and A1 covers the console before anything else. 4) At sustained heavy rain, TD calls a hold — running a wet FOH position is not a judgement call. 5) Weather brief at T-24 h and T-2 h with a named forecast source | TD, on ME's electrical safety report | Cover deployment **3–8 min** if pre-staged; hold duration is weather-led |
| WX-02 | Wind exceeding the structure's action threshold (temporary roof, PA hangs, LED wall, banners) | 15% at an outdoor show in exposed terrain `[OPS]` (P4) | **S5** — structural collapse is the deadliest failure mode in this industry | **20 CRITICAL** unmitigated | 1) **Use the structure supplier's engineered wind action plan and its numbers — never a generic threshold.** Typical shape: banners and scrim removed around 25–30 mph (11–13 m/s), lower or evacuate the structure around 35–40 mph (16–18 m/s) sustained `[STD]`. 2) Calibrated anemometer logging at trim height, not at ground level, with a named wind watcher who has stop authority. 3) Banners and scrim are sails and come off **first** — they are the largest load contributor and the cheapest to remove. 4) Pre-agreed hold, lower, and evacuate triggers signed by the client before build. **No outdoor temporary structure goes up without this plan.** | Rigging Lead / structure engineer holds stop authority; TD executes | Banner removal **5–15 min**; structure lowering 15–45 min; hold is weather-led |
| WX-03 | Lightning within 10 km | 10% in convective season `[OPS]` (P3) | **S5** — direct life-safety risk to crew, audience, and anyone on a metal structure | **15 SEVERE** | 1) Apply the **30/30 rule** `[STD]`: suspend activity when flash-to-bang is ≤ 30 s (≈10 km / 6 mi), and resume only **30 minutes after the last observed flash or thunder**. The 30-minute clock restarts on every subsequent flash. 2) Subscribe to a lightning detection service (Earth Networks, Blitzortung) with an alert to a named phone, not to a dashboard nobody watches. 3) On trigger: crew off all towers and structures, audience directed to hard-topped buildings or vehicles, caller reads the pre-scripted announcement. 4) The 30-minute hold is not negotiable with a client or a headliner | Safety Officer / TD | Suspension immediate; **minimum 30 min hold** after the last detection |
| WX-04 | Temperature extreme | 15% seasonal `[OPS]` (P4) | **S3** — heat: amp limiting, LED derate, laptop throttle, audience heat illness. Cold: sluggish LCD response, battery collapse | **12 HIGH** | 1) Heat above ~35 °C: shade amp racks, increase airflow, and expect thermal limiting; move LED walls to a lower brightness ceiling before the processor does it unpredictably. 2) Cold: **Li-ion loses 20–30% capacity at 0 °C** `[STD]` — halve expected transmitter runtime and double the battery stock. 3) Keep spare batteries warm in an insulated case, not in an open crate on a cold deck. 4) Water and shade provision for the audience is the Safety Officer's call, and it escalates fast in direct sun | TD for equipment; Safety Officer for people | Mitigation only; **no full recovery** while conditions persist |
| WX-05 | Condensation on equipment moved between cold and warm environments | 8% winter load-ins `[OPS]` (P3) | **S3** — moisture inside optics, on circuit boards, and on connectors, with a real short-circuit risk on power-up | 9 MEDIUM | 1) **Acclimatise gear in its closed cases for 30–60 min before opening or powering on.** The closed case is what makes this work — opening it early is what causes the condensation. 2) Projector optics and LED tiles are the most affected; a fogged lens looks like a focus fault and wastes diagnostic time. 3) Visibly wet gear stays off until dry and inspected; forcing power on is how a survivable delay becomes a dead unit. 4) Build the acclimatisation window into the load-in schedule as a real line item | TD | **30–60 min** acclimatisation, planned rather than reactive |

### 2.8 Security, Safety & Medical

| ID | Scenario | Prob % (P) | Impact (S) | Score | Plan B Protocol | Decision Maker | Recovery Time |
|----|----------|-----------|-----------|-------|-----------------|----------------|---------------|
| SC-01 | Unauthorised stage, backstage, or FOH access | 8% `[OPS]` (P3) | **S3** — someone unaccountable next to live power, rigging, and the console | 9 MEDIUM | 1) Single controlled entry point per restricted zone with a visible credential scheme; crew challenge anyone without one, every time. 2) FOH is a barriered position — an unbarriered console will be leaned on, and drinks will be put on it. 3) On an incursion, the nearest crew member calls security on the crew channel and stays with the person without physical contact. 4) Backstage doors are never propped for airflow or convenience | Head of Security; TD for the technical zones | **30–90 s** (escort out) |
| SC-02 | Attendee or presenter medical emergency requiring EMS | 3% serious/EMS-level at a 1,000-pax day `[OPS]` (P2); ~15% for first-aid-level presentations | **S5** — life safety, and in cardiac arrest the outcome is decided in minutes | **10 HIGH** | 1) **AED within 3 minutes of any point in the venue.** Survival from cardiac arrest falls roughly 7–10% per minute without defibrillation `[STD]`, so location and route matter more than equipment count. 2) Named first aiders per shift, published on the crew sheet with their comms channel. 3) One person is assigned to **meet and guide EMS in** — cable ramps, dock gates, and back corridors cost minutes otherwise, and the EMS route is walked and kept clear at load-in. 4) On stage: caller cuts the stream to slate, LX to house, A1 mutes, and the host clears the room's attention. Dignity for the casualty is part of the protocol | Safety Officer / first aider on scene; caller handles the room | EMS response **6–12 min** typical urban; AED intervention target **< 3 min** |
| SC-03 | Full venue evacuation (any cause) | 3% `[OPS]` (P2) | **S5** — event stopped, with a real crowd-flow injury risk during the movement | **10 HIGH** | 1) The venue's evacuation plan governs; the production supports it. Crew roles are assigned and rehearsed at the pre-show brief, not invented at the alarm. 2) A1 kills programme audio and holds the mic live for the announcement only; LX to full house; V1 posts the evacuation slide; stream cuts to slate. 3) Caller reads the pre-scripted announcement — calm, specific exit directions, no cause speculation. 4) Crew sweep assigned zones, then report to the assembly point **by name** so absences are detected. 5) Nobody re-enters until the venue authority clears it | **Venue Duty Manager**; TD executes the technical side | Clearance **3–8 min**; re-entry 20–60 min; restart 15–30 min or abandon |
| SC-04 | Deliberate disruption — heckler, protest, or stage rush | 4% general `[OPS]`; 20%+ where the event or a speaker is politically salient (P2→P4) | **S4** — hijacked content, and the disruption gets broadcast and archived if the stream is not cut | 8 MEDIUM → **16 SEVERE** for high-salience events | 1) **Cut the stream to slate immediately** — the live feed is the disruptor's amplifier and the permanent record. 2) A1 mutes any open mic the disruptor can reach; the presenter's mic stays live only if the presenter is managing it well. 3) Caller brings LX to house and posts a hold slide; security removes without crew involvement. 4) Pre-agreed with the client for salient events: whether to continue, break early, or close the segment. 5) Resume with the host, not with the interrupted presenter cold | Head of Security for the person; Show Caller for the show; Stream Operator cuts | Stream cut **< 5 s**; removal 30–120 s; resume 2–5 min |
| SC-05 | Equipment theft during open-access periods (expo halls, overnight, breaks) | 5% `[OPS]` (P3) | **S3** — a stolen lens, laptop, or radio mic removes a show capability with no replacement path | 9 MEDIUM | 1) Photograph and serial-log every high-value item at load-in; the list goes to the producer and the insurer. 2) Small high-value items (lenses, radio packs, laptops, hard drives) go into a locked case at every break, not left on a table. 3) Overnight security or a locked room is a contractual requirement for multi-day builds, agreed before the quote. 4) On discovery, report to venue security and police the same day — most insurance policies require a crime reference number | Producer, with Head of Security | Not recoverable on the day; capability loss is permanent for the show |
| SC-06 | Credible security threat (bomb threat, weapon report, hostile reconnaissance) | < 1% `[OPS]` (P1) | **S5** — event over, police-led, potential mass-casualty exposure | 5 MEDIUM *(S5 override applies)* | 1) **Do not investigate and do not search.** Report immediately to venue security and police; preserve any written or recorded threat exactly as received. 2) Evacuate or invacuate strictly as police and the venue direct — the correct action may be to stay inside, which is counter-intuitive under pressure. 3) Crew take nothing but themselves; equipment is irrelevant. 4) One spokesperson (Producer) for all external communication; crew make no statements and post nothing | **Police, with the Venue Duty Manager** | Event ends; site release is police-controlled, typically hours |

### 2.9 Legal, Insurance & Commercial

| ID | Scenario | Prob % (P) | Impact (S) | Score | Plan B Protocol | Decision Maker | Recovery Time |
|----|----------|-----------|-----------|-------|-----------------|----------------|---------------|
| LG-01 | Insurance lapse, or a certificate that does not meet the venue's requirement, discovered at load-in | 3% `[OPS]` (P2) | **S5** — no valid certificate means no load-in, and the event does not happen | **10 HIGH** | 1) Certificate of insurance issued and accepted by the venue at **T-14 days**, checked against three things the venue almost always specifies: the liability limit (commonly £5–10 m / $1–2 m public liability), the venue named as **additional insured**, and employers' liability where crew are employed. 2) Broker contact and policy number travel with the producer, on paper. 3) A gap found in business hours is fixable by endorsement in 1–4 h. Outside business hours it is not fixable, which is the entire reason for the T-14 deadline. 4) Sub-contractors provide their own certificates on the same schedule | Producer | **1–4 h** in business hours; **not recoverable** out of hours |
| LG-02 | Permit deficiency (noise consent, occupancy, temporary structure, street closure, laser or pyro notification, drone flight) | 5% `[OPS]` (P3) | **S5** — enforced shutdown, and a personally liable breach for whoever proceeds anyway | **15 SEVERE** | 1) Permit register built at contract stage with issuing authority, lead time, and owner per line. Lead times are the trap: a UK Temporary Event Notice needs **10 working days**, structure and road-closure consents need weeks. 2) Copies on site, on paper, presented on demand. 3) A missing permit means that **element** is cancelled, not the event — drop the pyro, drop the laser, drop the outdoor extension, and run the rest. 4) Never run an unpermitted element on the assumption nobody will check | Producer, with Client Lead | **1 h to not recoverable**; affected element is cancelled |
| LG-03 | Stream copyright claim — automated Content ID match on walk-in or bed music | 45% where commercial recordings are used `[FLD]` (P5) | **S3** — live stream muted or blocked mid-show, and the VOD asset becomes unusable | **15 SEVERE** | 1) Use production-library music with an explicit **streaming and synchronisation** licence (Epidemic Sound commercial tier, Artlist, Universal Production Music) for every bed, sting, and walk-in track. 2) Understand the distinction that causes most of these claims: a PRO blanket licence (PRS, ASCAP, BMI) covers **public performance in the room** and does **not** grant sync or streaming rights for your broadcast. 3) A live mute cannot be reversed in real time — switch to a cleared bed within 30–60 s and continue. 4) Keep the licence receipts and track IDs to clear the VOD afterwards; disputes take days | Stream Operator detects; Producer owns the licensing | **30–60 s** (switch to cleared bed); VOD clearance takes days |
| LG-04 | Sub-contractor no-show, or hire company delivers wrong or incomplete kit | 7% `[OPS]` (P3) | **S4** — a designed capability is simply absent hours before doors | **12 HIGH** | 1) Confirm at T-48 h against the **line-by-line kit list**, including quantities, and get the driver's ETA — "it's on the truck" is not a confirmation. 2) Local dry-hire fallback list with account details and phone numbers, per city, maintained in advance. 3) On a shortfall, TD re-scopes the design to what is physically present and states plainly what is lost, immediately, to the producer and client. 4) Any substitution is documented against the original order for the post-show credit claim | TD for re-scoping; Producer for the supplier | **1–4 h** (local dry hire, if stock exists) |
| LG-05 | Data protection or filming-consent issue (attendees captured on camera or in the stream without notice) | 3% `[OPS]` (P2) | **S3** — complaint, takedown demand, and possible regulatory exposure | 6 MEDIUM | 1) Filming and streaming notice on the ticket terms **and** on signage at every entrance. 2) Camera plot avoids sustained audience close-ups; the safe default is wide shots and the stage. 3) Honour any opt-out — a marked lanyard or a designated non-filmed seating block. 4) On a complaint, stop the shot immediately and route the person to the producer; edit the VOD before publication rather than arguing | Producer | Live shot corrected **< 30 s**; VOD edit before publication |
---

## 3. Escalation Chain

The chain is invoked by scene ID. The first person who can act on the time window gets the call. The matrix below is mobile-phone based — landlines and radio back the chain, they do not replace it. Every name has a deputy who has the same authority and the same keys.

### 3.1 Role Hierarchy and Default Authority

| Level | Role | Default authority | Stand-in |
|-------|------|-------------------|----------|
| L1 | Operator (A1, A2, V1, V2, LX, SM, ME) | Execute the row protocol for their domain | A2 under A1; V2 under V1; A1 under LX on stage |
| L2 | Technical Director (TD) | Cross-domain decision, holds and stop-show authority | Senior crew lead (A1, V1, or ME by domain) |
| L3 | Producer | Client-facing, scope, schedule, commercial | Associate Producer |
| L4 | Client Lead / Account Director | Resolves scope vs cost; speaks for the client | Account Manager |
| L5 | Venue Duty Manager / Building Engineer | Authority on building systems, evacuation, permits | Assistant Duty Manager |
| L6 | Safety Officer (named per show) | Authority on life-safety, holds the weather stop | Deputy Safety Officer |
| L7 | External: EMS, Fire, Police, Venue H&S | Authority on their domain only | n/a — first responder takes direction |

### 3.2 Response Time Targets

| Severity | Initial acknowledgement | Containment | Resolution |
|----------|------------------------|-------------|------------|
| S5 — life-safety, fire, evacuation, criminal | **Immediate** (whichever on-call is closest) | **< 60 s** for action; < 3 min for stabilisation | Per EMS / fire / police |
| S4 — show-stopping or stream down | **< 30 s** on comms; **< 3 min** on phone if no comms | **< 5 min** | 15–60 min |
| S3 — visible degradation | **< 60 s** on comms | **< 10 min** | 30–120 min |
| S2 — minor, absorbed | Next caller update | Within the segment | By show end |
| S1 — record only | Logged post-show | n/a | n/a |

### 3.3 Contact Matrix

The matrix below is the operational version. Real names and numbers live in the show pack, dated and printed fresh for each show. The roles here are the contract.

| ID | Scenario cluster | First responder (L1) | Escalates to (L2) | Client-facing (L3–L4) | External (L5–L7) |
|----|------------------|----------------------|-------------------|------------------------|-------------------|
| A-01–A-09 | Audio failures | A1 on comms, then A2 to line | TD at 30 s | Producer at 2 min | — |
| V-01–V-07 | Video failures | V1 on comms | TD at 60 s | Producer at 5 min | Stream platform NOC for V-07 |
| N-01 | Internet down | Network Lead on comms | TD at 60 s | Producer at 5 min | Venue IT |
| N-02 | Dante loss | A1 on comms | TD at 30 s | Producer at 5 min | — |
| N-03 | Wi-Fi saturation | Network Lead | TD at 5 min | Producer at 10 min | — |
| N-04 | DHCP exhaustion | Network Lead | TD at 5 min | — | — |
| N-05 | Comms failure | Show Caller | TD at 60 s | — | — |
| N-06 | Broadcast storm | Network Lead | TD at 60 s | Producer at 5 min | — |
| P-01–P-06 | Power failures | ME on comms | TD at 30 s | Producer at 5 min | Venue electrician for P-06 |
| H-01 | Speaker no-show | Producer via comms | Client Lead at 5 min | n/a (the answer) | — |
| H-02 | Speaker overrun | Show Caller | Producer at 5 min | Client Lead at 10 min | — |
| H-03 | Tech-unfamiliar presenter | V1, SM at lectern | Producer at 5 min | — | — |
| H-04 | Crew injury | First aider on scene | TD at 60 s | Producer at 5 min | EMS; Safety Officer |
| H-05 | Operator incapacitated | TD directly | Producer at 60 s | Client Lead at 5 min | — |
| H-06 | Late content | V1 via comms | Producer at 5 min | Client Lead at 10 min | — |
| VN-01 | Fire alarm | Venue Duty Manager via venue system | TD executes | Producer at 5 min | **Fire service** |
| VN-02 | HVAC failure | Producer via venue contact | TD at 5 min | Client Lead at 10 min | Venue Duty Manager |
| VN-03 | Water leak | ME for isolation | TD for relocation | Producer at 5 min | Venue Duty Manager |
| VN-04 | Access denied | Producer on the dock | Client Lead at 10 min | Client Lead | Venue security |
| VN-05 | Noise complaint | A1, supported by Producer | Client Lead at 10 min | Client Lead | Venue Duty Manager |
| VN-06 | Rigging refusal | Rigging Lead | TD at 30 min | Producer at 60 min | Venue structural engineer |
| VN-07 | Power shortfall | ME | TD at 30 min | Producer at 60 min | Venue electrician; generator hire |
| WX-01 | Rain onset | ME on electrical safety | TD at 5 min | Producer at 5 min | — |
| WX-02 | Wind over threshold | Rigging Lead / structure engineer | TD executes | Producer at 5 min | Venue Duty Manager |
| WX-03 | Lightning | Safety Officer | TD executes | Producer at 5 min | Cancel rigging crew, seek shelter |
| WX-04 | Temperature extreme | TD for equipment | Safety Officer for people | Producer at 5 min | Venue Duty Manager |
| WX-05 | Condensation | TD at load-in | — | — | — |
| SC-01 | Unauthorised access | Crew member on channel | Head of Security at 60 s | Producer at 5 min | Venue security |
| SC-02 | Medical emergency | First aider on scene | Safety Officer at 60 s | Producer at 5 min | **EMS** |
| SC-03 | Evacuation | Venue Duty Manager | TD executes | Producer at 5 min | **Fire service** |
| SC-04 | Disruption | Head of Security; Show Caller for the room | TD at 60 s | Producer at 5 min | Police if assault |
| SC-05 | Theft | Producer at the desk | Head of Security at 60 s | Producer | **Police** (crime ref) |
| SC-06 | Credible threat | **Do not investigate.** Crew member steps away | Head of Security at 60 s | Producer is spokesperson | **Police** |
| LG-01 | Insurance lapse | Producer at the dock | Client Lead at 30 min | Client Lead | Broker for endorsement |
| LG-02 | Permit deficiency | Producer | Client Lead at 30 min | n/a | Issuing authority |
| LG-03 | Stream copyright | Stream Operator on comms | Producer at 5 min | Client Lead at 10 min | Platform / rights holder |
| LG-04 | Sub-contractor shortfall | TD at the dock | Producer at 60 min | Client Lead at 90 min | Local dry-hire |
| LG-05 | Data protection | Producer | Client Lead at 30 min | Client Lead | Regulator on formal complaint |
| LG-06 | Scope dispute | Producer | Client Lead at 30 min | n/a | — |

### 3.4 Calling the Client (or the Building) — Script Templates

The first sentence of any external call is the same regardless of who is calling. The script exists so the calm is automatic.

**Client-facing incident (S3 or S4):**
> "This is [name] from [production] on the [show] at [venue]. We have a [domain] situation at [time]. The room is [stable / on a hold / running a fallback]. Expected resolution is [minutes]. Next update in [interval]. Do you need anything from us right now?"

**Venue incident (life-safety):**
> "This is [name], Technical Director on the [show] at [venue]. [One sentence on the situation.] We are [isolating / sheltering / evacuating] [zone]. We need [one thing] from the building. I will call back at [time]."

**Police, fire, EMS:** operator's scripted call from the venue emergency card. Do not improvise.

### 3.5 Comms Discipline During an Escalation

1. The first person on comms **declares the situation** with the ID: "VN-01 confirmed, zone B, evacuating." No improvisation.
2. The next person **acknowledges** with the same ID and the action they are taking. No new facts.
3. The Show Caller holds the air for the next 60 seconds unless the situation is escalating. Talking over each other is the failure mode.
4. The TD, Producer, or Safety Officer **summarises** every 3 minutes for the room. The summary is what the client hears.
5. Logs are kept on the master sheet in real time. The log is the post-incident report.

---

## 4. Pre-Show Risk Assessment Checklist

This checklist is run between the end of technical rehearsal and the call of "house open". Each item is a single yes/no with a sign-off name. Anything not "yes" is a hole that must be closed or signed off as accepted by the appropriate role holder. The list is run cold, not from memory — a missed row at 17:30 is a catastrophic row at 21:15.

**Sign-off authority key:** TD = Technical Director, ME = Master Electrician, A1 = Front-of-House Audio, V1 = Video Lead, LX = Lighting Lead, SM = Stage Manager, SO = Safety Officer, PROD = Producer, NET = Network Lead, ST = Stream Operator, SEC = Head of Security.

### 4.1 Safety & Life-Safety (run by SO with venue Duty Manager)

| # | Item | Sign-off |
|---|------|----------|
| 1 | Fire alarm tested within the last 30 days; venue's procedure briefed to crew | SO + Venue |
| 2 | Fire exits clear, illuminated, and unobstructed | SO |
| 3 | First aiders rostered, named on the crew sheet, and on comms | SO |
| 4 | AED located, within 3 minutes of any position, pads in date, battery test passed | SO |
| 5 | Venue evacuation route walked by every crew lead | SO |
| 6 | Assembly point confirmed and briefed to all departments | SO + PROD |
| 7 | Crew injury log started; reportable-incident thresholds understood (RIDDOR / OSHA) | SO |
| 8 | Isolated smoke detector list agreed with venue fire officer; fire watch posted where required | SO + Venue |
| 9 | Permit register complete; pyro, flame, laser, drone, temporary structure, street closure all on site in paper | PROD |
| 10 | Crowd density and egress capacity checked against expected attendance | SO + Venue |
| 11 | Crowd management plan briefed; security posts identified | SEC |
| 12 | Sufficient trained security for the event risk profile (1:100 baseline, 1:50 high-salience) | SEC + PROD |

### 4.2 Audio Redundancy (run by A1)

| # | Item | Sign-off |
|---|------|----------|
| 13 | Console primary show file saved and loaded; redundant show file loaded on spare console | A1 |
| 14 | AES50 B / Dante secondary link active on a physically separate path | A1 |
| 15 | Manual A/B switch or XLR panel at the drive rack on the primary path | A1 |
| 16 | Spare handheld mic on a coordinated frequency, live in a muted DCA, ready for hand-off | A1 + A2 |
| 17 | Wireless Workbench / WSM scan clean; all transmitters within coordination window | A2 |
| 18 | Battery log started; spares at 100% for every active transmitter | A2 |
| 19 | IEM backup transmitters pre-tuned; wedge fallback patched and level-checked | A2 |
| 20 | Gain-before-feedback margin ≥ 6 dB on every open mic at show level | A1 |
| 21 | SPL meter logging at the measurement position; threshold, trip, and notification set | A1 |
| 22 | Off-site recording fed from the same source as the stream, recording confirmed | A1 |

### 4.3 Video Redundancy (run by V1)

| # | Item | Sign-off |
|---|------|----------|
| 23 | Primary projector / LED wall powered, lamp hours logged, redundant-lamp mode active where applicable | V1 |
| 24 | Spare projector (or LED tile kit) on site, lamp-tested within the last hour | V1 |
| 25 | Switcher A/B panel wired and tested; one physical action moves the whole show | V1 |
| 26 | Backup switcher powered, on the same sources, hold slide on PGM | V1 |
| 27 | Media server understudy machine mirroring the same project, timecode-locked | V1 |
| 28 | Show laptop holds every deck as delivered at T-24 h; tested at the show resolution | V1 |
| 29 | Hold slide armed on a dedicated switcher input, confirmed not on the same path as the show | V1 |
| 30 | Presenter laptops checked: extend mode, notifications off, sleep off, mains connected | V1 |
| 31 | Dongle kit complete at the lectern (USB-C, Mini-DP, HDMI, plus spares) | V1 |
| 32 | EDID managers locked on every non-built-in laptop input | V1 |

### 4.4 Network & Streaming (run by NET and ST)

| # | Item | Sign-off |
|---|------|----------|
| 33 | Primary internet circuit tested; speed, latency, and packet loss logged | NET |
| 34 | Bonded failover tested with both carriers active; IMEI verified | NET |
| 35 | Backup stream encoder pre-authenticated to the platform's backup ingest URL | ST |
| 36 | Local ISO recording (Hyperdeck or card) running and confirmed writing | ST |
| 37 | Cloud ROS reachable; printed ROS available at every console | NET + A1 + V1 |
| 38 | Stage demos on wired VLANs, not on attendee Wi-Fi | NET |
| 39 | DHCP scope sized for the show (1,022 usable minimum for 500 attendees) | NET |
| 40 | Static IPs reserved for production, Dante, and demo VLANs | NET |
| 41 | Comms system tested across all positions; battery indicator logged per headset | C (Caller) |
| 42 | Handheld UHF radios distributed to all positions, channel verified | C |

### 4.5 Power (run by ME)

| # | Item | Sign-off |
|---|------|----------|
| 43 | Load schedule complete, every circuit named, every device on a circuit | ME |
| 44 | All circuits loaded to ≤ 80% continuous maximum, measured with a clamp meter | ME |
| 45 | Phase rotation and voltage verified on every 3-phase distro at energisation | ME |
| 46 | UPS runtime tested under expected load; numerical figure written on the rack | ME |
| 47 | UPS powering the agreed critical core only (console, comms, encoder, primary media server) | ME |
| 48 | Generator (if used) fuel-dipped to full + 50% reserve; load-bank tested | ME |
| 49 | RCD grouping verified: time-delayed upstream, split loads across 30 mA downstream | ME |
| 50 | Outdoor connections elevated, IP-rated, with drip loops; wet-weather plan deployed | ME |

### 4.6 Crew, Comms & Content (run by PROD and C)

| # | Item | Sign-off |
|---|------|----------|
| 51 | Crew list complete, with deputies named for every position; deputies present in rehearsal | PROD |
| 52 | Show file / scene / patch documentation present at every position | TD |
| 53 | Pre-show brief delivered: weather, security, evacuation, comms test, hold protocols | PROD + SO |
| 54 | Every presenter confirmed at venue with T-60 min physical check | PROD |
| 55 | Late content cutoff enforced: nothing accepted after T-24 h unless verified by V1 | PROD + V1 |
| 56 | Embedded video and web links in every deck tested individually | V1 |
| 57 | Spotter / runner for the lectern briefed | SM |
| 58 | Translator (if applicable) confirmed and briefed on comms | PROD |

### 4.7 Legal, Insurance & Compliance (run by PROD)

| # | Item | Sign-off |
|---|------|----------|
| 59 | Certificate of insurance on site, meeting venue requirements (limit, additional insured, EL) | PROD |
| 60 | Music licensing receipts on site for every bed, sting, and walk-in track | PROD + ST |
| 61 | Filming and streaming notice on ticket terms and entrance signage | PROD |
| 62 | Opt-out mechanism available (lanyard, non-filmed block) | PROD |
| 63 | Sub-contractor certificates on site (production, rigging, security, cleaning) | PROD |
| 64 | Weather stop authority written and signed by client for any outdoor element | PROD + SO |

### 4.8 Final Go / No-Go

| # | Item | Sign-off |
|---|------|----------|
| 65 | All S5 (life-safety) items closed | SO + TD |
| 66 | All HIGH (≥ 10) scenarios have powered, patched, tested redundancy | TD |
| 67 | Comms test: every position ack'd by name, batteries logged | C |
| 68 | A/V failover executed once with a stopwatch; residual figures written on the matrix | TD |
| 69 | House open time confirmed to producer and to client | PROD |
| 70 | Master incident log opened and dated | C |

House opens when items 65–70 are signed. Anything below that is a hole, not a number.

---

## 5. Post-Incident Report Template

Every incident at S3 or above, plus every S2 that recurs across a season, gets a full report. The template is below. Reports are filed same-day or early next morning; the half-life of accurate recollection is hours, not days. The report is dated, signed, and shared with the TD, Producer, and Client Lead. A copy trains the next show — that is the entire point.

### 5.1 Header

| Field | Value |
|-------|-------|
| Report ID | PIR-YYYYMMDD-VenueInitials-### |
| Show / date / venue | |
| Reported by | (name, role) |
| Incident time (start) | |
| Incident time (resumed) | |
| Person declaring all-clear | |
| Matrix scenario ID(s) | (A-01, V-07, etc.) |

### 5.2 Description

Plain language, written in the active voice, restricted to what was observed. No opinion, no attribution. Three sentences minimum, ten sentences maximum.

```
Example: "At 14:23, the FOH console displayed an AES50 error on link A and 
audio to the room dropped for 11 seconds. A2 confirmed the link fault on the 
AES50 status page. A1 executed the manual A/B switchover to the secondary 
spare console and the room was back in audio at 14:24. The primary console 
was not re-engaged mid-segment. At 14:49, after the segment closed, A2 walked 
the primary snake run and found the stage-end tail unseated from a road case 
that had been moved during the previous break."
```

### 5.3 Timeline

A single column, in real time, with the matrix-ID where applicable. The timeline is the artefact of the record.

| Time (HH:MM:SS) | Event | Matrix ID | Logged by |
|------------------|-------|-----------|-----------|
| | | | |
| | | | |
| | | | |

### 5.4 Root Cause

The 5-Whys, written out, not implied. The root cause is the answer to the **fifth** Why, not the first. Stop before you reach a person — root causes are systemic, not personal.

```
Why 1:  Audio dropped to the room.
Why 2:  AES50 link A failed.
Why 3:  The link-A tail was unseated from the road case.
Why 4:  The road case was moved during the break without informing A2.
Why 5:  There is no documented protocol for moving any case containing a 
        snake tail during a break.
```

### 5.5 Mitigation (what we did)

Bulleted, in the order they happened. Distinguish what was **planned** from what was **improvised**. Improvised steps are the most valuable to write down — they are the next row that should exist in §2.

- [ ] Planned: A/B switchover to spare console (matrix protocol, A-01)
- [ ] Improvised: A2 walked the snake run before the next segment, found the unseated tail

### 5.6 Impact (audience, client, contract)

Concretely. The client conversation is technical, not advocacy.

- Audience experience: (seconds of degradation, screens affected, recording lost?)
- Stream impact: (encoder, VOD, platform dashboard)
- Client-facing impact: (segment lost, deliverable affected, refund exposure)
- Contract clauses touched: (cite the clause number from the production contract)

### 5.7 Lessons Learned

Restricted to things that are **generalisable** and **actionable**. "Be more careful" is not a lesson. "A2 should be notified before any road case is moved during a break" is a lesson, because it is actionable.

1. ...
2. ...

### 5.8 Action Items

Each item has an owner, a due date, and a verification method. The figure in §2 changes when these are closed.

| # | Action | Owner | Due | Verification |
|---|--------|-------|-----|--------------|
| 1 | Add a hard rule to the crew brief: no road case is moved during a break without A2's sign-off | TD | Next show | Brief deck updated; brief signed |
| 2 | Add a pre-show check that AES50 B is on a separate cable path | A1 | Next show | Pre-show checklist updated |
| 3 | Update matrix row A-09 with the road-case failure mode discovered today | TD | Within 24 h | Edit applied, signed by TD |

### 5.9 Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Reporter | | | |
| TD | | | |
| Producer | | | |
| Client Lead | | | |
| Safety Officer (if S5) | | | |

### 5.10 Where the Report Goes

- Same-day to the show file.
- Weekly summary to the production company with the **ten most recent reports** appended.
- After every tenth show, the post-incident reports are re-read against §2: the rows that fired are refined, the rows that did not fire at the expected rate are re-baselined, and the checklists in §4 are updated. The matrix is a living document, not a published one.
