# WING Series Console - Comprehensive Knowledge Base
**Firmware Version:** 3.1
**Models:** WING, WING COMPACT, WING RACK
**Date:** October 20, 2025

This document is a deeply structured, comprehensive knowledge base extracted from the WING User Manual. It is designed to serve as an optimal training and reference document for AI models (like Claude) to understand the architecture, routing, processing, effects, and operational paradigms of the Behringer WING digital mixing console ecosystem.

---

## 1. System Architecture: Sources, Channels, Buses, and Outputs

The WING console introduces a flexible routing paradigm that separates physical/digital inputs ("Sources") from processing channels.

### 1.1 Sources
Sources represent the raw audio inputs. They carry properties such as Name, Icon, Color, Gain, Mute, Phantom Power (+48V), Phase Inversion, and Configuration (Mono, Stereo, Mid/Side). 
*   **Stereo/Mid-Side natively:** Any 48 channels can process mono, stereo, or mid/side without needing to link two adjacent channels. Mid/Side is decoded into standard stereo before processing.

**External Source Groups:**
*   **Local In:** On-board preamps (8 on WING, 24 on COMPACT/RACK).
*   **Aux In:** 8 TRS line-level inputs (WING only).
*   **AES/EBU:** 2 channels.
*   **AES50 A, B, and C:** 48 channels per port.
*   **StageConnect:** Up to 32 channels.
*   **USB Audio:** 48 channels via USB 2.0 interface.
*   **Expansion Card:** 64 channels (WING-LIVE SD card recorder by default).
*   **Internal Module:** 64 channels (optional Waves SoundGrid or Dante module).
*   **USB Player:** 4 channels (front panel USB flash drive).

**Internal Sources:**
*   **Bus / Main / Matrix:** Any output bus can be routed back as an input source.
*   **Oscillators:** 2 independent generators (Sine, Pink Noise, White Noise).
*   **User Signals (24):** Mono copies of any of the 40 inputs, 8 Auxes, 16 Buses, 8 Matrices, or 4 Mains. Can be tapped pre- or post-fader. Two adjacent User Signals can be grouped into a Stereo/MS source.
*   **User Patches (32):** Copies of external digital/analog sources. Allows combining non-adjacent signals or signals from different groups into Stereo/MS configurations.

### 1.2 Processing Channels
*   **40 Input Channels:** Feature full processing (EQ, Gate, Comp, 2x Inserts). Each channel accommodates a **MAIN** and an **ALT** source, allowing inline-console-style switching.
*   **8 Aux Channels:** Reduced processing but can still process mono/stereo signals. Have MAIN/ALT source switching.

### 1.3 Buses and Outputs
*   **4 Stereo Main Buses (M1-M4):** Channels have 4 independent Main sends (Pre or Post fader). Useful for creating distinct mixes (e.g., PA system vs. Livestream).
*   **16 Stereo Buses (B1-B16):** Can operate in three modes per channel send:
    1.  **TAP:** Signal derived from a customizable TAP point on Input channels (or fixed pre-fader on others). Used for monitor mixes.
    2.  **POST:** Signal derived post-fader. Used for FX sends.
    3.  **GROUP:** Send level deactivated; controlled solely by the channel fader for subgroup processing.
*   **8 Matrix Buses (MX1-MX8):** Receive signals from Mains and Buses. Cannot be routed to other Buses/Matrices. Used for system drive, fills, and delays.

---

## 2. Hardware and Panel Connections

### 2.1 Analog I/O by Model
*   **WING:** 8 Midas PRO mic preamps, 8 XLR outs, 8 1/4" TRS Aux In, 8 TRS Aux Out, 2 TRS Headphone outs.
*   **WING COMPACT:** 24 Midas PRO mic preamps, 8 XLR outs, 2 TRS Headphone outs.
*   **WING RACK:** 24 Midas PRO mic preamps, 8 XLR outs, 4x 1/4" TRS headphone outs on the rear (hardwired to XLR outs 1-4) + 1 independent front headphone out.

