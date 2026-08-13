# Technical Rider Specification — Master Template & Reference

A technical rider is a **contract annex**, not a wish list. Every line in it is either a *requirement* (the show does not happen without it) or a *request* (the first thing cut when the budget lands). Riders that fail to mark which is which are the root cause of most load-in arguments.

This document is two things:

1. **Sections 1-11** — the master tables with the exact columns to use, plus the engineering rules and formulas behind each one.
2. **Appendices A-C** — three complete, filled-in riders to copy and edit: corporate general session (16 ch, 2 projectors), rock band (32 ch, full PA, IEM, LED wall), and multi-track conference (24 ch, 3 breakouts, streaming).

## Conventions used throughout

| Marker | Meaning |
|--------|---------|
| **[R]** | Requirement — contractual, no substitution without written approval |
| **[P]** | Preferred — substitution allowed if approved by T-14 days |
| **[A]** | Advance — must be settled on the tech advance call, not on the day |
| *or equivalent* | Substitution permitted. Equivalent means same class, not same price |
| **BY** | Provided by: `PROD` production, `VEN` venue, `ART` artist, `RENT` sub-rental |
| `T-n` | Days (or hours, where stated) before the first performance |

## Document control block

Put this at the top of every rider you issue.

| Field | Value |
|-------|-------|
| Event / Artist | |
| Venue & city | |
| Show date(s) | |
| Rider revision | `v___` |
| Revision date | |
| Issued by (name / role) | |
| Production contact (24 h mobile) | |
| Advance deadline | T-21 days |
| Final revision lock | T-7 days |
| Supersedes | All prior revisions |

> **Rev discipline:** one rider, one revision number, one owner. A venue holding three PDFs with the same filename will build the wrong show. Increment the rev on every change and restate the supersedes line.

---
## 1. Stage Map

Issue the stage plot in **two forms**. A scaled drawing (Vectorworks, AutoCAD, or Capture — PDF at 1:50 metric or 1/4" = 1'-0" imperial) is the legal reference. An ASCII or plain-table version travels in email bodies, WhatsApp threads, and printed run sheets where the PDF will not, and it is the version the deck crew actually reads at 07:00.

### 1.1 Required annotations

Anything not on this list gets built wrong at least once per tour.

| Annotation | Why it matters |
|------------|----------------|
| Deck dimensions, downstage edge to upstage wall | Sets every other measurement; drives PA trim and sightlines |
| Stage height above house floor | Determines front-fill need and barricade-to-edge distance |
| Centre line (CL) and plaster line marked | Every position is dimensioned from these two datums, nothing else |
| Riser positions, sizes, heights | Riser height changes mic stand choice and monitor angle |
| Wedge positions with mix numbers | Prevents a wedge landing on the wrong send |
| DI / sub-snake drop-box positions | Cable lengths are ordered from this |
| Power drop positions with phase | Backline on the same phase as audio is the classic hum source |
| PA hang positions and exclusion zones | Rigger needs these before the truss goes up |
| FOH mix position with footprint | Reclaiming sold seats on the day is a losing fight |
| Backline items, labelled and oriented | Amp facing upstage vs. downstage changes the mic plot |
| Truss and motor points with trim heights | Cross-checks against §8 |
| Sightline limits and camera positions | Camera in the wrong place means a re-hang |

**FOH position rule [R]:** on centre line, between 2/3 and 3/4 of the room depth from the downstage edge, never under a balcony overhang, never in a side alcove. Minimum footprint **3.0 m wide × 2.4 m deep (10 ft × 8 ft)** on a level floor for a full band show; **2.4 m × 1.8 m** for corporate. Under a balcony the HF is shadowed and the low end sums, so the mix will not translate to the room — this is a technical requirement, not a preference.

### 1.2 ASCII stage map template

Copy this block and edit the dimensions and labels. Keep the datum markers.

```
                          UPSTAGE / BACK WALL
  <-------------------------- 14.0 m ------------------------->
  +==========================================================+
  |                                                          |
  |   [ LED WALL / CYC   10.0 m W x 5.5 m H, upstage 0.6 m ]  |   ^
  |                                                          |   |
  |        +--------------+          +--------------+        |   |
  |        | DRUM RISER   |          | KEYS RISER   |        |   |
  |        | 2.4x2.4x0.4m |          | 2.4x1.8x0.2m |        |  10.0 m
  |        |   M5  M6     |          |     M4       |        |  (deck
  |        +--------------+          +--------------+        |  depth)
  |                                                          |   |
  |   [GTR AMP]                                  [BASS RIG]  |   |
  |     M7 >                                        < M8     |   |
  |                                                          |   |
  |          o M2            o M1            o M3            |   |
  |         SL VOX          LEAD VOX        SR VOX           |   |
  |                                                          |   v
  +==========================================================+
        ^                     ^                     ^
     [SUB L]              PLASTER LINE            [SUB R]
                          & CENTRE LINE (CL)
                                 |
   (PA L hang)                    |                (PA R hang)
                                 |
                    <---- 18.0 m to FOH ---->
                                 |
                        +--------+--------+
                        |   FOH MIX POS   |
                        |  3.0 m x 2.4 m  |
                        +-----------------+
                             HOUSE / FRONT
```

Legend: `o` = vocal mic position, `M#` = monitor mix number, `>`/`<` = amp facing direction.

### 1.3 Tabular stage map (dimensioned positions)

Use this when the ASCII art will not survive the transport, and as the numeric source of truth for the deck crew. All positions are `X` = metres from centre line (negative = stage left / house right), `Y` = metres upstage of plaster line.

| Item | X (m) | Y (m) | Size / height | Orientation | Notes |
|------|-------|-------|---------------|-------------|-------|
| Lead vocal | 0.0 | 1.2 | — | Faces house | Tall boom, cable slack 3 m |
| SL vocal | -2.4 | 1.5 | — | Faces house | |
| SR vocal | +2.4 | 1.5 | — | Faces house | |
| Drum riser | 0.0 | 6.5 | 2.4 × 2.4 × 0.4 m | Faces house | Carpet + 2× drop box |
| Keys riser | +3.6 | 6.0 | 2.4 × 1.8 × 0.2 m | Faces house | Power on Phase B |
| Guitar amp | -4.2 | 5.0 | — | Faces upstage | Mic'd, off-axis to vocals |
| Bass rig | +4.8 | 5.5 | — | Faces upstage | DI + mic |
| LED wall | 0.0 | 9.4 | 10.0 × 5.5 m | Faces house | 0.6 m from back wall |
| PA hang L | -6.5 | -1.0 | Trim 7.5 m to grid | 4° in | Exclusion 2 m radius |
| PA hang R | +6.5 | -1.0 | Trim 7.5 m to grid | 4° in | Exclusion 2 m radius |
| Sub array L | -5.0 | 0.2 | Ground stacked | Faces house | |
| Sub array R | +5.0 | 0.2 | Ground stacked | Faces house | |
| FOH mix | 0.0 | -18.0 | 3.0 × 2.4 m | Faces stage | Level floor, 2× 20 A |

---
## 2. Input List

Column definitions, fixed for every rider you issue:

| Column | Content rule |
|--------|--------------|
| `Ch#` | Console input number. Never renumber mid-tour; add at the end |
| `Source` | The instrument or person, not the mic |
| `Mic Model` | Exact model, or model *or equivalent*. `DI` if direct |
| `Stand` | `TB` tall boom, `SB` short boom, `ST` straight, `DT` desk, `CL` clip/clamp, `—` none |
| `Phantom` | `Y` / `N`. Condensers and active DIs `Y`, dynamics `N` |
| `Insert` | Hardware or plug-in intended on that channel. `—` if none |
| `Notes` | Polarity, pad, HPF, sub-snake number, anything that stops a question at soundcheck |

**Stand count discipline:** total the stand column and put the number in the summary. `TB × 9, SB × 7, ST × 2, CL × 6` ordered as a count is unambiguous; "assorted stands" is how you end up with six tall booms for a drum kit.

### 2.1 Band — 32 channels

Standard 5-piece rock/pop configuration with keys and a spare pair. This is the reference list; Appendix B is the filled show version.

| Ch# | Source | Mic Model | Stand | Phantom | Insert | Notes |
|-----|--------|-----------|-------|---------|--------|-------|
| 1 | Kick in | Shure Beta 91A | — | Y | Gate + comp | Inside shell on pillow |
| 2 | Kick out | Audix D6 *or eq* | SB | N | Comp | 100 mm off port, polarity check vs Ch1 |
| 3 | Snare top | Shure SM57 | SB | N | Gate + comp | Rim-mount clip acceptable |
| 4 | Snare btm | Shure SM57 | SB | N | Gate | **Polarity invert** |
| 5 | Hi-hat | AKG C451 B *or eq* | SB | Y | HPF 200 Hz | Edge of bell, away from snare |
| 6 | Rack tom | Sennheiser e904 | CL | N | Gate + comp | |
| 7 | Floor tom 1 | Sennheiser e904 | CL | N | Gate + comp | |
| 8 | Floor tom 2 | Sennheiser e904 | CL | N | Gate + comp | Omit if 3-tom kit |
| 9 | OH L | Neumann KM 184 *or eq* | TB | Y | Comp | Spaced pair, 1.2 m above kit |
| 10 | OH R | Neumann KM 184 *or eq* | TB | Y | Comp | Match cable length to Ch9 |
| 11 | Ride | AKG C451 B *or eq* | SB | Y | HPF 250 Hz | |
| 12 | Drum sub mic | Shure Beta 52A | SB | N | — | Optional, FOH discretion |
| 13 | Bass DI | Radial J48 | — | Y | Comp | Pre-amp DI out from Ampeg SVT-4PRO |
| 14 | Bass mic | Sennheiser e902 *or eq* | SB | N | Comp | 8×10 cab, upper-left driver |
| 15 | Gtr SL 1 | Sennheiser MD 421-II | SB | N | — | 25 mm off grille, 40 mm off dust cap |
| 16 | Gtr SL 2 | Royer R-121 *or eq* | SB | N | — | Ribbon, blend with Ch15 |
| 17 | Gtr SR 1 | Shure SM57 | SB | N | — | |
| 18 | Gtr SR 2 | Audix i5 *or eq* | SB | N | — | |
| 19 | Acoustic gtr | Radial JDI | — | N | Comp + notch | Passive DI, piezo source |
| 20 | Keys L | Radial ProD2 (L) | — | N | Comp | Nord Stage 4 main out |
| 21 | Keys R | Radial ProD2 (R) | — | N | Comp | Linked to Ch20 |
| 22 | Keys aux L | Radial ProD2 (L) | — | N | — | Second board / laptop |
| 23 | Keys aux R | Radial ProD2 (R) | — | N | — | |
| 24 | Playback L | Radial ProD2 (L) | — | N | — | Timecode-locked, **do not fade** |
| 25 | Playback R | Radial ProD2 (R) | — | N | — | |
| 26 | Click | Radial ProD2 | — | N | — | **To monitors only, hard-muted at FOH** |
| 27 | Lead vox | Shure Axient AD2/KSM9HS | TB | N | Comp + DeEsser | RF, handheld, hypercardioid |
| 28 | Lead vox spare | Shure Axient AD2/KSM9HS | TB | N | Comp + DeEsser | Same channel strip as Ch27 |
| 29 | SL vox | Shure Beta 58A | TB | N | Comp | Wired |
| 30 | SR vox | Shure Beta 58A | TB | N | Comp | Wired |
| 31 | Talkback / MD | Shure SM58 | TB | N | HPF 150 Hz | Stage left, **not** in FOH mains |
| 32 | Spare | — | ST | — | — | Patched to sub-snake 1, ch 8 |

**Stand summary:** `TB × 5, SB × 12, ST × 1, CL × 3` plus 3 × rim clip. Sub-snakes: SL 12 ch, SR 12 ch, drums 12 ch.

### 2.2 Corporate — 16 channels

Two-panel-plus-lectern general session, the configuration that covers roughly 80% of corporate work.

| Ch# | Source | Mic Model | Stand | Phantom | Insert | Notes |
|-----|--------|-----------|-------|---------|--------|-------|
| 1 | Lectern L | Shure MX418/C 18" | DT | Y | Comp + gate | Gooseneck, on lectern shelf |
| 2 | Lectern R | Shure MX418/C 18" | DT | Y | Comp + gate | Redundant pair, one fader |
| 3 | Handheld 1 | Shure ULXD2/SM58 | TB | N | Comp + DeEsser | Q&A roamer, house left |
| 4 | Handheld 2 | Shure ULXD2/SM58 | TB | N | Comp + DeEsser | Q&A roamer, house right |
| 5 | Lav 1 | Shure ULXD1 + DPA 4066 | — | — | Comp + DeEsser | Presenter A, headworn |
| 6 | Lav 2 | Shure ULXD1 + DPA 6060 | — | — | Comp + DeEsser | Presenter B, subminiature |
| 7 | Lav 3 | Shure ULXD1 + DPA 6060 | — | — | Comp + DeEsser | Presenter C |
| 8 | Lav 4 | Shure ULXD1 + DPA 6060 | — | — | Comp + DeEsser | Spare, charged and cued |
| 9 | Panel table 1 | Shure MX392/C | DT | Y | Gate | Boundary, 2 seats per mic |
| 10 | Panel table 2 | Shure MX392/C | DT | Y | Gate | |
| 11 | Playback L | Radial ProAV2 (L) | — | N | — | From show laptop, 3.5 mm |
| 12 | Playback R | Radial ProAV2 (R) | — | N | — | |
| 13 | Video / VTR L | Radial ProD2 (L) | — | N | — | Balanced from switcher |
| 14 | Video / VTR R | Radial ProD2 (R) | — | N | — | |
| 15 | Remote caller | Radial ProAV1 | — | N | Comp + AGC | Teams/Zoom return, **mix-minus** |
| 16 | Walk-in music | Radial ProAV2 | — | N | — | Dedicated device, not the show laptop |

**Mix-minus [R]:** Ch15 must be fed a bus that excludes itself. Without it the remote caller hears their own voice delayed by the platform round trip and stops talking. This is the single most common corporate audio failure.

**Stand summary:** `DT × 4, TB × 2`. Wireless: 2 handheld + 4 bodypack = 6 RF channels, coordinated per §2.3.

### 2.3 RF coordination rule

| Item | Requirement |
|------|-------------|
| Coordination tool | Shure Wireless Workbench 6, or Sennheiser WSM. Scan **on site**, not from a saved show file |
| Scan timing | At load-in, and again after all other vendors have powered up |
| Band | Post-repack UHF: **470-608 MHz** and **614-616 MHz** (US). Avoid 608-614 MHz (radio astronomy) |
| Duplex gap | 653-663 MHz is licensed-only in the US; do not plan a show around it |
| Intermod | Third-order calculated clear for all active channels |
| Antennas | Paddle or helical on stands, 2 m minimum above deck, 3 m from LED wall |
| Spares | 1 spare RF channel per 6 active, fully coordinated and battery-fresh |
| Batteries | Fresh or freshly charged at every session boundary. Log the swap |

LED walls and video processors are broadband noise sources. Keep receive antennas out of the wall's near field and off the same power phase where practical.

---
## 3. Output List

The output list is where shows are lost. An input patched wrong is audible at soundcheck; an output patched wrong is silent until the moment it is needed — the record feed, the overflow room, the broadcast split.

| Out# | Destination | Signal Type | Cable | Notes |
|------|-------------|-------------|-------|-------|
| 1 | PA Main L | Dante / AES67 | Cat6A shielded, primary | Redundant on Out 3 |
| 2 | PA Main R | Dante / AES67 | Cat6A shielded, primary | Redundant on Out 4 |
| 3 | PA Main L (secondary) | Dante secondary | Cat6A shielded, secondary | Physically separate path |
| 4 | PA Main R (secondary) | Dante secondary | Cat6A shielded, secondary | |
| 5 | Sub aux-fed L | Dante / AES67 | Cat6A shielded | Aux-fed, not matrixed from L/R |
| 6 | Sub aux-fed R | Dante / AES67 | Cat6A shielded | |
| 7 | Front fill C | Dante / AES67 | Cat6A shielded | Delay +4.2 ms, -6 dB |
| 8 | Delay ring L | Dante / AES67 | Cat6A shielded | Delay +38 ms (13 m) |
| 9 | Delay ring R | Dante / AES67 | Cat6A shielded | |
| 10 | Sidefill SL | Analogue line | XLR 3-pin, 30 m | +4 dBu nominal |
| 11 | Sidefill SR | Analogue line | XLR 3-pin, 30 m | |
| 12 | Broadcast / stream L | Analogue line, **isolated** | XLR via Jensen ISO-MAX | Transformer isolated, no ground path |
| 13 | Broadcast / stream R | Analogue line, **isolated** | XLR via Jensen ISO-MAX | |
| 14 | Multitrack record 1-32 | Dante virtual soundcard | Cat6A to record rig | 48 kHz / 24-bit, pre-fader post-gain |
| 15 | Press / mult box | Analogue mic-level | 8× XLR passive mult | Transformer split, 1 per outlet |
| 16 | Overflow / lobby | Analogue line | XLR to house rack | Level-limited, -10 dB from mains |
| 17 | Hearing assist | Analogue line | XLR to induction loop | **ADA required**, verify before doors |
| 18 | Video switcher return | Analogue line | XLR to switcher aud in | Embedded to SDI programme |
| 19 | Confidence / green room | Analogue line | XLR | Mains-derived, includes talkback |
| 20 | Show relay / paging | Analogue line | XLR to house paging | Dressing rooms and corridors |

**Rules that go in the rider body, not just the table:**

