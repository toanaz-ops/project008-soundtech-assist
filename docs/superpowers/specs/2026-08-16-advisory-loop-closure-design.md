# Advisory loop closure — design spec

**Date:** 2026-08-16 · **Status:** design agreed, not yet planned
**Predecessor:** `2026-08-13-wing-scene-skill-design.md` (Phase 1, delivered)

---

## 1. Purpose

Phase 1 built a three-layer advisory engine — base rules, ToanAZ's principles,
per-show overrides — and proved every mechanism with tests. What it did not do is
let ToanAZ actually use the upper two layers. The `toanaz` layer holds a stub that
can never fire, the `show` layer holds nothing, and two of the three base rules
cannot express the condition their own rationale states.

This spec closes that gap. It is deliberately small. It adds no new rules, no new
scene analysis, and no new probes.

### 1.1 What clarification changed

The Phase 2 handoff recorded four open questions built on a reading of ToanAZ's
worked example that turned out to be wrong. He was asked directly, and the
answers reshaped the work:

- **Pre-fader is his norm, not his exception.** "Đa phần đều là pre, nhất là show
  lớn." Post-fader monitor sends are a deliberate trade of monitor independence
  for setup speed on small or easy shows. **Base rule G8 is therefore correct for
  him**, and the twelve findings it raises on `example-Vu.snap` are flagging a
  conscious shortcut, not a misconfiguration. The earlier framing of "twelve false
  positives" was a misreading.
- **Show scale is declared, not derived.** He knows before he builds the scene.
  So no `CONDITIONS` probe is needed, and spec §6.3's `iem_mix_count` /
  `band_has_guitar` example conditions are not required for his actual practice.
- **The per-channel pre/post split is a show-time judgement**, not a property of
  the channel. The tool cannot decide it and should not try.
- **Declaring a profile must cost one flag**, not a file written per show.

The consequence is that the largest piece of anticipated work — a condition
taxonomy and the scene analysis behind it — is not needed. What remains is
three narrow fixes and the first real content in `knowledge/toanaz/`.

## 2. Scope

**In scope**

1. `--profile NAME` to select exactly one show-layer file at run time, and the
   fix to the glob defect that makes this necessary.
2. An `any_of` key in the predicate language, so G7 and E6 can express the `OR`
   their rationales already state.
3. Narrowing G7 to the half of its condition that is verifiable today.
4. The first real content in `knowledge/toanaz/`, and removal of a stub whose
   text contradicts ToanAZ's stated practice.

**Out of scope, deliberately**

- New `CONDITIONS` probes. Show scale is declared.
- Any change to G8's predicate. It is correct as written.
- New base rules. That is a separate sub-project.
- Whether G7 should fire on wedges or only on IEM. Still open (§7).
- Everything deferred by Phase 1 spec §14 — OSC, audio analysis, the decision tier.

## 3. Profile selection

### 3.1 The defect this fixes

`advisory/layers.py::_show_rules` globs `knowledge/toanaz/shows/*.yaml` and
`*.yml` and applies every file it finds. Two show files means both are active,
permanently — last week's show still overrides tonight's. No test caught this
because the directory ships empty.

### 3.2 Behaviour

`wing doctor scene.snap --profile small` loads exactly
`knowledge/toanaz/shows/small.yaml`. **With no flag, no show-layer file is
loaded at all.** This is a behaviour change and is the fix.

`principles.yaml` is unaffected by the flag. Principles always apply; only the
show layer is selected.

An unrecognised profile name **raises**, naming the unknown value and listing the
available profiles. It must not degrade to "no profile". This project has shipped
the silent-default defect five times, and here the silent form is the worst
possible one: `--profile smal` would run with G8 still active while its author
believes it is off.

### 3.3 Surfaces

The flag must reach every command that resolves findings, not only `doctor`:

| Surface | Change |
|---|---|
| `wing doctor` | `--profile NAME` |
| `wing feedback` | `--profile NAME` |
| MCP `doctor` tool | `profile` parameter, optional |

