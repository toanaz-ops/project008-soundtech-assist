# WING remote control — probed against a live console

**Date:** 2026-08-18 · **Console:** WING RACK at `192.168.128.28`, firmware
`3.1-0-g9f314617:release`, made available by ToanAZ · **Result: the OSC address
vocabulary is now derived, verified and checked in.**

This supersedes the earlier version of this document, which concluded the
address vocabulary could not be obtained here. It could: the console describes
itself.

## Why this was probed

Sub-project C — read a running WING over the network — needs two separate
things, and they were being treated as one:

1. **A transport.** Where to send, over what, on which port.
2. **An address vocabulary.** What to send: the OSC address for a channel's
   fader, a send's mode, a mute.

Both are now answered.

## 1. The transport

From the WING manual, `user-files/User-Manual_WING-series_2025-10-20.pdf` p50
(`SETUP → REMOTE`), and confirmed by ToanAZ as correct:

| Fact | Source |
|---|---|
| OSC remote control on **UDP port 2223** | manual p50; **verified** — this probe talks to it |
| A second remote-control channel on **port 2222** | manual p50 |
| WING Edit, WING Copilot and Mixing Station use the **2222** channel, not OSC | ToanAZ; **verified** — `Get-NetTCPConnection` shows WING-Edit 3.2.1 established to `192.168.128.28:2222` |
| **REMOTE LOCK** (`SETUP → REMOTE`) locks either port, independently | manual p50; ToanAZ |
| Locking **TCP 2222** leaves those apps connected but **read-only** | ToanAZ |
| Up to **16 devices** may remote-control one WING | manual p50 |
| Console must be wired by Ethernet; clients may be wireless | manual p50 |

**REMOTE LOCK is not a safety net for OSC probing, and it is worth being clear
about why.** Locking 2222 protects the TCP path that WING Edit uses; it does
nothing to 2223. Locking 2223 blocks OSC outright, including the probe. So there
is no setting that makes the OSC port read-only. Safety here came from the shape
of the packets instead — see §4.

**A search trap:** the manual spells the second port's protocol **"TPC"**, not
"TCP". Searching the PDF for "TCP" returns nothing.

## 2. The protocol is self-describing

**This is the finding that changes sub-project C.** Sending an OSC message with
an empty argument list to a node returns that node's children as a list of
strings; sending one to a leaf returns its value.

```
--> /                    <-- /     ,sssssssssssssssss  ['$stat','cfg','$syscfg','io','ch','aux',
                                    'bus','main','mtx','dca','mgrp','fx','cards','play','rec',
                                    '$ctl','$globals']
--> /ch                  <-- /ch   ,ssss…  ['1','2', … ,'40']
--> /ch/1/send           <-- ,ssss…  ['1'…'16','MX1'…'MX8']
--> /ch/1/send/8         <-- ,ssssss  ['on','lvl','pon','mode','plink','pan']
--> /ch/1/send/8/mode    <-- ,s  ['PRE']
```

So the vocabulary does not have to be documented or transcribed. It can be
**walked**, and `probes/osc_walk.py` does exactly that: 1826 queries, 94 seconds,
900 leaves, written to `docs/handoff/2026-08-18-wing-osc-schema.json`.

`/?` is an identify query, answered on address `/*` with one comma-separated
string. Field layout, values from this console with the identifying two
redacted:

```
WING , 192.168.128.28 , <console name> , wing-rack , <serial> , 3.1-0-g9f314617:release
family    ip             name             model      serial     firmware
```

## 3. The address tree and the scene-file key tree are the same tree

Previously written down as *"a resemblance, not a finding"* and explicitly not to
be built on. It is now a finding, measured across the whole tree rather than
inferred from one example. Comparing the walked schema against
`user-files/example-Vu.snap`:

| Node | children in OSC | keys in file | only in OSC | only in file |
|---|---|---|---|---|
| root vs `ae_data` | 13 | 13 | — | — |
| `/ch` | 40 | 40 | — | — |
| `/ch/1` | 37 | 28 | — | — |
| `/bus` · `/aux` · `/main` · `/mtx` | 16 · 8 · 4 · 8 | same | — | — |
| `/dca` · `/mgrp` · `/fx` | 16 · 8 · 16 | same | — | — |
| `/io` · `/cfg` | 4 · 8 | same | — | — |

`$`-prefixed names excluded from the comparison: they are live values —
`$fdr`, `$mute`, `$solo` — which a saved scene does not carry.

**Every key the file has, the console has, at the same position.** The OSC tree
is a superset: it also exposes runtime state and some settings a scene does not
store.

Two differences, both explained, neither a protocol mismatch:

- **`/fx/1`** shows 6 children against the file's 34. FX parameters depend on the
  effect model loaded in that slot, and this console currently has a different
  one loaded than `example-Vu.snap` saved. **Consequence: no repair descriptor
  may assume a fixed key set under `/fx`.** None does today.
