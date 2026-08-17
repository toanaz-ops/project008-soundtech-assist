# Rule-set growth (sub-project B) — outcome and residuals

**Date:** 2026-08-17 · **Merged to `main` @ `cb21714`** (fast-forward from
`claude_desk/tiep-tuc-3dd3f9`) · 527 tests passing, 1 skipped (FastMCP, by design)

## What shipped

- **32 base rules** (was 3) across 8 YAML files. Structural: G7 (IEM no
  dynamics, error), G9 (wedge/generic monitor, warning), G8 (post-fader
  monitor send, now sees matrices), E6, R1–R6+R3M (click/talkback/timecode/
  record/mix-minus routing), N1, S1, S2, G10–G12. Presets at info:
  PC1–PC8 (`event: corporate`), PB1–PB6 (`event: band`).
- **Advisory engine sees mains and matrices** — iterators `output` and
  `channel.main_sends`; `channel.sends` yields matrix destinations (targets
  `ch.N.send.MXn`). ToanAZ's IEMs are matrices 5–8; they were invisible to
  every rule before this.
- Predicate operator `starts_with`; 8 derived properties on the query layer
  (Bus: `notch_count`, `max_boost_above_8k`, `receives_ambient`,
  `receives_any`; Channel: `iem_send_count`, `eq_has_lowmid_cut`,
  `eq_has_presence_lift`, `in_use`); 5 new classifier patterns; monitor role
  hierarchy `monitor.iem`/`monitor.wedge`/`monitor`.
- `event:` mechanism: no profile → everything runs (ToanAZ's decision);
  a profile declaring `event:` switches off other-event base rules with an
  `[off-event]` transparency line.
- Real-file contract pinned (`tests/test_advisory_realfile.py`): the
  untouched `example-Vu.snap` yields **22 findings** — new real catches are
  G10×4 (no ambient mic into any IEM matrix) and PB1 ch.16 (Snare Bot not
  polarity-inverted), PB2 ch.21 (Hihat HPF at 502 Hz), PB4 ch.22 (OH HPF at
  120 Hz), PB5 ch.13 (Kick In HPF at 55 Hz) — every value verified against
  raw JSON. Factory scene pinned silent. `--profile small` still
  suppresses G8.

## Domain facts recorded this cycle (do not re-derive)

- **TAP sends default pre-fader or pre-EQ on a WING** (ToanAZ,
  2026-08-16) — why G8 matches `POST` only. In G8's rationale.
- Insert slots store console tokens (`NONE`, `FX13`), never plugin names;
  `source.mode` is `M`/`ST`; `tap_point` is `POST_FDR` on every channel of
  both sample files including factory — three whole rule families were
  killed on this evidence (spec §8, do not re-mine).
- WING automix lives in `postins` with `mode: AUTO_X` → group, `w` → weight;
  channel EQ builds from raw key `eq` (NOT `peq`); bus EQ parses exactly 6
  bands (low/1–4/high, shelf shapes `leq`/`heq`).
- Factory buses 9–16 sit at fader 0 — the reason **N2 ships
  `enabled: false`** (probed values quoted in its rationale).

## Residuals (deferred, none load-bearing — triaged by the final review)

1. `render.findings` returns "No findings." before the `[suppressed]`/
   `[off-event]` lines, so transparency lines vanish on a clean scene.
2. `off_event_ids` doesn't subtract superseded rules — a rule both
   superseded and off-event would print two transparency lines (latent).
3. S1 (warning) and PC1/PC6 (info) both fire on a lectern/panel channel
   with HPF off — two findings for one knob; wordings complementary.
4. `Bus.receives_ambient` is one-hop; an ambient mic routed via an
   intermediate bus would still trip G10 (rationale doesn't say so yet).
5. Preset messages render raw floats ("55.16390228 Hz") — cosmetic.
6. Boundary tests unpinned: PC1/PC6 window edges, `max_boost_above_8k`
   strict bounds, aux `_fed_by` False branch, `profile_event` `.yml` path.
7. README.md:378-381 `event:` field phrasing could be misread in isolation
   (links to the correct section; polish only).

## Still open with ToanAZ

- **The limiter `dyn.mdl` token** (Phase-1 handoff §3.1, still unanswered):
  load a limiter onto a bus, save, read `mdl`. Unlocks G7's second clause
  (closure spec §7.1).
- Whether the four G10 findings on his real file are real advice or a
  deliberate small-rig choice — if deliberate, a show profile with
  `supersedes: [G10]` is the designed answer.

## Remaining roadmap (Phase-1 spec §14 decomposition)

A (advisory loop) done · **B (this) done** · C OSC read · D OSC write ·
E audio analysis · F decision tier (needs A, C, G) · G input pipelines.
C and G are unblocked. Ask ToanAZ; do not assume.