- **Aux-fed subs [P]** — subs on their own aux, not matrixed off L/R. Keeps guitars and vocals out of the sub array and buys 3-6 dB of usable headroom in the 60-120 Hz band.
- **Isolated broadcast split [R]** — transformer isolation on Out 12/13. A galvanic connection between the console and a broadcast truck is a guaranteed ground loop and a real shock hazard between two separately-earthed systems.
- **Hearing assistance [R]** — ADA (US) and equivalent statutes elsewhere are legal obligations, not rider items. Verify the loop or FM system passes audio before doors, every day.
- **Record feed is pre-fader [R]** — post-gain, pre-fader, pre-EQ. A FOH fader move must not damage the archive.

---

## 4. Monitor Requirements

| Mix# | Performer | Type (IEM/Wedge) | Model | Notes |
|------|-----------|------------------|-------|-------|
| 1 | Lead vocal | IEM stereo | Shure PSM1000 + SE846 | Ambient mic pair in mix, -18 dB |
| 2 | SL guitar / vox | IEM stereo | Shure PSM1000 + SE425 | Own vox +3 dB over house artist ref |
| 3 | SR guitar / vox | IEM stereo | Shure PSM1000 + SE425 | |
| 4 | Keys | IEM stereo | Shure PSM1000 + SE425 | Click hard left, cue right |
| 5 | Drums | IEM stereo | Shure PSM1000 + SE846 | + drum sub, see Mix 12 |
| 6 | Drum sub / thumper | Tactile | ButtKicker BK-LFE | Kick + floor tom only, 30-80 Hz |
| 7 | Bass | Wedge | d&b audiotechnik M4 | Single, stage right of rig |
| 8 | SL spot wedge | Wedge | d&b audiotechnik M4 | Backup for Mix 2 IEM failure |
| 9 | SR spot wedge | Wedge | d&b audiotechnik M4 | Backup for Mix 3 |
| 10 | Sidefill SL | Wedge / point source | Meyer Sound UPJ-1P | Ground stacked on sub |
| 11 | Sidefill SR | Wedge / point source | Meyer Sound UPJ-1P | |
| 12 | Guest / support act | Wedge ×2 | d&b audiotechnik M4 | Shared mix, downstage centre |
| 13 | Ambient mic feed | Source | 2× DPA 4560 or Audix M1250B | Downstage edge, into IEM mixes |
| 14 | Monitor engineer wedge | Wedge | d&b audiotechnik M4 | At monitor world |
| 15 | Shout / talkback | Mix | — | MD to all IEMs, latching key |
| 16 | Spare IEM pack | IEM stereo | Shure PSM1000 + SE425 | Coordinated, charged, on standby |

### 4.1 IEM requirements

| Item | Requirement | Reason |
|------|-------------|--------|
| Transmitters | 1 per stereo mix, **no shared packs** | A shared pack means two performers cannot have different mixes |
| Antenna distribution | Shure PA421B (4-way) or PA821B (8-way) combiner | Multiple whip antennas at close spacing cause IMD and dropouts |
| Antenna | Helical or paddle, 2 m above deck, line of sight to performers | Body-block and LED wall are the two dropout causes |
| Ambient mics [R] | Stereo pair, downstage edge, into every IEM mix | Without it performers are acoustically isolated and lose the room |
| Moulds | Artist provides custom moulds; production provides universal-fit spares | |
| Batteries | Fresh at every session boundary, logged | |
| Limiter | Hard limiter on every IEM mix, set at the console | Hearing protection. A feedback burst into moulds is an injury |

**Monitor console [R]:** dedicated monitor console at monitor world, minimum 16 mix buses, 32 inputs, with its own engineer. Sharing FOH for a full band show means neither mix gets attention during the set.

**Wedge coverage note:** the d&b M4 is a passive 2-way wedge driven from a D20 or 10D amplifier; specify the amplifier channel count in §7 power, since the amps draw the current, not the boxes. Meyer wedges (MJF-210) are self-powered and draw at the box — the two are not interchangeable in the power calculation.

---
## 5. LED / Video Specs

| Component | Spec | Qty | Notes |
|-----------|------|-----|-------|
| LED panel — main wall | ROE Visual Black Pearl BP2, 2.84 mm pitch, 500 × 500 mm, indoor | 220 | 20 W × 11 H = 10.0 m × 5.5 m |
| LED panel — spares | Same batch / same bin | 12 | 5% spare rate [R], hot spares on site |
| Wall resolution | 3520 × 1936 px = **6.81 Mpx** | — | 176 × 176 px per panel |
| LED processor | Brompton Tessera SX40 | 1 | 8.8 Mpx @ 60 Hz capacity, 4× 10 GbE |
| LED processor — backup | Brompton Tessera SX40 | 1 | Hot spare, pre-loaded, same firmware |
| Data distribution | Brompton XD 10G data distribution unit | 2 | Fibre to stage, redundant loop |
| Media server | disguise gx 2c | 1 | Primary, 4× 4K outputs |
| Media server — backup | disguise gx 2c | 1 | Understudy, frame-locked to primary |
| Playback / VJ | Resolume Arena 7 on Mac Studio M2 Ultra | 1 | Secondary content source |
| Switcher | Ross Carbonite Ultra 60 | 1 | 2 M/E, 24 inputs, 12 G |
| Switcher — corporate alt | Blackmagic ATEM 4 M/E Constellation 4K | 1 | Where budget precludes Carbonite |
| Projector | Panasonic PT-RZ21K, 20 000 lm, laser, WUXGA | 2 | Blend or dual-screen, see §5.2 |
| Projector lens | Panasonic ET-DLE060 (0.6:1) or ET-DLE105 (1.3-1.7:1) | 2 | Selected from throw calc |
| Screen | Da-Lite Fast-Fold Deluxe, 4.9 m × 2.7 m (16:9) | 2 | Rear-projection surface + dress kit |
| Camera | Sony HXC-FB80 with 20× box lens | 3 | FOH long, SL, SR |
| Camera — handheld | Sony PXW-Z280 | 1 | Roaming, wireless SDI |
| Camera control | Sony RCP-1500 remote control panels | 3 | At V1 position, shading |
| Multiview / monitoring | 2× 32" 4K UHD, 1× 55" programme | 3 | V1 and show caller |
| Confidence monitor | 55" UHD on stand, downstage | 2 | Mirrored programme, no OSD |
| Timer / clock | Stage Timer or DSAN PerfectCue Micro | 1 | Presenter countdown, wireless |
| Streaming encoder | Blackmagic Web Presenter 4K | 1 | 1080p59.94, 10 Mbps H.264 |
| Streaming — backup path | LiveU Solo PRO, bonded cellular | 1 | Auto-failover, 2× carrier SIM |
| Record | Blackmagic HyperDeck Studio 4K Pro | 2 | ProRes 422 HQ, A/B redundant |
| Genlock / reference | Blackmagic Sync Generator, tri-level 1080p59.94 | 1 | **All devices genlocked [R]** |
| Signal distribution | 12G-SDI on Belden 4794R, fibre over 100 m | — | See cable schedule |

### 5.1 Pixel and processing maths

**Wall pixel count.** BP2 panels are 500 × 500 mm at 2.84 mm pitch, giving 176 × 176 px per panel.

```
Horizontal:  20 panels x 176 px = 3520 px
Vertical:    11 panels x 176 px = 1936 px
Total:       3520 x 1936        = 6 814 720 px = 6.81 Mpx
Wall area:   10.0 m x 5.5 m     = 55.0 m2
```

**Processor headroom.** One Tessera SX40 carries 8.8 Mpx at 60 Hz.

```
Utilisation = 6.81 / 8.8 = 77.4%
```

Under 80%, so a single SX40 runs the wall with the second as a true hot spare rather than a required second half. Above 80% plan on two processors carrying half the wall each, which changes the backup story completely — you then need three units for redundancy.

**Canvas mapping.** A 3520 × 1936 canvas is not a broadcast raster. Content is authored at native wall resolution and the media server outputs 4× 4K DisplayPort feeds mapped into it. Do **not** let content arrive as 1920 × 1080 and get upscaled 1.83× — text and logos will visibly soften on a 2.84 mm wall at 6 m viewing distance.

**Viewing distance rule of thumb.** Minimum comfortable viewing distance in metres ≈ pixel pitch in mm. A 2.84 mm wall reads clean from about 2.8 m back. Front-row seats at 4 m are fine; a camera at 8 m with a long lens will resolve the pitch, so plan LED-in-shot framing accordingly.

### 5.2 Projection throw and brightness

Screen: Da-Lite Fast-Fold 4.9 m × 2.7 m (16:9), rear projection.

```
Throw distance = image width x throw ratio
ET-DLE060 (0.60:1):  4.9 m x 0.60 = 2.94 m   -> fits a 3.5 m deep RP booth
ET-DLE105 (1.3:1):   4.9 m x 1.30 = 6.37 m   -> needs a 7 m booth, unlikely
```

Choose the 0.6:1 short throw for rear projection in a typical 3.5-4 m booth. Verify booth depth on the advance — this is the number venues get wrong.

**Brightness check.** PT-RZ21K is 20 000 lm. Rear-projection screens transmit roughly 50-60% of incident light; take 55%.

```
Screen area   = 4.9 m x 2.7 m = 13.23 m2 = 142.4 ft2
Effective lm  = 20 000 x 0.55 = 11 000 lm
Illuminance   = 11 000 lm / 142.4 ft2 = 77 fL (foot-lamberts)
```

Target for an event room with stage wash and house light at 30% is **30-50 fL**. At 77 fL there is real headroom, which matters because the number that kills projection is not the projector, it is ambient light landing on the screen. Specify **zero front light within 1.5 m of the screen surface** [R] and get the lighting designer to sign off on the wash edge.

### 5.3 Video requirements as rider text

- **Genlock [R].** Every SDI source, the switcher, both HyperDecks and the media servers reference the same tri-level sync at 1080p59.94 (or 1080p50 in 50 Hz territories). Un-genlocked sources force the switcher to frame-sync, which adds a frame of latency per re-sync and produces visible glitching on cut.
- **Frame rate is a territory decision [A].** Settle 59.94 vs 50 on the advance. Mixed-rate content must be conformed before it arrives, not on the day.
- **Content deadline [R].** All playback content delivered T-48 h, in native canvas resolution, ProRes 422 HQ or DXV3 for Resolume. No H.264 for playback.
- **Redundancy.** Primary and backup media server frame-locked, switching on a clean take, tested at rehearsal not at showtime.

---

## 6. Lighting Specs

| Fixture | Type | Qty | Position | DMX Universe |
|---------|------|-----|----------|--------------|
| Chauvet Professional Rogue R2 Wash | Moving wash, 15× 40 W RGBW, 12-49° zoom | 12 | Mid truss (6), upstage truss (6) | U1 |
| Chauvet Professional Rogue R2 Spot | Moving spot, 260 W LED, 15° | 8 | FOH truss (4), mid truss (4) | U1 |
| Chauvet Professional Rogue R2X Beam | Moving beam, 132 W discharge, 2.5° | 8 | Upstage deck (4), mid truss (4) | U1 |
| Martin MAC Aura XB | Moving wash + aura, 550 W | 10 | Mid truss | U1 |
| Robe BMFL Spot | Followspot, 1700 W | 2 | FOH followspot chairs | U2 |
| Chauvet COLORdash Par-Quad 18 | LED par, RGBW | 16 | Upstage floor uplight (8), truss (8) | U2 |
| Chauvet COLORado Solo Batten 4 | LED batten, RGBW zoom | 8 | Upstage deck, cyc / wall wash | U2 |
| Chauvet STRIKE 4 | Blinder / audience, 4× 100 W warm white | 8 | FOH and mid truss, house-facing | U2 |
| ETC Source Four LED Series 3 Lustr | Ellipsoidal, 26° | 12 | FOH truss, key and specials | U2 |
| Chauvet Ovation E-260WW | Ellipsoidal, warm white 3000 K | 8 | Lectern key, podium specials | U2 |
| Chauvet Amhaze Whisper | Haze, water-based, low noise | 2 | SL and SR upstage | U3 |
| Look Solutions Unique 2.1 | Hazer, alt spec | 2 | Substitution for Amhaze | U3 |
| Antari W-715 | Fan, haze distribution | 2 | Upstage corners | U3 |
| MDG theONE | Fog / haze, CO2-driven | 1 | Upstage centre, effects only | U3 |
| Console | MA Lighting grandMA3 full-size | 1 | FOH lighting position | — |
| Console — backup | MA Lighting grandMA3 light, tracking backup | 1 | Adjacent, session-joined | — |
| DMX gateway | Luminex GigaCore 10 + LumiNode 4 | 4 | Stage L, stage R, FOH, dimmer world | U1-U3 |
| Dimming / relay | ETC Sensor3 48× 2.4 kW rack | 1 | Dimmer world SL | U3 |
| Followspot comms | On the lighting intercom ring | 2 | — | — |

### 6.1 Universe allocation and channel count

| Universe | Contents | Channels used | Headroom |
|----------|----------|---------------|----------|
| U1 | All moving lights (R2 Wash, R2 Spot, R2X Beam, MAC Aura XB) | ~430 | 82 ch |
| U2 | Followspots, pars, battens, blinders, ellipsoidals | ~370 | 142 ch |
| U3 | Atmospherics, house light relay, dimmer rack, spares | ~180 | 332 ch |

Rules that belong in the rider:

- **Never fill a universe.** Cap at 85% (435 of 512). The show will grow between the plot and the first preview, and a universe with no room forces a re-address at 02:00.
- **One universe per gateway port [R]** — do not daisy-chain two universes through one node port.
- **Terminate every DMX run [R]** with a 120 Ω terminator at the last fixture. Unterminated lines produce intermittent flicker that reads as a fixture fault and wastes an hour.
- **Data is Cat6A, not DMX, over distance.** Run sACN or Art-Net to a node near the fixtures, then short DMX tails. A 90 m DMX run with 20 fixtures on it is a fault waiting to happen.
- **Haze [A]** — confirm the venue permits water-based haze and that smoke detectors can be isolated by the venue's fire officer. Get this in writing. An unplanned alarm evacuation during a show is a career event.

---
## 7. Power Requirements

A power request that says "adequate clean power" will get you a wall socket behind a curtain. State amps, voltage, phase, connector and position, and show the arithmetic so the venue electrician can check it rather than argue with it.

### 7.1 Formulas

```
SINGLE PHASE
  W    = V x A x PF
  A    = W / (V x PF)
  kVA  = (V x A) / 1000

THREE PHASE (line-to-line voltage, e.g. 208 V wye)
  kVA  = (V_LL x A x 1.732) / 1000
  kW   = kVA x PF
  A    = (kW x 1000) / (V_LL x 1.732 x PF)

PER-LEG METHOD  (the one that matters for entertainment distro)
  A_per_leg = Total_W / (V_LN x 3)
            = Total_W / 360          for a 120/208 V wye system
            = Total_W / 690          for a 230/400 V system

CONTINUOUS LOAD DERATE  (NEC 210.19(A)(1), 210.20(A))
  Usable_continuous_A = Breaker_rating x 0.80
  Required_breaker    = Continuous_A / 0.80

VOLTAGE DROP (copper, K = 12.9; L in feet, CM = circular mils)
  Vd_1ph = (2 x K x I x L) / CM
  Vd_3ph = (1.732 x K x I x L) / CM
  Target: feeder + branch <= 3% total (NEC 210.19(A) informational note)
```

**Nominal voltage, stated correctly.** North American single phase is **120 V nominal**, not 110 V, though it is still written 110 V on older riders and some equipment plates. Service ranges 114-126 V under ANSI C84.1. Three phase is **120/208 V wye** (208 V line-to-line) for most venues and **277/480 V** for large arena services stepped down at a transformer. Europe, most of Asia, Australia: **230 V single / 400 V three phase**. Put the territory's numbers in the rider you actually send.

### 7.2 Usable capacity by circuit rating

| Nameplate | Voltage | Phase | Nameplate kVA | Usable continuous (80%) | Usable continuous kW @ PF 0.95 |
|-----------|---------|-------|---------------|-------------------------|-------------------------------|
| 20 A | 120 V | 1φ | 2.40 | 16 A | 1.82 kW |
| 30 A | 120 V | 1φ | 3.60 | 24 A | 2.74 kW |
| 20 A | 208 V | 1φ | 4.16 | 16 A | 3.16 kW |
| 30 A | 208 V | 3φ | 10.81 | 24 A | 8.21 kW |
| 60 A | 208 V | 3φ | 21.61 | 48 A | 16.42 kW |
| 100 A | 208 V | 3φ | 36.02 | 80 A | 27.37 kW |
| 200 A | 208 V | 3φ | 72.05 | 160 A | 54.75 kW |
| 400 A | 208 V | 3φ | 144.10 | 320 A | 109.50 kW |
| 32 A | 230 V | 1φ | 7.36 | 25.6 A | 5.59 kW |
| 63 A | 400 V | 3φ | 43.64 | 50.4 A | 33.17 kW |
| 125 A | 400 V | 3φ | 86.60 | 100 A | 65.82 kW |

Worked check on the 100 A 3φ row: `kVA = (208 × 100 × 1.732) / 1000 = 36.02 kVA`. At 80% and PF 0.95: `36.02 × 0.80 × 0.95 = 27.37 kW`. Every other row follows the same two steps.

**The 80% rule is not conservatism.** A load drawing current for three hours or more is a continuous load under the NEC, and the breaker must be sized at 125% of it. A show is continuous by definition. Sizing to nameplate means nuisance trips on the second chorus.

### 7.3 Circuit schedule — full production (rock show reference)

