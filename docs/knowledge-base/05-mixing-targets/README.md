# 05 - Mixing targets (automix knowledge)

Human-readable notes behind the machine tables in `wing_parser/automix/data/` (wave 12, 2026-11-09). The
tables drive the Automix feature: pick a genre, get a proposed channel strip (HPF, EQ, gate, compressor,
fader, FX, sends). These notes say where each number came from, where sources disagree, and what is
unverified.

## How to read the numbers

| Tag | Meaning |
|---|---|
| `high` / `medium` / `low` | A source states it; trust drops with vendor-blog level evidence. Almost everything here is `low`. |
| `eng_default` | An engineering convention. No source states this number. It is never upgraded silently. |

The only **measured** numbers are the relative loudness of kick, snare, bass and drums against the lead
vocal (De Man et al., ISMIR 2014). Everything else is textbook or vendor guidance, not ToanAZ's taste.
ToanAZ's own answers (Decision Box HW-191.Q1-Q6) go into `knowledge/toanaz/automix.yaml` and override the
base tables; an override without `ToanAZ` and an ISO date in its `source:` is ignored with a warning.

## Files

- [eq.md](eq.md) - HPF and EQ targets per source, masking pairs.
- [balance-and-dynamics.md](balance-and-dynamics.md) - fader offsets, headroom, compressor, gate.
- [effects.md](effects.md) - reverb, delay, send levels per genre.
- [wing-fx-and-meters.md](wing-fx-and-meters.md) - WING FX slot model, automix group, meters protocol.

## Source status

Opened and read: iZotope, FabFilter, Sound On Sound, Shure, QSC, Waves, Church Collective, Sharefaith,
Drew Brashler (WING blog), the ISMIR 2014 and WIMP 2017 papers, Ma/Reiss/Black 2015, Ronan et al. 2018, the
Maillot WING Remote Protocols text, plus three repository knowledge-base files.

**Not opened (abstract or catalogue record only; nothing here rests on their bodies):** Hafezi & Reiss, JAES
2015 (AES, HTTP 403); De Man & Reiss, AES Conv. 135, 2013 (403); Perez-Gonzalez & Reiss, WASPAA 2009; the
official WING Effects Guide PDF; Owsinski and Senior books. Their entries in `sources.yaml` carry
`opened: false`.

Every URL and citation id is in `wing_parser/automix/data/sources.yaml`. Autonomous decisions taken without
the owner are numbered AM-n in `docs/decisions/2026-11-09-automix-decisions.md`.
