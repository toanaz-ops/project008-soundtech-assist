# Reverb, delay and FX sends

Table: `fx.yaml`. Sources R1-R7 (see `sources.yaml`). The WING Effects Guide PDF could not be opened, so
**every per-genre FX number is low confidence or an engineering default**.

## Reverb

Rules of thumb from Sound On Sound and iZotope: faster, denser material takes shorter decay, sparse and slow
material tolerates longer (a ballad vocal can take 3-4 s). Pre-delay 5-10 ms for short ambience, 30-70 ms for
long reverb, never 0 for a vocal; iZotope: vocal 20-80 ms, drums 5-50 ms, guitars 40-100 ms. Returns are 100%
wet, sends post-fader, return filtered: low cut roughly 100-300 Hz, high cut from about 7 kHz.

| Genre | Decay s | Pre-delay ms | Low / high cut Hz |
|---|---|---|---|
| Pop | 0.8-1.8 | 20-80 | 150 / 7000 |
| Rock | 0.3-1.2 | 0-30 | 200 / 7000 |
| Ballad | 1.8-3.5 | 40-100 | 150 / 6500 |
| Jazz | 1.0-2.2 | 15-40 | 120 / 8000 |
| EDM | 0.8-2.5 | 10-60 | 250 / 6000 |
| Bolero | 1.8-3.0 | 20-60 | 150 / 8000 (no source, ballad extrapolation) |
| Speech | none | none | FX parameters left alone, all sends off (product decision: intelligibility first) |

The engine picks the short end of the range for a ROOM, the middle for a PLATE, the long end for a HALL
(AM-26).

## Delay

Slapback: single repeat about 80-150 ms (Sound On Sound) or 50-100 ms with no feedback (page 2). Rhythmic:
tempo-synced, quarter note first; ms = 60000 / BPM x beats (1/4 = 1, dotted 1/8 = 0.75). Feedback kept low;
darken and high-pass the repeats. Feedback percentages are low confidence starting points.

## Send levels

No source gives dB numbers; the table holds starting offsets derived from qualitative guidance: lead vocal
reverb -18..-8 dB, delay -24..-12; snare and toms reverb about -14..-6; kick, overheads, bass dry; electric
guitar reverb -20..-10. "Off to X" ranges in the research were resolved to **off** (AM-27). Genre wetness
offsets (ballad +3, rock -3, jazz reverb -2 / delay -6, EDM reverb -3 / delay +3) are `eng_default`.

## Disagreements

- Vocal pre-delay: Sound On Sound 100 ms and up for a lead, iZotope 20-80 ms, Sound On Sound page 2 30-70 ms.
  Default 20-80, longer for ballads.
- Slapback: 50-100 ms (page 2) versus 80-150 ms (Six Practical Uses).

## Unverified

The WING Effects Guide (model list, ranges, premium-slot membership), Chourdakis & Reiss JAES 2017 (citation
only), the books by Owsinski and Senior.
