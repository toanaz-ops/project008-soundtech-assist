# Corporate & B2B Events: Technical SOP

## Scope

Keynotes, general sessions, breakouts, panel discussions, AGMs, product launches, and sales kickoffs in hotel ballrooms, conference centers, and purpose-built auditoriums. Room sizes 100-2,000 seats. The defining constraint of corporate work is that **content arrives late and unvalidated** and **the client's CEO cannot be told "the slide didn't work."** Every protocol below exists to move failure earlier in time, where it is cheap.

Corporate differs from music production in three ways that drive every decision here:

1. **Content is the show.** A perfect PA with a black screen is a failed event. Video redundancy outranks audio redundancy in the priority list.
2. **No soundcheck with the actual talent.** Speakers arrive 30 minutes before they walk. Everything must be pre-validated with a stand-in.
3. **Zero tolerance for visible recovery.** Audiences forgive a 40 ms audio dropout. They do not forgive 6 seconds of Windows desktop on a 24-foot screen.

## Show Roles & Call Signs

| Role | Call Sign | Owns | Position |
|------|-----------|------|----------|
| Show Caller / Stage Manager | "SM" | Timing, cue calls, talent flow | Stage left wing, on comms |
| Graphics Operator | "G1" | Show laptops, clicker, slide parity | FOH or backstage rack |
| Video Engineer | "V1" | Switcher, scaler, projection, confidence feeds | FOH |
| Audio Engineer | "A1" | Console, RF, lectern/lav, automix | FOH |
| RF / A2 | "A2" | Mic swaps, transmitter batteries, spectrum monitoring | Backstage |
| Speaker Ready Room Tech | "SRR" | Slide intake, conversion, QC, sign-off | Separate room |
| Presenter Wrangler | "PW" | Getting talent to the wing on time | Backstage / green room |

On a small breakout, G1/V1/A1 collapse into one operator. The **SRR role never collapses** — if nobody owns slide intake, unvalidated content reaches the screen.

---

## 1. Speaker Ready Room Protocol

### 1.1 The 60-Minute Buffer Rule

**Rule: no deck goes to the show computer less than 60 minutes before that speaker's start time.** No exceptions for VIPs. If a deck arrives at T-20, the speaker presents the last validated version or presents from the ready room export, and the client is told in writing.

The 60 minutes is not padding. It is a measured work budget:

| Task | Typical | Worst Case | Why It Takes This Long |
|------|---------|------------|------------------------|
| Ingest + virus scan + copy to show share | 2 min | 8 min | 400 MB deck over hotel WiFi; USB 2.0 stick at 12 MB/s |
| Open + font audit | 3 min | 10 min | Cloud-font resolution timeout is 30 s per missing face |
| Font substitution repair | 5 min | 20 min | Reflow breaks layout on every slide; manual re-boxing |
| Embedded video codec test (per clip) | 2 min | 15 min | HEVC/ProRes transcode of a 90 s 4K clip = 6-12 min |
| Aspect ratio / off-canvas check | 3 min | 8 min | 4:3 legacy deck rebuilt to 16:9 |
| Animation + transition pass | 4 min | 12 min | Morph transitions fail on downgrade; rebuild as fades |
| Linked-file resolution (Excel charts, OLE) | 3 min | 15 min | Broken UNC paths to speaker's own C: drive |
| Full-speed dry run on preview station | 5 min | 10 min | Must play every video, hit every animation |
| Copy to show laptops A **and** B + verify hash | 3 min | 6 min | Two machines, byte-for-byte identical |
| Speaker sign-off | 5 min | 15 min | Speaker wants live edits |
| **Total** | **35 min** | **119 min** | 60 min = typical + 70% contingency |

The three killers, in order of frequency:

**Slide conversion.** A deck authored in Keynote 14 and exported to PPTX loses Magic Move, builds collapse to appear/disappear, and gradient fills flatten. A Google Slides deck exported to PPTX substitutes every non-Google font and drops all linked video. Conversion is never lossless, so it must be done and *inspected* before showtime, never at showtime.

**Font substitution.** PowerPoint for Windows can embed TrueType/OpenType faces, but only if the font's `fsType` embedding permission allows it — many commercial brand fonts are set to "Restricted" and silently refuse. **PowerPoint for Mac cannot embed fonts at all.** Microsoft 365 "cloud fonts" download on demand and fail on an offline show laptop. The visible symptom is silent: text reflows into Calibri or Arial, line breaks shift, and a headline that fit on one line now wraps and pushes off the slide. Nobody notices until it is on the 24-foot screen.

**Video codec issues.** PowerPoint for Windows decodes through Media Foundation. It reliably plays H.264/AAC in `.mp4` and legacy WMV. It does **not** reliably play HEVC (requires the paid HEVC Video Extension plus hardware decode), ProRes in `.mov`, DNxHD, VP9/WebM, or anything with an alpha channel. Keynote on macOS decodes through AVFoundation and plays ProRes and HEVC natively — which is exactly why a deck that worked on the speaker's MacBook dies on the show PC.

### 1.2 Slide Check Workflow

Run every deck through these nine steps in order. Do not skip ahead; step 3 depends on step 2 having been logged.

**Step 1 — Intake and label.** Copy from the speaker's media to the show share. Filename convention: `[SessionTime]_[LastName]_[v##]_[YYYYMMDD-HHMM].pptx`, e.g. `0930_Nakamura_v03_20260811-0812.pptx`. Never work on the speaker's original; never let the speaker work on the show copy.

**Step 2 — Structural audit before opening.** A `.pptx` is a ZIP archive. Copy it, rename to `.zip`, and inspect:

```
/ppt/media/          → every embedded image and video, with real file extensions
/ppt/fonts/          → embedded font subsets (fontdata files). EMPTY = no fonts embedded
/ppt/embeddings/     → OLE objects (Excel workbooks, Visio). High-risk items
/ppt/slideMasters/   → count of masters; >3 means an assembled multi-author deck
```

An empty `/ppt/fonts/` directory on a deck using brand typography is an immediate red flag. Also confirm codecs directly rather than trusting extensions:

```bash
# Enumerate every embedded media file with its true codec
for f in ppt/media/*; do
  ffprobe -v error -select_streams v:0 \
    -show_entries stream=codec_name,profile,width,height,r_frame_rate \
    -of default=nw=1 "$f"
done
```

**Step 3 — Font audit.** Open the deck on the preview station with the show laptop's exact font set installed. Use PowerPoint's `File → Info → Check for Issues → Inspect Document`, then verify visually against the speaker's PDF reference (always request a PDF alongside the deck — it is the ground truth for intended layout). The **Slidewise** add-in (Neuxpower, approx. $60/seat/yr) lists every font, flags non-embedded faces, and reports media codecs in one pane; it turns a 10-minute manual audit into about 60 seconds and is worth the license on any event with more than 20 decks.

Remediation, in order of preference:

| Situation | Fix | Cost of Fix |
|-----------|-----|-------------|
| Font available and licensed | Install on both show laptops, reboot PowerPoint | 2 min |
| Font restricted / unavailable | Substitute a metric-compatible face, then re-check every slide for reflow | 10-20 min |
| Single hero slide, brand-critical | Convert text to outlines (`Ctrl+Shift+G` after paste-as-EMF) or export slide as 1920×1080 PNG and place full-bleed | 3 min/slide |
| Speaker refuses substitution | Present from PDF in Acrobat full-screen (loses animation and video) | 1 min, but degrades show |

**Step 4 — Aspect ratio and safe area.** Force `Design → Slide Size → Widescreen 16:9` (13.333 × 7.5 in). Legacy 4:3 decks scaled up will pillarbox; scaled to fill they crop 25% of the height. Check for content within 3% of the frame edge — house masking and projector overscan eat it.

**Step 5 — Transcode all embedded video to house spec.** One codec, no exceptions. House spec is H.264 High Profile Level 4.1, 1920×1080, closed GOP, AAC-LC 48 kHz stereo:

```bash
ffmpeg -i input.mov \
  -c:v libx264 -profile:v high -level 4.1 -preset slow -crf 18 \
  -pix_fmt yuv420p -g 30 -keyint_min 30 -sc_threshold 0 \
  -vf "scale=1920:1080:flags=lanczos,fps=30" \
  -c:a aac -b:a 192k -ar 48000 -ac 2 \
  -movflags +faststart output.mp4
```

`-pix_fmt yuv420p` is mandatory — a yuv422p or yuv444p H.264 file will open in VLC and refuse to play in PowerPoint. Closed GOP (`-sc_threshold 0`) prevents the first-frame stall when a slide is revisited. Re-insert the transcoded file with `Insert → Video → This Device` (which embeds), never `Link to File`.

**Step 6 — Animation and transition pass.** Play the deck at full speed, key by key. Morph transitions require PowerPoint 2019+ on both machines and degrade to a hard cut on older builds. Anything triggered `On Click` inside an auto-advancing sequence will desync. Log the total click count per deck — G1 needs it for parity recovery (see 2.5).

**Step 7 — Presenter view and display assignment.** Set `Slide Show → Monitor` explicitly to the projector output, and confirm `Use Presenter View` matches what the speaker expects. A deck set to "Automatic" will pick the wrong display when the switcher's EDID changes.

**Step 8 — Full-speed dry run on the preview station.** Every video plays to its end. Every build fires. Audio routes to the ready room speakers so the SRR tech confirms the clip actually carries audio (a surprisingly common miss — speakers cut audio in their edit and expect it to be there).

**Step 9 — Deploy and sign off.** Copy to laptop A and laptop B. Verify identity by hash, not by eye:

```bash
# Run on both show laptops; strings must match exactly
certutil -hashfile "D:\SHOW\0930_Nakamura_v03.pptx" SHA256   # Windows
shasum -a 256 /Volumes/SHOW/0930_Nakamura_v03.pptx           # macOS
```

Then get a physical or digital signature on the sign-off sheet: *deck version, click count, video count, font substitutions made, speaker initials, time.* This sheet is the only defense when a speaker later claims the wrong version was shown.

### 1.3 Compatibility Matrix

Read this as "authored in X, presented on Y." Green-path combinations are the only ones that should reach a general session.

| Authored In | Presented On | Result | Required Mitigation |
|-------------|--------------|--------|---------------------|
| PowerPoint 365 (Win) | PowerPoint 365 (Win), same build | Full fidelity | Match build numbers; embed fonts |
| PowerPoint 365 (Win) | PowerPoint 365 (Mac) | Fonts substitute; Morph degrades; WMV fails | Transcode WMV → H.264; install fonts locally |
| PowerPoint 365 (Mac) | PowerPoint 365 (Win) | **No embedded fonts possible**; ProRes/HEVC clips dead | Install fonts on show PC; transcode all video |
| Keynote 14 (Mac) | Keynote 14 (Mac), same version | Full fidelity | Use `File → Save` package; keep on Mac |
| Keynote 14 (Mac) | PowerPoint (Win), via PPTX export | Magic Move lost; builds flatten; fonts substitute; gradients banded | Rebuild transitions as 0.5 s fades; full visual QC pass |
| Google Slides | Google Slides in Chrome | Fidelity OK, **network dependency** | Hardwired ethernet + offline cache pre-loaded |
| Google Slides | PowerPoint (Win), via PPTX export | All linked video lost; fonts substitute; some builds lost | Re-insert video as embedded H.264; full QC |
| Canva / Figma / Prezi | Any | Unpredictable | Export to PDF **and** to 1920×1080 PNG-per-slide; present the PNG deck |
| PDF | Acrobat / SumatraPDF full-screen | Layout guaranteed, no animation or video | Acceptable fallback for every deck; build it as insurance |

**Rule: run the presentation in its native application whenever possible.** A Keynote deck presented from a Mac in Keynote is lower risk than the same deck converted to PPTX for the house PC. This is the reason the dual-laptop rig in section 2 is one Windows machine and one Mac on many shows, rather than two identical PCs.

**Google Slides deserves a specific warning.** It has no true offline presentation mode that survives a hotel network failure. If a speaker insists on presenting live from Slides: use a wired ethernet drop (never venue WiFi), open the deck and step through every slide before the session so Chrome caches all assets, disable Chrome auto-update, and have the PPTX export loaded and standing by on laptop B. Assume the network will fail at least once per multi-day event.

### 1.4 Embedded Video Reference