### 2.2 Digital Connectivity (All Models)
*   **Ethernet:** 2 ports for remote control and Audio over IP (AoIP) modules.
*   **USB 2.0 (Type B):** 48x48 ASIO audio interface, MIDI DAW control, firmware updates.
*   **AES50 (3 ports):** 48x48 channels per port (SuperMAC, CAT-5e, max 80m).
*   **StageConnect:** 32 channels (44.1/48kHz, 24-bit) over standard DMX/microphone XLR cable.
*   **AES/EBU:** 1 stereo input, 1 stereo output via XLR.
*   **Expansion Slot:** Pre-installed with **WING-LIVE** (Dual 32-channel SD/SDHC card recording/playback). Supports Dante/MADI cards.
*   **MIDI & GPIO:** 5-pin MIDI IN/OUT. TRS jacks for GPIO (4 GPIOs on WING/RACK, 2 on COMPACT).

---

## 3. Control Surface and UI

### 3.1 Main Interface Elements
*   **Main Display:** 10.1" multi-touch screen with 6 touch-sensitive knobs below and 1 context-sensitive knob on the right.
*   **VIEW Buttons:** Hardware buttons that jump the main display to the specific section's screen (e.g., pressing VIEW on the fader bank opens the Fader Overview).
*   **Scribble Strips:** Mini LCD displays above faders showing channel number, name, icon, and a color bar. Include stereo level meters and DYN/GATE threshold LEDs.
*   **4-Channel Section (WING & RACK):** Dedicated physical rotary controls for a selected bank of 4 channels. Allows a second user to adjust Gain, Gate, Comp, Filter, Pan, and Sends without affecting the main screen.

