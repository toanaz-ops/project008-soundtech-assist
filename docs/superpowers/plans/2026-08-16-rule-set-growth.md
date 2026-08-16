# Rule-Set Growth (Sub-Project B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Grow the WING advisory base layer from 3 rules to ~30, split the monitor role into `monitor.iem` / `monitor.wedge`, and make mains and matrices visible to the advisory engine.

**Architecture:** Rules stay YAML data. Cross-object logic becomes tested Python properties on the query layer (`Channel`/`Bus`). The predicate DSL gains exactly one operator (`starts_with`). Three new/extended target iterators (`output`, `channel.main_sends`, matrix destinations in `channel.sends`). Rules carry an `event:` tag filtered by the show profile's declared event.

**Tech Stack:** Python 3 stdlib + PyYAML (`yaml.safe_load` for package data), pytest. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-08-16-rule-set-growth-design.md` — read it before starting any task. Section numbers below refer to it.

## Global Constraints

- ~200 lines per source file; split by responsibility layer if a file would grow past it
- `core/` imports only stdlib + YAML libraries; no layer imports upward
- `core/`, `query/`, `advisory/` are deterministic — no LLM calls
- Fully offline; `mcp` and `anthropic` stay uninstalled; the FastMCP build test must keep skipping
- Never fabricate a value the scene file does not state
- Rules are YAML data with mandatory `source:` and `rationale:`
- Files under `knowledge/` are written with ruamel round-trip only (no task here writes them)
- `docs/knowledge-base/` is read-only
- Float comparisons in tests use `pytest.approx`
- Every real-file count asserted in a test must first be established by running code against the file, never by reading the plan or spec
- Run tests with: `python -m pytest tests/ -x -q` (full) or `python -m pytest tests/<file>::<test> -v` (single)
- All paths relative to repo root. Tests set `monkeypatch.setenv("WING_DISABLE_LLM", "1")` whenever they call `scene.advisory.run()` or `scene.classifier`/role resolution on a full scene, matching the existing suite.

**Raw `.snap` JSON keys used by fixtures** (verified against `user-files/example-Vu.snap` on 2026-08-16): channel = `doc["ae_data"]["ch"]["<n>"]` with `name`, `fdr` (dB, −144 = −∞), `mute`, `flt` (`lc` bool, `lcf` Hz, `lcs` slope string), `main` (`"1"`..`"4"`: `{on, lvl, pre}`), `send` (`"1"`..`"16"`, `"MX1"`..`"MX8"`: `{on, lvl, pon, mode, plink, pan}` — `mode` ∈ PRE/POST/GRP), `gate` (`on, mdl, thr, range, att, hld, rel`), `dyn` (`on, mdl, thr, ratio, att, rel`), `peq` (`on`, `1g/1f/1q` … `leq` shape strings, `SHV` = shelf), `postins` (`{on, mode: "AUTO_X", ins, w}` — `mode` carries the automix group, `w` the weight), `in.set.inv` (polarity), `in.conn.grp` (`"OFF"` = unpatched). Buses/mains/matrices = `doc["ae_data"]["bus"|"main"|"mtx"]["<n>"]` with `name`, `fdr`, `mute`, `dyn`, `eq`, `send`.

**Fixture pattern** (copy exactly; it is the one the existing suite uses):

```python
import json
from wing_parser import WingScene

def _mutated_scene(vu_path, tmp_path, mutate, name="mutated.snap"):
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    mutate(doc["ae_data"])
    out = tmp_path / name
    out.write_text(json.dumps(doc), encoding="utf-8")
    return WingScene.load(out)
```

Put `_mutated_scene` in `tests/conftest.py` as a plain function import target (Task 2 adds it); every later fixture task imports it: `from tests.conftest import _mutated_scene` — pytest exposes conftest on `sys.path`; if that import fails, use `from conftest import _mutated_scene`.

---

### Task 1: `starts_with` predicate operator

**Files:**
- Modify: `wing_parser/advisory/predicates.py` (OPERATORS at line 21, `matches()` at line 39)
- Test: `tests/test_advisory_predicates.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `OPERATORS` contains `"starts_with"`; `matches(value, {"starts_with": prefix})` → `True` iff `value` is a `str` and `value.startswith(prefix)`. Non-string values (None, numbers) → `False`, never an exception. Load-time validation of the new operator comes free via `validation._validate_where`, which checks against `OPERATORS`.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_advisory_predicates.py`:

```python
class TestStartsWith:
    def test_matches_a_prefix(self):
        assert matches("monitor.iem", {"starts_with": "monitor"})

    def test_exact_value_counts_as_its_own_prefix(self):
        assert matches("monitor", {"starts_with": "monitor"})

    def test_rejects_a_non_prefix(self):
        assert not matches("subgroup", {"starts_with": "monitor"})

    def test_none_is_false_not_an_error(self):
        assert not matches(None, {"starts_with": "monitor"})

    def test_a_number_is_false_not_an_error(self):
        assert not matches(7, {"starts_with": "monitor"})

    def test_registered_in_operators(self):
        from wing_parser.advisory.predicates import OPERATORS
        assert "starts_with" in OPERATORS
```

Match the file's existing import style (it already imports `matches`; check the header and reuse it).

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_advisory_predicates.py -k StartsWith -v`
Expected: FAIL — `ValueError: unknown predicate operator 'starts_with'`

- [ ] **Step 3: Implement** — in `predicates.py`: add `"starts_with"` to the `OPERATORS` frozenset; in `matches()` add before the final `else`:

```python
        elif operator == "starts_with":
            if not isinstance(value, str) or not value.startswith(operand):
                return False
```

- [ ] **Step 4: Run the new tests, then the full suite**

Run: `python -m pytest tests/test_advisory_predicates.py -v && python -m pytest tests/ -x -q`
Expected: all PASS (406 passed, 1 skipped, plus the 6 new)

- [ ] **Step 5: Commit**

```bash
git add wing_parser/advisory/predicates.py tests/test_advisory_predicates.py
git commit -m "Add the starts_with predicate operator"
```

---

### Task 2: Advisory targets reach mains and matrices

**Files:**
- Modify: `wing_parser/advisory/evaluator.py` (`_channel_sends` at lines 35–56, `ITERATORS` at line 73)
- Modify: `tests/conftest.py` (add `_mutated_scene` from the header of this plan)
- Test: `tests/test_advisory_evaluator.py`, `tests/test_advisory_rules.py`

**Interfaces:**
- Consumes: `scene.bus_family()` → `tuple[Bus, ...]` (buses+auxes+mains+matrices, exists today in `query/scene.py:128`), `scene.family("main")` → `dict[int, Bus]`.
- Produces: iterator name `"output"` (context key `bus`, target name `f"{bus.kind}.{bus.number}"`, confidence `bus.role.confidence`); iterator name `"channel.main_sends"` (context keys `channel`, `main_send`, `destination_main`; target name `f"ch.{channel.number}.main.{ms.dest}"`; confidence `destination_main.role.confidence`, 0.0 if the main is missing); `"channel.sends"` additionally yields matrix destinations (target name `f"ch.{channel.number}.send.MX{send.dest}"`, context key `destination_bus` bound to the matrix Bus — same key as bus destinations, per spec §3.1).

- [ ] **Step 1: Write the failing tests** — append to `tests/test_advisory_evaluator.py` (it already imports `targets_for` or equivalent — check its header; if it tests via `evaluate`, import `targets_for` directly):

```python
from wing_parser.advisory.evaluator import targets_for


class TestOutputIterator:
    def test_output_yields_buses_mains_and_matrices(self, vu_scene):
        names = [t.name for t in targets_for(vu_scene, "output")]
        assert "bus.7" in names        # SIDEFILL
        assert "main.1" in names       # MAIN FOH
        assert "matrix.5" in names     # IEM MC
        assert len(names) == 16 + 8 + 4 + 8  # bus + aux + main + matrix

    def test_output_binds_the_bus_context_key(self, vu_scene):
        target = next(t for t in targets_for(vu_scene, "output") if t.name == "matrix.5")
        assert target.context["bus"].name == "IEM MC"


class TestChannelMainSendsIterator:
    def test_one_target_per_main_send(self, vu_scene):
        names = [t.name for t in targets_for(vu_scene, "channel.main_sends")]
        assert "ch.1.main.1" in names
        assert len(names) == 40 * 4

    def test_binds_channel_send_and_destination(self, vu_scene):
        target = next(t for t in targets_for(vu_scene, "channel.main_sends")
                      if t.name == "ch.1.main.2")
        assert target.context["channel"].number == 1
        assert target.context["main_send"].dest == 2
        assert target.context["destination_main"].name == "LiveStream"


class TestChannelSendsSeesMatrices:
    def test_matrix_destinations_are_yielded(self, vu_scene):
        names = [t.name for t in targets_for(vu_scene, "channel.sends")]
        assert "ch.1.send.MX5" in names

    def test_matrix_destination_binds_destination_bus(self, vu_scene):
        target = next(t for t in targets_for(vu_scene, "channel.sends")
                      if t.name == "ch.1.send.MX5")
        assert target.context["destination_bus"].kind == "matrix"
        assert target.context["destination_bus"].name == "IEM MC"
```

Add a module-scoped `vu_scene` fixture at the top of the test file if one does not exist:

```python
@pytest.fixture(scope="module")
def vu_scene(vu_path):
    return WingScene.load(vu_path)
```

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_advisory_evaluator.py -k "Output or MainSends or SeesMatrices" -v`
Expected: FAIL — `KeyError: no target iterator named 'output'` and missing MX names.

- [ ] **Step 3: Implement in `evaluator.py`**

Replace `_channel_sends` (keep its docstring's first line; rewrite the matrix note — matrices are now yielded, bound under the same `destination_bus` key, and the name uses the `MX` prefix so `ch.8.send.8` and `ch.8.send.MX8` stay distinct):

```python
def _channel_sends(scene) -> Iterator[Target]:
    """One target per bus or matrix send.

    Both destination families bind under the context key `destination_bus`
    so one rule can range over both; the target name keeps the raw file's
    MX prefix so bus 8 and matrix 8 stay distinct. Mains are a different
    record shape (MainSend) and have their own iterator below.
    """
    buses = {bus.number: bus for bus in scene.buses()}
    matrices = {m.number: m for m in scene.matrices()}
    for channel in scene.channels():
        for send in channel.sends:
            if send.dest_kind == "bus":
                destination, name = buses.get(send.dest), f"ch.{channel.number}.send.{send.dest}"
            elif send.dest_kind == "matrix":
                destination, name = matrices.get(send.dest), f"ch.{channel.number}.send.MX{send.dest}"
            else:
                continue
            yield Target(
                name=name,
                context={"channel": channel, "send": send, "destination_bus": destination},
                confidence=destination.role.confidence if destination else 0.0,
            )


def _outputs(scene) -> Iterator[Target]:
    """Every summing destination: buses, auxes, mains and matrices."""
    for bus in scene.bus_family():
        yield Target(
            name=f"{bus.kind}.{bus.number}",
            context={"bus": bus},
            confidence=bus.role.confidence,
        )


def _channel_main_sends(scene) -> Iterator[Target]:
    mains = scene.family("main")
    for channel in scene.channels():
        for main_send in channel.main_sends:
            destination = mains.get(main_send.dest)
            yield Target(
                name=f"ch.{channel.number}.main.{main_send.dest}",
                context={
                    "channel": channel,
                    "main_send": main_send,
                    "destination_main": destination,
                },
                confidence=destination.role.confidence if destination else 0.0,
            )
```

Register both in `ITERATORS`: `"output": _outputs, "channel.main_sends": _channel_main_sends`.

- [ ] **Step 4: Probe the real-file G8 shift before touching the count test.** G8's `where` is `destination_bus.role: monitor` and matrices `IEM MC`, `IEM CA SI 1/2`, `IEM3 BAKUP` (`\biem\d*\b` → monitor 0.95) and `SIDE` (`^side\b` → monitor 0.85) now enter its domain. Run:

```bash
python - <<'EOF'
import os; os.environ["WING_DISABLE_LLM"] = "1"
from wing_parser import WingScene
scene = WingScene.load("user-files/example-Vu.snap")
found = scene.advisory.run()
for f in sorted(found, key=lambda f: (f.rule_id, f.target)):
    print(f.rule_id, f.target, f.severity)