| Container / Codec | PowerPoint Win | PowerPoint Mac | Keynote | Verdict |
|-------------------|----------------|----------------|---------|---------|
| MP4 / H.264 High, yuv420p | Yes | Yes | Yes | **House standard** |
| MP4 / H.264, yuv422p or 10-bit | No | Intermittent | Yes | Transcode |
| MP4 or MOV / HEVC (H.265) 8-bit | Needs HEVC Video Extension + HW decode | Yes | Yes | Transcode |
| MOV / HEVC 10-bit, HDR | No | Yes | Yes | Transcode; also tone-map to Rec.709 |
| MOV / ProRes 422 / 4444 | No | No | Yes | Transcode |
| MOV / Animation codec with alpha | No | No | Partial | Pre-composite over background; transcode |
| WMV / VC-1 | Yes | No | No | Transcode |
| WebM / VP9 or AV1 | No | No | No | Transcode |
| MKV (any codec) | No | No | No | Remux to MP4 |
| GIF (animated) | Yes | Yes | Yes | Fine, but check loop count and file size |
| Linked video (any codec) | Path-dependent | Path-dependent | Path-dependent | **Always re-embed** |

HDR is worth calling out: a clip shot on an iPhone in Dolby Vision or HLG will look correct on the speaker's laptop and appear washed-out, grey, and low-contrast through an SDR projection chain. Tone-map at transcode time:

```bash
ffmpeg -i hdr_clip.mov -vf \
 "zscale=t=linear:npl=100,tonemap=hable:desat=0,zscale=p=bt709:t=bt709:m=bt709:r=tv,format=yuv420p" \
 -c:v libx264 -profile:v high -crf 18 -c:a aac -b:a 192k -ar 48000 sdr_clip.mp4
```

### 1.5 Ready Room Equipment

The ready room is not a lounge with a laptop. It is a **bit-for-bit replica of the show playback chain**, because the only valid test of "will this deck work on stage" is running it on hardware identical to the stage rig.

| Item | Specification | Street (2026 USD) | Why This Spec |
|------|---------------|-------------------|---------------|
| Preview station ×2 | Same model, OS build, Office build, GPU driver as show laptops. Dell Precision 3591 or Lenovo ThinkPad P16s: i7-1370P / Ryzen 7 PRO, 32 GB, 1 TB NVMe, discrete GPU | $2,200 ea | A deck that plays on a different GPU driver proves nothing |
| Mac preview station | MacBook Pro 14" M4 Pro, 24 GB, 1 TB, Keynote 14.x + Office 365 | $2,400 | Required to open native Keynote packages and ProRes clips |
| Test projector | Same native resolution as house rig. Epson PowerLite L630U (6,200 lm, WUXGA laser) or Panasonic PT-VMZ61 | $2,600-3,400 | Reveals font reflow and edge-crop at real scale; a monitor will not |
| Test screen | 80-100" diagonal, 16:9, matte white gain 1.0 | $400-900 | Same gamma/contrast character as house surface |
| Confidence monitor | 24" 1080p, sub-20 ms input lag. Dell P2425H or ASUS VG249 | $180-260 | Lets speakers rehearse against the exact display they will see on deck |
| Scaler / switcher | Identical model to show rig (e.g. second Roland V-8HD) | $2,499 | Same EDID and scaling behavior as the house path |
| Clicker ×2 | Same model as show clicker, with receivers | $130 ea | Speakers rehearse the actual button feel and advance latency |
| Countdown timer | DSAN Limitimer PRO-2000 or on-screen timer | $480 | Speakers rehearse to the real clock |
| Ingest | USB-A/C hub, SD/CF reader, DVD drive, 2× 1 TB USB-C SSD | $250 | Speakers still arrive with optical media and CF cards |
| Network | Wired gigabit to show file share; **no reliance on venue WiFi** | — | 400 MB decks over congested hotel WiFi = 8+ min |
| Printer | Monochrome laser, duplex | $220 | Speaker notes, sign-off sheets, running order |
| Audio monitoring | Powered 2.0 pair (JBL 104-BT) + headphones | $150 | Verify embedded clip audio actually exists |
| Font library | Client brand fonts pre-installed and license-verified on all stations | — | Substitution repair is impossible without the source faces |

**Room logistics.** Two intake desks minimum for events over 40 speakers; one queue position is a bottleneck by mid-morning. Signage with the hard deadline ("Decks due 60 minutes before your session — no exceptions") posted at the door and printed in the speaker pack. Ready room opens at least 60 minutes before doors and stays staffed through the last session of the day.

**Staffing ratio:** one SRR tech per 15 speakers per day, minimum two techs on any multi-track conference so one can escort a deck to the room while the other keeps intake moving.

---

## 2. Dual-Laptop Redundancy Architecture

### 2.1 Core Principle: Both Machines Always Live

The single most important design decision: **both laptops output continuously into a seamless switcher whose inputs are all scaled and synchronized.** Switching is then an internal video-layer cut of one frame. Nothing on either laptop changes, no cable is moved, and no handshake occurs.

The failure mode this avoids is EDID/HDCP renegotiation. Pulling HDMI from laptop A and plugging laptop B, or switching a non-seamless matrix, forces the sink to re-read EDID and re-establish HDCP. Measured on a Dell Precision 3591 into an Epson L1075U:

| Switch Method | Black Duration | Notes |
|---------------|----------------|-------|
| Physical HDMI swap | 3.5-7.0 s | EDID re-read, Windows display re-enumeration, PowerPoint may drop out of slideshow |
| Non-seamless matrix switch (no scaler) | 1.8-4.5 s | Sink re-locks to new timing; HDCP re-auth adds ~1.2 s |
| Seamless switcher, cut (Roland V-8HD) | **1 frame, 16.7 ms @ 60 Hz** | Imperceptible |
| Seamless switcher, 0.5 s dissolve | 500 ms, no black | Preferred on-screen look for a planned switch |

That 3.5-7.0 second figure is why the "just swap the cable" approach is not an acceptable redundancy plan for a general session, and it is also why **Windows display re-enumeration can kick PowerPoint out of slideshow mode entirely** — turning a 4-second problem into a 30-second problem with the presenter's desktop on screen.

### 2.2 Switcher Selection

| Device | Inputs | Latency | Genlock | Street (2026 USD) | Fit |
|--------|--------|---------|---------|-------------------|-----|
| Roland V-8HD | 8× HDMI 1080p | ~1 frame (16.7 ms) | Internal ref, all inputs scaled | ~$2,499 | **Breakouts and mid-size general sessions.** Workhorse choice |
| Roland V-160HD | 16 (HDMI + SDI) 1080p | ~1 frame | Yes, frame-sync all inputs | ~$4,499 | General session with camera IMAG added |
| Roland V-600UHD | 6 (4K HDMI/SDI/DP) | 1-2 frames | Yes | ~$8,000 | 4K native content, LED wall |
| Blackmagic ATEM Television Studio HD8 ISO | 8 (HDMI/SDI) | 1-2 frames | Yes, resync on all | ~$2,995 | When ISO recording of every input is a deliverable |
| Barco PDS-4K | 8 (HDMI/DP/SDI) | 1 frame | Yes, true seamless | ~$22,000-26,000 (rental $350-500/day) | Large-format general session; the industry reference presentation switcher |
| Analog Way Midra 4K (Eikos4/Saphyr4) | 8-12 | 1-2 frames | Yes | ~$10,000-16,000 | Multi-layer, PIP-heavy corporate keynote |
| Barco E2 / EX | Modular, 4K | 1 frame | Yes | Rental $1,200-3,000/day | Blended multi-screen, 3+ projector arrays |

**A note on "Barco Pulse."** Barco Pulse is not a switcher — it is the image-processing and control electronics platform inside Barco's laser projectors (UDX, F80/F70, G/I series). It provides warp, edge blend, EDID handling, and the web/Pulse API control interface on the **projector side**. The Barco product that performs seamless presentation switching is the **PDS-4K** (or E2/EX/S3 for screen management). A large keynote rig commonly uses both: a PDS-4K switching laptop A/B, feeding a Pulse-based UDX projector that handles warp and blend. Do not spec "Barco Pulse" expecting a switcher.

**Selection rule.** For a two-laptop presentation rig with a confidence feed, the V-8HD is sufficient and is roughly 1/10 the cost of a PDS-4K. Escalate to PDS-4K or E2 when the deliverable includes blended multi-projector arrays, 4K native content, or a client contract that specifies a redundant-PSU switcher.

### 2.3 Signal Flow

```
                     ┌────────────────────────────────────────────────┐
                     │            SHOW RACK (FOH or backstage)        │
 ┌──────────┐        │                                                │
 │ LAPTOP A │HDMI    │  ┌─────────────┐   ┌──────────────┐            │
 │ (PGM)    ├────────┼─►│ EDID        ├──►│              │            │
 │ Win 11   │  1080p │  │ emulator    │   │  SEAMLESS    │            │
 │ 1920x1080│  60 Hz │  │ (locked to  │   │  SWITCHER    │            │
 │ @60      │        │  │ 1080p60,    │   │              │ PGM out    │
 └────┬─────┘        │  │ HDCP OFF)   │   │ Roland V-8HD ├──┬─────────┼──► SCALER / PROC
      │              │  └─────────────┘   │              │  │         │    (warp, blend,
      │ USB          │                    │  In 1 = A    │  │         │     native res)
      │ (clicker     │  ┌─────────────┐   │  In 2 = B    │  │         │          │
      │  receiver 1) │  │ EDID        │   │  In 3 = HOLD │  │         │          ▼
 ┌────┴─────┐        │  │ emulator    ├──►│  In 4 = VT   │  │         │    PROJECTOR
 │ LAPTOP B │HDMI    │  │ (identical) │   │              │  │         │    (Barco Pulse
 │ (BKP)    ├────────┼─►└─────────────┘   │  MULTIVIEW ──┼──┼───────┐ │     platform:
 │ identical│        │                    │  AUX 1 ──────┼──┼─────┐ │ │     warp/blend/
 │ build    │        │                    └──────────────┘  │     │ │ │     EDID)
 └────┬─────┘        │                                      │     │ │ │
      │ USB          │                                      │     │ │ │
      │ (receiver 2) │                                      │     │ │ │
      │              └──────────────────────────────────────┼─────┼─┼─┘
      │                                                     │     │ │
 ┌────┴──────────────┐                            ┌─────────▼──┐  │ └──► BACKUP
 │ DSAN PerfectCue   │                            │ V1 MULTI-  │  │      PROJECTOR
 │ dual output       │                            │ VIEW 24"   │  │      (dark, on,
 │ advances A AND B  │                            └────────────┘  │       shutter closed)
 │ simultaneously    │                              ┌─────────────▼──┐
 └───────────────────┘                              │ CONFIDENCE MON │
                                                    │ 32" downstage  │
                                                    │ <20 ms lag     │
                                                    └────────────────┘
```

**Input assignments, standardized across every show so muscle memory transfers:**

| Input | Source | Purpose |
|-------|--------|---------|
| 1 | Laptop A (primary) | Live deck |
| 2 | Laptop B (backup) | Identical deck, same slide index |
| 3 | HOLD / logo slide (dedicated mini-PC or switcher still store) | The panic button. Always available, never depends on a laptop |
| 4 | Video playback (VT) machine | Sizzle reels, walk-in loop |
| 5-6 | Camera / IMAG | Optional |
| 7-8 | Spare / laptop C for a guest presenter's own machine | Guest machines never replace A or B |

**Input 3 is non-negotiable.** A branded hold slide on a source that is not either show laptop means that any laptop-side catastrophe is a one-button recovery to something the client is happy to have on screen. It costs a $250 mini-PC or one still-store slot.

### 2.4 EDID and HDCP Configuration

| Setting | Value | Consequence If Wrong |
|---------|-------|----------------------|
| EDID presented to laptops | Forced 1920×1080 @ 60 Hz, SDR, no audio (or 2ch 48 kHz if embedding audio) | Laptop picks 3840×2160 or 1920×1200 and the scaler soft-scales; text goes fuzzy |
| EDID source | Switcher's internal EDID manager, or inline emulator (DVIGear/Gefen, $60-120 each) | Losing EDID mid-show drops the laptop to 1024×768 and rearranges desktop icons |
| HDCP on switcher | **OFF** | With HDCP on, the record/stream leg and any non-compliant confidence monitor go black |
| Laptop content | No DRM-protected playback (no Netflix, no protected Apple TV content) | One protected clip asserts HDCP and takes down the whole downstream chain |
| Colorimetry | RGB Full range, Rec.709, SDR | RGB Limited on the laptop with Full on the projector = washed-out blacks and crushed whites |
| Refresh rate | 60 Hz on every device in the chain | 59.94 vs 60.00 mismatch produces a dropped frame every ~17 s, visible on scrolling content |

Lock display settings on both laptops and verify at every gear check. On Windows, confirm in `Advanced display settings` that the reported mode is exactly `1920 × 1080, 60.000 Hz`. On macOS, use SwitchResX or the Displays panel with `Option`-click on Scaled to expose the true mode list, and disable Overscan.

### 2.5 Master Clicker and Dual-Receiver Configuration

