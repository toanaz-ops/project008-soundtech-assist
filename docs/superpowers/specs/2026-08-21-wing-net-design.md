# Sub-project C + D — WING over Ethernet (OSC read & write)

**Date:** 2026-08-21 · **Status:** design authority for `wing_parser/net/`

Every protocol claim in §2 and §3 was **measured** against the lab console on
2026-08-21, not taken from documentation. Where the official document
(*WING Remote Protocols*, P-G Maillot, v3.0.6-27) disagrees with the console,
this file records the console's behaviour and says so. Do not "correct" this
file back towards the document.

## 1. Purpose

`wing-parser` reads `.snap` files offline. This subsystem lets it talk to a
running console: read the whole desk into the existing `WingScene`, write a
`.snap` file, and set parameters back.

**Goal stated by ToanAZ: reach the console's full functionality**, not a
convenience subset. Coverage is measured, not asserted (§7).

## 2. Verified protocol facts

### 2.1 Transport and identity

- OSC is **UDP 2223**. Identity handshake is **UDP 2222**.
- Sending the 5 bytes `WING?` to 2222 replies with a comma-separated record:

```
WING,192.168.128.28,WING-GIAQUY,wing-rack,01009Y90604AAE,3.1-0-g9f314617:release
     [ip]           [name]      [model]   [serial]       [firmware]
```

The lab console is a **`wing-rack`** on **firmware 3.1**, newer than the 3.0.6
document. Its root node carries a `$globals` the document does not list.

- WING **does not echo** a parameter write. Success is silent.
- Replies go to the client's source port unless the address is prefixed
  `/%<port>`.
- Only **one** OSC subscription exists console-wide, and it dies after 10 s.
  Subscriptions are **out of scope** for this subsystem.

### 2.2 Address space maps 1-to-1 onto `.snap`

| OSC | `.snap` |
|---|---|
| `/cfg /io /ch /aux /bus /main /mtx /dca /mgrp /fx /cards /play` | `ae_data.*` |
| `/$ctl/{cfg,layer,user,gpio,safes,daw,midi,osc,lib}` | `ce_data.*` |
| `/io/in/{LCL,AUX,A,B,C,SC,USB,CRD,MOD,PLAY,AES,USR,OSC}` | `io.in.*` |

`$`-prefixed keys are read-only and **absent from `.snap`** — the two reference
files contain zero of them. Skip every `$` key when building a scene. The one
exception is `/$ctl` itself, which is not a skipped key but the container that
*is* `ce_data`, and must be descended into.

`fdr = -oo` reads back as float `-144.0`, which is exactly the sentinel
`core/normalizer.to_db` already maps to `-inf`.

### 2.3 Reading — per-leaf is exact, node dumps are lossy

Reading a leaf returns a **triplet**: ascii display text, a normalised
`[0.0..1.0]` float, and the native value.

- `,sff` gives `['-42.3', 0.173, -42.316715240478516]` — float parameter
- `,sfi` gives `['1', 1.0, 1]` — integer parameter
- `,s` gives `['LCL']` — string or enumerated parameter

**The third element is bit-exact against the `.snap` file:**

| leaf | `.snap` file | node dump `,s *` | per-leaf read |
|---|---|---|---|
| `ch.1.flt.hcf` | `10018.26074` | `10k02` | `10018.2607421875` (exact) |
| `ch.1.eq.lq` | `0.997970223` | `1.00` | `0.9979702234268188` (exact) |
| `ch.1.flt.lcs` | `"24"` (string) | `24` | `'24'` (string kept) |

**This contradicts the official document**, which claims a `,s *` node dump
"will strictly correspond to what would be saved in a snap file". It corresponds
in *which keys exist*, not in *precision*. Therefore:

> **Node dumps discover shape. Per-leaf reads carry values. Never take a value
> from a node dump.**

### 2.4 Two hazards absent from the document

**(a) Node-dump replies cap at roughly 2 KB, not the documented 32 KB.**
Measured: `/aux/1 ,s *` = 1772 B ok · `/bus/1 ,s *` = 1276 B ok ·
`/ch/1 ,s *` (about 2100 B) returns **no reply at all**, and that is the very
example the official document prints.

