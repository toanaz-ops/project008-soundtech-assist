# Live-watch acceptance tests — COMPLETE

**Date:** 2026-08-23 · **Console:** WING-GIAQUY (wing-rack), serial
01009Y90604AAE, firmware 3.1-0-g9f314617 · **`main` @ `59197b8`+** ·
Operator: ToanAZ drove every change from **WING-Edit**.

This closes both open acceptance tests from the live-watch design §4.4 and the
third, smaller subscribe question (ROADMAP §6). The console had been out on a
show since 2026-08-22; this was the first window with it back.

## Test 1 — does polling detect a change? ✅ CLOSED

```
python -m wing_parser.cli net watch 192.168.128.28 --until 120
watching 220 leaves (40 ch, 16 bus, 4 main, 8 mtx, 16 dca)
```

~150 change events in 120 s, driven entirely from WING-Edit:

- Faders `/ch/1` … `/ch/16` `$fdr` moved in long continuous drags — each
  intermediate step reported (~250 ms apart), e.g. ch/15 dragged −70 dB → +0.3
  through thirteen distinct values.
- Solo presses on ch 1, 2, 3, 5, 7, 9 tracked on `$solo` 0→1→0 exactly as
  pressed.
- Extremes handled correctly, including the −144 dB (fully down) sentinel on
  ch/10, ch/11, ch/14–16.

Detection is proven against a real desk, with the operator on the real remote
app.

## Test 2 — does it coexist with WING-Edit? ✅ CLOSED

WING-Edit stayed connected for the entire window and was the *source* of every
change while the poller ran its full 220-leaf cycle. No errors, no dropped
readings, no displacement on either side. ToanAZ confirms he used WING-Edit
itself. *"cần song song không đá nhau"* holds.

## Test 3 — OSC subscribe verbs: NEGATIVE, closed as underivable

Redo of `docs/probes/probe2_subscribe_wide.py`, this time with controls being
moved throughout every listen window (the previous run's fatal caveat was that
the desk was idle). The control GET passed — the harness demonstrably worked,
and the sampled fader value matched the drag in progress. All ten candidate
subscribe verbs (`/*S~` bare/s/i, `/*S i`, `/*~` bare/i, `/xremote`,
`/subscribe`, `/%0/*S~`, `/* ?`) were silent anyway.

Conclusion: firmware 3.1 answers none of them. **Polling is the only change
mechanism; do not spend more time on subscribe.** Written up per the
limiter-token precedent: a negative result is recorded, not retried into
silence.

## Finding worth keeping: the walk can transiently lose families

The FIRST watch run this session warned that seven top-level families
(`/io, /ch, /aux, /bus, /main, /mtx, /$ctl`) "did not resolve" and watched only
16 leaves; a direct re-probe seconds later (`probes/probe_family_resolve.py`)
showed every family answering instantly, and an immediate rerun resolved all
220 leaves with no warnings. So `walk_schema` can lose whole families to UDP
loss or console load under burst probing, recover on retry, and — because
`build_watch_list` reports unresolved nodes instead of folding them into
"absent" — the failure is visible rather than silent. Standing rule: **if a
watch session opens with unresolved families, rerun before believing the list
is small.** The probe script stays in `probes/` as evidence.

## What changed in the repo

- `docs/ROADMAP.md` §6 rewritten: nothing left waiting on hardware.
- `probes/probe_family_resolve.py` added (the re-probe above).
- `docs/probes/probe2_subscribe_wide.py`: import path fixed (pointed at a
  worktree deleted in the 2026-08-23 branch cleanup).

## Next

Nothing blocks G2b except the two human inputs in
`docs/superpowers/plans/2026-08-23-next-steps.md` Step 0: one real running-order
`.xlsx`, and ~20 seeded Vietnamese terms in the `cuesheet:` vocabulary.