| Circuit | Amps | Voltage | Phase | Distro | Load Calc |
|---------|------|---------|-------|--------|-----------|
| **SERVICE** | 400 A | 120/208 V | 3φ wye + N + G | Camlock Series 16 to main distro, SL upstage | Total connected 86.0 kW → 86 000 / 360 = **238.9 A/leg**; 238.9 / 0.80 = 298.6 A req. → 400 A. Utilisation 238.9 / 320 = **74.7%** |
| A-1 Audio PA | 100 A | 120/208 V | 3φ | Motion Labs 100 A → 12× L5-20R at PA hangs | 24× LEOPARD @4.5 A = 108 A; 6× 900-LFC @8 A = 48 A → 156 A + fills 16 A = 172 A ÷ 3 = **57.3 A/leg** (71.6% of 80 A) |
| A-2 Audio control | 30 A | 120/208 V | 3φ | Motion Labs 30 A → 6× L5-20R at FOH + mon world | Consoles 8 A, drive rack 3 A, RF rack 3 A, processing 2 A = 16 A ÷ 3 = **5.3 A/leg**. Isolated ground, tech earth |
| A-3 Stage / backline | 30 A | 120 V | 1φ (Phase B only) | 8× L5-20R across deck, 2 per drop box | Guitar amps 2× 6 A, bass 8 A, keys 4 A, pedals 2 A = **24 A** = 2.88 kW (80% of 30 A) |
| L-1 Lighting main | 200 A | 120/208 V | 3φ wye | Motion Labs 200 A → 6× Socapex 19-pin + 12× L6-30 | Connected 32.0 kW → 32 000 / 360 = **88.9 A/leg**; 88.9 / 0.80 = 111 A req. → 200 A. Utilisation **55.6%** |
| L-2 Followspot | 20 A | 120 V | 1φ | 2× L5-20R at spot chairs | 2× BMFL Spot @ 1900 W = 3800 W / 120 = **31.7 A** → split across 2× 20 A circuits, 15.8 A each (79%) |
| V-1 LED wall | 100 A | 120/208 V | 3φ wye | Motion Labs 100 A → 8× L6-30 to wall PSU loops | 55 m² × 350 W/m² max = 19 250 W → 19 250 / 360 = **53.5 A/leg**; /0.80 = 66.8 A req. → 100 A. Utilisation **66.8%** |
| V-2 Video control | 60 A | 120/208 V | 3φ | Motion Labs 60 A → 10× L5-20R at V1, servers, racks | Servers 2000 W, switcher/racks 2000 W, cameras 600 W, decks 300 W = 4900 W → **13.6 A/leg** (28% of 48 A) |
| V-3 Projection | 30 A | 208 V | 1φ (2 legs) | 2× L6-30R at projector positions | 2× PT-RZ21K @ 2100 W = 4200 W / 208 = **20.2 A** → 1 projector per 30 A circuit, 10.1 A each |
| C-1 Comms / network | 20 A | 120 V | 1φ | 4× L5-20R, UPS-backed | Intercom base 2 A, switches 3 A, wireless BP charging 2 A = **7 A** |
| U-1 UPS critical | 20 A | 120 V | 1φ | APC SMT3000RM2U at FOH, 2700 W / 2880 VA | Console 4 A, drive rack 3 A, primary media server 8 A = **15 A** = 75% of 20 A. Runtime at 1800 W ≈ 7 min |
| S-1 Shore / house | 20 A | 120 V | 1φ | House GPO, work light and tools only | **Not for show equipment.** Tools, chargers, vacuum |

**Phase balance check.** With A-1, L-1 and V-1 all as three-phase loads, each leg carries its own share automatically. The single-phase circuits (A-3, L-2, V-3, C-1, U-1) must be deliberately spread:

```
Leg A:  A-3 stage (24 A) + C-1 comms (7 A)              = 31 A
Leg B:  L-2 followspot (15.8 A) + U-1 UPS (15 A)        = 30.8 A
Leg C:  V-3 projection leg 1 (10.1 A) + spare (20 A)    = 30.1 A
Imbalance = (31 - 30.1) / 31 = 2.9%   -> target is under 10%
```

Neutral current on a wye system rises with imbalance and with third-harmonic content from switch-mode supplies (every LED fixture and every Class-D amplifier). Specify a **full-size or oversized neutral [R]** on all feeders. A half-size neutral on a modern LED rig is a fire risk, not a theoretical concern.

### 7.4 Worked total for the rock show

```
SUBSYSTEM LOADS (connected, at 120 V per-leg basis)
  Audio  PA + control + backline .......  22.6 kW
  LED wall (max, 350 W/m2) .............  19.3 kW
  Lighting (connected) .................  32.0 kW
  Video (control + projection) .........   9.1 kW
  Comms, network, misc .................   3.0 kW
                                         --------
  TOTAL CONNECTED ......................  86.0 kW

PER-LEG CURRENT
  86 000 W / 360 = 238.9 A per leg

REQUIRED BREAKER
  238.9 / 0.80 = 298.6 A  ->  400 A three-phase service [R]

SERVICE kVA
  (208 x 238.9 x 1.732) / 1000 = 86.1 kVA

REALISTIC RUNNING LOAD (diversity 0.70 applied to lighting and LED only)
  Audio 22.6 + Comms 3.0 + Video 9.1 = 34.7 kW at full
  (Lighting 32.0 + LED 19.3) x 0.70  = 35.9 kW
  Running total                       = 70.6 kW  ->  196 A per leg (61% of 320 A)
```

**Why size to connected load, not diversified load.** Diversity says the lighting rig never sits at 100% because a look does not use every fixture. That is true on average and false at the exact moment the LD builds a full-white blinder cue on the last chorus. Size the service to connected load; use the diversified figure only for generator fuel and heat planning.

### 7.5 Connectors

| Connector | Rating | Typical use |
|-----------|--------|-------------|
| NEMA 5-15 | 15 A 125 V | Domestic. Avoid for show gear |
| NEMA L5-20 (twist) | 20 A 125 V | Standard show single-phase outlet [R] |
| NEMA L6-30 (twist) | 30 A 250 V | LED wall PSU, projectors, 208 V single phase |
| NEMA L21-30 | 30 A 120/208 V 3φ | Small three-phase drops, LED processors |
| CS6365 (California) | 50 A 125/250 V | Sub-distro feeds, motor controllers |
| Socapex 19-pin | 6 × 20 A circuits | Lighting truss multicable [R] |
| Camlock Series 16 (E1016) | 400 A per pole | Main service tie-in, 5 wire L1/L2/L3/N/G |
| Powerlock / Litton | 400-660 A | European and touring main tie-in |
| powerCON TRUE1 TOP | 20 A 250 V | Self-powered speakers, LED fixtures, daisy-chain |
| IEC 60309 (blue) 32 A | 32 A 230 V 1φ | European single-phase drops |
| IEC 60309 (red) 63 A | 63 A 400 V 3φ | European three-phase drops |

### 7.6 Grounding, protection and generator

| Item | Requirement |
|------|-------------|
| Grounding | Single-point technical earth at the main distro. **No neutral-to-ground bond downstream** of the service disconnect [R] |
| Isolated ground | Audio control (A-2) on an isolated-ground circuit, bonded only at the service |
| GFCI / RCD | Required on all outdoor, wet-location and audience-accessible circuits. **Never** on a life-safety or show-critical feed without a plan for what a trip costs |
| Feeder inspection | Every cable visually inspected and tested before energising. Damaged jacket = out of service, tagged |
| Cable protection | Yellow Jacket or Guard Dog ramps on every crossing. No cable across a fire exit path [R] |
| Tie-in | **Licensed electrician only** [R], with venue authorisation in writing. Lock-out / tag-out during connection |
| Generator (if no shore) | 150 kVA, 120/208 V 3φ, 400 A, sound-attenuated. **THD < 5%**, voltage regulation ±1%, frequency ±0.25 Hz |
| Genset loading | 86.1 kVA on 150 kVA = **57%** loaded. Target 50-80% — under 30% causes wet stacking, over 80% leaves no transient headroom |
| Generator redundancy | Second unit with auto-transfer for broadcast or ticketed shows |
| Fuel | Minimum show duration + 4 hours reserve. Refuel only with the load transferred |
| Voltage drop, stage feeder | 2/0 AWG copper, 3φ, 200 A, 45 m (147 ft): `Vd = (1.732 × 12.9 × 200 × 147) / 133 100 = 4.94 V` = **2.4% of 208 V**, inside the 3% target |

**Do not share phases between audio and lighting or LED** where it can be avoided. Dimmer racks, LED drivers and motor controllers inject harmonics and switching noise onto the neutral and ground. Put audio on its own phase and its own technical earth, and the buzz that would otherwise take two hours to chase never appears.

---
## 8. Rigging

Rigging is the only part of a rider where an error is measured in injuries. Nothing in this section is a preference.

| Truss Section | Length | Load | Motor | Height |
|---------------|--------|------|-------|--------|
| FOH truss | 12.0 m Global Truss F34 (4× 3 m + 2 corner) | Truss 99 kg + 4× Rogue R2 Spot 128 kg + 4× S4 LED 44 kg + 4× STRIKE 4 44 kg + cable 40 kg = **355 kg** | 2× CM Lodestar Model L, 1 t (2000 lb) | Trim 8.5 m to underside |
| Mid truss | 12.0 m Global Truss F34 | Truss 99 kg + 6× R2 Wash 216 kg + 4× R2 Spot 128 kg + 10× MAC Aura XB 260 kg + cable 50 kg = **753 kg** | 3× CM Lodestar Model L, 1 t | Trim 8.5 m to underside |
| Upstage truss | 10.0 m Global Truss F34 | Truss 83 kg + 6× R2 Wash 216 kg + 4× R2X Beam 100 kg + cable 35 kg = **434 kg** | 2× CM Lodestar Model L, 1 t | Trim 7.0 m to underside |
| LED header truss | 10.0 m Global Truss F34 | Truss 83 kg + LED 220 panels × 8.0 kg = 1760 kg + hanging bars 90 kg = **1933 kg** | 4× CM Lodestar Model RR, 2 t (4000 lb) | Trim 6.5 m to top of wall |
| PA hang L | Meyer MG-LEOPARD grid | 12× LEOPARD @ 34.5 kg = 414 kg + grid 50 kg = **464 kg** | 1× CM Lodestar Model L, 1 t | Trim 7.5 m to top box |
| PA hang R | Meyer MG-LEOPARD grid | Same as PA hang L = **464 kg** | 1× CM Lodestar Model L, 1 t | Trim 7.5 m to top box |
| Sub flown L (option) | Meyer 900-LFC frame | 3× 900-LFC @ 98 kg = 294 kg + frame 40 kg = **334 kg** | 1× CM Lodestar Model L, 1 t | Trim 9.0 m, behind PA hang |
| Sub flown R (option) | Meyer 900-LFC frame | **334 kg** | 1× CM Lodestar Model L, 1 t | Trim 9.0 m |
| Followspot truss | 2× 3.0 m F34 spans, house-rigged | Truss 50 kg + 2× BMFL Spot 74 kg + op 200 kg = **324 kg** | House points, static | Per venue spot chair |
| **Totals** | — | **Suspended load 5395 kg (5.4 t)** | **16 motors** (12× 1 t, 4× 2 t) | — |

### 8.1 Motor utilisation check

| Position | Load | Motors | Load per motor | Motor WLL | Utilisation |
|----------|------|--------|----------------|-----------|-------------|
| FOH truss | 355 kg | 2 × 1 t | 178 kg | 1000 kg | 17.8% |
| Mid truss | 753 kg | 3 × 1 t | 251 kg | 1000 kg | 25.1% |
| Upstage truss | 434 kg | 2 × 1 t | 217 kg | 1000 kg | 21.7% |
| LED header | 1933 kg | 4 × 2 t | 483 kg | 2000 kg | 24.2% |
| PA hang (each) | 464 kg | 1 × 1 t | 464 kg | 1000 kg | 46.4% |
| Sub hang (each) | 334 kg | 1 × 1 t | 334 kg | 1000 kg | 33.4% |

**Never assume even load sharing across motors.** Three motors on a 753 kg truss do not each carry 251 kg — the real distribution depends on where the fixtures sit and how level the truss is. Size each motor as though it could take the largest share, which is the reason every figure above sits well under 50%.

### 8.2 Truss capacity check

Global Truss F34 is a 290 mm square box truss, 50 mm main tubes, 2.0 mm wall. Section weights: 2.0 m = 17.0 kg, 3.0 m = 24.8 kg, 4.0 m = 32.4 kg.

```
MID TRUSS — worst case span
  Span between motor points:  6.0 m (3 motors over 12.0 m)
  F34 uniformly distributed load allowance at 6.0 m span: ~600 kg  (manufacturer chart)
  Applied fixture load over that span: 753 kg x (6.0/12.0) = 377 kg
  Utilisation: 377 / 600 = 62.8%   -> acceptable

LED HEADER — check as UDL
  Span between motor points:  3.33 m (4 motors over 10.0 m)
  F34 UDL allowance at 3.33 m span: ~1200 kg
  Applied load per span: 1933 / 3 spans = 644 kg
  Utilisation: 644 / 1200 = 53.7%   -> acceptable
```

Always work from the **current manufacturer load chart for the exact span and the exact support condition** (two-point simple span vs. multi-point continuous). Interpolating between chart rows is acceptable; extrapolating past the end of the chart is not.

### 8.3 Bridle geometry

When a motor cannot sit directly above the point, a bridle spreads it to two structural members. Leg tension rises sharply with the angle from vertical:

```
  T_leg = (Load / 2) / cos(theta)        theta = angle from vertical

  theta = 30 deg:  T = (L/2) / 0.866 = 0.577 x L per leg
  theta = 45 deg:  T = (L/2) / 0.707 = 0.707 x L per leg
  theta = 60 deg:  T = (L/2) / 0.500 = 1.000 x L per leg   <- each leg now carries the FULL load
  theta = 75 deg:  T = (L/2) / 0.259 = 1.932 x L per leg   <- nearly 2x. Do not.

  Example: 464 kg PA hang on a 45 deg bridle
    T_leg = 464 x 0.707 = 328 kg per leg
    Both legs and both beams must be rated for 328 kg plus their own share
```

**Hard limit [R]: no bridle leg beyond 60° from vertical** without an engineer's review. At 60° each leg already carries the whole load, and every degree past that multiplies fast.

### 8.4 Rigging requirements as rider text

| Item | Requirement |
|------|-------------|
| Personnel | **ETCP-certified rigger** (Arena or Theatre discipline as applicable) for all overhead work [R] |
| Structural approval | Venue provides written point capacities and a rigging plot **before** load-in [A]. No verbal capacities |
| Rigging plot | Production submits a plot with point positions, loads and trims at **T-14 days** for venue review |
| Design factor | Steel 5:1 minimum on all lifting hardware. Synthetics per manufacturer |
| Dynamic derate | Chain hoist capacity is a static rating. Derate for any moving or shock-loaded position |
| Steel | 1/4" 7×19 GAC wire rope slings; 5/8" screw-pin anchor shackles, 3.25 t WLL |
| Round slings | 1 t and 2 t rated. Choke hitch = 80% of vertical rating; basket hitch = 200% |
| Safeties | Secondary steel on every fixture, every panel, every accessory [R] |
| Load cells | Required on any point above 75% of capacity, or where the venue requires monitoring |
| Motor control | Motion Labs 8-way controller, or Kinesys Elevation 1+ for variable-speed and position monitoring |
| Ground rules | Deck cleared and closed during all flying operations. Hard hats in the fly zone [R] |
| Inspection | All hardware inspected and logged before each build. Damaged gear tagged out, removed from site |
| Local law | Comply with local structural and rigging regulation. Where local rule is stricter than this rider, local rule wins |

---
## 9. Backline

`Provided By`: **PROD** production, **VEN** venue, **ART** artist travels with it, **RENT** local sub-rental.

| Item | Spec | Qty | Provided By |
|------|------|-----|-------------|
| Drum kit | DW Collector's Series Maple: 22"×18" kick, 10"×8" and 12"×9" rack toms, 16"×16" floor | 1 | RENT |
| Snare | Ludwig Black Beauty 14"×6.5" | 1 | ART |
| Snare, backup | Yamaha Recording Custom 14"×5.5" | 1 | RENT |
| Cymbals | Zildjian K Custom: 14" hats, 16"/18" crash, 21" ride | 1 set | ART |
| Drum hardware | DW 9000 series: hi-hat stand, 3× boom, snare stand, throne | 1 set | RENT |
| Kick pedal | DW 9000 single | 1 | ART |
| Drum rug | 2.4 m × 2.4 m, non-slip, taped and marked | 1 | PROD |
| Bass head | Ampeg SVT-4PRO, 1200 W | 1 | RENT |
| Bass cab | Ampeg SVT-810E, 8×10", 800 W, 4 Ω | 1 | RENT |
| Bass head, backup | Ampeg SVT-3PRO | 1 | RENT |
| Guitar amp SL | Fender Twin Reverb '65 reissue, 85 W 2×12" | 1 | RENT |
| Guitar amp SR | Vox AC30C2, 30 W 2×12" | 1 | RENT |
| Guitar amp, backup | Marshall JCM800 2203 head + 1960A 4×12" cab | 1 | RENT |
| Guitar amp stand | Amp lift / tilt stand | 3 | PROD |
| Keyboard | Nord Stage 4 Compact 73 | 1 | ART |
| Keyboard, second tier | Yamaha Montage M8x | 1 | RENT |
| Keyboard stand | K&M Spider Pro, 2-tier | 1 | RENT |
| Keyboard bench | Adjustable, padded | 1 | RENT |
| Piano (corporate / conf) | Yamaha C7X 7'6" grand, **tuned to A440 day of show** | 1 | VEN |
| Piano tuning | Certified technician, T-4 h from doors | 1 | VEN |
| Acoustic guitar | Taylor 814ce with ES2 electronics | 1 | ART |
| Guitar stands | Hercules GS414B tilt-back | 6 | PROD |
| Guitar tech station | Table, task light, tuner, string winder, 20 A power | 1 | PROD |
| DI boxes | Radial J48 (active) ×4, JDI (passive) ×2, ProD2 ×6, ProAV2 ×2 | 14 | PROD |
| Instrument cable | 6 m and 10 m, Mogami / Canare, tested | 20 | PROD |
| Power strips, stage | Furman SS-6B, 15 A, on Phase B only | 6 | PROD |
| Music stands | Manhasset #48 with LED clip light | 6 | PROD |
| Riser — drums | 2.4 × 2.4 m × 0.4 m, carpeted, skirted | 1 | PROD |
| Riser — keys | 2.4 × 1.8 m × 0.2 m, carpeted, skirted | 1 | PROD |
| Riser stairs | With handrail, both risers | 2 | PROD |
| Towels, black | Fresh, per show | 12 | VEN |
| Water, still | 500 ml, room temperature, 6 per performer per show | 36 | VEN |