**(b) A request that produces no reply wedges the client socket.** Measured:
send `/ch/1 ,s *`, get no reply, then send `/ch/2/fdr` **on the same socket** —
it also times out. A fresh socket works at once. Two causes share this
signature: an oversized node dump, and a **GET on an address that does not
exist** (`/ch/40/zzz` and `/ch/99/fdr` both reproduce it).

> The client MUST treat a timeout as "rotate the source port", not merely
> "retry". Retrying on the same socket cannot succeed.

### 2.5 Throughput

Pipelining — fire a batch, then collect — is fast and nearly lossless:

- **10 760 leaf reads in 3.81 s = 2822 reads/s, 8 lost (0.07 %)** at batch 200
- batch 500 is worse: 4.86 s, 27 lost. **Use batch 200.**
- 269 leaves per channel; whole console is about 24 430 parameters, roughly **9 s**
- A retry pass for the ~0.1 % that drop is mandatory, not optional

An adaptive walk that discovers the 2 KB ceiling at runtime cost 1220 requests
of which 59 timed out at 1.5 s each — 88 s of the 100 s total. Hence the shape
descriptor in §4 is computed once and cached, never re-probed per run.

### 2.6 Writing

Verified on the lab desk. All three set forms work on FW 3.1:

```
/ch/40/fdr  ,f  -6.0      fader becomes -6.0
/ch/40/fdr  ,s  "-12.5"   fader becomes -12.5
/ch/40/mute ,i  1         mute on
/ch/40/name ,s  "PROBE"   name set
/ch/40/mute ,i  -1        TOGGLE, verified flipping both directions
```

Multi-parameter node writes work in all three documented forms:

```
/ch/40 ,s "fdr=4,mute=1"                          reply  /*  ,s OK
/      ,s "/ch.40.fdr=-3,mute=0"                  reply  /*  ,s OK
/      ,s "/ch.40.fdr=-8,mute=1,/dca.16.fdr=-5"   reply  /*  ,s OK
```

**The reply address is `/*` for the relative form too.** The document shows
`/ch/1*` for a relative node write; the console sends `/*`. Match on the payload
string, not on the reply address.

Error payloads observed, all on address `/*`:

| condition | reply |
|---|---|
| unknown leaf in a node write (`nosuchparam=1`) | `NODE NOT FOUND` |
| unknown node (`/nosuch.1.fdr=0`) | `NODE NOT FOUND` |
| bad enum value (`proc=NOPE`) | `VALUE ERROR` |
| assigning to a node (`/ch.40=1`) | `NODE IS NOT PAR` |

Documented but not yet observed: `BUFFER OVERFLOW`, `INCOMPLETE DATA`,
`STACK EMPTY`. Treat any unrecognised payload as an error, not as success.

**Out-of-range values are silently clamped and return `OK`.** Measured:
`fdr=999` stores **+10.0 dB**; `fdr=-999` stores **-oo (-144)**. The console
never refuses a level.

> Because the console clamps rather than rejects, `OK` is not proof the value
> landed. **Every write must be verified by reading the leaf back.**

### 2.7 String quoting

Per-leaf reads return strings verbatim. The four hostile names `VOX, LEAD`,
`A=B`, `IT'S OK` and `X,Y=Z` all round-tripped byte-for-byte through a `,s` set
followed by a `,s` get.

Node dumps quote a value containing `,` or `=` in **single quotes**:
`...,16.name='A,B=C',col=1,...`. The node-text parser must honour that.

## 3. Node-text grammar (`,s *` replies)

Used for **shape discovery only**. Assignments are comma-separated; `.` walks
the tree; a leading `.` pops one level per dot.

```
/ch/1/in *   set.srcauto=0,altsrc=0,inv=0,...,dlyon=0,.conn.grp=LCL,in=1,...,.
             |                 |                 |
             descend into set  stays in set      pop out of set, descend conn

/mtx/1 *     in.set.inv=0,trim=0.0,bal=0.0,..dir.on=0,...
                                           |
                                           pop TWO levels
```

Values may be single-quoted; `-oo` means -144.

## 4. Architecture

Read: walk the schema once, then pipelined per-leaf reads, then a nested dict,
then a `RawScene`, then the existing `WingScene`, unchanged.

