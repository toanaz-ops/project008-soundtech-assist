# Advisory Loop Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the advisory engine's upper two layers usable — a `--profile` flag to declare a small show, an `any_of` key so two base rules can express the `OR` their rationales state, and the first real content in `knowledge/toanaz/`.

**Architecture:** Six tasks over the existing `wing_parser/advisory/` package plus its two interface surfaces. Nothing new is introduced except one predicate key and one flag; the rest is narrowing, threading a parameter, and writing YAML. No new scene analysis, no new conditions, no new base rules.

**Tech Stack:** Python 3.11+, PyYAML, ruamel.yaml, pytest. Stdlib `argparse` for the CLI. `mcp` is an optional extra and stays uninstalled.

**Spec:** `docs/superpowers/specs/2026-08-16-advisory-loop-closure-design.md`

## Global Constraints

- ~200 lines per source file, split by responsibility layer, not by convenience.
- `core/` may import only stdlib, PyYAML and ruamel, and never from a layer above it.
- The advisory engine is **deterministic**: no LLM call, no network, no randomness. The same scene and rule set produce the same findings in the same order.
- The tool runs fully offline. With no key, no network, or the kill switch set, only unresolvable names degrade to `unknown`.
- Never fabricate a value the file does not state.
- Descriptors and advisory rules are YAML data, not Python.
- Files under `knowledge/` are written with `ruamel.yaml` round-trip, never `yaml.safe_dump`. This plan only *reads* them, so `yaml.safe_load` is correct throughout.
- Every `Finding` records its deciding layer (`base` / `toanaz` / `show`).
- Every advisory rule YAML carries `source:` and `rationale:`.
- Do not move, rewrite or edit anything under `docs/knowledge-base/`.
- Float comparisons in tests use `pytest.approx`.
- Run tests with `python -m pytest`. Baseline before this plan: **364 passed, 1 skipped, 1 warning**. The skip is the FastMCP build test; the warning is a deliberate unasserted one in `test_read_log_skips_a_corrupt_line`. Both must still be there at the end.
- Measured baseline on `user-files/example-Vu.snap`: **17 findings** — G8×12, G7×4 (buses 7-10), E6×1 (ch.11).

---

### Task 1: `any_of` in the model, loader and evaluator

**Files:**
- Modify: `wing_parser/advisory/models.py`
- Modify: `wing_parser/advisory/loader.py`
- Modify: `wing_parser/advisory/layers.py`
- Modify: `wing_parser/advisory/evaluator.py`
- Test: `tests/test_advisory_predicates.py`
- Test: `tests/test_advisory_evaluator.py`

**Interfaces:**
- Consumes: `Rule`, `all_match`, `resolve_path`, `_validate_where`
- Produces:
  - `Rule.any_of: tuple[dict[str, Any], ...]` — defaults to `()`
  - `wing_parser.advisory.loader._validate_any_of(raw, path: Path, rule_id: str) -> tuple[dict, ...]`
  - `Finding.evidence["_any_of"]` — the index of the matched clause, present only on rules that have `any_of`

- [ ] **Step 1: Write the failing loader tests**

Add to `tests/test_advisory_predicates.py`:

```python
def _rule_doc(**when_extra):
    when = {"for_each": "channel", "where": {"channel.muted": True}}
    when.update(when_extra)
    return {"rules": [{"id": "T", "title": "t", "severity": "warning",
                       "source": "s", "rationale": "r", "when": when,
                       "message": "m"}]}


def test_any_of_clauses_are_read_into_the_rule(tmp_path: Path):
    path = tmp_path / "r.yaml"
    path.write_text(
        yaml.safe_dump(_rule_doc(any_of=[{"channel.number": 8},
                                         {"channel.name": "HS4"}])),
        encoding="utf-8",
    )
    rule = load_rules(path, layer="base")[0]
    assert rule.any_of == ({"channel.number": 8}, {"channel.name": "HS4"})


def test_an_empty_any_of_is_rejected(tmp_path: Path):
    """`any_of:` with the value left off would make any() False and kill
    the rule in silence -- the same present-but-null shape as `enabled:`."""
    path = tmp_path / "empty.yaml"
    path.write_text(
        "rules:\n"
        "  - id: T\n    title: t\n    severity: warning\n    source: s\n"
        "    rationale: r\n    message: m\n"
        "    when:\n      for_each: channel\n      where: {}\n"
        "      any_of:\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="any_of"):
        load_rules(path, layer="base")


def test_an_any_of_that_is_a_list_but_empty_is_rejected(tmp_path: Path):
    path = tmp_path / "empty-list.yaml"
    path.write_text(yaml.safe_dump(_rule_doc(any_of=[])), encoding="utf-8")
    with pytest.raises(ValueError, match="any_of"):
        load_rules(path, layer="base")


def test_a_non_list_any_of_is_rejected(tmp_path: Path):
    path = tmp_path / "scalar.yaml"
    path.write_text(yaml.safe_dump(_rule_doc(any_of="channel.number")), encoding="utf-8")
    with pytest.raises(ValueError, match="any_of"):
        load_rules(path, layer="base")


def test_a_nested_any_of_is_rejected(tmp_path: Path):
    """One level only. The predicate language stays small on purpose."""
    path = tmp_path / "nested.yaml"
    path.write_text(
        yaml.safe_dump(_rule_doc(any_of=[{"any_of": [{"channel.number": 8}]}])),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="nest"):
        load_rules(path, layer="base")


def test_an_unknown_operator_inside_an_any_of_clause_is_rejected(tmp_path: Path):
    """Operator validation stopped at `where` and must reach in here too."""
    path = tmp_path / "op.yaml"
    path.write_text(
        yaml.safe_dump(_rule_doc(any_of=[{"channel.number": {"greater": 8}}])),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="greater"):
        load_rules(path, layer="base")


def test_a_principle_may_also_carry_any_of(tmp_path: Path):
    """layers._as_rules reads the same when: block and must validate it
    the same way; the toanaz layer is the hand-edited one."""
    directory = tmp_path / "knowledge"
    directory.mkdir()
    (directory / "principles.yaml").write_text(
        "principles:\n"
        "  - id: p1\n    principle: x\n    source: s\n    rationale: r\n"
        "    when:\n      for_each: channel\n      where: {}\n"
        "      any_of:\n",
        encoding="utf-8",
    )
    from wing_parser.advisory.layers import _principles
    with pytest.raises(ValueError, match="any_of"):
        _principles(directory)
```

