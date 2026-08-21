# Sub-project C + D — WING over Ethernet — complete

**Date:** 2026-08-21 · **Branch:** `claude_desk/behringer-wing-ethernet-mixer-5de617`
**Console used:** `WING-GIAQUY`, a **`wing-rack`** on **FW 3.1-0-g9f314617**, at
`192.168.128.28`, serial `01009Y90604AAE`

Design authority: `docs/superpowers/specs/2026-08-21-wing-net-design.md`. Every
protocol claim in it was measured against that console. Where the official
document (*WING Remote Protocols* v3.0.6-27) disagrees, the spec records the
console's behaviour and says which is which.

## 1. What landed

`wing_parser/net/` — nine modules, none over 200 lines:

| module | responsibility |
|---|---|
| `codec.py` | OSC encode/decode; the reply-triplet value rule |
| `identity.py` | `WING?` handshake on UDP 2222 |
| `client.py` | pipelined UDP; retry with chunk bisection; source-port rotation |
| `schema.py` | breadth-first `,s ?` walk; dump fallback for oversized nodes |
| `nodetext.py` | `,s *` grammar; returns raw tokens and refuses to coerce |
| `snapshot.py` | leaf reads → `RawScene` |
| `write.py` | set, toggle, node write, push; the four §6 guards |
| `jsontypes.py` + `export.py` | `RawScene` → `.snap` file |
| `cli/net_commands.py` | the `wing net` group and the `--live` flags |

`RawScene` (`core/loader.py`) gained an optional `path` and a `source` label, so
a console-read scene flows through `WingScene` untouched. **Nothing in `core/`,
`query/`, `advisory/` or `showcontext/` changed to support live data** — that
was the design bet and it held.

## 2. The command surface

```powershell
python -m wing_parser.cli net identity 192.168.128.28
python -m wing_parser.cli net snapshot 192.168.128.28 -o today.snap
python -m wing_parser.cli net get 192.168.128.28 /ch/1/fdr
python -m wing_parser.cli net set 192.168.128.28 /ch/1/fdr -6.0 --confirm
python -m wing_parser.cli net toggle 192.168.128.28 /ch/1/mute --confirm
python -m wing_parser.cli net push 192.168.128.28 show.snap --confirm

python -m wing_parser.cli doctor --live 192.168.128.28
python -m wing_parser.cli analyze --live 192.168.128.28
python -m wing_parser.cli routing --live 192.168.128.28
python -m wing_parser.cli channel --live 192.168.128.28 11
```

`--live` and a file argument are mutually exclusive; argparse enforces it.
`set`, `toggle` and `push` send nothing without `--confirm`.

**Use PowerShell, not Git Bash.** An OSC address begins with `/`, and MSYS
rewrites that into a Windows path — `/ch/1/fdr` silently becomes
`C:/Program Files/Git/ch/1/fdr` and the command reports no reply. This was hit
during verification, not theorised.

## 3. Measured results

| | |
|---|---|
| whole-console read | **3.2 s shape + values, 25 170 leaves, 0 unresolved** |
| snapshot twice, no writes between | **0 drift** across 21 232 leaves — the read is exactly reproducible |
| push a whole scene | 21 344 leaves in **1.1 s** fire-and-forget |
| push the console's own values back | `landed=21232, mismatched=0, absent=0`; **2 leaves** moved by one quantisation step |
| **advisory on the live desk vs the file pushed to it** | **22 findings and 22 findings** |
| `doctor --live` end to end | 22 findings in **11.9 s** |
| `net snapshot -o` then `WingScene.load` | 822 KB file, reloads to 22 findings and the same 2 anomalies as the source |
| whole-scene push, cross-console | 29 s: 1.1 s of writes, the rest verifying all 28056 leaves |
| offline suite | **994 passed, 1 skipped** (FastMCP, by design); no test opens a socket to a console |

`example-Vu.snap` still yields exactly **22** findings and `factory-scene.snap`
still yields **none** — the standing constraint held throughout.

## 4. The six findings that shaped the work

Each cost a measurement and would have been wrong if reasoned about.

**1. A node dump is lossy display text, not snap-equivalent.** The official
document says a `,s *` dump "will strictly correspond to what would be saved in
a snap file". It corresponds in *which keys*, not *precision*: `10018.26074`
comes back as `10k02`, `0.997970223` as `1.00`. Dumps discover shape; per-leaf
reads carry values.

**2. Which element of a reply triplet to take depends on the tag, and the wrong
choice is silent.** Settled by pushing `example-Vu.snap` onto the console and
reading all 21 344 leaves back: `,sff` → take the **native** float (display is
rounded, 2770 cases); `,sfi` → take the **display** string, because the native
int is often a **0-based index** (`/io/in/CRD/1/col` reads native `0` where the
file holds `1`, 1066 cases). `codec.leaf_value` had this backwards; a snapshot
built on it would have been off by one on 1066 leaves while looking plausible.