The requirement is that **one press advances both laptops**, keeping slide indices identical so a failover lands on the same slide. There are three ways to achieve it, in descending order of reliability.

**Option A — DSAN PerfectCue with two computer outputs (recommended).** The PerfectCue system is built for exactly this: one handheld transmitter, one receiver base, and **two independent USB HID outputs**, each connected to one laptop. A single press sends Page Down to both machines simultaneously. It also carries the cue-light function (see section 5).

| Item | Model | Street (2026 USD) | Notes |
|------|-------|-------------------|-------|
| PerfectCue base + transmitter | DSAN PC-AS7 / PerfectCue Signature | $650-850 | 2 computer outputs, cue light out, 300+ ft range |
| PerfectCue Micro | DSAN PC-MICRO | $550-700 | Compact 2-output version, breakout-friendly |
| Spare transmitter | DSAN PC-TX | $180-250 | One per stage, always |
| Cue light | DSAN SL-31 (3-color) | $350-420 | Green/amber/red, driven from the base |

**Option B — Two consumer clickers, mechanically paired.** Two Logitech Spotlight units, one receiver in each laptop, both clickers taped together or held in one hand so a single squeeze hits both. Crude, cheap, works. The failure mode is unequal actuation — one clicker registers, the other does not, and slide parity silently drifts.

**Option C — One clicker on laptop A, G1 shadows on laptop B.** G1 manually advances the backup with a keyboard while watching the multiview. Viable for a 20-slide deck; unmanageable for a 90-slide deck with builds.

**Presenter-facing clicker comparison:**

| Model | Link | Range | Measured Advance Latency | Battery | Street (2026 USD) | Notes |
|-------|------|-------|--------------------------|---------|-------------------|-------|
| Logitech Spotlight | 2.4 GHz USB receiver + BLE | ~30 m | 45-70 ms | USB-C rechargeable, 3 months/charge, 1 min charge = 3 h | ~$130 | Highlight/magnify cursor features; vibration timer alert. Presenter favorite |
| Logitech R500s | 2.4 GHz USB + BLE | ~20 m | 50-80 ms | 2× AAA | ~$40 | Cheap, reliable, no timer feedback |
| Kensington Presenter Expert (K72426) | 2.4 GHz USB | ~45 m | 40-65 ms | 2× AAA | ~$70-90 | Cursor control, 4-button; receiver stores in body |
| Kensington Expert Wireless w/ green laser (K72356) | 2.4 GHz USB | ~45 m | 40-65 ms | 2× AAA | ~$120 | Green laser far more visible on large screens than red |
| DSAN PerfectCue TX | Proprietary UHF | ~100 m | 30-50 ms | 9 V | included | **Dual-output, cue-light integrated** |

Practical notes that matter more than the spec sheet:

- **Green laser over red.** On a 24-foot screen at 100 lux ambient, a 1 mW red pointer is nearly invisible. Green at the same power reads clearly. Better still, discourage laser use entirely and use the Spotlight's on-screen digital highlight, which is visible on the stream and the IMAG feed.
- **2.4 GHz congestion.** Clicker receivers share the band with venue WiFi, Bluetooth comms, and every attendee's phone hotspot. Put receivers on a USB extension so they are not buried behind a laptop or inside a metal rack — a 2 m USB-A extension moving the receiver into open air is the single most effective fix for intermittent advance failures.
- **Battery discipline.** Fresh cells or full charge before every session, not every day. Log it on the gear-check sheet. A clicker at 15% will exhibit range loss before it exhibits total failure, which reads as "random missed clicks."
- **Always have a wired backup.** A USB numeric keypad or a plain wired mouse on the lectern, mapped to Page Down. Zero RF dependency.

### 2.6 Failover Time Budget

**Target: under 3 seconds from fault onset to correct content back on screen.** Measured breakdown on a V-8HD rig with G1 and V1 both on comms:

| Phase | Measured | Notes |
|-------|----------|-------|
| Fault occurs → visible on multiview | 0-100 ms | V1 sees it on the multiview before the audience registers it |
| V1 recognition / decision | 700-1,400 ms | Dominant term. Trained operators cluster at ~800 ms; untrained exceed 3 s alone |
| Hand to switcher, press PGM 2 (or CUT) | 250-500 ms | Muscle memory; button position must never change between shows |
| Switcher executes cut | 16.7 ms | One frame at 60 Hz |
| Projector / display settle | 0 ms | No re-sync: input was already genlocked and scaled |
| Confidence monitor settle | 0-40 ms | Same genlocked path |
| **Total, seamless path** | **0.97-2.04 s** | Comfortably inside budget |
| Same fault, non-seamless path | 4.1-8.4 s | Fails budget by 2-3× |

Two things dominate the result. First, **operator recognition time is the largest single term**, which is why the multiview monitor is mandatory equipment and not a luxury — V1 cannot detect a fault on a source they cannot see. Second, **nothing in the video path renegotiates**, which is what keeps the switch itself at one frame.

Reduce recognition time further by pre-arming: during any high-stakes segment (CEO keynote, product reveal), V1 keeps laptop B selected on PREVIEW with a finger resting on CUT. This removes the source-selection step and brings total failover to **0.75-1.3 s**.

### 2.7 Failover Drill (run before doors, every show day)

1. G1 confirms both laptops on the same deck, same slide, click count logged.
2. V1 selects laptop A to PGM, laptop B to PVW. Multiview confirms both images identical.
3. SM calls "standby failover drill."
4. G1 pulls the HDMI from laptop A **at the laptop end** (simulating the most common real fault: a dongle or cable failure).
5. V1 cuts to input 2. Stopwatch from the moment the multiview thumbnail goes black to the moment PGM shows correct content.
6. Record the time. **If it exceeds 3.0 s, re-drill until it does not.**
7. Restore laptop A, verify it re-syncs, cut back.
8. Repeat with a different fault: force-quit PowerPoint on laptop A; then Windows-lock laptop A.
9. Log all three times on the show report.

Common drill findings worth pre-empting: laptop A does not re-acquire after cable reinsertion because the EDID emulator was inline on the wrong side of the break; PowerPoint on laptop B was sitting in edit view rather than slideshow view; laptop B's screensaver engaged during the 40 minutes it sat unused (set both machines to `Never` sleep, `Never` screensaver, and pin a small looping media file if the OS insists on idling).

### 2.8 Show Laptop Configuration Checklist

Applies identically to A and B. Any difference between the two machines invalidates the redundancy.

**Windows 11:**

```powershell
# Pause updates, disable notifications during show, prevent sleep
powercfg /change monitor-timeout-ac 0
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
powercfg /setactive SCHEME_MIN            # High performance
# Focus Assist / Do Not Disturb ON, Settings > System > Notifications > Off
# Settings > Windows Update > Pause for 5 weeks
# Disable Fast Startup (causes display enumeration oddities on wake)
powercfg /hibernate off
```

Also: set GPU preference for `POWERPNT.EXE` to the discrete GPU explicitly (`Settings → Display → Graphics`) so Optimus does not switch mid-show and drop a frame; disable OneDrive sync on the show folder; uninstall or disable Teams/Slack/Outlook auto-start; set PowerPoint `Options → Advanced → Display → Disable hardware graphics acceleration` **off** (leave acceleration on) but **enable** `Disable Slide Show hardware graphics acceleration` if video tearing appears; disable `Use Presenter View` unless the presenter has explicitly requested it.

**macOS (Sequoia / Tahoe):**

```bash
sudo pmset -a disablesleep 1 displaysleep 0 sleep 0
sudo mdutil -a -i off                     # Spotlight indexing off
defaults write com.apple.dock autohide -bool false && killall Dock
```

Also: Focus mode / Do Not Disturb on; disable AirPlay Receiver and Sidecar; disable Handoff; disable automatic macOS and App Store updates; screen-record and accessibility permissions for Keynote/PowerPoint granted in advance (a permission prompt at showtime is a full stop); use an Apple or StarTech multiport adapter, never an unbranded dongle — cheap dongles are the leading cause of intermittent EDID dropouts on Mac show rigs.

**Both:** local admin password known to G1 and V1; disk not encrypted with a pre-boot PIN nobody on the crew has; all content on the internal SSD, never on a network share or USB stick at showtime; wallpaper set to the client's hold graphic so an accidental desktop reveal is at least on-brand.

---

## 3. Presentation Hardware Specifications

### 3.1 Projector Brightness: The Math Behind the Rule of Thumb

Do not spec lumens by seat count alone. Seat count is a proxy for screen size, and **screen area is what actually consumes lumens**. The governing relationship:

```
Required lumens = (Target luminance in fL × Screen area in ft²) / Screen gain
                  ÷ (projector lumen derate factor)
```

Target luminance for corporate work in a lit ballroom is **35-50 fL** (foot-lamberts) on screen. Cinema targets 16 fL in near-darkness; a ballroom with stage wash, house at 20%, and chandeliers up needs roughly triple that to hold contrast. AVIXA's contrast-ratio standard frames it by task: 7:1 for passive viewing, **15:1 for basic decision making (typical slides)**, 50:1 for analytical detail, 80:1 for full-motion video.

Apply a **derate factor of 0.7** to any manufacturer's ANSI lumen figure to account for lamp/laser aging, filter loading, and the fact that real content is not a full-white field. Then add headroom for ambient.

| Room | Seats | Typical Screen (16:9) | Area | Target | Gain | Calculated | **Spec** |
|------|-------|----------------------|------|--------|------|-----------|----------|
| Breakout | 50-100 | 10 ft W × 5.6 ft H | 56 ft² | 40 fL | 1.0 | 2,240 lm ÷ 0.7 = 3,200 | **3,000-4,000 lm** |
| Small general session | 100-250 | 12 ft W × 6.75 ft H | 81 ft² | 40 fL | 1.0 | 3,240 ÷ 0.7 = 4,630 | **5,000-6,000 lm** |
| Mid general session | 250-500 | 16 ft W × 9 ft H | 144 ft² | 40 fL | 1.0 | 5,760 ÷ 0.7 = 8,230 | **8,000-10,000 lm** |
| Large general session | 500-1,000 | 20 ft W × 11.25 ft H | 225 ft² | 45 fL | 1.0 | 10,125 ÷ 0.7 = 14,460 | **12,000-15,000 lm** |
| Arena / plenary | 1,000-2,000 | 24 ft W × 13.5 ft H | 324 ft² | 45 fL | 1.0 | 14,580 ÷ 0.7 = 20,830 | **20,000-30,000 lm** |
| Plenary, high ambient | 1,000-2,000 | 30 ft W × 16.9 ft H | 507 ft² | 50 fL | 1.0 | 25,350 ÷ 0.7 = 36,214 | **2× 20,000 lm stacked, or LED** |

The commonly quoted shorthand — 3,000 lm for 100 seats, 8,000 lm for 500, 15,000 lm for 1,000+ — falls out of this math and is a sound starting point. Deviate upward when: the room has windows without blackout, the client wants house lights above 30% for note-taking, the screen is wider than the seat count implies, or a rear-projection surface is used (rear-pro fabrics typically run 0.8-1.2 gain but scatter more).

**Stacking.** Two projectors converged on one screen give roughly **1.8× brightness** (not 2×, due to convergence softening and light-path losses) plus instant redundancy. On any general session over 500 seats, stacking is the correct answer to both brightness and failover: two 10,000 lm units stacked deliver ~18,000 lm and survive a single-unit failure at half brightness rather than going dark. Budget 45-90 minutes for convergence.

| Projector | Lumens | Native | Light Source | Purchase (2026 USD) | Rental/day |
|-----------|--------|--------|--------------|---------------------|------------|
| Epson PowerLite L630U | 6,200 | WUXGA 1920×1200 | Laser 3LCD | ~$2,800 | $175-250 |
| Panasonic PT-VMZ71 | 7,000 | WUXGA | Laser 3LCD | ~$3,500 | $200-300 |
| Epson Pro L1075U | 7,000 | WUXGA | Laser 3LCD | ~$8,000 | $350-500 |
| Panasonic PT-RZ790 | 7,000 | WUXGA | Laser DLP | ~$9,000 | $400-550 |
| Epson Pro L1505UH | 12,000 | WUXGA | Laser 3LCD | ~$20,000 | $700-1,000 |
| Panasonic PT-RZ21K | 20,000 | WUXGA | Laser DLP | ~$45,000 | $1,200-1,800 |
| Christie D20WU-HS | 20,000 | WUXGA | Laser DLP | ~$40,000 | $1,200-1,800 |
| Panasonic PT-RQ22K | 20,000 | 4K 3840×2400 | Laser DLP | ~$60,000 | $1,800-2,500 |
| Barco UDX-4K32 (Pulse platform) | 31,000 | 4K UHD | Laser DLP | ~$130,000 | $2,500-4,000 |

