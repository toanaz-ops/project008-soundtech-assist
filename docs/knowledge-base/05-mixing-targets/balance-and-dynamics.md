# Balance, headroom, compressor and gate

Tables: `balance.yaml`, `dynamics.yaml`. Sources F1-F8 (see `sources.yaml`).

## Fader balance

The one measured result: De Man et al. (ISMIR 2014, Table 2 and section 4.2) measured the perceived loudness
of each processed source soloed against the full mix. Against the lead vocal at 0: kick -10.5, snare -14.1,
drums group -10.0, bass -6.9 loudness units; only the vocal differs significantly from the rest. The classic
"equal loudness for all sources" prior (Perez-Gonzalez & Reiss, not opened) is therefore wrong for vocals.

Caveats the tables do not hide:

- These are **loudness** offsets, not fader positions. Fader offsets per genre in `balance.yaml` are derived
  from them plus engineering judgement and are all `low` or `eng_default`. No genre-resolved study was found.
- Pop snare at -10 dB comes from the research table, while the measured loudness gap is -14.1 LU. Kept visible.
- Jazz, EDM, bolero and speech have **no source** (`eng_default`).

Anchor: the lead-vocal fader, clamped to -10..0 dB, else -5 dB (iZotope gain-staging: balance near unity,
push room above). A fader already at -inf is left alone (AM-24). Small rooms: electric guitar and drums
-3 dB for stage volume (AM-12, qualitative).

Headroom guard: each channel with a main send on is assumed at -18 dBFS nominal (iZotope: nominal, **not** a
peak target) plus its fader; the power sum must stay at or below -3 dBFS. If not, every proposed fader is
trimmed by the same amount. The -3 dBFS ceiling is an engineering default.

## Compressor

Starting points only (Sharefaith church-AV guide, low weight, and Ma/Reiss/Black 2015): vocal 2-4:1,
attack 2-10 ms, release 40-100 ms, 3-6 dB gain reduction; kick and snare about 3.5-4:1; bass 2.6-4:1;
keys 1.8-2.5:1. Electric guitar: usually left uncompressed (no row). Playback: never compressed.
Genre deltas (jazz lighter, rock heavier, pop vocal heavier, EDM hard vocal, speech steady 3-4:1) have no
source. **Threshold cannot be read offline**: the engine assumes a -12 dBFS peak (AM-23); meters (phase 2,
experimental) may refine this. Ratio is capped at 8:1 (AM-17) and at 4:1 for speech (Doctor rule PC5).

## Gate

Drums only (kick, snare, toms): attack 0-1 ms, hold 30-150 ms, release 50-250 ms; range 12-30 dB kick, 12-20
dB snare (partial range keeps ghost notes), 20-40 dB toms (Waves; Church Collective, no numbers). Sources
quote range as a negative number; the WING leaf stores a depth. Threshold is an assumed -40 dB. Jazz, ballad
and bolero get no gates (AM-11, low confidence). Only the WING GATE model is written; CMB gets a Skipped row.

## Disagreements and unverified

- -18 dBFS is a DAW nominal (iZotope); live vocal peaks sit above it.
- WING fader range -inf..+10 dB and trim 0..+72 dB are from the scene inventory, not the manual (not read).
- Per-genre fader offsets, 3-6 dB gain-reduction targets (secondary snippets), books by Senior and Owsinski:
  unverified.