**Tuning and consumables [R]:** all rented backline delivered **tuned, restrung and functional**, with spare tubes for valve amps and spare heads for the kit. "It was working at the shop" is not a defence at 15:00 on a show day. Guitar strings and drum heads are consumables billed to production, and the rider should say so explicitly to avoid an invoice argument.

---

## 10. Crew

| Role | Count | Call Time | Notes |
|------|-------|-----------|-------|
| Production Manager | 1 | 06:00 | On site before the first truck. Owns the schedule and the venue relationship |
| Head Rigger (ETCP) | 1 | 06:30 | First up, points before anything else moves |
| Rigger (ETCP) | 2 | 06:30 | Up-riggers, high steel |
| Head Carpenter / Deck | 1 | 07:00 | Deck, risers, marks |
| Stagehand — load-in | 8 | 07:00 | Truck push. Released after audio/lighting hang unless retained |
| Audio A1 (FOH) | 1 | 08:00 | FOH mix, system tune, RF coordination |
| Audio A2 (Monitors) | 1 | 08:00 | Monitor world, IEM management |
| Audio A3 (Stage / RF tech) | 1 | 08:00 | Patch, mic plot, battery discipline, stage fixes during show |
| Systems Tech | 1 | 07:30 | PA build, prediction vs. measured, Dante network |
| Lighting Designer / LD | 1 | 09:00 | Console, focus, cue build |
| Lighting Director (board op) | 1 | 09:00 | Show operation where LD does not run it |
| Lighting Tech / Electrician | 3 | 07:00 | Hang, address, focus, dimmer world |
| Followspot Operator | 2 | 17:00 | Called for rehearsal onward only |
| Video Director / V1 | 1 | 09:00 | Switcher, camera direction |
| Video Engineer / EIC | 1 | 08:00 | Signal path, genlock, shading, record and stream |
| LED Tech | 2 | 07:30 | Wall build, processor mapping, spare panel swaps |
| Media Server Operator | 1 | 10:00 | Content load, playback, backup server |
| Camera Operator | 3 | 15:00 | Rehearsal onward |
| Streaming Operator | 1 | 12:00 | Encoder, bitrate, platform, failover test |
| Backline Tech — drums | 1 | 10:00 | ART crew where touring |
| Backline Tech — guitars | 1 | 10:00 | Tuning, changes, pedal boards |
| Stage Manager | 1 | 09:00 | Calls the show, owns the deck during performance |
| Show Caller | 1 | 12:00 | Corporate and conference; merges with SM on band shows |
| Wardrobe | 1 | 14:00 | Where costume changes exist |
| Stagehand — load-out | 10 | Show end | Released on truck doors closed |
| Loader | 4 | 07:00 and show end | Truck loading only, both ends of the day |
| Licensed Electrician | 1 | 06:30 | Tie-in and disconnect. **Must be present for both** [R] |
| Local Safety / Fire Marshal liaison | 1 | Per venue | Haze isolation, egress sign-off |

### 10.1 Labour rules that belong in the rider

| Item | Rule |
|------|------|
| Minimum call | 4 hours per IATSE and most local agreements. A 90-minute call bills 4 hours |
| Meal penalty | Break within 5 hours of call, or penalty rate applies for every hour after |
| Overtime | After 8 hours in a day, or after the contracted straight-time window. Confirm the local rate on the advance |
| Double time | Typically after 12 hours, and on designated holidays |
| Turnaround | Minimum 8 hours between release and next call. 10 hours on multi-day builds |
| Crew size authority | The venue's steward sets crew size on union houses. Negotiate at the advance, not at 07:00 |
| Head count vs. skill | Eight hands who have never seen a line array are not a substitute for a systems tech |

**Advance the labour call properly.** The single most common budget overrun on a one-day build is a crew call that ignored the minimum-call and meal-penalty rules. Get the local rate card in writing at T-21 and schedule §11 around the meal breaks rather than discovering them.

---
## 11. Load-In / Load-Out Schedule

The schedule is built backwards from the **first audience touchpoint** (doors, downbeat, or opening video roll), not from when the trucks can arrive. All times in the table are T-relative to that touchpoint. A schedule that starts at "trucks at 06:00" with no downstream coordination will overrun the doors.

### 11.1 Master load-in (rock show reference, 20:00 doors)

| Time (T-relative) | Activity | Crew | Equipment |
|-------------------|----------|------|-----------|
| T-14 h (06:00) | Production manager, head rigger on site, walk the venue | PM, HR | — |
| T-13.5 h (06:30) | Tie-in, main distro energised, work lights | ELEC, 2× SH | Camlock tie, Motion Labs 400 A distro, multimeter |
| T-13 h (07:00) | Stagehand call, truck push begins | 8× SH, 2× LOADER | Pallet jacks, ramp, carpet |
| T-12.5 h (07:30) | PA hang motor points set, truss ground-assembled | 3× RIG, SYS | Global Truss F34, CM Lodestar L, ground-rig frames |
| T-12 h (08:00) | Audio A1/A2/A3 call, FOH drive rack build | A1, A2, A3, SYS | DiGiCo SD12, SD-Rack, drive racks, RF rack, WWB6 scan |
| T-12 h (08:00) | Lighting techs call, fixture hang starts | 3× LT, LD | All moving lights, pars, blinders, console power |
| T-11.5 h (08:30) | LED wall build begins, truss up to trim | 2× LEDT, 3× RIG | ROE BP2 panels, Brompton SX40, motor control |
| T-10 h (10:00) | PA flown, lifted to trim, system tech starts prediction vs measured | SYS, RIG | LEOPARD hangs, 900-LFC subs, Smaart, capture |
| T-9 h (11:00) | LED wall at trim, processor mapping begins | LEDT, V1 | Tessera SX40, disguise gx 2c, fibre to stage |
| T-8.5 h (11:30) | Lighting focus, console patch, address | LD, LT | grandMA3, fixture addressing, focus track |
| T-8 h (12:00) | Media server load, content ingest, frame-lock test | MSO, V1 | disguise, Resolume, HyperDeck |
| T-7.5 h (12:30) | **Crew meal break — 30 min, all departments** | ALL | Catering, no work on deck |
| T-7 h (13:00) | Backline load, drum riser, amp stands, keys rig | 2× BLT, SH | DW kit, Nord Stage 4, amp lift, DI boxes |
| T-6.5 h (13:30) | Monitor world build, IEM packs distributed, ambient mics placed | A2 | Shure PSM1000 ×6, M4 wedges, sidefills UPJ-1P |
| T-6 h (14:00) | Mic patch, sub-snake runs, sub-snake test, talkback | A3 | All mics per §2.1, drum sub-snake 12 ch, HH MM-100 tester |
| T-5.5 h (14:30) | System EQ, delay ring timing, sub array alignment | A1, SYS | Smaart, FFT, measurement mic at FOH |
| T-5 h (15:00) | Line check, channel by channel, gates and compressors set | A1, A3 | Soloed channel, walkie-talkie to stage |
| T-4 h (16:00) | Camera shading, ISO record start, multiview set | V1, VE | Sony HXC-FB80, RCP-1500, HyperDeck Studio 4K Pro |
| T-4 h (16:00) | Streaming encoder test, YouTube RTMP check, bonded cellular online | STREAM | Blackmagic Web Presenter 4K, LiveU Solo PRO |
| T-3.5 h (16:30) | LD cue build, focus and palette work, haze test with fire marshal | LD, LT, FIRE | grandMA3, Amhaze Whisper, MDG theONE |
| T-3 h (17:00) | Rehearsal call, artists on stage, run full show | ALL, ART | Full system live, MD on talkback |
| T-2 h (18:00) | **Doors crew call** — house, F&B, security, merch | HOUSE, FOH, SEC | — |
| T-2 h (18:00) | Dinner break, 60 min, in two sittings | ALL, ART | Catering, no work on stage |
| T-1.5 h (18:30) | Walk-in music on lobby, hearing assist loop test | A1, HOUSE | Lobby feed, induction loop receiver |
| T-1 h (19:00) | Doors — house opens, walk-in, F&B service | ALL | Show relay to dressing rooms |
| T-0.5 h (19:30) | Artists dressed, mic'd, talkback check to MD | A3, SM, ART | Final patch test |
| T-0 (20:00) | House lights to show, downbeat | A1, A2, LD, V1 | Full show systems live |
| Show end (~22:00) | Curtain call, playback off, encore bed | A1, A2 | — |
| Show end + 15 min | Artist clear of stage, wardrobe change | WARD, ART | — |
| Show end + 30 min | **Load-out begins** — backline strike, soft goods | 10× SH, 2× BLT | Cases, carts, hardware |
| Show end + 60 min | PA down, lighting down, cable pulls | SYS, LT, SH | Hoists reverse-rigged, cable coilers |
| Show end + 90 min | LED wall strike, processor pack | LEDT, SH | Panel cases, foam, anti-static |
| Show end + 120 min | Truss down, motors down, points clear | 3× RIG, SH | Hoists to cases, hardware to bins |
| Show end + 150 min | Distro de-energised, tie-in removed | ELEC | Lock-out/tag-out, cable reel |
| Show end + 180 min | Truck doors closed, venue broom-clean | LOADER, SH | Final sweep, dock master sign-off |

### 11.2 Schedule rules that belong in the rider

| Item | Rule |
|------|------|
| Schedule authority | The Production Manager owns the schedule. Changes after T-7 days require written PM approval [R] |
| Meal breaks | One unpaid 30-min meal break per 5 hours of work, OR penalty rates apply. Schedule the break explicitly; do not assume it will be discovered |
| Minimum call | 4 hours per IATSE / most local agreements. Schedule does not save a 90-minute call |
| Hard stops | Lighting focus, line check, and system tune are non-negotiable hard stops before rehearsal. Slip them and you are deciding on the day to skip RF coordination |
| Walkie channels | Assign by department at the morning meeting: A1, A2, A3, LD, V1, RIG, SM, PROD. Posting the list saves the first hour of "who has channel 4" |
| Handover | The PM-to-PM handover at shift change is in writing, not verbal. A 30-second voice note is not a handover |
| Contingency time | Build 60-90 min of slack into the schedule. A clean build still uses it; a hard build needs it |
| Weather call (outdoor) | PM makes the weather call by T-4 h with the promoter and LD. Haze, wind, and rain each have a documented threshold |

### 11.3 Quick build — corporate / conference

A one-day corporate or conference build compresses the same flow. Trucks at 04:00, doors at 13:00, show at 14:00. Skip what does not apply: no PA fly, no LED wall build, no monitor world.

| Time | Activity | Crew | Notes |
|------|----------|------|-------|
| T-9 h (04:00) | Truck push, distro, FOH position | 4× SH, ELEC, A1 | Camlock, projector lift |
| T-8 h (05:00) | Stage build, risers, lectern, screens down | 4× SH, CARP | Risers, drape, screen frames |
| T-7 h (06:00) | Lighting hang, FOH truss, focus | 2× LT, LD | grandMA3 on PC, smaller rig |
| T-6 h (07:00) | Audio line check, RF coord, lav check | A1, A2 | 6× RF channels, WWB6 scan |
| T-5 h (08:00) | Video path, switcher, cameras, record | V1, VE | Ross Carbonite or ATEM 4 M/E |
| T-4 h (09:00) | Streaming test, YouTube RTMP, OBS scene | STREAM | Web Presenter 4K, LiveU backup |
| T-3 h (10:00) | Rehearsal with presenters, run-of-show | A1, V1, SM | Click track, slide advance |
| T-2 h (11:00) | Meal break, presentation load to servers | ALL, MSO | ProRes content, native canvas |
| T-1 h (12:00) | Final system check, walk-in music, hearing loop | A1, HOUSE | Verify ADA loop |
| T-0 (13:00) | Doors | — | — |
| T+1 h (14:00) | Show | A1, A2, LD, V1, SM, STREAM | Full crew live |
| Show end + 30 min | Load-out, truck pack | 6× SH, LOADER | Compressed 3-4 h strike |

---

# Appendix A — Corporate General Session (16 ch, 2 projectors)

**Event:** Acme Industries Annual General Meeting 2026
**Venue:** Hilton San Francisco Union Square, Grand Ballroom (capacity 200 seated banquet, 300 theatre)
**Date:** 14 March 2026, doors 13:00, show 14:00-17:00
**Rider revision:** v1.0
**Issued by:** Production Manager — see cover sheet
**Advance deadline:** T-21 days (21 Feb 2026)

## A.1 Stage and room

| Parameter | Value |
|-----------|-------|
| Room | Grand Ballroom, 30.5 m × 18.3 m, 5.6 m ceiling |
| Stage | 12.2 m × 4.3 m × 0.4 m high, carpeted, skirted on three sides |
| House left riser | 2.4 m × 1.8 m × 0.2 m — panel / moderator position |
| House right riser | 2.4 m × 1.8 m × 0.2 m — secondary panel / podium |
| Centre lectern | 0.8 m × 0.6 m, locking front panel, gooseneck light, confidence 24" |
| FOH position | House centre, 18.3 m from downstage, 3.0 m × 1.8 m, level floor, sightline clear |
| Projection | Two screens 4.9 m × 2.7 m Da-Lite Fast-Fold Deluxe, rear projection, 1.5 m stage left and stage right of centre |
| Projection booth | 4.0 m deep, upstage centre, two Panasonic PT-RZ21K at ET-DLE060 short throw |
| Audience | 200 banquet rounds OR 300 theatre, ground-supported seating, no balcony |
| Sightline check | Worst seat at 30° from centre sees both screens with full image |

**No flown PA [R].** Self-powered point-source Meyer Sound UPM-1P and USW-210P subs on the stage lip, with delay ring of 4× UPM-1P at 12 m back. The ballroom ceiling is 5.6 m — too low for a meaningful line array hang, and a corporate room does not need one. FOH volume target is 85-90 dB(A) at the mix position, not concert level.

## A.2 Input list — 16 channels

| Ch# | Source | Mic Model | Stand | Phantom | Insert | Notes |
|-----|--------|-----------|-------|---------|--------|-------|
| 1 | Lectern L | Shure MX418/C 18" gooseneck | DT | Y | Comp + gate | On lectern, redundant pair one fader |
| 2 | Lectern R | Shure MX418/C 18" gooseneck | DT | Y | Comp + gate | |
| 3 | Handheld 1 (Q&A) | Shure ULXD2/SM58 | TB | N | Comp + DeEsser | Roamer, house left, RF ch A1 |
| 4 | Handheld 2 (Q&A) | Shure ULXD2/SM58 | TB | N | Comp + DeEsser | Roamer, house right, RF ch A2 |
| 5 | Lav 1 | Shure ULXD1 + DPA 4066 headset | — | — | Comp + DeEsser | CEO opening, headworn, beige |
| 6 | Lav 2 | Shure ULXD1 + DPA 6060 subminiature | — | — | Comp + DeEsser | CFO, subminiature, beige |
| 7 | Lav 3 | Shure ULXD1 + DPA 6060 subminiature | — | — | Comp + DeEsser | COO, subminiature, beige |
| 8 | Lav 4 (spare) | Shure ULXD1 + DPA 6060 subminiature | — | — | Comp + DeEsser | Spare, charged, cued |
| 9 | Panel table 1 | Shure MX392/C boundary | DT | Y | Gate | 2 seats per mic, table 1 of 4 |
| 10 | Panel table 2 | Shure MX392/C boundary | DT | Y | Gate | Table 2 of 4 |
| 11 | Panel table 3 | Shure MX392/C boundary | DT | Y | Gate | Table 3 of 4 |
| 12 | Panel table 4 | Shure MX392/C boundary | DT | Y | Gate | Table 4 of 4 |
| 13 | Playback L | Radial ProAV2 | — | N | — | Show laptop, 3.5 mm TRRS to RCA, summed to 2× XLR |
| 14 | Playback R | Radial ProAV2 | — | N | — | Linked to Ch13, **do not split** |
| 15 | Remote caller | Radial ProAV1 | — | N | Comp + AGC | Teams/Zoom return, **mix-minus to bus 7** |
| 16 | Walk-in music | Radial ProAV2 | — | N | — | Dedicated iPad, not show laptop |

**Stand summary:** `DT × 6, TB × 2`. Wireless: 2× ULXD2 handheld + 4× ULXD1 bodypack = **6 RF channels** (plus 1× spare ULXD1 on standby). Coordination with WWB6, scan on site, 470-608 MHz.

**Mix-minus [R]:** Ch15 fed from Bus 7 which excludes Ch15 from its source. Tested at rehearsal with the actual remote site on the call. No bus = no show, this is non-negotiable.

## A.3 Output list