- [ ] **Step 2: Run them and verify they fail**

Run: `python -m pytest tests/test_advisory_predicates.py -k any_of -v`
Expected: FAIL — `TypeError: Rule.__init__() got an unexpected keyword argument 'any_of'` on the first, and no `ValueError` raised on the rest.

- [ ] **Step 3: Add the field to the model**

In `wing_parser/advisory/models.py`, add to `Rule`, after `applies_when` and before `supersedes`:

```python
    any_of: tuple[dict[str, Any], ...] = ()
```

- [ ] **Step 4: Add the loader validation**

In `wing_parser/advisory/loader.py`, add after `_validate_where`:

```python
def _validate_any_of(raw, path: Path, rule_id: str) -> tuple[dict, ...]:
    """Read and check an `any_of` block. One level, never empty.

    `when.get("any_of")` returns None both when the key is absent and
    when it is present with the value left off, so the caller tests
    membership and only reaches here in the second case. That distinction
    is the whole point: an absent `any_of` means "this rule has no OR",
    while a blank one would make `any(...)` False and silently kill the
    rule -- the same present-but-null hazard `_optional` exists for.
    """
    if raw is None:
        raise ValueError(
            f"{path}: rule {rule_id} has an empty any_of; remove the key "
            "or give it at least one clause"
        )
    if not isinstance(raw, list):
        raise ValueError(
            f"{path}: rule {rule_id} has an any_of that must be a list, not "
            f"{type(raw).__name__} ({raw!r})"
        )
    if not raw:
        raise ValueError(
            f"{path}: rule {rule_id} has an empty any_of; remove the key "
            "or give it at least one clause"
        )

    clauses: list[dict] = []
    for clause in raw:
        if not isinstance(clause, dict):
            raise ValueError(
                f"{path}: rule {rule_id} has an any_of clause that must be a "
                f"mapping, not {type(clause).__name__} ({clause!r})"
            )
        if "any_of" in clause:
            raise ValueError(
                f"{path}: rule {rule_id} nests any_of inside an any_of clause; "
                "one level of OR only"
            )
        _validate_where(clause, path, rule_id)
        clauses.append(dict(clause))
    return tuple(clauses)
```

- [ ] **Step 5: Read it in both loaders**

In `loader.py::_rule_from`, replace the two lines that build `where` with:

```python
    where = dict(when.get("where") or {})
    _validate_where(where, where_from, entry["id"])
    any_of = (
        _validate_any_of(when["any_of"], where_from, entry["id"])
        if "any_of" in when
        else ()
    )
```

and add `any_of=any_of,` to the `Rule(...)` call, immediately after `applies_when=...`.

In `layers.py::_as_rules`, make the identical change: after the existing
`_validate_where(where, path, entry["id"])`, add

```python
        any_of = (
            _validate_any_of(when["any_of"], path, entry["id"])
            if "any_of" in when
            else ()
        )
```

and `any_of=any_of,` in its `Rule(...)` call after `applies_when=...`. Add
`_validate_any_of` to the existing `from wing_parser.advisory.loader import ...` line.

- [ ] **Step 6: Run the loader tests**

Run: `python -m pytest tests/test_advisory_predicates.py -v`
Expected: PASS.

- [ ] **Step 7: Write the failing evaluator tests**

Add to `tests/test_advisory_evaluator.py`:

```python
def test_any_of_fires_when_either_clause_matches(scene):
    findings = evaluate(
        scene,
        rule(where={"channel.number": 8},
             any_of=({"channel.name": "nothing"}, {"channel.muted": False})),
    )
    assert [f.target for f in findings] == ["ch.8"]


def test_any_of_does_not_fire_when_no_clause_matches(scene):
    assert evaluate(
        scene,
        rule(where={"channel.number": 8},
             any_of=({"channel.name": "nothing"}, {"channel.muted": True})),
    ) == []


def test_where_still_gates_a_rule_that_has_any_of(scene):
    """`where` is AND with the whole any_of block, not an alternative to it."""
    assert evaluate(
        scene,
        rule(where={"channel.number": 999}, any_of=({"channel.muted": False},)),
    ) == []


def test_evidence_records_which_clause_matched(scene):
    finding = evaluate(
        scene,
        rule(where={"channel.number": 8},
             any_of=({"channel.name": "nothing"}, {"channel.muted": False})),
    )[0]
    assert finding.evidence["_any_of"] == 1
    assert finding.evidence["channel.muted"] is False
    assert finding.evidence["channel.number"] == 8


def test_a_rule_without_any_of_carries_no_marker(scene):
    finding = evaluate(scene, rule(where={"channel.number": 8}))[0]
    assert "_any_of" not in finding.evidence
```

- [ ] **Step 8: Run them and verify they fail**

Run: `python -m pytest tests/test_advisory_evaluator.py -k any_of -v`
Expected: FAIL — the first two produce findings for every channel, because `any_of` is ignored.

- [ ] **Step 9: Evaluate `any_of`**

In `wing_parser/advisory/evaluator.py`, add above `evaluate`:

```python
def _matched_clause(context: dict[str, Any], clauses: tuple[dict, ...]) -> int | None:
    """Index of the first `any_of` clause that matches, or None."""
    for index, clause in enumerate(clauses):
        if all_match(context, clause):
            return index
    return None
```

and replace the body of the target loop in `evaluate` with:

```python
    for target in targets_for(scene, rule.for_each):
        if rule.requires_classifier and target.confidence < LOW:
            continue
        if not all_match(target.context, rule.where):
            continue

        matched = None
        if rule.any_of:
            matched = _matched_clause(target.context, rule.any_of)
            if matched is None:
                continue

        evidence = {path: resolve_path(target.context, path) for path in rule.where}
        if matched is not None:
            evidence.update(
                {path: resolve_path(target.context, path) for path in rule.any_of[matched]}
            )
            evidence["_any_of"] = matched

        findings.append(
            Finding(
                rule_id=rule.id,
                layer=rule.layer,
                severity=rule.severity,
                target=target.name,
                message=render(rule.message, target.context),
                evidence=evidence,
                confidence=target.confidence if rule.requires_classifier else 1.0,
            )
        )
```

