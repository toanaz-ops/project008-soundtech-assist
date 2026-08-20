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
convenience subset. Coverage is measured, not asserted (§2.10).

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

**(b) An oversized node dump poisons every reply that follows it on the same
socket.** This is sharper and nastier than a simple timeout. Measured with a
batch of 20 known-good `/ch/N/fdr` reads:

| batch | replies received |
|---|---|
| 20 good requests only | **20 / 20** |
| oversized dump **first**, then 20 good | **0 / 20** |
| 10 good, oversized dump, 10 good | **10 / 20** — everything after it is lost |
| 10 good, **nonexistent address**, 10 good | **20 / 20** |

Two conclusions, and the second corrects an earlier draft of this document:

1. An oversized dump kills the console's reply stream to that source port. It is
   not recoverable in place — but **rotating the source port and resending
   recovers completely**, measured 20 / 20 on the retry.
2. **A GET on an address that does not exist is harmless.** It simply produces
   no reply for that one request; the socket keeps working and every other
   reply in the batch still arrives. An earlier draft claimed otherwise; that
   claim came from a probe loop that rotated its socket after every timeout and
   so never actually tested it.

> Therefore: **never put a request that might be oversized into a pipelined
> batch.** Missing addresses are safe to pipeline; oversized dumps are not.

**Schema queries can never be oversized**, which is what makes the architecture
in §4 work. A `,s ?` reply lists only one node's immediate children and never
recurses. Largest observed across the whole tree: **1312 B** (`/ch/1`), against
`/bus/1` 908, `/aux/1` 868, `/$ctl/user` 932, `/ch` 972. Node *dumps* by
contrast reach 1832 B (`/io/in/LCL`) before the ceiling bites.

### 2.5 Throughput

Pipelining — fire a batch, then collect — is fast and nearly lossless:

- **10 760 leaf reads in 3.81 s = 2822 reads/s, 8 lost (0.07 %)** at batch 200
- batch 500 is worse: 4.86 s, 27 lost. **Use batch 200.**
- 269 leaves per channel; whole console is **25 060 leaves**, roughly **9 s**
- A retry pass for the ~0.1 % that drop is mandatory, not optional

The schema walk is the same story. Done one request at a time it takes **55 s**
(5332 requests). Done as a **breadth-first walk with each level pipelined**, the
identical result takes **0.95 s** with zero unresolved nodes — a 58× difference,
and the reason §4 walks the schema fresh on every snapshot instead of caching it.

Whole-console snapshot is therefore about **10 s**: 0.95 s of shape plus ~9 s of
values.

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

**WING over-pads a string whose length is exactly `4k-1`.** OSC 1.0 pads a
string with 1-4 NULs to a multiple of 4, so an 11-character string occupies 12
bytes. Measured on the wire:

| payload | length | OSC 1.0 says | WING sends |
|---|---|---|---|
| `OK` | 2 | 4 | 4 |
| `NODE NOT FOUND` | 14 | 16 | 16 |
| `VALUE ERROR` | 11 | 12 | **16** |
| `NODE IS NOT PAR` | 15 | 16 | **20** |

Only the two whose length is `4k-1` differ, and both gain exactly 4 bytes. The
official document shows `VALUE ERROR` over-padded the same way but shows
`NODE IS NOT PAR` at 16, which this firmware contradicts.

Consequence: **decoding must ignore trailing padding, and a byte-exact
re-encode of a console reply is not always possible.** That costs nothing in
practice -- this subsystem encodes requests and decodes replies, never the
reverse -- but a round-trip test must assert the *decoded value*, not the bytes.

### 2.8 A latent parser bug this work exposed

`query/build_blocks.build_dyn` read the dynamics ratio with `float(...)`. A
compressor stores a number, but **a gate stores the string `"1:3"`**, and a
WING defaults its aux dynamics to `GATE`. Neither reference `.snap` contains a
gate on a strip -- both carry only `CMB` and `COMP` -- so the whole test suite
passed while the parser could not open a scene saved from an untouched desk.
Reading the live console raised `ValueError: could not convert string to float:
'1:3'` on **7 of 8 aux strips**.