print("total", len(found))
EOF
```

Record the output in the Step 5 test comment. Every new `G8` target must name an `MX` send whose raw `mode` is `"POST"` and `on` is true — spot-check one against the raw JSON before accepting the number.

- [ ] **Step 5: Update `tests/test_advisory_rules.py::test_the_sample_scene_reports_fourteen_findings`** — rename it `test_the_sample_scene_finding_counts`, set the counts to the probed values, and add a comment stating the date, the probe command, and why the number changed (matrix sends became visible). Add `_mutated_scene` to `tests/conftest.py` (code in the plan header).

- [ ] **Step 6: Full suite**

Run: `python -m pytest tests/ -x -q`
Expected: PASS. If any other real-file assertion broke, fix it the same way — probe first, then assert, never guess.

- [ ] **Step 7: Commit**

```bash
git add wing_parser/advisory/evaluator.py tests/
git commit -m "Extend advisory targets to mains and matrices"
```

---

### Task 3: Monitor role hierarchy — G7 splits into G7 (IEM, error) and G9 (wedge/generic, warning)

**Files:**
- Modify: `wing_parser/classifier/data/patterns.yaml` (buses section, lines 64–72)
- Modify: `wing_parser/query/bus.py` (`is_monitor`, line 71)
- Modify: `wing_parser/advisory/resolver.py` (`_monitor_bus_count`, line 26)
- Modify: `wing_parser/advisory/base_rules/monitors.yaml` (G7, G8)
- Test: `tests/test_classifier_matcher.py`, `tests/test_query_bus.py`, `tests/test_advisory_rules.py`, `tests/test_advisory_resolver.py`

**Interfaces:**
- Consumes: `starts_with` operator (Task 1), `output` iterator (Task 2).
- Produces: bus kinds `monitor.iem`, `monitor.wedge`, `monitor`; `Bus.is_monitor` true for any `monitor`-prefixed confident role; rule ids `G7` (iem, error, `for_each: output`), `G9` (wedge+generic, warning, `for_each: output`), `G8` unchanged id with `destination_bus.role: {starts_with: monitor}`.

- [ ] **Step 1: Write the failing classifier tests** — in `tests/test_classifier_matcher.py`, following its existing test style:

```python
def test_iem_buses_classify_as_monitor_iem():
    for name in ("IEM1", "IEM MC", "in ear 2", "iem3 bakup"):
        assert classify(name, "buses").kind == "monitor.iem", name

def test_wedge_and_sidefill_classify_as_monitor_wedge():
    for name in ("WEDGE 1", "SIDEFILL", "side fill L", "SIDE"):
        assert classify(name, "buses").kind == "monitor.wedge", name

def test_generic_monitor_names_stay_plain_monitor():
    for name in ("MON VOX", "MON L", "Monitor 3"):
        assert classify(name, "buses").kind == "monitor", name
```

And in `tests/test_query_bus.py`:

```python
def test_is_monitor_accepts_the_dotted_monitor_roles(vu_scene):
    sidefill = vu_scene.bus(7)          # SIDEFILL -> monitor.wedge
    assert sidefill.is_monitor
    iem = vu_scene.matrix(5)            # IEM MC -> monitor.iem
    assert iem.is_monitor
```

(Reuse or add the module-scoped `vu_scene` fixture pattern from Task 2.)

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_classifier_matcher.py tests/test_query_bus.py -k "monitor or iem or wedge" -v`
Expected: FAIL — kinds come back `monitor`, and `is_monitor` is False for `monitor.iem`.

- [ ] **Step 3: Implement the split.** In `patterns.yaml` buses section, change only the `kind:` values on the existing iem and wedge/side lines (patterns and confidences stay — they carry hard-won comments; keep those comments):

```yaml
  - { match: '^mon\b|monitor',  kind: monitor,             confidence: 0.9 }
  - { match: '\biem\d*\b|in\s*ear', kind: monitor.iem,     confidence: 0.95 }
  - { match: 'wedge|side\s*fill|sidefill', kind: monitor.wedge, confidence: 0.9 }
  - { match: '^side\b',         kind: monitor.wedge,       confidence: 0.85 }
```

In `bus.py`:

```python
    @property
    def is_monitor(self) -> bool:
        found = self.role
        is_monitor_kind = found.kind == "monitor" or found.kind.startswith("monitor.")
        return is_monitor_kind and is_confident(found)
```

In `resolver.py` (`_monitor_bus_count` docstring must state the 2026-08-16 behaviour change — monitors that are matrices now count):

```python
def _monitor_bus_count(scene) -> int:
    """Confident monitor-role outputs across the whole bus family.

    Counted over bus_family() since 2026-08-16: on the real console the
    IEM mixes are matrices, and a scene whose monitors are all matrices
    used to count as having none.
    """
    return sum(1 for bus in scene.bus_family() if bus.is_monitor)
```

- [ ] **Step 4: Rewrite `monitors.yaml`.** G8: change the `destination_bus.role` line to `destination_bus.role: {starts_with: monitor}` and append to its rationale (keep everything already there):

```yaml
      Two facts recorded 2026-08-16. ToanAZ on TAP sends: "Tap tren wing
      mac dinh la pre-fader hoac pre eq" -- a TAP send draws from a tap
      point that defaults to pre-fader or pre-EQ, so TAP is not evidence
      of a post-fader monitor send and this rule deliberately matches
      POST only. And matrix destinations became visible to this rule the
      same day: on the real console the IEM mixes are matrices.
```

G7 becomes IEM-only at `for_each: output` (carry over the existing rationale text about `dyn.on` defaulting and the parked model clause, then add the split note):

```yaml
  - id: G7
    title: "IEM output has no active dynamics"
    severity: error
    source: >
      docs/knowledge-base/02-event-ops-framework/Core-Skills-Overview.md section 3.4 step 8;
      docs/knowledge-base/04-templates-and-matrices/Technical-Rider-Spec.md section 4.1
    rationale: >
      A feedback burst into in-ear moulds is a hearing injury.
      Core-Skills-Overview section 3.4 step 8 calls a hard limiter on
      every IEM output non-optional, typically -6 to -10 dBFS; the
      rider's section 4.1 limiter row says "A feedback burst into moulds
      is an injury". Split 2026-08-16: error is reserved for outputs
      confidently classified monitor.iem, because both sources scope the
      injury claim to in-ears; wedges and unspecified monitors are G9 at
      warning. This rule still checks only that the dynamics processor
      is switched on. It cannot also check that the loaded model is a
      limiter: the dyn.mdl token a WING stores for one is not recorded
      anywhere in this repository and must not be guessed; the only
      models observed in real data are COMP and CMB. See the 2026-08-16
      advisory-closure spec section 7.1 for the clause to add once that
      token is known. Same build_dyn caveat as before: a bus whose raw
      dyn block is absent entirely reads as on: False and would trip
      this rule without the scene stating it.
    requires_classifier: true
    when:
      for_each: output
      where:
        bus.role: monitor.iem
        bus.dyn.on: false
    message: >
      {bus.kind} {bus.number} ({bus.name}) is an IEM output with its
      dynamics processor bypassed: slot holds {bus.dyn.model}, on =
      {bus.dyn.on}. A feedback burst into moulds is a hearing injury.
```

G9, new rule in the same file:

```yaml
  - id: G9
    title: "Wedge or monitor output has no active dynamics"
    severity: warning
    source: >
      docs/knowledge-base/02-event-ops-framework/Core-Skills-Overview.md section 3.4 step 8;
      docs/knowledge-base/04-templates-and-matrices/Technical-Rider-Spec.md section 4.1
    rationale: >
      The same sources as G7, one severity lower, by ToanAZ's decision of
      2026-08-16: the hearing-injury claim is IEM-scoped in both cited
      passages, and on a wedge or sidefill a limiter chiefly protects
      drivers and the room. Generic monitor-role outputs (a bus named MON
      VOX says monitor but not which flavour) sit here too -- error is
      reserved for a confirmed IEM.
    requires_classifier: true
    when:
      for_each: output
      where:
        bus.role: {in: [monitor, monitor.wedge]}
        bus.dyn.on: false
    message: >
      {bus.kind} {bus.number} ({bus.name}) is a monitor output with its
      dynamics processor bypassed: slot holds {bus.dyn.model}, on =
      {bus.dyn.on}.
```

- [ ] **Step 5: Probe the real file** (same probe script as Task 2 Step 4). Expected shape — verify, then assert: G7 silent (all four IEM matrices have `dyn.on: true`, verified 2026-08-16); `G9` fires on `bus.7` (SIDEFILL, `dyn.on: false`) and possibly on other newly visible monitor-role outputs — check each raw `dyn.on` before accepting. Update `tests/test_advisory_rules.py`: `test_three_base_rules_ship` → `{"G8", "G7", "G9", "E6"}`; `test_g7_fires_only_where_the_dynamics_are_bypassed` becomes two tests:

```python
def test_g7_is_silent_because_every_iem_matrix_has_dynamics_on(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    assert [f for f in scene.advisory.run() if f.rule_id == "G7"] == []

def test_g9_fires_on_the_sidefill_at_warning(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    findings = [f for f in scene.advisory.run() if f.rule_id == "G9"]
    assert [(f.target, f.severity) for f in findings] == [("bus.7", "warning")]
```

(If the probe shows additional genuine G9 targets, extend the expected list with a comment quoting the raw `dyn.on` evidence.) Add a synthetic G7 firing test:

```python
def test_g7_fires_when_an_iem_matrix_bypasses_dynamics(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    scene = _mutated_scene(vu_path, tmp_path,
                           lambda ae: ae["mtx"]["5"]["dyn"].__setitem__("on", False))
    findings = [f for f in scene.advisory.run() if f.rule_id == "G7"]
    assert [(f.target, f.severity) for f in findings] == [("matrix.5", "error")]
```

Update the total in `test_the_sample_scene_finding_counts` from the probe.

- [ ] **Step 6: Grep the tree for stale G7/monitor claims** (the fix-where-reported lesson):

```bash
grep -rn "G7" README.md skills/ examples/ docs/superpowers/specs/ | grep -vi "rule-set-growth"
grep -rn "bus 7\|SIDEFILL" README.md skills/
```

Update every hit that states G7's old scope/severity or calls SIDEFILL a G7 error (handoff docs under `docs/handoff/` are historical records — leave them). Typical hits: the README findings example and `skills/` rule tables.

- [ ] **Step 7: Full suite**

Run: `python -m pytest tests/ -x -q`
Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add wing_parser/ tests/ README.md skills/
git commit -m "Split the monitor role: G7 narrows to IEM at error, G9 covers wedges at warning"
```

---

### Task 4: `event:` tag on rules, filtered by the profile's declared event

**Files:**
- Modify: `wing_parser/advisory/models.py` (Rule), `wing_parser/advisory/loader.py` (`_rule_from`), `wing_parser/advisory/layers.py` (`_as_rules`, `_show_rules`), `wing_parser/advisory/resolver.py` (`active_rules`, new `off_event_ids`, facade), `wing_parser/cli/render.py` (`findings`), `wing_parser/cli/commands.py` (`doctor`)
- Test: `tests/test_advisory_resolver.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `models.EVENTS: tuple[str, ...] = ("universal", "corporate", "band")`; `Rule.event: str = "universal"`; `layers.profile_event(directory, profile) -> str | None` (reads the show file's top-level `event:` key, validates against `EVENTS`, `None` when absent or no profile); `resolver.off_event_ids(scene, directory, profile) -> dict[str, str]` mapping each skipped base rule id to its own event tag; `AdvisoryFacade.off_event(profile)` exposing it; `render.findings(items, suppressed, off_event=None, declared_event=None)` printing one line per skipped rule.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_advisory_resolver.py` (reuse its existing helpers for writing a temp knowledge dir + show file; read the file's existing show-profile tests first and follow their setup style):