- [ ] **Step 10: Run the full suite**

Run: `python -m pytest`
Expected: PASS, 364 + 12 new = **376 passed, 1 skipped, 1 warning**. The 17-finding count on the sample scene is unchanged, because no shipped rule uses `any_of` yet.

- [ ] **Step 11: Prove the empty-`any_of` guard discriminates**

Temporarily delete the two `if raw is None:` / `if not raw:` blocks from `_validate_any_of`, run `python -m pytest tests/test_advisory_predicates.py -k empty -v`, and confirm both tests go red. Restore them and confirm green. Paste both outputs into the report — this guard is the one whose absence fails silently.

- [ ] **Step 12: Commit**

```bash
git add wing_parser/advisory/ tests/test_advisory_predicates.py tests/test_advisory_evaluator.py
git commit -F - <<'EOF'
Add any_of to the predicate language

Two base rules state an OR in their rationale that all_match cannot
express: G7 needs "not a limiter or bypassed", E6 needs "range over 6 or
hold under 200". One level of OR beside where covers both without
turning a small declarative language into a big one, so nesting an
any_of inside an any_of is rejected at load.

An empty any_of raises rather than defaulting. any() over an empty list
is False, so a blank `any_of:` would disable the whole rule in silence --
the same present-but-null shape that has bitten this project five times.
EOF
```

---

### Task 2: A supersede-only rule needs no `when` and no `message`

**Files:**
- Modify: `wing_parser/advisory/loader.py`
- Modify: `wing_parser/advisory/layers.py`
- Modify: `wing_parser/advisory/evaluator.py`
- Test: `tests/test_advisory_predicates.py`
- Test: `tests/test_advisory_resolver.py`

**Interfaces:**
- Produces: `ITERATORS["none"]` — a target iterator that yields nothing, used by rules that exist only for their `supersedes` list

**Why this task exists.** A show-layer rule that only switches a base rule off has no target of its own. `layers._as_rules` already handles that for principles by synthesising `{"for_each": "channel", "where": {"channel.number": -1}}` — a clause that matches nothing because no channel is numbered -1. `loader.load_rules`, which reads `shows/`, raises instead, so the same idea has two different fates depending on which file it is written in. Task 6 needs to write exactly such a rule into `shows/small.yaml`.

The `-1` is also a magic value standing in for "no targets". Replacing it with an explicit empty iterator says what it means and removes the number from both the code and the tests that assert on it.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_advisory_predicates.py`:

```python
def test_a_supersede_only_rule_needs_no_when_or_message(tmp_path: Path):
    path = tmp_path / "show.yaml"
    path.write_text(
        yaml.safe_dump(
            {"rules": [{"id": "show.off", "title": "Wedges tonight",
                        "severity": "info", "source": "show sheet",
                        "rationale": "no in-ear packs", "supersedes": ["G8"]}]}
        ),
        encoding="utf-8",
    )
    rule = load_rules(path, layer="show")[0]
    assert rule.for_each == "none"
    assert rule.where == {}
    assert rule.supersedes == ("G8",)