**Nothing in `core/`, `query/`, `advisory/` or `showcontext/` changes**, because
`WingScene.__init__` already takes a `RawScene` rather than a path
(`wing_parser/query/scene.py:26`). The build layer already coerces with
`bool(...)`, `float(...)`, `int(...)`, so OSC's int `1` lands correctly where
the JSON holds `true`, and `int("24")` handles the string-typed `lcs`.
**Analysis therefore needs no type map.** Only writing a `.snap` file that
WING-Edit will re-open needs exact JSON types (§5).

### 4.1 Modules — one responsibility per file, ~200 lines maximum

| file | responsibility |
|---|---|
| `net/codec.py` | OSC encode/decode: 4-byte padding, tags `s/f/i/b`, triplet replies |
| `net/client.py` | UDP socket; single request; pipelined batch (200); retry pass; timeout means rotate source port |
| `net/identity.py` | `WING?` on 2222, giving name, model, serial, firmware |
| `net/schema.py` | recursive `,s ?` walk to a leaf inventory with declared types; skips `$` |
| `net/nodetext.py` | parse `,s *` node text per §3 — shape only, never values |
| `net/snapshot.py` | leaf reads to nested `ae`/`ce` dicts to a `RawScene` |
| `net/jsontypes.py` | restore exact JSON types for file export |
| `net/write.py` | set, toggle, node write, dry-run, read-back verify |
| `net/data/wing_shape.yaml` | cached leaf inventory, so §2.5's 88 s of probing happens once |
| `net/data/wing_jsontypes.yaml` | generated JSON-type oracle (§5) |
| `cli/net_commands.py` | the `wing net` command group |

`RawScene` (`core/loader.py:14`) gains a `source: str` field defaulting to the
file path, so `WingScene.path`, `__repr__` and the
`f"no channel {number} in {self.path.name}"` messages stay meaningful for a
console target.

## 5. JSON type oracle

A live read gives `lc = 0` where the file holds `false`, and `acc = 0` where the
file holds `0`. The OSC schema cannot separate those — both declare
`int [0 .. 1]`. So the oracle is **generated from the two reference files**
(`user-files/example-Vu.snap`, `user-files/factory-scene.snap`) as a shape-path
map (`ch.*.flt.lc` to bool, `ch.*.flt.lcs` to str), committed as
`net/data/wing_jsontypes.yaml`, with the OSC schema as fallback for paths the
references do not cover. Generation is a script under `examples/`, not runtime
code. Correctness is proven by the round-trip in §7, not by inspection.

## 6. Write safety

1. **Dry-run is the default.** Nothing leaves the socket without `--confirm`.
2. **Identity is echoed before any write** — name, model, serial.
3. **Optional serial pin** via `WING_WRITE_ALLOW_SERIAL`; when set and not
   matching, the write is refused. Off by default.
4. **Read-back verify after every write** — mandatory, because §2.6 shows the
   console clamps silently and still answers `OK`.

`core/normalizer.from_db` already exists as the inverse conversion and is
reused for level writes.

## 7. Verification

Offline, with no console present, and the FastMCP test still skipping:

```powershell
python -m pytest tests/
python -m wing_parser.cli doctor user-files\example-Vu.snap
python -m wing_parser.cli doctor user-files\factory-scene.snap
```

The first real file must still yield **exactly 22 findings**, the second none.

Live behaviour is tested by replaying against `tests/fake_wing.py`, a loopback
UDP server driven by `tests/data/wing_osc_fixtures.json` (74 recorded exchanges,
including the three deliberate no-reply cases) and
`tests/data/wing_write_fixtures.json`. **No test touches the network.**

**The round-trip is the proof of fidelity, and it is self-verifying** — it needs
no human at the console:

1. `wing net push <ip> user-files/example-Vu.snap --confirm` writes the whole
   scene to the desk over OSC
2. `wing net snapshot <ip> -o live.snap` reads it back
3. `wing diff user-files/example-Vu.snap live.snap` must report **zero changes**

Any difference is either a fidelity bug or a rack-vs-full-console difference
that must be **explained in writing**, never waved away.

**Coverage is measured, not claimed.** A test compares the leaf inventory in
`wing_shape.yaml` against every key path present in the two reference `.snap`
files, and fails if the subsystem cannot reach one of them.

## 8. Out of scope

Realtime subscription (`/*S~`), metering (native UDP channel 3, the doorway to
sub-project E), the native binary/TCP interface on 2222, and MCP live support
(handoff §5.4 stays open).