| Out# | Destination | Signal Type | Cable | Notes |
|------|-------------|-------------|-------|-------|
| 1 | Meyer UPM-1P L (FOH main) | Analogue | XLR 3-pin, 15 m | Self-powered |
| 2 | Meyer UPM-1P R (FOH main) | Analogue | XLR 3-pin | |
| 3 | Meyer UPM-1P C (centre fill) | Analogue | XLR 3-pin | Front of stage lip |
| 4 | Meyer USW-210P sub L | Analogue | XLR | Ground-stacked, phase-aligned |
| 5 | Meyer USW-210P sub R | Analogue | XLR | |
| 6-9 | Delay ring UPM-1P ×4 | Analogue | XLR, 30 m | 12 m back from downstage, +9 ms delay |
| 10 | Mix-minus send to Ch15 bus | Internal | — | Bus 7, excludes Ch15 |
| 11 | Record (HyperDeck) | Analogue | XLR | -10 dB pad, pre-fader post-gain |
| 12 | Video switcher return (SDI embed) | Analogue | XLR | To Ross Carbonite aud in |
| 13 | Overflow / lobby | Analogue | XLR | Level-limited, -10 dB from mains |
| 14 | Hearing assist (induction loop) | Analogue | XLR | **ADA required [R]**, tested before doors |
| 15 | Press mult (passive split) | Analogue | 4× XLR passive | 1 per outlet, transformer split |
| 16 | Confidence monitor (lectern) | Analogue | 3.5 mm to HDMI | Off console PFL, not programme |

## A.4 Console and DSP

| Item | Make/Model | Qty | Notes |
|------|------------|-----|-------|
| FOH console | Yamaha RIVAGE PM7 with CS-R10 control surface | 1 | 144 in / 64 out, Dante I/O |
| Console backup | Yamaha DM7 | 1 | Tracking backup, session-joined |
| I/O rack | RIVAGE RPio622 | 1 | 32 in / 16 out analogue, Dante |
| Wireless | Shure ULXD4Q × 2 (4 receivers each) | 2 | 8 channels total, networked via WWB6 |
| Antenna dist | Shure UA844+SWB | 2 | 4-way active antenna distribution |
| Antennas | Shure UA874 active paddle | 2 | 2 m above deck, line-of-sight to lectern |
| Record | Blackmagic HyperDeck Studio HD Pro | 1 | ProRes 422 HQ, 1080p59.94, timecode-stamped |

## A.5 PA design

A corporate room at 200-300 seats with a 5.6 m ceiling does not need a line array. A self-powered point-source system gives better speech intelligibility, lower visual profile, and faster build.

| Position | Model | Qty | Mount | Notes |
|----------|-------|-----|-------|-------|
| FOH main L/R | Meyer Sound UPM-1P | 2 | U-bracket on stand, 2.3 m | 100° × 100° coverage, 16 kg each |
| Centre fill | Meyer Sound UPM-1P | 1 | Stage lip, low stand | Covers front 8 m, fills the speech-in-front gap |
| Delay ring | Meyer Sound UPM-1P | 4 | Truss or ceiling per venue | 12 m from downstage, +9 ms, 6 dB below mains |
| Subwoofer | Meyer Sound USW-210P | 2 | Ground-stacked, SL+SR | Dual 10", 35-180 Hz, for video playback and walk-in only — **not for speech** |
| System processor | Meyer Sound Galileo GALAXY 408 | 1 | At FOH, networked | All EQ, delay, and array optimisation |

**Speech-vs-music priority [R]:** the system is tuned for speech intelligibility. STI target 0.55 minimum (good), 0.60+ preferred. Music playback is on a separate bus with a slight low-mid lift and a higher sub level. The two buses are not summed to the same output.

## A.6 Video

| Item | Spec | Qty | Notes |
|------|------|-----|-------|
| Projector | Panasonic PT-RZ21K, 20 000 lm, laser, WUXGA | 2 | Rear projection, ET-DLE060 short throw |
| Projector lens | ET-DLE060 0.6:1 | 2 | Throw 2.94 m to 4.9 m screen |
| Screen | Da-Lite Fast-Fold Deluxe 4.9 m × 2.7 m, rear surface | 2 | Dressed on all four sides |
| Switcher | Ross Carbonite Ultra 60 | 1 | 2 M/E, 24 inputs, 12G-SDI |
| Camera | Sony HXC-FB80 with 20× box lens | 3 | FOH long centre, SL handheld, SR handheld |
| Camera control | Sony RCP-1500 | 3 | At V1 |
| Multiview | 2× 32" 4K UHD | 2 | V1 + show caller |
| Confidence monitor | 24" 1080p on lectern, 1× 55" downstage centre | 2 | Mirrored programme, no OSD |
| Streaming encoder | Blackmagic Web Presenter 4K | 1 | 1080p59.94, 6 Mbps H.264 to YouTube Live |
| Streaming backup | LiveU Solo PRO, bonded cellular | 1 | Auto-failover, 2× carrier SIM |
| Record | HyperDeck Studio HD Pro | 1 | ProRes 422 HQ, A/B redundant |
| Genlock | Blackmagic Sync Generator, tri-level 1080p59.94 | 1 | **All devices genlocked [R]** |

**Content deadline [R]:** all presentation files delivered T-48 h in 1920×1080 PNG (slides) and ProRes 422 HQ (video), 16:9, 59.94 fps. Speakers do not bring their own laptops on stage. Show laptop loaded from approved masters only.

## A.7 Lighting

A corporate general session needs even, clean, camera-friendly light. The lighting design is the show.

| Fixture | Type | Qty | Position | DMX Universe |
|---------|------|-----|----------|--------------|
| ETC Source Four LED Series 3 Lustr | Ellipsoidal, 26° or 36° | 12 | FOH truss, 3-colour front wash | U1 |
| ETC ColorSource Spot V | LED spot, RGBW | 8 | FOH truss, key and specials | U1 |
| Chauvet COLORdash Par-Quad 18 | LED par, RGBW | 16 | Stage wash, truss front | U1 |
| Chauvet Ovation E-260WW | Warm white ellipsoidal, 3000 K | 6 | Lectern key, panel key | U2 |
| Chauvet Ovation F-915VW | Fresnel, variable white | 8 | Stage wash, soft | U2 |
| Chauvet Amhaze Whisper | Haze, water-based, low noise | 1 | Upstage SR | U2 |
| House light | Relay on architectural dimmer | 1 | All zones | U2 |
| Console | MA Lighting grandMA3 light | 1 | FOH lighting position | — |
| Console backup | grandMA3 onPC command wing | 1 | Tracking backup | — |
| DMX node | Luminex LumiNode 4 | 2 | FOH, dimmer world | U1-U2 |

**Tuning [R]:** all white light at 3200 K for camera, with presenters keyed at 5600 K (+/- 200 K crossfade) when on screen. The on-stage talent must read consistently to camera; the audience sees warm white, the camera sees daylight, the operator crossfades at the right cue. No mismatched colour temperatures on a mixed source.

## A.8 Power

| Circuit | Amps | Voltage | Phase | Distro | Load Calc |
|---------|------|---------|-------|--------|-----------|
| **SERVICE** | 100 A | 120/208 V | 3φ wye | Camlock to main distro, upstage SL | Total connected 12.8 kW → 12800 / 360 = **35.6 A/leg**; /0.80 = 44.5 A req. → 100 A. Utilisation **44.5%** |
| A-1 FOH audio | 20 A | 120 V | 1φ | 6× L5-20R at FOH position | Console 4 A, I/O rack 2 A, RF rack 2 A, processing 1 A, drive 2 A = **11 A** = 1.32 kW (55% of 20 A). Isolated ground [R] |
| A-2 Stage audio | 20 A | 120 V | 1φ | 4× L5-20R at stage drop | DI rack 2 A, playback 1 A, RF dist 1 A = **4 A** |
| V-1 Projection | 30 A | 208 V | 1φ per projector | 2× L6-30R, one per projector | 2× PT-RZ21K @ 2100 W = 4200 W / 208 = **20.2 A** → 1 projector per 30 A circuit, 10.1 A each |
| V-2 Video control | 20 A | 120 V | 1φ | 6× L5-20R at V1 + camera CCU | Servers 2 A, switcher 2 A, cameras 1.5 A, decks 1 A = **6.5 A** |
| L-1 Lighting | 60 A | 120/208 V | 3φ | Motion Labs 60 A → 6× Socapex 19-pin + 6× L5-20 | Connected 7.2 kW → 7200 / 360 = **20.0 A/leg**; /0.80 = 25.0 A req. → 60 A. Utilisation **41.7%** |
| C-1 Comms | 20 A | 120 V | 1φ | 4× L5-20R, UPS-backed | Intercom 1 A, switch 2 A, RF charging 1 A = **4 A** |
| S-1 House | 20 A | 120 V | 1φ | House GPO, work light, tools only | **Not for show equipment** |

**Phase balance:**
```
Leg A: A-1 FOH (11) + V-2 video (6.5)                = 17.5 A
Leg B: A-2 stage (4) + C-1 comms (4)                 = 8.0 A
Leg C: V-3 spare + lighting leg (20.0/3 of 7.2 kW)   = 12.0 A
Imbalance = (17.5 - 8.0) / 17.5 = 54%  -> re-balance, move A-1 to Leg C
```

**Re-balance on the advance.** The leg imbalance is large because FOH audio is on a single phase; move A-1 to Leg C and split the lighting draw so the system sits under 10% imbalance.

## A.9 Rigging

The corporate rig is house-rigged where possible. No motors or chain hoists run for a one-day corporate build.

| Item | Spec | Qty | Notes |
|------|------|-----|-------|
| FOH truss | 12.0 m Global Truss F34, house-rigged | 1 | Trim 4.5 m, 6× S4 LED + 8× ColorSource |
| Stage left truss | 6.0 m F34 | 1 | Panel key, 3× S4 LED + 2× Ovation |
| Stage right truss | 6.0 m F34 | 1 | Panel key, 3× S4 LED + 2× Ovation |
| Rigging personnel | ETCP rigger for any non-house point | 1 | **Not required if all points house-rigged [A]** |
| Rigging plot | Production submits at T-14 days | 1 | Venue confirms point capacities in writing |
| Design factor | 5:1 on all steel, synthetics per manufacturer | — | [R] |
| Safeties | Secondary steel on every fixture | — | [R] |
| Hard hats | In the fly zone during any overhead work | — | [R] |

## A.10 Backline

The corporate rider has minimal backline. The room and the venue provide most of it.

| Item | Spec | Qty | Provided By |
|------|------|-----|-------------|
| Lectern | Custom, locking front panel, gooseneck light, confidence 24", cable cubby | 1 | RENT |
| Lectern mic | Shure MX418/C 18" gooseneck | 2 | PROD |
| Panel table | 1.8 m × 0.6 m, skirted, cable management | 4 | VEN |
| Panel mic | Shure MX392/C boundary | 4 | PROD |
| Podium (secondary) | Sloped top, locking, 1.2 m | 1 | VEN |
| Confidence monitor | 24" 1080p, HDMI in, floor stand | 1 | RENT |
| Music stand | Manhasset #48 with LED clip light | 1 | RENT |
| Table for awards / trophies | 1.8 m × 0.6 m, draped | 1 | VEN |
| Water, still | 500 ml, room temp, 4 per speaker | 16 | VEN |
| Water, sparkling | 500 ml, 2 per speaker | 8 | VEN |

## A.11 Crew

| Role | Count | Call | Notes |
|------|-------|------|-------|
| Production Manager | 1 | 04:00 | On site for trucks |
| Audio A1 (FOH) | 1 | 05:00 | Mix, RF coord, system tune |
| Audio A2 (stage / backup) | 1 | 05:00 | Mic plot, lav check, stage mgmt |
| Video Director / V1 | 1 | 06:00 | Switcher, camera shading |
| Video Engineer | 1 | 06:00 | Signal path, genlock, record, stream |
| Lighting Designer / Board Op | 1 | 06:00 | Console, focus, cue build |
| Lighting Tech | 2 | 06:00 | Hang, focus, dimmer world |
| Streaming Operator | 1 | 11:00 | Encoder, bitrate, platform |
| Show Caller | 1 | 12:00 | Merges with Stage Manager |
| Stagehand — load-in/out | 6 | 04:00 and show end | One shift |
| Loader | 2 | 04:00 and show end | Truck only |
| Licensed Electrician | 1 | 05:00 | Tie-in, disconnect [R] |

---

# Appendix B — Rock Band (32 ch, full PA, IEM, LED wall)

**Event:** Vega Falls — "Atlas Burning" North American Tour, Leg 1
**Venue:** The Eastern, Atlanta GA (2 400 cap live music venue, 14 m stage, 9 m ceiling)
**Date:** 22 April 2026, doors 19:00, show 20:30
**Rider revision:** v1.0
**Issued by:** Tour Production Manager
**Advance deadline:** T-21 days (1 April 2026)
**Final revision lock:** T-7 days (15 April 2026)

## B.1 Stage and room

| Parameter | Value |
|-----------|-------|
| Room | The Eastern, 38 m × 26 m, 9 m clear height, balcony three sides |
| Stage | 14.0 m wide × 9.0 m deep, 1.2 m high, hard deck, black marley |
| Drum riser | 2.4 m × 2.4 m × 0.4 m, centred, carpeted |
| Keys riser | 2.4 m × 1.8 m × 0.2 m, stage right of drum riser, carpeted |
| FOH position | House centre, 22 m from downstage edge, 3.0 m × 2.4 m, level floor, **not under balcony** |
| Monitor world | Stage left, 2.4 m × 2.4 m, under side balcony, **open to deck** |
| Backline area | Downstage, 4.2 m × 3.0 m clear, all on Phase B |
| LED wall | Upstage centre, 4.0 m × 2.5 m, ROE Visual Black Pearl BP2, 0.6 m from back wall |
| Side screens | 2× 2.5 m × 1.4 m IMAG, SL and SR, flown with PA |
| Camera positions | FOH long, SL handheld, SR handheld, drum-cam |
| Sightline check | Balcony front row at 35° sees the full LED wall, all performers, and the lyric screen |

## B.2 Input list — 32 channels

| Ch# | Source | Mic Model | Stand | Phantom | Insert | Notes |
|-----|--------|-----------|-------|---------|--------|-------|
| 1 | Kick in | Shure Beta 91A | — | Y | Gate + comp | Inside shell on pillow, polarity check |
| 2 | Kick out | Audix D6 | SB | N | Comp | 100 mm off port, polarity check vs Ch1 |
| 3 | Snare top | Shure SM57 | SB | N | Gate + comp | Rim-mount clip acceptable |
| 4 | Snare btm | Shure SM57 | SB | N | Gate | **Polarity invert** |
| 5 | Hi-hat | AKG C451 B | SB | Y | HPF 200 Hz | Edge of bell, away from snare |
| 6 | Rack tom 1 | Sennheiser e904 | CL | N | Gate + comp | |
| 7 | Rack tom 2 | Sennheiser e904 | CL | N | Gate + comp | |
| 8 | Floor tom | Sennheiser e904 | CL | N | Gate + comp | |
| 9 | OH L | Neumann KM 184 | TB | Y | Comp | Spaced pair, 1.4 m above kit, matched pair |
| 10 | OH R | Neumann KM 184 | TB | Y | Comp | Match cable length to Ch9 |
| 11 | Ride | AKG C451 B | SB | Y | HPF 250 Hz | |
| 12 | Drum sub mic | Shure Beta 52A | SB | N | — | Optional, FOH discretion |
| 13 | Bass DI | Radial J48 | — | Y | Comp | Pre-amp DI out from Ampeg SVT-4PRO |
| 14 | Bass mic | Sennheiser e902 | SB | N | Comp | 8×10 cab, upper-left driver, 25 mm off grille |
| 15 | Gtr SL 1 | Sennheiser MD 421-II | SB | N | — | 25 mm off grille, 40 mm off dust cap |
| 16 | Gtr SL 2 | Royer R-121 | SB | N | — | Ribbon, blend with Ch15, **phantom OFF [R]** |
| 17 | Gtr SR 1 | Shure SM57 | SB | N | — | Vox AC30C2, top input |
| 18 | Gtr SR 2 | Audix i5 | SB | N | — | Bottom input, blend with Ch17 |
| 19 | Acoustic gtr | Radial JDI | — | N | Comp + notch | Taylor 814ce, passive DI for piezo source |
| 20 | Keys L | Radial ProD2 (L) | — | N | Comp | Nord Stage 4 main L out |
| 21 | Keys R | Radial ProD2 (R) | — | N | Comp | Linked to Ch20 |
| 22 | Keys aux L | Radial ProD2 (L) | — | N | — | Second board (Yamaha Montage M8x) |
| 23 | Keys aux R | Radial ProD2 (R) | — | N | — | |
| 24 | Playback L | Radial ProD2 (L) | — | N | — | Timecode-locked, **do not fade at FOH** |
| 25 | Playback R | Radial ProD2 (R) | — | N | — | |
| 26 | Click | Radial ProD2 | — | N | — | **To monitors only, hard-muted at FOH** |
| 27 | Lead vox | Shure Axient Digital AD2/KSM9HS | TB | N | Comp + DeEsser | RF, hypercardioid capsule |
| 28 | Lead vox spare | Shure Axient Digital AD2/KSM9HS | TB | N | Comp + DeEsser | Same channel strip as Ch27 |
| 29 | SL vox | Shure Beta 58A | TB | N | Comp | Wired, guitarist |
| 30 | SR vox | Shure Beta 58A | TB | N | Comp | Wired, bassist |
| 31 | Talkback / MD | Shure SM58 | TB | N | HPF 150 Hz | Stage left, **not in FOH mains** |
| 32 | Spare | — | ST | — | — | Patched to sub-snake 1 ch 8 |

**Stand summary:** `TB × 5, SB × 12, ST × 1, CL × 3` plus 3× rim clip. Sub-snakes: SL 12 ch, SR 12 ch, drums 12 ch.

## B.3 Output list

