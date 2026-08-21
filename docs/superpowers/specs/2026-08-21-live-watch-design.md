# Sub-project C2 — watching a live console, and three small closures

**Date:** 2026-08-21 · **Status:** design authority for `wing_parser/net/watch/`

Every protocol claim in §2 was **measured** against the lab console
`WING-GIAQUY` (`wing-rack`, firmware `3.1-0-g9f314617:release`) at
`192.168.128.28` on 2026-08-21. Where a claim is *not* proven, §2.6 says so
explicitly rather than letting silence read as evidence. Do not promote an
unproven line in §2.6 into a fact without re-measuring.

This spec follows `2026-08-21-wing-net-design.md`, which built `net/` (OSC read
and write). It does not modify that subsystem; it adds a consumer of it.

## 1. Purpose

`wing net` can read a console and write to it, but only in single shots. This
sub-project answers a different question, continuously:

> **What just changed on the desk, and who is it going to affect?**

ToanAZ stated one hard requirement, and it outranks every other goal here:

> **"Cần song song không đá nhau"** — this must run alongside WING-Edit,
> Companion/Stream Deck and any future OSC client without any of them
> displacing another.

That requirement is what selects the mechanism in §3. It is not a preference.

### 1.1 Where this sits against what he asked for

He named four capabilities. Three already shipped in C/D:

| Capability | State |
|---|---|
| Run `doctor`/`analyze` against live state | done — `--live IP` |
| Export running state to a `.snap` | done — `net snapshot -o` |
| Compare a console against a saved file | **partial** — via `net snapshot` then `diff`; §6.2 closes it |
| **Watch continuously: levels, changes** | **this spec** |

## 2. Measured facts

### 2.1 Read-only (`$`) keys exist and are readable over OSC

A `,s "?"` schema query returns one line per key, giving its name, whether it
is a node, and for a leaf its type and range:

```
lock      int [0 .. 1]
ppm       int [-200 .. 200]
usbstate  list [-, ERR, IDLE, BUSY]
```

Note the format is **line-oriented**. Splitting the reply on whitespace shreds
`int [0 .. 1]` into four phantom keys. `net/schema.py` already parses by line
(`_parse_lines`); any new consumer must reuse it rather than re-parse.

Read-only keys found, per family:

| node | read-only keys |
|---|---|
| `/ch/N` | `$col $name $icon $solo $sololed $presolo $fdr $mute $muteovr` |
| `/bus/N` `/main/N` `/mtx/N` | `$col $name $icon $solo $sololed $fdr $mute $muteovr` |
| `/dca/N` | `$solo $sololed` |
| `/io/in/LCL/N` | `$ha $ract $rdest $mute` |
| `/` (root) | `$stat $syscfg $ctl $globals` |

### 2.2 `$fdr` and `$mute` are EFFECTIVE values

`/ch/1/$fdr` reads `sff ('-oo', 0.0, -144.0)` on a factory scene — the same
`-144.0` sentinel `core/normalizer.to_db` already maps to `-inf`.

The `$` form is the value **after** DCA contribution and mute-override are
folded in, where the bare `fdr` is the strip's own position. This is what makes
a watch-list cheap: pulling a DCA down shows up on every channel it governs
without the watcher modelling DCA membership at all.

**Consequence beyond this sub-project:** advisory rules currently read `fdr`
from a file, which is *intent*. `$fdr` is *result*. Whether any rule should
move is a question for ToanAZ (§7.1), not a change to make here.

### 2.3 There is NO meter over OSC

Measured, all silent: `/$meters`, `/meters`, `/ch/1/$ppm`, `/ch/1/$lvl`,
`/ch/1/$meter`, `/main/1/$ppm`, `/$stat/ppm/1`. The root exposes 17 nodes —
`$stat cfg $syscfg io ch aux bus main mtx dca mgrp fx cards play rec $ctl
$globals` — and none is a meter.

`/$stat/ppm` is **not** a meter: it read `sfi ('0', 0.5, 200)` and returned an
identical value on 20 consecutive reads across 2 s. It is a setting with range
`[-200 .. 200]`.

**Therefore metering requires the native protocol** (the `2026-08-21` spec's
"native UDP channel 3"), which is a second transport, not a new use of the
existing one. This is why §5 sequences metering *after* change-watching, which
reverses the order that seemed natural before measuring.