- **`/rec`** lacks the file's `path`.

Concretely, every path in `wing_parser/edit/data/repairs.yaml` was checked
end-to-end against the live console:

| Repair descriptor path | OSC address | Console replied |
|---|---|---|
| `ae_data.ch.1.send.8.mode` (G8, R4) | `/ch/1/send/8/mode` | `,s ['PRE']` |
| `ae_data.ch.16.in.set.inv` (PB1) | `/ch/16/in/set/inv` | `,sfi ['0', 0.0, 0]` |
| `ae_data.ch.1.mute` (PC8) | `/ch/1/mute` | `,sfi ['0', 0.0, 0]` |
| `ae_data.ch.1.flt.lc` (S1) | `/ch/1/flt/lc` | `,sfi ['0', 0.0, 0]` |
| `ae_data.ch.1.main.1.pre` (R5) | `/ch/1/main/1/pre` | `,sfi ['0', 0.0, 0]` |

Every one queried directly against the console, not read off the walked
schema. `send.on` and `main.on` (R1, R2, R3, R3M, R6) sit beside `mode` and
`pre` in the same nodes, both of which answered.

`/ch/1/send` returning `1…16, MX1…MX8` also confirms at the protocol level the
matrix-send distinction found earlier from the file alone: `MX5` and `5` are
different destinations on the console too, not an artefact of the file format.

## 4. How this was kept safe, and what remains unproven

`probes/osc_probe.py` builds packets with `message(address)`. **There is no
parameter for arguments and no code path that encodes one** — every packet it
can emit carries the type-tag `","` with an empty type list. A console cannot be
given a new value without a value being sent, so nothing in this probe is able
to change a parameter. That is a property of the code, not a promise.

The residual risk is an address that is itself an action needing no argument —
a snapshot recall, say. Handled by choosing addresses rather than by code:
nouns only, and the very first packet went to
`/wing_parser_probe_does_not_exist`, which cannot be anything. It drew no reply,
which also established that the console does not answer indiscriminately, so
every later reply identified a real address.

**Nothing about writing has been tested, and nothing should be without ToanAZ
present and a console that is not in a show.** The open question is visible in
the reply shapes:

| Reply shape | Count | Meaning | Example |
|---|---|---|---|
| `,sfi` | 379 | text, normalised float, integer | `/cfg/dcamgrp` → `['1', 1.0, 1]` |
| `,sff` | 309 | text, normalised float, real value in units | `…/$lvl` → `['-4.6', 0.6353, -4.5882]` |
| `,s` | 212 | text only | `/cfg/mainlink` → `['OFF']` |

A read returns **three representations of one value**. Which one a *write* must
carry — the text token, the normalised 0–1 float, or the real value — is not
derivable from a read and must be established deliberately. Getting it wrong on
`,sff` is the difference between −4.6 dB and 0.64 dB.

## 5. Reproduction (PowerShell)

From the repository root, with the console reachable:

```powershell
python probes\osc_probe.py "/?" "/" "/ch/1/send/8/mode"
```

```powershell
python probes\osc_walk.py
```

The walk writes `wing-osc-schema.json` into the working directory and takes
about 95 seconds on a LAN.

**Do not run these through Git Bash.** MSYS rewrites any argument that looks
like a POSIX path, so `"/"` arrives as `C:/Program Files/Git/` and `/ch/1/fdr`
becomes a Windows path. The first run of this probe hit exactly that and would
have concluded the console ignores OSC. Under `bash`, prefix with
`MSYS_NO_PATHCONV=1`.

## 6. Superseded

The following were concluded in the earlier version of this document and are now
wrong. They are kept so the correction is legible:

- *"The address vocabulary is not here and has to come from an external protocol
  reference or from observing a live console."* Half right: observation was the
  answer, but it did not need packet capture. The console answers direct
  questions.
- *"`WING-Edit.exe` yields nothing to a string scan, and unpacking it is the
  expensive next step."* True but irrelevant. The binary never had to be opened.

Still true and still worth not repeating: the manual contains no address table
(one page of 167 mentions OSC, only to say the port can be locked), and no
packet-capture tooling is installed on this machine — `tshark`, `dumpcap` and
`npcap` are all absent, though `pktmon` ships with Windows.

## 7. What sub-project C now needs

Not discovery. Design. The vocabulary is in
`docs/handoff/2026-08-18-wing-osc-schema.json`, the transport is known, and
`wing_parser/edit/journal.py` already produces the patches a write path would
send. Open questions for that cycle, in order:

1. **Which representation a write carries** (§4). Answer with ToanAZ present.
2. **Whether the console pushes changes unsolicited**, or must be polled. Not
   probed — a subscription mechanism, if one exists, was not looked for.
3. **How `ce_data.osc.ronly` relates to REMOTE LOCK.** Both sample files hold
   `{"ronly": false}`. Whether toggling REMOTE LOCK moves that flag is a
   one-minute experiment at the console and is still unanswered.