Also verify the throw distance is achievable before the truck loads. A 16 ft wide screen with a 1.3-1.9:1 standard zoom needs 21-30 ft of throw; if the room only allows 14 ft, a 0.8:1 short-throw lens is a separate line item ($2,000-6,000, or $150-400/day rental) and often the difference between a working plot and a rebuild on site.

### 3.2 Screen: Aspect Ratio and Surface

**16:9 vs 16:10 is the most common self-inflicted softness problem in corporate AV.** The chain has three aspect ratios in it:

- Content is authored 16:9 (1920×1080) in PowerPoint's default widescreen.
- Many laptops are 16:10 (MacBook Pro/Air at 1920×1200 effective, ThinkPad and Dell at 1920×1200, Surface at 3:2).
- Most professional installation and event projectors are **WUXGA 1920×1200, i.e. 16:10**.

Feed 1080p content into a WUXGA projector and it letterboxes to 1920×1080 within the 1920×1200 panel — which is correct and sharp, using 90% of the panel. The failure is when the projector is set to "Fill" or "Zoom": it stretches 1080 lines to 1200, resampling every pixel and producing visibly soft text with uneven stroke weights.

**Rules:**
1. Author 16:9. Screen 16:9. Projector aspect mode set to **Normal / Native**, never Fill or Zoom.
2. Force laptop output to exactly 1920×1080, not 1920×1200 or scaled-HiDPI.
3. On a WUXGA projector with a 16:9 screen, use lens shift and masking so the unused 120 lines fall on drape, not on the screen surface.
4. Never mix: if the house screen is 16:10, rebuild the deck at 16:10 (13.333 × 8.333 in) rather than pillarboxing.
5. Confirm with a **1920×1080 pixel-grid test pattern** at gear check. If the one-pixel checkerboard shows moiré or grey mush instead of crisp alternation, you are scaling somewhere in the chain. Track it down before doors.

**Surface selection:**

| Surface | Gain | Best For | Notes | Cost (2026 USD) |
|---------|------|----------|-------|-----------------|
| Matte white (Da-Lite Da-Mat, Draper Matt White) | 1.0 | Front projection, wide seating, controlled light | Widest viewing cone (~160°), no hot-spotting. Default choice | 9×16 ft Fast-Fold ~$3,500-5,000 + dress kit $600-900 |
| Unity/pearlescent (Da-Lite High Power) | 2.4-2.8 | Narrow rooms, brightness-starved rigs | Retroreflective; falls off badly off-axis. Only with tight seating | ~$4,000-6,000 |
| Rear projection (Da-Lite Ultra Wide Angle, Dual Vision) | 0.8-1.2 | Presenter walks in front of screen; no shadow, no blinding | Needs 12-20 ft of backstage depth or a mirror | ~$4,500-7,000 |
| ALR / CLR (Da-Lite Parallax Pure 0.8, Draper ReAct 3.0, Screen Innovations Slate 1.2, Stewart Phantom HALR) | 0.6-1.2 | Rooms with unavoidable ambient light | Rejects off-axis light; **requires correct projector geometry** | 120" diag $4,000-6,500 |
| LED wall (2.6-3.9 mm pitch) | n/a | 800+ seats, high ambient, no throw available | 1,200-1,800 nits; immune to ambient light; solves projection entirely | Rental $300-600/panel-day; 16×9 ft ≈ $6,000-12,000/day |

**On ALR screens specifically.** Ambient Light Rejecting surfaces use an optical structure — angular-selective layers or micro-louvers — that reflects light arriving from the projector axis toward the audience while absorbing light arriving from other angles, chiefly the ceiling. Real-world benefit is a 2-3× improvement in perceived contrast under 100-200 lux ambient, which is the difference between "readable" and "impressive" without adding lumens.

Two constraints decide whether ALR will work:
- **Geometry is not optional.** Ceiling-light-rejecting (CLR) surfaces are designed for a specific projector position, usually ultra-short-throw from below. Hang a standard long-throw projector above a CLR screen and it rejects *your projector* along with the ambient light. Confirm the surface's designed geometry against your rig before specifying.
- **Viewing cone narrows.** Half-gain angles of 35-45° are typical versus ~80° for matte white. In a wide ballroom, outboard seats lose brightness. For seating wider than about 120° total, matte white plus more lumens is the better trade.

Practical verdict for event work: ALR is worth it for fixed installs, executive briefing centers, and small-to-mid rooms with windows. For a one-off ballroom general session, blackout the room properly and spend the money on lumens and a stacked pair instead — you get redundancy with it.

### 3.3 Cable Runs and Distance Limits

HDMI is a high-frequency unequalized interface with no error correction. It works perfectly or it fails in ways that mimic other problems: intermittent sparkles, green/pink frames, periodic black flashes on scene changes, or a link that comes up at gear check and drops when the room warms up. **Distance-related HDMI failures are the single most common cause of unexplained video faults in ballroom rigs.**

| Distance | Signal | Cable / Method | Notes | Cost (2026 USD) |
|----------|--------|----------------|-------|-----------------|
| 0-5 m | HDMI 2.0 (18 Gbps, up to 4K60) | Premium Certified passive copper, 24 AWG | Only distance HDMI 2.0 is actually certified for | $20-40 |
| 0-10 m | HDMI, 1080p60 (4.46 Gbps) | Passive copper 22-24 AWG | Reliable for 1080p. Marginal for 4K | $30-60 |
| 10-15 m | HDMI, 1080p60 | Passive 22 AWG, **or active copper** | 15 m is the practical passive ceiling at 1080p. Test the actual cable, not the spec | $50-90 |
| 15-30 m | HDMI | **Active copper** (built-in equalizer, directional) | Directional — source end is labeled. Reversed = no link | $90-180 |
| 15-100 m | HDMI over Cat6a | **HDBaseT** extender pair (Extron DTP2, Crestron DM Lite, Atlona) | 100 m at 1080p, ~70 m at 4K60. Sub-frame latency. Solid-core Cat6a, no patch panels | $500-1,400/pair |
| 15-120 m | **3G-SDI** (1080p60) | Belden 1694A / Canare L-5CFB, BNC | The professional answer for long runs. Locking, ruggedized, daisy-chainable, error-tolerant | $1.50-3.00/m + $8-15/connector |
| 15-200 m | HD-SDI (1.485 Gbps, 1080i/720p) | Belden 1694A | Even more margin at lower bit rate | same |
| 30-100 m | HDMI | **Active Optical Cable (AOC)** | Hybrid fiber/copper, directional, thin and light. Do not kink | $150-400 (30 m) |
| 100 m-10 km | SDI over fiber | SM/MM fiber + converters (Blackmagic Mini Converter Optical Fiber 12G) | Immune to EMI and ground loops; the only sane option between buildings | $495 per converter, both ends |
| Any | 12G-SDI (4K60) | Belden 4794R | **45-70 m maximum** — 12G is far more distance-limited than 3G | $4-7/m |

**Decision rule for a ballroom rig.** FOH is typically 20-40 m from the stage, which is past the reliable HDMI limit and inside the comfortable SDI limit. So: keep HDMI runs short and local (laptop to switcher inside the rack, under 3 m), then **convert to 3G-SDI for anything crossing the room**, and convert back to HDMI at the projector. Two Blackmagic Micro Converters ($75-155 each, or a Decimator MD-HX at ~$400 for scaling plus conversion) buy a run that simply works.

**Field practice that prevents most of these faults:**

- **Test every cable before it goes in the floor**, not after. A cable tester or a quick loop-through at the rack takes 30 seconds; tracing a bad cable under carpet and cable ramp takes 40 minutes.
- **Never coil active or optical HDMI tighter than a 10 cm radius.** AOC fiber breaks internally and the failure is intermittent, not clean.
- Label both ends of every run with source and destination, and mark the source end of directional cables. Reversed active HDMI produces a dead link that looks identical to a dead port.
- **Strain-relieve every HDMI connector.** HDMI has no locking mechanism; a 0.5 kg cable hanging off a laptop port will disconnect. Use a Neutrik NAHDMI panel connector at the rack edge, tie the cable off, or use locking HDMI (HDMI cables with side screws).
- Keep video and mains cable separated by at least 300 mm where they run parallel; cross at 90° where they must cross.
- Run **one spare of every cross-room cable**, terminated and tested, coiled at both ends. Not a spare in the truck — a spare already in the floor.

### 3.4 End-to-End Video Latency Budget

Latency matters in corporate because the presenter watches the confidence monitor and the audience watches the screen, while the audio arrives on its own timeline. Divergence above roughly 2 frames becomes visible on lip-sync with IMAG, and above ~120 ms the presenter starts to feel the clicker lag.

| Stage | Latency @ 60 Hz | Notes |
|-------|-----------------|-------|
| Clicker press → PowerPoint advance | 45-70 ms | Logitech Spotlight, measured |
| PowerPoint render → HDMI out | 16.7-33 ms | 1-2 frames, GPU-dependent |
| EDID emulator / DA | <1 ms | Buffer only |
| Seamless switcher (V-8HD) | 16.7 ms | 1 frame |
| Scaler / warp-blend processor | 16.7-33 ms | 1-2 frames; Barco Pulse warp adds 1 frame |
| HDBaseT extender pair | <1 ms | Negligible |
| SDI conversion (each direction) | <1 ms | Negligible |
| Projector image processing | 16.7-50 ms | Set to "Low Latency" / "Fast" mode where available; some default to 3-frame processing |
| **Total, clicker to photons** | **112-205 ms** | Presenter-perceptible at the top of that range |
| Confidence monitor path (consumer TV) | +30-120 ms | **Use a monitor with <20 ms lag, never a hotel TV** |

Two actionable items: turn on the projector's low-latency mode (it is off by default on most units and costs nothing), and never use a hotel-supplied consumer TV as a confidence monitor — a 100 ms display lag on top of a 150 ms chain means the presenter clicks and sees nothing for a quarter second, which visibly breaks their rhythm and provokes double-clicks that skip slides.

---

## 4. Audio for Corporate

Corporate audio is a speech-intelligibility problem, not a music problem. The target is **STIPA ≥ 0.62** measured at the worst seat, with FOH speech at **72-78 dB(A)** slow at the mix position and walk-in music at **82-86 dB(A)**. Everything below serves those numbers.

### 4.1 Lectern: Gooseneck Plus Handheld Backup

The lectern gets **two mics on two console channels, always**: a permanently mounted gooseneck as the primary, and a handheld on the shelf as the backup. The handheld lives faded down but gain-set and phantom-free, ready to be pushed up in under a second. A gooseneck failure with no backup means a speaker shouting over a 500-seat room.