`commands.feedback` looks a finding up by id through `scene.advisory.run()`. If
`doctor` and `feedback` see different rule sets, `wing feedback G8:ch.8.send.8`
reports "no such finding" immediately after `doctor` printed it. The two must
agree.

### 3.4 Signatures

```python
active_rules(scene, directory=None, profile=None) -> list[Rule]
suppressed_ids(scene, directory=None, profile=None) -> dict[str, str]
run(scene, directory=None, profile=None) -> list[Finding]
AdvisoryFacade.run(profile=None)      # and .rules(profile=None), .suppressed(profile=None)
```

`profile=None` means no show-layer file. `_show_rules(directory, profile)` returns
`[]` when `profile` is None, and otherwise loads the one named file, raising if it
is absent.

## 4. `any_of` in the predicate language

### 4.1 Syntax and semantics

```yaml
when:
  for_each: bus
  where:                       # every key must match, as today
    bus.role: monitor
  any_of:                      # and at least one clause must match
    - bus.dyn.on: false
    - bus.dyn.model: {not_in: [...]}
```

Each `any_of` entry is itself a `where`-shaped mapping evaluated with the existing
`all_match`, so an entry is an AND-group and the list is OR-ed. That expresses
`(A and B) or C`, which covers both real cases without nesting.

A rule with no `any_of` behaves exactly as today.

### 4.2 Validation, all at load time

| Condition | Result |
|---|---|
| `any_of` is not a list | `ValueError(f"{path}: …")` |
| an entry is not a mapping | `ValueError` |
| an entry contains its own `any_of` | `ValueError` — one level only, no nesting |
| `any_of` is present but empty | `ValueError` |
| an unknown operator inside an `any_of` entry | `ValueError` |

The empty case matters most. `any(...)` over an empty list is `False`, so
`any_of:` with the value left off would silently disable the whole rule — the same
present-but-null shape that has bitten this project five times. It must raise.

The operator-name validation added in the Phase 2 fix wave currently inspects
`where` only. It must recurse into `any_of` entries.

### 4.3 Model and evaluator

`Rule` gains `any_of: tuple[dict[str, Any], ...] = ()` — a tuple, because `Rule`
is a frozen dataclass. `evaluate()` requires `all_match(context, rule.where)` and,
when `any_of` is non-empty, that at least one entry also matches.

`Finding.evidence` records the index of the first matching `any_of` entry under
the key `_any_of`, so a finding can be traced back to the clause that produced it.
The leading underscore keeps it from colliding with a dotted path, since every
other evidence key is one. Rules without `any_of` do not carry the key.

### 4.4 Message discipline

A rule with `any_of` can fire for more than one reason, so **its message must
state facts rather than assert a conclusion.** G7's current message says the
dynamics slot "holds COMP, **not a limiter**". Under `any_of` the same rule could
fire because a genuine limiter is loaded but bypassed, making that sentence false.

Messages for `any_of` rules render the fields (`{bus.dyn.model}`, `{bus.dyn.on}`)
and let the reader draw the conclusion.

## 5. Narrowing G7

### 5.1 The problem

G7 decides with `bus.dyn.model: {not_in: [LIM, LIMIT, PRECISION_LIM, BRICK]}`.
Those four tokens appear nowhere — not in either sample `.snap`, not in any
descriptor, not in `docs/knowledge-base/`. The only dynamics models in real data
are `COMP` and `CMB`. G7 therefore cannot *not* fire on a monitor bus.

`user-files/WING_Series_Manual_Knowledge_Base.md` §9.2 names the limiter-capable
processors — Even Comp/Lim (L193), 76 Limiter Amp (L195), Precision Limiter
(L202) — but those are display names, not the stored `dyn.mdl` token, and nothing
found so far establishes the mapping.

### 5.2 Decision

`any_of` separates two clauses of unequal standing:

- `bus.dyn.on: false` — **verifiable today.** Bus 7 `SIDEFILL` has `dyn.on=False`.
  Bypassed dynamics on a monitor bus means no limiting regardless of what is
  loaded. This is an observation, not an inference.
- `bus.dyn.model: {not_in: [...]}` — **not verifiable**, because the token list is
  invented.

**G7 ships with the `dyn.on` clause only, and therefore with no `any_of` at all** —
a single clause belongs in `where`. The model clause is held until ToanAZ reads a
real token off a console; §7.1 records the exact edit, which is what converts G7
to an `any_of` rule.

So G7 is not what exercises `any_of` on delivery. E6 is (§5.4).

### 5.3 Consequences, stated plainly

Finding counts on `user-files/example-Vu.snap`:

| | Today | After §5 | After §5 with `--profile small` |
|---|---|---|---|
| G8 | 12 | 12 | 0 |
| G7 | 4 | 1 (bus 7 only) | 1 |
| E6 | 1 | 1 | 1 |
| **Total** | **17** | **14** | **2** |

The cost: a monitor bus carrying `COMP` **switched on** is no longer reported.
That is exactly the "no limiter at all" case ToanAZ may want to see. It is
accepted because the alternative is a `severity: error` resting on a fabricated
list, and an honest silence beats a confident wrong answer. The README already
tells the reader G7 is not ground truth; §5 makes the code match that admission.

G7's final `severity` depends on the wedge-versus-IEM question in §7.2 and is left
at `error` until it is answered.

### 5.4 E6 gains the clause its rationale already states

E6's rationale says the sources permit a gate alongside an automixer only with
"a gate range of no more than 6 dB **with** a hold of at least 200 ms". That is a
conjunction, so a violation is `range > 6 **or** hold < 200`. The shipped
predicate tests only `range_dB: {gt: 6.0}` and ignores `hold_ms` entirely — a 4 dB
range at 30 ms hold still chatters, which is precisely the failure the cited
sentence exists to prevent, and E6 stays silent on it.

E6 becomes:

```yaml
    when:
      for_each: channel
      where:
        channel.gate.on: true
        channel.post_insert.on: true
        channel.post_insert.automix_group: {not: null}
      any_of:
        - channel.gate.range_dB: {gt: 6.0}
        - channel.gate.hold_ms: {lt: 200.0}
```

**Measured impact on `example-Vu.snap`: none.** Channel 11 `HS4` is the only
channel that satisfies the three `where` conditions at all, and it fails both
clauses (range 40 dB, hold 10 ms), so E6 stays at one finding either way.

That has a direct testing consequence: **the real file cannot discriminate the two
clauses**, because they select the same single target. The test that proves the
hold clause works must synthesise a channel with an acceptable range and a short
hold, the way the existing E6 test already synthesises a switched-on insert.

E6's message must also change under §4.4 — it currently reports only the range,
so a finding raised by the hold clause would name a number that is not the reason.
It renders both fields.

## 6. Content in `knowledge/toanaz/`

### 6.1 The first profile

`knowledge/toanaz/shows/small.yaml`:

```yaml
rules:
  - id: show.small.post-monitors-are-deliberate
    title: "Small show: post-fader monitor sends are the deliberate shortcut"
    severity: info
    source: "ToanAZ, field practice, 2026-08-16"
    rationale: >
      Pre-fader is the norm, especially on a big show. On a small or easy
      show, post-fader monitor sends trade monitor independence for setup
      speed, deliberately. G8 states the generic rule correctly; this
      profile records when its author is choosing against it on purpose.
    supersedes: [G8]
```

### 6.2 A supersede-only rule needs no `when`

The file above has no `when:` block, because the rule has no target of its own —
it exists solely for its `supersedes` list.

`layers._as_rules`, which reads `principles.yaml`, already synthesises a
match-nothing target for exactly this case. `loader.load_rules`, which reads
`shows/`, does not: it raises when `when.for_each` is absent, so writing the file
above today would require a fake clause such as `where: {bus.number: -1}`.