| Out# | Destination | Signal Type | Cable | Notes |
|------|-------------|-------------|-------|-------|
| 1 | PA Main L (primary) | Dante / AES67 | Cat6A shielded, primary | Meyer LEOPARD hang L |
| 2 | PA Main R (primary) | Dante / AES67 | Cat6A shielded, primary | Meyer LEOPARD hang R |
| 3 | PA Main L (secondary) | Dante secondary | Cat6A shielded, secondary | Physically separate path |
| 4 | PA Main R (secondary) | Dante secondary | Cat6A shielded, secondary | |
| 5 | Sub aux-fed L | Dante | Cat6A shielded | Aux-fed, not matrixed |
| 6 | Sub aux-fed R | Dante | Cat6A shielded | |
| 7 | Front fill C | Dante | Cat6A shielded | Meyer UPM-1P, delay +4.2 ms, -6 dB |
| 8 | Front fill out-fill L | Dante | Cat6A shielded | Meyer UPQ-1P, downstage edge |
| 9 | Front fill out-fill R | Dante | Cat6A shielded | |
| 10 | Delay ring L (balcony) | Dante | Cat6A shielded | Meyer LEOPARD delay, +38 ms |
| 11 | Delay ring R (balcony) | Dante | Cat6A shielded | |
| 12 | Sidefill SL | Analogue | XLR 3-pin, 30 m | d&b M4, +4 dBu nominal |
| 13 | Sidefill SR | Analogue | XLR 3-pin | |
| 14 | IEM mix 1 (lead) | Dante to PSM1000 | Cat6A | Shure PSM1000 transmitter |
| 15 | IEM mix 2 (SL gtr/vox) | Dante to PSM1000 | Cat6A | |
| 16 | IEM mix 3 (SR gtr/vox) | Dante to PSM1000 | Cat6A | |
| 17 | IEM mix 4 (keys) | Dante to PSM1000 | Cat6A | |
| 18 | IEM mix 5 (drums) | Dante to PSM1000 | Cat6A | |
| 19 | IEM mix 6 (bass) | Dante to PSM1000 | Cat6A | |
| 20 | IEM mix 7 (spare) | Dante to PSM1000 | Cat6A | Coordinated, on standby |
| 21 | Broadcast / stream L | Analogue, **isolated** | XLR via Jensen ISO-MAX | Transformer isolated |
| 22 | Broadcast / stream R | Analogue, **isolated** | XLR via Jensen ISO-MAX | |
| 23 | Multitrack record 1-32 | Dante virtual soundcard | Cat6A to record rig | 48 kHz / 24-bit, pre-fader post-gain |
| 24 | Press / mult box | Analogue mic-level | 8× XLR passive mult | Transformer split |
| 25 | Overflow / lobby | Analogue | XLR | -10 dB from mains |
| 26 | Hearing assist | Analogue | XLR to induction loop | **ADA required [R]** |
| 27 | Video switcher return | Analogue | XLR | To Carbonite aud in |
| 28 | Confidence / green room | Analogue | XLR | Mains-derived, with talkback |
| 29 | Show relay / paging | Analogue | XLR | Dressing rooms |
| 30 | Video walls (IMAG L) | Dante | Cat6A to LED processor | Wall feed |
| 31 | Video walls (IMAG R) | Dante | Cat6A | |
| 32 | Lyric / confidence stage | Analogue | HDMI from media server | 2× 32" downstage |

## B.4 Monitor world

| Mix# | Performer | Type | Model | Notes |
|------|-----------|------|-------|-------|
| 1 | Lead vocal | IEM stereo | Shure PSM1000 + SE846 | Ambient pair at -18 dB in mix |
| 2 | SL guitar / vox | IEM stereo | Shure PSM1000 + SE425 | Own vox +3 dB over house artist ref |
| 3 | SR guitar / vox | IEM stereo | Shure PSM1000 + SE425 | |
| 4 | Keys | IEM stereo | Shure PSM1000 + SE425 | Click hard left, cue right |
| 5 | Drums | IEM stereo | Shure PSM1000 + SE846 | + drum sub feed |
| 6 | Bass | IEM stereo | Shure PSM1000 + SE425 | + bass mic + DI blend |
| 7 | Drum sub / thumper | Tactile | ButtKicker BK-LFE (kit) + Clark Synthesis TST239 (bass seat) | Kick + floor tom only, 30-80 Hz |
| 8 | SL spot wedge | Wedge | d&b audiotechnik M4 | Backup for Mix 2 IEM failure |
| 9 | SR spot wedge | Wedge | d&b audiotechnik M4 | Backup for Mix 3 |
| 10 | Sidefill SL | Wedge | d&b audiotechnik M4 | d&b D20 amplifier, single 12"+horn |
| 11 | Sidefill SR | Wedge | d&b audiotechnik M4 | |
| 12 | Guest / support | Wedge ×2 | d&b audiotechnik M4 | Shared mix, downstage centre |
| 13 | Ambient mic feed | Source | 2× DPA 4560 | Downstage edge, into all IEM mixes |
| 14 | Monitor engineer wedge | Wedge | d&b M4 | At monitor world |
| 15 | Shout / talkback | Mix | — | MD to all IEMs, latching key |
| 16 | Spare IEM pack | IEM stereo | Shure PSM1000 + SE425 | Coordinated, charged, on standby |

**Monitor console [R]:** DiGiCo SD12-96 at monitor world, 96 kHz, 24 mix buses, 32-bit floating point, with 2× SD-Rack (56 in / 40 out). The monitor world runs on a fully independent console from FOH.

**Ambient mics [R]:** DPA 4560 CORE binaural pair, mounted on a stereo bar at the downstage edge, fed to all IEM mixes. Without ambient mics, IEM-wearing performers feel isolated and lose the room, and the show goes flat.

## B.5 PA design

A 2 400-cap room with 9 m of clear height and a balcony on three sides needs a flown line array with delay. The reference design is Meyer Sound LEOPARD with 900-LFC subs, ground-stacked or flown depending on sightlines.

| Position | Model | Qty | Mount | Notes |
|----------|-------|-----|-------|-------|
| Main hang L | Meyer Sound LEOPARD | 12 | Flown, MG-LEOPARD grid, 4° inter-box | 8 m trim, top box at 8.5 m |
| Main hang R | Meyer Sound LEOPARD | 12 | Flown | Mirror of L |
| Sub L | Meyer Sound 900-LFC | 3 | Flown, behind PA hang | Cardioid array, 30-125 Hz |
| Sub R | Meyer Sound 900-LFC | 3 | Flown | |
| Front fill | Meyer Sound UPM-1P | 2 | Stage lip | Delay +4.2 ms, -6 dB |
| Out fill | Meyer Sound UPQ-1P | 2 | Downstage edge, ground | Wide coverage front rows |
| Delay ring (balcony) | Meyer Sound LEOPARD | 4 | House-rigged or flown | +38 ms, -3 dB from mains |
| System processor | Meyer Sound Galileo GALAXY 408 | 1 | At FOH, networked | All EQ, delay, array optimisation |
| Drive | Meyer Sound MDM-832 | 2 | At amp world | AES3 distribution to amps |

**Sub array option:** flown cardioid (preferred) or ground-stacked. The flown option keeps the deck clear and the sightline open, costs 2× motors and 4× flying frames. At a 2 400-cap club the flown option is normal.

**Tuning target [R]:** SPL 100-103 dB(A) slow at FOH during the loudest chorus, with 6-10 dB of headroom available from the LEOPARD before limiting. C-weighted peak should not exceed 125 dB at the mix position. House curve: gentle low-mid shelf, 4 dB at 80 Hz, 2 dB at 10 kHz, no aggressive dips in the vocal range 1-4 kHz.

## B.6 LED / Video

| Item | Spec | Qty | Notes |
|------|------|-----|-------|
| LED panel — main wall | ROE Visual Black Pearl BP2, 2.84 mm pitch, 500 × 500 mm, indoor | 80 | 16 W × 8 H = 8.0 m × 4.0 m, set to **4.0 m × 2.5 m** for this tour |
| LED panel — spares | Same batch / same bin | 4 | 5% spare rate [R] |
| Wall resolution | 1408 × 880 px | — | 88 × 110 px per panel |
| LED processor | Brompton Tessera SX40 | 1 | 4.4 Mpx @ 60 Hz capacity, 1.4 Mpx used |
| LED processor — backup | Brompton Tessera SX40 | 1 | Hot spare, pre-loaded |
| Data distribution | Brompton XD 10G | 1 | Fibre to stage |
| Media server | disguise gx 2c | 1 | Primary, 4× 4K outputs |
| Media server — backup | disguise gx 2c | 1 | Understudy, frame-locked |
| Playback / VJ | Resolume Arena 7 on Mac Studio M2 Ultra | 1 | Secondary content source |
| Switcher | Ross Carbonite Ultra 60 | 1 | 2 M/E, 24 inputs |
| IMAG screens | 2× 2.5 m × 1.4 m LED panels, flown with PA | 2 | Side IMAG, ROE BP2 outdoor spec |
| Camera | Sony HXC-FB80 with 20× box lens | 3 | FOH long, SL, SR |
| Camera — handheld | Sony PXW-Z280 | 1 | Roaming, wireless SDI |
| Camera — drum | Sony PXW-Z280 with 16× lens | 1 | Drum-cam, mounted to riser |
| Camera control | Sony RCP-1500 | 3 | At V1 |
| Multiview | 2× 32" 4K UHD + 1× 55" programme | 3 | V1 + show caller |
| Confidence monitor | 32" UHD on stand, downstage | 2 | Mirrored programme |
| Lyric / talkback monitor | 32" UHD, stage left | 1 | For MD |
| Streaming encoder | Blackmagic Web Presenter 4K | 1 | 1080p59.94, 8 Mbps H.264 to YouTube |
| Streaming backup | LiveU Solo PRO, bonded cellular | 1 | Auto-failover, 2× carrier SIM |
| Record | Blackmagic HyperDeck Studio 4K Pro × 2 | 2 | ProRes 422 HQ, A/B redundant |
| Genlock | Blackmagic Sync Generator, tri-level 1080p59.94 | 1 | **All devices genlocked [R]** |

**Content deadline [R]:** all playback content delivered T-48 h in 1408×880 native canvas, ProRes 422 HQ or DXV3. No H.264 for playback. Content conformed to 59.94 fps at ingest, not at showtime.

## B.7 Lighting

A 32-channel rock show gets a serious lighting rig. The plot below is a reference for a 2 400-cap room.

| Fixture | Type | Qty | Position | DMX Universe |
|---------|------|-----|----------|--------------|
| Chauvet Professional Rogue R2 Wash | Moving wash, 15× 40 W RGBW, 12-49° zoom | 12 | Mid truss (6), upstage truss (6) | U1 |
| Chauvet Professional Rogue R2 Spot | Moving spot, 260 W LED, 15° | 8 | FOH truss (4), mid truss (4) | U1 |
| Chauvet Professional Rogue R2X Beam | Moving beam, 132 W discharge, 2.5° | 8 | Upstage deck (4), mid truss (4) | U1 |
| Martin MAC Aura XB | Moving wash + aura, 550 W | 10 | Mid truss | U1 |
| Robe BMFL Spot | Followspot, 1700 W | 2 | FOH followspot chairs | U2 |
| Chauvet COLORdash Par-Quad 18 | LED par, RGBW | 16 | Upstage floor uplight (8), truss (8) | U2 |
| Chauvet COLORado Solo Batten 4 | LED batten, RGBW zoom | 8 | Upstage deck, cyc / wall wash | U2 |
| Chauvet STRIKE 4 | Blinder / audience, 4× 100 W warm white | 8 | FOH and mid truss, house-facing | U2 |
| ETC Source Four LED Series 3 Lustr | Ellipsoidal, 26° | 8 | FOH truss, key and specials | U2 |
| Chauvet Ovation E-260WW | Ellipsoidal, warm white 3000 K | 4 | Downstage key, podium specials | U2 |
| Chauvet Amhaze Whisper | Haze, water-based, low noise | 2 | SL and SR upstage | U3 |
| Look Solutions Unique 2.1 | Hazer, alt spec | 2 | Substitution for Amhaze | U3 |
| Antari W-715 | Fan, haze distribution | 2 | Upstage corners | U3 |
| MDG theONE | Fog / haze, CO2-driven | 1 | Upstage centre, effects only | U3 |
| Console | MA Lighting grandMA3 full-size | 1 | FOH lighting position | — |
| Console backup | grandMA3 light, tracking backup | 1 | Adjacent, session-joined | — |
| DMX gateway | Luminex GigaCore 10 + LumiNode 4 | 4 | Stage L, R, FOH, dimmer world | U1-U3 |
| Dimming / relay | ETC Sensor3 24× 2.4 kW rack | 1 | Dimmer world SL | U3 |
| Followspot comms | On the lighting intercom ring | 2 | — | — |

**Haze [A]:** confirm the venue permits water-based haze. The Eastern has a smoke management policy: haze is permitted provided detectors are isolated by the venue fire officer, in writing, before doors. No verbal isolation.

## B.8 Power

| Circuit | Amps | Voltage | Phase | Distro | Load Calc |
|---------|------|---------|-------|--------|-----------|
| **SERVICE** | 400 A | 120/208 V | 3φ wye + N + G | Camlock Series 16 to main distro, SL upstage | Total connected 86.0 kW → 86 000 / 360 = **238.9 A/leg**; /0.80 = 298.6 A req. → 400 A. Utilisation **74.7%** |
| A-1 Audio PA | 100 A | 120/208 V | 3φ | Motion Labs 100 A → 12× L5-20R at PA hangs | 24× LEOPARD @4.5 A = 108 A; 6× 900-LFC @8 A = 48 A; fills 16 A → 172 A ÷ 3 = **57.3 A/leg** (71.6% of 80 A) |
| A-2 Audio control | 30 A | 120/208 V | 3φ | Motion Labs 30 A → 6× L5-20R at FOH + monitor world | Consoles 8 A, drive rack 3 A, RF rack 3 A, processing 2 A = 16 A ÷ 3 = **5.3 A/leg**. Isolated ground [R] |
| A-3 Stage / backline | 30 A | 120 V | 1φ (Phase B only) | 8× L5-20R across deck | Guitar amps 2× 6 A, bass 8 A, keys 4 A, pedals 2 A = **24 A** = 2.88 kW (80% of 30 A) |
| L-1 Lighting main | 200 A | 120/208 V | 3φ wye | Motion Labs 200 A → 6× Socapex 19-pin + 12× L6-30 | Connected 32.0 kW → 32 000 / 360 = **88.9 A/leg**; /0.80 = 111 A req. → 200 A. Utilisation **55.6%** |
| L-2 Followspot | 20 A | 120 V | 1φ per spot | 2× L5-20R at spot chairs | 2× BMFL Spot @ 1900 W = 3800 W / 120 = **31.7 A** → 1 spot per 20 A circuit, 15.8 A each (79%) |
| V-1 LED wall | 60 A | 120/208 V | 3φ wye | Motion Labs 60 A → 8× L6-30 to wall PSU loops | 20 m² × 350 W/m² max = 7000 W → 7000 / 360 = **19.4 A/leg**; /0.80 = 24.3 A req. → 60 A |
| V-2 Video control | 60 A | 120/208 V | 3φ | Motion Labs 60 A → 10× L5-20R at V1, servers, racks | Servers 2000 W, switcher/racks 2000 W, cameras 600 W, decks 300 W = 4900 W → **13.6 A/leg** |
| V-3 Projection | 30 A | 208 V | 1φ | 2× L6-30R | Not used on this show (LED only) — kept as spare |
| C-1 Comms / network | 20 A | 120 V | 1φ | 4× L5-20R, UPS-backed | Intercom 2 A, switches 3 A, wireless BP charging 2 A = **7 A** |
| U-1 UPS critical | 20 A | 120 V | 1φ | APC SMT3000RM2U at FOH, 2700 W | Console 4 A, drive rack 3 A, primary media server 8 A = **15 A** = 75% of 20 A. Runtime at 1800 W ≈ 7 min |
| S-1 Shore / house | 20 A | 120 V | 1φ | House GPO, work light, tools | **Not for show equipment** |

**Phase balance:**
```
Leg A:  A-3 stage (24 A) + C-1 comms (7 A)              = 31 A
Leg B:  L-2 followspot (15.8 A) + U-1 UPS (15 A)        = 30.8 A
Leg C:  V-2 video leg (13.6 A) + spare (20 A)           = 33.6 A
Imbalance = (33.6 - 30.8) / 33.6 = 8.3%  -> acceptable, under 10%
```

**Voltage drop check, stage feeder:** 2/0 AWG copper, 3φ, 200 A, 45 m (147 ft). `Vd = (1.732 × 12.9 × 200 × 147) / 133 100 = 4.94 V` = **2.4% of 208 V**, inside the 3% target.

## B.9 Rigging

| Truss Section | Length | Load | Motor | Height |
|---------------|--------|------|-------|--------|
| FOH truss | 12.0 m Global Truss F34 (4× 3 m + 2 corner) | Truss 99 kg + 4× R2 Spot 128 kg + 4× S4 LED 44 kg + 4× STRIKE 4 44 kg + cable 40 kg = **355 kg** | 2× CM Lodestar Model L, 1 t | Trim 8.5 m |
| Mid truss | 12.0 m Global Truss F34 | Truss 99 kg + 6× R2 Wash 216 kg + 4× R2 Spot 128 kg + 10× MAC Aura XB 260 kg + cable 50 kg = **753 kg** | 3× CM Lodestar Model L, 1 t | Trim 8.5 m |
| Upstage truss | 10.0 m Global Truss F34 | Truss 83 kg + 6× R2 Wash 216 kg + 4× R2X Beam 100 kg + cable 35 kg = **434 kg** | 2× CM Lodestar Model L, 1 t | Trim 7.0 m |
| LED header truss | 8.0 m Global Truss F34 | Truss 67 kg + LED 80 panels × 8.0 kg = 640 kg + hanging bars 90 kg = **797 kg** | 3× CM Lodestar Model L, 1 t | Trim 6.5 m to top of wall |
| PA hang L | Meyer MG-LEOPARD grid | 12× LEOPARD @ 34.5 kg = 414 kg + grid 50 kg = **464 kg** | 1× CM Lodestar Model L, 1 t | Trim 7.5 m to top box |
| PA hang R | Meyer MG-LEOPARD grid | **464 kg** | 1× CM Lodestar Model L, 1 t | Trim 7.5 m |
| Sub flown L | Meyer 900-LFC frame | 3× 900-LFC @ 98 kg = 294 kg + frame 40 kg = **334 kg** | 1× CM Lodestar Model L, 1 t | Trim 9.0 m, behind PA |
| Sub flown R | Meyer 900-LFC frame | **334 kg** | 1× CM Lodestar Model L, 1 t | Trim 9.0 m |
| **Totals** | — | **Suspended load 3935 kg (3.9 t)** | **14 motors** (14× 1 t) | — |