| Item | Model | Pattern | Key Specs | Street (2026 USD) |
|------|-------|---------|-----------|-------------------|
| Primary gooseneck | **Shure MX412/C** (12", cardioid) | Cardioid | 50 Hz-17 kHz; sensitivity −35 dBV/Pa (17.8 mV/Pa); max SPL ~127 dB; self-noise 28 dB(A); phantom 11-52 V @ 2 mA; attached in-line XLR preamp | ~$380-420 |
| Alt gooseneck, higher rejection | **Shure MX412/S** (12", supercardioid) | Supercardioid | Tighter pattern, ~3 dB more gain-before-feedback, narrower sweet spot | ~$400-440 |
| Longer reach | **Shure MX418/C** (18") | Cardioid | For tall lecterns and standing speakers over 6'2" | ~$430-470 |
| Desktop variant (panel tables) | **Shure MX412D/C** | Cardioid | Integral desktop base, mute switch, LED | ~$450-490 |
| Premium alternative | **Sennheiser MEG 14-40** (15.7") | Supercardioid | Very low self-noise, superb off-axis; used where the lectern is on-camera | ~$700-800 |
| Premium alternative | **DPA 4098** (SC4098) supercardioid gooseneck | Supercardioid | Exceptional intelligibility and feedback margin; 4098 series available in 30/45/60 cm | ~$900-1,100 |
| Handheld backup, wired | **Shure SM58S** (with switch) | Cardioid | Indestructible, universally understood | ~$120 |
| Handheld backup, wireless | **Shure ULXD2/SM58** on ULXD4 | Cardioid | Lets the backup travel with a roaming presenter | ~$1,300 (TX) + $1,400 (RX) |

**Gooseneck setup values that work as a starting point:**

| Parameter | Value | Reason |
|-----------|-------|--------|
| Capsule position | 200-250 mm from mouth, aimed at the mouth, 15-20° off-axis | Closer invites plosives and lectern-boundary buildup; further loses 6 dB of gain-before-feedback |
| Gain | Set for −18 dBFS average, −10 dBFS peaks on normal speech | Leaves headroom for the one speaker who shouts |
| HPF | 100 Hz, 12 dB/oct (raise to 120 Hz for a boomy male voice) | Removes lectern rumble, HVAC, footfall through the deck |
| Lectern boundary cut | −3 to −4 dB, 300 Hz, Q 1.4 | A hard lectern top reflects into a cardioid capsule and builds 200-500 Hz by 4-6 dB |
| Presence | +2 to +3 dB, 3 kHz, Q 1.0 | Consonant articulation; the biggest single STI improvement available |
| Sibilance | De-esser 6 kHz, 3-4 dB reduction | Only if needed; gooseneck distance usually makes this unnecessary |
| Gate | Threshold −48 dBFS, range 12 dB, attack 2 ms, hold 120 ms, release 250 ms | **Prefer automix over gating** (see 4.4). If gating, keep range shallow so it never chatters |
| Compressor | 3:1 @ −18 dBFS, attack 12 ms, release 180 ms, makeup to taste | Levels the speaker who leans in and out |
| Feedback margin | Ring out and notch to leave **6 dB** of headroom above show level | Below 6 dB, one speaker leaning in causes a howl |

Mount the gooseneck on a **shock mount** and, on a hollow wooden lectern, decouple further with a neoprene pad under the base. A speaker who taps the lectern for emphasis transmits 40 dB of thump straight into the capsule otherwise.

### 4.2 Lavalier and Headworn Microphones

| Model | Capsule Ø | Pattern | Max SPL | Colors | Street (2026 USD) | Notes |
|-------|-----------|---------|---------|--------|-------------------|-------|
| **Countryman B3** | **2.5 mm** | Omni | Up to ~150 dB (version-dependent) | Black, tan, cocoa, light beige, white | ~$400-450 | Near-invisible. **Multiple skin-tone options** and multiple sensitivity/gain versions. Interchangeable protective caps give flat, **+4 dB**, or **+8 dB** HF lift |
| **Countryman B6** | 2.0 mm | Omni | up to ~150 dB | 5 colors | ~$430-480 | Even smaller; more fragile. For on-camera executives |
| **Sennheiser MKE 2** (Gold / esp) | 3.3 mm | Omni | 142 dB | Black, beige | ~$500-600 | ~5 mV/Pa; gold-plated, **sweat/humidity resistant** — the reliability choice for a nervous keynote speaker under stage lighting |
| **Shure TwinPlex TL47** | 4.0 mm | Omni | 141 dB | Black, tan, cocoa, white | ~$430-490 | 1.6 mm paintable cable, dual-diaphragm. TL45 (lower sens) / TL46 / TL48 (higher) variants |
| **DPA 6060** subminiature | 3.0 mm | Omni | 144 dB | 5 colors | ~$700-800 | Reference-grade; IP58 |
| **DPA 4061** | 5.4 mm | Omni | 144 dB | Black, beige | ~$550-650 | High SPL, very robust |
| **Sennheiser HSP Essential Omni** headworn | 3.9 mm | Omni | 140 dB | Beige, black | ~$300-350 | For a presenter who moves and gestures a lot |
| **DPA 4066 / 6066** headworn | 5.4 / 3.0 mm | Omni | 144 dB | Beige, brown, black | ~$700-1,000 | Best gain-before-feedback of any body-worn option |
| **Countryman E6** headworn | 2.5 mm | Omni / directional | ~140 dB | 3 skin tones | ~$450-500 | Single-ear, minimal on camera |

**On skin-tone matching.** This is a client-facing detail that gets noticed on the recording and the IMAG feed. Stock at minimum black, tan/beige, cocoa, and white in the case, and choose per presenter — a black lav on a light-skinned presenter in a white shirt is as conspicuous as a white one on dark skin. Match to the **garment** when the mic sits on a lapel, and to **skin** when it is placed at the hairline or on the cheek. Cost of a full color set is a few hundred dollars and it is the cheapest professionalism available.

**Placement and gain reality.** A lav at the sternum sits 200-250 mm from the mouth, off-axis, behind a chin that shadows high frequencies. Expect:

- **6-8 dB less gain-before-feedback** than a lectern gooseneck. Budget for it: a room that is marginal on a gooseneck will feed back on a lav.
- **HF loss of 4-8 dB above 4 kHz** from chin shadowing. Compensate with the Countryman **+4 dB or +8 dB protective cap** (mechanical, no noise penalty) before reaching for EQ, then add +2-3 dB at 4 kHz if still dull.
- **Chest resonance boost of 3-6 dB around 700-900 Hz.** Cut 2-4 dB with Q 1.5-2.0.
- Position on the **centerline** (sternum, 150-200 mm below the chin) rather than a lapel where possible: a lapel mic loses 6-10 dB when the presenter turns their head away from it, which reads as inconsistent level no matter how good the compressor is.

**Rigging that prevents clothing noise:** Rycote Undercovers or Overcovers, Hollywood Topstick double-sided tape, and a **strain-relief loop** of cable taped below the capsule so tension on the cable never reaches the mic. Route the cable inside the shirt, not down the outside. Tape the transmitter to the body or use a belt clip at the small of the back — never let it dangle in a jacket pocket where it swings against the body.

**VIP dual-redundant configuration.** For a CEO keynote or anything being broadcast, put **two lavs on two transmitters on two receiver channels**: mic A on the right of the sternum, mic B on the left, roughly 100 mm apart. Keep A live and B muted-but-monitored. A1 can swap channels in under a second on a capsule failure, a cable pull, or an RF hit. Do not sum them live — 100 mm of spacing produces comb filtering around 1.7 kHz and above. Keep the two transmitters on frequencies from **different** intermod groups so a single interferer cannot take out both.

### 4.3 Wireless Frequency Coordination

**US spectrum reality as of 2026.** The 600 MHz band (617-652 and 663-698 MHz) was reallocated to mobile carriers and is no longer available for wireless microphones. Do not deploy legacy gear tuned there; it is both illegal and, in practice, unusable next to an LTE/5G tower. Current usable spectrum:

| Band | Status | Practical Use |
|------|--------|---------------|
| 470-608 MHz (UHF TV 14-36) | **Primary workhorse.** Unlicensed operation permitted in locally vacant TV channels | Where nearly all corporate RF lives |
| 614-616 MHz (duplex gap) | Available, narrow | 2-4 channels of overflow |
| 653-663 MHz | Restricted / not generally available | Verify before use |
| 902-928 MHz (ISM) | Available, shared with everything | Consumer-grade systems; heavy congestion |
| 941-960 MHz | Available with restrictions | Some pro systems (verify licensing) |
| 1.9 GHz DECT | License-free, self-coordinating | Sennheiser SpeechLine DW, Shure MXW. **Excellent for lecterns and panels** |
| 2.4 GHz | License-free, contended with WiFi | Small systems only; never for a keynote |
| 5.8 GHz | License-free | Camera hops, IFB |

**Toolchain:**

| Tool | Purpose | Cost (2026 USD) |
|------|---------|-----------------|
| **Shure Wireless Workbench 7 (WWB7)** | Frequency coordination, intermod analysis, live monitoring, scan import/export | **Free** (Win/macOS) |
| Sennheiser Wireless Systems Manager (WSM) | Same, for Sennheiser fleets | Free |
| Networked receiver scan (ULXD4/AD4Q via Ethernet) | Provides the RF scan data WWB coordinates against | included with receiver |
| **RF Venue RF Explorer Pro / Spectrum Analyzer** | Standalone scan when no networked receiver is available; finds non-TV interferers | $250-600 |
| Shure Axient Digital AD600 Spectrum Manager | Continuous scanning, real-time backup-frequency deployment | ~$5,000 |
| RF Venue 4-Zone / Diversity Fin antenna | Antenna distribution and pattern control | $400 (Fin) - $1,800 (4-Zone) |
| Shure UA844+SWB active antenna distro | 4-way split, powers remote antennas | ~$900 |
| **Shure Frequency Finder / RabbitEars.info / FCC LMS** | Pre-visit desk research on local TV occupancy | Free |

**Channel density per 6 MHz TV channel** (Shure figures, use for planning):

| System | Standard Mode | High Density Mode | Min Spacing |
|--------|---------------|-------------------|-------------|
| Shure ULX-D | 17 channels | **47 channels** (reduced TX power ≈1 mW, shorter range ~30 m) | ~350 kHz standard |
| Shure Axient Digital | 23 channels | **47 channels** | ~250 kHz standard, 125 kHz HD |
| Shure SLX-D | 16 channels | n/a | ~400 kHz |
| Analog (BLX/SLX legacy) | 8-10 channels | n/a | **≥2 MHz, plus 3rd-order intermod clearance** |

Digital systems earn their price here: an analog rig needing 2 MHz of separation plus intermod exclusion runs out of spectrum at 8-10 channels in a crowded market, while a ULX-D rig fits 17 comfortably. On a conference with 12+ channels, digital is not an upgrade, it is a requirement.

**Spectrum scan protocol — run this in order, on site, every event:**

1. **Desk research, 1-2 weeks out.** Pull the local TV allotment from RabbitEars or the FCC database for the venue's exact coordinates. Note occupied channels and their ERP. Build a preliminary coordination in WWB7 against that exclusion list.
2. **Vendor RF meeting.** Get every other RF user in the building on one call or one spreadsheet: other AV vendors, the broadcast truck, translation/interpretation, comms, the client's own kit, the venue's house systems, any hearing-assist loop. Assign non-overlapping spectrum blocks in writing. **Two vendors independently coordinating in the same band is the number one cause of show-day RF failure.**
3. **On-site scan, load-in.** Scan 470-608 MHz with all of your own transmitters **off**. Use a networked receiver or RF Explorer at the receive antenna position, at antenna height. Export the scan.
4. **Second scan with everyone else live.** Other vendors power up. Re-scan. The delta is what they occupy. Feed both scans into WWB7 as exclusions.
5. **Coordinate in WWB7.** Let it compute a compatible set with 3rd- and 5th-order intermod exclusion. Request **more frequencies than you need** — a spare per group. Deploy to receivers over the network (`Deploy` in WWB7), never by hand-typing.
6. **Walk test, at antenna height, with the room configured as it will be.** Walk every position any transmitter will occupy: lectern, full stage width, panel seats, the aisle where the roving Q&A mic goes, and backstage. Watch RF level and audio on the WWB7 monitor. Anything below −85 dBm or showing diversity thrash gets an antenna reposition.
7. **Re-scan with a full room.** Bodies absorb UHF: a full ballroom drops received level by **6-10 dB** versus an empty one. This is why the walk test in an empty room is optimistic and why antennas belong **above** head height with line of sight to the stage, not on the floor behind a drape.
8. **Monitor continuously.** WWB7 running on the audio laptop for the whole show, logging RF level and dropouts. A2 watches it. Interference that appears mid-show gets the pre-coordinated spare frequency, not an improvised guess.

**Antenna practice that eliminates most dropouts:** receive antennas on stands **2.5-3 m high**, 2-5 m from the nearest transmitter position but with clear line of sight, spaced at least 1/4 wavelength (~150 mm at 500 MHz, in practice 1 m) apart for true diversity, never behind LED walls or metal set pieces, never coiled coax, and always with the correct loss budget (RG-8X for runs over 15 m; add an inline amp only if the loss exceeds ~6 dB).

### 4.4 Automix for Panel Discussions (Behringer WING)

**Correction to a common misstatement:** the WING does not provide "8-channel automix groups." Per the WING manual, **Automix is available in the INS 2 insert slot on all 40 input channels, with two automix groups, X and Y**, enabled globally under `SETUP → Audio → Automix X/Y`. Any number of the 40 input channels can be assigned to either group. The practical limit on a panel is the number of open mics, not an 8-channel ceiling. The algorithm is classic Dugan-style **gain sharing** (not spectral/AI-based): the sum of all channel gains in a group is held constant, so as one mic becomes active the others are attenuated proportionally, keeping the group's total open-mic noise contribution and feedback exposure roughly fixed regardless of how many mics are in the group.

**Why this matters acoustically.** Every open mic adds to both the noise floor and the feedback exposure. The rule of thumb is **+3 dB of both for every doubling of open mics** (the NOM, number of open microphones, penalty). Six open panel mics is a 7.8 dB penalty versus one — enough to turn a comfortable room into a ringing one. Gain sharing recovers most of that automatically and faster than any human can ride faders.

**Setup for a 6-person panel plus moderator:**

| Step | Action | WING Path |
|------|--------|-----------|
| 1 | Enable the automix engines | `SETUP → Audio → Automix X enable` (use Y only if you need a second independent group) |
| 2 | Insert Automix on each speech channel | Channel → `INS 2` slot → load **Automix** |
| 3 | Assign every panel mic to **group X** | Automix processor on each channel → Group = X |
| 4 | Set per-channel **Weight** | Start at 0 dB on all; raise the moderator +3 to +6 dB so they can always cut in |
| 5 | Set group **Depth** | Start at **−15 dB**; this is the maximum attenuation applied to an inactive mic |
| 6 | Bypass or relax channel gates | A gate ahead of automix double-gates and causes chatter (see below) |
| 7 | Verify with the automix meters | Each channel shows its live gain contribution; watch it during a talk test |
| 8 | Store as a snapshot with scope set | `LIBRARY → SNAPSHOTS`, scope to include INS 2 parameters |

**Group assignment rules:**

- **One group for all simultaneously-open speech mics on the same acoustic stage.** Gain sharing only works across mics that are actually competing. Putting the panel in X and the moderator in Y defeats the purpose — the moderator's mic would no longer duck the panel's.
- **Use group Y for an acoustically separate zone**: audience Q&A floor mics, a satellite location, or an on-stage interview area far from the panel table. Two independent gain-sharing pools, no cross-interaction.
- **Never put these in an automix group:** playback and VT channels, music, the lectern mic if a solo presenter is speaking while the panel is off (or, better, assign it to X too and let it win by weight), and any channel A1 intends to ride manually. Automix and a hand on the fader fight each other.

**Depth selection:**

| Depth | Effect | Use When |
|-------|--------|----------|
| −6 dB | Gentle; preserves room ambience and cross-talk feel | Broadcast/recorded panels where natural room tone is wanted |
| −12 to −15 dB | **Default.** Clear winner-takes-most behavior, still natural | Standard corporate panel |
| −20 dB and beyond | Aggressive; audible pumping on fast interchanges, and a speaker who starts mid-sentence gets clipped | High-feedback rooms only, as a last resort |

**Weight is not volume.** Weight biases which mic wins the gain-sharing competition; the fader still sets level. If one panelist is quiet and keeps getting ducked by a louder neighbour, the fix is **input gain and weight**, not fader. Set input gains so all panel mics read comparable levels on normal speech first, *then* adjust weight for priority. Weight applied to fix a gain error produces a mic that either never opens or never closes.

**Do not gate and automix the same channel.** A gate ahead of the automix insert makes the automix see a signal that is already being chopped, so it cannot compute stable gain shares — the audible result is chatter on sibilants and a mic that drops the first syllable of every sentence. Choose one: automix for panels and multi-mic speech (nearly always correct), gating for a single loud source with heavy bleed. If a channel truly needs both, set the gate range to no more than 6 dB with a 200 ms hold so it acts as a mild noise reducer rather than a switch.

**Panel channel starting values:**

| Parameter | Value |
|-----------|-------|
| Mic | Shure MX412D/C desktop gooseneck per seat, or TwinPlex TL47 lav per panelist |
| Gain | −18 dBFS average on normal speech, matched across all seats |
| HPF | 120 Hz, 12 dB/oct (table mics pick up more LF than lectern mics) |
| Table boundary cut | −3 dB @ 250 Hz, Q 1.4 |
| Presence | +2 dB @ 3.5 kHz |
| Compressor | 3:1 @ −18 dBFS, 15 ms / 200 ms, post-automix |
| Automix | Group X, Weight 0 dB (moderator +4 dB), Depth −15 dB |
| Gate | Bypassed |

### 4.5 System Levels, Coverage, and Program Audio

| Target | Value | Measurement |
|--------|-------|-------------|
| Speech, FOH position | **72-78 dB(A)** slow | Averaged over 30 s of continuous speech |
| Walk-in / play-off music | **82-86 dB(A)** slow | Loud enough to fill the room, quiet enough to talk over |
| Awards / high-energy reveal | 90-95 dB(A) peak | Brief; do not sustain |
| Coverage variance, front to back | **≤ 6 dB** | Broadband, measured at seated ear height |
| Speech intelligibility | **STIPA ≥ 0.62** at the worst seat | NTI XL2 or Smaart with STIPA source |
| Feedback margin at show level | **≥ 6 dB** | Ring-out test before doors |
| Speech HPF, system | 80-100 Hz | Nothing musical in speech below this |
| Program headroom | Mix bus peaks −6 dBFS | Leaves room for the unexpected |

**Delay speakers.** Any seat more than ~20 m from the main arrays needs fill. Set delay time from the physical distance at **2.91 ms/m** (343 m/s at 20 °C), then add a **10-15 ms Haas offset** so the delay speaker arrives slightly *after* the mains — this keeps the listener's sense of localization on the stage rather than on the speaker above their head. Verify with dual-channel transfer function measurement, not by ear alone, and re-check if the room temperature will shift more than a few degrees between soundcheck and showtime (speed of sound changes ~0.6 m/s per °C, which is 1-2 ms over a 30 m throw).

**Program audio from the show laptops.** Embed audio in the HDMI to the switcher and de-embed at the rack, or run a separate analog pair from a small USB interface. Either way:

- **De-embed, do not rely on the projector.** Projector speakers are never used, and pulling audio off a projector's analog out puts a 25 m unbalanced run in the signal path.
- Set the laptop's OS output level to **100%** and control level at the console. A laptop at 60% has already thrown away headroom and added noise.
- Mute the laptop's system sounds. A Teams notification chime at 90 dB(A) in a 500-seat room is a career moment.
- **Both laptops' audio must be patched and gain-matched.** A video failover that lands on laptop B with no audio is only half a recovery.
- Sync check: a video that is 2 frames out of lip-sync is noticeable. If the video path adds 3 frames (50 ms) of processing, delay the audio to match. Measure it with a clap-sync clip in the test deck, do not estimate.

---

## 5. Timing and Cue Protocol

Corporate events are contractual about time. A general session that runs 12 minutes long pushes lunch, pushes the breakouts, and in a hotel can trigger overtime charges across catering and AV. Timing discipline is a deliverable, not a courtesy.

### 5.1 The Warning Ladder

Agree this in the production meeting, brief every speaker on it in the ready room, and never improvise it live.

| Cue | Signal | Delivery | Speaker Expectation |
|-----|--------|----------|---------------------|
| Halfway | Optional; on-screen timer only | Confidence monitor | Informational |
| **10 minutes remaining** | Timer shows 10:00; no light change | Confidence monitor / timer display | Begin planning the wrap |
| **5 minutes remaining** | **Green light on** (steady) + timer 5:00 | Cue light + timer | Start moving to closing content |
| **2 minutes remaining** | **Amber light on** (steady) | Cue light + timer | Wrap current point. Do not start a new section |
| **Time / hard stop** | **Red light on** (steady) | Cue light + timer at 00:00 | Deliver one closing sentence and hand back |
| **Over by 60 s** | **Red flashing** | Cue light | Stop now. SM prepares intervention |
| **Over by 2 min** | Red flashing + SM/host intervention | Host walks on, or IFB to host | Escalation (see 5.4) |

Two design choices in that ladder are deliberate. **Green means "5 minutes left," not "you're fine."** A light that means "everything is normal" is ignored; a light that only ever appears as the first warning gets noticed. And **the ladder is briefed in advance** — a speaker seeing an unexplained amber light for the first time mid-keynote will interpret it as a technical problem and lose their thread.

### 5.2 Cue Light and Timer Hardware

| Item | Model | Street (2026 USD) | Notes |
|------|-------|-------------------|-------|
| 3-color cue light | **DSAN Signal-Light SL-31** | ~$350-420 | Green/amber/red, steady or flash, driven from PerfectCue base or standalone controller |
| Single-color cue light | DSAN SL-11 | ~$220-280 | For a simple "wrap" signal |
| Speaker timer, large display | **DSAN Limitimer PRO-2000** | ~$480 | Programmable segments, chime, drives an SL-series light |
| Speaker timer, multi-segment | DSAN Limitimer PRO-3000 / AS-1 audience display | ~$700 / ~$500 | For multi-speaker sessions with per-speaker allocations |
| Combined cue + advance | **DSAN PerfectCue** (PC-AS7) | ~$650-850 | Cue light output **and** dual computer advance in one box (see 2.5) |
| Wireless timer/cue app | Stage Timer / Irisdown Countdown on the confidence feed | $0-200 | Renders the timer as a layer on the confidence monitor. No extra hardware on stage |
| IFB, wireless | **Shure PSM300** (P3TR) | ~$700/set | Single-ear earpiece for hosts and moderators |
| IFB, wireless (broadcast standard) | **Comtek PR-216 / M-216 TX** | ~$500 RX / ~$800 TX | The industry reference for talent IFB |
| Crew comms, wired | Clear-Com HelixNet, 2-channel | ~$2,500 base + $450/beltpack | For fixed positions |
| Crew comms, wireless | **Hollyland Solidcom C1 Pro** 4-pack (DECT, full duplex) | ~$1,000-1,300 | Excellent value; ENC noise cancelling; 1.9 GHz so it does not compete with UHF mic spectrum |
| Crew comms, wireless (premium) | Clear-Com FreeSpeak II | ~$1,200/beltpack + base | For large crews and long distances |

**Cue light placement.** Downstage centre on the deck, angled up toward the speaker's eyeline, roughly 2-4 m in front of the lectern and **outside the audience's sightline** — a red light visible to the room telegraphs that the speaker is over time. On a thrust or in-the-round stage, use two lights, or switch to IFB and an on-screen timer instead.

**Timer on the confidence monitor is the single highest-value addition** to a corporate rig. A timer layered onto the confidence feed (Irisdown Countdown, Stage Timer, or the switcher's own overlay) is always in the speaker's field of view, needs no extra hardware on the deck, and can be reset per speaker from FOH. Use large digits, count **down** not up, and switch the digits to amber at 2:00 and red at 0:00 so the color coding matches the cue light for anyone using both.

**IFB versus cue light.** Cue lights are non-verbal and never interrupt: right for a solo keynote where the speaker must not be distracted. IFB is bidirectional and specific: right for a host, moderator, or emcee who is expected to manage the room ("wrap the panel after the next answer," "we're going to VT in 30"). A moderator on a panel should always have IFB — they are the only person who can steer a panel back on time, and they can only do it if SM can talk to them.

### 5.3 Speaker Overrun Handling

**Prevention beats intervention.** Every one of these is cheaper than a live intervention:

- Brief the ladder in the ready room and have the speaker acknowledge it on the sign-off sheet.
- Have the speaker rehearse to the actual clock on the ready room timer. A speaker who has never timed their talk will run 20-30% long.
- Build the running order with **buffer between sessions**, not a continuous back-to-back schedule. 5 minutes between speakers absorbs normal variance.
- Put the timer on the confidence monitor from the first second of the talk, not at the 5-minute mark.
- Agree the escalation path with the client **in the production meeting, in writing**, including who has authority to cut off a senior executive. That decision must never be made for the first time at 2 minutes over.

**Escalation, in order:**

| Stage | Trigger | Action | Who |
|-------|---------|--------|-----|
| 1 | 5 min remaining | Green cue light, timer visible | SM |
| 2 | 2 min remaining | Amber cue light | SM |
| 3 | 0:00 | Red cue light, steady | SM |
| 4 | +60 s | Red flashing | SM |
| 5 | +90 s | IFB to host/moderator: "Standby to wrap [Name]" | SM → host |
| 6 | +2 min | Host walks to the edge of the stage into the speaker's peripheral vision, applauding lightly | Host |
| 7 | +3 min | Host walks on, takes the handheld, "Let's give a huge thank you to..." Music stinger under. Slide cuts to hold graphic | Host + A1 + V1 |
| 8 | +4 min, only with pre-agreed client authority | Play-off music up to 82-86 dB(A), house lights to 70%, screen to hold graphic | A1 + LX + V1 |

Stage 7 is the workable intervention and it is entirely non-confrontational: the host thanking a speaker reads to the audience as a planned transition. **Stage 8 requires explicit prior authorization**, ideally from the client's own senior stakeholder, because bringing music up on a talking executive is a decision with political consequences. Get that authorization in the production meeting and note who gave it.

### 5.4 Stage Manager Scripts and Cue Calling

**Cue calling language.** Standardized, because ambiguity on comms costs seconds. Every cue is called in two parts: a **standby** (department, cue number, at least 10 seconds ahead) and a **go** (department name last, so the operator's trigger word arrives at the exact moment of execution).

```
SM: "Standby AUDIO 12, VIDEO 12, LX 12."
A1: "Audio 12 standing by."
V1: "Video 12 standing by."
LX: "LX 12 standing by."
SM: (at the moment)  "Audio 12, Video 12, LX 12 — GO."
```

Never say "go" in conversation on an open channel. Never call a cue without a standby. If a standby is not acknowledged by every department named, **do not call the go** — re-standby instead.

**Cue sheet format.** One row per cue, printed, in a binder, with a pencil. The show file on the console is not a substitute; a console reboot must not erase the show's structure.

| Cue | Time | Trigger | AUDIO (A1) | VIDEO (V1/G1) | LX | SM Note |
|-----|------|---------|-----------|----------------|-----|---------|
| 1 | 08:45 | Doors open | Walk-in playlist up, 84 dB(A) | Hold graphic, PGM = In 3 | House 100%, stage wash off | PW: speakers to SRR |
| 2 | 08:58 | SM call | Music fade to 74 dB(A) over 8 s | Hold graphic | House to 60% | "2 minutes" over PA optional |
| 3 | 09:00:00 | SM go | Music out over 3 s. **Host lav CH1 open** | Opening titles VT, PGM = In 4 | House to 20%, stage wash up | Host walks on VT out |
| 4 | 09:02 | Host intro ends | CH1 stays open | **PGM = In 1 (Laptop A)**, PVW = In 2 | Lectern special up | G1: confirm slide 1 of Nakamura v03 |
| 5 | 09:02 | Speaker at lectern | Gooseneck CH3 open, host CH1 closed | Confidence feed live, timer reset 20:00 | — | **Cue light armed** |
| 6 | 09:17 | Timer 5:00 | — | — | — | **Green light** |
| 7 | 09:20 | Timer 2:00 | — | — | — | **Amber light** |
| 8 | 09:22 | Timer 0:00 | — | — | — | **Red light** |
| 9 | 09:22 | Speaker wraps | CH3 closed, CH1 (host) open | PGM = In 3 hold graphic | House to 40% | Applause; PW: next speaker to wing |
| 10 | 09:23 | Panel set | CH4-10 open, **Automix X active** | PGM = In 1, panel deck | Panel wash up, lectern special out | 6 chairs preset SL |

**Pre-show verbal checklist**, run by SM on comms with every department answering aloud. No silent assumptions.

```
SM: "Comms check, all positions."            → each position answers by name
SM: "A1, RF status?"                         → "All 14 channels green, batteries fresh, WWB monitoring"
SM: "A1, lectern gooseneck and handheld?"    → "Both gain-set, handheld faded and ready"
SM: "A1, automix group X active?"            → "Confirmed, 7 channels, depth -15"
SM: "G1, laptops A and B?"                   → "Both on Nakamura v03, slide 1, hash verified, 42 clicks"
SM: "G1, clicker?"                           → "Dual output confirmed, both machines advancing, spare TX on lectern shelf"
SM: "V1, switcher?"                          → "In 1 PGM, In 2 PVW, In 3 hold graphic armed, HDCP off"
SM: "V1, failover drill time?"               → "1.4 seconds, logged"
SM: "V1, projectors?"                        → "Both lamps on, converged, backup shuttered"
SM: "LX, presets?"                           → "Cue 1 loaded"
SM: "PW, talent?"                            → "Nakamura in the wing, mic'd, briefed on cue lights"
SM: "SRR, deck status?"                      → "All morning decks validated and deployed, signed off"
SM: "Standby cue 1."
```

**Post-show report**, written the same day while detail is fresh: failover drill times, any RF events with timestamps, decks that arrived late and what was done, actual versus scheduled session times, and every fault with its resolution. This document is what turns a single event's pain into next event's prevention, and it is what protects the crew when a client's recollection of events differs.

---

## 6. Common Failure Modes

The failures below are the ones corporate crews actually see, ordered roughly by frequency on multi-day general sessions. Each row is the on-site truth, not the textbook version. "Symptom" is what the audience or crew sees first; "Cause" is the underlying fault chain (often several layers deep); "Fix" is the live recovery; "Prevention" is the gear check or protocol that would have made it not happen.

The general rule across all of them: **the first 30 seconds are about getting correct content back on screen or correct audio back in the room.** Diagnosis can happen in parallel; audience and presenter never wait for it. If the fix takes longer than the budget allows, go to the next column's solution (hold graphic, play-off music, host intervention) and come back to the real fix once the room is stable.

| # | Symptom | Cause | Fix | Prevention |
|---|---------|-------|-----|------------|
| 1 | **Presenter laptop crashes mid-session** (BSOD, frozen app, black screen) | OS update forced mid-show; GPU driver fault; overheating; presenter plugged in a personal USB device that triggered a driver load | V1 cuts to laptop B (input 2) on the seamless switcher — 1 frame. G1 force-restarts laptop A in parallel. Once laptop A is back, verify slide index, cut back when parity is confirmed | Pause Windows updates for 5 weeks pre-show (see 2.8); pin GPU preference for PowerPoint; ban presenter USB insertion; carry a fresh, imaged spare laptop C with the same deck loaded, sitting on the rack as a tertiary backup |
| 2 | **Clicker battery dead / lost / left at hotel** | Speaker brought their own clicker with unknown charge state; alkaline cells leaked; 2.4 GHz receiver unplugged during transport | Wired USB mouse or numeric keypad at the lectern mapped to Page Down / arrow keys (always pre-wired and tested — see 2.5). G1 takes over advance on laptop B from FOH while a runner sources fresh cells or a spare clicker | Issue a venue-owned clicker at check-in, fresh cells in front of the speaker; never trust a personal clicker; keep a 4-pack of spare AAA/9 V cells in the SRR and on the lectern; log clicker battery voltage on the gear check sheet |
| 3 | **Slide aspect ratio mismatch on screen** (letterboxed, pillarboxed, stretched faces, cropped edges) | Speaker's deck authored at 4:3, or 16:10, or 16:9 but with content in a 4:3 safe area; laptop output set to a non-1080p mode; projector aspect mode on "Fill" or "Zoom" instead of "Normal" | V1 selects the hold graphic (input 3) immediately. G1 forces laptop to 1920×1080 @ 60 Hz, verifies on multiview. If deck itself is wrong, present the PDF export full-screen in Acrobat as the fallback until SRR re-renders at 16:9 | Force `Slide Size → Widescreen 16:9` at intake (step 4 in 1.2); lock EDID to 1080p60 (2.4); set projector aspect to Normal / Native; verify with the 1-pixel checkerboard test pattern at gear check |
| 4 | **Microphone feedback / howling** | Open mic gain too hot; speaker leaning into the lectern mic; new mic position closer to a speaker than the ring-out was done; automix not active and multiple panel mics are open | A1 pulls the offending mic's fader down 6-10 dB immediately, then rings out a new notch with the room muted; if persistent, switch to the handheld backup on the shelf (4.1) | Ring out to 6 dB headroom at soundcheck with the actual mic in position; engage automix group X for any panel >3 mics (4.4); set HPF and lectern boundary cut as in 4.1; never change mic position once the show has started |
| 5 | **Recording / stream dropouts** (encoder freezes, dropped frames, audio gaps in the recording) | Encoder overload from a 1080p60 source it can only handle at 1080p30; network uplink congestion from venue sharing; wrong audio routing (stream gets program but presenter audio is on a separate bus); encoder fan overheating in a closed rack | A2 / V1 confirm encoder input is still live on the encoder's local confidence monitor. If the encoder has crashed, swap to the backup encoder (always racked and pre-configured). Audio: confirm the stream mix bus is actually routed to the encoder's audio input — the most common cause of "video good, audio missing" is a wrong routing matrix page | Spec encoder for the actual resolution and bitrate (e.g. Magewell or AVer capture + OBS / vMix on a dedicated laptop, not a consumer encoder doing 1080p60 H.265); provision a **dedicated** uplink (separate SSID or wired) with committed bandwidth; rack encoder with 100 mm clearance and a small fan; build the audio send to the encoder as a labeled bus and verify it at every gear check |
| 6 | **Backup laptop fails to switch (V1 cuts to input 2 and the image is wrong / black / out of sync)** | Laptop B was in edit view, not slideshow; slide index drifted from A because of unequal clicker actuation; laptop B was asleep; cable wasn't actually live (input 2 not patched) | V1 cuts to input 3 (hold graphic) immediately — never to a source that has not been confirmed live. G1 wakes laptop B, brings it to slideshow at the same slide index as A, then V1 cuts to it. Whole incident should land under 3 s if hold graphic is pre-armed | Drill the failover before doors every show day (2.7); both laptops set to Never sleep, Never screensaver; PerfectCue dual-output clicker (2.5) so parity cannot drift; multiview always shows both laptops so V1 sees a fault on B before they have to switch to it |
| 7 | **Projector goes dark mid-session** | Single-unit failure; lamp/laser fault; fiber or HDMI cable pull; thermal shutdown from blocked intake | V1 cuts to backup projector (already lit and shuttered on standby — see 3.1); on a stacked pair, the surviving unit keeps the show running at ~half brightness; A1 brings house lights up 20% to mask the loss | Stack projectors on any rig over 500 seats (3.1); keep backup projector on, lamp warm, shutter closed; verify all projector intake paths are clear of drape and signage; test every cross-room cable pre-rig |
| 8 | **Confidence monitor goes black / shows wrong source** | Cable pull; presenter bumped the lectern HDMI; monitor's input select got changed by a presenter who "fixed" the remote | G1 confirms laptop A and B are still on PGM via the multiview — the audience screen is unaffected. V1 / G1 swaps the confidence feed to a backup monitor or layers the deck source via the switcher's AUX output | Lock the lectern's cable paths with strain relief (3.3); tape over the confidence monitor's input button or remove the remote from the lectern; pre-patch a labeled spare confidence monitor at FOH that V1 can switch the AUX to in under 5 s |
| 9 | **Embedded video plays no audio in the deck** | Speaker exported clip without audio; codec is HEVC/ProRes and PowerPoint's Media Foundation plays video but not the audio track; AAC sample rate is not 48 kHz | G1 advances past the clip, V1 cuts to hold graphic if it loops badly. A1 plays the clip's audio from a backup stereo file cued on the playback machine; V1 cuts back to laptop when clear | Always verify clip audio in the ready room dry run (step 8 in 1.2); transcode to house spec H.264/AAC 48 kHz stereo (1.2 step 5); for any hero clip, also stage the audio as a separate file on the playback machine, labeled and cued |
| 10 | **Wireless mic dropout mid-sentence** | RF interference from a previously-coordinated source that came up late (cell tower, broadcast truck, another vendor's gear); transmitter battery low; antenna cable damaged; presenter walked behind an LED wall | A2 mutes the failing channel and unmutes the redundant channel (VIP dual-mic config, 4.2) in under 1 s. SM does not announce it; A2 monitors WWB7 and deploys the pre-coordinated spare frequency if the issue persists | Continuous WWB7 monitoring (4.3); coordinated spare frequency per group; remote antennas above head height with line of sight to the stage; transmitter battery voltage logged at every gear check; dual-mic config for any VIP being recorded |
| 11 | **Hold slide / logo displays correctly but never goes away** (operator forgets to cut back) | Distraction on comms; PGM and PVW were swapped and V1 cut to what they thought was PVW | V1 / G1 cuts to laptop A or B explicitly by name; SM confirms on comms; whole event pause, no further action needed once correct source is on air | Standardize input assignments across every show (2.3); color-code PGM and PVW borders on the multiview (PGM red, PVW green) so the live source is unambiguous; SM calls "PGM is 1, PVW is 2" on comms at every transition |
| 12 | **PowerPoint enters slideshow but display is on the laptop screen, not the projector** | Presenter View enabled and assigned to the wrong display; "Automatic" display detect picked the internal panel when the switcher's EDID changed | G1 disables Presenter View, sets the slide show monitor explicitly, restarts the slideshow. V1 cuts to hold graphic to cover the 10-15 s window | Set `Slide Show → Monitor` explicitly (step 7 in 1.2); configure both show laptops identically; pin to extended desktop, not duplicate, and verify at gear check with the projector actually on |
| 13 | **Font substitution visible on screen mid-deck** (text reflows, headline wraps, brand typeface replaced with Arial) | Font's `fsType` embedding bit was Restricted; cloud font download failed offline; font installed on the preview station but not the show laptop | V1 cuts to hold graphic. G1 substitutes a metric-compatible face and re-checks the affected slides, then V1 cuts back. If too many slides are affected, present the PDF export full-screen for the rest of the session | Embed fonts at intake (1.2 step 3); install all brand fonts on both show laptops from a verified font pack; for brand-critical hero slides, convert text to outlines or use the full-bleed PNG fallback; always have the PDF export standing by as insurance |
| 14 | **Audio is fine on FOH but missing from the recording / stream** | Encoder audio input source is wrong; audio routing matrix is on the wrong page; a mute group that mutes the stream bus is engaged | A2 / broadcast engineer verifies the encoder's audio meter — if silent, repatches from the labeled stream mix bus; if that bus is dead, repatches from the program L/R bus as emergency | Build a labeled, dedicated stream mix bus and physically label every cable; verify audio on the recording at every gear check and again at the top of every break; never let a single mute group control both FOH and stream |
| 15 | **House lights come up during a video segment** | LX op misread the cue sheet; preset 4 loaded instead of preset 5; DMX cue triggered by a stray controller | LX cues back to the correct preset immediately. SM calls "Standby LX, return to preset 5" so LX op confirms before re-cueing | Number presets in the order they're used; SM calls every LX preset by name on comms with a standby; never let a stage manager override an LX cue without an explicit "LX go" |
| 16 | **Switcher locks up / freezes on a frame** | Static-discharge event on a rear-panel input; firmware bug on certain HDMI sources; thermal overload in a poorly-ventilated rack | V1 powers the switcher cycle (cold reboot takes 30-45 s — too long for live). If a spare switcher is racked, swap inputs in under 60 s. Cover with hold graphic from the mini-PC on input 3 during recovery | Rack switcher with 50 mm clearance and a quiet fan; keep firmware current between events, not during; carry a pre-configured spare switcher for any general session; never route the show through a switcher that is also driving the multiview (separate the multiview output's source if the switcher is overloaded) |
| 17 | **Speaker arrives with a wrong / corrupted / password-locked file** | USB stick failing; file from email was the wrong version; file is a Mac package the show PC cannot read | SRR tech attempts recovery with the speaker present (re-export from package, find a clean USB). If recovery fails, present the **last validated version** from the show share; if no prior version, present the PDF export. Client is told in writing, on the spot, by the account lead — not by the crew mid-show | 60-minute buffer rule (1.1) — every deck is ingested, validated, and signed off well before showtime; speakers are emailed the intake deadline three times in the week before; the SRR tech never assumes a deck will work until step 9 is signed |
| 18 | **Camera / IMAG feed missing on the confidence monitor or screens** | Camera operator not in position; CCU settings wrong on a freshly-powered desk; tally light wiring fault; lens cap on | V1 cuts to a pre-built "Camera warming up" hold card if available. SM calls camera op by name; op confirms position and CCU. Show proceeds on deck only if IMAG is not the deliverable | Pre-show camera check at every position with the actual lens in place; tally test; CCU scene file stored on the desk; a dedicated camera op for any session where IMAG is being recorded |
| 19 | **Cue light fails / shows wrong color** | Cable pull at the lectern; controller firmware glitch; LED segment burned out | SM switches to on-screen timer overlay on the confidence monitor (no hardware dependency — see 5.2); verbal countdown on IFB to the host as the final fallback | Test cue light at gear check with all three colors; tape the cue light cable path; carry a spare SL-31 in the case; brief the speaker on the on-screen timer as the primary cue and the light as secondary |
| 20 | **Stream goes live with the wrong slide on screen** | Encoder captured laptop A's edit view instead of the switcher PGM out; encoder source set to input 1 instead of the switcher's program output | Broadcast engineer cuts the stream to a hold card or paused state; fixes the routing; replays the missed segment as a recorded insert if possible, or acknowledges the gap on stream once live again | The encoder's source must be the **switcher's PGM output**, not a laptop directly; verify at every gear check that what the encoder sees matches what the audience sees; never let the encoder and the PGM be switched independently |

### 6.1 The Two Universal Recoveries

When nothing else is fast enough, these two actions cover the vast majority of live failures on a corporate rig:

1. **Cut to the hold graphic (input 3).** Always one button press, always already-synchronized, never depends on either show laptop. From a hold graphic you have time to diagnose.
2. **Bring house lights up 20% and play walk-in music at 82 dB(A).** Even before the video is back, an audience that can see each other and has audio to listen to reads the situation as "brief transition," not "catastrophe." This buys 30-60 seconds of goodwill that no amount of technical work can buy back later.

A third, for any failure that will take longer than 60 seconds to resolve: **the host walks on, thanks the previous speaker, and the session proceeds on interim content (sizzle reel, hold slide, awards recap VT)** while the crew works in the background. The audience rarely notices the original fault; they always notice the recovery.

### 6.2 Failure-Mode Quick Reference (print and laminate for the show rack)

| Failure | First Action (≤ 1 s) | Second Action (≤ 30 s) | Recovery Owner |
|---------|----------------------|------------------------|----------------|
| Laptop A dead | Cut to In 2 (laptop B) | Restart laptop A in parallel | V1 + G1 |
| Both laptops dead | Cut to In 3 (hold graphic) | Bring up laptop C from rack | V1 + G1 |
| Clicker dead | Use wired mouse on lectern | Replace battery / swap clicker | G1 |
| Wrong aspect ratio | Cut to In 3 | Force 1080p60 on surviving laptop | V1 + G1 |
| Mic feedback | Pull fader 6-10 dB | Ring out new notch; switch to backup | A1 |
| Recording dropout | Confirm encoder input; swap to backup encoder | Repatch audio; verify stream | A2 + broadcast |
| Backup laptop wrong on switch | Cut to In 3 | Wake / re-index laptop B | V1 + G1 |
| Projector dark (single) | Open backup projector shutter | Cut to backup input | V1 |
| Projector dark (stacked pair) | Surviving unit covers at half brightness | Diagnose; LX up 20% if needed | V1 + LX |
| Wireless mic dropout | Mute failed channel, unmute redundant | Deploy spare frequency from WWB7 | A2 |
| PowerPoint on wrong display | Cut to In 3 | Disable Presenter View, restart slideshow | G1 |
| Font substitution on screen | Cut to In 3 | Substitute font or show PDF fallback | G1 |
| Audio missing from stream | Verify encoder audio meter | Repatch from labeled stream bus | A2 |
| House lights wrong | SM calls LX preset by name | LX cues back | LX + SM |
| Switcher freeze | Cover with In 3 hold graphic | Cold reboot switcher (30-45 s) or swap | V1 |
| Speaker with bad file | Present last validated version | Present PDF export | G1 + account lead |
| Cue light dead | Switch to on-screen timer overlay | Use IFB verbal countdown | SM |

---

## 7. Pre-Show Summary Checklist

Run this list at every gear check, every day, before doors. It is the condensed version of everything in §§1-6. If every box is checked, the show will run; if any box is unchecked, the show **will** find that box during the session.

### 7.1 Speaker Ready Room (SRR)

- [ ] Ready room open at least 60 minutes before doors; staffed through the last session
- [ ] All brand fonts installed and license-verified on both PC and Mac preview stations
- [ ] Test projector and test screen powered; 1-pixel checkerboard pattern is sharp
- [ ] Slidewise (or equivalent) installed and licensed on the preview station
- [ ] ffmpeg available for emergency transcode
- [ ] Sign-off sheet template printed, with fields for deck version, click count, video count, font substitutions, speaker initials, time
- [ ] Speaker pack includes the hard 60-minute deadline in writing
- [ ] Intake queue staffed at one tech per 15 speakers per day; minimum two techs on multi-track conferences

### 7.2 Show Laptops (A and B)

- [ ] Identical hardware, OS build, Office build, GPU driver, and font set
- [ ] Windows updates paused 5 weeks; macOS auto-update disabled
- [ ] Power settings: Never sleep, Never screensaver, High performance / `pmset disablesleep 1`
- [ ] Notifications off (Focus Assist / Do Not Disturb)
- [ ] GPU preference for PowerPoint pinned to discrete GPU
- [ ] OneDrive, Teams, Slack, Outlook auto-start disabled
- [ ] Disk not encrypted with a pre-boot PIN nobody has
- [ ] All content on local SSD, never network share or USB stick
- [ ] Local admin password known to G1 and V1
- [ ] Wallpaper set to client hold graphic
- [ ] Hash-verified identical copies of every active deck on both machines
- [ ] Slide show monitor explicitly assigned; Presenter View configured per speaker preference

### 7.3 Video Path

- [ ] Both laptops outputting 1920×1080 @ 60 Hz, RGB Full, Rec.709, SDR (verified in Advanced display settings / SwitchResX)
- [ ] EDID emulators in line, locked to 1080p60 SDR
- [ ] HDCP OFF on switcher and downstream
- [ ] Seamless switcher (V-8HD or equivalent) on the rack, fans clear, firmware current
- [ ] Input 1 = laptop A, Input 2 = laptop B, Input 3 = hold graphic (non-negotiable), Input 4 = VT
- [ ] Hold graphic source tested and ready (mini-PC or switcher still store)
- [ ] PGM / PVW / Multiview all visible at FOH on labeled monitors
- [ ] Confidence monitor powered, <20 ms input lag, on the switcher's AUX output
- [ ] Backup projector powered, lamp warm, shutter closed, converged with primary
- [ ] All cross-room cables pre-tested, labeled both ends, one spare of every run already in the floor
- [ ] Projector low-latency mode ON
- [ ] Audio de-embed point identified; audio gain-matched on both laptops

### 7.4 Clicker

- [ ] PerfectCue base powered, both USB outputs connected to laptop A and B
- [ ] PerfectCue transmitter battery fresh (voltage logged on gear check sheet)
- [ ] Spare transmitter on the lectern shelf
- [ ] Wired USB mouse or numeric keypad at the lectern, mapped to Page Down, tested
- [ ] Receivers on USB extensions, in open air, not buried behind the laptop

### 7.5 Audio

- [ ] Lectern gooseneck gain-set, HPF at 100 Hz, presence at 3 kHz, ring-out complete, 6 dB feedback margin
- [ ] Handheld backup on the shelf, gain-set, faded down, phantom-free, ready to push up in <1 s
- [ ] All wireless frequencies coordinated in WWB7 with written vendor RF agreement
- [ ] Spare frequency assigned per group, deployed to receivers over the network
- [ ] Transmitter batteries fresh on every pack (voltage logged), spares in the case
- [ ] Antenna placement: 2.5-3 m high, line of sight to stage, 1 m apart for diversity, not behind LED walls
- [ ] WWB7 monitoring continuously on the audio laptop for the entire show
- [ ] Walk test done in the configured room; antenna repositioned for any channel below −85 dBm
- [ ] Panel mics all in automix group X; depth −15 dB; moderator weighted +4 dB
- [ ] Speech at 72-78 dB(A) at FOH; walk-in at 82-86 dB(A); STIPA ≥ 0.62 at the worst seat

### 7.6 Comms and Cue

- [ ] Comms check completed by every position answering aloud (see 5.4 script)
- [ ] DSAN Limitimer PRO-2000 (or equivalent) running; timer layered onto confidence monitor from the first second of every talk
- [ ] Cue light tested in all three colors, tape-path secure
- [ ] IFB to host and moderator tested, fresh battery
- [ ] Cue sheet printed, in a binder, with a pencil, at the SM position
- [ ] Escalation ladder briefed in the production meeting, in writing, including authority to cut off a senior executive
- [ ] SM script for the verbal pre-show checklist in hand

### 7.7 Recording / Stream

- [ ] Encoder source = switcher PGM output (never a laptop directly)
- [ ] Encoder confidence monitor shows correct content
- [ ] Stream mix bus labeled, physically labeled at the patch bay, verified at gear check
- [ ] Audio on the recording confirmed at every gear check and at the top of every break
- [ ] Dedicated uplink provisioned (separate SSID or wired), bandwidth committed
- [ ] Backup encoder racked, pre-configured, ready to swap
- [ ] Encoder in rack with 100 mm clearance and a quiet fan; intake clear

### 7.8 Failover Verification

- [ ] Failover drill run on every show day before doors (2.7); time recorded
- [ ] Drill time under 3.0 s; re-drilled if not
- [ ] Drill covered: HDMI pull from laptop A, force-quit PowerPoint on A, Windows-lock A
- [ ] Laptop B re-confirmed at the same slide index after each drill
- [ ] Hold graphic (input 3) tested as a one-button recovery
- [ ] Post-show report template ready; will be filled out the same day

### 7.9 The Last-Five-Minutes List (run by SM, every show)

- [ ] "Comms check, all positions" — every position answers by name
- [ ] A1: RF status, lectern and handheld, automix group active
- [ ] G1: laptops A and B on the right deck, right slide, hash verified, click count logged, clicker dual-output confirmed
- [ ] V1: switcher inputs assigned, hold graphic armed, HDCP off, failover drill time
- [ ] V1: projectors both on, converged, backup shuttered
- [ ] LX: presets loaded in order
- [ ] PW: speaker in the wing, mic'd, briefed on cue lights
- [ ] SRR: all current decks validated, deployed, signed off
- [ ] SM: standby cue 1

When every box on §§7.1-7.9 is checked, the show is as safe as process can make it. The remaining risk is the speaker, the content, and the network — and those are the variables the production meeting exists to bound. Anything that survives all nine sections has a real chance of being the boring, on-time, on-budget event the client forgot to thank you for.

<!--/CURSOR-->