### 2.4 Polling is fast enough that latency is not a design problem

Watch-list of `$fdr $mute $solo` per channel, via `client.get_many`:

| channels | leaves | median round | rounds/s | unanswered |
|---|---|---|---|---|
| 8 | 24 | 0.017 s | 58 | 0 |
| 40 | 120 | **0.022 s** | **44.5** | 0 |
| 48 | 144 | 0.425 s | 2.4 | 24 |

A 208-leaf list (40 ch + 16 bus + 8 mtx + 16 dca) sustained **819 rounds in
90 s**. Its opening sample answered all 208 leaves; the loop did not record
per-round shortfalls, so "no losses across all 819 rounds" is **not** claimed —
only that the loop held its rate. §4.4 measures the rest.

### 2.5 An absent address costs 20x — the watch-list must contain only real ones

The 48-channel row above is not network trouble. The console has 40 channels,
so 8 × 3 = **exactly 24** addresses do not exist, and the retry ladder hunts
for every one of them every round: 0.425 s against 0.022 s.

This is the same asymmetry `2026-08-21-wing-net-design.md` records — a ladder
sized for a poisoned batch is pathological for an absent address.

### 2.6 NOT proven — do not cite these as facts

1. **That subscription is unavailable.** Ten forms were sent and all were
   silent: `/*S~` (bare, `,s ""`, `,i 1`), `/*S ,i 1`, `/*~` (bare and `,i 1`),
   `/xremote`, `/subscribe`, `/%0/*S~`, `/* ,s "?"`. The control `/ch/1/fdr`
   answered throughout, so the harness was sound. **But a subscription reports
   CHANGES, and the desk was idle** — a working subscription would also have
   been silent. This experiment cannot distinguish the two and must be redone
   with a control being moved. Recorded as *unproven*, not as *absent*.
2. **That polling detects a change.** The 90 s / 819 round watch saw 0 events
   because nothing on the desk moved during it. The loop is proven; the
   detection is not. §4.4 makes this the first acceptance test.
3. **That WING-Edit does not hold the subscription.** ToanAZ reports several
   WING-Edit instances connect simultaneously without trouble, which is
   *consistent with* WING-Edit using the native interface rather than an OSC
   subscription — but nobody has measured it. Plausible, unverified.

### 2.7 Break-on-first-silence discovery is unreliable, rarely

A naive walk — probe `/{family}/{n}/$fdr` upward, stop at the first silence —
reported `/main` as **0 present** on one run. `/main/1/$fdr` then answered
**10/10** on a fresh socket, and **10/10** immediately after a deliberate
timeout on a dead address. Repeating the identical walk 6 times over 5 families
(30 walks) reproduced the correct inventory **30/30**.

So the fault is real, rare, and **silent**: one dropped datagram truncates a
whole family to zero and reports nothing. A watch-list quietly missing all four
mains never reports a main fader move, and nothing looks wrong.

**This is the load-bearing reason for §3.2.** It is not a hypothetical.

## 3. Design

### 3.1 Mechanism: poll, do not subscribe

Two ways to learn what changed:

| | `/*S~` subscription | **polling a watch-list** |
|---|---|---|
| latency | near-immediate | one round (measured 22 ms) |
| traffic | low | higher, and bounded by the list |
| catches sub-round transients | yes | **no** |
| **coexists with other clients** | **no — one subscription console-wide, 10 s life** | **yes — consumes no shared resource** |

Polling is a plain request/reply exchange, indistinguishable from what
`net get` already does, so it claims nothing another client can lose. The
exclusivity that makes subscription unusable here is a protocol property, not
an implementation detail, so no amount of care makes subscription satisfy §1's
hard requirement.

The 10 s expiry disappears entirely under polling: there is nothing to renew.

**Decision: polling is the mechanism. `/*S~` is not implemented.** §2.6(1)
records why its silence is not evidence, so a later cycle can revisit it with a
proper experiment rather than re-deriving the question.

### 3.2 The watch-list is built from the schema walk, never by probing upward

`net/schema.py`'s `walk_schema` already retries, rotates a poisoned socket, and
— decisively — returns `unresolved_nodes` **separately** from `leaves` rather
than folding an unanswered node into "absent".