Fixed here rather than worked around in `net/`, because it is a file-path bug
that live data merely revealed. `Dyn.ratio` is now `float | None`, `None` for
the `a:b` form -- matching the sibling `Gate`, which models no ratio at all for
the same reason. **No advisory rule reads `Dyn.ratio`**, so no finding changes;
`example-Vu.snap` still yields exactly 22 and `factory-scene.snap` still none.

> Open question for ToanAZ: should a gate's `1:3` be modelled as a number at
> all, and if so with which convention? Left as `None` rather than guessed.

### 2.9 The JSON tree is dynamic — a cached inventory would be wrong

A node's parameter set changes with the value of its model key. Proved by
controlled experiment on `/aux/1/dyn`, writing `mdl` and re-reading the schema:

| `dyn/mdl` | parameters the node exposes |
|---|---|
| `GATE` | `on mix gain thr mdl` + **`acc range att hld ratio rel`** |
| `COMP` | `on mix gain thr mdl` + **`auto det env knee ratio att hld rel`** |
| `CMB` | `on mix gain thr mdl` + **`cmode cpeak depth fast ingain peak`** |

`example-Vu.snap` holds `aux.1.dyn.mdl = COMP` and carries exactly the COMP key
set. Two schema walks taken minutes apart across the *whole console* differed by
exactly six leaves — `acc, range` present in one and `auto, det, env, knee` in
the other — and by nothing else, because `/aux/1/dyn/mdl` was `GATE` during the
first walk and `COMP` during the second. Nothing else in 25 060 leaves moved.

This has two consequences that shape the whole subsystem:

1. **Shape must be discovered per snapshot, never cached.** A static leaf
   inventory would silently omit parameters that exist on a loaded desk. At
   0.95 s the walk is cheap enough that there is no reason to cache it.
2. **Writes must be ordered.** Setting `dyn.ratio` before `dyn.mdl=COMP` targets
   a leaf that does not exist yet and earns `NODE NOT FOUND`. See §6, item 5.

### 2.10 Coverage against the reference files

Measured: the two reference `.snap` files hold **28 635** distinct scalar leaves
between them; the empty lab console exposes **25 060**. The 3 613 in the files
but not on the console are **not** protocol gaps — every one is explained:

| count | path shape | why |
|---|---|---|
| 3 190 | `/$ctl/layer/WEDIT/…` | WING-Edit's own layer layout; exists only once WING-Edit has connected |
| 128 | `/io/in/SC/…` | StageConnect inputs; no SC device attached to the lab rack |
| 48 | `/aux/N/dyn/{cmode,cpeak,depth,fast,ingain,peak}` | §2.9 — the file's aux dynamics are in a different model |
| rest | `/$ctl/user/…` | user-button assignments, dynamic per §2.9 |

Conversely 36 leaves are reachable but in neither file — `/aux/N/dyn/{acc,range,att,ratio,hld,rel}`,
again §2.9. **The subsystem must therefore be judged on whether it can reach
whatever the console currently exposes, not against a fixed list.**

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

Two phases, both pipelined, both safe for the reasons measured above:

```
phase 1  SHAPE    breadth-first ',s ?' walk, each level pipelined      0.95 s
                  safe to pipeline: a schema reply can never overflow (§2.4)
                  fresh every run: the tree is dynamic (§2.9)
                          |
                          v  25 060 leaf addresses + declared types
phase 2  VALUES   per-leaf GET, batch 200, retry pass for the ~0.1%    ~9 s
                  safe to pipeline: a missing address does not poison (§2.4)
                          |
                          v
                  nested ae / ce dicts -> RawScene -> WingScene, unchanged
```

