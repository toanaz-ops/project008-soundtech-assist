# Tech Expos & Hackathons — Event Type SOP

## Event Profile

Tech expos and hackathons diverge from corporate general sessions in four ways, and every decision in this document traces back to one of them:

1. **The content is software, and software fails live.** A slide deck renders identically every time. A live demo depends on network reachability, third-party API availability, auth token freshness, container cold-start latency, and the presenter's laptop thermal state. Field-tracked failure rate for unrehearsed live demos: **30-40% hit a visible fault** — a stall over 10 seconds, an error state, a crash, or the wrong data on screen. Treat every live demo as a probabilistic event with a mandatory deterministic fallback.
2. **Device density runs 3-4x a normal conference.** Attendees bring a laptop, a phone, and at least one dev board, tablet, or second phone. Wi-Fi and DHCP get engineered at 3 devices per head, not 1.
3. **Participant-owned hardware sits on your network and your power.** You do not control the OS, the PSU leakage current, or what someone plugs in at 03:00.
4. **Hackathons run 24-72 hours continuously.** No dark period for repairs, no quiet load-out, staff rostered in shifts.

### Crew Roles (minimum viable)

| Role | Owns | Critical decision authority |
|------|------|-----------------------------|
| Show Caller | Running order, cue stack | Calls the cut to backup video |
| **Demo Wrangler** | Presenter laptops, demo state, stall clock | Declares a demo dead (see §1.4) |
| Network Lead (NOC) | All 3 VLANs, WAN, captive portal | Rate-limit changes, DHCP scope resize |
| A1 (Audio) | Console, RF coordination, stream audio bed | Mic mute at hard stop |
| V1 (Switcher) | ATEM, cameras, multiview | Source selection |
| Stream Operator | Encoder, RTMP targets, recordings | Failover to backup encoder |
| Stage Manager | Timer, presenter staging, hard stops | Enforces hard cut |
| Booth Liaison | Sponsor power/network/AV loans | Booth load approvals |

**Comms:** Hollyland Solidcom C1 Pro (6-headset full-duplex wireless intercom) — chosen specifically because it operates in **1.9 GHz DECT**, not 2.4 GHz. At a tech event the 2.4 GHz band is unusable for anything mission-critical. Back this with Motorola CP100d UHF handhelds on a licensed or coordinated frequency for load-in/load-out.

---

## 1. Live Demo Protocol

### 1.1 Why the Pre-Recorded Fallback Is Mandatory, Not Optional

The pre-record is not a contingency for lazy presenters. It is the only way to make demo content **deterministic in a non-deterministic environment**. The failure sources are independent and compound:

| Failure source | Typical incidence per demo | Notes |
|----------------|---------------------------|-------|
| Network / DNS / captive portal interception | 12-18% | Highest single cause. Venue Wi-Fi, corporate VPN split-tunnel, portal re-auth mid-demo |
| Third-party API fault (rate limit, 5xx, expired key) | 8-12% | Free-tier keys throttle exactly when a demo repeats a call |
| Cold start / first-request latency | 6-10% | Serverless and container platforms: 3-20 s on first hit |
| Application crash / unhandled exception | 5-8% | Often triggered by an input path never rehearsed |
| Laptop-side fault (thermal throttle, OS update, display negotiation) | 4-7% | See §1.7 |
| Wrong data state (test account emptied, seed data stale) | 3-6% | Someone reset the demo DB overnight |

Compounded across a 5-minute multi-step demo, **the probability that nothing visible goes wrong sits around 60-70%**. A pre-recorded capture converts that into 100% — the demo *will* play, at the *rehearsed length*, with *rehearsed narration*.

**Policy statement to put in the presenter agreement:**

> Every demo segment must be accompanied by a pre-recorded 1080p screen capture of the full demo path, delivered no later than **T-24 hours**. Presenters without a delivered and verified recording will present slides only. This is non-negotiable and applies to keynotes, sponsor sessions, and hackathon final pitches.
### 1.2 Recording Specification — OBS Studio

Send this verbatim to presenters. Deviation from these settings is the most common reason a delivered file is unusable (wrong aspect, VFR timing that drifts against narration, or 4K downscaled to mush).

**Settings → Video**

```
Base (Canvas) Resolution:    1920x1080
Output (Scaled) Resolution:  1920x1080          # must match canvas — no scaling
Downscale Filter:            (disabled/greyed when 1:1; else Lanczos)
Common FPS Values:           60                 # integer, NOT 59.94, NOT fractional
```

**Settings → Output → Output Mode: Advanced → Recording tab**

```
Type:                    Standard
Recording Format:        Hybrid MP4   (OBS 30.2+; else MKV, remux after)
Video Encoder:           NVIDIA NVENC H.264   (fallback: x264)
Audio Encoder:           FFmpeg AAC
Rescale Output:          UNCHECKED

--- NVENC H.264 ---
Rate Control:            CBR
Bitrate:                 8000 Kbps
Keyframe Interval:       2 s
Preset:                  P5: Slow (Good Quality)      # quality-oriented
Tuning:                  High Quality
Multipass Mode:          Two Passes (Quarter Res)
Profile:                 high
Look-ahead:              Enabled
Psycho Visual Tuning:    Enabled
Max B-frames:            2

--- x264 fallback ---
Rate Control:            CBR
Bitrate:                 8000 Kbps
Keyframe Interval:       2 s
CPU Usage Preset:        veryfast   (medium if the machine is idle)
Profile:                 high
Tune:                    (none)
```

**Settings → Audio**

```
Sample Rate:   48 kHz              # 48k, never 44.1k — matches the show clock end to end
Channels:      Stereo
Audio Bitrate (per track): 320 Kbps
Track 1:       Narration mic + desktop audio (the mix the switcher will use)
```

Rationale for each number:

- **1920x1080 / 60 fps** — 60 fps preserves smooth cursor motion, scroll, and UI animation. A 30 fps capture of a scrolling terminal or a dragged canvas reads as stuttery on a large screen and is the single most noticeable quality gap between a good and bad demo recording.
- **8 Mbps CBR** — CBR, not VBR or CQP, because the downstream switcher and streaming encoder need predictable decode load and the file needs a predictable size for offload. 8 Mbps at 1080p60 on screen content (large flat colour areas, sharp text edges) holds text crisp; 5 Mbps visibly softens 12 pt terminal text. VBR would starve exactly the high-motion moments you care about.
- **2-second keyframe interval** — makes the file cleanly seekable so the playback operator can scrub to a cue point in rehearsal, and matches the GOP the stream platform wants if the file is ever pushed direct to air.
- **48 kHz / 320 kbps AAC** — 48 kHz is the show-wide sample rate (Dante, ATEM, console all lock to 48 k). A 44.1 kHz file resampled live introduces avoidable drift and a resampler in the path. 320 kbps removes any question of coding artefacts on a voice bed that may get re-encoded twice more downstream (stream encoder, then platform transcode).

**Resulting file size:** 8 Mbps video + 0.32 Mbps audio ≈ **3.7 GB per hour**, ≈ **310 MB per 5-minute demo**. Budget accordingly on the playback machine.
### 1.3 Capture Hygiene (the part presenters get wrong)

| Item | Requirement | Why |
|------|-------------|-----|
| Capture source | **Display Capture** (Windows 10/11: Windows Graphics Capture method) or macOS Screen Capture. Not Window Capture. | Window Capture drops frames on GPU-composited windows and goes black when the window loses focus |
| Display scaling | Set OS scaling to **100%** on the capture display | Non-100% scaling makes OBS capture at a non-native size and rescale, softening text |
| Display resolution | Native **1920x1080** on the captured display | Capturing a 2560x1440 or 4K display then downscaling to 1080p destroys small text legibility |
| Cursor | **Visible** | The audience follows the cursor to understand the demo |
| Browser zoom | **125-150%** | 100% browser text at 1080p is unreadable past row 15 in a ballroom |
| Terminal font | **18-24 pt** minimum | See the 1/50 rule in §1.8 |
| Notifications | OS Focus Assist / Do Not Disturb **ON**; Slack, Teams, Mail quit | A DM preview on the keynote screen is a career event |
| Desktop | Clean; no personal files, no unrelated tabs, bookmark bar hidden | |
| Browser profile | Fresh profile, logged into demo accounts only | Autocomplete leaking real credentials or personal history |
| Narration | Recorded on the same take as the video, or delivered as a clean stem | Post-synced narration drifts and the presenter then talks over their own recording |
| Length | Matches the live demo runtime **±10%** | The recording has to slot into the same hole in the running order |

**Delivery:** MP4 to a single collection point (S3 pre-signed upload or the show Dropbox), filename `SESSION-ID_PRESENTER-LASTNAME_DEMO_v1.mp4`. The Demo Wrangler verifies each file by **playing it end to end on the actual playback machine** — not by opening it on their own laptop. Codec support and colour range differences are real and they bite at showtime.

### 1.4 Playback Trigger — When to Cut to the Recording

The decision must be pre-delegated and mechanical, because the person on stage is the *worst* judge of how long a stall has lasted. The Demo Wrangler runs a physical stopwatch the moment a demo action is initiated.

**Cut immediately, no discussion, on any of:**

| Trigger | Threshold / condition |
|---------|----------------------|
| Stall | **> 10 seconds** with no meaningful screen change — spinner, progress bar not advancing, blank pane, terminal with no output |
| Network error | Any visible error surface: HTTP 4xx/5xx page, `ERR_CONNECTION_*`, DNS failure, captive-portal redirect appearing |
| Crash | App exits, tab crash, kernel panic, blue screen, unhandled exception traceback on screen |
| Auth failure | Login rejected, token expired, MFA prompt to a device that is not in the room |
| Wrong data state | Demo account is empty, seed data missing, obviously incorrect output |
| Repeat attempt | Presenter retries the **same** action a second time and it fails again — do not allow a third attempt |

**Why 10 seconds:** audience tolerance for dead air on a screen is roughly 7-12 seconds before attention breaks and phones come out. Below 10 s a recovery still reads as "loading". Past 10 s it reads as broken, and the room's read of the *product* — not just the demo — changes. 10 s is also long enough that genuine cold starts (3-8 s) resolve on their own and you do not cut unnecessarily.

**The cut mechanics:**

1. Demo Wrangler calls on intercom: **"ROLLING B"** (unambiguous, two syllables, no similar-sounding cue in the stack).
2. V1 takes the switcher to the playback input. This is a **cut**, not a dissolve — a dissolve reads as intentional editing and draws attention; a hard cut reads as a source change the audience largely ignores.
3. A1 keeps the presenter mic **open** and unchanged.
4. Stage Manager gives the presenter the pre-briefed hand signal (flat palm, then rolling index finger) meaning *the recording is on screen, keep talking, narrate over it*.
5. Presenter's briefed line: **"Let's look at the recorded version so we don't waste your time."** Rehearsed, calm, no apology, no explanation of what broke.
6. Demo Wrangler works the problem off-air. Recovery back to live **only** at a natural segment boundary and only if the fault is confirmed fixed — never mid-narration.

**Do NOT:** narrate the failure, show the terminal to the audience to debug, ask the room "can everyone see that?", or let the presenter tether to a phone hotspot live on stage.
### 1.5 Playback Rig

A dedicated machine. Never play the fallback from the presenter's laptop — the presenter's laptop is the thing that is broken.

```
Machine:     Dedicated laptop (i5-1240P / M2 or better, 16 GB), on AC, battery >80%
Player:      mpv (preferred) or VLC — no on-screen controls, no playlist UI
Output:      HDMI → ATEM Mini Extreme ISO input 5, 1080p60, audio embedded
Display mode: Extended desktop, player fullscreen on the SECOND display only
             (operator keeps the file list and cue points on display 1)
State:       File preloaded, PAUSED on frame 1, one keypress from playing
Power plan:  Never sleep, never dim, screensaver off, OS updates deferred
Network:     DISCONNECTED (or VLAN 20 only). No cloud sync, no update checks.
```

`mpv` invocation that gives a clean, controls-free, correctly-parked output:

```bash
mpv --fullscreen --fs-screen=1 --screen=1 \
    --osc=no --osd-level=0 --no-input-default-bindings \
    --pause --start=0 \
    --keep-open=yes --image-display-duration=inf \
    --audio-device=hdmi \
    "SESSION-14_NAKAMURA_DEMO_v1.mp4"
```