Two readers of one idea, drifted apart — the defect family that produced three
separate bugs in Phase 2. `load_rules` adopts the same synthesis, and the magic
`-1` disappears from both the code and the tests that carry it.

### 6.3 Removing the stub

`knowledge/toanaz/principles.yaml` currently holds
`toanaz.iem-shared-band.guitar-prefader`, `enabled: false`, gated on
`monitor_bus_count: 1`. Two reasons to delete it, the second decisive:

1. Its condition can never match ToanAZ's rig, which has four monitor buses.
2. **Its text contradicts his stated practice.** It reads "guitar sends pre-fader,
   all other sources post-fader" as a standing principle. He has since said the
   opposite: pre-fader is the norm and post-fader is the small-show shortcut.
   Leaving it in place would enshrine a misreading in the file that is supposed to
   hold his judgement.

`principles.yaml` ends this work holding no principles. That is the honest state:
empty because he has not yet needed one, not because the layer is broken. The
explanatory header comments stay, minus the worked example that is no longer true.

## 7. Open questions, carried forward

Neither blocks this work.

### 7.1 The limiter token

What `dyn.mdl` does a WING store when a limiter is loaded? Answering it means
loading one onto a bus and saving the scene. When known, G7 regains its second
clause:

```yaml
  any_of:
    - bus.dyn.on: false
    - bus.dyn.model: {not_in: [<the real tokens>]}
```

### 7.2 Wedges or IEM only

G7's rationale cites two IEM-scoped sources, but its predicate establishes only
`bus.role == monitor`, and three of its four original findings landed on
`SIDEFILL`, `MON L` and `MON R`. Options: split `iem` from `wedge` as distinct
roles in `patterns.yaml`; split G7 into two rules at two severities; or reword the
message. This decides G7's final severity.

## 8. Testing

Every count below is measured against `user-files/example-Vu.snap`.

| Test | What it catches |
|---|---|
| two files in `shows/`, `--profile small` applies only one | The glob defect. **Must fail against current code.** |
| no flag → 14 findings | The show layer is no longer applied automatically |
| `--profile small` → 2 findings | The profile actually suppresses G8 |
| `--profile smal` → raises, listing available names | The silent-typo failure |
| an id printed by `doctor --profile X` resolves under `feedback --profile X` | The two surfaces cannot diverge |
| `any_of: []` → raises | An empty value silently disabling a whole rule |
| nested `any_of` → raises | The one-level constraint |
| unknown operator inside an `any_of` entry → raises at load | Validation currently stops at `where` |
| a target matching neither clause does not fire; matching either does | `any_of` semantics in both directions |
| G7 fires on bus 7 only, message states facts | The narrowed predicate, and message discipline |
| a supersede-only show rule with no `when` loads | §6.2, and no `-1` remains in the tree |
| E6 still fires only on ch.11, on the unmodified file | §5.4 changes no behaviour on real data |
| a **synthesised** channel with range ≤ 6 and hold < 200 fires E6 | The hold clause, which the real file cannot discriminate |
| E6's message names both range and hold | A hold-raised finding must not report only the range |

Two mutations must be demonstrated, because both defects are silent:

- Revert the glob fix — the two-file test goes red.
- Delete the empty-`any_of` guard — a rule stops firing with nothing reported.

## 9. Constraints inherited

Unchanged from Phase 1 and binding here: ~200 lines per source file, split by
responsibility layer; `core/` imports only stdlib, PyYAML and ruamel, never from
a layer above; the advisory engine is deterministic with stable finding order;
files under `knowledge/` are written with `ruamel.yaml` round-trip, never
`yaml.safe_dump`; every `Finding` records its deciding layer; every rule YAML
carries `source:` and `rationale:`; nothing under `docs/knowledge-base/` may be
moved or edited; never fabricate a value the file does not state; float
comparisons in tests use `pytest.approx`.