```python
def _write_show(directory, name, body):
    shows = directory / "shows"
    shows.mkdir(parents=True, exist_ok=True)
    (shows / f"{name}.yaml").write_text(body, encoding="utf-8")


BAND_RULE = """
rules: []
event: band
"""

def test_a_profile_event_switches_off_other_events_rules(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser import WingScene
    from wing_parser.advisory.resolver import active_rules, off_event_ids
    from wing_parser.advisory.models import Rule
    scene = WingScene.load(vu_path)
    _write_show(tmp_path, "bandshow", BAND_RULE)

    # Base rules are all universal today, so plant a corporate one via a
    # temporary base-rules fixture is NOT possible without touching package
    # data -- instead assert on the mechanism with the loader-level rules:
    ids = {r.id for r in active_rules(scene, tmp_path, "bandshow")}
    assert "G7" in ids  # universal rules survive
    assert off_event_ids(scene, tmp_path, "bandshow") == {}  # nothing corporate ships yet

def test_profile_event_validation_rejects_unknown_values(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser import WingScene
    from wing_parser.advisory.resolver import active_rules
    scene = WingScene.load(vu_path)
    _write_show(tmp_path, "badshow", "rules: []\nevent: wedding\n")
    with pytest.raises(ValueError, match="event"):
        active_rules(scene, tmp_path, "badshow")

def test_rule_event_defaults_to_universal_even_when_blank(tmp_path):
    from wing_parser.advisory.loader import load_rules
    rule_yaml = tmp_path / "r.yaml"
    rule_yaml.write_text(
        "rules:\n"
        "  - id: T1\n"
        "    title: t\n"
        "    severity: info\n"
        "    source: s\n"
        "    rationale: r\n"
        "    message: m\n"
        "    event:\n"          # present but blank -- the .get(None) hazard
        "    when:\n"
        "      for_each: channel\n"
        "      where: {}\n",
        encoding="utf-8",
    )
    assert load_rules(rule_yaml, layer="base")[0].event == "universal"

def test_rule_event_rejects_unknown_values(tmp_path):
    from wing_parser.advisory.loader import load_rules
    rule_yaml = tmp_path / "r.yaml"
    rule_yaml.write_text(
        "rules:\n"
        "  - id: T1\n    title: t\n    severity: info\n    source: s\n"
        "    rationale: r\n    message: m\n    event: gala\n"
        "    when: {for_each: channel, where: {}}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="event"):
        load_rules(rule_yaml, layer="base")
```

Once Task 12 lands band-tagged rules, `test_a_profile_event_switches_off_other_events_rules` gets strengthened there (its Step 5) to assert real ids appear in `off_event_ids` under a corporate profile.

- [ ] **Step 2: Run to verify failure**

Run: `python -m pytest tests/test_advisory_resolver.py -k event -v`
Expected: FAIL — `Rule` has no `event`, `off_event_ids` does not exist.

- [ ] **Step 3: Implement.**

`models.py`: add `EVENTS: tuple[str, ...] = ("universal", "corporate", "band")` next to `SEVERITIES`, and `event: str = "universal"` to `Rule` (after `hardness`).

`loader.py` `_rule_from`, before constructing the Rule:

```python
    event = _optional(entry, "event", "universal")
    if event not in EVENTS:
        raise ValueError(
            f"{where_from}: rule {entry['id']} has event {event!r}; "
            f"expected one of {EVENTS}"
        )
```

and pass `event=event`. Import `EVENTS` alongside `SEVERITIES`. Mirror the same block in `layers._as_rules` (same `_optional` route — a blank `event:` in a hand-edited principles file must not become `None`).

`layers.py`: add

```python
def profile_event(directory: Path | None, profile: str | None) -> str | None:
    """The event a show file declares at its top level, or None.

    Validated here so a typo'd event fails at load, not silently runs
    everything -- the same failure direction _show_rules chose for a
    mistyped profile name.
    """
    if profile is None:
        return None
    shows = config.knowledge_dir(directory) / SHOWS_DIR
    for suffix in (".yaml", ".yml"):
        path = shows / f"{profile}{suffix}"
        if path.is_file():
            declared = _load_yaml(path).get("event")
            if declared is None:
                return None
            if declared not in EVENTS:
                raise ValueError(
                    f"{path}: event {declared!r}; expected one of {EVENTS}"
                )
            return declared
    return None
```

(import `EVENTS` from models; `_show_rules` already raises for a missing profile file, so returning `None` on the not-found path here never masks it — `active_rules` calls `_show_rules` first.)

`resolver.py`: in `active_rules`, after the `suppressed` filter, apply the event filter to base rules only:

```python
    declared = profile_event(directory, profile)
    kept = [r for r in base if r.id not in suppressed]
    if declared is not None:
        kept = [r for r in kept if r.event in ("universal", declared)]
    return kept + higher
```

and add:

```python
def off_event_ids(scene, directory: Path | None = None,
                  profile: str | None = None) -> dict[str, str]:
    """Base rules skipped because the profile declares a different event."""
    declared = profile_event(directory, profile)
    if declared is None:
        return {}
    return {r.id: r.event for r in load_base_rules()
            if r.event not in ("universal", declared)}
```

Facade: `def off_event(self, profile=None): return off_event_ids(self._scene, self._directory, profile)`.

`render.py` `findings()`: add parameters `off_event: dict[str, str] | None = None, declared_event: str | None = None`; after the suppressed loop:

```python
    for rule_id, rule_event in (off_event or {}).items():
        lines.append(
            f"  [off-event] {rule_id} is {rule_event}-only; "
            f"profile declares event {declared_event}"
        )
```

`commands.py` `doctor()`: fetch `profile = getattr(args, "profile", None)` once, then

```python
        print(render.findings(
            found,
            scene.advisory.suppressed(profile),
            off_event=scene.advisory.off_event(profile),
            declared_event=layers.profile_event(None, profile),
        ))
```

— wait: `commands.py` must not re-derive the directory. Give the facade the job instead: add `AdvisoryFacade.declared_event(profile)` returning `profile_event(self._directory, profile)`, and call `scene.advisory.declared_event(profile)` here. Do it that way.

- [ ] **Step 4: Run the new tests, then full suite**

Run: `python -m pytest tests/test_advisory_resolver.py tests/test_cli.py -q && python -m pytest tests/ -x -q`
Expected: PASS. `findings()`'s new parameters default to None, so existing render tests stay green.

- [ ] **Step 5: Commit**

```bash
git add wing_parser/ tests/
git commit -m "Add event tags to rules, filtered by the profile's declared event"
```

---

### Task 5: Bus derived properties — `notch_count`, `max_boost_above_8k`, `receives_ambient`, `receives_any`

**Files:**
- Modify: `wing_parser/query/bus.py`
- Test: `tests/test_query_bus.py`