def test_a_rule_with_a_when_block_still_needs_for_each(tmp_path: Path):
    """Omitting `when` entirely is the supersede-only case. Writing one
    with no for_each is a different thing and stays an error."""
    path = tmp_path / "bad.yaml"
    path.write_text(
        yaml.safe_dump(
            {"rules": [{"id": "T", "title": "t", "severity": "warning",
                        "source": "s", "rationale": "r", "message": "m",
                        "when": {"where": {}}}]}
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="for_each"):
        load_rules(path, layer="show")


def test_a_rule_with_a_target_still_needs_a_message(tmp_path: Path):
    path = tmp_path / "nomsg.yaml"
    path.write_text(
        yaml.safe_dump(
            {"rules": [{"id": "T", "title": "t", "severity": "warning",
                        "source": "s", "rationale": "r",
                        "when": {"for_each": "channel", "where": {}}}]}
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="message"):
        load_rules(path, layer="show")
```

Add to `tests/test_advisory_evaluator.py`:

```python
def test_the_none_iterator_yields_no_targets(scene):
    assert list(targets_for(scene, "none")) == []
    assert evaluate(scene, rule(for_each="none", where={})) == []
```

- [ ] **Step 2: Run them and verify they fail**

Run: `python -m pytest tests/test_advisory_predicates.py -k supersede_only -v` and `python -m pytest tests/test_advisory_evaluator.py -k none_iterator -v`
Expected: FAIL — `ValueError: … has no when.for_each` on the first, `KeyError: no target iterator named 'none'` on the second.

- [ ] **Step 3: Add the empty iterator**

In `wing_parser/advisory/evaluator.py`, add above `ITERATORS`:

```python
def _nothing(scene) -> Iterator[Target]:
    """No targets at all, for a rule that exists only to supersede another."""
    return iter(())
```

and add `"none": _nothing,` to the `ITERATORS` dict.

- [ ] **Step 4: Accept a supersede-only rule in `load_rules`**

In `wing_parser/advisory/loader.py::_rule_from`, replace the required-field loop and the `when` handling with:

```python
    if not entry.get("id"):
        raise ValueError(f"{where_from}: rule is missing required field 'id'")

    when = entry.get("when")
    supersede_only = when is None

    required = ["title", "severity", "source", "rationale"]
    if not supersede_only:
        required.append("message")
    for field in required:
        if not entry.get(field):
            raise ValueError(
                f"{where_from}: rule {entry['id']} is missing required field {field!r}"
            )

    severity = entry["severity"]
    if severity not in SEVERITIES:
        raise ValueError(
            f"{where_from}: rule {entry['id']} has severity {severity!r}; "
            f"expected one of {SEVERITIES}"
        )

    if supersede_only:
        when = {"for_each": "none", "where": {}}
    if not isinstance(when, dict):
        raise ValueError(
            f"{where_from}: rule {entry['id']} has a when: block that must "
            f"be a mapping, not {type(when).__name__} ({when!r})"
        )
    if not when.get("for_each"):
        raise ValueError(f"{where_from}: rule {entry['id']} has no when.for_each")
```

and change the `message=` argument of the `Rule(...)` call to:

```python
        message=entry.get("message") or entry["title"],
```

- [ ] **Step 5: Use the same empty target in `_as_rules`**

In `wing_parser/advisory/layers.py::_as_rules`, replace

```python
            when = {"for_each": "channel", "where": {"channel.number": -1}}
```

with

```python
            when = {"for_each": "none", "where": {}}
```

and update that function's docstring sentence "a missing `when` becomes a rule that matches nothing" to name the `none` iterator rather than describing a clause that cannot match.

- [ ] **Step 6: Remove the `-1` from the tests that carry it**

Run `grep -rn "channel.number.: -1\|bus.number.: -1" tests/` and update each occurrence: a fixture that used the magic clause to mean "this rule has no target" drops its `when:` block entirely. Do not weaken any assertion — if a test asserted the rule loads and supersedes, it still asserts that.

- [ ] **Step 7: Run the full suite**

Run: `python -m pytest`
Expected: PASS, **380 passed, 1 skipped, 1 warning**. The 17-finding count is unchanged.

- [ ] **Step 8: Commit**

```bash
git add wing_parser/advisory/ tests/
git commit -F - <<'EOF'
Let a supersede-only rule omit when and message

A show rule that exists solely to switch a base rule off has no target.
layers._as_rules already synthesised one for principles; loader.load_rules
raised instead, so the same idea had two fates depending on which file it
was written in -- the two-copies-that-drift shape that produced three
separate bugs in Phase 2.

The synthesised target is now an explicit "none" iterator that yields
nothing, replacing a where clause on channel.number -1 that meant the
same thing by arithmetic accident.
EOF
```

---

### Task 3: Select one profile instead of globbing every show file

**Files:**
- Modify: `wing_parser/advisory/layers.py`
- Modify: `wing_parser/advisory/resolver.py`
- Test: `tests/test_advisory_resolver.py`

**Interfaces:**
- Consumes: `load_rules`, `config.knowledge_dir`
- Produces:
  - `layers._show_rules(directory, profile=None) -> list[Rule]`
  - `resolver.active_rules(scene, directory=None, profile=None)`
  - `resolver.suppressed_ids(scene, directory=None, profile=None)`
  - `resolver.run(scene, directory=None, profile=None)`
  - `AdvisoryFacade.run(profile=None)`, `.rules(profile=None)`, `.suppressed(profile=None)`

**The defect.** `_show_rules` globs every `*.yaml` and `*.yml` under `shows/` and applies all of them. Two show files means both are active permanently — last week's show still overrides tonight's. Nothing caught it because the directory ships empty.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_advisory_resolver.py`:

```python
def _supersede_only(rule_id: str, target: str) -> dict:
    return {"rules": [{"id": rule_id, "title": "t", "severity": "info",
                       "source": "s", "rationale": "r", "supersedes": [target]}]}


def test_no_profile_loads_no_show_file(scene, knowledge):
    (knowledge / "shows" / "small.yaml").write_text(
        yaml.safe_dump(_supersede_only("show.small", "G8")), encoding="utf-8"
    )
    assert {r.id for r in active_rules(scene, directory=knowledge)} == {"G8", "G7", "E6"}


def test_a_profile_loads_only_its_own_file(scene, knowledge):
    """The regression test for the glob defect: with two files present,
    only the named one may take effect."""
    (knowledge / "shows" / "small.yaml").write_text(
        yaml.safe_dump(_supersede_only("show.small", "G8")), encoding="utf-8"
    )
    (knowledge / "shows" / "wedges.yaml").write_text(
        yaml.safe_dump(_supersede_only("show.wedges", "G7")), encoding="utf-8"
    )

    ids = {r.id for r in active_rules(scene, directory=knowledge, profile="small")}
    assert "G8" not in ids
    assert "G7" in ids
    assert "show.small" in ids
    assert "show.wedges" not in ids


def test_a_yml_spelling_is_found_too(scene, knowledge):
    (knowledge / "shows" / "small.yml").write_text(
        yaml.safe_dump(_supersede_only("show.small", "G8")), encoding="utf-8"
    )
    assert "G8" not in {r.id for r in active_rules(scene, directory=knowledge, profile="small")}


def test_an_unknown_profile_raises_and_lists_what_exists(scene, knowledge):
    (knowledge / "shows" / "small.yaml").write_text(
        yaml.safe_dump(_supersede_only("show.small", "G8")), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="smal"):
        active_rules(scene, directory=knowledge, profile="smal")
    with pytest.raises(ValueError, match="small"):
        active_rules(scene, directory=knowledge, profile="smal")


def test_suppressed_ids_honours_the_profile(scene, knowledge):
    (knowledge / "shows" / "small.yaml").write_text(
        yaml.safe_dump(_supersede_only("show.small", "G8")), encoding="utf-8"
    )
    assert suppressed_ids(scene, directory=knowledge) == {}
    assert suppressed_ids(scene, directory=knowledge, profile="small") == {"G8": "show.small"}


def test_run_honours_the_profile(scene, knowledge):
    (knowledge / "shows" / "small.yaml").write_text(
        yaml.safe_dump(_supersede_only("show.small", "G8")), encoding="utf-8"
    )
    assert [f for f in run(scene, directory=knowledge, profile="small")
            if f.rule_id == "G8"] == []
    assert [f for f in run(scene, directory=knowledge) if f.rule_id == "G8"] != []
```

Add `suppressed_ids` to the existing `from wing_parser.advisory.resolver import ...` line in that file.

- [ ] **Step 2: Run them and verify they fail**

Run: `python -m pytest tests/test_advisory_resolver.py -k profile -v`
Expected: FAIL — `TypeError: active_rules() got an unexpected keyword argument 'profile'`.

- [ ] **Step 3: Select one file in `_show_rules`**

In `wing_parser/advisory/layers.py`, replace `_show_rules` entirely:

```python
def _show_rules(directory: Path | None, profile: str | None = None) -> list[Rule]:
    """Load exactly the named show file, or none at all.

    This used to glob every `*.yaml` and `*.yml` under `shows/` and apply
    all of them, which meant two show files were both active for ever --
    last week's overrides still in force tonight, with nothing to say so.
    Nothing caught it because the directory ships empty.

    A profile is selected by name and nothing is loaded without one. An
    unrecognised name raises rather than degrading to "no profile": a
    mistyped `--profile smal` would otherwise run with the base rule still
    active while its author believes it is switched off, which is the
    worst shape this failure can take.
    """
    if profile is None:
        return []

    shows = config.knowledge_dir(directory) / SHOWS_DIR
    for suffix in (".yaml", ".yml"):
        path = shows / f"{profile}{suffix}"
        if path.is_file():
            return load_rules(path, layer="show")

    available = sorted(
        {p.stem for p in list(shows.glob("*.yaml")) + list(shows.glob("*.yml"))}
    ) if shows.is_dir() else []
    raise ValueError(
        f"no profile named {profile!r} in {shows}; "
        f"available: {', '.join(available) if available else '(none)'}"
    )
```

- [ ] **Step 4: Thread the parameter through the resolver**

In `wing_parser/advisory/resolver.py`, change the four signatures and every internal call:

```python
def active_rules(scene, directory: Path | None = None,
                 profile: str | None = None) -> list[Rule]:
    candidates = _principles(directory) + _show_rules(directory, profile)
```

```python
def suppressed_ids(scene, directory: Path | None = None,
                   profile: str | None = None) -> dict[str, str]:
    """Map each switched-off base rule to the higher-layer rule that did it."""
    higher = [r for r in _principles(directory) + _show_rules(directory, profile)
              if _is_active(scene, r)]
    return {rule_id: r.id for r in higher for rule_id in r.supersedes}
```

```python
def run(scene, directory: Path | None = None,
        profile: str | None = None) -> list[Finding]:
    return evaluate_all(scene, active_rules(scene, directory, profile))
```

and in `AdvisoryFacade`:

```python
    def run(self, profile: str | None = None) -> list[Finding]:
        return run(self._scene, self._directory, profile)

    def rules(self, profile: str | None = None) -> list[Rule]:
        return active_rules(self._scene, self._directory, profile)

    def suppressed(self, profile: str | None = None) -> dict[str, str]:
        return suppressed_ids(self._scene, self._directory, profile)
```

`_principles` is unchanged and takes no profile — principles always apply.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest`
Expected: PASS, **387 passed, 1 skipped, 1 warning**. The 17-finding count is unchanged, because `knowledge/toanaz/shows/` is still empty.

- [ ] **Step 6: Prove the glob fix discriminates**

Temporarily restore the old globbing body of `_show_rules` (ignoring `profile` and loading every file), run `python -m pytest tests/test_advisory_resolver.py -k profile_loads_only -v`, and confirm `test_a_profile_loads_only_its_own_file` goes red because `show.wedges` also took effect. Restore and confirm green. Paste both outputs into the report.

- [ ] **Step 7: Commit**

```bash
git add wing_parser/advisory/ tests/test_advisory_resolver.py
git commit -F - <<'EOF'
Select one show profile by name instead of globbing them all

_show_rules applied every file under shows/, so two show files were both
in force permanently and last week's overrides still applied tonight. The
directory ships empty, which is the only reason no test caught it.

A profile is now selected by name, nothing loads without one, and an
unrecognised name raises with the available names listed rather than
degrading to "no profile" -- a mistyped --profile smal would otherwise
leave the base rule firing while its author believes it is off.
EOF
```

---

### Task 4: `--profile` on the CLI and the MCP surface

**Files:**
- Modify: `wing_parser/cli/commands.py`
- Modify: `wing_parser/cli/__main__.py`
- Modify: `wing_parser/mcp/tools.py`
- Test: `tests/test_cli.py`
- Test: `tests/test_mcp.py`

**Interfaces:**
- Consumes: `AdvisoryFacade.run(profile)` from Task 3
- Produces: `--profile NAME` on `wing doctor` and `wing feedback`; `profile` parameter on the MCP `doctor` tool

**Why `feedback` too.** `commands.feedback` resolves a finding by id through `scene.advisory.run()`. If `doctor` and `feedback` see different rule sets, `wing feedback G8:ch.8.send.8` reports "no such finding" immediately after `doctor` printed it.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cli.py`:

```python
def _write_small_profile(directory):
    shows = directory / "shows"
    shows.mkdir(parents=True, exist_ok=True)
    (shows / "small.yaml").write_text(
        yaml.safe_dump(
            {"rules": [{"id": "show.small", "title": "Small show",
                        "severity": "info", "source": "s", "rationale": "r",
                        "supersedes": ["G8"]}]}
        ),
        encoding="utf-8",
    )


def test_doctor_without_a_profile_is_unchanged(vu_path, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    _write_small_profile(tmp_path)
    assert main(["doctor", str(vu_path)]) == 0
    assert "G8" in capsys.readouterr().out


def test_doctor_with_a_profile_suppresses_the_superseded_rule(
    vu_path, tmp_path, capsys, monkeypatch
):
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    _write_small_profile(tmp_path)
    assert main(["doctor", str(vu_path), "--profile", "small"]) == 0
    out = capsys.readouterr().out
    assert "G8" not in out
    assert "G7" in out


def test_an_unknown_profile_exits_cleanly(vu_path, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    _write_small_profile(tmp_path)
    assert main(["doctor", str(vu_path), "--profile", "smal"]) == 1
    err = capsys.readouterr().err
    assert "smal" in err
    assert "small" in err


def test_feedback_sees_the_same_findings_doctor_printed(
    vu_path, tmp_path, capsys, monkeypatch
):
    """An id doctor prints under a profile must resolve under the same
    profile, or the two surfaces have diverged."""
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    _write_small_profile(tmp_path)
    assert main(["doctor", str(vu_path), "--profile", "small", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    target_id = f"{payload[0]['rule_id']}:{payload[0]['target']}"

    assert main(["feedback", target_id, "--verdict", "correct",
                 "--scene", str(vu_path), "--profile", "small"]) == 0


def test_feedback_without_the_profile_cannot_find_a_suppressed_finding(
    vu_path, tmp_path, capsys, monkeypatch
):
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    _write_small_profile(tmp_path)
    assert main(["feedback", "G8:ch.8.send.8", "--verdict", "correct",
                 "--scene", str(vu_path), "--profile", "small"]) == 1
```

Add `import yaml` to that file if it is not already imported.

Add to `tests/test_mcp.py`:

```python
def test_doctor_accepts_a_profile(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    shows = tmp_path / "shows"
    shows.mkdir(parents=True, exist_ok=True)
    (shows / "small.yaml").write_text(
        yaml.safe_dump(
            {"rules": [{"id": "show.small", "title": "Small show",
                        "severity": "info", "source": "s", "rationale": "r",
                        "supersedes": ["G8"]}]}
        ),
        encoding="utf-8",
    )
    assert "G8" not in tools.doctor(str(vu_path), profile="small")
    assert "G8" in tools.doctor(str(vu_path))


def test_doctor_with_an_unknown_profile_returns_a_message(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    out = tools.doctor(str(vu_path), profile="nope")
    assert out.lower().startswith("error")
    assert "nope" in out


def test_the_doctor_tool_still_exposes_its_parameters():
    assert list(inspect.signature(tools.doctor).parameters) == ["path", "profile"]
```

Add `import yaml` to that file if it is not already imported.

- [ ] **Step 2: Run them and verify they fail**

Run: `python -m pytest tests/test_cli.py tests/test_mcp.py -k profile -v`
Expected: FAIL — `error: unrecognized arguments: --profile` from argparse, and `TypeError` on the MCP tool.

- [ ] **Step 3: Pass the profile through the CLI commands**

In `wing_parser/cli/commands.py`, change `_run_advisory` to take the profile:

```python
def _run_advisory(scene: WingScene, profile: str | None = None) -> list | None:
```

and its body's call to `scene.advisory.run(profile)`. Extend its docstring's list of surfaced errors with "an unknown profile name".

In `doctor`, change the call to:

```python
    found = _run_advisory(scene, getattr(args, "profile", None))
```

`feedback` already routes through `_run_advisory` at line 105, so it needs only the same second argument:

```python
    findings = _run_advisory(scene, getattr(args, "profile", None))
```

Also update `doctor`'s suppression line, which currently reads `render.findings(found, scene.advisory.suppressed())`, so the suppression report comes from the same profile the findings did:

```python
        print(render.findings(found, scene.advisory.suppressed(getattr(args, "profile", None))))
```

- [ ] **Step 4: Wire the flag in argparse**

In `wing_parser/cli/__main__.py`, the `doctor` and `feedback` sub-parsers are both bound to the local name `node`. Add one line to each, immediately before its `set_defaults` call:

```python
    node = sub.add_parser("doctor", help="advisory findings only")
    node.add_argument("file")
    node.add_argument("--json", action="store_true", help="machine-readable output")
    node.add_argument(
        "--profile",
        default=None,
        help="apply one show profile from knowledge/toanaz/shows/<name>.yaml",
    )
    node.set_defaults(handler=commands.doctor)
```

```python
    node = sub.add_parser("feedback", help="record a verdict on a finding")
    node.add_argument("finding_id", help="for example G8:ch.8.send.8")
    node.add_argument("--verdict", required=True, choices=VERDICTS)
    node.add_argument("--scene", required=True, help="the .snap the finding came from")
    node.add_argument("--note", default="")
    node.add_argument(
        "--profile",
        default=None,
        help="apply one show profile from knowledge/toanaz/shows/<name>.yaml",
    )
    node.set_defaults(handler=commands.feedback)
```

Do not add it to `analyze`, `channel`, `routing` or `diff` — none of them evaluate rules.

- [ ] **Step 5: Add the parameter to the MCP tool**

In `wing_parser/mcp/tools.py`, change the `doctor` tool to:

```python
@_guard
def doctor(path: str, profile: str | None = None) -> str:
    """Report advisory findings for a WING scene: rules that look violated,
    each with the layer that decided it. Pass `profile` to apply one show
    profile from the knowledge directory, which can switch base rules off
    for a show whose author is deviating from them on purpose. Use this to
    answer "what looks wrong with this scene".
    """
    scene = WingScene.load(path)
    found = scene.advisory.run(profile)
    text = render.findings(found, scene.advisory.suppressed(profile))
    scene.classifier.flush()
    return text
```

Keep the existing docstring's substance if it differs; it must stay over 60 characters and describe when to reach for the tool. Do not change `TOOLS`.

- [ ] **Step 6: Run the full suite**

Run: `python -m pytest`
Expected: PASS, **396 passed, 1 skipped, 1 warning**.

- [ ] **Step 7: Check it by hand**

```bash
WING_DISABLE_LLM=1 python -m wing_parser.cli doctor user-files/example-Vu.snap --profile nope
```
Expected: exit 1, `error: no profile named 'nope' in …; available: (none)`, no traceback. Paste the output into the report.

- [ ] **Step 8: Commit**

```bash
git add wing_parser/cli/ wing_parser/mcp/ tests/test_cli.py tests/test_mcp.py
git commit -F - <<'EOF'
Add --profile to doctor and feedback, and to the MCP doctor tool

feedback resolves a finding by id through the same advisory run doctor
prints, so the flag has to reach both: without it, wing feedback would
report "no such finding" for an id doctor had just listed under a
profile.
EOF
```

---

### Task 5: Narrow G7, and give E6 the clause its rationale states

**Files:**
- Modify: `wing_parser/advisory/base_rules/monitors.yaml`
- Modify: `wing_parser/advisory/base_rules/dynamics.yaml`
- Test: `tests/test_advisory_rules.py`

**Interfaces:**
- Consumes: `any_of` from Task 1

**G7.** Its predicate excludes `[LIM, LIMIT, PRECISION_LIM, BRICK]`. Those tokens appear nowhere — not in either sample `.snap`, not in any descriptor, not in `docs/knowledge-base/`. The only dynamics models in real data are `COMP` and `CMB`, so G7 cannot *not* fire. `bus.dyn.on: false` is verifiable today and is what ships. The model clause returns when a real token is read off a console; the spec's §7.1 records the exact edit.

**E6.** Its rationale states a conjunction — range no more than 6 dB **with** a hold of at least 200 ms — so a violation is `range > 6` **or** `hold < 200`. The shipped predicate tests only the range. Measured: channel 11 `HS4` is the only channel on `example-Vu.snap` that satisfies E6's three `where` conditions at all, and it fails both clauses, so **E6 stays at one finding**. The real file cannot tell the two clauses apart, so the hold clause needs a synthesised test.

- [ ] **Step 1: Write the failing tests**

Replace `test_g7_fires_on_bus_eight` in `tests/test_advisory_rules.py` with:

```python
def test_g7_fires_only_where_the_dynamics_are_bypassed(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    findings = [f for f in scene.advisory.run() if f.rule_id == "G7"]
    # Bus 7 SIDEFILL has dyn.on False; buses 8, 9 and 10 have it True.
    # The model half of G7 is held back until a real limiter token is
    # known, so a bus carrying COMP switched on is no longer reported.
    assert [f.target for f in findings] == ["bus.7"]
    assert findings[0].severity == "error"


def test_g7_states_facts_rather_than_asserting_a_conclusion(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    message = next(f for f in scene.advisory.run() if f.rule_id == "G7").message
    assert "COMP" in message
    assert "not a limiter" not in message


def test_the_sample_scene_reports_fourteen_findings(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    found = scene.advisory.run()
    counts = {rule_id: sum(1 for f in found if f.rule_id == rule_id)
              for rule_id in ("G8", "G7", "E6")}
    assert counts == {"G8": 12, "G7": 1, "E6": 1}
    assert len(found) == 14


def test_e6_still_fires_only_on_the_headset_channel(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    findings = [f for f in scene.advisory.run() if f.rule_id == "E6"]
    assert [f.target for f in findings] == ["ch.11"]


def test_e6_fires_on_a_short_hold_even_when_the_range_is_acceptable(
    vu_path, tmp_path, monkeypatch
):
    """The real file cannot discriminate E6's two clauses -- channel 11 is
    the only channel meeting the preconditions and it fails both -- so the
    hold clause needs a synthesised case."""
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    gate = doc["ae_data"]["ch"]["11"]["gate"]
    gate["range"] = 4      # the raw key is "range"; the view exposes range_dB
    gate["hld"] = 30       # the raw key is "hld"; the view exposes hold_ms
    live = tmp_path / "short_hold.snap"
    live.write_text(json.dumps(doc), encoding="utf-8")

    findings = [f for f in WingScene.load(live).advisory.run() if f.rule_id == "E6"]
    assert [f.target for f in findings] == ["ch.11"]
    assert findings[0].evidence["_any_of"] == 1


def test_e6_message_names_both_range_and_hold(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    message = next(f for f in scene.advisory.run() if f.rule_id == "E6").message
    assert "40.0" in message
    assert "10.0" in message
```

The two raw gate keys were read off the file before this plan was written — `python -c "import json; print(json.load(open('user-files/example-Vu.snap'))['ae_data']['ch']['11']['gate'])"` prints `{'on': True, 'mdl': 'GATE', …, 'range': 40, 'att': 10, 'hld': 10, …}`. They are `range` and `hld`, not `rang` or `hold`.

- [ ] **Step 2: Run them and verify they fail**

Run: `python -m pytest tests/test_advisory_rules.py -v`
Expected: FAIL — G7 reports four targets, the total is 17, and E6's message lacks the hold.

- [ ] **Step 3: Narrow G7**

In `wing_parser/advisory/base_rules/monitors.yaml`, replace G7's `when` block and `message`:

```yaml
    when:
      for_each: bus
      where:
        bus.role: monitor
        bus.dyn.on: false
    message: >
      Bus {bus.number} ({bus.name}) is a monitor bus with its dynamics
      processor bypassed: slot holds {bus.dyn.model}, on = {bus.dyn.on}.
      Nothing is limiting this mix.
```

and append to its `rationale`, inside the existing block:

```
      This rule currently checks only that the dynamics processor is
      switched on. It cannot also check that the loaded model is a
      limiter, because the dyn.mdl token a WING stores for one is not
      recorded anywhere in this repository and must not be guessed; the
      only models observed in real data are COMP and CMB. See the design
      spec section 7.1 for the exact clause to add once that token is
      known.
```

- [ ] **Step 4: Give E6 its `any_of`**

In `wing_parser/advisory/base_rules/dynamics.yaml`, replace E6's `when` block and `message`:

```yaml
    when:
      for_each: channel
      where:
        channel.gate.on: true
        channel.post_insert.on: true
        channel.post_insert.automix_group:
          not: null
      any_of:
        - channel.gate.range_dB: {gt: 6.0}
        - channel.gate.hold_ms: {lt: 200.0}
    message: >
      Channel {channel.number} ({channel.name}) has both an active gate
      (range {channel.gate.range_dB} dB, hold {channel.gate.hold_ms} ms)
      and automix group {channel.post_insert.automix_group}. The gate
      opens late and the automixer reads that as speech onset, ramping
      the first syllable.
```

and append to its `rationale`:

```
      Section 4.4 states the permitted configuration as a conjunction --
      no more than 6 dB of range with a hold of at least 200 ms -- so a
      violation is either condition failing, not only the range. A 4 dB
      range at 30 ms hold still chatters, which is the failure that
      sentence exists to prevent.
```

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest`
Expected: PASS, **400 passed, 1 skipped, 1 warning**. The sample scene now reports **14** findings.

- [ ] **Step 6: Commit**

```bash
git add wing_parser/advisory/base_rules/ tests/test_advisory_rules.py
git commit -F - <<'EOF'
Narrow G7 to what is verifiable, and give E6 its second clause

G7 excluded four limiter model ids that appear nowhere in this
repository -- not in either sample scene, not in any descriptor, not in
the knowledge base -- so it could not not-fire. It now checks only that
the dynamics processor is switched on, which is an observation rather
than an inference, and drops from four findings to one. A monitor bus
carrying COMP switched on is no longer reported; an honest silence beats
severity: error resting on an invented list.

E6's rationale states a conjunction and its predicate tested half of it,
so a 4 dB range at 30 ms hold went unreported. Measured impact on the
sample scene: none, because channel 11 is the only channel meeting the
preconditions and it fails both clauses.
EOF
```

---

### Task 6: Write the first real content into `knowledge/toanaz/`

**Files:**
- Create: `knowledge/toanaz/shows/small.yaml`
- Modify: `knowledge/toanaz/principles.yaml`
- Test: `tests/test_advisory_rules.py`

**Interfaces:**
- Consumes: supersede-only rules from Task 2, profile selection from Tasks 3 and 4

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_advisory_rules.py`:

```python
def test_the_shipped_small_profile_loads_and_suppresses_g8(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    found = scene.advisory.run(profile="small")
    assert [f.rule_id for f in found if f.rule_id == "G8"] == []
    assert {f.rule_id for f in found} == {"G7", "E6"}
    assert len(found) == 2


def test_the_small_profile_records_who_switched_g8_off(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    assert scene.advisory.suppressed(profile="small") == {
        "G8": "show.small.post-monitors-are-deliberate"
    }


def test_the_shipped_principles_file_still_loads(scene, monkeypatch):
    """principles.yaml holds no principles now. It must still parse, and
    it must not quietly stop being read."""
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    assert scene.advisory.rules()
    assert [r for r in scene.advisory.rules() if r.layer == "toanaz"] == []
```

These tests read the **real** in-repo knowledge directory, so each must opt out of the session-scoped `_isolated_knowledge_dir` fixture in `tests/conftest.py` that points every other test at a throwaway directory. The opt-out is one line, the same one `tests/test_classifier_cache.py::test_the_shipped_seed_file_matches_the_module_fallback` uses — take `monkeypatch` as a parameter and start each test with:

```python
    monkeypatch.delenv(config.ENV_VAR, raising=False)
```

with `from wing_parser import config` imported at the top of the file. The `scene` fixture is module-scoped but `config.knowledge_dir()` reads the environment at call time, so deleting the variable inside the test still takes effect.

- [ ] **Step 2: Run them and verify they fail**

Run: `python -m pytest tests/test_advisory_rules.py -k small_profile -v`
Expected: FAIL — `ValueError: no profile named 'small' …`.

- [ ] **Step 3: Write the profile**

Create `knowledge/toanaz/shows/small.yaml`:

```yaml
# Show profiles, selected by name with --profile <name>.
#
# Nothing here applies unless it is named on the command line. A profile
# records a deliberate deviation from a base rule for a kind of show, so
# that the deviation is written down rather than remembered.
rules:
  - id: show.small.post-monitors-are-deliberate
    title: "Small show: post-fader monitor sends are the deliberate shortcut"
    severity: info
    source: "ToanAZ, field practice, 2026-08-16"
    rationale: >
      Pre-fader is the norm, especially on a big show. On a small or easy
      show, post-fader monitor sends trade monitor independence for setup
      speed, deliberately. Base rule G8 states the generic rule correctly;
      this profile records when its author is choosing against it on
      purpose, rather than leaving twelve findings to be re-read and
      re-dismissed every time the scene is checked.
    supersedes: [G8]
```

- [ ] **Step 4: Empty the principles file**

Replace `knowledge/toanaz/principles.yaml` with:

```yaml
# ToanAZ's personal mixing principles.
#
# These override the generic base rules. hardness: hard applies always;
# hardness: flexible applies only when every applies_when condition
# matches. supersedes names the base rules switched off while active.
#
# Empty because no standing principle has been needed yet, not because
# the layer is unused. A deviation that depends on the kind of show
# belongs in shows/ and is selected with --profile; a principle belongs
# here only if it holds regardless of the show.
principles: []
```

The removed entry, `toanaz.iem-shared-band.guitar-prefader`, was a worked example rather than a real principle. Two reasons it goes: its `applies_when: {monitor_bus_count: 1}` can never match a rig with four monitor buses, and its text — "guitar sends pre-fader, all other sources post-fader" — contradicts what ToanAZ has since stated, which is that pre-fader is the norm and post-fader is the small-show shortcut. Leaving it would enshrine a misreading in the file that exists to hold his judgement.

- [ ] **Step 5: Run the full suite**

Run: `python -m pytest`
Expected: PASS, **403 passed, 1 skipped, 1 warning**.

- [ ] **Step 6: Check both paths by hand**

```bash
WING_DISABLE_LLM=1 python -m wing_parser.cli doctor user-files/example-Vu.snap
WING_DISABLE_LLM=1 python -m wing_parser.cli doctor user-files/example-Vu.snap --profile small
```
Expected: 14 findings, then 2. Paste the first line of each into the report.

- [ ] **Step 7: Commit**

```bash
git add knowledge/toanaz/ tests/test_advisory_rules.py
git commit -F - <<'EOF'
Add the small-show profile and empty the principles stub

The first real content in knowledge/toanaz/. A small show declares
--profile small, G8 switches off, and the deviation is written down with
its reasoning instead of being re-dismissed on every run.

principles.yaml held a worked example, not a principle: its condition
could never match a four-monitor-bus rig, and its text said the opposite
of what its author has since stated. An honestly empty layer beats a
sample that cannot fire and would mislead the next reader.
EOF
```

---

## Verification

After Task 6, confirm all of the following and report each:

- `python -m pytest` → **403 passed, 1 skipped, 1 warning**. The skip is the FastMCP build test; the warning is the deliberate one in `test_read_log_skips_a_corrupt_line`.
- `doctor` on `user-files/example-Vu.snap` → 14 findings; with `--profile small` → 2.
- `grep -rn "channel.number.: -1" wing_parser/ tests/` returns nothing.
- `grep -rn "PRECISION_LIM" wing_parser/` returns nothing outside a comment or rationale explaining why the token list was removed.
- The wheel still builds: `python -m pip wheel . --no-deps -w <a temp dir>`.
- Every source file touched is still under ~200 lines.