**Pyro and rigger certification [R]:** the tour carries cold-spark fountains and a confetti drop on the encore. The rigger is **ETCP Arena** certified with **pyrotechnic permit** for the tour (jurisdiction: State of Georgia Pyrotechnic Operator License, current). The venue requires a copy of the licence on file before load-in. No pyrotechnics operator on site, no pyro. The cold-spark units are Galaxis G-Flame X-FIRE units, four total, rigged to the mid truss on dedicated 1 t points.

## B.10 Backline

| Item | Spec | Qty | Provided By |
|------|------|-----|-------------|
| Drum kit | DW Collector's Series Maple: 22"×18" kick, 10"×8" and 12"×9" rack toms, 16"×16" floor | 1 | RENT |
| Snare | Ludwig Black Beauty 14"×6.5" | 1 | ART |
| Snare, backup | Yamaha Recording Custom 14"×5.5" | 1 | RENT |
| Cymbals | Zildjian K Custom: 14" hats, 16"/18" crash, 21" ride | 1 set | ART |
| Drum hardware | DW 9000 series: hi-hat stand, 3× boom, snare stand, throne | 1 set | RENT |
| Kick pedal | DW 9000 single | 1 | ART |
| Drum rug | 2.4 m × 2.4 m, non-slip, taped and marked | 1 | PROD |
| Bass head | Ampeg SVT-4PRO, 1200 W | 1 | RENT |
| Bass cab | Ampeg SVT-810E, 8×10", 800 W, 4 Ω | 1 | RENT |
| Bass head, backup | Ampeg SVT-3PRO | 1 | RENT |
| Guitar amp SL | Fender Twin Reverb '65 reissue, 85 W 2×12" | 1 | RENT |
| Guitar amp SR | Vox AC30C2, 30 W 2×12" | 1 | RENT |
| Guitar amp, backup | Marshall JCM800 2203 head + 1960A 4×12" cab | 1 | RENT |
| Guitar amp stand | Amp lift / tilt stand | 3 | PROD |
| Keyboard | Nord Stage 4 Compact 73 | 1 | ART |
| Keyboard, second tier | Yamaha Montage M8x | 1 | RENT |
| Keyboard stand | K&M Spider Pro, 2-tier | 1 | RENT |
| Keyboard bench | Adjustable, padded | 1 | RENT |
| Acoustic guitar | Taylor 814ce with ES2 electronics | 1 | ART |
| Guitar stands | Hercules GS414B tilt-back | 6 | PROD |
| Guitar tech station | Table, task light, tuner, string winder, 20 A power | 1 | PROD |
| DI boxes | Radial J48 (active) ×4, JDI (passive) ×2, ProD2 ×6, ProAV2 ×2 | 14 | PROD |
| Instrument cable | 6 m and 10 m, Mogami / Canare, tested | 20 | PROD |
| Power strips, stage | Furman SS-6B, 15 A, on Phase B only | 6 | PROD |
| Music stands | Manhasset #48 with LED clip light | 6 | PROD |
| Riser — drums | 2.4 × 2.4 m × 0.4 m, carpeted, skirted | 1 | PROD |
| Riser — keys | 2.4 × 1.8 m × 0.2 m, carpeted, skirted | 1 | PROD |
| Riser stairs | With handrail, both risers | 2 | PROD |
| Towels, black | Fresh, per show | 12 | VEN |
| Water, still | 500 ml, room temperature, 6 per performer per show | 36 | VEN |
| Ear plugs | Etymotic ER-20XS for all crew near PA | 30 | PROD |
| In-ear moulds | Artist custom moulds | 1 set | ART |
| In-ear spares | Universal-fit Shure SE425 | 6 pairs | PROD |
| Spare batteries | AA for Axient, 9 V for active DI, all fresh | 60 | PROD |

## B.11 Crew

| Role | Count | Call | Notes |
|------|-------|------|-------|
| Tour Production Manager | 1 | 06:00 | Owns the day |
| Head Rigger (ETCP Arena) | 1 | 06:30 | First up |
| Rigger (ETCP) | 2 | 06:30 | Up-riggers, high steel |
| Pyro Op (with permit) | 1 | 16:00 | Cold spark and confetti, on permit |
| Head Carpenter / Deck | 1 | 07:00 | Deck, risers, marks |
| Stagehand — load-in | 8 | 07:00 | Released after audio/lighting hang |
| Audio A1 (FOH) | 1 | 08:00 | FOH mix, system tune, RF |
| Audio A2 (Monitors) | 1 | 08:00 | Monitor world, IEM |
| Audio A3 (Stage / RF tech) | 1 | 08:00 | Patch, mic plot, batteries |
| Systems Tech | 1 | 07:30 | PA build, prediction, Dante network |
| Lighting Designer | 1 | 09:00 | Console, focus, cue build |
| Lighting Director | 1 | 09:00 | Show op where LD does not |
| Lighting Tech | 3 | 07:00 | Hang, address, focus |
| Followspot Operator | 2 | 17:00 | Rehearsal onward |
| Video Director | 1 | 09:00 | Switcher, cameras |
| Video Engineer | 1 | 08:00 | Signal path, genlock, record, stream |
| LED Tech | 2 | 07:30 | Wall build, mapping, spares |
| Media Server Operator | 1 | 10:00 | Content load, backup |
| Camera Operator | 3 | 15:00 | Rehearsal onward |
| Streaming Operator | 1 | 12:00 | Encoder, bitrate, failover |
| Backline Tech — drums | 1 | 10:00 | ART crew where touring |
| Backline Tech — guitars | 1 | 10:00 | Tuning, changes, pedal boards |
| Stage Manager | 1 | 09:00 | Calls the show |
| Show Caller | 1 | 12:00 | Merges with SM |
| Wardrobe | 1 | 14:00 | Costume changes |
| Stagehand — load-out | 10 | Show end | Released on truck doors closed |
| Loader | 4 | 07:00 and show end | Truck only |
| Licensed Electrician | 1 | 06:30 | Tie-in, disconnect [R] |
| Local Safety / Fire Marshal liaison | 1 | Per venue | Haze isolation, egress sign-off |

## B.12 Load-in schedule

See §11.1 master load-in for full timeline. Build summary:

| Window | Activity | Crew count |
|--------|----------|------------|
| 06:00-08:00 | Tie-in, truss ground assembly, truck push, distro energise | 15 |
| 08:00-12:00 | Audio, lighting, video, LED wall build, PA fly | 28 |
| 12:00-13:00 | Meal break | All |
| 13:00-15:00 | Backline, monitors, mic patch, line check | 24 |
| 15:00-17:00 | System tune, video shading, lighting focus | 20 |
| 17:00-19:00 | Rehearsal, dinner break | All |
| 19:00 | Doors | House |
| 20:30 | Show | All |
| 22:30 | Load-out | 16 |
| 01:30 | Truck doors closed | 4 |

---

# Appendix C — Multi-Track Conference (24 ch, 3 breakouts, streaming)

**Event:** Helios Cloud Summit 2026, Day 1
**Venue:** Moscone West, Level 3, San Francisco CA (3 conference rooms, 1 main hall, 1 200 cap)
**Date:** 9 June 2026, doors 08:00, main programme 09:00-17:00
**Rider revision:** v1.0
**Issued by:** Conference AV Manager
**Advance deadline:** T-21 days (19 May 2026)
**Final revision lock:** T-7 days (2 June 2026)

## C.1 Room topology

Three independent rooms plus the main hall, all fed from a central audio/video core that records, streams, and routes between rooms.

| Room | Capacity | Function | Audio matrix out |
|------|----------|----------|------------------|
| Main Hall (Level 3, Room 3001) | 1 200 | Keynotes, general session | Matrix out 1-2, video to 1× record + 1× stream |
| Breakout A (Room 3004) | 250 | Track 1: Platform | Matrix out 3-4, video to 1× record + 1× IMAG in main |
| Breakout B (Room 3006) | 250 | Track 2: AI/ML | Matrix out 5-6, video to 1× record + 1× IMAG in main |
| Breakout C (Room 3008) | 150 | Track 3: DevOps | Matrix out 7-8, video to 1× record |
| Overflow (Level 3 foyer) | 200 | Watching main programme on screen | Fed from main hall matrix, no mics |

**Matrix routing [R]:** all four rooms are mixed on a central **DiGiCo Quantum 338** at the AV core, with a 16×16 Dante matrix. Any room can be routed to any other room, the record feed, the stream feed, the IMAG in the main hall, and the overflow foyer. Routes are preset and locked at the tech advance; day-of changes go through the AV manager.

## C.2 Main Hall input list — 24 channels

| Ch# | Source | Mic Model | Stand | Phantom | Insert | Notes |
|-----|--------|-----------|-------|---------|--------|-------|
| 1 | Lectern L | Shure MX418/C 18" gooseneck | DT | Y | Comp + gate | On lectern, redundant pair one fader |
| 2 | Lectern R | Shure MX418/C 18" gooseneck | DT | Y | Comp + gate | |
| 3 | Handheld 1 | Shure ULXD2/SM58 | TB | N | Comp + DeEsser | Q&A roamer, house left, RF ch A1 |
| 4 | Handheld 2 | Shure ULXD2/SM58 | TB | N | Comp + DeEsser | Q&A roamer, house right, RF ch A2 |
| 5 | Lav 1 | Shure ULXD1 + DPA 4066 | — | — | Comp + DeEsser | Keynote A, headworn |
| 6 | Lav 2 | Shure ULXD1 + DPA 6060 | — | — | Comp + DeEsser | Keynote B, subminiature |
| 7 | Lav 3 | Shure ULXD1 + DPA 6060 | — | — | Comp + DeEsser | Keynote C |
| 8 | Lav 4 (spare) | Shure ULXD1 + DPA 6060 | — | — | Comp + DeEsser | Charged, cued |
| 9 | Panel table 1 | Shure MX392/C boundary | DT | Y | Gate | 2 seats per mic, 4 mics per panel of 8 seats |
| 10 | Panel table 2 | Shure MX392/C boundary | DT | Y | Gate | |
| 11 | Panel table 3 | Shure MX392/C boundary | DT | Y | Gate | |
| 12 | Panel table 4 | Shure MX392/C boundary | DT | Y | Gate | |
| 13 | Panel table 5 | Shure MX392/C boundary | DT | Y | Gate | |
| 14 | Panel table 6 | Shure MX392/C boundary | DT | Y | Gate | |
| 15 | Playback L | Radial ProAV2 | — | N | — | Show laptop, ProRes 422 HQ |
| 16 | Playback R | Radial ProAV2 | — | N | — | Linked to Ch15 |
| 17 | Video / VTR L | Radial ProD2 | — | N | — | From switcher, programme audio |
| 18 | Video / VTR R | Radial ProD2 | — | N | — | |
| 19 | Remote caller 1 | Radial ProAV1 | — | N | Comp + AGC | Teams/Zoom, **mix-minus to bus 7** |
| 20 | Remote caller 2 | Radial ProAV1 | — | N | Comp + AGC | Second remote, **mix-minus to bus 8** |
| 21 | Audience Q&A 1 | Shure MX412 gooseneck | DT | Y | Comp + gate | Wired aisle mic, dedicated to Q&A |
| 22 | Audience Q&A 2 | Shure MX412 gooseneck | DT | Y | Comp + gate | Wired aisle mic |
| 23 | Walk-in music | Radial ProAV2 | — | N | — | Dedicated iPad |
| 24 | BGM / intermission | Radial ProAV2 | — | N | — | Linked to Ch23, separate playlist |

**Stand summary main hall:** `DT × 11, TB × 2`. Wireless: 2× ULXD2 handheld + 4× ULXD1 bodypack = **6 RF channels main hall** + 6 per breakout room = 24 RF channels total in the venue. Coordination across rooms is critical — see §C.6.

**Breakout room input list (each of A, B, C):** 8 channels per room, 24 channels total. See §C.3 for the breakout channel map.

## C.3 Breakout room channel map

Each breakout room has its own 8-channel input list. Channels 25-32 on the central console (Quantum 338) handle Breakout A, 33-40 handle B, 41-48 handle C. The breakout rooms are mixed from the central console via Dante, not from local consoles.

| Ch# | Source | Mic Model | Stand | Phantom | Insert | Notes |
|-----|--------|-----------|-------|---------|--------|-------|
| 25 / 33 / 41 | Lectern | Shure MX418/C 18" | DT | Y | Comp + gate | Per breakout room |
| 26 / 34 / 42 | Handheld | Shure ULXD2/SM58 | TB | N | Comp + DeEsser | Q&A, per room |
| 27 / 35 / 43 | Lav 1 | Shure ULXD1 + DPA 4066 | — | — | Comp + DeEsser | Per room |
| 28 / 36 / 44 | Lav 2 (spare) | Shure ULXD1 + DPA 6060 | — | — | Comp + DeEsser | Per room |
| 29 / 37 / 45 | Panel 1 | Shure MX392/C | DT | Y | Gate | Per room |
| 30 / 38 / 46 | Panel 2 | Shure MX392/C | DT | Y | Gate | Per room |
| 31 / 39 / 47 | Playback L | Radial ProAV2 | — | N | — | Per room |
| 32 / 40 / 48 | Playback R | Radial ProAV2 | — | N | — | Per room |

**Mix-minus per breakout [R]:** each room's remote caller (if any) gets a mix-minus bus that excludes only that room's caller. Without it, remote presenters hear themselves delayed and stop talking. Tested at the morning rehearsal.

## C.4 Output list — central matrix

The central DiGiCo Quantum 338 routes 16×16 to the following destinations:

| Out# | Destination | Signal Type | Notes |
|------|-------------|-------------|-------|
| 1 | Main hall PA L | Dante | Meyer LINA line array L |
| 2 | Main hall PA R | Dante | Meyer LINA line array R |
| 3 | Main hall sub L | Dante | Meyer 750-LFC, aux-fed |
| 4 | Main hall sub R | Dante | Meyer 750-LFC, aux-fed |
| 5 | Main hall front fill | Dante | Meyer UPM-1P, 4 boxes |
| 6 | Main hall delay ring | Dante | Meyer LINA delay, 6 boxes |
| 7 | Breakout A PA L | Dante | Self-powered, room A |
| 8 | Breakout A PA R | Dante | |
| 9 | Breakout B PA L | Dante | |
| 10 | Breakout B PA R | Dante | |
| 11 | Breakout C PA L | Dante | |
| 12 | Breakout C PA R | Dante | |
| 13 | Record (all 4 rooms) | Dante | ProRes 422 HQ, 4 iso tracks + 1 mix |
| 14 | Stream (main hall) | Dante | To Blackmagic Web Presenter 4K |
| 15 | Stream (overflow) | Dante | To YouTube secondary channel |
| 16 | Press mult | Analogue | 4× XLR passive split |

**Aux-fed subs [R]:** main hall subs on a dedicated aux bus, not matrixed off L/R. Subs do not pick up handheld wireless content. Speech intelligibility in the bass region is the goal, not chest-thump.

**Record feed is pre-fader, pre-EQ, post-gain [R].** FOH fader moves do not damage the archive. Record runs from the morning rehearsal through the end of the closing session, with a separate file per session boundary.

## C.5 Console and DSP

| Item | Make/Model | Qty | Position | Notes |
|------|------------|-----|----------|-------|
| FOH console (central) | DiGiCo Quantum 338 | 1 | AV core, Level 3 comms room | 128 in / 64 out, 24 mix buses, 16×16 matrix |
| Console backup | DiGiCo SD12 | 1 | AV core, adjacent | Tracking backup, session-joined |
| Stage rack | DiGiCo MQ-Rack | 4 | One per room | 32 in / 16 out, Dante |
| Wireless — main | Shure ULXD4Q × 2 (4 receivers each) | 2 | Main hall | 8 channels, WWB6 networked |
| Wireless — A | Shure ULXD4Q × 2 | 2 | Breakout A | 8 channels |
| Wireless — B | Shure ULXD4Q × 2 | 2 | Breakout B | 8 channels |
| Wireless — C | Shure ULXD4Q × 2 | 2 | Breakout C | 8 channels |
| Antenna dist | Shure UA844+SWB × 4 | 4 | Per room | 4-way active antenna distribution |
| Antennas | Shure UA874 active paddle | 8 | 2 per room, 2 m above deck | Line-of-sight to presenter positions |
| IEM (if any) | Shure PSM300 × 2 | 2 | Per room, presenters | Not in base spec; add for translators |
| Record | Blackmagic HyperDeck Studio 4K Pro × 2 | 2 | AV core | ProRes 422 HQ, A/B redundant |
| Multitrack record | Sound Devices MixPre-10 II | 1 | AV core, ISO capture | 12-channel backup, redundant to HyperDeck |
| Network switch | Luminex GigaCore 10 | 4 | AV core, FOH, each breakout | Dante and control on separate VLANs |

## C.6 RF coordination

24 RF channels across 4 rooms in one venue is a coordination problem, not a "set them all up and hope" problem.