`--keep-open=yes` matters: without it the player quits at end of file and the switcher input goes to a desktop or black. With it the last frame holds, which is a safe thing to be sitting on.

**Cue-point discipline:** for demos over 3 minutes, log chapter timecodes so the operator can enter mid-file if the live demo failed at step 4 of 6. Chapter marks in the file (`--chapters-file`) or a printed cue sheet taped to the playback laptop. A printed cue sheet has never crashed.

### 1.6 Rehearsal Requirements

**Minimum three full run-throughs per demo, timed, on the show rig.** Not three partial walk-throughs — three complete passes from first slide to last, stopwatch running, no stopping to fix things.

| Pass | When | Conditions | Pass criteria |
|------|------|-----------|---------------|
| 1 | T-7 days | Presenter's own environment. Purpose: find the broken steps. | Demo path completes; runtime logged as baseline |
| 2 | T-24 to T-48 h | **Show network (VLAN 20), show laptop or presenter laptop with show dongle, show display resolution.** | Completes on show infrastructure; runtime within 10% of baseline |
| 3 | T-2 h (day of, in room) | Full technical: real switcher, real mic, real lighting, real timer, Demo Wrangler on stopwatch, **fallback cut rehearsed at least once** | Runtime within 10% of allotted slot; ROLLING B cut executed cleanly |

**Timing rules:**

- Record all three runtimes. **Variance greater than 10% between passes means the demo is not stable** — either the demo gets simplified or it goes to recorded-only. High variance is almost always a network- or cold-start-dependent step, which is exactly the step that will fail on stage.
- If any pass exceeds the allotted slot, cut demo scope now. Content never shrinks under stage pressure; it expands.
- Pass 3 **must** include one deliberate failure injection: Wrangler calls ROLLING B at a random point, V1 cuts, presenter delivers the briefed line and narrates over the recording for 20 seconds. A fallback that has never been rehearsed does not exist.

### 1.7 Local-First Demo Architecture

Push presenters toward removing the dependency rather than mitigating it. In priority order:

1. **Fully local** — everything on the laptop: local DB, local services, `docker compose up`, mocked external APIs. Zero network dependency. This is the target.
2. **Local with recorded API fixtures** — real code path, external calls served from a local mock (WireMock, `msw`, VCR-style cassettes). Demonstrates the real integration logic without the real internet.
3. **Local server on VLAN 20** — demo backend on a machine in the room, on the isolated demo VLAN, wired. No WAN dependency.
4. **Remote with a warmed instance** — if the demo must hit production, warm it: fire the exact demo requests every 60 s starting 15 minutes before the slot to defeat cold starts, and confirm rate-limit headroom on the API key.
5. **Cold remote over public Wi-Fi** — never. Refuse this.

**Pre-flight for any demo touching the network:** confirm the API key is not on a free tier that throttles, confirm the token expiry is past the end of the session, and confirm nobody has a scheduled job that resets the demo database during show hours.

### 1.8 On-Screen Legibility (the 1/50 rule)

Text must be at least **1/50 of the image height** to be readable from the back of a typical ballroom. At 1080p that is **≥ 22 px cap height**. Practically:

- Terminal: 18-24 pt, and increase the terminal window's font, do not just zoom the whole desktop
- Browser: 125-150% zoom
- IDE: 16-20 pt, minimap off, sidebar collapsed
- **Light theme for slides, dark theme for terminals** — a dark IDE under high ambient stage wash loses all contrast on a projector; on an LED wall it is fine. Confirm against the actual screen in pass 3.
---

## 2. Network Segmentation Architecture — Three Isolated VLANs

### 2.0 Design Principle

Attendee traffic must be incapable of affecting show-critical audio and video. Not "prioritised below" — **incapable**. Dante is a real-time protocol with a fixed latency budget (typically 1 ms at 48 kHz) and no retransmission; a burst of attendee multicast or a broadcast storm from someone's misconfigured dev board will produce audible dropouts. The separation is enforced at layer 2 (separate VLANs, separate SSIDs) and at layer 3 (ACLs denying inter-VLAN routing), plus QoS as a third line of defence.

### 2.1 Address Plan

| VLAN | Name | Subnet | Usable hosts | Gateway | Purpose |
|------|------|--------|--------------|---------|---------|
| 10 | AV-STREAM | `10.10.10.0/24` | 254 | `10.10.10.1` | Dante, NDI, PTP, encoders, ATEM, PTZ cameras |
| 20 | DEMO | `10.10.20.0/24` | 254 | `10.10.20.1` | Presenter laptops, demo servers, playback rig |
| 30 | PUBLIC | `192.168.100.0/22` | 1022 | `192.168.100.1` | Attendee / participant Wi-Fi |
| 40 | BOOTH *(optional)* | `10.10.40.0/24` | 254 | `10.10.40.1` | Sponsor booth wired drops |
| 99 | MGMT | `10.10.99.0/24` | 254 | `10.10.99.1` | Switch/AP/controller management, admin only |

**VLAN 10 — AV/STREAM static assignment map:**

```
10.10.10.1              Gateway / L3 switch SVI
10.10.10.2  - .9        Network infrastructure (switch mgmt IPs if in-band)
10.10.10.10 - .49       Dante devices
                          .10  Behringer WING (console, PTP leader candidate)
                          .11  Stage box / DL16 or S16
                          .12  Dante Virtual Soundcard / recording PC
                          .15  Zoom F6 / backup recorder (if networked)
10.10.10.50 - .79       NDI sources
                          .50  ATEM Mini Extreme ISO
                          .51-.54  PTZ cameras 1-4
                          .60  NDI screen-share PC
10.10.10.80 - .89       Encoders
                          .80  Primary encoder PC (OBS)
                          .81  Teradek VidiU X (backup encoder)
10.10.10.90 - .99       Control surfaces, tally, PTZ controller (AW-RP60)
10.10.10.200 - .250     DHCP pool (reserved for temporary AV kit only)
```

**VLAN 20 — DEMO:**

```
10.10.20.1              Gateway
10.10.20.10 - .19       Demo servers (static; wired)
10.10.20.20 - .29       Local caches (registry mirror, npm proxy, apt cache)
10.10.20.30             Playback rig (when networked; normally disconnected)
10.10.20.100 - .200     DHCP pool, presenter laptops, 4-hour lease
```

**VLAN 30 — PUBLIC sizing math (read this before you deploy a /22):**

```
192.168.100.0/22  spans 192.168.100.0 – 192.168.103.255
                  = 1024 addresses, 1022 usable
DHCP pool         192.168.100.50 – 192.168.103.250  ≈ 968 leases
```

At 3 devices per person a /22 supports roughly **320 participants**. It is correctly sized for a 200-300 person event and **will exhaust** at 500 or 1000. Do not deploy /22 at scale and discover this at keynote start.

| Participants | Devices @ 3/head | Required usable | Recommended subnet | Usable |
|--------------|------------------|-----------------|--------------------|--------|
| 200 | 600 | ~700 | `192.168.100.0/22` | 1022 |
| 500 | 1500 | ~1700 | `10.30.0.0/21` | 2046 |
| 1000 | 3000 | ~3400 | `10.30.0.0/20` | 4094 |

Two mitigations that buy real headroom on any scope: **shorten the DHCP lease to 2 hours** (30 minutes if the scope is under pressure) so churn returns addresses, and remember that **concurrent** associations run about 1.5-2x headcount rather than the full 3x — the third device is usually asleep in a bag. Size the *scope* for 3x anyway; size the *bandwidth* for 1.5-2x.
### 2.2 VLAN 10 — AV/Stream: QoS and Bandwidth