**Interfaces:**
- Consumes: `Bus.data.eq.bands` (`tuple[EqBand, ...] | None`, fields `freq/gain/q/shape`), `self._scene.channels()`, `Channel.source_type`, `matcher.HIGH`.
- Produces (exact semantics later tasks' YAML relies on):
  - `Bus.notch_count -> int` — bands with `gain <= -6.0` and `q >= 8.0`, skipping `shape == "SHV"` (shelves are not notches). Empty/None bands → 0.
  - `Bus.max_boost_above_8k -> float | None` — max `gain` over bands with `freq > 8000.0` and `gain > 0.0`; `None` when no such band.
  - `Bus.receives_ambient -> bool` — any channel whose `source_type.kind == "utility.ambient"` with `confidence >= HIGH` has a send with `on == true` targeting this bus (`dest_kind` matching this bus's family, `dest == self.number`); for `kind == "main"`, main-sends with `on == true` count instead. Aux → False.
  - `Bus.receives_any -> bool` — any channel send (`dest_kind` family match + `on`) or, for mains, any main-send `on`, targets this bus. Aux → False, documented.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_query_bus.py`. Use `_mutated_scene` for the positive ambient case (no ambient channels exist in the real file):

```python
from tests.conftest import _mutated_scene


class TestNotchCount:
    def test_counts_only_narrow_deep_cuts(self, vu_path, tmp_path, monkeypatch):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            eq = ae["bus"]["7"]["eq"]
            eq["on"] = True
            for i, (g, q) in enumerate(
                [(-8, 9), (-7, 10), (-6.5, 8.5), (-9, 12), (-6.1, 8.0), (-12, 20),  # six notches
                 (-8, 4),    # deep but wide -> not a notch
                 (-3, 12),   # narrow but shallow -> not a notch
                ], start=1):
                eq[f"{i}g"], eq[f"{i}q"], eq[f"{i}f"] = g, q, 500.0 + i
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert scene.bus(7).notch_count == 6

    def test_no_bands_is_zero(self, vu_path, monkeypatch):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        from wing_parser import WingScene
        scene = WingScene.load(vu_path)
        # mutation check lives here: if the property returned a constant
        # instead of counting, this zero and the six above cannot both pass
        assert all(isinstance(b.notch_count, int) for b in scene.bus_family())


class TestMaxBoostAbove8k:
    def test_reports_the_largest_high_boost(self, vu_path, tmp_path, monkeypatch):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            eq = ae["main"]["1"]["eq"]
            eq["on"] = True
            eq["1g"], eq["1f"], eq["1q"] = 2.5, 10000.0, 1.0
            eq["2g"], eq["2f"], eq["2q"] = 4.0, 12000.0, 1.0
            eq["3g"], eq["3f"], eq["3q"] = 5.0, 4000.0, 1.0   # below 8k, ignored
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert scene.main(1).max_boost_above_8k == pytest.approx(4.0)

    def test_none_when_nothing_boosts_the_top(self, vu_path, tmp_path, monkeypatch):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            eq = ae["main"]["1"]["eq"]
            eq["on"] = True
            eq["1g"], eq["1f"] = -3.0, 12000.0
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert scene.main(1).max_boost_above_8k is None


class TestReceives:
    def test_receives_ambient_true_when_a_confident_ambient_channel_feeds_it(
        self, vu_path, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            ae["ch"]["20"]["name"] = "AMBIENT L"      # utility.ambient, 0.85
            ae["ch"]["20"]["send"]["MX5"]["on"] = True
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert scene.matrix(5).receives_ambient
        assert not scene.matrix(6).receives_ambient

    def test_receives_any_via_main_sends(self, vu_path, monkeypatch):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        from wing_parser import WingScene
        scene = WingScene.load(vu_path)
        assert scene.main(1).receives_any   # 28 main-sends are on in this file
```

- [ ] **Step 2: Run to verify failure** — `python -m pytest tests/test_query_bus.py -k "Notch or Boost or Receives" -v` → FAIL (`AttributeError`).

- [ ] **Step 3: Implement in `bus.py`** (add `from wing_parser.classifier.matcher import HIGH` to the existing matcher import):

```python
    @property
    def notch_count(self) -> int:
        """Bands narrow and deep enough that all three knowledge-base
        sources would call them feedback notches: q >= 8, cut >= 6 dB.
        Shelves (shape SHV) are tonal moves, not notches, and are skipped."""
        bands = self.data.eq.bands or ()
        return sum(
            1 for band in bands
            if band.shape != "SHV" and band.gain <= -6.0 and band.q >= 8.0
        )

    @property
    def max_boost_above_8k(self) -> float | None:
        bands = self.data.eq.bands or ()
        boosts = [b.gain for b in bands if b.freq > 8000.0 and b.gain > 0.0]
        return max(boosts) if boosts else None

    def _fed_by(self, channel) -> bool:
        if self.data.kind == "main":
            return any(m.on and m.dest == self.data.number for m in channel.main_sends)
        if self.data.kind in ("bus", "matrix"):
            return any(
                s.on and s.dest == self.data.number and s.dest_kind == self.data.kind
                for s in channel.sends
            )
        return False   # aux inputs are not channel-send destinations

    @property
    def receives_any(self) -> bool:
        return any(self._fed_by(ch) for ch in self._scene.channels())

    @property
    def receives_ambient(self) -> bool:
        return any(
            self._fed_by(ch)
            for ch in self._scene.channels()
            if ch.source_type.kind == "utility.ambient"
            and ch.source_type.confidence >= HIGH
        )
```

If `bus.py` crosses ~200 lines, move the four properties plus `_fed_by` to a new `wing_parser/query/bus_derived.py` mixin class `BusDerived` and make `Bus(BusDerived)` — same public names either way.

- [ ] **Step 4: Run new tests + full suite** — `python -m pytest tests/test_query_bus.py -v && python -m pytest tests/ -x -q` → PASS.

- [ ] **Step 5: Commit**

```bash
git add wing_parser/query/ tests/test_query_bus.py
git commit -m "Add cross-object derived properties to the Bus view"
```

---

### Task 6: Channel derived properties — `iem_send_count`, `eq_has_lowmid_cut`, `eq_has_presence_lift`, `in_use`

**Files:**
- Modify: `wing_parser/query/channel.py`
- Test: `tests/test_query_build_channel.py` or `tests/test_query_scene.py` — put them in a new `tests/test_query_channel_derived.py` to keep files focused

**Interfaces:**
- Consumes: `Channel.data.sends`, `Channel.data.main_sends`, `Channel.data.eq.bands`, `self._scene` bus lookups, `matcher.HIGH`.
- Produces:
  - `Channel.iem_send_count -> int` — sends with `on == true` whose destination (bus or matrix by `dest_kind`) has a confident role starting with `"monitor.iem"` (equal counts too).
  - `Channel.eq_has_lowmid_cut -> bool` — any band `200.0 <= freq <= 500.0` with `gain < 0.0`.
  - `Channel.eq_has_presence_lift -> bool` — any band `2000.0 <= freq <= 4000.0` with `gain > 0.0`.
  - `Channel.in_use -> bool` — `not source_ref.is_off` AND `not muted` AND `fader_dB > -90.0` AND (any send `on` or any main-send `on`). The `-90` floor is what keeps a factory scene (all faders −144) out of N1 — the discriminator the spec's §4 acceptance constraint demands; its docstring must say so and cite the probe.

- [ ] **Step 1: Write the failing tests** — create `tests/test_query_channel_derived.py`:

```python
import json

import pytest

from wing_parser import WingScene
from tests.conftest import _mutated_scene


@pytest.fixture()
def vu_scene(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    return WingScene.load(vu_path)


class TestIemSendCount:
    def test_counts_only_on_sends_to_iem_roles(self, vu_path, tmp_path, monkeypatch):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            ae["ch"]["20"]["name"] = "CLICK"
            for mx in ("MX5", "MX6", "MX7"):        # IEM MC, IEM CA SI 1/2
                ae["ch"]["20"]["send"][mx]["on"] = True
            ae["ch"]["20"]["send"]["MX1"]["on"] = True   # FLOWN -> pa_zone, not IEM
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert scene.channel(20).iem_send_count == 3


class TestEqShapes:
    def test_lowmid_cut_seen(self, vu_path, tmp_path, monkeypatch):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            eq = ae["ch"]["20"]["peq"]
            eq["on"] = True
            eq["1g"], eq["1f"], eq["1q"] = -3.0, 300.0, 1.4
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert scene.channel(20).eq_has_lowmid_cut

    def test_boost_in_the_lowmid_is_not_a_cut(self, vu_path, tmp_path, monkeypatch):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            eq = ae["ch"]["20"]["peq"]
            eq["on"] = True
            for i in range(1, 5):
                eq[f"{i}g"], eq[f"{i}f"] = 2.0, 300.0
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert not scene.channel(20).eq_has_lowmid_cut

    def test_presence_lift_seen(self, vu_path, tmp_path, monkeypatch):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            eq = ae["ch"]["20"]["peq"]
            eq["on"] = True
            eq["2g"], eq["2f"], eq["2q"] = 2.5, 3000.0, 1.0
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert scene.channel(20).eq_has_presence_lift


class TestInUse:
    def test_factory_scene_has_no_channel_in_use(self, factory_path, monkeypatch):
        # The spec's acceptance constraint: factory defaults are the
        # reference nothing-configured state. Faders there sit at -144.
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        scene = WingScene.load(factory_path)
        assert [c.number for c in scene.channels() if c.in_use] == []

    def test_a_patched_unmuted_routed_channel_with_fader_up_is_in_use(
        self, vu_path, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            ch = ae["ch"]["20"]
            ch["fdr"] = 0
            ch["mute"] = False
            ch["main"]["1"]["on"] = True
            ch["in"]["conn"]["grp"] = "A"
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert scene.channel(20).in_use
```

- [ ] **Step 2: Verify the factory-fader premise before implementing** (never assert an unverified claim):

```bash
python - <<'EOF'
import json
doc = json.load(open("user-files/factory-scene.snap", encoding="utf-8"))
faders = {c["fdr"] for c in doc["ae_data"]["ch"].values()}
print("factory channel faders:", faders)
EOF
```

If any factory fader is above −90, the `-90.0` discriminator fails the spec's acceptance constraint — stop, record the probed values in the task notes, and pick the discriminator the data supports (e.g. also require `name != ""` is NOT allowed — N1 needs unnamed; fall back to shipping N1/N2 disabled per spec §4). Then run the tests: `python -m pytest tests/test_query_channel_derived.py -v` → FAIL (`AttributeError`).

- [ ] **Step 3: Implement in `channel.py`** (imports: `HIGH` from matcher):

```python
    @property
    def iem_send_count(self) -> int:
        families = {"bus": self._scene.family("bus"), "matrix": self._scene.family("matrix")}
        count = 0
        for send in self.data.sends:
            if not send.on:
                continue
            destination = families.get(send.dest_kind, {}).get(send.dest)
            if destination is None:
                continue
            role = destination.role
            if role.confidence >= HIGH and (
                role.kind == "monitor.iem" or role.kind.startswith("monitor.iem.")
            ):
                count += 1
        return count

    @property
    def eq_has_lowmid_cut(self) -> bool:
        bands = self.data.eq.bands or ()
        return any(200.0 <= b.freq <= 500.0 and b.gain < 0.0 for b in bands)

    @property
    def eq_has_presence_lift(self) -> bool:
        bands = self.data.eq.bands or ()
        return any(2000.0 <= b.freq <= 4000.0 and b.gain > 0.0 for b in bands)

    @property
    def in_use(self) -> bool:
        """Patched, unmuted, routed, and with the fader actually up.

        The -90 dB floor is the discriminator that keeps a factory-default
        scene (every fader at -144) from reading as in use -- the
        acceptance constraint in the 2026-08-16 rule-set-growth spec §4.
        """
        if self.data.source_ref.is_off or self.data.muted:
            return False
        if self.data.fader_dB <= -90.0:
            return False
        return any(s.on for s in self.data.sends) or any(
            m.on for m in self.data.main_sends
        )
```

If `channel.py` crosses ~200 lines, split the same way as Task 5 (a `ChannelDerived` mixin in `wing_parser/query/channel_derived.py`).

- [ ] **Step 4: Run new tests + full suite** — PASS.

- [ ] **Step 5: Commit**

```bash
git add wing_parser/query/ tests/test_query_channel_derived.py
git commit -m "Add cross-object derived properties to the Channel view"
```

---

### Task 7: New classifier patterns

**Files:**
- Modify: `wing_parser/classifier/data/patterns.yaml`
- Test: `tests/test_classifier_matcher.py`

**Interfaces:**
- Produces channel kinds `utility.timecode`, `utility.remote_caller`, `speech.panel`, `speech.qa`; bus kind `mix_minus`. Confidences below.

- [ ] **Step 1: Write the failing tests** — each new pattern gets a plausible name AND a numbered variant (the `\biem\b`-never-matched-`IEM3` lesson):

```python
def test_timecode_channels_classify():
    for name in ("LTC", "TIME CODE", "TC IN", "LTC 2"):
        assert classify(name, "channels").kind == "utility.timecode", name

def test_remote_caller_channels_classify():
    for name in ("ZOOM", "Teams 1", "REMOTE CALLER", "CALLER 2"):
        assert classify(name, "channels").kind == "utility.remote_caller", name

def test_panel_channels_classify():
    for name in ("PANEL 1", "Panel3", "SEAT 2"):
        assert classify(name, "channels").kind == "speech.panel", name

def test_qa_channels_classify():
    for name in ("Q&A 1", "QA 2", "ROVER", "ROVING 1", "AUDIENCE MIC"):
        assert classify(name, "channels").kind == "speech.qa", name

def test_mix_minus_buses_classify():
    for name in ("MIX MINUS", "MM 1", "N-1 ZOOM"):
        assert classify(name, "buses").kind == "mix_minus", name

def test_new_patterns_do_not_steal_existing_names():
    # 'TC IN' must not break talkback; 'SEAT' must not break strings, etc.
    assert classify("TB", "buses").kind == "talkback"
    assert classify("MON VOX", "buses").kind == "monitor"
    assert classify("HS4", "channels").kind == "speech.headset"
```

- [ ] **Step 2: Run to verify failure** — the five new tests FAIL (kind comes back `unknown` or a wrong family).

- [ ] **Step 3: Add the patterns.** Channels section:

```yaml
  # Utility signals that must never reach programme outputs
  - { match: '\bltc\b|time\s*code|\btc\s*in\b|\btc\d*\b', kind: utility.timecode, confidence: 0.9 }
  - { match: '\bzoom\b|\bteams\b|\bcaller\b|\bremote\b|\bskype\b', kind: utility.remote_caller, confidence: 0.85 }
  # Corporate speech roles
  - { match: '\bpanel\s*\d*\b|\bseat\s*\d+\b', kind: speech.panel, confidence: 0.85 }
  - { match: 'q\s*&\s*a|\bqa\s*\d*\b|\brov(er|ing)\b|audience\s*mic', kind: speech.qa, confidence: 0.8 }
```

Buses section:

```yaml
  # A bus built to exclude exactly one remote caller (rider: "n-1")
  - { match: 'mix\s*minus|\bmm\s*\d*\b|\bn-1\b', kind: mix_minus, confidence: 0.85 }
```

If a chosen regex fails a test (e.g. normalisation lowercases and collapses whitespace — `classify` runs `clean()` first), adjust the regex, not the test names, and re-run until the listed names classify. Check `Panel3`: `\bpanel\s*\d*\b` matches `panel3`? There is no word boundary between `l` and `3` — that is the point of `\d*` inside the token: `panel\s*\d*\b` ends at `3`. Verify with the test, not by eye.

- [ ] **Step 4: Full suite** — PASS (existing pattern tests prove nothing regressed).

- [ ] **Step 5: Commit**

```bash
git add wing_parser/classifier/data/patterns.yaml tests/test_classifier_matcher.py
git commit -m "Add timecode, remote-caller, panel, Q&A and mix-minus patterns"
```

---

### Task 8: Routing rules R1, R2, R3, R3M

**Files:**
- Create: `wing_parser/advisory/base_rules/routing.yaml`
- Test: `tests/test_advisory_rules_routing.py` (new file — `test_advisory_rules.py` is near its size ceiling)

**Interfaces:**
- Consumes: iterators from Task 2, patterns from Task 7.
- Produces rule ids `R1`, `R2`, `R3`, `R3M`.

- [ ] **Step 1: Write the failing tests** — create `tests/test_advisory_rules_routing.py`:

```python
import pytest

from wing_parser import WingScene
from tests.conftest import _mutated_scene


@pytest.fixture(scope="module")
def vu_scene(vu_path):
    return WingScene.load(vu_path)


def _findings(scene, rule_id):
    return [f for f in scene.advisory.run() if f.rule_id == rule_id]


def test_r1_fires_when_a_click_reaches_the_foh_main(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "CLICK"
        ae["ch"]["20"]["main"]["1"]["on"] = True   # main 1 = MAIN FOH
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    findings = _findings(scene, "R1")
    assert [(f.target, f.severity) for f in findings] == [("ch.20.main.1", "error")]


def test_r1_stays_silent_when_the_click_feeds_only_monitors(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "CLICK"
        ae["ch"]["20"]["send"]["MX5"]["on"] = True   # IEM matrix is fine
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert _findings(scene, "R1") == []


def test_r2_fires_when_talkback_reaches_the_foh_main(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "TB"
        ae["ch"]["20"]["main"]["1"]["on"] = True
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _findings(scene, "R2")] == ["ch.20.main.1"]


def test_r2_allows_talkback_into_the_tb_out_main(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "TB"
        ae["ch"]["20"]["main"]["4"]["on"] = True   # main 4 'TB OUT' -> role talkback
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert _findings(scene, "R2") == []


def test_r3_and_r3m_fire_on_any_routed_timecode(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "LTC"
        ae["ch"]["20"]["send"]["9"]["on"] = True       # bus 9, mode whatever it was
        ae["ch"]["20"]["main"]["2"]["on"] = True
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _findings(scene, "R3")] == ["ch.20.send.9"]
    assert [f.target for f in _findings(scene, "R3M")] == ["ch.20.main.2"]


def test_routing_rules_are_silent_on_the_untouched_real_file(vu_scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    found = {f.rule_id for f in vu_scene.advisory.run()}
    assert found.isdisjoint({"R1", "R2", "R3", "R3M"})
```

Caution on the R3 fixture: channel 20's send "9" may already be `on` in the raw file with other sends also on — the mutation sets exactly one bus send; first zero every send: add `for k, s in ae["ch"]["20"]["send"].items(): s["on"] = False` at the top of that `mutate` (and in R1's monitor-only test, same reset before enabling MX5). Do the same reset for `main` (`for m in ae["ch"]["20"]["main"].values(): m["on"] = False`) in every routing fixture before switching on the one send under test.

- [ ] **Step 2: Run to verify failure** — `python -m pytest tests/test_advisory_rules_routing.py -v` → FAIL (no rules R1…).

- [ ] **Step 3: Create `wing_parser/advisory/base_rules/routing.yaml`:**

```yaml
# Signal-routing rules: things that must never reach an output family.
# All universal. loader.load_base_rules globs this directory, so the file
# is picked up with no registration step.
rules:
  - id: R1
    title: "Click track reaches a FOH main"
    severity: error
    source: "docs/knowledge-base/04-templates-and-matrices/Technical-Rider-Spec.md L175: click is 'To monitors only, hard-muted at FOH'"
    rationale: >
      A click in the PA is audible to the audience. The rider states the
      routing baldly and bolds it: to monitors only, hard-muted at FOH
      (input list row 26, repeated verbatim at L1092). Only a main whose
      role is confidently `main` counts as FOH here: main 4 on the real
      console is named TB OUT and classifies as talkback, and a click
      send to a monitor matrix is exactly where a click belongs.
    requires_classifier: true
    when:
      for_each: channel.main_sends
      where:
        channel.source_type: utility.click
        main_send.on: true
        destination_main.role: main
    message: >
      Channel {channel.number} ({channel.name}) looks like a click track
      and its send to main {destination_main.number}
      ({destination_main.name}) is on.

  - id: R2
    title: "Talkback reaches a FOH main"
    severity: error
    source: "docs/knowledge-base/04-templates-and-matrices/Technical-Rider-Spec.md L180: talkback 'Stage left, not in FOH mains'"
    rationale: >
      Talkback is engineer-to-stage, never programme (the same fact the
      talkback bus pattern records in patterns.yaml). The rider's input
      row 31 bolds "not in FOH mains". The destination-role test is what
      lets the real console's dedicated TB OUT main pass: it classifies
      as talkback, not main, so feeding it is the intended routing.
    requires_classifier: true
    when:
      for_each: channel.main_sends
      where:
        channel.source_type: utility.talkback
        main_send.on: true
        destination_main.role: main
    message: >
      Channel {channel.number} ({channel.name}) looks like a talkback mic
      and its send to main {destination_main.number}
      ({destination_main.name}) is on.

  - id: R3
    title: "Timecode routed into a mix destination"
    severity: error
    source: "docs/knowledge-base/03-event-type-sops/Live-Entertainment-Shows.md L46: LTC 'sounds like audio noise -- never patch it through a normal audio channel'"
    rationale: >
      LTC rides XLR and sounds like noise; any bus or matrix send that is
      on is a route toward ears. requires_classifier is deliberately
      false: the confidence bound to a send target is the destination's
      role, and an unnamed destination must not exempt a timecode channel
      -- the channel-side kind equality in `where` is the classification
      doing the work. R3M is the same rule over main sends; rule ids must
      be unique, so the pair shares this rationale.
    requires_classifier: false
    when:
      for_each: channel.sends
      where:
        channel.source_type: utility.timecode
        send.on: true
    message: >
      Channel {channel.number} ({channel.name}) looks like timecode and
      its send to {destination_bus.kind} {destination_bus.number}
      ({destination_bus.name}) is on. LTC sounds like audio noise on a
      loudspeaker.

  - id: R3M
    title: "Timecode routed into a main"
    severity: error
    source: "docs/knowledge-base/03-event-type-sops/Live-Entertainment-Shows.md L46: LTC 'sounds like audio noise -- never patch it through a normal audio channel'"
    rationale: >
      The main-send half of R3; see R3. Split because one rule has one
      for_each.
    requires_classifier: false
    when:
      for_each: channel.main_sends
      where:
        channel.source_type: utility.timecode
        main_send.on: true
    message: >
      Channel {channel.number} ({channel.name}) looks like timecode and
      its send to main {destination_main.number}
      ({destination_main.name}) is on.
```

- [ ] **Step 4: Run new tests, probe both real files** (probe script from Task 2 Step 4 plus the same for `factory-scene.snap`), update `test_the_sample_scene_finding_counts` if anything shifted (it must not — the silence test in Step 1 asserts it), full suite.

- [ ] **Step 5: Commit**

```bash
git add wing_parser/advisory/base_rules/routing.yaml tests/test_advisory_rules_routing.py
git commit -m "Add click, talkback and timecode routing rules"
```

---

### Task 9: Routing rules R4, R5, R6 and naming rules N1, N2

**Files:**
- Modify: `wing_parser/advisory/base_rules/routing.yaml`
- Test: `tests/test_advisory_rules_routing.py`

**Interfaces:**
- Consumes: `record` and `mix_minus` bus roles, `stream` role, `Channel.in_use`, `Bus.receives_any`.
- Produces rule ids `R4`, `R5`, `R6`, `N1`, `N2`.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_advisory_rules_routing.py`:

```python
def test_r4_fires_on_a_post_fader_send_to_a_record_bus(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["bus"]["12"]["name"] = "RECORD"
        ae["ch"]["1"]["send"]["12"]["on"] = True
        ae["ch"]["1"]["send"]["12"]["mode"] = "POST"
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    findings = [f for f in scene.advisory.run() if f.rule_id == "R4"]
    assert [(f.target, f.severity) for f in findings] == [("ch.1.send.12", "warning")]


def test_r4_is_silent_when_the_record_send_is_pre(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["bus"]["12"]["name"] = "RECORD"
        ae["ch"]["1"]["send"]["12"]["on"] = True
        ae["ch"]["1"]["send"]["12"]["mode"] = "PRE"
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f for f in scene.advisory.run() if f.rule_id == "R4"] == []


def test_r5_fires_on_a_post_fader_main_send_to_a_record_main(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["main"]["3"]["name"] = "RECORD"       # was RECODING (typo, unclassified)
        # ch 1 already has main 3 on with pre False in the real file
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    findings = [f for f in scene.advisory.run() if f.rule_id == "R5"]
    assert ("ch.1.main.3", "warning") in [(f.target, f.severity) for f in findings]


def test_r6_fires_when_the_caller_feeds_its_own_mix_minus(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "ZOOM"
        ae["bus"]["12"]["name"] = "MIX MINUS"
        ae["ch"]["20"]["send"]["12"]["on"] = True
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    findings = [f for f in scene.advisory.run() if f.rule_id == "R6"]
    assert [(f.target, f.severity) for f in findings] == [("ch.20.send.12", "error")]


def test_n1_fires_on_an_unnamed_channel_that_is_actually_in_use(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ch = ae["ch"]["20"]
        ch["name"] = ""
        ch["fdr"] = 0
        ch["mute"] = False
        ch["main"]["1"]["on"] = True
        ch["in"]["conn"]["grp"] = "A"
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in scene.advisory.run() if f.rule_id == "N1"] == ["ch.20"]


def test_n1_and_n2_are_silent_on_the_factory_scene(factory_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    scene = WingScene.load(factory_path)
    assert scene.advisory.run() == []   # the whole base set, not just N1/N2


def test_n2_fires_on_an_unnamed_output_receiving_signal(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["bus"]["12"]["name"] = ""
        ae["bus"]["12"]["fdr"] = 0
        ae["ch"]["1"]["send"]["12"]["on"] = True
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in scene.advisory.run() if f.rule_id == "N2"] == ["bus.12"]
```

- [ ] **Step 2: Probe N2's factory premise before implementing.** N2 = unnamed output + `receives_any` + output fader above the floor. Factory mains receive 40 main-sends `on` — so N2 MUST carry a fader condition. Probe factory output faders:

```bash
python - <<'EOF'
import json
doc = json.load(open("user-files/factory-scene.snap", encoding="utf-8"))
ae = doc["ae_data"]
for fam in ("bus", "main", "mtx", "aux"):
    print(fam, sorted({v.get("fdr") for v in ae.get(fam, {}).values()}))
EOF
```

If factory output faders are NOT all ≤ −90, N2 cannot meet the factory-silence constraint with this shape: ship N2 with `enabled: false` and a rationale line quoting the probed values (spec §4 fallback), and change the N2 test to assert it loads disabled. Run the tests → FAIL.

- [ ] **Step 3: Append to `routing.yaml`:**

```yaml
  - id: R4
    title: "Send to a record destination is post-fader"
    severity: warning
    source: "docs/knowledge-base/04-templates-and-matrices/Technical-Rider-Spec.md L260: 'Record feed is pre-fader [R] -- post-gain, pre-fader, pre-EQ. A FOH fader move must not damage the archive.'"
    rationale: >
      A post-fader record feed bakes every FOH move into the archive.
      Marked [R] (contractual) in the rider and restated at L1475. Only
      the fader half is checkable: tap_point cannot carry the pre-EQ
      half, because POST_FDR is the stored value on all 80 channels of
      both sample files including factory defaults (probed 2026-08-16),
      so a tap_point clause would fire on everything or nothing. Known
      silence on the real file: its record main is named RECODING, a typo
      that stays unclassified by design, and reporting the unclassified
      name is the tool's existing, correct behaviour.
    requires_classifier: true
    when:
      for_each: channel.sends
      where:
        destination_bus.role: record
        send.on: true
        send.mode: POST
    message: >
      Channel {channel.number} ({channel.name}) feeds record destination
      {destination_bus.number} ({destination_bus.name}) post-fader: a FOH
      fader move changes the archive.

  - id: R5
    title: "Main-send to a record main is post-fader"
    severity: warning
    source: "docs/knowledge-base/04-templates-and-matrices/Technical-Rider-Spec.md L260: 'Record feed is pre-fader [R]'"
    rationale: >
      The main-send half of R4; see R4. MainSend carries its own pre
      flag, so this checks main_send.pre directly.
    requires_classifier: true
    when:
      for_each: channel.main_sends
      where:
        destination_main.role: record
        main_send.on: true
        main_send.pre: false
    message: >
      Channel {channel.number} ({channel.name}) feeds record main
      {destination_main.number} ({destination_main.name}) post-fader.

  - id: R6
    title: "Remote caller feeds its own mix-minus bus"
    severity: error
    source: "docs/knowledge-base/04-templates-and-matrices/Technical-Rider-Spec.md L208: 'Ch15 must be fed a bus that excludes itself... This is the single most common corporate audio failure.'; L879: 'No bus = no show, this is non-negotiable.'"
    rationale: >
      A mix-minus bus exists to exclude exactly one channel: the caller
      it returns to. The caller appearing in its own return means the
      remote end hears itself delayed by the platform round trip and
      stops talking. The general obligation (every caller must HAVE a
      mix-minus) is not decidable from names alone and is out of scope
      per the spec's blocked list; this narrow, unambiguous form is.
    requires_classifier: true
    when:
      for_each: channel.sends
      where:
        channel.source_type: utility.remote_caller
        destination_bus.role: mix_minus
        send.on: true
    message: >
      Channel {channel.number} ({channel.name}) looks like a remote
      caller and its send into mix-minus bus {destination_bus.number}
      ({destination_bus.name}) is on -- the caller will hear itself
      delayed.

  - id: N1
    title: "Channel is in use but unnamed"
    severity: info
    source: "docs/knowledge-base/04-templates-and-matrices/Risk-Contingency-Matrix.md L135: 'undocumented setups are the real failure here'; L362 sign-off row 52"
    rationale: >
      A deputy cannot drive an unlabelled console. In use means patched,
      unmuted, routed somewhere, and fader above -90 dB -- the last
      condition is the discriminator that keeps a factory-default scene
      (every fader at -144) silent, which is this rule's acceptance
      constraint from the 2026-08-16 spec.
    requires_classifier: false
    when:
      for_each: channel
      where:
        channel.in_use: true
        channel.name: ""
    message: >
      Channel {channel.number} is patched, unmuted and routed, but has no
      name.

  - id: N2
    title: "Output receives signal but is unnamed"
    severity: info
    source: "docs/knowledge-base/04-templates-and-matrices/Risk-Contingency-Matrix.md L135; L362"
    rationale: >
      The output-side half of N1. Guarded by the output's own fader for
      the same factory-silence reason -- factory mains receive 40 live
      main-sends out of the box.
    requires_classifier: false
    when:
      for_each: output
      where:
        bus.receives_any: true
        bus.name: ""
        bus.fader_dB: {gt: -90.0}
    message: >
      {bus.kind} {bus.number} receives signal but has no name.
```

(If Step 2's probe forced the disabled fallback for N2 — or for N1 via Task 6 — set `enabled: false` on that rule and put the probed fader values in its rationale.)

- [ ] **Step 4: Run new tests; probe both real files; update the counts test with evidence comments; full suite** — PASS. The factory-silence test is now a permanent suite fixture guarding every future rule.

- [ ] **Step 5: Commit**

```bash
git add wing_parser/advisory/base_rules/routing.yaml tests/test_advisory_rules_routing.py tests/test_advisory_rules.py
git commit -m "Add record-feed, mix-minus and naming rules"
```

---

### Task 10: Speech rules S1, S2 and monitor-quality rules G10, G11, G12

**Files:**
- Create: `wing_parser/advisory/base_rules/speech.yaml`, `wing_parser/advisory/base_rules/monitors_quality.yaml`
- Test: `tests/test_advisory_rules_speech.py` (new)

**Interfaces:**
- Consumes: `starts_with`, `output` iterator, `notch_count`, `max_boost_above_8k`, `receives_ambient`.
- Produces rule ids `S1`, `S2`, `G10`, `G11`, `G12`.

- [ ] **Step 1: Write the failing tests** — create `tests/test_advisory_rules_speech.py` with the same imports/fixtures as Task 8's file:

```python
def test_s1_fires_on_a_speech_channel_without_hpf(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "LECTERN"
        ae["ch"]["20"]["flt"]["lc"] = False
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    findings = [f for f in scene.advisory.run() if f.rule_id == "S1"]
    assert [(f.target, f.severity) for f in findings] == [("ch.20", "warning")]


def test_s1_respects_the_engaged_hpf(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "LECTERN"
        ae["ch"]["20"]["flt"]["lc"] = True
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    targets = [f.target for f in scene.advisory.run() if f.rule_id == "S1"]
    assert "ch.20" not in targets


def test_s1_on_the_real_file_matches_the_probe(vu_scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    findings = sorted(f.target for f in vu_scene.advisory.run() if f.rule_id == "S1")
    # Probed 2026-08-16: the five speech-classified channels (ch.1/2/3 VOX,
    # ch.8 MC, ch.11 HS4) all have filter.low_cut_on True, so S1 is silent
    # on the untouched real file. Re-verify with the Task 2 probe script if
    # this ever goes red.
    assert findings == []


def test_s2_fires_when_playback_sits_in_an_active_automix_group(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "PLAYBACK"
        ae["ch"]["20"]["postins"]["on"] = True     # AUTO_X mode already present
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    findings = [f for f in scene.advisory.run() if f.rule_id == "S2"]
    assert [(f.target, f.severity) for f in findings] == [("ch.20", "error")]


def test_s2_ignores_a_configured_but_inactive_automix(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "PLAYBACK"
        ae["ch"]["20"]["postins"]["on"] = False
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f for f in scene.advisory.run() if f.rule_id == "S2"] == []


def test_g10_fires_on_every_iem_output_when_no_ambient_channel_exists(vu_scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    findings = sorted(f.target for f in vu_scene.advisory.run() if f.rule_id == "G10")
    assert findings == ["matrix.5", "matrix.6", "matrix.7", "matrix.8"]
    severities = {f.severity for f in vu_scene.advisory.run() if f.rule_id == "G10"}
    assert severities == {"info"}


def test_g11_fires_beyond_five_notches_on_a_monitor(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        eq = ae["bus"]["7"]["eq"]                   # SIDEFILL -> monitor.wedge
        eq["on"] = True
        for i in range(1, 7):                        # 6 notches
            eq[f"{i}g"], eq[f"{i}q"], eq[f"{i}f"] = -8.0, 10.0, 400.0 + 100 * i
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    findings = [f for f in scene.advisory.run() if f.rule_id == "G11"]
    assert [(f.target, f.severity) for f in findings] == [("bus.7", "warning")]


def test_g12_fires_on_a_high_boost_on_the_foh_main(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        eq = ae["main"]["1"]["eq"]
        eq["on"] = True
        eq["1g"], eq["1f"], eq["1q"] = 3.0, 10000.0, 1.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    findings = [f for f in scene.advisory.run() if f.rule_id == "G12"]
    assert [(f.target, f.severity) for f in findings] == [("main.1", "info")]
```

Note the six-band cap: the raw `peq` block carries bands `1g`…; channel EQ showed 4 bands, bus EQ band count may differ — before writing the G11 fixture, print `sorted(doc["ae_data"]["bus"]["7"]["eq"].keys())` and use only the band indices that exist; if fewer than 6 PEQ bands exist on a bus, mutate TWO buses' worth? No — G11 needs >5 on ONE output: if the bus EQ has 6+ bands use them; if it has only 4, lower nothing — instead check whether `mtx`/`main` EQ has more bands, and if no output has ≥6 bands, G11's `gt: 5` can never fire on real hardware: STOP and flag to the orchestrator — the rule threshold must then be renegotiated with ToanAZ (do not silently change it).

- [ ] **Step 2: Run to verify failure.**

- [ ] **Step 3: Create the two YAML files.** `speech.yaml`:

```yaml
rules:
  - id: S1
    title: "Speech channel without a high-pass filter"
    severity: warning
    source: "docs/knowledge-base/02-event-ops-framework/Core-Skills-Overview.md L690: 'Non-negotiable rule: every speech channel gets an HPF.'; L752 targets 100% by 'Configuration audit'"
    rationale: >
      A lectern mic with no HPF in a room with typical HVAC wastes 6-10
      dB of usable headroom on inaudible rumble and reduces gain before
      feedback for no benefit (L690, quoted). L752's metrics table names
      "Configuration audit" as the measurement method -- the source
      itself says this is a file-inspectable rule. Fires on any channel
      whose classified kind starts with speech.; sung-vocal HPF corners
      differ from spoken ones (L680-681) but every row of the L674 table
      has SOME high-pass, so absence is flaggable at one severity for
      all of them.
    requires_classifier: true
    when:
      for_each: channel
      where:
        channel.source_type: {starts_with: "speech."}
        channel.filter.low_cut_on: false
    message: >
      Channel {channel.number} ({channel.name}) classifies as
      {channel.source_type} and its low-cut filter is off.

  - id: S2
    title: "Music-family channel inside an active automix group"
    severity: error
    source: "docs/knowledge-base/01-live-audio-ai/AI-Plugins-In-Live-Sound.md L385-386: 'Do not put a music channel (playback, walk-in, a performing instrument) into an automix group.'; Core-Skills-Overview.md L711; Corporate-B2B-Events.md L657"
    rationale: >
      Sustained broadband content wins the gain-sharing fight permanently
      and ducks all speech mics (L385-386, quoted). Checks
      post_insert.on, not just the group assignment, for the same reason
      E6 does: a configured-but-inactive automix is a false positive.
      Checks post_insert because that is where WING automix lives
      (Corporate-B2B L646 puts Automix in the INS 2 slot; the observed
      raw postins block carries mode AUTO_X) -- an assumption to
      re-verify if a future scene shows automix in preins. Lectern mics
      are deliberately out of scope: Corporate-B2B L657 hedges them
      ("or, better, assign it to X too and let it win by weight").
    requires_classifier: true
    when:
      for_each: channel
      where:
        channel.post_insert.on: true
        channel.post_insert.automix_group: {not: null}
      any_of:
        - channel.source_type: {in: [utility.playback, utility.click]}
        - channel.source_type: {starts_with: "instrument."}
        - channel.source_type: {starts_with: "drums."}
    message: >
      Channel {channel.number} ({channel.name}) classifies as
      {channel.source_type} and sits in automix group
      {channel.post_insert.automix_group} with the insert on. Sustained
      broadband content ducks every speech mic in the group.
```

`monitors_quality.yaml`:

```yaml
rules:
  - id: G10
    title: "IEM output receives no ambient mic"
    severity: info
    source: "docs/knowledge-base/02-event-ops-framework/Core-Skills-Overview.md L471: 'For IEM, supply ambient mics... Without ambience, performers over-sing because they cannot hear the room.'; Technical-Rider-Spec.md L292 marks ambient-into-every-IEM [R]"
    rationale: >
      Without ambience, IEM performers are acoustically isolated and
      over-sing. Info, not warning: a small show may deliberately run
      IEM without ambient mics, and the profile mechanism exists for
      recording exactly that; on the known real file this fires on all
      four IEM matrices because no ambient channel exists at all.
    requires_classifier: true
    when:
      for_each: output
      where:
        bus.role: monitor.iem
        bus.receives_ambient: false
    message: >
      {bus.kind} {bus.number} ({bus.name}) is an IEM output and no
      confidently-classified ambient mic channel sends to it.

  - id: G11
    title: "More than five narrow notches on a monitor output"
    severity: warning
    source: "docs/knowledge-base/03-event-type-sops/Live-Entertainment-Shows.md L556: 'Five is the typical maximum -- beyond that, more notches are indicative of a placement problem, not an EQ problem.'; Core-Skills-Overview.md L470; Risk-Contingency-Matrix.md L88"
    rationale: >
      The three sources disagree on notch geometry and count and this
      rule records the chosen envelope. Core-Skills L470: Q 20-30, -6 to
      -12 dB, 2-3 modes maximum. Live-Entertainment L554-556: Q 8-10,
      6-12 dB deep, five maximum. Risk-Contingency L88: Q 8-12, 3-6 dB.
      Chosen: a notch is q >= 8 with a cut of 6 dB or more (the loosest
      bound all three call a notch), threshold above five (the loosest
      maximum) -- the permissive envelope, so a finding means every
      source agrees something is wrong, and the fix is physical, not EQ.
    requires_classifier: true
    when:
      for_each: output
      where:
        bus.role: {starts_with: monitor}
        bus.notch_count: {gt: 5}
    message: >
      {bus.kind} {bus.number} ({bus.name}) carries {bus.notch_count}
      narrow deep EQ cuts. Beyond five, the sources call this a
      loudspeaker-placement or mic-pattern problem, not an EQ problem.

  - id: G12
    title: "EQ boost above 8 kHz on a house output"
    severity: info
    source: "docs/knowledge-base/01-live-audio-ai/AI-Plugins-In-Live-Sound.md L490-492: 'Do not EQ it back in at the console -- you will only overdrive the HF drivers for the front rows. Use a delay zone with its own HF trim instead.'"
    rationale: >
      Air absorption rolls off 6-10 dB above 8 kHz at the back of a
      large room; boosting it back at the console overdrives the HF
      drivers for the front rows. Info, not warning, because the same
      document's L486 house-curve table prescribes "+2 dB above 8 kHz"
      for a small-format live band: L490 is about compensating a large
      room, L486 about voicing a small rig, and a scene file cannot
      tell the rooms apart.
    requires_classifier: true
    when:
      for_each: output
      where:
        bus.role: {in: [main, pa_zone]}
        bus.max_boost_above_8k: {not: null}
    message: >
      {bus.kind} {bus.number} ({bus.name}) boosts {bus.max_boost_above_8k}
      dB above 8 kHz. If this compensates air absorption at the back of
      the room, the sources say to use a delay zone with its own HF trim
      instead.
```

- [ ] **Step 4: Probe the real file for S1 and G12** and replace the S1 placeholder assertion with the probed target list (with a comment naming each channel and its raw `flt.lc` value). G10's four matrices are asserted directly (premise verified in this plan's prep: no ambient-named channels exist). Update the counts test. Full suite.

- [ ] **Step 5: Commit**

```bash
git add wing_parser/advisory/base_rules/ tests/
git commit -m "Add speech HPF, automix-exclusion and monitor-quality rules"
```

---

### Task 11: Corporate preset rules PC1–PC8

**Files:**
- Create: `wing_parser/advisory/base_rules/presets_corporate.yaml`
- Test: `tests/test_advisory_rules_presets.py` (new)

**Interfaces:**
- Consumes: `speech.lectern`, `speech.panel`, `speech.qa`, `speech.mc` roles; `eq_has_lowmid_cut`, `eq_has_presence_lift`; `event:` mechanism (Task 4).
- Produces rule ids `PC1`–`PC8`, all `severity: info`, all `event: corporate`, all `requires_classifier: true`.

- [ ] **Step 1: Write the failing tests** — create `tests/test_advisory_rules_presets.py` (same header as Task 8's file). One firing test and one silent test per rule; all follow this exact shape, varying only the mutation and rule id — write all sixteen out:

```python
def _presets(scene, rule_id):
    return [f for f in scene.advisory.run() if f.rule_id == rule_id]


def test_pc1_fires_on_a_lectern_hpf_outside_the_window(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "LECTERN"
        ae["ch"]["20"]["flt"]["lc"] = True
        ae["ch"]["20"]["flt"]["lcf"] = 60.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PC1")] == ["ch.20"]

def test_pc1_accepts_110_hz(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "LECTERN"
        ae["ch"]["20"]["flt"]["lc"] = True
        ae["ch"]["20"]["flt"]["lcf"] = 110.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert _presets(scene, "PC1") == []

def test_pc2_fires_when_the_boundary_cut_is_missing(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "LECTERN"
        eq = ae["ch"]["20"]["peq"]
        eq["on"] = True
        for i in range(1, 5):
            eq[f"{i}g"] = 0.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PC2")] == ["ch.20"]

def test_pc2_accepts_a_250_hz_cut(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "LECTERN"
        eq = ae["ch"]["20"]["peq"]
        eq["on"] = True
        eq["1g"], eq["1f"], eq["1q"] = -3.0, 250.0, 1.4
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert _presets(scene, "PC2") == []

def test_pc3_fires_without_a_presence_lift(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "PANEL 1"
        eq = ae["ch"]["20"]["peq"]
        eq["on"] = True
        for i in range(1, 5):
            eq[f"{i}g"] = 0.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PC3")] == ["ch.20"]

def test_pc3_accepts_a_3k_lift(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "PANEL 1"
        eq = ae["ch"]["20"]["peq"]
        eq["on"] = True
        eq["2g"], eq["2f"], eq["2q"] = 2.0, 3000.0, 1.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert _presets(scene, "PC3") == []

def test_pc4_fires_on_a_deep_lectern_gate(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "LECTERN"
        gate = ae["ch"]["20"]["gate"]
        gate["on"], gate["range"], gate["thr"] = True, 30, -48
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PC4")] == ["ch.20"]

def test_pc4_accepts_the_documented_envelope(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "LECTERN"
        gate = ae["ch"]["20"]["gate"]
        gate["on"], gate["range"], gate["thr"] = True, 12, -48
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert _presets(scene, "PC4") == []

def test_pc5_fires_on_heavy_speech_compression(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "LECTERN"
        dyn = ae["ch"]["20"]["dyn"]
        dyn["on"], dyn["ratio"] = True, 8
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PC5")] == ["ch.20"]

def test_pc5_accepts_three_to_one(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "LECTERN"
        dyn = ae["ch"]["20"]["dyn"]
        dyn["on"], dyn["ratio"] = True, 3
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert _presets(scene, "PC5") == []

def test_pc6_fires_on_a_panel_hpf_outside_the_window(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "PANEL 1"
        ae["ch"]["20"]["flt"]["lc"] = True
        ae["ch"]["20"]["flt"]["lcf"] = 80.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PC6")] == ["ch.20"]

def test_pc6_accepts_120_hz(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "PANEL 1"
        ae["ch"]["20"]["flt"]["lc"] = True
        ae["ch"]["20"]["flt"]["lcf"] = 120.0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert _presets(scene, "PC6") == []

def test_pc7_fires_when_the_mc_has_no_weight_advantage(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "MC"
        ins = ae["ch"]["20"]["postins"]
        ins["on"], ins["w"] = True, 0
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PC7")] == ["ch.20"]

def test_pc7_accepts_plus_four(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "MC"
        ins = ae["ch"]["20"]["postins"]
        ins["on"], ins["w"] = True, 4
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert _presets(scene, "PC7") == []

def test_pc8_fires_on_an_unmuted_qa_mic(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "Q&A 1"
        ae["ch"]["20"]["mute"] = False
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert [f.target for f in _presets(scene, "PC8")] == ["ch.20"]

def test_pc8_accepts_a_muted_qa_mic(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    def mutate(ae):
        ae["ch"]["20"]["name"] = "Q&A 1"
        ae["ch"]["20"]["mute"] = True
    scene = _mutated_scene(vu_path, tmp_path, mutate)
    assert _presets(scene, "PC8") == []


def test_corporate_presets_are_off_under_a_band_profile(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.advisory.resolver import off_event_ids
    scene = WingScene.load(vu_path)
    shows = tmp_path / "shows"; shows.mkdir(parents=True, exist_ok=True)
    (shows / "bandshow.yaml").write_text("rules: []\nevent: band\n", encoding="utf-8")
    off = off_event_ids(scene, tmp_path, "bandshow")
    assert {f"PC{i}" for i in range(1, 9)} <= set(off)
    assert all(v == "corporate" for k, v in off.items() if k.startswith("PC"))
```

Watch PC7's premise: `postins.w` observed at −12 default; the query layer's `automix_weight` mapping — confirm with `python -c "..."` that `scene.channel(20).post_insert.automix_weight` reflects `w` and `automix_group` is non-null when `mode` is `AUTO_X`; if `automix_group` is derived from `mode` regardless of `on`, PC7 must also require `channel.post_insert.on: true` (it does, below).

- [ ] **Step 2: Run to verify failure.**

- [ ] **Step 3: Create `presets_corporate.yaml`.** All eight follow one shape; the full file (write it exactly — severities all info, `event: corporate` on every rule):

```yaml
# Textbook starting values for corporate speech events. Deviation is
# information, never an error: the sources call these "starting point"
# values, and ToanAZ chose (2026-08-16) to ship them at info with the
# profile mechanism available to switch whole event families off.
rules:
  - id: PC1
    title: "Lectern HPF outside the 90-160 Hz window"
    severity: info
    event: corporate
    source: "docs/knowledge-base/03-event-type-sops/Corporate-B2B-Events.md L545: 'HPF 100 Hz, 12 dB/oct (raise to 120 Hz for a boomy male voice)'; Core-Skills-Overview.md L679: lectern gooseneck 100-150 Hz"
    rationale: >
      The two sources give 100-120 and 100-150; the window here is 90-160
      -- wide enough to span both plus boundary tolerance, so a finding
      means the corner is genuinely somewhere else.
    requires_classifier: true
    when:
      for_each: channel
      where:
        channel.source_type: speech.lectern
      any_of:
        - channel.filter.low_cut_on: false
        - channel.filter.low_cut_hz: {lt: 90.0}
        - channel.filter.low_cut_hz: {gt: 160.0}
    message: >
      Channel {channel.number} ({channel.name}): lectern preset expects a
      high-pass near 100-120 Hz; low cut on = {channel.filter.low_cut_on},
      corner = {channel.filter.low_cut_hz} Hz.

  - id: PC2
    title: "Lectern/panel channel missing the low-mid boundary cut"
    severity: info
    event: corporate
    source: "docs/knowledge-base/03-event-type-sops/Corporate-B2B-Events.md L546: '-3 to -4 dB, 300 Hz, Q 1.4'; L678: '-3 dB @ 250 Hz, Q 1.4'"
    rationale: >
      A hard lectern or table top reflects into the capsule and builds
      200-500 Hz by 4-6 dB (L546 reason column). The check is presence of
      ANY cut in 200-500 Hz, not its exact depth: L499 of
      AI-Plugins-In-Live-Sound notes rooms where the panel cut should be
      -6, so depth is a room call.
    requires_classifier: true
    when:
      for_each: channel
      where:
        channel.source_type: {in: [speech.lectern, speech.panel]}
        channel.eq.on: true
        channel.eq_has_lowmid_cut: false
    message: >
      Channel {channel.number} ({channel.name}): the corporate preset
      carries a boundary cut near 250-300 Hz and this EQ has no cut
      anywhere in 200-500 Hz.

  - id: PC3
    title: "Lectern/panel channel missing the presence lift"
    severity: info
    event: corporate
    source: "docs/knowledge-base/03-event-type-sops/Corporate-B2B-Events.md L547: '+2 to +3 dB, 3 kHz, Q 1.0 -- Consonant articulation; the biggest single STI improvement available'; L679: '+2 dB @ 3.5 kHz'"
    rationale: >
      Consonant articulation lives at 2-4 kHz; the preset lift there is
      the cheapest intelligibility gain the sources name.
    requires_classifier: true
    when:
      for_each: channel
      where:
        channel.source_type: {in: [speech.lectern, speech.panel]}
        channel.eq.on: true
        channel.eq_has_presence_lift: false
    message: >
      Channel {channel.number} ({channel.name}): the corporate preset
      lifts 3-3.5 kHz and this EQ has no boost anywhere in 2-4 kHz.

  - id: PC4
    title: "Lectern gate outside the documented envelope"
    severity: info
    event: corporate
    source: "docs/knowledge-base/03-event-type-sops/Corporate-B2B-Events.md L549: 'Threshold -48 dBFS, range 12 dB... Prefer automix over gating. If gating, keep range shallow so it never chatters'"
    rationale: >
      The preset gates a lectern at -48 dBFS with 12 dB of range at most;
      a deeper range chatters, a threshold far above -40 gates on speech
      itself. ROS L274 verifies -60 dB for panel goosenecks -- this rule
      deliberately bounds only the lectern case.
    requires_classifier: true
    when:
      for_each: channel
      where:
        channel.source_type: speech.lectern
        channel.gate.on: true
      any_of:
        - channel.gate.range_dB: {gt: 12.0}
        - channel.gate.threshold_dB: {gt: -40.0}
    message: >
      Channel {channel.number} ({channel.name}): lectern gate at
      threshold {channel.gate.threshold_dB} dBFS, range
      {channel.gate.range_dB} dB; the preset is -48 dBFS with range 12.

  - id: PC5
    title: "Speech compression ratio above 4:1"
    severity: info
    event: corporate
    source: "docs/knowledge-base/02-event-ops-framework/Core-Skills-Overview.md L438: 'compression 2:1 to 3:1 with 3-6 dB gain reduction on peaks for speech'; Corporate-B2B-Events.md L550, L680 both 3:1"
    rationale: >
      Every speech preset in the knowledge base sits at 2:1-3:1. Above
      4:1 speech starts pumping; the threshold here is 4 so the
      documented 3:1 passes with margin.
    requires_classifier: true
    when:
      for_each: channel
      where:
        channel.source_type: {starts_with: "speech."}
        channel.dyn.on: true
        channel.dyn.ratio: {gt: 4.0}
    message: >
      Channel {channel.number} ({channel.name}): speech compression at
      {channel.dyn.ratio}:1; the presets sit at 2:1-3:1.

  - id: PC6
    title: "Panel HPF outside the 100-160 Hz window"
    severity: info
    event: corporate
    source: "docs/knowledge-base/03-event-type-sops/Corporate-B2B-Events.md L677: 'HPF 120 Hz, 12 dB/oct (table mics pick up more LF than lectern mics)'"
    rationale: >
      Table mics take more structure-borne LF than lectern mics, so the
      panel preset corner is higher (120 vs 100). Window 100-160.
    requires_classifier: true
    when:
      for_each: channel
      where:
        channel.source_type: speech.panel
      any_of:
        - channel.filter.low_cut_on: false
        - channel.filter.low_cut_hz: {lt: 100.0}
        - channel.filter.low_cut_hz: {gt: 160.0}
    message: >
      Channel {channel.number} ({channel.name}): panel preset expects a
      high-pass near 120 Hz; low cut on = {channel.filter.low_cut_on},
      corner = {channel.filter.low_cut_hz} Hz.

  - id: PC7
    title: "MC in an automix group without a weight advantage"
    severity: info
    event: corporate
    source: "docs/knowledge-base/03-event-type-sops/Corporate-B2B-Events.md L648: 'raise the moderator +3 to +6 dB so they can always cut in'; L681: '(moderator +4 dB)'"
    rationale: >
      The moderator must win a simultaneous-talk fight. speech.mc is the
      moderator/host proxy -- on ToanAZ's shows the MC is the host. The
      DSL has no lte, so the check is lt 3.0: a null weight fails lt and
      stays silent, which is correct -- an absent weight is not a stated
      value.
    requires_classifier: true
    when:
      for_each: channel
      where:
        channel.source_type: speech.mc
        channel.post_insert.on: true
        channel.post_insert.automix_group: {not: null}
        channel.post_insert.automix_weight: {lt: 3.0}
    message: >
      Channel {channel.number} ({channel.name}) is the MC in automix
      group {channel.post_insert.automix_group} at weight
      {channel.post_insert.automix_weight} dB; the preset gives the
      moderator +3 to +6 dB.

  - id: PC8
    title: "Q&A mic unmuted in the saved scene"
    severity: info
    event: corporate
    source: "docs/knowledge-base/02-event-ops-framework/Core-Skills-Overview.md L499: audience Q&A mics 'Killed by default, opened only during Q&A'; L741: 'Q&A mic feeds back instantly'"
    rationale: >
      An audience-facing mic that is open by default is the fastest
      feedback in the book (L741). The stated exception is real -- a
      scene saved DURING Q&A legitimately trips this -- which is why it
      is info, and why the profile mechanism exists.
    requires_classifier: true
    when:
      for_each: channel
      where:
        channel.source_type: speech.qa
        channel.muted: false
    message: >
      Channel {channel.number} ({channel.name}) classifies as an
      audience/Q&A mic and is not muted in this scene.
```

- [ ] **Step 4: Run the new tests, probe the real file (all PC rules must be silent — no lectern/panel/qa names exist; the MC bus exists but `speech.mc` is a channel domain — verify), update counts test, full suite.**

- [ ] **Step 5: Commit**

```bash
git add wing_parser/advisory/base_rules/presets_corporate.yaml tests/test_advisory_rules_presets.py
git commit -m "Add the corporate speech preset rules"
```

---

### Task 12: Band preset rules PB1–PB6

**Files:**
- Create: `wing_parser/advisory/base_rules/presets_band.yaml`
- Test: `tests/test_advisory_rules_presets.py` (append)

**Interfaces:**
- Consumes: `drums.*`, `instrument.bass`, `utility.click` roles; `effective_polarity`, `iem_send_count`.
- Produces rule ids `PB1`–`PB6`, all `severity: info`, all `event: band`.

- [ ] **Step 1: Write the failing tests** — append; same shape as Task 11 (one firing, one silent per rule). The firing mutations:

```python
# PB1: name "SNARE BOT", in.set.inv False (and source polarity False) -> fires;
#      silent when ae["ch"]["20"]["in"]["set"]["inv"] = True
# PB2: name "HI HAT", flt.lc True, lcf 100.0 -> fires; silent at lcf 200.0
# PB3: name "RIDE", flt.lc True, lcf 150.0 -> fires; silent at lcf 250.0
# PB4: name "OH L", flt.lc True, lcf 100.0 -> fires; silent at lcf 300.0
# PB5: name "KICK", flt.lc True, lcf 80.0 -> fires; silent at lcf 30.0 and
#      silent when flt.lc is False (HPF off is the documented correct state)
# PB6: name "CLICK", sends MX5+MX6+MX7 on -> fires (3 > 2); silent with two
```

Write each pair out fully in the file — the pattern is the Task 11 shape with these mutations, asserting `[("ch.20", "info")]` / `[]` (PB6 asserts target `ch.20`). Also append the event-filter strengthening test promised in Task 4:

```python
def test_band_presets_are_off_under_a_corporate_profile(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.advisory.resolver import off_event_ids
    scene = WingScene.load(vu_path)
    shows = tmp_path / "shows"; shows.mkdir(parents=True, exist_ok=True)
    (shows / "corp.yaml").write_text("rules: []\nevent: corporate\n", encoding="utf-8")
    off = off_event_ids(scene, tmp_path, "corp")
    assert {f"PB{i}" for i in range(1, 7)} <= set(off)
```

- [ ] **Step 2: Run to verify failure.**

- [ ] **Step 3: Create `presets_band.yaml`:**

```yaml
# Textbook starting values for band shows. Info severity throughout;
# event: band switches the family off under a corporate profile.
rules:
  - id: PB1
    title: "Snare-bottom channel is not polarity inverted"
    severity: info
    event: band
    source: "docs/knowledge-base/04-templates-and-matrices/Technical-Rider-Spec.md L153: snare btm 'Polarity invert' (bolded; repeated L1070)"
    rationale: >
      The bottom mic faces the opposite head; un-inverted it cancels the
      top mic. Checks effective_polarity -- channel inversion XOR source
      inversion -- because inverting twice is not inverting.
    requires_classifier: true
    when:
      for_each: channel
      where:
        channel.source_type: drums.snare.bottom
        channel.effective_polarity: false
    message: >
      Channel {channel.number} ({channel.name}) classifies as snare
      bottom and its effective polarity is not inverted.

  - id: PB2
    title: "Hi-hat HPF outside the 160-250 Hz window"
    severity: info
    event: band
    source: "docs/knowledge-base/04-templates-and-matrices/Technical-Rider-Spec.md L154: hi-hat 'HPF 200 Hz'"
    rationale: >
      The hat mic needs nothing below 200 Hz; what is there is snare and
      kick bleed.
    requires_classifier: true
    when:
      for_each: channel
      where:
        channel.source_type: drums.hihat
      any_of:
        - channel.filter.low_cut_on: false
        - channel.filter.low_cut_hz: {lt: 160.0}
        - channel.filter.low_cut_hz: {gt: 250.0}
    message: >
      Channel {channel.number} ({channel.name}): hi-hat preset is a
      high-pass near 200 Hz; low cut on = {channel.filter.low_cut_on},
      corner = {channel.filter.low_cut_hz} Hz.

  - id: PB3
    title: "Ride HPF outside the 200-300 Hz window"
    severity: info
    event: band
    source: "docs/knowledge-base/04-templates-and-matrices/Technical-Rider-Spec.md L160: ride 'HPF 250 Hz'"
    rationale: >
      Same reasoning as the hi-hat, one row down the input list.
    requires_classifier: true
    when:
      for_each: channel
      where:
        channel.source_type: drums.ride
      any_of:
        - channel.filter.low_cut_on: false
        - channel.filter.low_cut_hz: {lt: 200.0}
        - channel.filter.low_cut_hz: {gt: 300.0}
    message: >
      Channel {channel.number} ({channel.name}): ride preset is a
      high-pass near 250 Hz; low cut on = {channel.filter.low_cut_on},
      corner = {channel.filter.low_cut_hz} Hz.

  - id: PB4
    title: "Overhead HPF outside the 160-450 Hz window"
    severity: info
    event: band
    source: "docs/knowledge-base/02-event-ops-framework/Core-Skills-Overview.md L686: 'Overheads / cymbals | 200-400 Hz | 12-18 dB/oct | Reject kick and tom bleed'"
    rationale: >
      Overheads carry cymbals; kick and tom energy under 200 Hz is bleed
      by definition.
    requires_classifier: true
    when:
      for_each: channel
      where:
        channel.source_type: drums.overhead
      any_of:
        - channel.filter.low_cut_on: false
        - channel.filter.low_cut_hz: {lt: 160.0}
        - channel.filter.low_cut_hz: {gt: 450.0}
    message: >
      Channel {channel.number} ({channel.name}): overhead preset is a
      high-pass at 200-400 Hz; low cut on = {channel.filter.low_cut_on},
      corner = {channel.filter.low_cut_hz} Hz.

  - id: PB5
    title: "Kick or bass high-passed above 45 Hz"
    severity: info
    event: band
    source: "docs/knowledge-base/02-event-ops-framework/Core-Skills-Overview.md L687: 'Kick / bass | Off, or 30 Hz | 12 dB/oct | Protect sub drivers from DC/subsonic only'"
    rationale: >
      The one row of the HPF table where off is correct. Only a HIGH
      corner is flagged: it eats the instrument's fundamentals. HPF off
      never fires this rule.
    requires_classifier: true
    when:
      for_each: channel
      where:
        channel.filter.low_cut_on: true
        channel.filter.low_cut_hz: {gt: 45.0}
      any_of:
        - channel.source_type: {starts_with: drums.kick}
        - channel.source_type: instrument.bass
    message: >
      Channel {channel.number} ({channel.name}): kick/bass preset is HPF
      off or 30 Hz; this channel's corner is
      {channel.filter.low_cut_hz} Hz.

  - id: PB6
    title: "Click reaches more than two IEM mixes"
    severity: info
    event: band
    source: "docs/knowledge-base/03-event-type-sops/Live-Entertainment-Shows.md L609: click 'Drummer only'; L635: 'Click track audible to drummer and bassist only'"
    rationale: >
      The document disagrees with itself -- L609 says drummer only, L635
      says drummer and bassist -- so the chosen threshold is the
      permissive reading: more than two IEM destinations. The
      unconditional half (click into a FOH main) is R1 at error.
    requires_classifier: true
    when:
      for_each: channel
      where:
        channel.source_type: utility.click
        channel.iem_send_count: {gt: 2}
    message: >
      Channel {channel.number} ({channel.name}) looks like a click track
      and reaches {channel.iem_send_count} IEM mixes; the sources allow
      the drummer, at most the bassist too.
```

- [ ] **Step 4: Run new tests, probe both files (real file has DRUM bus but check whether any CHANNEL classifies drums.\* with a firing condition — probe, then either extend the expected real-file table or confirm silence), update counts test, full suite.**

- [ ] **Step 5: Commit**

```bash
git add wing_parser/advisory/base_rules/presets_band.yaml tests/test_advisory_rules_presets.py
git commit -m "Add the band preset rules"
```

---

### Task 13: The real-file contract test

**Files:**
- Create: `tests/test_advisory_realfile.py`
- Modify: `tests/test_advisory_rules.py` (retire the per-rule count assertions that the new table duplicates — keep the behavioural ones)

**Interfaces:** consumes everything; produces the regression contract.

- [ ] **Step 1: Generate the table.** Run the probe (Task 2 Step 4 script) one final time against both files. Then write `tests/test_advisory_realfile.py`:

```python
"""The full advisory contract on the two shipped sample files.

Any rule change that shifts real-file behaviour must edit this table in
the same commit, with the probe evidence in the diff. Generated from a
live run on 2026-08-16 -- regenerate with:
python - <<'EOF'
import os; os.environ["WING_DISABLE_LLM"] = "1"
from wing_parser import WingScene
for f in sorted(WingScene.load("user-files/example-Vu.snap").advisory.run(),
                key=lambda f: (f.rule_id, f.target)):
    print(f'    ("{f.rule_id}", "{f.target}", "{f.severity}"),')
EOF
"""
import pytest

from wing_parser import WingScene

EXPECTED_VU = [
    # PASTE THE PROBE OUTPUT HERE -- every row spot-checked against the
    # raw JSON before commit. Do not hand-compose rows.
]


def test_the_real_file_advisory_contract(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    scene = WingScene.load(vu_path)
    got = sorted((f.rule_id, f.target, f.severity) for f in scene.advisory.run())
    assert got == sorted(EXPECTED_VU)


def test_the_factory_scene_stays_silent(factory_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    assert WingScene.load(factory_path).advisory.run() == []


def test_the_small_profile_still_suppresses_g8(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    # Uses the real in-repo knowledge dir: shows/small.yaml supersedes G8.
    import os
    from wing_parser import config
    monkeypatch.delenv(config.ENV_VAR, raising=False)
    scene = WingScene.load(vu_path)
    found = scene.advisory.run("small")
    assert not any(f.rule_id == "G8" for f in found)
    assert scene.advisory.suppressed("small") == {"G8": "show.small.post-monitors-are-deliberate"}
```

The `EXPECTED_VU` list is filled from the probe, and at least three rows must be spot-checked against raw JSON values in a comment (e.g. the G9 sidefill row against `bus.7.dyn.on`, one G8 MX row against its raw `mode`, one G10 row against the absence of ambient names).

- [ ] **Step 2: Run the new file, prune the duplicated count test from `test_advisory_rules.py`** (keep every behavioural test — message contents, evidence, any_of indices), full suite.

- [ ] **Step 3: Commit**

```bash
git add tests/
git commit -m "Pin the real-file advisory contract"
```

---

### Task 14: Documentation sweep

**Files:**
- Modify: `README.md`, `skills/` (every file the greps hit), `examples/` if applicable

**Interfaces:** none — prose only.

- [ ] **Step 1: Grep the whole tree** (the closure lesson — the first fix round caught two of five copies):

```bash
grep -rn "G7\|G8\|E6\|three.*rule\|3 rule" README.md skills/ examples/ --include="*.md" --include="*.py"
grep -rn "monitor" README.md skills/*.md | grep -vi "monitor.iem\|monitor.wedge"
```

- [ ] **Step 2: Update every hit:** the rule table (now ~30 rules across 7 files — list id, severity, event, one-line description), the monitor role hierarchy, the `output`/`channel.main_sends` iterators, the `event:` mechanism and its `[off-event]` transparency line, the `starts_with` operator, and the derived-property list. State plainly which rules are info-tier presets. Do not edit `docs/handoff/` or `docs/superpowers/` history.

- [ ] **Step 3: Re-run the greps; zero stale hits. Full suite one last time: `python -m pytest tests/ -q` — record the final pass count.**

- [ ] **Step 4: Commit**

```bash
git add README.md skills/ examples/
git commit -m "Document the grown rule set, the event mechanism and the monitor split"
```

---

## Self-review record (spec → plan)

- Spec §3.1 → Tasks 2 (iterators), §3.2 → Task 3, §3.3 → Task 1, §3.4 → Tasks 5–6, §3.5 → Task 4, §3.6 → file placements in Tasks 8–12; §4 structural rules → Tasks 3, 8, 9, 10; §5 presets → Tasks 11, 12; §6 expected behaviour → Task 13; §7 testing → every task's steps + Task 13; §8 killed/blocked → no tasks, by design; §9 docs → Task 14; §10 constraints → Global Constraints.
- The `_monitor_bus_count` change (spec §3.1 last bullet) lands in Task 3 with the split, since it depends on `is_monitor`.
- Type consistency: `off_event_ids` returns `dict[rule_id -> rule.event]` (Task 4) and Tasks 11/12 assert exactly that shape. Property names in YAML (`bus.notch_count`, `channel.in_use`, …) match the Task 5/6 definitions verbatim.
- Known intentional deviation: none.