### 3.2 Fader Sections
*   **WING:** Left (12 faders), Center (8 faders), Right (4 faders).
*   **WING COMPACT:** Left (13 faders) and a dedicated Main Fader section (with a 2.4" screen and 16 quick-access buttons for DCA spills and SOF).
*   **WING RACK:** 4 physical rotary encoders mapping to a virtual layout.

### 3.3 Sends On Faders (SOF)
Allows physical faders to control send levels to a specific Bus, Main, or Matrix.
*   **Standard SOF:** Destination changes based on selected channel.
*   **Alternative SOF:** Destination remains fixed even if another channel is selected.

### 3.4 Custom Controls (CC)
User-assignable hardware buttons and encoders. Up to 16 layers available. Can control specific channel parameters, FX parameters, DAW controls, Mute Groups, Scene navigation, and GPIOs.
*   **Prefix Modifiers:** Adding `*` before a CC name displays its exact value on screen. Adding `|` inverts the background illumination.

---

## 4. Main Screens Overview

*   **HOME:** Channel specific processing. Select Icons, Colors, Tags (DCA/Mute Group assignment). Allows copying/initializing channel scope. Includes RTA settings.
*   **EFFECTS:** Manages the 16 FX Rack slots (8 Premium FX, 8 Standard FX). Note: Channel inline EQ/Comp/Gate do *not* consume these 16 slots. FX can be applied via Insert Points or Bus Sends.
*   **METERS:** Pre-fader level meters and mute status for all 40 inputs, 8 auxes, 16 buses, 16 DCAs, 4 mains, and 8 matrices.
*   **ROUTING:**
    *   *Channels:* Patch Sources to Channels (MAIN/ALT).
    *   *Sources:* Define Gain, +48V, Phase, Mono/Stereo/MS mode, and HA Remote (Preamp remote control via AES50).
    *   *Outputs:* Route any Source or Bus to physical/digital outputs.
*   **SETUP:**
    *   *General:* Brightness, Time/Date, Touch Settings, Firmware Update (via USB), Show Meter Page When Locked.
    *   *Audio:* Clock Rate (48kHz), Automix X/Y enables, Solo System (Live, Studio, Solo In Place).
    *   *Surface:* Meter source, Fader speed, Spill configurations.
    *   *Remote:* MIDI routing, AES50 HA Remote/Cust Sync toggles, Network IP configuration.
    *   *DAW:* MCU/HUI emulation configurations.
*   **LIBRARY:** Manages SHOW files, SNAPSHOTS (full console saves with customizable Scope), SNIPPETS (selective parameter saves), CLIPS (USB audio files), FX, and CHAN presets.
*   **OVERVIEW / FADERS / SENDS / CONFIG / MUTE GROUPS:** Deep-dive visual control for current fader banks.

---

## 5. Channel Processing Architecture

Processing blocks can be reordered via drag-and-drop on the HOME screen. Standard slots:
`Input/Filter -> GATE -> COMP -> INS 1 (Pre) -> EQ -> FADER -> INS 2 (Post) -> Pan/Width -> MAIN/BUS SENDS`

### 5.1 TAP Points
Available points to extract signal for User Signals or TAP-mode sends:
1.  **INPUT:** Immediately after preamp.
2.  **FILTER:** Post low-cut/high-cut filters.
3.  **TAP 3/4/5:** Inter-processing slots (customizable depending on block order).
4.  **PRE FDR:** Post processing, pre-fader.
5.  **POST FDR:** Post fader, pre-INS2.
6.  **POST PROC:** Post INS2, pre-Width control.

### 5.2 Key Channel Blocks
*   **TRIM & BALANCE:** Up to ±18dB trim. Balance attenuates L/R up to 9dB.
*   **FILTER:** 6/12/18/24 dB/oct slopes. Tool filters: Tilt EQ, Maxer, All-Pass 90°, All-Pass 180°.
*   **GATE & COMP:** Can load specific analog emulations. Sidechain options: Key Source, Key Filter, Key Solo, Peak/RMS detector. XOVER MODE allows splitting frequencies (compressing only specific bands and adding uncompressed bands back).
*   **EQ:** WING EQ (6-band parametric + L/H shelves). Can load analog EQ emulations.
*   **AUTOMIX:** Available in INS 2 on the 40 Input Channels. Automatically attenuates inactive mics to keep a constant noise floor (X and Y groups available).

---

## 6. Monitors and Talkback
Accessed via the MONITORING/TALKBACK panel.
*   **Talkback (A & B):** Switch modes (Push, Latch, Auto). Assignable to any Bus/Matrix/Main. Can follow specific send levels or uniform master level.
*   **Headphones/Speakers:** Two independent monitor paths. Includes Source selection, Dim/PFL Dim amounts, Direct In (mix a secondary signal in), 8-band EQ, Pan, Width, and Limiter.

---

## 7. Recording and Playback (WING-LIVE & USB)

### 7.1 WING-LIVE (SD Card)
*   Records up to 64 channels across two linked SD cards (32 channels per card).
*   SD cards formatted FAT32 (32kB clusters) directly on console. Files saved in `X_LIVE` folder.
*   Playback modes: Play, A->B loop, Continuous Loop.
*   Supports Battery Backup (3V CR123) to safely close files during power failure.

### 7.2 4-Track USB Recorder
*   Records 2 or 4 tracks (16 or 24-bit WAV) directly to USB drive on front panel.
*   Features a Playlist mode for playback.

---

## 8. Essential Shortcuts & System Modes

*   **Reset Touch Panel:** Hold SETUP, UTILITY, and CLR SOLO until an X appears, then hold SETUP and CLR SOLO for 1.5s. (Fixes ghost touches).
*   **Ghost Click Test:** Hold METERS + HOME during boot.
*   **Emergency Boot Mode:** Hold SETUP while powering up. Mounts `WING OS` and `WING DATA` directly to USB for firmware flashing if the console is bricked.
*   **Surface Test Mode:** Hold SETUP while booting. Tests all LEDs.
*   **Surface Lock:** Hold HOME (can use combination passwords).
*   **Initialize Console (Safe Boot):** Hold CLR SOLO while booting. Clears temporary state but keeps saved snapshots.
*   **Screenshot:** Hold CLR SOLO + press UTILITY (Saves BMP to `/screens` folder on USB).
*   **Bypass Startup Files:** Hold LIBRARY while booting (ignores `STARTUP*.snap/show`).
*   **Module Config:** Hold UTILITY for 5s during boot. Type `MOD-WSG` or `MOD-DANTE`.

---

## 9. Internal Effects Library

### 9.1 Equalizers
*   **WING EQ:** 6-band parametric.
*   **GEQ:** 31-band graphic. Has a "TRUE CURVE" mode to minimize interaction between overlapping filters.
*   **PIA 560 GEQ:** 10-band API 500-series style graphic EQ.
*   **Triple DEQ:** 3-band dynamic EQ (downward/upward compression and expansion).
*   **SOUL Analog:** 4-band SSL-style parametric.
*   **Even 88-Formant:** 4-band Neve 88RS-style.
*   **Even 84:** 3-band Neve 1073/1084 style.
*   **Fortissimo 110:** 4-band Focusrite ISA style.
*   **Pulsar P1a/M5:** Pultec-style passive tube EQ emulation.
*   **Mach EQ4:** 6-band Maag-style with AIR FREQ.

### 9.2 Dynamics (Compressors & Gates)
*   **WING Compressor/Expander/Gate:** Default digital dynamics.
*   **Even 88 Comp / Even 88 Gate:** Neve 88RS style dynamics.
*   **One Knob Compressor:** Transparent, auto-attack/release via Crest Factor.
*   **Listen Mic Toolkit (LMT):** SSL Talkback compressor style (explosive 80s drums). Includes a transient shaper.
*   **BDX 160 Comp:** DBX 160 style VCA.
*   **BDX 560 Easy:** DBX 560 style with negative ratio (beyond infinity) and soft knee.
*   **DRAW MORE Comp / 241:** Drawmer-style compressor and gate.
*   **RED3 Compressor:** Focusrite RED3 style transparent VCA.
*   **SOUL 9000 / SOUL Bus Comp:** SSL 9000K channel comp and G-Series Bus Comp.
*   **Even Comp/Lim:** Neve 33609 diode-bridge style.
*   **Eternal Bliss:** Empirical Labs Distressor style.
*   **76 Limiter Amp:** UREI 1176 FET style. Features "ALL" buttons-in mode.
*   **LA Leveler:** Teletronix LA-2A Opto style.
*   **Fair Kid:** Fairchild 670 Variable-Mu tube compressor style.
*   **No-Stressor:** Distressor style, with Optical emulation at 10:1 and NUKE modes.
*   **PIA 2250 Rack:** API 2500 style (Feed-back / Feed-forward switching).
*   **LTA100 Leveler:** Summit Audio TLA-100A style.
*   **C5-Combinator:** 5-band multiband compressor.
*   **Precision Limiter:** Digital peak brickwall.
*   **Wave Designer:** SPL Transient Designer style.
*   **Auto Rider:** Vocal rider (automates fader movements to maintain target level).
*   **BDX902 De-Esser / 2-Band De-Esser:** High-frequency dynamic controllers.

### 9.3 Channel Strips (Combos)
*   **EVEN Channel:** Even 88 Gate + 88 Formant + Comp/Lim.
*   **SOUL Channel:** Soul 9000 Gate + Analog + 9000 Comp.
*   **Vintage Channel:** 76 Limiter + Pulsar EQ + LA Leveler.
*   **Bus Channel:** Soul Warmth + Even 84 + Soul Bus Comp.
*   **Mastering:** Tape Machine + Mach EQ + Ultra Enhancer + Precision Limiter.

### 9.4 Reverbs & Delays
*   **Algorithmic Reverbs:** Hall, Room, Chamber, Plate, Concert, Ambience.
*   **VSS3 Reverb:** TC Electronic true stereo algorithmic reverb with distinct ER and Tail modulation layering.
*   **Vintage Room / Reverb / Plate:** Lexicon 480L / 250 / EMT 140 style emulations.
*   **Gated / Reverse Reverb:** 1980s non-linear verbs.
*   **Shimmer Reverb:** Pitch-shifted harmonic octave verb.
*   **Spring Reverb:** Mechanical tank emulation.
*   **Delays:** Stereo Delay, Ultratap Delay, Tape Delay (Roland Space Echo style), Oilcan Delay (Tel-Ray fluid-filled style), BBD Delay (Bucket Brigade dark delay).

### 9.5 Modulation, Pitch & Excitation
*   **Modulation:** Dimension CRS (Roland Dimension D), Stereo Chorus, Stereo Flanger, Rotary Speaker (Leslie), Phaser, Tremolo/Panner, Mood Filter (Moog style), Velvet Imager (K-Stereo imaging).
*   **Pitch:** Stereo Pitch, Dual Pitch, Pitch Fix (Autotune style), Double Vocal.
*   **Exciters:** Exciter (Aphex Aural Exciter), Ultra Enhancer (SPL Vitalizer), Tape Machine, SOUL Warmth Pre, Psycho Bass, Sub Octaver (Boss OC-2), Sub Monster.

---

## 10. Specifications Highlights
*   **Processing:** 40-bit floating point, 48 kHz.
*   **Latency:** 1.0 ms (Analog In to Analog Out). Stagebox latency: 1.2 ms.
*   **Matrix:** 500 x 502 point-to-point routing matrix.
*   **ADC/DAC:** 114 dB dynamic range (ADC), 120 dB dynamic range (DAC).
*   **Power:** Auto-ranging 100-240 VAC, 130 W consumption.
