# HPF, EQ and masking targets

Tables: `eq_targets.yaml`, `masking.yaml`. Sources S1-S10 (see `sources.yaml`).

## What the engine does

- HPF on for every classified channel except playback; corner is the typical value below, slope 12 dB/oct
  (Core-Skills-Overview L686 gives 12-18).
- EQ on the WING **STD** model only: up to two cuts into bands 1-2, up to two boosts into bands 3-4, an
  optional high shelf. Cut default -3 dB, Q 2.0; boost default +2 dB, Q 1.0 (engineering conventions,
  `eng_default`: most pages give a frequency and a reason, rarely a dB figure).
- Hard limits: gain -6..+3 dB, Q 0.7..4. Live work prefers cuts over boosts because boosts cost feedback
  margin (FabFilter).

## Starting points per source (summary)

| Source | HPF Hz | Typical cuts | Typical boosts |
|---|---|---|---|
| Kick | 35 | 200-500 boxy, 600 honk | 60-90 punch, 1-5k click |
| Snare | 100 | 400-700 ring, 900-1500 papery | 150-250 body, 2-3.5k snap, 8k shelf |
| Toms | 60 | 250 mud | 60-120 body, 0.8-1.5k attack |
| Hi-hat | 300, clamped to 250 | 3-7k harsh | 12k shelf |
| Overhead / ride | 250 / 300 | 4k / 5-7k | 8-12k shelf |
| Bass | 35 | 200-400 mud | 220-300 character, 0.8-1k articulation |
| Electric guitar | 100 | 200-300 tubby, 3-6k fizz | 4k +3 dB presence |
| Acoustic guitar | 70 | 150-400 tubby | 1.5k presence, 8-12k air |
| Keys / strings / horns | 60 / 120 / 150 | 200-500 mud | strings, horns: air shelf |
| Vocal | 100 | 200-500 mud, 500-1200 nasal | 4k +3, 1-1.5k +3 |
| MC / lectern | 100 | 300 -3 dB Q1.4 | 3k +2 dB |

Sibilance (5-8 kHz, -6..-12 dB narrow) is deliberately left to a de-esser, as Shure and QSC suggest.

## Masking pairs

Kick vs bass: let one instrument own 50-100 Hz; dip the kick near 180 Hz, lift the bass 220-300 Hz (Sound On
Sound, Kick & Bass). Vocal vs electric guitar: cut the guitar near 4 kHz (QSC). Vocal vs keys: gentle 2-4 kHz
dip on the keys. Vocal vs snare: **no source**, kept as `eng_default`.

## Disagreements kept visible

- Hi-hat HPF: iZotope cheat sheet says "lightly", iZotope drums says 300-500 Hz. The repository Doctor rule
  PB2 allows 160-250 Hz, and **the existing rule wins** (AM-9): the engine clamps into the Doctor window.
- Vocal HPF: Shure says male about 80 Hz and female about 140 Hz; iZotope says 100-250 Hz. Engine uses 100.
- Kick HPF: Sound On Sound 30-40 Hz, iZotope 25-60 Hz. Engine uses 35.

## Unverified

AES papers on masking-based auto-EQ (Hafezi & Reiss, De Man & Reiss) were not readable; no bound in the
engine rests on them. No source found for keys HPF, playback, speech.mc specifics, tom HPF exact values,
snare-vs-vocal masking, or any **genre EQ tilt** (rock +1 dB presence, jazz and speech halve boosts are
product heuristics).