**The derivation is indirect, and must be.** `schema._expand` drops every `$`
child by design (`if name.startswith("$"): continue`, because `$` keys are
absent from `.snap`) — so the very keys this sub-project watches are the ones
the walk will never list. The builder therefore reads the walk for the **strip
set**, not for the watch addresses:

1. `walk_schema(host)` → `leaves`, every ordinary leaf on the desk
2. any address matching `^/(ch|bus|main|mtx|dca)/(\d+)/` proves that strip
   exists
3. the `$` keys from §3.3's YAML are appended to each strip that exists

Measured 2026-08-21 (`docs/probes/probe9_stripset.py`): the walk took **1.00 s**,
returned **25 062 leaves and 0 unresolved nodes**, and implied exactly
40 channels, 16 buses, 4 mains, 8 matrices and 16 DCAs — contiguous from 1,
matching the truth probes 7 and 8 established. The resulting watch-list is
**220 leaves**. One second is the startup cost of a watch session, paid once.

`schema.py` is **not** modified to include `$` keys: it feeds the `.snap`
exporter, where a `$` key would be wrong.

The builder inherits the property that matters: **it can say what it failed to
resolve.** Per §2.7 a builder that cannot say so fails silently and invisibly.

**A watch session whose list is incomplete must say so at startup.** Concretely:
it prints the unresolved addresses to stderr and continues watching the rest —
it does not abort, because a partial watch is still useful, and it does not
print a bare total, because "watching 208 leaves" while four mains are missing
is the exact failure this rule exists to prevent. In `--json` mode the first
object carries `"unresolved": [...]`, so a consumer sees it too.

### 3.3 What is watched is declared in YAML, not in code

Following `descriptors/` and `advisory/base_rules/`, where the engine is code
and the content is data — the pattern that took base rules from 3 to 39 without
the evaluator changing shape.

`net/watch/data/watchlist.yaml`:

```yaml
# Effective values (sec 2.2): $fdr and $mute already fold in DCA and
# mute-override, so a DCA move surfaces on every channel it governs.
families:
  ch:   ["$fdr", "$mute", "$solo"]
  bus:  ["$fdr", "$mute", "$solo"]
  main: ["$fdr", "$mute", "$solo"]
  mtx:  ["$fdr", "$mute", "$solo"]
  dca:  ["$solo"]
```

Widening coverage is a data edit. Adding `$name` to catch renames, or
`/io/in/LCL/N/$ha` to catch preamp changes, needs no Python.

### 3.4 Modules

Three files, each one responsibility, each well under the ~200-line norm.

| file | does | depends on |
|---|---|---|
| `net/watch/list.py` | read the YAML, walk the schema, emit the concrete address list **plus what it could not resolve** | `net/schema.py`, the YAML |
| `net/watch/events.py` | the `Change` record: address, before, after, elapsed, and the human label for the strip | `query/` for names |
| `net/watch/poller.py` | the loop: sample, diff against the previous sample, yield `Change`es, pace itself | `net/client.py`, the two above |

`net/client.py`, `codec.py` and `schema.py` are **not modified**. Polling is a
new consumer of a tested transport, not a change to it.

### 3.5 CLI

```
wing net watch <ip> [--json] [--interval SECONDS] [--until SECONDS]
```

- default `--interval 0.25` — well above the 22 ms floor, leaving the desk and
  the network almost entirely idle between rounds
- startup prints the resolved list size **and any unresolved node**, per §3.2
- each change prints elapsed time, the address, the strip's name, before, after
- `--json` emits one object per line, so a session can be piped and replayed
- `--until` bounds a run; without it, runs until interrupted. Named
  `--until` and not `--for`: argparse accepts `--for`, but its dest is
  then `for`, and `args.for` is a **SyntaxError** — reachable only via
  `getattr(args, "for")`, which no other handler in this CLI does.
  Measured, not assumed; the first draft of this spec said `--for` and a
  Task 4 implementer caught the collision.

Deliberately **not** a full-screen TUI. A line-per-event log is greppable,
pipeable and diffable; a TUI is a separate decision, not a default.

### 3.6 Values are read from the display string, per the established rule

