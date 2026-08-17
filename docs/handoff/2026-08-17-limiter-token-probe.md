# The limiter `dyn.mdl` token — probed to exhaustion, closed as offline-underivable

**Date:** 2026-08-17 · **Status:** answered as far as this machine can answer
it. Do not spend a fourth session searching. It needs two minutes on a real
console.

## The question

G7 wants a second clause, `bus.dyn.model: {not_in: [<limiter tokens>]}`, so
that an IEM output with a limiter loaded stops firing. The 2026-08-16
advisory-closure spec §7.1 records the exact edit. It has been open since
Phase 1 because nobody knows what token a WING writes when a limiter is
loaded, and the standing rule forbids guessing it.

## Three independent probes, all negative

### 1. Both sample `.snap` files — the model enum has one value

```powershell
python -c "
import json, collections
vals=collections.defaultdict(collections.Counter)
for name in ['example-Vu','factory-scene']:
    d=json.load(open('user-files/%s.snap'%name,encoding='utf-8'))
    def walk(n):
        if isinstance(n,dict):
            dyn=n.get('dyn')
            if isinstance(dyn,dict) and 'ratio' in dyn:
                for k in ('mdl','det','env'): vals[k][dyn.get(k)]+=1
            for v in n.values(): walk(v)
    walk(d)
print({k:dict(c) for k,c in vals.items()})"
```

Result: `mdl -> {'COMP': 139}`, `env -> {'LOG': 139}`, `det -> {'RMS': 120,
'PEAK': 19}`. Every compressor-shaped dynamics block in both files, channels
and buses alike, is `COMP`. A single-valued enum says nothing about its other
members. `ratio` tops out at 10 on exactly one block, so the fallback idea of
inferring "limiter" from a high ratio has no real data to calibrate against
either.

### 2. `WING-Edit.exe` — packed, no enum table to extract

Scanned all 93,612,712 bytes for ASCII and UTF-16LE strings (7,337,545 of
them), then used `CMB` — a token confirmed real by the `.snap` files — as an
anchor and printed its neighbours. `CMB` occurs exactly once, at `0x1fd04f0`,
surrounded on both sides by two- and three-byte binary noise (`'{j'`, `'Oj'`,
`'c&Q'`, …). String tables survive packing as contiguous runs; this is not
one. The Phase-2 session's "found `COMP`, `CMB`, `LIM`, `LIMIT`, `LIMITER`
but no co-located enum table" was right, and the reason is that the
executable is compressed. No amount of further scanning changes this.

### 3. `WING_Series_Manual_Knowledge_Base.md` §9.2 — display names only

Even Comp/Lim (L193), 76 Limiter Amp (L195), Precision Limiter (L202). These
are what the console prints on screen, not what it writes to the file. No
source in this repository maps one to the other.

## Two schema facts discovered on the way — new, worth keeping

**The `dyn` block has two different shapes, not one.**

| shape | keys | where | count |
|---|---|---|---|
| compressor | `att auto det env gain hld knee mdl mix on ratio rel thr` | channels, buses, mains, matrices | 71 + 68 |
| aux input | `cmode cpeak depth fast gain ingain mdl mix on peak thr` | `/ae_data/aux/1–8` only | 5 + 8 |

The aux shape has no `ratio`, `att` or `rel`; it has `peak`, `cpeak`, `depth`,
`fast` and a `cmode` selector (`COMP` in all 13 observed). On
`factory-scene.snap` the aux blocks carry **no `mdl` key at all** — the five
`CMB` values come only from `example-Vu.snap`'s named FX returns. So `CMB` is
an aux-input model and tells us nothing about bus dynamics. `build_dyn`
(`wing_parser/query/build_blocks.py:19`) reads both shapes safely because
every field goes through `.get` with a default; the aux shape simply lands on
`ratio=1.0` and `model="NONE"`.

**FX-rack `mdl` is a separate namespace.** `/ae_data/…/fx/16` reads
`"mdl": "C5-CMB"`, slot 14 `"DOUBLE"`, slot 15 `"NONE"`. A limiter token
harvested from an FX slot would not be a `dyn.mdl` value and must not be used
for G7.

## What actually answers it

On a real WING: load a limiter onto any bus, save the scene, and hand over the
`.snap`. Then read the bus's `dyn.mdl`. Repeat for each limiter-capable model
he would really use — `not_in` needs the **complete** list, and a missing
member makes G7 fire on a protected IEM, which is the failure mode the rule
exists to prevent.

Until then G7 ships with `bus.dyn.on: false` alone, which is verifiable today
and honest about what it does not check.