**DSCP marking scheme (per Audinate's published Dante QoS guidance):**

| Traffic | DSCP | Hex | Queue | Notes |
|---------|------|-----|-------|-------|
| PTP time-critical (event msgs) | 56 (CS7) | 0x38 | Strict priority 1 | Sync/Delay_Req — highest |
| Dante audio | **46 (EF)** | 0x2E | Strict priority 2 | The number that matters most |
| PTP general / reserved | 8 (CS1) | 0x08 | Medium | |
| Stream egress to RTMP | 34 (AF41) | 0x22 | Medium-high | Deliberately **not** EF — see below |
| Everything else | 0 (BE) | 0x00 | Best effort | |

Keep the stream egress out of the EF queue. EF should contain only Dante and PTP. A 9 Mbps RTMP push with bursty TCP behaviour sharing a strict-priority queue with audio-over-IP is how you get audio dropouts that look like a Dante problem and are actually your own stream.

**Bandwidth budget on VLAN 10:**

| Source | Per-stream | Count | Total |
|--------|-----------|-------|-------|
| Dante 48 kHz/24-bit, ~1.5 Mbps/ch incl. overhead | 1.5 Mbps | 64 ch | ~96 Mbps |
| NDI (full/High Bandwidth) 1080p60 | 125-140 Mbps | 2 | ~280 Mbps |
| NDI|HX (compressed) 1080p60 | 8-20 Mbps | 4 | ~80 Mbps |
| RTMP egress | 9 Mbps | 1 | 9 Mbps |

Full NDI at ~130 Mbps per stream is the item that breaks naive designs: **four full-NDI 1080p60 sources will saturate a gigabit link**. Either use NDI|HX for anything that is not a primary program source, or move NDI to its own 10 GbE-uplinked switch, or keep full NDI streams to a maximum of three per gigabit segment with nothing else on it.

**Layer-2 settings on VLAN 10 (all mandatory):**

```
MTU:                    1500          # standard frames. Dante does NOT want jumbo.
IGMP snooping:          ENABLED, with an IGMP querier on the VLAN
Energy Efficient Ethernet (802.3az): DISABLED on every AV port
EEE/green-ethernet:     DISABLED globally
Spanning tree:          RSTP; AV access ports = portfast/edge
Flow control (802.3x):  DISABLED
Storm control:          ENABLED on access ports, broadcast 1%
```

EEE is the classic silent killer here: it parks the PHY in a low-power state and adds microseconds of wake latency that manifests as intermittent Dante clock instability. Turn it off and forget it exists. Likewise IGMP snooping without a querier is worse than no snooping — multicast groups age out and audio drops.

### 2.3 VLAN 20 — Speaker Demo

```
DHCP:               10.10.20.100–.200, lease 4 h
Internet:           PERMITTED (many demos need it)
Inter-VLAN:         DENIED to VLAN 10, 30, 99
Client isolation:   OFF   # presenters need laptop → demo server reachability
Guaranteed rate:    100 Mbps committed on the WAN
Marking:            AF41 (DSCP 34) for demo traffic during show hours
SSID:               EVENT-DEMO, WPA3-SAE (transition mode WPA2-PSK), NOT hidden
PSK:                unique, rotated daily, never printed on public signage
```

Hiding the SSID accomplishes nothing except making presenter laptops slower to associate and more likely to roam badly. Use a strong PSK instead.

**Wired is the default for demos.** Every presenter position gets a Cat6 drop on VLAN 20. Wi-Fi on VLAN 20 exists as the fallback, not the plan. A wired demo is immune to the single largest failure category in §1.1.

### 2.4 VLAN 30 — Public Wi-Fi

```
DHCP:               large scope per §2.1 table, lease 2 h (30 min under pressure)
Captive portal:     ENABLED — ToS acceptance, optional email capture
Per-client rate:    5 Mbps down / 2 Mbps up
Aggregate cap:      60% of WAN circuit (leaves 40% for demo + stream + ops)
Client isolation:   ENABLED  (station-to-station blocked)
mDNS / Bonjour:     BLOCKED (no AirPlay discovery flooding the air)
SSDP / UPnP:        BLOCKED
P2P / BitTorrent:   BLOCKED at the firewall
Inter-VLAN:         DENIED to 10, 20, 40, 99 — internet only
DNS:                forced to the local resolver (redirect :53, block DoH endpoints
                    only if the venue policy requires it)
```

Client isolation on VLAN 30 is not optional. Without it, one attendee's device scanning the /22 will generate enough ARP and unicast flood to degrade the whole airspace, and you have handed 300 strangers a flat L2 network with each other's laptops on it.

**Per-client 5/2 Mbps rationale:** 5 Mbps streams 1080p video, loads any web app, and pulls a package at a tolerable rate. It is low enough that 968 clients cannot collectively demand more than the circuit — and high enough that nobody complains. Uncapped attendee Wi-Fi at a hackathon means a handful of `docker pull` and OS-update clients consume the entire circuit within minutes of doors.
### 2.5 Switch Configuration — Cisco IOS (Catalyst / CBS350)

VLAN and SVI creation:

```cisco
enable
configure terminal
!
hostname EVENT-CORE-01
!
vlan 10
 name AV-STREAM
vlan 20
 name DEMO
vlan 30
 name PUBLIC
vlan 40
 name BOOTH
vlan 99
 name MGMT
!
interface Vlan10
 description AV / Dante / NDI / Encoders
 ip address 10.10.10.1 255.255.255.0
 no ip proxy-arp
 no shutdown
!
interface Vlan20
 description Speaker Demo
 ip address 10.10.20.1 255.255.255.0
 ip access-group ACL-DEMO-IN in
 no shutdown
!
interface Vlan30
 description Public Attendee Wi-Fi
 ip address 192.168.100.1 255.255.252.0
 ip access-group ACL-PUBLIC-IN in
 no ip proxy-arp
 no shutdown
!
interface Vlan99
 description Management
 ip address 10.10.99.1 255.255.255.0
 no shutdown
!
ip routing
```

Note the `/22` mask on Vlan30: `255.255.252.0`. Getting this wrong to `255.255.255.0` is a common and confusing fault — DHCP hands out `.101.x` addresses that cannot reach the `.100.1` gateway.
Isolation ACLs — this is the enforcement, not the QoS:

```cisco
ip access-list extended ACL-PUBLIC-IN
 remark --- Public VLAN 30: internet only, no internal reachability ---
 deny   ip any 10.10.10.0 0.0.0.255      log-input
 deny   ip any 10.10.20.0 0.0.0.255      log-input
 deny   ip any 10.10.40.0 0.0.0.255      log-input
 deny   ip any 10.10.99.0 0.0.0.255      log-input
 deny   ip any 192.168.100.0 0.0.3.255   
 permit ip any any
!
ip access-list extended ACL-DEMO-IN
 remark --- Demo VLAN 20: internet + own subnet, never AV or MGMT ---
 deny   ip any 10.10.10.0 0.0.0.255      log-input
 deny   ip any 10.10.99.0 0.0.0.255      log-input
 deny   ip any 192.168.100.0 0.0.3.255
 permit ip any any
```

The `deny ip any 192.168.100.0 0.0.3.255` line inside `ACL-PUBLIC-IN` blocks routed station-to-station traffic between public clients; wireless client isolation on the AP handles the same-AP case. You need both.

DHCP scopes on the switch (fine for an event; use a proper server if you want reporting):

```cisco
ip dhcp excluded-address 10.10.20.1 10.10.20.99
ip dhcp excluded-address 192.168.100.1 192.168.100.49
!
ip dhcp pool DEMO
 network 10.10.20.0 255.255.255.0
 default-router 10.10.20.1
 dns-server 10.10.99.53 1.1.1.1
 lease 0 4 0
!
ip dhcp pool PUBLIC
 network 192.168.100.0 255.255.252.0
 default-router 192.168.100.1
 dns-server 1.1.1.1 9.9.9.9
 lease 0 2 0
```

`lease 0 2 0` = 0 days, 2 hours, 0 minutes. Drop to `lease 0 0 30` the moment scope utilisation passes 80%.
QoS — classify, mark, and trust at the AV edge:

```cisco
mls qos
!
class-map match-any CM-PTP-CRITICAL
 match ip dscp 56
class-map match-any CM-DANTE-AUDIO
 match ip dscp 46
class-map match-any CM-STREAM
 match ip dscp 34
!
policy-map PM-AV-IN
 class CM-PTP-CRITICAL
  set dscp 56
  priority
 class CM-DANTE-AUDIO
  set dscp 46
  priority
 class CM-STREAM
  set dscp 34
  bandwidth percent 20
 class class-default
  bandwidth percent 10
!
! --- AV access ports: trust device DSCP, no negotiation, no EEE ---
interface range GigabitEthernet1/0/1 - 8
 description VLAN10 AV - Dante / NDI / ATEM / Encoders
 switchport mode access
 switchport access vlan 10
 spanning-tree portfast
 mls qos trust dscp
 no power inline police
 storm-control broadcast level 1.00
 no energy-efficient-ethernet
 no shutdown
!
! --- Presenter drops ---
interface range GigabitEthernet1/0/9 - 16
 description VLAN20 DEMO - presenter positions
 switchport mode access
 switchport access vlan 20
 spanning-tree portfast
 storm-control broadcast level 2.00
 no shutdown
```

Dante devices mark their own traffic EF/CS7 correctly. `mls qos trust dscp` preserves those markings rather than re-writing them to zero at the access port, which is the default behaviour and the reason QoS "does nothing" on a fresh switch.
Multicast, trunks, and AP ports:

```cisco
! Dante multicast flows and NDI discovery need snooping WITH a querier
ip igmp snooping
ip igmp snooping vlan 10
ip igmp snooping vlan 10 querier
ip igmp snooping vlan 10 querier address 10.10.10.1
no ip igmp snooping vlan 30 querier
!
! Uplink trunk to distribution / other room switches
interface TenGigabitEthernet1/0/1
 description UPLINK-TO-DIST
 switchport mode trunk
 switchport trunk allowed vlan 10,20,30,40,99
 switchport trunk native vlan 99
 mls qos trust dscp
 no shutdown
!
! Access-point ports: trunk, native = mgmt, tagged SSID VLANs
interface range GigabitEthernet1/0/17 - 24
 description WIRELESS-AP
 switchport mode trunk
 switchport trunk allowed vlan 20,30,99
 switchport trunk native vlan 99
 spanning-tree portfast trunk
 power inline auto
 no shutdown
!
end
write memory
```

VLAN 10 is deliberately absent from the AP trunk. Nothing wireless belongs on the AV VLAN — no Dante over Wi-Fi, ever.

**CBS350 CLI variance:** the Cisco Business 350 series uses a slightly different syntax for a few of these. `mls qos trust dscp` becomes `qos trust dscp` (with global `qos` and `qos advanced-mode`), and EEE is `no eee` per interface or `no eee enable` globally. Verify with `show qos` and `show eee` after applying.

**Verification commands to run before doors:**

```cisco
show vlan brief
show ip interface brief
show ip dhcp pool
show ip dhcp binding | count           ! watch scope utilisation
show ip access-lists ACL-PUBLIC-IN     ! hit counters prove the deny is working
show ip igmp snooping querier
show mls qos interface Gi1/0/1
show interfaces status err-disabled
show interfaces counters errors        ! CRC on an AV port = bad cable, fix now
```
### 2.6 Switch Configuration — Ubiquiti

UniFi switches are controller-driven; there is no persistent CLI config on a UniFi-adopted switch (SSH exists but changes are overwritten on provision). Configure in the controller, then verify by SSH.

**UniFi Network Application steps:**

```
Settings → Networks → Create New Network
  Name: AV-STREAM   | VLAN ID 10 | Host 10.10.10.1/24 | DHCP Server: Off (static AV)
  Name: DEMO        | VLAN ID 20 | Host 10.10.20.1/24 | DHCP 10.10.20.100-.200, lease 14400
  Name: PUBLIC      | VLAN ID 30 | Host 192.168.100.1/22 | DHCP .100.50-.103.250, lease 7200
                       Isolate Network: ENABLED   ← the one-click inter-VLAN block
  Name: BOOTH       | VLAN ID 40 | Host 10.10.40.1/24 | DHCP 10.10.40.100-.200

Settings → Profiles → Switch Ports
  Profile "AV-PORT"     : Native VLAN 10, Tagged: none, Storm Control BC 1%,
                          LLDP-MED on, 802.3az OFF, PoE per device
  Profile "DEMO-PORT"   : Native VLAN 20, Tagged: none
  Profile "AP-TRUNK"    : Native VLAN 99 (MGMT), Tagged: 20, 30, 40

Settings → WiFi → Create New
  SSID "EVENT-DEMO"  : Network DEMO(20),  WPA3/WPA2 transition, 5 GHz + 6 GHz
  SSID "EVENT-WIFI"  : Network PUBLIC(30), WPA2 or Open+Portal,
                        Client Device Isolation: ON
                        Bandwidth Profile: 5000 down / 2000 up Kbps
                        Multicast Enhancement (IGMPv3): ON
                        Multicast and Broadcast Control: ON
                        Minimum Data Rate 5 GHz: 12 Mbps  (2.4 GHz: disable band)

Settings → Security → Traffic & Firewall Rules
  LAN In  | Drop | Source: PUBLIC(30)  | Dest: AV-STREAM(10)
  LAN In  | Drop | Source: PUBLIC(30)  | Dest: DEMO(20)
  LAN In  | Drop | Source: DEMO(20)    | Dest: AV-STREAM(10)

Settings → Guest Hotspot → Enable, Portal: Terms of Service
```

**EdgeSwitch / EdgeRouter (real CLI, Vyatta-style) equivalent for the isolation rules:**

```bash
configure
set interfaces switch switch0 vif 30 address 192.168.100.1/22
set interfaces switch switch0 vif 30 description PUBLIC
set service dhcp-server shared-network-name PUBLIC subnet 192.168.100.0/22 \
    start 192.168.100.50 stop 192.168.103.250
set service dhcp-server shared-network-name PUBLIC subnet 192.168.100.0/22 lease 7200
set service dhcp-server shared-network-name PUBLIC subnet 192.168.100.0/22 \
    default-router 192.168.100.1
!
set firewall name PUBLIC-IN default-action accept
set firewall name PUBLIC-IN rule 10 action drop
set firewall name PUBLIC-IN rule 10 destination address 10.10.0.0/16
set firewall name PUBLIC-IN rule 10 log enable
set interfaces switch switch0 vif 30 firewall in name PUBLIC-IN
commit ; save
```

The `10.10.0.0/16` supernet covers VLANs 10, 20, 40, and 99 in one rule, which is why the address plan puts all internal VLANs inside `10.10.x.x` and public outside it. That choice makes the firewall trivially auditable.
### 2.7 Switch Hardware

| Model | Ports | PoE budget | Uplink | Use |
|-------|-------|-----------|--------|-----|
| Netgear M4250-10G2XF-PoE+ (GSM4212PX) | 8× 1G PoE+ | 240 W | 2× 10G SFP+ | **Preferred AV core.** AV-optimised profiles for Dante/NDI out of the box |
| Netgear M4250-40G8XF-PoE+ | 40× 1G PoE+ | 480/960 W | 8× 10G SFP+ | Larger AV core |
| Cisco CBS350-24P-4X | 24× 1G PoE+ | 195 W | 4× 10G SFP+ | General purpose, full CLI |
| Cisco C9200L-24P-4G | 24× 1G PoE+ | 370 W | 4× 1G SFP | Where the venue standard is Catalyst |
| Ubiquiti USW-Pro-24-PoE | 24× 1G PoE+ | 400 W | 2× 10G SFP+ | Public/attendee distribution |
| Ubiquiti USW-Pro-Aggregation | — | — | 28× 10G SFP+ | Aggregation for multi-room |

**Do not** put the show on unmanaged switches, and do not accept a shared venue switch for VLAN 10. Bring your own AV core, patch into the venue only for WAN.

**Redundancy:** dual uplinks in an LACP port-channel to distribution, core switch and router on UPS (§3.5). For the AV core specifically, a cold spare switch pre-configured with the same running-config on a USB stick, in the case, in the room.

---

## 3. Hackathon-Specific Requirements

### 3.1 Power Distribution

**The base unit of arithmetic:** a 120 V / 20 A branch circuit delivers 2400 VA nominal, but NEC Article 210.23(A) limits continuous load to 80% → **1920 W usable**. Design to 1920 W, never 2400 W.

**Per-participant load budget:**

| Device | Draw |
|--------|------|
| Laptop + charger (charging, under load) | 75 W |
| Phone / tablet charging | 15 W |
| Misc (second monitor share, USB hub, dev board) | 10 W |
| **Per participant** | **100 W** |

**Per-table math:**

```
8-person table   ×  100 W  =   800 W  =  6.7 A @ 120 V
10-person table  ×  100 W  =  1000 W  =  8.3 A @ 120 V

One 20 A circuit (1920 W usable):
  → 2 × 8-person tables   = 1600 W  (83% of usable — acceptable)
  → 1 × 10-person table   = 1000 W  (52% — conservative, recommended)
```

**Recommendation: one 20 A circuit per 10-person table.** The 48% headroom is not waste. It absorbs a soldering iron (40 W), a resin 3D printer (60-120 W), a hot glue gun (100 W), an e-bike or drone battery charger (100-300 W), and the gaming laptop with a 330 W PSU that someone will absolutely bring. At 83% utilisation the first surprise device trips the breaker and takes eight teams' unsaved work with it.
**Service sizing by headcount:**

```
3-phase 120/208 V, 100 A service:
  Per leg usable: 100 A × 0.8 = 80 A → 80 A × 120 V = 9600 W
  Three legs:                          28,800 W total
  @ 100 W/participant:                 288 participants

200 participants  → 100 A 3-phase           (comfortable, ~70% loaded)
500 participants  → 50,000 W → 200 A 3-phase (or 2 × 100 A)
1000 participants → 100,000 W → 400 A 3-phase
```

Always add the AV/production load on a **separate service or at minimum separate legs** from participant power. Production draw (PA amps, LED wall, lighting, switcher rack) is typically 6-15 kW and must never share a branch circuit with participant tables. A tripped participant breaker should never mute the PA.

**Distribution hardware:**

| Item | Model | Notes |
|------|-------|-------|
| Distro | Lex PowerRACK PR8-3D or Motion Labs D2N-1003 | 100 A 3-phase in, breakered 20 A duplex out |
| Distro (small) | Lex BB2A-100A "Bento Box" | 100 A in → 12× 20 A GFCI duplex |
| Feeder | 2/0 or 4/0 SOOW Bates/camlock | Per electrician; do not improvise feeder |
| Branch | 12/3 SOOW with 20 A Edison, ≤75 ft | See voltage drop below |
| Branch (long) | 10/3 SOOW, 75-150 ft | |
| Table box | Quad box (4× 20 A) per table | Flush to table leg, strain relieved |
| Power strip | Tripp Lite TLM615SA / Furman SS-6B, 15 A, integral breaker, 15 ft cord | **One per table position** |
| Cable protection | Checkers Yellow Jacket YJ5-125 (5-channel) or Guard Dog GD5X125 | ADA-compliant ramp profile |

**Voltage drop — why cable gauge is not optional:**

```
Vdrop = (2 × K × I × L) / CM        K = 12.9 (copper), CM = circular mils

12 AWG (6530 CM), 16 A load, 100 ft run:
  (2 × 12.9 × 16 × 100) / 6530 = 6.3 V  = 5.3% drop   ← EXCEEDS 3% target

10 AWG (10380 CM), 16 A load, 100 ft run:
  (2 × 12.9 × 16 × 100) / 10380 = 4.0 V = 3.3% drop   ← acceptable

10 AWG, 16 A, 75 ft:  3.0 V = 2.5% drop                ← good
```

Rule: **12 AWG up to 75 ft, 10 AWG from 75 to 150 ft, beyond 150 ft move the distro closer.** Excessive voltage drop shows up as laptop chargers running hot and cheap PSUs dropping out under transient load, which reads to participants as "the power is broken."
### 3.2 GFCI Requirements and the Cumulative Leakage Problem

**Code basis:** NEC Article 590.6(A) requires GFCI protection for all 125 V, single-phase, 15/20/30 A receptacle outlets in temporary installations. A hackathon in a ballroom is a temporary installation. Article 590.6(B)(2) permits an **assured equipment grounding conductor program** as the alternative for receptacles that are not 125 V/15-30 A — do not rely on this to avoid GFCI on participant tables. Provide GFCI. Verify local AHJ requirements; some jurisdictions and venues are stricter.

**Placement options:**
1. **GFCI at the distro** (preferred) — breakered GFCI outputs, one device protects one branch, all resets in one place staffed by production.
2. GFCI receptacle in each table quad box — more devices to fail, resets happen unsupervised by participants.
3. Portable GFCI in-line adapters — last resort, they walk off.

**The failure mode nobody plans for:**

A Class A GFCI trips at **6 mA ±1 mA** — meaning it may legitimately trip as low as **4 mA**. Every switch-mode laptop PSU has Y-capacitors from line and neutral to chassis ground, which pass a small, continuous, entirely normal leakage current to earth:

```
Typical laptop PSU leakage:  0.5 – 3.5 mA each  (65-100 W class, varies by brand)
Conservative planning value: 0.5 mA each

  6 PSUs × 0.5 mA = 3.0 mA   → 50-75% of trip threshold
 10 PSUs × 0.5 mA = 5.0 mA   → at or past a 4 mA-trip device
 12 PSUs × 0.5 mA = 6.0 mA   → NUISANCE TRIP, no fault present
```

Leakage is **cumulative and additive** on a single GFCI. The GFCI is working correctly; there is no fault; and it will keep tripping. This is the single most common power failure at hackathons and it is entirely predictable.

**Mitigation:**

| Rule | Detail |
|------|--------|
| **Cap 8-10 laptop PSUs per GFCI device** | Hard limit. Fewer if PSUs are unbranded. |
| Use more, smaller branches | Six 20 A GFCI branches at 8 PSUs each beats two branches at 24 |
| One GFCI per table, not per zone | Isolates the trip to one table, and makes the cause obvious |
| Log it | If a GFCI trips twice with no identifiable faulty device, redistribute the load — do not defeat the GFCI, ever |
| Never bypass | Removing GFCI protection to stop nuisance trips is not an option available to you |

**Cable management:**

- All floor crossings in cable ramp (Yellow Jacket / Guard Dog). Gaff tape alone is not acceptable across a walking path and is not ADA-compliant.
- Ramp profile must meet ADA slope: **≤1:12 for a change in level over 1/2 in**; 5-channel ramps are designed for this. Add high-contrast edge marking.
- Route branch runs under table skirts and along table legs, never across aisles.
- Strain-relieve every quad box to the table leg with a tie or Velcro so a pulled cable does not become a trip hazard or an arc.
- Label both ends of every branch: `DISTRO-A / CKT-7 / TABLE-14`.
- **No daisy-chained power strips** (NEC/OSHA and every fire marshal). One strip per table position, plugged directly into the quad box. Brief the staff to walk the floor hourly during a 24 h event and break up chains.
- Overnight charging: fire watch for continuously staffed events. **No lithium battery charging (drones, e-bikes, RC packs) unattended, and nothing charging in an egress path or blocking an exit.** Designate a supervised battery charging table on its own dedicated circuit, on a hard non-combustible surface, away from exits.
### 3.3 Wi-Fi Density Design

**Device count basis: 3 devices per participant.** Laptop + phone + (tablet | second phone | dev board | smartwatch on Wi-Fi). Count all three for **AP sizing and DHCP scope**, because an associated-but-idle device still consumes an association slot and still sends probe and keepalive traffic. Count 1.5-2x for **bandwidth**.

**Design target: 50 client associations per radio.** Below 40 is luxurious; 60-80 is where TCP retries and airtime contention become perceptible; past 100 per radio the cell collapses under management-frame overhead regardless of how fast the radio is.

| Participants | Devices (3x) | Radios needed | **AP count** | 5 GHz channel width | Notes |
|--------------|-------------|---------------|--------------|--------------------|-------|
| 200 | 600 | 12 | **10-12** | 40 MHz | Comfortable; 12 × 40 MHz channels available, minimal reuse |
| 500 | 1500 | 30 | **20-25** | **20 MHz** | Must drop to 20 MHz; 25 channels, ~1x reuse |
| 1000 | 3000 | 60 | **40-50** | **20 MHz** + 6 GHz | 20 MHz mandatory, add 6 GHz, reduce TX power hard |

Counts assume 5 GHz plus 6 GHz both carrying clients on Wi-Fi 6E hardware. On 5 GHz-only APs, add 30-40%.

**Channel planning (US / FCC):**

```
2.4 GHz : 3 non-overlapping channels (1, 6, 11)  — 20 MHz only
5 GHz   : UNII-1  ch 36-48    (4 × 20 MHz)
          UNII-2A ch 52-64    (4 × 20 MHz, DFS)
          UNII-2C ch 100-144  (12 × 20 MHz, DFS)
          UNII-3  ch 149-165  (5 × 20 MHz)
          = 25 usable 20 MHz channels | 12 × 40 MHz | 6 × 80 MHz
6 GHz   : 59 × 20 MHz | 29 × 40 MHz | 14 × 80 MHz   (Wi-Fi 6E/7 clients only)
```

**The channel-width tradeoff:** 80 MHz channels give a single client higher peak throughput and are the right answer in a sparse office. In a room with 25 APs they are catastrophic — only 6 non-overlapping channels exist, so every channel is reused 4+ times and co-channel interference means APs spend their airtime deferring to each other. **Aggregate capacity in a dense room is a function of channel count, not channel width.** Go to 20 MHz above ~12 APs.

**Radio configuration:**

| Setting | Value | Why |
|---------|-------|-----|
| 2.4 GHz | **Disabled on 70-80% of APs** | Only 3 channels; keep a few enabled for IoT/dev boards (ESP32, Pi Zero W) in a designated area |
| 5 GHz channel width | 20 MHz (dense) / 40 MHz (≤12 APs) | Above |
| 5 GHz TX power | **11-14 dBm** in dense rooms | Not max. High power creates large overlapping cells and clients that refuse to roam |
| 2.4 GHz TX power | 6-9 dBm if enabled | Must be below 5 GHz power to make band steering work |
| Minimum RSSI at cell edge | **-67 dBm** | Design coverage to this, not to "bars showing" |
| Minimum data rate (5 GHz) | **12 Mbps** | Kills 6/9 Mbps legacy rates that hog airtime |
| Minimum data rate (2.4 GHz) | 12 Mbps | Also disables 802.11b clients entirely |
| Legacy rate support | Disable 1, 2, 5.5, 6, 9, 11 Mbps | A single client at 1 Mbps can consume 30%+ of a cell's airtime |
| Band steering | Enabled | Push dual-band clients off 2.4 GHz |
| WPA/TKIP | **Disabled** | TKIP forces the whole cell to legacy protection |
| Multicast/broadcast control | Enabled | Blocks mDNS/SSDP flooding |
| Airtime fairness | Enabled | Stops one slow client dominating |
| Client isolation (public SSID) | Enabled | §2.4 |
| DFS channels | Enabled, but avoid near radar (coastal/airport) | Free capacity; a DFS hit moves an AP mid-event |

**AP hardware:** Cisco Catalyst 9166I or 9166D1 (directional, good for large rooms), Aruba AP-635/AP-655, Ruckus R770, Ubiquiti U6-Enterprise or U7-Pro. For 500+ headcount in a single hall, **directional/patch antennas aimed down and across from a high mount** materially outperform omnis on the ceiling — they shrink cells, which is exactly what you want.

**Mounting:** APs on stands or truss at 3-4 m, aimed at the seating, spaced 10-15 m in dense config. Never above a metal ceiling grid, never behind an LED wall, never inside a pipe-and-drape corner.
### 3.4 WAN Sizing and Local Caching (the hackathon-specific bottleneck)

**The thundering-herd problem.** At kickoff, every team simultaneously runs `docker pull`, `npm install`, `pip install`, `git clone`, and an IDE update. Consider 500 participants each pulling 1 GB of artefacts in the first 30 minutes:

```
500 × 1 GB = 500 GB in 1800 s
           = 277 MB/s
           = 2.2 Gbps sustained
```

No event WAN circuit absorbs that. Attempting it means a saturated link, 30-second DNS timeouts, and a room full of people who cannot start — during the exact window when the event's credibility is set.

**Two fixes, apply both:**

**(a) WAN sizing** — rule of thumb 1 Mbps sustained per concurrent device with a 5 Mbps per-client burst ceiling:

| Participants | Concurrent devices (~1.75x) | Minimum WAN |
|--------------|---------------------------|-------------|
| 200 | 350 | 350-500 Mbps |
| 500 | 875 | 1 Gbps |
| 1000 | 1750 | **1 Gbps minimum, 2 Gbps preferred** |

Order the circuit with a written SLA, a static IP block, and **no CGNAT** (CGNAT breaks inbound demo webhooks and complicates RTMP). Commission and speed-test it at least 7 days out, not on show morning.

**(b) Local artefact caches on VLAN 20, reachable read-only from VLAN 30.** This is what actually saves the event — it converts a 2.2 Gbps WAN demand into LAN traffic.

```
10.10.20.20   registry-mirror   Docker registry pull-through cache
10.10.20.21   npm-proxy         Verdaccio (or Nexus/Artifactory)
10.10.20.22   apt-cache         apt-cacher-ng
10.10.20.23   pypi-mirror       devpi
10.10.20.24   git-mirror        Local clone of the starter/template repos
```

Docker pull-through cache in one command:

```bash
docker run -d --restart=always --name registry-mirror -p 5000:5000 \
  -e REGISTRY_PROXY_REMOTEURL=https://registry-1.docker.io \
  -e REGISTRY_STORAGE_FILESYSTEM_ROOTDIRECTORY=/var/lib/registry \
  -v /srv/registry:/var/lib/registry \
  registry:2
```

Participant-side, published in the welcome pack and on table cards:

```bash
# Docker — /etc/docker/daemon.json, then: systemctl restart docker
{ "registry-mirrors": ["http://10.10.20.20:5000"] }

# npm
npm config set registry http://10.10.20.21:4873

# pip
pip config set global.index-url http://10.10.20.23/root/pypi/+simple/
pip config set global.trusted-host 10.10.20.23

# apt — /etc/apt/apt.conf.d/01proxy
Acquire::http::Proxy "http://10.10.20.22:3142";
```

**Pre-warm the caches during load-in** by pulling the images and packages the starter templates reference. A cold cache on the first pull helps nobody.

**Also send the pre-event email at T-3 days** telling participants to pull their base images, run their installs, and update their IDE and OS **before travelling**. This single email removes more WAN load than any hardware you can rent.
### 3.5 24-72 Hour Continuous Operation

| Concern | Provision |
|---------|-----------|
| Crew rotation | 3 shifts × 8 h. **Minimum overnight: 1 NOC + 1 AV tech + 1 venue/safety contact.** Never a lone operator overnight. |
| UPS | Core switch, router, ONT/WAN handoff, AP PoE injectors, NOC laptop. **APC SMT1500RM2U (1500 VA / 1000 W, ~25 min at half load)** or SMT2200RM2U for longer hold. Network gear only — do not put participant power on UPS. |
| Generator | Only if the venue service is unreliable. If used, a UPS between generator and network gear is mandatory (generators produce dirty power on load step). |
| Overnight quiet hours | 00:00-06:00. PA off or bed music only, house lights to 40%, no announcements. |
| Overnight network | Do not push config changes overnight without a second person and a rollback. The 03:00 "quick fix" is how events die. |
| Monitoring | UptimeKuma or LibreNMS on VLAN 99 polling gateway, each switch, each AP, WAN, caches. Alerts to the on-call phone **and** the intercom channel. |
| Power strip discipline | Hourly floor walk to break up daisy chains and check for hot connectors |
| Fire watch | Per venue/AHJ requirement for overnight occupancy |
| Consumables restock | Gaff tape, cable ties, spare 15 A strips, HDMI cables, USB-C dongles, AA/AAA batteries |

**Label the show-critical power.** Every UPS cord, switch PSU, and AP injector gets a bright tag: **DO NOT UNPLUG — EVENT NETWORK**. At 04:00 a participant looking for an outlet will unplug the least-obviously-important thing they can find, and that is your core switch.

### 3.6 Judging Setup

**Presentation timer:**

| Option | Model / product | Notes |
|--------|----------------|-------|
| **Preferred** | **StageTimer.io** | Browser-based, syncs unlimited viewers over the network. Operator controls from the booth; separate views for stage, presenter confidence monitor, and judges. Runs on VLAN 20. |
| Alternative | Irisdown Presentation Timer | Windows, dual-screen, integrates with PowerPoint |
| Hardware | DSAN PerfectCue PC-AS + Limitimer | Physical, no network dependency, cue light to presenter |
| Cheap and reliable | 55" display running a fullscreen timer page + a phone stopwatch as backup | |

The ATEM has no timer function. Do not plan around one.

**Timing structure for final pitches:**

```
3:00   Pitch (hard slot)
2:00   Judge Q&A
0:30   Warning bell + amber on the countdown display
3:00   Red + double bell
3:15   HARD STOP — Stage Manager cues A1 to mute the mic
```

Announce the hard-stop rule at the participant briefing **and** enforce it on team one. Enforcement on team one costs 15 seconds of awkwardness; non-enforcement costs 40 minutes of schedule by team twelve and the last teams present to an empty room.
**Scoring system:**

| Platform | Strengths | Watch out for |
|----------|-----------|---------------|
| **Devpost** | Industry standard for hackathons. Submission intake, judge assignment, weighted criteria, tie-break handling, public gallery. | Judge sessions time out; judges lose unsaved scores. Brief judges to submit each project before moving on. |
| Judgify | Flexible custom rubrics, good for expo-style multi-round | Less familiar to participants |
| Google Forms + Sheets | Zero cost, works offline-ish, fully controllable | You own the normalisation math and the tie-breaks manually |

**Rubric — 5 criteria, 1-5 scale:**

```
Technical Execution   ×2 weight   Does it work? Is the implementation sound?
Innovation            ×2          Novelty of approach
Impact / Usefulness   ×2          Does it solve a real problem?
Design / UX           ×1
Presentation          ×1
                      ─────
Max raw score: 5 × (2+2+2+1+1) = 40
```

**Normalise across judges.** Judges score on different internal scales — one averages 3.2, another averages 4.4. Comparing raw totals from different judge panels is invalid. Convert each judge's scores to **z-scores within that judge's own set**, then average the z-scores per project:

```
z = (score − judge_mean) / judge_stdev
```

Devpost does a version of this internally; if you are on Sheets, do it explicitly. Every project must be seen by at least **3 judges**, and no project by fewer, or normalisation has nothing to work with.

**Declare the tie-break rule before judging opens**, in writing: highest Technical Execution, then highest Impact, then head judge decides. Deciding a tie-break after the scores are in looks like — and functionally is — an arbitrary decision.

**Judge kit:**

- Printed rubric sheets and pens. Non-negotiable offline backup; when Devpost sessions expire mid-round, paper is the recovery path (photograph each sheet immediately, re-enter later).
- Device on **VLAN 20** with the PSK, not public Wi-Fi.
- Printed schedule with team names, table numbers, and pitch order.
- Head judge has the tie-break authority and the scoring deadline.

**Leaderboard display:**

- 55" display or a stage screen region, fed from the scoring platform or a Sheets-backed HTML page.
- **Hidden from teams during judging.** A visible running leaderboard biases later judges (anchoring) and demoralises teams mid-round. Reveal at the awards segment only.
- Refresh manually or on a 60 s poll; a live-updating board on screen invites the audience to watch scores instead of pitches.
- Have a static PNG of the final standings ready as fallback in case the web board fails at the reveal.

**Submission freeze:** hard deadline enforced by **git commit hash** recorded at the cutoff, with the Devpost submission timestamp as the authoritative record. Announce that commits after the hash are not judged. This ends every "we pushed a fix at 09:02" argument before it starts.
---

## 4. Streaming and Recording Infrastructure

### 4.1 Camera Package — and an important correction on the AW-UE4

**The Panasonic AW-UE4 is not a mechanical PTZ camera.** It is a compact 4K box camera with a fixed ultra-wide lens and **ePTZ** (electronic pan/tilt/zoom — cropping and panning within the 4K sensor to produce a 1080p output). It has no motors. It is excellent and cheap for a locked-off wide, an audience shot, or an overhead, and it takes PoE with HDMI and USB-C out. It is the wrong choice if you need to follow a presenter walking a stage.

Spec the package accordingly:

| Model | Type | Zoom | Output | Control | Role |
|-------|------|------|--------|---------|------|
| **AW-UE4** | 4K **ePTZ**, fixed wide lens | Digital crop only | HDMI, USB-C (UVC), PoE | Web UI, Panasonic PTZ Control Center. **No RS-422.** | Locked wide, audience, overhead, second angle. 2-3 of these. |
| **AW-UE20** | True 4K PTZ, motorised | Optical | HDMI, SDI, PoE+ | IP, RS-422 | Entry motorised PTZ |
| **AW-UE40 / UE50** | True 4K PTZ | **24x optical** | HDMI/SDI (UE50 has SDI), PoE+ | IP, RS-422, AW-RP60 | **Primary presenter follow camera** |
| **AW-UE80 / UE100** | True 4K PTZ | 24x optical | SDI/HDMI/**NDI\|HX** | IP, RS-422, NDI | Where NDI over the AV VLAN is preferred to HDMI runs |
| **AW-UE150** | Flagship 4K PTZ | 20x optical | 12G-SDI, HDMI, optical | IP, RS-422 | Large-stage keynote |
| **AW-RP60** | PTZ controller | — | — | IP / serial | Joystick control of up to 200 cameras; assign 1-4 to the switcher inputs |

**Minimum viable multi-camera plan for a keynote + pitch stage:**

```
CAM 1  AW-UE40  (24x PTZ)   Stage right, presenter follow / medium
CAM 2  AW-UE40  (24x PTZ)   Stage left, wide-to-tight, judge reactions
CAM 3  AW-UE4   (ePTZ)      Locked wide, full stage — the safe shot
CAM 4  AW-UE4   (ePTZ)      Audience / reverse
```

CAM 3 is the shot you cut to when anything goes wrong with a moving camera. Always have a locked wide.

**Cabling:** HDMI over active optical (Ruipro / Monoprice SlimRun AOC) for runs over 10 m — passive HDMI beyond 10 m at 1080p60 is a coin flip and beyond 15 m it will not work. Alternatively use the UE80's NDI|HX output over the Cat6 already going to the camera for PoE, which collapses two cable runs into one. Budget the NDI bandwidth per §2.2.

### 4.2 Switcher — ATEM Mini Extreme ISO

```
Inputs           8 × HDMI (all inputs have independent standards converters —
                 mismatched presenter laptop resolutions are handled in hardware)
Outputs          2 × HDMI (assignable: Program, Multiview, Aux, clean feeds)
USB-C #1         Webcam out — appears as a 1080p UVC device to OBS
USB-C #2        External disk — ISO recording target
Audio in         2 × 3.5 mm stereo line
Monitoring       2 × headphone out
Network          Ethernet — built-in RTMP/RTMPS streaming engine (no PC required)
Keying           4 upstream keyers + chroma, 2 DVE, SuperSource
Media            2 media players (stills/clips loaded from ATEM Software Control)
Multiview        Up to 16 views on one HDMI output
ISO recording    All 8 inputs + Program, H.264, plus a DaVinci Resolve
                 .drp project file with the cut timeline reconstructed
```

**Input map (fix this and print it, taped to the switcher):**

```
IN 1   CAM 1  — PTZ presenter follow
IN 2   CAM 2  — PTZ wide/reaction
IN 3   CAM 3  — locked wide  ← the safe shot
IN 4   CAM 4  — audience
IN 5   PLAYBACK RIG          ← ROLLING B target (§1.5)
IN 6   PRESENTER LAPTOP A    (via switcher/scaler at the lectern)
IN 7   PRESENTER LAPTOP B    (hot-swap position)
IN 8   TIMER / LEADERBOARD / holding slide
```

Presenter laptops on 6 and 7 as a pair matters: the next presenter connects and confirms signal on 7 while 6 is live, which removes the dongle fumble from the transition.
### 4.3 Signal Flow

```
CAM 1-4 ──HDMI/AOC──┐
PLAYBACK RIG ───────┤
PRESENTER A/B ──────┼──▶ ATEM Mini Extreme ISO
TIMER/GFX ──────────┘         │
                              ├──▶ HDMI OUT 1: PROGRAM ──▶ house LED wall / projector
                              ├──▶ HDMI OUT 2: MULTIVIEW ──▶ 24" booth monitor
                              ├──▶ USB-C #1 (UVC 1080p) ──▶ Encoder PC (OBS)
                              │                                 │
                              │                                 ├─▶ RTMP primary  (YouTube)
                              │                                 ├─▶ RTMP secondary (Twitch/LinkedIn)
                              │                                 └─▶ LOCAL RECORD → NVMe
                              ├──▶ USB-C #2 ──▶ Samsung T7 Shield 2TB (ISO record)
                              └──▶ Ethernet ──▶ built-in RTMP engine (BACKUP path,
                                                 hot standby, different stream key)

Behringer WING ──Matrix Out 1/2──▶ ATEM 3.5 mm audio in  (program audio bed)
              └──USB / Dante────▶ Isolated multitrack audio backup
```

**Two independent stream paths, deliberately.** The ATEM's built-in streaming engine and the OBS encoder PC are separate devices with separate encoders. Primary is OBS (needed for lower thirds, timer overlay, sponsor bugs, scene composition). If the encoder PC dies, the ATEM's internal engine goes live on a second stream key with no graphics but with picture and sound. Configure and test both; leave the ATEM path armed and stopped.

### 4.4 Stream Encoding

**Primary — OBS on the encoder PC:**

```
Video capture:   ATEM Mini Extreme via USB-C, "Video Capture Device", 1920x1080 @ 60
Audio:           ATEM embedded (from WING matrix), 48 kHz stereo

Output → Streaming:
  Encoder:            NVIDIA NVENC H.264  (GPU: RTX 3060 / A2000 or better)
  Rate Control:       CBR
  Bitrate:            8000 Kbps           (9000 for high-motion content)
  Keyframe Interval:  2 s                 ← required by YouTube/Twitch, non-negotiable
  Preset:             P4: Medium / Low-Latency Quality
  Profile:            high
  B-frames:           2
  Audio Bitrate:      160 Kbps stereo AAC (platform re-encodes; 320 is wasted here)

Output → Recording (simultaneous, different settings):
  Bitrate:            20000 Kbps CBR      ← archive quality, not stream quality
  Path:               D:\REC  (dedicated NVMe, NOT the OS drive)
  Format:             Hybrid MP4
  Automatic File Splitting: every 15 min or 4 GB
```

Automatic file splitting is a real protection: an unsplit 30-hour recording that hits a fault is one corrupt file, while a split recording loses at most 15 minutes.

**Backup — Teradek VidiU X:**

```
Input:      HDMI, up to 1080p60
Codec:      H.264, up to ~10 Mbps
Connectivity: Ethernet (use this), Wi-Fi, or USB LTE modem
Recording:  SD card, records while streaming (third independent recording)
Bonding:    Teradek Sharelink — combines Ethernet + Wi-Fi + LTE into one
            reliable session; the correct answer for a venue with a poor circuit
Power:      Internal battery + DC — survives a brief power event
```

The VidiU X on Sharelink with an LTE modem attached is the only path that survives a total venue WAN failure. For a keynote being watched by press or investors, that is worth the rental.
### 4.5 Bitrate Ladder

**Ingest (what you push).** One layer only — you push a single high-quality stream and the platform builds the ABR ladder:

| Source | Resolution | FPS | Video bitrate | Audio | Total |
|--------|-----------|-----|---------------|-------|-------|
| Primary ingest | 1920×1080 | 60 | 8000 Kbps CBR | 160 Kbps | **8.16 Mbps** |
| High-motion variant | 1920×1080 | 60 | 9000 Kbps CBR | 160 Kbps | 9.16 Mbps |
| Constrained-uplink fallback | 1280×720 | 30 | 3500 Kbps CBR | 128 Kbps | 3.63 Mbps |

**Platform-generated ladder** (YouTube/Twitch transcode; listed so you know what viewers actually receive and can sanity-check quality complaints):

```
1080p60   6000 – 9000 Kbps
1080p30   4500 Kbps
720p60    3500 – 4500 Kbps
720p30    2500 Kbps
480p30    1000 – 1500 Kbps
360p30      600 – 800 Kbps
```

Twitch only transcodes for partners/affiliates or when capacity allows — a non-partner channel pushes 8 Mbps and viewers on poor connections get buffering with no lower rung to fall to. If your audience is bandwidth-constrained and you are not partnered, **push 720p60 at 4500 Kbps** instead, or use YouTube as primary.

**Self-hosted / SRT to a cloud transcoder** — encode the ladder yourself:

```
1080p60  →  8000 Kbps,  keyint 2 s,  H.264 high
 720p60  →  4500 Kbps,  keyint 2 s
 720p30  →  2500 Kbps,  keyint 2 s
 480p30  →  1200 Kbps,  keyint 2 s
```

Keep the keyframe interval identical across every rung. Mismatched GOPs break segment-aligned ABR switching and viewers see a stall on every quality change.

**Uplink requirement:**

```
Stream bitrate            8.16 Mbps
× 3 headroom factor    =  24.5 Mbps  dedicated, committed upload
```

3x, not 1.2x. TCP-based RTMP is bursty, competes with the retransmit window, and shares the circuit with attendees and demos. The stream gets a **guaranteed 25 Mbps** carved out of the WAN and marked **AF41 / DSCP 34** per §2.2 — never left to compete on best-effort with a room of 1000 devices. If you are running dual RTMP targets, double it to 50 Mbps.

### 4.6 Backup Recording — Four Independent Layers

Redundancy only counts when the layers share no common failure. These four share no drive, no host, and no codec path:

| Layer | Device | Target | Format | Notes |
|-------|--------|--------|--------|-------|
| 1 | **ATEM Extreme ISO** | Samsung T7 Shield 2 TB USB-C SSD | H.264, all 8 inputs + Program | Needs **≥ 500 MB/s sustained**. Verify against Blackmagic's supported-disk list and test with Blackmagic Disk Speed Test before the show. |
| 2 | **OBS on encoder PC** | Dedicated internal NVMe (`D:\REC`) | Hybrid MP4, 20 Mbps | Separate host, separate encoder, separate disk from layer 1 |
| 3 | **Camera-internal SD** | UHS-I U3 / V30 in each PTZ that supports it | Camera codec | Survives total control-room failure |
| 4 | **Isolated audio** | WING USB recorder, or Zoom F6 in **32-bit float** | WAV | 32-bit float is unclippable — a mic hit that destroys the video's audio is fully recoverable here |

**Cloud sync, running continuously alongside the local recordings:**

```bash
# Every 15 min, throttled so it never touches the show bandwidth budget.
# Runs on the encoder PC, egress on VLAN 20, hard-capped at 20 Mbit.
while true; do
  rclone copy /d/REC s3:event-2026-archive/program/ \
    --bwlimit 20M \
    --transfers 2 \
    --min-age 2m \
    --log-file /d/REC/rclone.log --log-level INFO
  sleep 900
done
```

`--min-age 2m` stops rclone from uploading the file OBS is actively writing. `--bwlimit 20M` is not optional: an unthrottled multi-gigabyte upload will eat the stream's headroom and you will debug it as a "streaming problem."
### 4.7 Storage Math — Do This Before You Buy Drives

```
Stream archive @ 8 Mbps      =  8 / 8 × 3600 / 1024      ≈  3.5 GB/hr
OBS local record @ 20 Mbps   = 20 / 8 × 3600 / 1024      ≈  8.8 GB/hr
ATEM ISO, 9 streams @ ~45 Mbps each = 405 Mbps           ≈ 178 GB/hr   ← the problem
```

A 30-hour hackathon:

```
Program stream archive:   30 × 3.5  GB  =    105 GB    fine
OBS local record:         30 × 8.8  GB  =    264 GB    fine on a 1 TB NVMe
ATEM ISO full duration:   30 × 178  GB  =  5,340 GB    ← 5.3 TB. Not happening on a 2 TB SSD.
```

**Therefore: run ISO recording only on the segments that will actually be edited.** Opening keynote, sponsor sessions, final pitches, awards — realistically about 4 hours:

```
ATEM ISO, 4 hours:  4 × 178 GB = 712 GB   → comfortable on a 2 TB T7 Shield
```

For the remaining ~26 hours (ambient floor coverage, overnight), record Program only via OBS. Arm and disarm ISO from ATEM Software Control as part of the segment cue.

**Offload protocol** — do this at the end of every major segment, not at the end of the event:

1. Stop recording, wait for the file to finalise (ATEM: wait for the disk indicator to clear).
2. Copy, never move, to a second physical drive.
3. Verify with checksums before deleting anything:
   ```bash
   # Windows
   certutil -hashfile "SEGMENT-03.mp4" SHA256
   # macOS / Linux
   shasum -a 256 SEGMENT-03.mp4
   ```
4. Spot-play the copy — first 10 s, middle, last 10 s.
5. Only then clear source media, and only if a third copy exists in the cloud.

### 4.8 Audio for Stream and Lip Sync

**Program audio bed** comes from the console, not from a camera mic. On the Behringer WING, use a **Matrix output** rather than a Main output so the stream mix is independent of house level — the house PA level changes during the show, the stream mix must not.

```
WING Matrix 1/2  →  stream mix:  presenter mics, playback audio,
                    ambient/audience mic at −20 dB for room feel
WING Main L/R    →  house PA (independent)
```

Feed Matrix 1/2 to the ATEM's 3.5 mm line input, or keep it in the digital domain via Dante/USB into the encoder PC if you want the stream mix built in OBS. The 3.5 mm path is simpler and one less failure point.

**Lip sync.** Every HDMI camera and every scaler adds latency, and they do not all add the same amount. Audio arrives ahead of video, so audio must be delayed to match.

Per-input delay on the ATEM (Audio tab in ATEM Software Control, per input, in ms):

```
Typical values to start from:
  AW-UE40 via HDMI direct        30 – 60 ms
  AW-UE4 via HDMI                20 – 40 ms
  NDI|HX source into OBS        100 – 200 ms  ← the big one
  Presenter laptop via scaler    40 – 80 ms
```

**Measure, do not guess. Clap test:**

1. Stand in frame, in front of the live camera, on mic.
2. Single sharp clap. Record 10 seconds through the full chain, including the encoder.
3. Open the recording in Resolve or Premiere and read the offset between the audio transient and the video frame where the hands meet.
4. Enter that offset as audio delay on that input.
5. Repeat **per camera** — they differ, and cutting between two cameras with different delays produces sync that drifts on every cut.

Do this at load-in, and re-verify after any change to the video chain. A 100 ms sync error is clearly visible to a stream audience and is the most common complaint on hackathon streams.
---

## 5. Sponsor Booth Support

### 5.1 Power per Booth

Standard 10×10 ft booth allocation: **one 20 A / 120 V duplex outlet, 1920 W usable.**

Typical booth load:

| Item | Draw |
|------|------|
| 55" LED display | 120 W |
| Laptop + charger | 75 W |
| LED booth lighting (2× bar) | 60 W |
| Phone/tablet chargers, small gear | 45 W |
| **Typical total** | **300 W** |

At 300 W, six booths would theoretically fit one 20 A circuit. **Design to three booths per 20 A circuit** (900 W, 47% loaded). The headroom absorbs the sponsor who arrives with a second display, a coffee machine, or a demo rig nobody declared — and it means one booth's fault does not dark three neighbours plus itself.

**Load declaration.** Every sponsor submits declared wattage at **T-10 days**. Anything above 500 W gets a **dedicated 20 A circuit** and is charged for it. Trigger items:

| Demo type | Draw | Provision |
|-----------|------|-----------|
| VR/GPU workstation (RTX 4090 class) | 600-1000 W | Dedicated 20 A |
| FDM/resin 3D printer | 60-350 W | Dedicated 20 A + heat/fume check |
| Robotics arm / CNC demo | 500-1500 W | Dedicated circuit, possibly 208 V — involve the electrician |
| Coffee machine / kettle / warming plate | 1000-1500 W | Dedicated 20 A. Common and always undeclared. |
| Large LED video wall | 400-1500 W | Dedicated, per m² spec |
| Server rack / edge appliance | 400-1200 W | Dedicated + UPS |

Undeclared loads discovered on site get plugged in only after the Booth Liaison confirms circuit capacity. "Just plug it into the neighbour's strip" is how you take down a row.

GFCI applies to booths exactly as to participant tables (§3.2), including the cumulative-leakage cap.

### 5.2 Network per Booth

| Item | Spec |
|------|------|
| Wired drop | 1× Cat6, 1 Gbps, one per booth |
| VLAN | **VLAN 40 (BOOTH)** where available, otherwise VLAN 30 with a static reservation |
| **Never** | VLAN 10. Sponsor equipment does not go on the AV VLAN under any circumstance. |
| Rate limit | **25 Mbps down / 10 Mbps up** per booth (relaxed vs public — sponsors run live demos) |
| Addressing | Static DHCP reservation per booth MAC, documented in the booth sheet |
| Inter-booth | Isolated from other booths and from VLAN 10/20/99; internet only |
| Extra drops | Available at cost, T-10 days notice, second drop shares the booth rate limit |
| Booth Wi-Fi | Public SSID only. Sponsors wanting reliable wireless get a wired drop and their own travel router on it. |

Booths are untrusted third-party equipment, operated by people who are not your crew, plugged in and unplugged repeatedly over the event. Treat the booth VLAN with the same suspicion as public.

### 5.3 Signage Specifications

| Item | Spec |
|------|------|
| Booth ID sign | **22 × 28 in**, 1/4 in foam core, full colour one side |
| Hanging banner | **8 × 3 ft**, 13 oz vinyl, 1 in grommets at corners + 2 ft centres |
| Table throw | 6 ft or 8 ft, 4-sided, dye-sublimated |
| Digital signage | **1920 × 1080, 16:9**. MP4 (H.264, 8 Mbps, 48 kHz AAC) or PNG. Loop under 90 s. |
| Safe margin | **0.25 in** on all print; keep text and logos inside it |
| Bleed | 0.125 in |
| Print resolution | 150 dpi at final size minimum (300 dpi for anything under 11 × 17 in) |
| Colour | CMYK for print, sRGB for digital |
| Artwork deadline | **T-5 days.** Late artwork ships as a generic sponsor-name-only sign. |
| File naming | `SPONSOR-NAME_ITEM_v#.ext` |

State the deadline consequence in the sponsor pack. Without a stated consequence, 40% of artwork arrives during load-in.
### 5.4 AV Loan Equipment Inventory

Standard booth AV kit, one per booth that ordered it:

| Item | Model | Qty/kit | Replacement value |
|------|-------|---------|-------------------|
| Display 43" | Samsung BE43T-H / LG 43UT640S | 1 | $450 |
| Display 55" | Samsung BE55T-H / LG 55UT640S | 1 | $700 |
| Display stand | Peerless-AV SR560M or SmartMount cart | 1 | $300 |
| HDMI cable, 25 ft **active** | Monoprice SlimRun AOC / Ruipro | 1 | $60 |
| HDMI cable, 6 ft | Belkin / Monoprice Certified Premium | 1 | $15 |
| USB-C → HDMI adapter | Anker A8306 / Cable Matters 201062 | 1 | $25 |
| Mini DisplayPort → HDMI | StarTech MDP2HDMI | 1 | $22 |
| Lightning → HDMI | Apple A1438 (genuine — third-party fails HDCP) | 1 | $50 |
| USB-A → USB-C adapter pair | Anker | 2 | $12 |
| Power strip, 15 A, 15 ft cord | Tripp Lite TLM615SA | 1 | $28 |
| USB charging hub | Anker 543 / PowerPort 6 | 1 | $40 |
| Gaff tape roll | Pro Tapes Pro Gaff 2" black | 1 | $22 |
| Cable ties (Velcro) | 8" reusable, pack of 25 | 1 | $10 |

**Show spares held at the AV desk** (not issued, drawn on demand):

```
4 × 25 ft active HDMI          6 × USB-C → HDMI adapter
4 × 6 ft HDMI                  4 × Mini DP → HDMI
2 × 43" display                2 × Lightning → HDMI (genuine Apple)
2 × display stand              6 × 15 A power strip
2 × HDMI → HDMI scaler/EDID manager (Decimator / BMD Micro Converter)
4 × Cat6 patch, 25 ft          2 × 5-port gigabit switch
```

The EDID manager / scaler is the single most valuable spare on the list. It resolves the "presenter laptop refuses to output" fault (§6) by presenting a clean, known 1080p60 EDID to a laptop that is failing to negotiate with the switcher.

**Loan tracking protocol:**

| Step | Action |
|------|--------|
| Asset tag | Every item barcoded/numbered, logged against the booth number |
| Checkout | Booth rep signs; **photograph the item and the signed sheet together** |
| Hold | Credit card authorisation or company ID retained for the duration |
| Condition | Note pre-existing damage at checkout — this prevents every dispute |
| Return | **Within 2 hours of expo close.** Late returns billed at day rate. |
| Damage schedule | Published in the sponsor pack: cable $60, adapter $25-50, display $450-700, stand $300 |
| Reconciliation | Full physical count before crew leaves the floor, against the checkout log |

Do the reconciliation count on the floor, before load-out trucks. Missing items found the next morning are gone.
---

## 6. Failure Modes — Tech Events

### 6.1 Demo and Presentation

| # | Symptom | Root cause | Detection | Immediate action | Prevention |
|---|---------|-----------|-----------|------------------|------------|
| 1 | Demo hangs on a spinner mid-pitch | API rate limit hit, serverless cold start, or expired token | Demo Wrangler stopwatch passes 10 s | **ROLLING B** — cut to recording, presenter narrates | Warm the endpoint every 60 s from T-15 min; verify key tier and token expiry; prefer local mocks (§1.7) |
| 2 | Presenter laptop outputs nothing to the switcher | HDCP handshake failure, or USB-C DisplayPort alt-mode not negotiating, or resolution the switcher rejects | Black on ATEM multiview for that input | Insert EDID manager/scaler in line; else move to spare laptop with PDF + video | Test **every** laptop at check-in with the **actual** dongle; force 1080p60; avoid USB-C, prefer native HDMI |
| 3 | Slides will not load on stage | Google Slides/Figma needs cloud; captive portal intercepted the session | Presenter clicking, nothing rendering | Switch to the offline copy collected at check-in | **Mandate offline PDF + PPTX on the show laptop**, collected at check-in. No exceptions. |
| 4 | Laptop throttles, demo becomes a slideshow | Thermal throttle under 3D/ML load, or on battery power-saving | Frame rate visibly collapses | Cut to recording; put the machine on AC | Rehearse the full runtime on AC with an external cooling pad; disable background sync/indexing/updates |
| 5 | Notification or personal content appears on the keynote screen | Focus Assist / DND not enabled | It is on the LED wall | Switcher cuts to holding slide immediately | Check-in checklist item, verified by Demo Wrangler, not self-reported |
| 6 | Demo shows empty/wrong data | Demo DB reset by a scheduled job or a teammate | Wrong output on screen | ROLLING B | Freeze the demo environment at T-4 h; disable scheduled jobs; snapshot seed data |
| 7 | Presenter overruns badly, schedule collapses | No enforced hard stop | Timer past hard stop | Stage Manager cues A1 to **mute the mic**; walk on if needed | Visible countdown, briefed hard-stop rule, enforced on team one |
| 8 | Recording plays but no audio on stream | Playback rig audio not embedded on HDMI, or ATEM input audio set to input-follow-video off | Stream audio meters flat during playback | Switch ATEM input audio to ON for input 5 | Test the fallback playback **with audio** in rehearsal pass 3 |

### 6.2 Network

| # | Symptom | Root cause | Detection | Immediate action | Prevention |
|---|---------|-----------|-----------|------------------|------------|
| 9 | Public Wi-Fi collapses at keynote start; devices associate but get no IP | **DHCP scope exhausted** — 3000 devices against a /22's ~968 leases | `show ip dhcp binding \| count` at 100%; APs show associated-but-no-IP | Drop lease to **30 min** (`lease 0 0 30`); activate the pre-staged second scope | Size /21 or /20 from the start per §2.1; alert at 80% utilisation |
| 10 | Whole room's Wi-Fi is slow despite plenty of APs | 80 MHz channels in a dense deployment → co-channel interference; and/or TX power at max preventing roaming | Controller shows high channel utilisation, low airtime efficiency | Force **20 MHz**, drop 5 GHz TX to 11-14 dBm, disable 2.4 GHz on most APs | Design at 20 MHz above ~12 APs; §3.3 |
| 11 | Nobody can start at kickoff; WAN pinned at 100% | Thundering herd of `docker pull` / `npm install` | WAN graph flat at ceiling, DNS timing out | Enforce the 5 Mbps per-client cap; point the room at the local caches | Local registry/npm/apt caches, pre-warmed; T-3 day pre-pull email (§3.4) |
| 12 | Dante audio dropouts that correlate with stream activity | AV and stream traffic on the same segment; full NDI at ~130 Mbps/stream saturating a gigabit link | Dante Controller latency/clock errors timed to stream start | Move stream egress off the Dante segment; police it into AF41 | Strict VLAN separation, EF queue for Dante only, NDI\|HX for secondary sources, 10 GbE uplinks (§2.2) |
| 13 | Intermittent Dante clock instability, no obvious cause | **802.3az EEE** active on AV switch ports, or IGMP snooping enabled with no querier | `show eee` shows enabled; multicast groups aging out | `no energy-efficient-ethernet` on AV ports; enable an IGMP querier on VLAN 10 | Standing config item — both are in the §2.2 checklist |
| 14 | Attendees report other people's laptops visible on the network | Client isolation off on the public SSID | Anything discoverable from a test client | Enable Client Device Isolation now | §2.4 — isolation is mandatory on VLAN 30 |
| 15 | Presenter's VPN breaks the demo | Corporate VPN full-tunnel routing demo traffic offsite, or split-tunnel misconfigured | Demo works off-VPN, fails on-VPN | Disconnect VPN if the demo does not need it | Cover VPN state in check-in; rehearsal pass 2 on the show network |
### 6.3 Power

| # | Symptom | Root cause | Detection | Immediate action | Prevention |
|---|---------|-----------|-----------|------------------|------------|
| 16 | GFCI trips repeatedly, no faulty device found | **Cumulative PSU leakage** — 10-12 laptop PSUs × 0.5-3.5 mA each exceeds the 4-6 mA Class A threshold | Trips under load, resets fine, no single device reproduces it | Split the load across more branches; **never bypass the GFCI** | Cap 8-10 laptop PSUs per GFCI; one GFCI per table (§3.2) |
| 17 | Breaker trips and takes 8 teams' work with it | Circuit designed at 83%+ utilisation, then someone plugs in a kettle or a gaming laptop | Dark tables | Reset, redistribute, move the offending device to a dedicated circuit | One 20 A circuit per 10-person table (48% headroom) — §3.1 |
| 18 | Laptop chargers running hot, cheap PSUs cutting out under load | **Excessive voltage drop** — 12 AWG on a 100 ft run at 16 A = 5.3% | Measure voltage at the far end of the run under load | Re-feed on 10 AWG, or relocate the distro closer | 12 AWG ≤75 ft, 10 AWG 75-150 ft (§3.1) |
| 19 | Core switch or AP goes dark overnight | A participant unplugged it looking for an outlet at 04:00 | Monitoring alert; APs offline | Restore, re-tag, brief the overnight crew | UPS on all network gear + bright **DO NOT UNPLUG — EVENT NETWORK** tags (§3.5) |
| 20 | Daisy-chained strips found on the floor | Participants extending reach | Hourly floor walk | Break the chain, provide a proper drop | Brief it at kickoff; hourly walks; enough quad boxes that nobody needs to improvise |

### 6.4 Stream and Record

| # | Symptom | Root cause | Detection | Immediate action | Prevention |
|---|---------|-----------|-----------|------------------|------------|
| 21 | Stream drops every ~15 min | Uplink contention, CGNAT session resets, or the encoder PC on Wi-Fi | OBS log shows dropped frames climbing before each disconnect | Move encoder to wired; fail over to the ATEM's built-in engine on the backup key | Dedicated 25 Mbps committed upload, AF41-marked, static IP, no CGNAT (§4.5) |
| 22 | Total venue WAN failure mid-keynote | Circuit or venue-side fault | Stream and everything else down | Teradek VidiU X on **Sharelink** with LTE modem carries the stream | Rent the bonded LTE path for any press-facing keynote (§4.4) |
| 23 | ATEM ISO recording stops partway | SSD sustained write below ~500 MB/s, or exFAT fragmentation, or the drive is not on BMD's supported list | ATEM disk indicator drops out; short/truncated files | Swap to the spare verified SSD; drop to Program-only recording | Verified BMD-supported SSD (T7 Shield), **freshly reformatted exFAT before every event**, ISO armed only for key segments (§4.7) |
| 24 | Audio out of sync on the stream, drifts on every camera cut | Different HDMI/NDI latency per input, no per-input audio delay set | Clap test shows different offsets per camera | Set per-input audio delay on the ATEM for each source | Clap test every camera at load-in and after any video chain change (§4.8) |
| 25 | 30 hours of recording is one corrupt file | No automatic file splitting | Discovered in post, which is too late | — | OBS automatic file splitting every 15 min / 4 GB (§4.4) |
| 26 | Cloud sync eats the stream bandwidth | Unthrottled rclone/Dropbox upload | Stream bitrate drops when sync runs | Kill the sync; restart with `--bwlimit 20M` | Throttle from the start; `--min-age 2m` (§4.6) |
| 27 | Viewers on poor connections buffer with no lower quality option | Non-partner Twitch channel gets no transcode ladder | Viewer complaints, platform shows source-only | Switch primary to YouTube, or push 720p60 @ 4500 Kbps | Know your platform's transcode status before choosing ingest bitrate (§4.5) |

### 6.5 RF and Audio

| # | Symptom | Root cause | Detection | Immediate action | Prevention |
|---|---------|-----------|-----------|------------------|------------|
| 28 | Wireless mic dropouts and hits, worst when the room fills | **2.4 GHz digital mics in a room with 3000 Wi-Fi devices.** The band is unusable at a tech event. | Receiver RF meter dips correlate with attendance | Swap to UHF bodypacks; run a scan and re-coordinate | **Never spec 2.4 GHz wireless mics for a tech event.** UHF only. Scan and coordinate on site. |
| 29 | Intercom unusable during the show | 2.4 GHz intercom competing with attendee Wi-Fi | Crew comms breaking up | Move to the DECT system or wired partyline | Hollyland Solidcom C1 Pro (**1.9 GHz DECT**) — outside the contested bands |
| 30 | Stream mix level jumps whenever house level is adjusted | Stream fed from Main L/R instead of a Matrix out | Stream loudness tracks the house fader | Re-patch the stream feed to Matrix 1/2 | Stream mix on an independent Matrix output (§4.8) |
| 31 | Unrecoverable clipped audio on the archive | Mic hit peaked into the recorder's ceiling | Waveform flat-topped in post | — | Zoom F6 in **32-bit float** as the isolated audio layer — unclippable (§4.6) |

### 6.6 Judging

| # | Symptom | Root cause | Detection | Immediate action | Prevention |
|---|---------|-----------|-----------|------------------|------------|
| 32 | Judge scores lost | Devpost session expired mid-round; scores never submitted | Judge reports blank form | Re-enter from the **printed rubric sheets**; photograph sheets immediately | Paper rubrics as standing backup; brief judges to submit per project, not per round (§3.6) |
| 33 | Winner disputed as unfair | Raw totals compared across judges scoring on different internal scales | Judge means differ by more than ~1 point | Recompute with z-score normalisation | Normalise by default; ≥3 judges per project (§3.6) |
| 34 | Tie with no resolution path | Tie-break rule not pre-declared | Two projects level at the reveal | Head judge decides, and it will look arbitrary | Publish the tie-break order in writing before judging opens |
| 35 | "We pushed a fix after the deadline" | Submission cutoff not technically enforced | Argument at judging | Judge the recorded commit hash only | Record the git commit hash at cutoff; announce the rule at kickoff (§3.6) |
| 36 | Later judges' scores cluster toward the current leader | Anchoring bias from a visible live leaderboard | Score distribution skews by round | Hide the board | Leaderboard hidden from teams and judges until the awards reveal (§3.6) |

### 6.7 Failure Modes — Summary Matrix

The preceding subsections cover 36 distinct symptoms in detail. The following summary distils the highest-impact scenarios into a single decision-ready table with the columns the on-call crew needs at 02:00: **Scenario | Probability | Impact | Fix | Recovery time**. Probabilities are per-event unless noted; impact is **L**ow (cosmetic / no schedule impact), **M**edium (one segment affected, recovery within segment), **H**igh (keynote at risk, or recovery crosses segment boundaries), **C**ritical (event-wide or safety). Recovery time is best-case wall-clock from trigger to stable state with the documented fix applied.

| # | Scenario | Probability | Impact | Fix | Recovery time |
|---|----------|------------|--------|-----|---------------|
| 1 | Live demo hangs on spinner / API failure mid-pitch | High (30-40% of unrehearsed demos) | H | Demo Wrangler calls **ROLLING B** at 10 s; V1 cuts to playback rig; presenter narrates over recording | 30 s (cut and playback) |
| 2 | Presenter laptop outputs nothing to the switcher (HDCP / USB-C / resolution) | Medium (5-10% of presenters) | H | Insert EDID manager/scaler in line on that input; failing that, swap to spare laptop with PDF + video | 2-5 min |
| 3 | Slides will not load on stage (cloud dependency, captive portal) | Medium (8-12%) | M | Switch to offline PPTX/PDF collected at check-in, loaded on show laptop | 1 min |
| 4 | Livestream encoder fails (OBS crash, NVENC fault, dropped frames spike) | Medium (10-15% per 8 h stream) | H | Fail over to ATEM built-in streaming engine on the backup RTMP key; restart OBS while ATEM carries the show | 30-60 s (ATEM hot standby) |
| 5 | Total venue WAN failure mid-keynote | Low (1-3% per event) | C | Teradek VidiU X on **Sharelink** with LTE modem bonded path takes the stream | 2-5 min to rebind RTMP target |
| 6 | Public Wi-Fi collapses at keynote start (DHCP scope exhausted) | Medium-High (frequent at >300 headcount) | H | Drop lease to 30 min; activate pre-staged second scope; alert attendees to reconnect | 5-15 min for scope relief |
| 7 | Thundering herd at kickoff WAN-pins the link (`docker pull`) | High (almost certain at 200+ headcount) | H | Re-point room at local caches (registry-mirror, Verdaccio, apt-cacher, devpi); enforce per-client 5/2 cap | 10-30 min as caches warm |
| 8 | Dante audio dropouts correlated with stream activity | Medium (without proper VLAN/QoS) | C | Move stream egress off the AV segment; confirm EF queue contains only Dante + PTP | 5-10 min reconfiguration |
| 9 | Wireless mic dropouts / hits when the room fills | High if 2.4 GHz mics used | H | Swap to UHF bodypacks; re-coordinate frequencies | 5-15 min if spares on hand |
| 10 | GFCI trips with no faulty device (cumulative PSU leakage) | High at 10+ devices per GFCI | M | Redistribute load across more branches; never bypass GFCI | 5-10 min per cycle |
| 11 | Sponsor booth network NOT isolated — sponsor device floods VLAN 30 | Medium (undeclared equipment) | M-H | Move sponsor drop to VLAN 40 with ACL; rate-limit to 25/10 Mbps; isolate from other booths | 10-20 min port reassign |
| 12 | Presenter unfamiliar with provided clicker / cannot advance deck | Medium (15-20% of presenters) | L-M | A1 calls "HOLD"; presenter uses keyboard arrows; rehearse advance forward on backup laptop | 30 s coaching |
| 13 | Judging platform (Devpost) down or sessions expired mid-round | Medium (per multi-hour round) | H | Pivot to printed rubric sheets; photograph each immediately; re-enter after platform recovers | 15-30 min manual entry |
| 14 | ATEM ISO recording stops partway (SSD write below threshold) | Medium (sustained 9-stream ISO) | M | Swap to verified spare SSD; drop to Program-only recording for the rest of the segment | 2-5 min |
| 15 | Cloud sync eats stream bandwidth (unthrottled rclone) | Medium (if sync runs unscheduled) | H | Kill the sync; restart with `--bwlimit 20M` and `--min-age 2m` | 1-2 min |
| 16 | Audio out of sync on stream, drifts on every camera cut | High without per-input delay | M | Run clap test; set per-input audio delay on ATEM Audio tab for each source | 10-20 min per chain |
| 17 | Core switch or AP unplugged overnight by participant | Medium at 24+ h events | H | Restore power; re-tag with DO NOT UNPLUG; brief overnight crew | 5-15 min boot/restore |
| 18 | Notification / personal content appears on keynote screen | Low-Medium (Focus Assist slip) | M-H | Switcher cuts to holding slide immediately; Demo Wrangler disables DND on the offender | 10 s (cut) |
| 19 | Stream fed from Main L/R — level jumps when house fader moves | Medium (if mis-patched) | L | Re-patch stream feed to dedicated WING Matrix 1/2; restore independent mix | 2-5 min |
| 20 | Viewers on poor connections buffer with no transcode ladder | Medium (non-partner Twitch) | L | Switch primary ingest to YouTube, or push 720p60 @ 4500 Kbps | 5-10 min to reconfigure OBS |

---

## 7. Pre-Show Checklist — Final Walk

Run this in order at **T-2 hours** before doors, with the Show Caller reading items aloud and the responsible role calling out confirmed. Anything unchecked at T-1 hour is a stop-the-show item to resolve before opening.

| # | Item | Confirmed by | Notes |
|---|------|--------------|-------|
| 1 | All presenter fallback recordings delivered and verified on the **playback rig** (not on a laptop) | Demo Wrangler | File plays end-to-end with audio; chapter timecodes logged |
| 2 | ROLLING B cut rehearsed at least once with the actual V1 switching | V1 + Demo Wrangler | Hard cut, presenter briefed line delivered, no dissolve |
| 3 | ATEM input map matches printed legend taped to switcher; all 8 inputs show clean signal | V1 | Test pattern on each input, audio on IN 5 |
| 4 | Per-input audio delay calibrated via clap test on every camera and the playback rig | A1 + V1 | Offsets logged; re-test after any video chain change |
| 5 | OBS encoder live on YouTube and Twitch (or chosen platforms); bitrate stable; dropping frames <1% | Stream Operator | Keyframe interval 2 s, CBR 8000 Kbps, 1080p60 |
| 6 | ATEM built-in streaming engine armed and tested on backup RTMP key, then stopped | Stream Operator | ATEM ready to take over with one click |
| 7 | Four recording layers verified: ATEM ISO, OBS local record, camera SD cards, isolated audio (32-bit float) | Stream Operator + A1 | Each layer recording; spot-check file growth after 60 s |
| 8 | All three VLANs up and isolated: `show ip access-lists ACL-PUBLIC-IN` shows hits on deny rules | Network Lead | Test station on VLAN 30 cannot ping 10.10.x.x; VLAN 20 cannot reach VLAN 10 |
| 9 | DHCP scope utilisation <80% on VLAN 30; if higher, activate second scope now | Network Lead | Loop to §2.1 sizing table |
| 10 | Local artefact caches (registry-mirror, npm-proxy, apt-cache, pypi-mirror, git-mirror) responding and pre-warmed | Network Lead | `docker pull` from a VLAN 30 client completes in <2 s |
| 11 | UPS on core switch, router, WAN handoff, and AP PoE injectors; AC confirmed; battery test passed | Network Lead | SMT1500/SMT2200 holding load; runtime logged |
| 12 | Wireless mic frequency coordination complete and logged; UHF bodypacks paired; spare batteries in | A1 | No 2.4 GHz wireless in the audio chain |
| 13 | Hollyland Solidcom C1 Pro intercom on **1.9 GHz DECT**; every crew role has a working headset, batteries >80% | Show Caller | Backup Motorola CP100d UHF handhelds on load-in/load-out frequency |
| 14 | GFCI integrity verified on every participant and booth branch; leakage distribution per §3.2 (cap 8-10 PSUs per GFCI) | Booth Liaison | Test trip and reset on each GFCI; no daisy-chained strips |
| 15 | Stage timer (StageTimer.io or hardware) synced and visible to presenter, judges, and stage | Stage Manager | Backup phone stopwatch at the caller's position |
| 16 | Devpost (or chosen judging platform) reachable from VLAN 20 judge devices; printed rubric sheets distributed | Head Judge | Tie-break rule published in writing; ≥3 judges per project confirmed |
| 17 | Sponsor booth power and network confirmed against declared loads; undeclared loads rejected or reassigned | Booth Liaison | Each booth has the documented wattage and correct VLAN assignment |
| 18 | Edge cases rehearsed: hard stop at 3:15, presenter swap, missing recording, scope exhaustion, WAN failover | Show Caller | Each trigger exercised at least once; crew knows their cue |
| 19 | Consumables and spares stocked at the AV desk: gaff tape, cable ties, AA/AAA, 25 ft active HDMI, USB-C dongles, 15 A strips | Stage Manager | Counted against the §5.4 spare list |
| 20 | Emergency contacts posted at every crew position: Show Caller, Network Lead, A1, V1, Stream Operator, venue security, on-call electrician | Stage Manager | Phone numbers, not just names — radios fail when you need them most |

**Stop-the-show gate:** if items 1, 5, 8, 11, or 12 are unchecked at T-1 hour, doors do not open until they are. The remaining items can be cleared during the first 30 minutes of the event with the floor in a holding pattern.

<!-- CHUNK-END -->