`2026-08-21-wing-net-design.md` §2.3 measured that `,sfi` replies carry a
0-based **index** as the native value, and that taking it would corrupt 1066
leaves while looking reasonable. The rule is `,sff` → native float, `,sfi` →
display string, `,s` → the string. Change detection compares the same
representation the existing codec already yields; it does not re-interpret.

## 4. Testing

### 4.1 Offline, deterministic — the default

The `net` suite's existing pattern: a fake UDP server driven by recorded
exchanges (`tests/data/wing_osc_fixtures.json`). Poller tests drive a scripted
sequence of samples and assert the emitted `Change`es. No console, no sleeps.

### 4.2 The watch-list builder must be tested against a schema that is short

Give `walk_schema` a stub returning a console with 2 channels and 1 bus, and
assert the list contains exactly those addresses — **and** that a stub reporting
an unresolved node produces a list that says so. Per §2.7 the second half is
the one that matters; without it the silent-truncation bug has no test.

### 4.3 A test must be shown to fail

The G1 handoff's lesson: a test that has never been seen red may assert
nothing. Each new test is proven by reverting the production line it covers and
capturing the failure.

### 4.4 Live acceptance — the two experiments §2.6 leaves open

Not automated; run against the lab console and **written up with their output**,
whatever it says:

1. **Detection.** Start `wing net watch`, move one fader, confirm the change is
   reported and note the delay. Closes §2.6(2).
2. **Coexistence.** With WING-Edit connected and driving the desk, run the
   watcher for 5 minutes. Neither may disturb the other. Closes §2.6(3) and is
   the direct test of §1's hard requirement.

A negative result is recorded, not retried into silence — the limiter-token
probe is the precedent.

## 5. Sequencing

1. **§6 small closures** — independent, and they stop MCP falling further behind.
2. **C2 as specced here** — change watching.
3. **Metering** — a separate spec. §2.3 measured that it needs the native
   protocol, so it is a new transport, not an extension of this. It is also the
   doorway to sub-project E, and belongs in a cycle that says so.

## 6. Three closures ToanAZ has approved

### 6.1 MCP gains `show` and `live`

`wing_parser/mcp/tools.py` exposes six tools; `doctor(path, profile)` accepts
neither a show context nor a console, so a Claude session on MCP can see
neither Q1–Q7 nor a desk. Add `show` to `doctor`, and `live` to `doctor`,
`analyze`, `channel` and `routing` — mirroring the CLI, which is the authority.
Closes the open question carried since the G1 handoff.

### 6.2 `diff --live`

`diff` takes two files. Accept `--live IP` for either side, so a console
compares against a saved scene directly instead of by way of `net snapshot`.

### 6.3 Commit the five real scenes

`CAI LUONG`, `GIAQUY_WING`, `LIVE`, `OCHESTRA`, `Snapshot1` — `snapshot.9`
files from WING Edit 3.0, yielding 0, 13, 13, 1 and 17 findings. They were
deliberately left untracked because they are ToanAZ's show data; he was told
that committing writes them permanently into git history, including channel and
artist names, and confirmed on 2026-08-21 that this repo is private and he
wants them in.

Pin each file's finding count in a test, the way `example-Vu.snap`'s 22 and
`factory-scene.snap`'s 0 are pinned. That is the point of adding them: they are
a fivefold wider corpus, and the last cycle found a real parser bug
(`build_dyn` could not read a gate's `"1:3"` ratio) precisely because reference
files were too narrow.

## 7. Open questions — do not guess

1. **Should any advisory rule read `$fdr` instead of `fdr`?** §2.2 establishes
   the two differ: intent versus result. A rule about what the audience hears
   may want the effective value. This is ToanAZ's call about his own judgement,
   and it is a rule-layer question, not a `net/` one.
2. Everything still open in `docs/handoff/2026-08-21-next-session-prompt.md` §5:
   the limiter `dyn.mdl` token, G10's standing, the `expects:` vocabulary, and
   whether a gate's `1:3` ratio should be modelled numerically.

## 8. Out of scope

Metering and the native transport (§5.3), `/*S~` subscription (§3.1, with
§2.6(1) recording what is unproven), the binary/TCP interface on 2222, a TUI
(§3.5), and any change to `net/client.py`, `codec.py` or `schema.py`.