**3. Write every value as a display-domain string.** Dispatching the OSC type
from the Python value left **1919 of 21 344 leaves wrong**; the string form left
**5**. An int often selects an *index*: `dyn.ratio` has schema
`list [1.1, 1.2, 1.3, 1.5, …]`, so `,i 3` sets `1.5` where `,s "3"` sets `3.0`.
And because a `.snap` writes an integral float as a bare int, `"lvl": 0` arrives
as a Python `int` and a type-dispatching writer sends `,i` to a **fader**. The
5 that still fail are scientific notation (`1.490116119e-07`), which WING's
string parser does not accept.

**4. A reply that never comes poisons the source port, and rotation must be
per-chunk.** An oversized reply kills the console's reply stream to that port —
every reply after it in the batch is lost. Rotating between retry *rounds* is
not enough: bisecting the chunk size to 1 still left 27 nodes unresolved,
because each isolated request after the first still landed on the poisoned
socket. Rotating after any short *chunk* took it to 3. A GET on a missing
address, by contrast, is harmless and safe to pipeline.

**5. A retry ladder must stop when it stops helping.** Halving the chunk size
isolates a poisoned request, but an address that will never answer is not a
poison to isolate. A cross-console push leaves thousands of leaves genuinely
absent, and bisecting that set to chunk size 1 pays an idle timeout each: the
push ran past **two minutes** where its writes take 1.1 s. The fix is one line —
if a round recovers nothing, stop — and it also took the schema walk from 3.2 s
to 1.0 s.

**6. The JSON tree is dynamic, so nothing about its shape may be cached.**
Proved by writing `/aux/1/dyn/mdl` and re-reading the schema: `GATE` exposes
`acc range att hld ratio rel`, `COMP` exposes `auto det env knee …`, `CMB`
exposes `cmode cpeak depth fast …`. Two whole-console walks minutes apart
differed by exactly those six leaves and nothing else out of 25 060.

## 5. A latent parser bug this exposed

`query/build_blocks.build_dyn` read the dynamics ratio with `float(...)`. A
compressor stores a number, but **a gate stores the string `"1:3"`**, and a WING
defaults its aux dynamics to `GATE`. Neither reference `.snap` contains a gate
on a strip — both carry only `CMB` and `COMP` — so the whole suite passed while
the parser could not open a scene saved from an untouched desk. Reading the live
console raised on **7 of 8 aux strips**.

`Dyn.ratio` is now `float | None`, `None` for the `a:b` form, matching sibling
`Gate` which models no ratio at all for the same reason. No advisory rule reads
`Dyn.ratio`, so no finding moved.

## 6. Open questions for ToanAZ

1. **Should a gate's `1:3` be a number at all, and under which convention?**
   Left as `None` rather than guessed. Nothing reads it today.
2. **Which `type` id does a live rack write?** Unmeasured — no console-authored
   `.snap` exists. `example-Vu.snap` carries `snapshot.11`, `factory-scene.snap`
   carries `snapshot.10`, so the two references do not agree. `snapshot.11` is
   assumed and the assumption is marked in `snapshot.py`. **To settle it: with
   WING-Edit connected to this console, save a scene and read its `type`.**
   WING-Edit could not be driven from here — it is a portable exe at
   `Z:\My Drive\SOFTWARE\Wing-Edit_PC_3.2.1\` and is not Start-menu registered,
   so the automation layer cannot see it.
3. **18 boolean shapes are a WING inconsistency, not a modelling gap.** The send
   `plink` family is `1` in one reference file and `true` in the other. Byte-exact
   type reproduction is impossible in principle for those.
4. The three documented-but-unobserved node-write errors (`BUFFER OVERFLOW`,
   `INCOMPLETE DATA`, `STACK EMPTY`) are treated as errors without having been
   seen. Any unrecognised payload is an error, so this is safe, not guessed.

## 7. State of the lab console

**The desk was restored to `factory-scene.snap` at the end of the session**, by
`wing net push`. `doctor --live` reports no findings, matching what the file
gives. Before that it held a pushed copy of `example-Vu.snap`, written over OSC
as the round-trip test. Individual leaves exercised during probing —
`/ch/40/{fdr,mute,name}`, `/dca/16`, `/mgrp/8/name` — were restored at the time.

To return it to a clean desk, **push `user-files/factory-scene.snap`**. Do not
use the pre-push capture taken at the start of this session: it was read with
the naive value rule, before finding 2 above, so every `,sfi` leaf in it holds
a 0-based index rather than the value. Restoring from it would quietly set
`col`, `icon` and the IO patch indices one step low across the desk. The
factory file is a real console-authored scene and has no such problem.

## 8. What is deliberately not here

Realtime subscription (`/*S~`), metering (native UDP channel 3 — the doorway to
sub-project E), the native binary/TCP interface on 2222, and MCP live support.
The first two were offered and declined; the last is handoff §5.4 and stays open.

`/fx/1`'s `,s ?` schema still cannot be read directly — its dump is used
instead. That is a console limit, not a gap: all 34 of its parameters are
reached and read.