| Item | Requirement |
|------|-------------|
| Total RF channels | 24 active (8 main + 6× A, 6× B, 6× C; some spares) |
| Coordination tool | Shure Wireless Workbench 6, scan on site, full frequency re-coordination per room |
| Band | 470-608 MHz + 614-616 MHz (US) |
| Intermod | Third-order calculated clear for all 24 active channels |
| Inter-room isolation | Minimum 2 m vertical and 5 m horizontal between antenna pairs in adjacent rooms |
| Spare channels | 4 spare coordinated (1 per room) on standby |
| Battery rotation | Fresh or freshly charged at every session boundary, logged |

**Walkthrough test [A]:** at the morning rehearsal, every presenter walks the room with their bodypack on. Dropouts are caused by body block, so the test catches what a static RF plot does not. The Shure UA874 paddle antenna's null toward the floor helps; bodypack diversity with a secondary antenna on the receiver is the only reliable fix for body block in a high-density room.

## C.7 PA design per room

The conference is mixed in a 1 200-cap main hall and three 150-250 cap breakouts. The PA design is appropriate to the room, not a one-size-fits-all.

### Main hall

| Position | Model | Qty | Mount | Notes |
|----------|-------|-----|-------|-------|
| Main hang L | Meyer Sound LINA | 8 | Flown, MG-LINA grid | 100° × 50° per box, very compact line array |
| Main hang R | Meyer Sound LINA | 8 | Flown | Mirror of L |
| Sub L | Meyer Sound 750-LFC | 2 | Flown, cardioid | Aux-fed, video playback only |
| Sub R | Meyer Sound 750-LFC | 2 | Flown | |
| Front fill | Meyer Sound UPM-1P | 4 | Stage lip | Delay +3.8 ms |
| Delay ring | Meyer Sound LINA | 6 | House-rigged, 18 m from downstage | +12 ms, -3 dB from mains |
| System processor | Meyer Sound Galileo GALAXY 408 | 1 | At FOH | EQ, delay, optimisation |
| Drive | Meyer Sound MDM-832 | 2 | Amp world | AES3 distribution |

**Tuning target [R]:** SPL 95-98 dB(A) slow at FOH during applause, 88-92 dB(A) during speech. STI 0.55 minimum across 90% of seats, 0.60+ in 70% of seats. Subs muted for speech; on a separate bus for video playback and walk-in music.

### Breakout rooms

| Room | Speaker | Sub | Notes |
|------|---------|-----|-------|
| A (250 cap) | 2× Meyer UPQ-1P self-powered | 2× Meyer USW-210P ground-stacked | Mounted on stands, no flown rig |
| B (250 cap) | 2× Meyer UPQ-1P self-powered | 2× Meyer USW-210P | Same as A |
| C (150 cap) | 2× Meyer UPM-1P self-powered | 1× Meyer USW-210P | Smaller, no flown rig |

All breakouts are self-powered, ground-stacked. No motors, no rigging crew, no truss. Build time per room is under 90 minutes with 2× A2 stage audio techs.

## C.8 Video

| Item | Spec | Qty | Notes |
|------|------|-----|-------|
| Main hall projector | Panasonic PT-RZ21K, 20 000 lm, laser | 2 | Centre and confidence screen |
| Main hall confidence | 4.9 m × 2.7 m Da-Lite Fast-Fold Deluxe | 2 | Rear projection, ET-DLE060 |
| IMAG in main | 2× 4.0 m × 2.25 m LED panels flown with PA | 2 | Show breakout rooms during general session |
| Breakout projector | Panasonic PT-RZ890, 8 500 lm, laser | 3 | One per breakout room |
| Breakout screen | 3.0 m × 1.7 m Da-Lite Fast-Fold | 3 | 16:9, front projection |
| Switcher (central) | Ross Carbonite Ultra 60 | 1 | 2 M/E, 24 inputs, 12G-SDI |
| Switcher (per breakout) | Blackmagic ATEM Mini Extreme ISO | 3 | 8 inputs, ISO record to USB |
| Camera (main) | Sony HXC-FB80 with 20× box lens | 3 | FOH long centre, SL handheld, SR handheld |
| Camera (per breakout) | Sony HXC-FB80 | 1 per room | 3 total, fixed mount |
| Camera control | Sony RCP-1500 | 3 | At V1 in main hall |
| Multiview | 2× 32" 4K UHD + 1× 55" programme | 3 | V1 + show caller |
| Confidence monitor | 24" 1080p on lectern | 4 | One per room |
| Streaming encoder (main) | Blackmagic Web Presenter 4K | 1 | 1080p59.94, 6 Mbps H.264 to YouTube Live |
| Streaming encoder (breakouts) | Blackmagic Web Presenter HD | 3 | One per breakout, 1080p59.94 |
| Streaming backup | LiveU Solo PRO × 4 | 4 | Bonded cellular, 2× carrier SIM each |
| Record (main) | HyperDeck Studio 4K Pro × 2 | 2 | ProRes 422 HQ, A/B redundant |
| Record (per breakout) | ATEM Mini ISO records to USB | 3 | Backup ISO, local copy |
| Genlock | Blackmagic Sync Generator, tri-level 1080p59.94 | 1 | **All devices genlocked [R]** |

**Streaming to YouTube [A]:** the conference streams the main hall to a single YouTube Live event, with breakout rooms streamed to separate YouTube Live events on the same channel. The chat is moderated by the AV core. OBS 30 is the scene compositor for the main feed, with a multi-view of presenter, slides, and lower-third.

**Audience Q&A [A]:** the platform Slido runs the Q&A queue. The Q&A moderator advances questions to the moderator, the moderator hands off to the speaker, and the speaker answers. Wired aisle mics (Ch21, Ch22) walk to the asker, so a soft-spoken audience member does not need a handheld.

## C.9 Lighting

Conference lighting is even, camera-friendly, and bright enough for slides. It is not a show.

| Fixture | Type | Qty | Position | DMX Universe |
|---------|------|-----|----------|--------------|
| ETC Source Four LED Series 3 Lustr | Ellipsoidal, 26° or 36° | 16 | Main hall FOH truss (12), breakouts (4) | U1 |
| ETC ColorSource Spot V | LED spot, RGBW | 8 | Main hall FOH truss, specials | U1 |
| Chauvet COLORdash Par-Quad 18 | LED par, RGBW | 24 | All rooms, stage wash | U1 |
| Chauvet Ovation E-260WW | Warm white ellipsoidal | 12 | Lectern key, panel key (4 per room) | U2 |
| Chauvet Ovation F-915VW | Fresnel, variable white | 12 | Stage wash, soft | U2 |
| House light | Relay on architectural dimmer | 4 | Per room | U2 |
| Console (main) | MA Lighting grandMA3 light | 1 | Main hall FOH | — |
| Console (per breakout) | grandMA3 onPC command wing | 3 | One per breakout | — |
| DMX node | Luminex LumiNode 4 | 4 | Per room | U1-U2 |

**House light integration [R]:** architectural lighting is on a relay or DMX gate controlled from the FOH console. A 30-second fade to "show" before the keynote, and a 5-second bump to 100% on a fire alarm cue. The integration is tested at load-in and again at the morning rehearsal.

## C.10 Power

| Circuit | Amps | Voltage | Phase | Distro | Load Calc |
|---------|------|---------|-------|--------|-----------|
| **SERVICE (main)** | 200 A | 120/208 V | 3φ wye | Camlock to main distro, main hall SL | Main hall total 18.0 kW → 18000 / 360 = **50.0 A/leg**; /0.80 = 62.5 A req. → 200 A. Utilisation **31.3%** |
| A-1 Main audio | 30 A | 120/208 V | 3φ | Motion Labs 30 A → 6× L5-20R at FOH | Consoles 6 A, drive 4 A, RF 4 A, processing 2 A = 16 A ÷ 3 = **5.3 A/leg**. Isolated ground [R] |
| A-2 Breakout audio | 20 A × 3 | 120 V | 1φ | One per breakout, 4× L5-20R each | Per breakout 6 A = **30 A total across 3 rooms** |
| A-3 Q&A aisle mics | 20 A | 120 V | 1φ | 4× L5-20R at Q&A station | 2× MX412 base + receiver = **1 A** |
| V-1 Main projection | 30 A × 2 | 208 V | 1φ per projector | 2× L6-30R | 2× PT-RZ21K @ 2100 W = 4200 W / 208 = **20.2 A** → 1 per 30 A circuit |
| V-2 Breakout projection | 20 A × 3 | 120 V | 1φ | 1× L5-20R per room | 3× PT-RZ890 @ 660 W = 1980 W / 120 = **16.5 A** → 1 per 20 A circuit, 5.5 A each |
| V-3 Video control (main) | 20 A | 120 V | 1φ | 6× L5-20R at V1 | Servers 2 A, switcher 2 A, cameras 1.5 A, decks 1 A = **6.5 A** |
| V-4 Video control (breakouts) | 20 A × 3 | 120 V | 1φ | 1× L5-20R per room | Per breakout 2 A |
| L-1 Main lighting | 60 A | 120/208 V | 3φ | Motion Labs 60 A → 6× Socapex 19-pin | Main hall 7.2 kW → 7200 / 360 = **20.0 A/leg**; /0.80 = 25.0 A req. → 60 A. Utilisation **41.7%** |
| L-2 Breakout lighting | 20 A × 3 | 120 V | 1φ | 1× L5-20R per room | Per breakout 1.5 kW / 120 = **12.5 A** |
| C-1 Comms / network | 30 A | 120/208 V | 3φ | Motion Labs 30 A → 6× L5-20R, UPS-backed | Intercom 2 A, switches 5 A, RF charging 2 A, AV core 4 A = **13 A ÷ 3 = 4.3 A/leg** |
| U-1 UPS critical | 30 A | 120 V | 1φ | APC SRT3000XLI at AV core, 2700 W | Central console 4 A, drive rack 4 A, both record decks 4 A, both media servers 8 A = **20 A** = 67% of 30 A. Runtime at 2000 W ≈ 8 min |
| S-1 Shore / house | 20 A × 4 | 120 V | 1φ | House GPO, work light, tools | **Not for show equipment** |

**Phase balance main service:**
```
Leg A:  A-1 audio (5.3) + V-3 video (6.5) + A-3 Q&A (1) + 1/3 V-1 (6.7) = 19.5 A
Leg B:  1/3 V-1 (6.7) + 1/3 L-1 (20/3 = 6.7) + 1/3 C-1 (4.3)         = 17.7 A
Leg C:  1/3 V-1 (6.7) + 1/3 L-1 (6.7) + U-1 UPS (20)                  = 33.4 A
Imbalance = (33.4 - 17.7) / 33.4 = 47%  -> re-balance, split U-1 across all 3 legs
```

**Re-balance on the advance.** A 47% imbalance is too high. The UPS is a single-phase load; either move it to a smaller UPS on Leg B, or step it up to a 3-phase UPS at the AV core. The latter is the right answer for a 1 200-cap conference.

## C.11 Rigging

| Item | Spec | Qty | Notes |
|------|------|-----|-------|
| Main hall FOH truss | 12.0 m Global Truss F34, house-rigged | 1 | Trim 5.5 m, 8× S4 LED + 8× ColorSource |
| Main hall IMAG truss | 8.0 m Global Truss F34, house-rigged | 1 | Trim 4.5 m, 2× LED IMAG panels |
| Breakout truss A | 6.0 m F34, house-rigged | 1 | Trim 3.5 m, 4× S4 LED |
| Breakout truss B | 6.0 m F34, house-rigged | 1 | Trim 3.5 m, 4× S4 LED |
| Breakout truss C | 4.0 m F34, house-rigged | 1 | Trim 3.0 m, 4× S4 LED |
| Rigging personnel | ETCP rigger for any non-house point | 1 | **Not required if all points house-rigged [A]** |
| Rigging plot | Production submits at T-14 days | 1 | Venue confirms point capacities in writing |
| Design factor | 5:1 on all steel, synthetics per manufacturer | — | [R] |
| Safeties | Secondary steel on every fixture | — | [R] |
| Hard hats | In the fly zone during any overhead work | — | [R] |

## C.12 Backline / fixtures

| Item | Spec | Qty | Provided By |
|------|------|-----|-------------|
| Lectern (main) | Custom, locking front panel, gooseneck light, confidence 24", cable cubby | 1 | RENT |
| Lectern (breakouts) | Sloped top, locking, confidence 22" | 3 | VEN |
| Lectern mic | Shure MX418/C 18" gooseneck | 8 (2 main + 6 breakouts) | PROD |
| Panel table (main) | 4.0 m × 0.8 m, skirted, cable management | 1 (8 seats) | VEN |
| Panel table (breakouts) | 2.4 m × 0.6 m, skirted | 3 (4 seats each) | VEN |
| Panel mic | Shure MX392/C boundary | 12 (6 main + 2 per breakout × 3) | PROD |
| Wired Q&A mic | Shure MX412 gooseneck on stand | 2 | PROD |
| Aisle mic cable | 30 m, XLR, on cable reel | 2 | PROD |
| Confidence monitor | 24" 1080p, HDMI in, floor stand | 4 (1 per room) | RENT |
| Music stand | Manhasset #48 with LED clip light | 4 (1 per room) | RENT |
| Slido Q&A kiosk | iPad Pro 12.9" on stand, with charger | 4 (1 per room) | RENT |
| Presenter confidence | 24" 1080p confidence monitor per lectern | 4 | RENT |
| Water, still | 500 ml, room temp, 4 per speaker | 80 (over 20 speakers) | VEN |
| Water, sparkling | 500 ml, 2 per speaker | 40 | VEN |
| Coffee service | At lectern, fresh, replaced hourly | 4 sets | VEN |
| Headset mic spares | DPA 4066, 6060 (full colour kit) | 2 of each | PROD |
| Lav body pack spares | Shure ULXD1, charged, paired | 4 | PROD |
| Handheld spares | Shure ULXD2/SM58, charged, paired | 2 | PROD |
| Spare batteries | AA, fresh, in dispenser | 80 | PROD |

## C.13 Crew

| Role | Count | Call | Notes |
|------|-------|------|-------|
| Conference AV Manager | 1 | 05:00 | Owns the day across all rooms |
| Audio A1 (FOH central) | 1 | 05:00 | At AV core, mixes all 4 rooms |
| Audio A2 (main hall) | 1 | 05:00 | Stage, lav check, monitor presenter needs |
| Audio A3 (breakouts) | 3 | 06:00 | One per breakout room |
| Video Director (main) | 1 | 06:00 | Switcher, camera shading |
| Video Engineer (main) | 1 | 06:00 | Signal path, genlock, record, stream |
| Video Tech (breakouts) | 3 | 07:00 | One per breakout room |
| Streaming Operator (main) | 1 | 07:00 | YouTube RTMP, OBS, bitrate, failover |
| Streaming Operator (breakouts) | 1 | 08:00 | All 3 breakouts, sequential |
| Lighting Designer | 1 | 06:00 | Console, focus, cue build |
| Lighting Tech (main) | 2 | 06:00 | Hang, focus |
| Lighting Tech (breakouts) | 3 | 07:00 | One per breakout |
| Show Caller (main) | 1 | 08:00 | Calls the run-of-show |
| Show Caller (breakouts) | 3 | 08:00 | One per breakout |
| Stagehand — load-in/out | 8 | 04:00 and 17:00 | One shift |
| Loader | 2 | 04:00 and 17:00 | Truck only |
| Licensed Electrician | 1 | 05:00 | Tie-in, disconnect [R] |
| Network Engineer | 1 | 04:00 | Dante network, switches, VLANs |
| Local Safety / Fire Marshal liaison | 1 | Per venue | Egress sign-off |

## C.14 Load-in schedule

| Time (T-relative to 09:00 doors) | Activity | Crew | Equipment |
|-----------------------------------|----------|------|-----------|
| T-5 h (04:00) | Truck push, distro, AV core rack build | 8× SH, 2× LOADER, ELEC, NET | Camlock, network switches, racks |
| T-4 h (05:00) | Audio crew call, RF scan, antenna deployment | A1, A2, A3 ×3 | Shure WWB6, ULXD4Q receivers |
| T-4 h (05:00) | Main hall FOH position build, line array ground assembly | A1, audio crew | Meyer LINA frames, MDM-832 |
| T-3 h (06:00) | Lighting hang, video path, switcher power-up | LT ×2, VE, V1 | grandMA3, Carbonite, HyperDecks |
| T-2.5 h (06:30) | PA fly, sub fly, delay ring deployment | A1, audio crew | Lodestar motors, LINA grid |
| T-2 h (07:00) | Breakout room builds start, in parallel | A3 ×3, LT ×3, VT ×3 | All self-powered speakers, 4 S4 LED per room |
| T-1.5 h (07:30) | System tune main hall, line check, lav check | A1, A2 | Smaart, RF coordination across all 24 channels |
| T-1 h (08:00) | Streaming test, YouTube RTMP, OBS scene test, OBS failover | STREAM ×2, VE | Web Presenter 4K, LiveU Solo PRO |
| T-1 h (08:00) | Walk-in music on, hearing loop test | A1 | Loop receiver, lobby feed |
| T-0 (09:00) | Doors, general session begins | ALL | All systems live |
| 12:00-13:00 | Lunch break, room reset for breakouts | SH ×4 | Reset rooms, swap mics if needed |
| 13:00-17:00 | Breakouts run in parallel, streamed | A1, A3 ×3, STREAM | Central console mixes all |
| 17:00 | Sessions end, all rooms close | ALL | — |
| T+0.5 h (17:30) | Load-out begins | 8× SH, 2× LOADER | Cases, cable coilers |
| T+2 h (19:00) | Distro de-energised, tie-in removed | ELEC | Lock-out/tag-out |
| T+3 h (20:00) | Truck doors closed, AV core packed | 4× SH, LOADER | Final pack |

---

<!-- end of file -->