**Node dumps are not on this path at all.** They are the one request shape that
can overflow and poison a batch, and their values are lossy (§2.3). `nodetext.py`
therefore exists only to read a dump as a fast human-facing cross-check, and
nothing in the snapshot path may depend on it. There is no cached shape file:
`wing_shape.yaml` is **deleted from the design** — §2.9 shows it would be wrong
and §2.5 shows it would save less than a second.

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
| `net/client.py` | UDP socket; single request; pipelined batch (200); retry pass; rotate source port after a poisoned batch (§2.4) |
| `net/identity.py` | `WING?` on 2222, giving name, model, serial, firmware |
| `net/schema.py` | **breadth-first** `,s ?` walk, each level pipelined, to a leaf inventory with declared types; skips `$` except `/$ctl` |
| `net/nodetext.py` | parse `,s *` node text per §3 — cross-check only, never on the snapshot path (§4) |
| `net/snapshot.py` | leaf reads to nested `ae`/`ce` dicts to a `RawScene` |
| `net/jsontypes.py` | restore exact JSON types for file export |
| `net/write.py` | set, toggle, node write, dry-run, read-back verify |
| `net/data/wing_jsontypes.yaml` | generated JSON-type oracle (§5) |
| `cli/net_commands.py` | the `wing net` command group |

`RawScene` (`core/loader.py:14`) gains a `source: str` field defaulting to the
file path, so `WingScene.path`, `__repr__` and the
`f"no channel {number} in {self.path.name}"` messages stay meaningful for a
console target.

## 5. JSON type oracle

Smaller than first designed, because the OSC reply tag already settles most of
it. Measured against a 600-leaf live sample cross-checked with both reference
files, these three rules classified every leaf correctly:

| reply tag | `.snap` representation |
|---|---|
| `,s` | JSON string |
| `,sff` | JSON number, **written without a trailing `.0`** when integral |
| `,sfi` | JSON int **or** JSON bool — the tag cannot say which |

The `.0` rule is WING's own convention, not a guess: neither reference file
contains a single `":N.0"`. So an integral float must be emitted as a bare
integer for the file to look like one the console wrote.

That leaves exactly one open question — **which integers a `.snap` writes as
`true`/`false`** — and that is the whole oracle. It is generated by
`examples/generate_jsontypes.py` from the two reference files into
`net/data/wing_jsontypes.yaml`: **342 shape paths**, where a shape path
collapses numeric segments (`ch/7/eq/on` and `ch/31/eq/on` share `ch/*/eq/on`),
and `ce_data` is rooted at `$ctl` to match the OSC address space.

**18 of the 342 are a genuine WING inconsistency, not a modelling failure.**
The send `plink` family is `1` in `example-Vu.snap` and `true` in
`factory-scene.snap` — the same shape, written both ways by the console itself.
Values never leave `{0, 1}` and every consumer coerces with `bool()`, so taking
bool for them costs nothing. Byte-exact type reproduction is therefore
**impossible in principle** for those 18, which is worth stating plainly rather
than leaving a future reader to rediscover.

None of this affects analysis. `wing diff` compares built records, not raw
JSON, and the build layer coerces with `bool()`/`float()`/`int()` — so the
oracle matters only for producing a file that reads back as WING's own.

## 6. Write safety

1. **Dry-run is the default.** Nothing leaves the socket without `--confirm`.
2. **Identity is echoed before any write** — name, model, serial.
3. **Optional serial pin** via `WING_WRITE_ALLOW_SERIAL`; when set and not
   matching, the write is refused. Off by default.
4. **Read-back verify after every write** — mandatory, because §2.6 shows the
   console clamps silently and still answers `OK`.

5. **Writes are ordered, and the order is discovered, not hardcoded.** §2.9
   shows a leaf can fail to exist until its node's model key is set. Rather than
   maintain a list of which keys are magic — which would rot as firmware changes
   — `write.py` converges:

   ```
   repeat:
       write every pending leaf the current schema says exists
       re-walk the schema for the nodes just touched
       until a pass writes nothing new
   ```

   A leaf still unwritten when the loop stops is **reported as unreachable**,
   never silently dropped.

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

**Coverage is measured, not claimed** — see §2.10, which already does this and
explains every one of the 3 613 differences. The standing test is the round-trip
above: whatever the console exposes must survive push, read-back and diff. A
fixed expected-leaf list would be wrong for the reason §2.10 gives.

## 8. Out of scope

Realtime subscription (`/*S~`), metering (native UDP channel 3, the doorway to
sub-project E), the native binary/TCP interface on 2222, and MCP live support
(handoff §5.4 stays open).
