# Wing Scene Parser — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Python library that reads Behringer WING `.snap` scene files and answers questions about them, with a rule-based advisory module, delivered as a CLI, an MCP server, and five Claude Skills.

**Architecture:** Five layers, each depending only on the one below. `core/` decodes the file format (the hardware-abstraction analogue — the `.snap` format is the "hardware"). `descriptors/` interprets encoded fields into meaning. `query/` builds view objects over the decoded data. `classifier/` and `advisory/` sit on top of query. `cli/` and `mcp/` are the interface surfaces. Parsing and rule evaluation are strictly deterministic; the only LLM call in the system is an optional classifier fallback at the edge, whose result is cached to YAML.

**Tech Stack:** Python 3.11+ (3.14.6 is installed locally), `PyYAML` (already installed), `anthropic` (optional extra), `mcp` (FastMCP), `pytest` + `pytest-cov`. CLI uses stdlib `argparse` — no click/typer dependency, so the tool stays installable in a minimal offline environment.

**Spec:** `docs/superpowers/specs/2026-08-13-wing-scene-skill-design.md`

---

## Global Constraints

Every task's requirements implicitly include this section.

- **File length ceiling: ~200 lines per source file.** If a module approaches it, split by responsibility — never let a file accumulate. This is a standing rule from the project owner.
- **Split by responsibility layer,** not by technical convenience: format decoding, interpretation, query, rules, interface. Command dispatch is separate from output rendering; MCP tool definitions are separate from handler logic.
- **`core/` may import only the standard library and PyYAML.** It must never import from `descriptors/`, `query/`, `classifier/`, or `advisory/`. The rule is layer discipline, not stdlib purity: PyYAML is a hard dependency of the package, and `core/versions.py` reads the version registry from YAML.
- **Parser and advisory engine are deterministic.** The same `.snap` file must always yield the same findings. No LLM call may appear in `core/`, `query/`, or `advisory/`.
- **The tool must run fully offline.** With no `ANTHROPIC_API_KEY`, no network, or the fallback disabled, everything works; only names the pattern matcher cannot resolve degrade to `unknown`.
- **Never fabricate EQ band values.** An `eq.mdl` with no descriptor yields `bands=None` plus a `descriptor_missing` anomaly. Never apply the `STD` layout to another model.
- **`-144` becomes `float("-inf")` at the data layer**, in `core/normalizer.py`, not at presentation time.
- **Descriptors and advisory rules are YAML data, not Python.** Adding a rule or a descriptor must never require a code change.
- **Files under `knowledge/` are human-editable and machine-written, so they are written with `ruamel.yaml` in round-trip mode, never `yaml.safe_dump`.** PyYAML discards comments at parse time, so any file the tool rewrites would lose ToanAZ's own annotations on the first write. `ruamel.yaml>=0.18` is a hard dependency. Read-only YAML — descriptors, patterns, version registry — stays on PyYAML.
- **Every `Finding` records its deciding layer** (`base` / `toanaz` / `show`).
- **Every advisory rule YAML carries `source:` and `rationale:`.** Where knowledge-base sources disagree, record which value was chosen and why.
- **Do not move or rewrite `docs/knowledge-base/`.**
- **Float comparisons in tests use `pytest.approx`.** Scene files store `-7.899999619`, not `-7.9`.
- **License: MIT.**

### Layer map

| Layer | Package | Analogue | May import |
|---|---|---|---|
| Format decoding | `core/` | HAL | stdlib, `yaml` |
| Interpretation | `descriptors/` | driver | `core`, `yaml` |
| Query | `query/` | backend | `core`, `descriptors` |
| Classification | `classifier/` | backend | `core`, `query`, optionally `anthropic` |
| Rules | `advisory/` | backend | `core`, `query`, `classifier` |
| Interfaces | `cli/`, `mcp/` | API + UI | everything below |

---

## File Structure

```
<repo root>
├── pyproject.toml
├── LICENSE                                 # MIT
├── README.md
├── wing_parser/
│   ├── __init__.py                         # public exports
│   ├── core/
│   │   ├── __init__.py
│   │   ├── versions.py                     # version registry, loaded from versions.yaml
│   │   ├── loader.py                       # read file, detect version
│   │   ├── normalizer.py                   # -144 → -inf, "8" → 8
│   │   ├── validator.py                    # section counts, anomaly collection
│   │   └── models.py                       # frozen data records
│   ├── descriptors/
│   │   ├── __init__.py
│   │   ├── registry.py                     # YAML loading + lookup
│   │   ├── tags.py                         # "#D8,#M1" grammar
│   │   ├── safes.py                        # positional bitmap
│   │   ├── proc_chain.py                   # "GEDI" + ptap + source groups
│   │   ├── eq_models.py                    # per-model band builder
│   │   └── data/
│   │       ├── versions.yaml               # the schema delta
│   │       ├── tap_points.yaml
│   │       ├── proc_chain.yaml
│   │       ├── eq_models.yaml
│   │       ├── tags.yaml
│   │       ├── safes.yaml
│   │       └── io.yaml
│   ├── query/
│   │   ├── __init__.py
│   │   ├── build_blocks.py                 # blocks shared by channels and buses
│   │   ├── build_channel.py                # raw ch entry  → ChannelData
│   │   ├── build_bus.py                    # raw bus entry → BusData
│   │   ├── build_io.py                     # sources, DCAs, mute groups
│   │   ├── scene.py                        # WingScene — the entry point
│   │   ├── channel.py                      # Channel view
│   │   ├── bus.py                          # Bus / Aux / Main / Matrix view
│   │   ├── groups.py                       # DCA / mute-group reverse index
│   │   ├── routing.py
│   │   └── diff.py
│   ├── classifier/
│   │   ├── __init__.py
│   │   ├── normalize.py                    # name cleanup
│   │   ├── matcher.py                      # pattern + confidence
│   │   ├── cache.py                        # YAML read/write
│   │   ├── resolve.py                      # cache → pattern → model
│   │   ├── llm.py                          # optional Claude fallback
│   │   └── data/patterns.yaml
│   ├── advisory/
│   │   ├── __init__.py
│   │   ├── models.py                       # Finding, Rule, severities
│   │   ├── predicates.py                   # path resolution + operators
│   │   ├── loader.py                       # rule YAML → Rule objects
│   │   ├── evaluator.py                    # target iteration + findings
│   │   ├── resolver.py                     # three-layer resolution
│   │   ├── feedback.py                     # JSONL verdict log
│   │   └── base_rules/
│   │       ├── monitors.yaml               # G8, G7
│   │       └── dynamics.yaml               # E6
│   ├── config.py                           # knowledge-dir resolution
│   ├── cli/
│   │   ├── __init__.py
│   │   ├── __main__.py                     # argparse wiring
│   │   ├── commands.py                     # one function per command
│   │   └── render.py                       # output formatting
│   └── mcp/
│       ├── __init__.py
│       ├── server.py                       # FastMCP wiring
│       └── tools.py                        # five tool definitions
├── knowledge/toanaz/
│   ├── principles.yaml
│   ├── classifier.yaml
│   ├── feedback.jsonl
│   └── shows/.gitkeep
├── skills/
│   ├── wing-analyze/SKILL.md
│   ├── wing-channel/SKILL.md
│   ├── wing-diff/SKILL.md
│   ├── wing-routing/SKILL.md
│   └── wing-doctor/SKILL.md
├── tests/
│   ├── conftest.py                         # points at the two real .snap files
│   ├── test_core_versions.py               # Task 1
│   ├── test_core_normalizer.py             # Task 2
│   ├── test_core_validator.py              # Task 3
│   ├── test_descriptors_proc_chain.py      # Task 4
│   ├── test_descriptors_tags.py            # Task 5
│   ├── test_descriptors_safes.py           # Task 6
│   ├── test_descriptors_eq_models.py       # Task 7
│   ├── test_query_build_channel.py         # Task 8
│   ├── test_query_build_io.py              # Task 9
│   ├── test_query_scene.py                 # Task 10
│   ├── test_query_bus.py                   # Task 11
│   ├── test_query_groups.py                # Task 11
│   ├── test_query_routing.py               # Task 12
│   ├── test_query_diff.py                  # Task 13
│   ├── test_classifier_matcher.py          # Task 14
│   ├── test_classifier_cache.py            # Task 15
│   ├── test_classifier_llm.py              # Task 16
│   ├── test_classifier_resolve.py          # Task 17
│   ├── test_advisory_predicates.py         # Task 18
│   ├── test_advisory_evaluator.py          # Task 19
│   ├── test_advisory_rules.py              # Task 20
│   ├── test_advisory_resolver.py           # Task 20
│   ├── test_advisory_feedback.py           # Task 21
│   ├── test_cli.py                         # Task 22
│   ├── test_mcp.py                         # Task 23
│   └── test_examples.py                    # Task 24
└── examples/
    ├── analyze_vu.py
    ├── diff_factory_vs_vu.py
    └── advisory_check.py
```

Real-file fixtures are the already-committed `user-files/factory-scene.snap` and `user-files/example-Vu.snap`; `tests/conftest.py` points at them rather than duplicating 1.2 MB into `tests/`.

There is no `tests/fixtures/synthetic/` directory. Spec section 12 anticipated three hand-written synthetic files; instead every edge case in this plan is built inside the test that needs it, by loading a real file, mutating one field, and writing it to `tmp_path`. A truncated section, a missing DCA block, an unknown `type`, a switched-on automix insert, a flipped polarity — each is one mutation, visible in the test that depends on it. Hand-maintained fixture files would drift from what the tests assume about them.

---

## Milestones

| After task | You have |
|---|---|
| 7 | A working decoder: both files parse, every encoded field is interpreted |
| 13 | A working query library: channels, sources, buses, groups, routing, diff |
| 17 | Classification with confidence, caching, and optional Claude fallback |
| 21 | The advisory engine with three layers, three rules, and the verdict log |
| 24 | CLI, MCP server, Skills — Phase 1 complete |

## Deviations from the spec

Two, both deliberate. Reject either and the affected tasks change.

**`schema/common.yaml` is not built.** Spec section 3.2 describes two schema files: `common.yaml` holding a structural map of where every section and field lives, plus `versions.yaml` holding the delta. This plan builds `versions.yaml` (Task 1) and drops `common.yaml`.

The spec's purpose for splitting them was to avoid duplicating a near-identical schema per firmware version, and `versions.yaml` alone achieves that — it is where a new firmware gets added, in five lines. A full data-driven field map would additionally require the builders to interpret it at construction time, which is a small ORM for one file format with one known layout. The structural knowledge instead lives in `core/validator.py` (section counts) and the three builders (field paths), all of which are short and directly tested.

The cost: adding a *field* that the console starts writing needs a Python edit, not a YAML edit. Adding a *firmware version*, a *descriptor*, or a *rule* still needs no code. If you want field-level extensibility too, add a task before Task 8 that defines `common.yaml` and a generic field-mapper, and rewrite the three builders to consume it.

**`Insert.automix_group` is derived, not stored raw.** The file stores `postins.mode: "AUTO_X"`; the record exposes `automix_group: "X"`. The raw string is not retained. If a future firmware uses `mode` for something other than automix, Task 8's `_insert` needs revisiting.

---

## Reference values from the real files

Every task's tests use these verified values. They come from `user-files/example-Vu.snap` (`snapshot.11`) unless noted.

| Path | Value |
|---|---|
| `type` | `"snapshot.11"` (`factory-scene.snap`: `"snapshot.10"`) |
| `ae_data.cards` keys | `["wlive", "wmadi"]` (factory: `["wlive"]`) |
| section counts | ch 40, aux 8, bus 16, main 4, mtx 8, dca 16, mgrp 8 |
| `ae_data.ch["8"].name` | `"M8 MC"` |
| `ae_data.ch["8"].fdr` | `-7.899999619` |
| `ae_data.ch["8"].proc` | `"GEDI"` |
| `ae_data.ch["8"].ptap` | `"5"` (a string) |
| `ae_data.ch["8"].flt` | `{lc: true, lcf: 151.0619354, lcs: "24", hc: false, ...}` |
| `ae_data.ch["8"].eq` | `{on: true, mdl: "STD", lg: -5.099999905, lf: 169.4942627, 2g: -8.899999619, 2f: 241.1459351, ...}` |
| `ae_data.ch["8"].gate` | `{on: true, mdl: "GATE", thr: -62, range: 12, ...}` |
| `ae_data.ch["8"].postins` | `{on: false, mode: "AUTO_X", ins: "NONE", w: -12}` |
| `ae_data.ch["8"].in.conn` | `{grp: "A", in: 8, altgrp: "OFF", altin: 1}` |
| `ae_data.ch["8"].in.set` | `{inv: false, trim: 7.000000477, dly: 0.1, dlyon: false, ...}` |
| `ae_data.ch["8"].send["8"]` | `{on: true, lvl: -19.89999962, mode: "POST", pon: false, pan: 0}` |
| `ae_data.io.in.A["8"]` | `{g: 5, vph: false, pol: false, mode: "M", name: ""}` |
| `ae_data.ch["13"]` | name `"Kick In "` (trailing space), tags `"#M1"` |
| `ae_data.ch["1"].name` | `"Mic 1 VOX IEM1"` |
| `ae_data.ch["6"].name` | `"M6 D.PHOI"` (Vietnamese: backup) |
| `ae_data.bus["8"]` | name `"MON VOX"`, `dyn: {mdl: "COMP", thr: -15, ratio: 3}` |
| `ae_data.bus["1"].tags` | `"#D1"` |
| `ae_data.aux["1"].tags` | `"#D8,#D9"` (pattern `#D8,#D<n>` across auxes) |
| `ae_data.dca["1"]` | `{name: "MIC", fdr: -3.79999876}` |
| `ae_data.mgrp["1"]` | `{name: "FBAND", mute: true}` |
| `ce_data.safes.ch` | 40 spaces (nothing safe) |
| EQ model counts | 150 × `STD`, 2 × `PULSAR` across both files |

---

## Task 1: Project scaffold and version detection

**Files:**
- Create: `pyproject.toml`
- Create: `LICENSE`
- Create: `wing_parser/__init__.py`
- Create: `wing_parser/core/__init__.py`
- Create: `wing_parser/core/versions.py`
- Create: `wing_parser/core/loader.py`
- Create: `wing_parser/descriptors/__init__.py`
- Create: `wing_parser/descriptors/data/versions.yaml`
- Create: `tests/conftest.py`
- Test: `tests/test_core_versions.py`

**Interfaces:**
- Consumes: nothing
- Produces:
  - `wing_parser.core.versions.SceneVersion` — frozen dataclass with `type_id: str`, `label: str`, `meta_keys: tuple[str, ...]`, `has_globals: bool`, `cards: tuple[str, ...]`, `known: bool`
  - `wing_parser.core.versions.load_registry(path: Path | None = None) -> dict[str, SceneVersion]`
  - `wing_parser.core.versions.resolve(type_id: str, registry: dict[str, SceneVersion]) -> SceneVersion` — returns a `known=False` copy of the newest entry for an unrecognised `type_id`
  - `wing_parser.core.loader.RawScene` — frozen dataclass with `version: SceneVersion`, `ae: dict`, `ce: dict`, `meta: dict`, `path: Path`
  - `wing_parser.core.loader.load_raw(path: str | Path) -> RawScene`

- [ ] **Step 1: Create the package skeleton and packaging metadata**

`pyproject.toml`:

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "wing-parser"
version = "0.1.0"
description = "Read and analyse Behringer WING .snap scene files"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "ToanAZ" }]
dependencies = ["PyYAML>=6.0"]

[project.optional-dependencies]
llm = ["anthropic>=0.40"]
mcp = ["mcp>=1.2,<2"]
dev = ["pytest>=8.0", "pytest-cov>=5.0"]

[project.scripts]
wing = "wing_parser.cli.__main__:main"

[tool.setuptools.packages.find]
include = ["wing_parser*"]

[tool.setuptools.package-data]
wing_parser = ["descriptors/data/*.yaml", "classifier/data/*.yaml", "advisory/base_rules/*.yaml"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-q"
```

`LICENSE` — the standard MIT text, copyright `2026 ToanAZ`.

`wing_parser/__init__.py`:

```python
"""Read and analyse Behringer WING .snap scene files."""

__version__ = "0.1.0"
```

`wing_parser/core/__init__.py` and `wing_parser/descriptors/__init__.py` are empty files.

- [ ] **Step 2: Write the version registry data**

`wing_parser/descriptors/data/versions.yaml`:

```yaml
# Schema deltas between WING snapshot versions.
# The ae_data/ce_data payload is identical across all known versions;
# only the outer envelope differs. Adding a firmware means adding an
# entry here — no Python change.
newest: snapshot.11

versions:
  snapshot.10:
    label: "Wing-Edit 3.2.x"
    meta_keys:
      - creator_fw
      - creator_sn
      - creator_model
      - creator_version
      - creator_name
      - created
    has_globals: true
    cards: [wlive]

  snapshot.11:
    label: "Wing-Edit 3.3.x"
    meta_keys:
      - creator
      - creator_vers
      - creator_model
      - creator_name
    has_globals: false
    cards: [wlive, wmadi]
```

- [ ] **Step 3: Write the failing test**

`tests/conftest.py`:

```python
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
USER_FILES = REPO_ROOT / "user-files"


@pytest.fixture(scope="session")
def factory_path() -> Path:
    return USER_FILES / "factory-scene.snap"


@pytest.fixture(scope="session")
def vu_path() -> Path:
    return USER_FILES / "example-Vu.snap"
```

Fix wave (2026-08-14): the suite was not hermetic. Dropping a show file
into `knowledge/toanaz/shows/` — which the README's own "Add a
show-specific override" section instructs a user to do — turned tests
red, because any test that never passed an explicit `directory=` was
silently reading whatever a user had actually put in the real, in-repo
knowledge directory. Added a session-scoped autouse fixture:

```python
import os
from pathlib import Path

import pytest

from wing_parser import config

REPO_ROOT = Path(__file__).resolve().parents[1]
USER_FILES = REPO_ROOT / "user-files"


@pytest.fixture(scope="session")
def factory_path() -> Path:
    return USER_FILES / "factory-scene.snap"


@pytest.fixture(scope="session")
def vu_path() -> Path:
    return USER_FILES / "example-Vu.snap"


@pytest.fixture(scope="session", autouse=True)
def _isolated_knowledge_dir(tmp_path_factory):
    """Point every test at a throwaway knowledge directory by default.

    Without this, the suite reads `config.knowledge_dir()`'s real default
    -- the in-repo `knowledge/toanaz/`. The README's own "Add a
    show-specific override" section tells a user to drop a `.yaml` file
    into `knowledge/toanaz/shows/`; doing that on a real checkout used to
    turn tests red, because tests that never pass an explicit
    `directory=` were silently reading whatever a user had actually put
    there. `knowledge/toanaz/classifier.yaml` ships with `channels: {}`
    and `buses: {}`, and `principles.yaml`'s one shipped principle is
    `enabled: false`, so an empty tmp directory (nothing on disk at all)
    resolves identically to the shipped default -- this costs no
    coverage. A test that deliberately needs the real in-repo directory
    opts in explicitly with `monkeypatch.delenv(config.ENV_VAR, ...)` or
    by constructing its own `directory=` fixture, the way
    `test_classifier_cache.py` and `test_advisory_resolver.py` already
    do.

    A plain `monkeypatch` fixture is function-scoped and cannot be
    requested from a session-scoped fixture, so the environment variable
    is set and restored by hand instead.
    """
    directory = tmp_path_factory.mktemp("knowledge")
    previous = os.environ.get(config.ENV_VAR)
    os.environ[config.ENV_VAR] = str(directory)
    yield directory
    if previous is None:
        os.environ.pop(config.ENV_VAR, None)
    else:
        os.environ[config.ENV_VAR] = previous
```

`test_classifier_cache.py::test_the_shipped_seed_file_matches_the_
module_fallback` deliberately reads the real in-repo directory, so it
was updated to `monkeypatch.delenv(config.ENV_VAR, raising=False)`
rather than relying on the env var being unset by default. Verified by
dropping a throwaway show file into the real `knowledge/toanaz/shows/`
directory and confirming the full suite still passes (355 tests at the
time of that check) before removing it.

`tests/test_core_versions.py`:

```python
import pytest

from wing_parser.core.loader import load_raw
from wing_parser.core.versions import load_registry, resolve


def test_registry_has_both_known_versions():
    registry = load_registry()
    assert set(registry) == {"snapshot.10", "snapshot.11"}
    assert registry["snapshot.10"].label == "Wing-Edit 3.2.x"
    assert registry["snapshot.10"].has_globals is True
    assert registry["snapshot.11"].has_globals is False
    assert registry["snapshot.11"].cards == ("wlive", "wmadi")


def test_unknown_version_falls_back_to_newest_and_is_marked_unknown():
    registry = load_registry()
    resolved = resolve("snapshot.99", registry)
    assert resolved.type_id == "snapshot.99"
    assert resolved.known is False
    assert resolved.cards == registry["snapshot.11"].cards


def test_loads_factory_as_snapshot_10(factory_path):
    raw = load_raw(factory_path)
    assert raw.version.type_id == "snapshot.10"
    assert raw.version.known is True
    assert set(raw.ae) >= {"cfg", "io", "ch", "aux", "bus", "main", "mtx", "dca", "mgrp"}
    assert list(raw.ae["cards"]) == ["wlive"]


def test_loads_vu_as_snapshot_11(vu_path):
    raw = load_raw(vu_path)
    assert raw.version.type_id == "snapshot.11"
    assert raw.version.known is True
    assert list(raw.ae["cards"]) == ["wlive", "wmadi"]
    assert raw.meta["creator_model"]


def test_missing_type_field_is_an_error(tmp_path):
    bad = tmp_path / "bad.snap"
    bad.write_text('{"ae_data": {}, "ce_data": {}}', encoding="utf-8")
    with pytest.raises(ValueError, match="type"):
        load_raw(bad)


def test_top_level_array_is_an_error(tmp_path):
    bad = tmp_path / "bad.snap"
    bad.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ValueError, match="list"):
        load_raw(bad)
```

- [ ] **Step 4: Run the test and verify it fails**

Run: `python -m pytest tests/test_core_versions.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.core.loader'`

- [ ] **Step 5: Implement the version registry**

`wing_parser/core/versions.py`:

```python
"""Version registry for WING snapshot schemas.

The ae_data/ce_data payload is identical across all observed versions;
only the outer envelope differs. This module owns that delta.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

import yaml

_DATA = Path(__file__).resolve().parent.parent / "descriptors" / "data" / "versions.yaml"


@dataclass(frozen=True)
class SceneVersion:
    type_id: str
    label: str
    meta_keys: tuple[str, ...]
    has_globals: bool
    cards: tuple[str, ...]
    known: bool = True


def load_registry(path: Path | None = None) -> dict[str, SceneVersion]:
    doc = yaml.safe_load((path or _DATA).read_text(encoding="utf-8"))
    return {
        type_id: SceneVersion(
            type_id=type_id,
            label=entry["label"],
            meta_keys=tuple(entry["meta_keys"]),
            has_globals=bool(entry["has_globals"]),
            cards=tuple(entry["cards"]),
        )
        for type_id, entry in doc["versions"].items()
    }


def newest_id(path: Path | None = None) -> str:
    doc = yaml.safe_load((path or _DATA).read_text(encoding="utf-8"))
    return doc["newest"]


def resolve(type_id: str, registry: dict[str, SceneVersion]) -> SceneVersion:
    """Return the version entry for type_id.

    An unrecognised type_id yields the newest known schema with known=False,
    so the caller can warn and still attempt a parse rather than refusing
    the file outright.
    """
    if type_id in registry:
        return registry[type_id]
    fallback = registry[newest_id()]
    return replace(fallback, type_id=type_id, known=False)
```

- [ ] **Step 6: Implement the loader**

`wing_parser/core/loader.py`:

```python
"""Read a .snap file and split it into payload and envelope."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wing_parser.core.versions import SceneVersion, load_registry, resolve


@dataclass(frozen=True)
class RawScene:
    version: SceneVersion
    ae: dict[str, Any]
    ce: dict[str, Any]
    meta: dict[str, Any]
    path: Path


def load_raw(path: str | Path) -> RawScene:
    file_path = Path(path)
    doc = json.loads(file_path.read_text(encoding="utf-8"))

    if not isinstance(doc, dict):
        raise ValueError(
            f"{file_path}: expected a JSON object at the top level, "
            f"found {type(doc).__name__}; not a WING snapshot"
        )

    type_id = doc.get("type")
    if not type_id:
        raise ValueError(f"{file_path}: missing top-level 'type' field; not a WING snapshot")

    version = resolve(type_id, load_registry())
    meta = {k: v for k, v in doc.items() if k not in {"ae_data", "ce_data"}}

    return RawScene(
        version=version,
        # `or {}` rather than a .get default: a corrupt file can carry
        # "ae_data": null, where the key is present and the default never
        # fires. Downstream code must never receive None here.
        ae=doc.get("ae_data") or {},
        ce=doc.get("ce_data") or {},
        meta=meta,
        path=file_path,
    )
```

- [ ] **Step 7: Run the test and verify it passes**

Run: `python -m pytest tests/test_core_versions.py -v`
Expected: PASS — 6 tests

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml LICENSE wing_parser/ tests/conftest.py tests/test_core_versions.py
git commit -m "Add package scaffold and .snap version detection

Version deltas live in descriptors/data/versions.yaml. An unrecognised
type_id resolves to the newest known schema with known=False so the
parser warns and still tries, rather than refusing a file the day new
firmware ships."
```

---

## Task 2: Normalizer

**Files:**
- Create: `wing_parser/core/normalizer.py`
- Test: `tests/test_core_normalizer.py`

**Interfaces:**
- Consumes: nothing from earlier tasks
- Produces:
  - `wing_parser.core.normalizer.NEG_INF: float` — `float("-inf")`
  - `wing_parser.core.normalizer.SENTINEL_MINUS_INF: int` — `-144`
  - `wing_parser.core.normalizer.to_db(value: float | int | None) -> float` — maps `-144` to `-inf`, passes everything else through as `float`
  - `wing_parser.core.normalizer.from_db(value: float) -> float` — the inverse, for writing values back out
  - `wing_parser.core.normalizer.int_keyed(section: dict[str, Any]) -> dict[int, Any]` — `{"1": {...}}` → `{1: {...}}`, sorted ascending
  - `wing_parser.core.normalizer.is_silent(db: float) -> bool`

- [ ] **Step 1: Write the failing test**

`tests/test_core_normalizer.py`:

```python
import math

import pytest

from wing_parser.core.normalizer import (
    NEG_INF,
    from_db,
    int_keyed,
    is_silent,
    to_db,
)


def test_sentinel_becomes_negative_infinity():
    assert to_db(-144) == NEG_INF
    assert to_db(-144.0) == NEG_INF
    assert math.isinf(to_db(-144))


def test_real_levels_pass_through_as_floats():
    assert to_db(-7.899999619) == pytest.approx(-7.9, abs=1e-6)
    assert to_db(0) == 0.0
    assert isinstance(to_db(0), float)


def test_values_below_the_sentinel_are_still_silent_not_passed_through():
    # The console never writes below -144, but a corrupt file might.
    assert to_db(-200) == NEG_INF


def test_none_is_silent():
    assert to_db(None) == NEG_INF


def test_from_db_round_trips():
    assert from_db(NEG_INF) == -144.0
    assert from_db(-7.9) == pytest.approx(-7.9)


def test_int_keyed_converts_and_sorts():
    section = {"10": "j", "2": "b", "1": "a"}
    assert list(int_keyed(section).items()) == [(1, "a"), (2, "b"), (10, "j")]


def test_int_keyed_rejects_non_numeric_keys():
    with pytest.raises(ValueError, match="non-numeric"):
        int_keyed({"1": "a", "oops": "b"})


def test_is_silent():
    assert is_silent(NEG_INF) is True
    assert is_silent(-7.9) is False
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m pytest tests/test_core_normalizer.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.core.normalizer'`

- [ ] **Step 3: Implement the normalizer**

`wing_parser/core/normalizer.py`:

```python
"""Turn raw .snap encodings into ordinary Python values.

Two conversions live here and nowhere else:

  * the -144 sentinel, which the console writes for -inf dB
  * string numeric section keys ("1".."40"), which become ints

Doing this at the data layer means no consumer ever has to remember
that -144 is special.
"""

from __future__ import annotations

from typing import Any

NEG_INF: float = float("-inf")
SENTINEL_MINUS_INF: int = -144


def to_db(value: float | int | None) -> float:
    """Convert a raw level field to dB, mapping the sentinel to -inf."""
    if value is None:
        return NEG_INF
    numeric = float(value)
    if numeric <= SENTINEL_MINUS_INF:
        return NEG_INF
    return numeric


def from_db(value: float) -> float:
    """Inverse of to_db, for writing a level back into .snap form."""
    if value == NEG_INF:
        return float(SENTINEL_MINUS_INF)
    return float(value)


def is_silent(db: float) -> bool:
    return db == NEG_INF


def int_keyed(section: dict[str, Any]) -> dict[int, Any]:
    """Convert a string-keyed section to int keys, ascending."""
    converted: dict[int, Any] = {}
    for key, value in section.items():
        try:
            converted[int(key)] = value
        except (TypeError, ValueError) as exc:
            raise ValueError(f"section has a non-numeric key: {key!r}") from exc
    return dict(sorted(converted.items()))
```

- [ ] **Step 4: Run the test and verify it passes**

Run: `python -m pytest tests/test_core_normalizer.py -v`
Expected: PASS — 8 tests

- [ ] **Step 5: Commit**

```bash
git add wing_parser/core/normalizer.py tests/test_core_normalizer.py
git commit -m "Add level and key normalization

-144 becomes float('-inf') here, at the data layer, so no consumer has
to know the sentinel exists. Section keys become ints at the same point."
```

---

## Task 3: Core data models and validator

**Files:**
- Create: `wing_parser/core/models.py`
- Create: `wing_parser/core/validator.py`
- Test: `tests/test_core_validator.py`

**Interfaces:**
- Consumes: `SceneVersion` (Task 1), `to_db` / `int_keyed` (Task 2)
- Produces:
  - `wing_parser.core.models.Anomaly` — frozen dataclass `code: str`, `where: str`, `detail: str`
  - `wing_parser.core.models.OFF_GROUP: str = "OFF"` — module-level constant, not a class attribute
  - `wing_parser.core.models.SourceRef` — frozen dataclass `group: str`, `index: int`, plus the derived property `is_off` (compares `group` against `OFF_GROUP`)
  - `wing_parser.core.models.SourceData` — `group`, `index`, `name`, `gain_dB`, `phantom`, `polarity`, `mode`
  - `wing_parser.core.models.Send` — `dest: int`, `on: bool`, `level_dB: float`, `mode: str`, `pre_on: bool`, `pan: float`
  - `wing_parser.core.models.MainSend` — `dest: int`, `on: bool`, `level_dB: float`, `pre: bool`
  - `wing_parser.core.models.Filter`, `Gate`, `Dyn`, `Insert`, `Eq`, `EqBand` (fields listed in the code below)
  - `wing_parser.core.models.ChannelData`, `BusData`, `DcaData`, `MuteGroupData`
  - `wing_parser.core.validator.EXPECTED_COUNTS: dict[str, int]`
  - `wing_parser.core.validator.check_counts(ae: dict) -> list[Anomaly]`
  - `wing_parser.core.validator.check_required_keys(ae: dict, ce: dict) -> list[Anomaly]`
  - `wing_parser.core.validator.validate(raw) -> list[Anomaly]` — takes a `RawScene`, returns every anomaly found; never raises

- [ ] **Step 1: Write the data records**

`wing_parser/core/models.py`:

```python
"""Frozen data records for a decoded scene.

These are plain values with no back-references. Cross-object navigation
(channel -> source, DCA -> members) lives in the query layer, so this
module stays free of construction-order problems.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

OFF_GROUP = "OFF"


@dataclass(frozen=True)
class Anomaly:
    code: str
    where: str
    detail: str


@dataclass(frozen=True)
class SourceRef:
    group: str
    index: int

    @property
    def is_off(self) -> bool:
        return self.group == OFF_GROUP


@dataclass(frozen=True)
class SourceData:
    group: str
    index: int
    name: str
    gain_dB: float
    phantom: bool
    polarity: bool
    mode: str


@dataclass(frozen=True)
class EqBand:
    name: str
    freq: float
    gain: float
    q: float
    shape: str | None = None


@dataclass(frozen=True)
class Eq:
    on: bool
    model: str
    bands: tuple[EqBand, ...] | None
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Filter:
    low_cut_on: bool
    low_cut_hz: float
    low_cut_slope: int
    high_cut_on: bool
    high_cut_hz: float
    high_cut_slope: int


@dataclass(frozen=True)
class Gate:
    on: bool
    model: str
    threshold_dB: float
    range_dB: float
    attack_ms: float
    hold_ms: float
    release_ms: float


@dataclass(frozen=True)
class Dyn:
    on: bool
    model: str
    threshold_dB: float
    ratio: float
    attack_ms: float
    release_ms: float


@dataclass(frozen=True)
class Insert:
    on: bool
    slot: str
    automix_group: str | None
    automix_weight: float | None


@dataclass(frozen=True)
class Send:
    """One send from a channel, aux, bus, main or matrix.

    A send block mixes two destination families under one dict: numeric
    keys ("1".."16") address buses, and "MX1".."MX8" address matrices.
    Bus 3 and MX3 are different destinations, so the number alone cannot
    identify one — dest_kind is what keeps them apart.
    """

    dest_kind: str        # "bus" | "matrix"
    dest: int
    on: bool
    level_dB: float
    mode: str
    pre_on: bool
    pan: float


@dataclass(frozen=True)
class MainSend:
    dest: int
    on: bool
    level_dB: float
    pre: bool


@dataclass(frozen=True)
class ChannelData:
    number: int
    name: str
    icon: int
    color: int
    muted: bool
    fader_dB: float
    pan: float
    width: float
    solo_safe: bool
    proc_raw: str
    proc_chain: tuple[str, ...]
    tap_point: str
    tags_raw: str
    trim_dB: float
    polarity_invert: bool
    delay_ms: float
    delay_on: bool
    source_ref: SourceRef
    alt_source_ref: SourceRef
    filter: Filter
    eq: Eq
    gate: Gate
    dyn: Dyn
    pre_insert: Insert
    post_insert: Insert
    sends: tuple[Send, ...]
    main_sends: tuple[MainSend, ...]


@dataclass(frozen=True)
class BusData:
    number: int
    kind: str            # "bus" | "main" | "matrix" | "aux"
    name: str
    color: int
    muted: bool
    fader_dB: float
    tags_raw: str
    eq: Eq
    dyn: Dyn
    delay_ms: float
    sends: tuple[Send, ...]
    main_sends: tuple[MainSend, ...]


@dataclass(frozen=True)
class DcaData:
    number: int
    name: str
    muted: bool
    fader_dB: float


@dataclass(frozen=True)
class MuteGroupData:
    number: int
    name: str
    muted: bool
```

- [ ] **Step 2: Write the failing test**

`tests/test_core_validator.py`:

```python
import json

import pytest

from wing_parser.core.loader import load_raw
from wing_parser.core.validator import EXPECTED_COUNTS, validate


def test_real_files_produce_no_anomalies(factory_path, vu_path):
    assert validate(load_raw(factory_path)) == []
    assert validate(load_raw(vu_path)) == []


def test_expected_counts_match_the_console():
    assert EXPECTED_COUNTS == {
        "ch": 40, "aux": 8, "bus": 16, "main": 4,
        "mtx": 8, "dca": 16, "mgrp": 8,
    }


def test_short_section_is_reported_not_raised(vu_path, tmp_path):
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"].pop("40")
    truncated = tmp_path / "short.snap"
    truncated.write_text(json.dumps(doc), encoding="utf-8")

    anomalies = validate(load_raw(truncated))
    codes = {a.code for a in anomalies}
    assert "count_mismatch" in codes
    assert any("ch" in a.where for a in anomalies)


def test_missing_section_is_reported(vu_path, tmp_path):
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    del doc["ae_data"]["dca"]
    stripped = tmp_path / "nodca.snap"
    stripped.write_text(json.dumps(doc), encoding="utf-8")

    anomalies = validate(load_raw(stripped))
    assert any(a.code == "missing_section" and a.where == "ae_data.dca" for a in anomalies)


def test_unknown_version_is_reported_as_an_anomaly(vu_path, tmp_path):
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["type"] = "snapshot.99"
    future = tmp_path / "future.snap"
    future.write_text(json.dumps(doc), encoding="utf-8")

    anomalies = validate(load_raw(future))
    assert any(a.code == "unknown_version" for a in anomalies)


def test_null_payload_is_reported_not_raised(vu_path, tmp_path):
    # "ae_data": null is valid JSON, so .get(key, default) never fires its
    # default. The validator must survive it — collecting anomalies is its
    # whole job, and an exception here would destroy the parse.
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"] = None
    nulled = tmp_path / "nullae.snap"
    nulled.write_text(json.dumps(doc), encoding="utf-8")

    anomalies = validate(load_raw(nulled))
    assert any(a.code == "missing_section" and a.where == "ae_data.ch" for a in anomalies)


def test_non_collection_section_is_reported_not_raised(vu_path, tmp_path):
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"] = 42
    corrupt = tmp_path / "intch.snap"
    corrupt.write_text(json.dumps(doc), encoding="utf-8")

    anomalies = validate(load_raw(corrupt))
    assert any(
        a.code == "malformed_section" and a.where == "ae_data.ch" for a in anomalies
    )
```

- [ ] **Step 3: Run the test and verify it fails**

Run: `python -m pytest tests/test_core_validator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.core.validator'`

- [ ] **Step 4: Implement the validator**

`wing_parser/core/validator.py`:

```python
"""Structural checks over a raw scene.

Collects anomalies rather than raising, so a partially malformed file
still yields useful output. Nothing here interprets a value; that is the
descriptors layer's job.
"""

from __future__ import annotations

from wing_parser.core.loader import RawScene
from wing_parser.core.models import Anomaly

EXPECTED_COUNTS: dict[str, int] = {
    "ch": 40,
    "aux": 8,
    "bus": 16,
    "main": 4,
    "mtx": 8,
    "dca": 16,
    "mgrp": 8,
}

REQUIRED_AE = ("cfg", "io", "ch", "aux", "bus", "main", "mtx", "dca", "mgrp")
REQUIRED_CE = ("cfg", "safes")


def check_counts(ae: dict) -> list[Anomaly]:
    found: list[Anomaly] = []
    if not isinstance(ae, dict):
        return found                      # already reported by check_required_keys
    for section, expected in EXPECTED_COUNTS.items():
        if section not in ae:
            continue
        value = ae[section]
        if not isinstance(value, (dict, list)):
            found.append(
                Anomaly(
                    code="malformed_section",
                    where=f"ae_data.{section}",
                    detail=f"expected a collection, found {type(value).__name__}",
                )
            )
            continue
        actual = len(value)
        if actual != expected:
            found.append(
                Anomaly(
                    code="count_mismatch",
                    where=f"ae_data.{section}",
                    detail=f"expected {expected} entries, found {actual}",
                )
            )
    return found


def _check_block(block: object, label: str, required: tuple[str, ...]) -> list[Anomaly]:
    if not isinstance(block, dict):
        return [
            Anomaly(
                code="malformed_section",
                where=label,
                detail=f"expected an object, found {type(block).__name__}",
            )
        ]
    return [
        Anomaly("missing_section", f"{label}.{section}", "section absent")
        for section in required
        if section not in block
    ]


def check_required_keys(ae: dict, ce: dict) -> list[Anomaly]:
    return _check_block(ae, "ae_data", REQUIRED_AE) + _check_block(
        ce, "ce_data", REQUIRED_CE
    )


def validate(raw: RawScene) -> list[Anomaly]:
    found: list[Anomaly] = []
    if not raw.version.known:
        found.append(
            Anomaly(
                code="unknown_version",
                where="type",
                detail=(
                    f"{raw.version.type_id} is not a known schema; "
                    f"parsing with {raw.version.label} layout — results unverified"
                ),
            )
        )
    found.extend(check_required_keys(raw.ae, raw.ce))
    found.extend(check_counts(raw.ae))
    return found
```

- [ ] **Step 5: Run the test and verify it passes**

Run: `python -m pytest tests/test_core_validator.py -v`
Expected: PASS — 5 tests

- [ ] **Step 6: Commit**

```bash
git add wing_parser/core/models.py wing_parser/core/validator.py tests/test_core_validator.py
git commit -m "Add core data records and structural validator

Records are plain frozen values with no back-references; cross-object
navigation belongs to the query layer. The validator collects anomalies
instead of raising, so a partly malformed file still yields output."
```

---

## Task 4: Descriptor registry, tap points, and proc chain

**Files:**
- Create: `wing_parser/descriptors/registry.py`
- Create: `wing_parser/descriptors/proc_chain.py`
- Create: `wing_parser/descriptors/data/tap_points.yaml`
- Create: `wing_parser/descriptors/data/proc_chain.yaml`
- Create: `wing_parser/descriptors/data/io.yaml`
- Test: `tests/test_descriptors_proc_chain.py`

**Interfaces:**
- Consumes: nothing from earlier tasks
- Produces:
  - `wing_parser.descriptors.registry.load(name: str) -> dict` — loads `descriptors/data/<name>.yaml`, cached with `functools.lru_cache`
  - `wing_parser.descriptors.registry.DATA_DIR: Path`
  - `wing_parser.descriptors.proc_chain.decode(proc: str) -> tuple[str, ...]` — `"GEDI"` → `("GATE", "EQ", "DELAY", "INSERT")`
  - `wing_parser.descriptors.proc_chain.tap_point(ptap: str | int) -> str` — `"5"` → `"POST_FDR"`
  - `wing_parser.descriptors.proc_chain.source_group_label(group: str) -> str` — `"A"` → `"AES50-A"`

- [ ] **Step 1: Write the descriptor data**

`wing_parser/descriptors/data/tap_points.yaml`:

```yaml
# ch.ptap selects where TAP-mode sends draw their signal.
# Values are stored as strings in the file, e.g. "5".
# Source: WING_Series_Manual_Knowledge_Base.md section 5.1
points:
  "1": { id: INPUT,     label: "Input",           note: "immediately after the preamp" }
  "2": { id: FILTER,    label: "Post filter",     note: "after low-cut / high-cut" }
  "3": { id: TAP3,      label: "Tap 3",           note: "inter-processing slot" }
  "4": { id: PRE_FDR,   label: "Pre-fader",       note: "post processing, pre-fader" }
  "5": { id: POST_FDR,  label: "Post-fader",      note: "post fader, pre-INS2" }
  "6": { id: POST_PROC, label: "Post processing", note: "post INS2, pre-width" }
unknown: UNKNOWN_TAP
```

`wing_parser/descriptors/data/proc_chain.yaml`:

```yaml
# ch.proc is an encoded string listing active processing blocks in order,
# e.g. "GEDI". Each character maps to one block.
# Source: bitfocus/companion-module-behringer-wing field survey, confirmed
# against WING_Series_Manual_Knowledge_Base.md section 5.
blocks:
  G: { id: GATE,   label: "Gate" }
  E: { id: EQ,     label: "Equaliser" }
  D: { id: DELAY,  label: "Delay" }
  I: { id: INSERT, label: "Insert" }
  C: { id: COMP,   label: "Compressor" }
  F: { id: FILTER, label: "Filter" }
unknown_prefix: UNKNOWN_
```

`wing_parser/descriptors/data/io.yaml`:

```yaml
# Source groups addressable by ch.in.conn.grp.
# Source: WING_Series_Manual_Knowledge_Base.md section 1.1
groups:
  LCL:  { label: "Local In",        channels: 24 }
  AUX:  { label: "Aux In",          channels: 8 }
  A:    { label: "AES50-A",         channels: 48 }
  B:    { label: "AES50-B",         channels: 48 }
  C:    { label: "AES50-C",         channels: 48 }
  SC:   { label: "StageConnect",    channels: 32 }
  USB:  { label: "USB Audio",       channels: 48 }
  CRD:  { label: "Expansion Card",  channels: 64 }
  MOD:  { label: "Internal Module", channels: 64 }
  PLAY: { label: "USB Player",      channels: 4 }
  AES:  { label: "AES/EBU",         channels: 2 }
  USR:  { label: "User Signal",     channels: 24 }
  OSC:  { label: "Oscillator",      channels: 2 }
  # Quoted deliberately: YAML 1.1 parses a bareword OFF as boolean false,
  # which would make the "OFF" lookup miss and return the raw group name.
  "OFF": { label: "Not patched",    channels: 0 }
```

- [ ] **Step 2: Write the failing test**

`tests/test_descriptors_proc_chain.py`:

```python
from wing_parser.core.loader import load_raw
from wing_parser.descriptors import registry
from wing_parser.descriptors.proc_chain import (
    decode,
    source_group_label,
    tap_point,
)


def test_decodes_the_gedi_chain():
    assert decode("GEDI") == ("GATE", "EQ", "DELAY", "INSERT")


def test_decode_preserves_order():
    assert decode("EGID") == ("EQ", "GATE", "INSERT", "DELAY")


def test_empty_chain_is_empty_tuple():
    assert decode("") == ()


def test_unknown_letter_is_flagged_not_dropped():
    assert decode("GZ") == ("GATE", "UNKNOWN_Z")


def test_tap_point_accepts_the_string_form_the_file_uses():
    assert tap_point("5") == "POST_FDR"
    assert tap_point(5) == "POST_FDR"
    assert tap_point("1") == "INPUT"


def test_unknown_tap_point_is_named_not_crashed():
    assert tap_point("99") == "UNKNOWN_TAP"


def test_source_group_label():
    assert source_group_label("A") == "AES50-A"
    assert source_group_label("OFF") == "Not patched"
    assert source_group_label("ZZ") == "ZZ"


def test_registry_caches():
    assert registry.load("proc_chain") is registry.load("proc_chain")


def test_every_channel_in_the_real_file_decodes(vu_path):
    raw = load_raw(vu_path)
    for entry in raw.ae["ch"].values():
        chain = decode(entry["proc"])
        assert all(not block.startswith("UNKNOWN_") for block in chain), entry["proc"]
        assert tap_point(entry["ptap"]) != "UNKNOWN_TAP"
```

- [ ] **Step 3: Run the test and verify it fails**

Run: `python -m pytest tests/test_descriptors_proc_chain.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.descriptors.registry'`

- [ ] **Step 4: Implement the registry**

`wing_parser/descriptors/registry.py`:

```python
"""Load descriptor YAML files.

Descriptors say what a value means. Schema says where a value is and
whether it is well formed. Keeping them apart is what lets a user add a
new EQ model or tap point without touching Python.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

DATA_DIR = Path(__file__).resolve().parent / "data"


@lru_cache(maxsize=None)
def load(name: str) -> dict[str, Any]:
    path = DATA_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"no descriptor named {name!r} in {DATA_DIR}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))
```

- [ ] **Step 5: Implement the proc-chain and tap-point decoders**

`wing_parser/descriptors/proc_chain.py`:

```python
"""Decode the encoded processing-chain string, tap point, and source group."""

from __future__ import annotations

from wing_parser.descriptors import registry


def decode(proc: str) -> tuple[str, ...]:
    """Turn 'GEDI' into ('GATE', 'EQ', 'DELAY', 'INSERT').

    Order is significant: it is the order the blocks run in. An
    unrecognised letter becomes UNKNOWN_<letter> rather than being
    silently dropped, so a new firmware block shows up in output.
    """
    doc = registry.load("proc_chain")
    blocks = doc["blocks"]
    prefix = doc["unknown_prefix"]
    return tuple(
        blocks[letter]["id"] if letter in blocks else f"{prefix}{letter}"
        for letter in (proc or "")
    )


def tap_point(ptap: str | int) -> str:
    """Map ch.ptap to a named tap point. The file stores this as a string."""
    doc = registry.load("tap_points")
    entry = doc["points"].get(str(ptap))
    return entry["id"] if entry else doc["unknown"]


def source_group_label(group: str) -> str:
    entry = registry.load("io")["groups"].get(group)
    return entry["label"] if entry else group
```

- [ ] **Step 6: Run the test and verify it passes**

Run: `python -m pytest tests/test_descriptors_proc_chain.py -v`
Expected: PASS — 9 tests. The last one proves all 40 real channels decode cleanly.

- [ ] **Step 7: Commit**

```bash
git add wing_parser/descriptors/ tests/test_descriptors_proc_chain.py
git commit -m "Add descriptor registry, proc-chain and tap-point decoders

ch.proc is an encoded block list and ch.ptap is a string-typed enum;
both now decode from YAML rather than hardcoded maps. Unknown values
surface as UNKNOWN_* instead of being dropped."
```

---

## Task 5: Tags grammar

**Files:**
- Create: `wing_parser/descriptors/tags.py`
- Create: `wing_parser/descriptors/data/tags.yaml`
- Test: `tests/test_descriptors_tags.py`

**Interfaces:**
- Consumes: `registry.load` (Task 4)
- Produces:
  - `wing_parser.descriptors.tags.Membership` — frozen dataclass `dcas: tuple[int, ...]`, `mute_groups: tuple[int, ...]`, `unknown: tuple[str, ...]`
  - `wing_parser.descriptors.tags.parse(tags_raw: str) -> Membership`

- [ ] **Step 1: Write the descriptor data**

`wing_parser/descriptors/data/tags.yaml`:

```yaml
# The `tags` field on channels, auxes, buses, mains and matrices encodes
# group membership. Membership is stored on the member, not on the group,
# so a reverse index has to be built to answer "who is in DCA 1".
#
# Grammar: zero or more tokens separated by ",". Each token is a prefix
# plus a 1-based integer, e.g. "#D8,#D10" or "#M1".
separator: ","
prefixes:
  "#D": { kind: dca,        max: 16 }
  "#M": { kind: mute_group, max: 8 }
```

- [ ] **Step 2: Write the failing test**

`tests/test_descriptors_tags.py`:

```python
from wing_parser.core.loader import load_raw
from wing_parser.descriptors.tags import parse


def test_empty_string_yields_no_membership():
    m = parse("")
    assert m.dcas == ()
    assert m.mute_groups == ()
    assert m.unknown == ()


def test_single_mute_group():
    assert parse("#M1").mute_groups == (1,)


def test_single_dca():
    assert parse("#D1").dcas == (1,)


def test_multiple_dcas_comma_separated():
    # Real value from example-Vu.snap aux 1
    m = parse("#D8,#D9")
    assert m.dcas == (8, 9)
    assert m.mute_groups == ()


def test_mixed_kinds():
    m = parse("#D8,#M2,#D10")
    assert m.dcas == (8, 10)
    assert m.mute_groups == (2,)


def test_results_are_sorted_and_deduplicated():
    assert parse("#D10,#D2,#D2").dcas == (2, 10)


def test_whitespace_is_tolerated():
    m = parse(" #D8 , #M1 ")
    assert m.dcas == (8,)
    assert m.mute_groups == (1,)


def test_out_of_range_index_is_unknown_not_silently_accepted():
    m = parse("#M99")
    assert m.mute_groups == ()
    assert m.unknown == ("#M99",)


def test_unrecognised_prefix_is_reported():
    assert parse("#Z3").unknown == ("#Z3",)


def test_real_file_tag_distribution(vu_path):
    raw = load_raw(vu_path)

    channel_tags = {e["tags"] for e in raw.ae["ch"].values() if e["tags"]}
    assert channel_tags == {"#M1", "#M2"}

    bus_dcas = set()
    for entry in raw.ae["bus"].values():
        bus_dcas.update(parse(entry["tags"]).dcas)
    assert bus_dcas == {1, 2, 3, 4, 5, 6}

    # No tag anywhere in the file fails to parse.
    for section in ("ch", "aux", "bus", "main", "mtx"):
        for entry in raw.ae[section].values():
            assert parse(entry.get("tags", "")).unknown == ()
```

- [ ] **Step 3: Run the test and verify it fails**

Run: `python -m pytest tests/test_descriptors_tags.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.descriptors.tags'`

- [ ] **Step 4: Implement the tags parser**

`wing_parser/descriptors/tags.py`:

```python
"""Parse the `tags` membership string.

Membership is stored on the member ("I am in DCA 8"), not on the group,
so building the reverse index is the query layer's job. This module only
turns one string into structured membership.
"""

from __future__ import annotations

from dataclasses import dataclass

from wing_parser.descriptors import registry


@dataclass(frozen=True)
class Membership:
    dcas: tuple[int, ...] = ()
    mute_groups: tuple[int, ...] = ()
    unknown: tuple[str, ...] = ()


def parse(tags_raw: str) -> Membership:
    doc = registry.load("tags")
    separator = doc["separator"]
    prefixes = doc["prefixes"]

    # Longest prefix first, so a future "#DX" cannot be shadowed by "#D"
    # merely because "#D" appears earlier in the YAML. Without this, adding
    # a nested tag kind would need a code change or an unwritten ordering
    # rule in the data file.
    by_length = sorted(prefixes, key=len, reverse=True)

    dcas: set[int] = set()
    mute_groups: set[int] = set()
    unknown: list[str] = []

    for token in (tags_raw or "").split(separator):
        token = token.strip()
        if not token:
            continue
        spec = next(((p, prefixes[p]) for p in by_length if token.startswith(p)), None)
        if spec is None:
            unknown.append(token)
            continue
        prefix, rules = spec
        try:
            index = int(token[len(prefix):])
        except ValueError:
            unknown.append(token)
            continue
        if not 1 <= index <= rules["max"]:
            unknown.append(token)
            continue
        (dcas if rules["kind"] == "dca" else mute_groups).add(index)

    return Membership(
        dcas=tuple(sorted(dcas)),
        mute_groups=tuple(sorted(mute_groups)),
        unknown=tuple(unknown),
    )
```

- [ ] **Step 5: Run the test and verify it passes**

Run: `python -m pytest tests/test_descriptors_tags.py -v`
Expected: PASS — 10 tests

- [ ] **Step 6: Commit**

```bash
git add wing_parser/descriptors/tags.py wing_parser/descriptors/data/tags.yaml tests/test_descriptors_tags.py
git commit -m "Add tags grammar for DCA and mute-group membership

The tags field stores membership on the member, not the group. This
parses one member's string; the reverse index lands in the query layer."
```

---

## Task 6: Scene-safe bitmap

**Files:**
- Create: `wing_parser/descriptors/safes.py`
- Create: `wing_parser/descriptors/data/safes.yaml`
- Test: `tests/test_descriptors_safes.py`

**Interfaces:**
- Consumes: `registry.load` (Task 4)
- Produces:
  - `wing_parser.descriptors.safes.decode(bitmap: str, expected: int | None = None) -> tuple[bool, ...]` — one entry per position; tuple index 0 is position 1
  - `wing_parser.descriptors.safes.decode_scene(ce_safes: dict) -> dict[str, tuple[bool, ...]]` — every flat-string section of `ce_data.safes`
  - `wing_parser.descriptors.safes.is_safe(flags: tuple[bool, ...], number: int) -> bool` — 1-based lookup, `False` when out of range

- [ ] **Step 1: Write the descriptor data**

`wing_parser/descriptors/data/safes.yaml`:

```yaml
# ce_data.safes holds a positional bitmap per section: one character per
# channel/bus/etc, in ascending order. A space means "not safe"; any
# other character means "safe".
#
# Verified against both sample files, which agree exactly: safes.ch is 40
# spaces, and the block holds thirteen sections — ten flat strings and
# three nested dicts (source, output and area, each keyed by input group
# or surface area). The nested blocks use the same encoding one level
# down; nothing in Phase 1 reads them.
#
# custom (22) and setup (2) are flat and therefore decoded, even though no
# Phase 1 rule consumes them: decode_scene promises every flat section, and
# a promise the data quietly contradicts is worse than an unused entry.
not_safe_char: " "
flat_sections: [ch, aux, bus, main, mtx, dca, mute, fx, custom, setup]
nested_sections: [source, output, area]
expected_lengths:
  ch: 40
  aux: 8
  bus: 16
  main: 4
  mtx: 8
  dca: 16
  mute: 8
  fx: 16
  custom: 22
  setup: 2
```

- [ ] **Step 2: Write the failing test**

`tests/test_descriptors_safes.py`:

```python
from wing_parser.core.loader import load_raw
from wing_parser.descriptors.safes import decode, decode_scene, is_safe


def test_all_spaces_means_nothing_is_safe():
    assert decode("    ") == (False, False, False, False)


def test_non_space_marks_safe():
    assert decode(" X  X") == (False, True, False, False, True)


def test_is_safe_uses_one_based_numbering():
    flags = decode(" X ")
    assert is_safe(flags, 1) is False
    assert is_safe(flags, 2) is True
    assert is_safe(flags, 3) is False


def test_out_of_range_lookup_is_false_not_an_error():
    flags = decode(" X ")
    assert is_safe(flags, 99) is False
    assert is_safe(flags, 0) is False


def test_short_bitmap_is_padded_to_expected_length():
    assert decode("X", expected=4) == (True, False, False, False)


def test_real_file_has_nothing_scene_safe(vu_path):
    sections = decode_scene(load_raw(vu_path).ce["safes"])
    assert len(sections["ch"]) == 40
    assert not any(sections["ch"])
    assert not any(sections["bus"])


def test_decode_scene_skips_nested_sections(vu_path):
    sections = decode_scene(load_raw(vu_path).ce["safes"])
    assert {"source", "output", "area"}.isdisjoint(sections)


def test_decode_scene_covers_every_flat_section(vu_path):
    # The real block holds thirteen sections: ten flat strings and three
    # nested dicts. decode_scene promises every flat one, so pin that
    # against the file rather than against the allowlist it reads.
    raw_safes = load_raw(vu_path).ce["safes"]
    flat = {k for k, v in raw_safes.items() if isinstance(v, str)}
    assert set(decode_scene(raw_safes)) == flat
    assert flat == {
        "ch", "aux", "bus", "main", "mtx", "dca", "mute", "fx", "custom", "setup",
    }
```

- [ ] **Step 3: Run the test and verify it fails**

Run: `python -m pytest tests/test_descriptors_safes.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.descriptors.safes'`

- [ ] **Step 4: Implement the safes decoder**

`wing_parser/descriptors/safes.py`:

```python
"""Decode the ce_data.safes positional bitmap.

Scene Safe turns out to live inside the file, not only in console state,
which is why scene-safe rules are reachable in Phase 1.
"""

from __future__ import annotations

from typing import Any

from wing_parser.descriptors import registry


def decode(bitmap: str, expected: int | None = None) -> tuple[bool, ...]:
    """One bool per position. Index 0 is position 1."""
    doc = registry.load("safes")
    blank = doc["not_safe_char"]
    text = bitmap or ""
    if expected is not None and len(text) < expected:
        text = text.ljust(expected, blank)
    return tuple(char != blank for char in text)


def decode_scene(ce_safes: dict[str, Any]) -> dict[str, tuple[bool, ...]]:
    """Decode every flat section of ce_data.safes.

    Nested sections (source.A, source.LCL, ...) are skipped; nothing in
    Phase 1 needs per-source safe flags.
    """
    doc = registry.load("safes")
    lengths = doc["expected_lengths"]
    decoded: dict[str, tuple[bool, ...]] = {}
    for section in doc["flat_sections"]:
        value = ce_safes.get(section)
        if isinstance(value, str):
            decoded[section] = decode(value, expected=lengths.get(section))
    return decoded


def is_safe(flags: tuple[bool, ...], number: int) -> bool:
    """1-based lookup. Out of range is False, not an error."""
    if number < 1 or number > len(flags):
        return False
    return flags[number - 1]
```

- [ ] **Step 5: Run the test and verify it passes**

Run: `python -m pytest tests/test_descriptors_safes.py -v`
Expected: PASS — 7 tests

- [ ] **Step 6: Commit**

```bash
git add wing_parser/descriptors/safes.py wing_parser/descriptors/data/safes.yaml tests/test_descriptors_safes.py
git commit -m "Decode the ce_data.safes positional bitmap

Scene Safe is stored in the file, one character per channel, so
scene-safe rules are reachable without live console state."
```

---

## Task 7: EQ model dispatch

**Files:**
- Create: `wing_parser/descriptors/eq_models.py`
- Create: `wing_parser/descriptors/data/eq_models.yaml`
- Test: `tests/test_descriptors_eq_models.py`

**Interfaces:**
- Consumes: `registry.load` (Task 4); `Anomaly`, `Eq`, `EqBand` (Task 3)
- Produces:
  - `wing_parser.descriptors.eq_models.build(raw_eq: dict) -> tuple[Eq, list[Anomaly]]`

- [ ] **Step 1: Write the descriptor data**

`wing_parser/descriptors/data/eq_models.yaml`:

```yaml
# Band layout per EQ model.
#
# Only STD ships complete. Across both sample files, 150 of 152 EQ blocks
# use STD and 2 use PULSAR; the other nine models documented in the manual
# never appear, so writing descriptors for them would be guesswork with no
# data to check against.
#
# A model with no entry here yields bands=None plus a descriptor_missing
# anomaly. It must never be parsed with another model's layout: PULSAR is
# a Pultec-style passive EQ whose parameters are boost/attenuate pairs,
# structurally unlike STD's freq/gain/Q triples.
models:
  STD:
    label: "WING EQ"
    bands:
      - { name: low,  gain: lg, freq: lf, q: lq, shape: leq }
      - { name: "1",  gain: 1g, freq: 1f, q: 1q }
      - { name: "2",  gain: 2g, freq: 2f, q: 2q }
      - { name: "3",  gain: 3g, freq: 3f, q: 3q }
      - { name: "4",  gain: 4g, freq: 4f, q: 4q }
      - { name: high, gain: hg, freq: hf, q: hq, shape: heq }
```

Keys such as `1g`, `lg` and `hg` are unquoted here and load as strings, because they start with a digit or letter but are not valid YAML numbers. If a future model uses a key that *is* a bare number, quote it.

- [ ] **Step 2: Write the failing test**

`tests/test_descriptors_eq_models.py`:

```python
import pytest

from wing_parser.core.loader import load_raw
from wing_parser.descriptors.eq_models import build


def test_std_model_yields_six_bands(vu_path):
    eq, anomalies = build(load_raw(vu_path).ae["ch"]["8"]["eq"])

    assert anomalies == []
    assert eq.on is True
    assert eq.model == "STD"
    assert eq.bands is not None
    assert [b.name for b in eq.bands] == ["low", "1", "2", "3", "4", "high"]


def test_std_band_values_match_the_file(vu_path):
    eq, _ = build(load_raw(vu_path).ae["ch"]["8"]["eq"])
    band2 = next(b for b in eq.bands if b.name == "2")

    assert band2.gain == pytest.approx(-8.9, abs=1e-6)
    assert band2.freq == pytest.approx(241.1459, abs=1e-3)
    assert band2.q == pytest.approx(3.7243, abs=1e-3)


def test_shelf_shape_is_captured(vu_path):
    eq, _ = build(load_raw(vu_path).ae["ch"]["8"]["eq"])
    assert next(b for b in eq.bands if b.name == "low").shape == "SHV"
    assert next(b for b in eq.bands if b.name == "1").shape is None


def test_unknown_model_yields_no_bands_and_an_anomaly():
    eq, anomalies = build({"on": True, "mdl": "PULSAR", "lowboost": 3.0})

    assert eq.model == "PULSAR"
    assert eq.bands is None
    assert eq.raw["lowboost"] == 3.0
    assert len(anomalies) == 1
    assert anomalies[0].code == "descriptor_missing"
    assert "PULSAR" in anomalies[0].detail


def test_unknown_model_never_borrows_the_std_layout():
    # STD-shaped keys under a foreign model must still be refused.
    eq, anomalies = build({"on": True, "mdl": "SOUL", "1g": 3.0, "1f": 100.0, "1q": 1.0})
    assert eq.bands is None
    assert anomalies[0].code == "descriptor_missing"


def test_missing_band_key_is_reported_not_guessed():
    eq, anomalies = build({"on": True, "mdl": "STD", "lg": 0.0, "lf": 100.0, "lq": 1.0})
    assert eq.bands is None
    assert anomalies[0].code == "eq_band_incomplete"


def test_every_eq_in_both_files_either_builds_or_is_flagged(factory_path, vu_path):
    seen: dict[str, int] = {}
    for path in (factory_path, vu_path):
        raw = load_raw(path)
        for section in ("ch", "aux", "bus", "main", "mtx"):
            for entry in raw.ae[section].values():
                if "eq" not in entry:
                    continue
                eq, anomalies = build(entry["eq"])
                seen[eq.model] = seen.get(eq.model, 0) + 1
                if eq.model == "STD":
                    assert eq.bands is not None and anomalies == []
                else:
                    assert eq.bands is None and anomalies

    assert seen["STD"] == 150
    assert seen["PULSAR"] == 2
```

- [ ] **Step 3: Run the test and verify it fails**

Run: `python -m pytest tests/test_descriptors_eq_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.descriptors.eq_models'`

- [ ] **Step 4: Implement the EQ builder**

`wing_parser/descriptors/eq_models.py`:

```python
"""Build an Eq record from the raw eq block, dispatching on eq.mdl.

The refusal path matters as much as the success path. An EQ model with no
descriptor yields bands=None rather than borrowing another model's
layout: PULSAR stores boost/attenuate pairs, not freq/gain/Q triples, and
reading it as STD would produce plausible wrong numbers rather than an
obvious failure.
"""

from __future__ import annotations

from typing import Any

from wing_parser.core.models import Anomaly, Eq, EqBand
from wing_parser.descriptors import registry


def _refuse(raw_eq: dict[str, Any], model: str, on: bool, anomaly: Anomaly):
    return Eq(on=on, model=model, bands=None, raw=dict(raw_eq)), [anomaly]


def build(raw_eq: dict[str, Any]) -> tuple[Eq, list[Anomaly]]:
    model = raw_eq.get("mdl", "UNKNOWN")
    on = bool(raw_eq.get("on", False))
    spec = registry.load("eq_models")["models"].get(model)

    if spec is None:
        return _refuse(
            raw_eq, model, on,
            Anomaly(
                code="descriptor_missing",
                where=f"eq.mdl={model}",
                detail=(
                    f"no band descriptor for EQ model {model!r}; "
                    "band data left unparsed rather than guessed"
                ),
            ),
        )

    bands: list[EqBand] = []
    for band_spec in spec["bands"]:
        gain_key, freq_key, q_key = band_spec["gain"], band_spec["freq"], band_spec["q"]
        if any(key not in raw_eq for key in (gain_key, freq_key, q_key)):
            return _refuse(
                raw_eq, model, on,
                Anomaly(
                    code="eq_band_incomplete",
                    where=f"eq.mdl={model}",
                    detail=(
                        f"band {band_spec['name']!r} is missing one of "
                        f"{gain_key}/{freq_key}/{q_key}"
                    ),
                ),
            )
        shape_key = band_spec.get("shape")
        bands.append(
            EqBand(
                name=str(band_spec["name"]),
                gain=float(raw_eq[gain_key]),
                freq=float(raw_eq[freq_key]),
                q=float(raw_eq[q_key]),
                shape=raw_eq.get(shape_key) if shape_key else None,
            )
        )

    return Eq(on=on, model=model, bands=tuple(bands), raw=dict(raw_eq)), []
```

- [ ] **Step 5: Run the test and verify it passes**

Run: `python -m pytest tests/test_descriptors_eq_models.py -v`
Expected: PASS — 7 tests. The last is the milestone check: it walks every EQ block in both files and confirms the 150/2 split.

- [ ] **Step 6: Run the whole suite with coverage**

Run: `python -m pytest --cov=wing_parser.core --cov=wing_parser.descriptors --cov-report=term-missing`
Expected: all tests pass; coverage on `wing_parser/core` at or above 80%.

- [ ] **Step 7: Commit**

```bash
git add wing_parser/descriptors/eq_models.py wing_parser/descriptors/data/eq_models.yaml tests/test_descriptors_eq_models.py
git commit -m "Dispatch EQ band layout on eq.mdl, refusing unknown models

Only STD ships a descriptor. PULSAR and friends yield bands=None plus a
descriptor_missing anomaly rather than being read with STD's layout,
which would produce plausible wrong numbers instead of a clear failure."
```

**Milestone 1.** Both files now decode end to end: version, levels, keys, proc chain, tap points, tags, scene-safe flags, EQ bands.

---

## Task 8: Channel builder

**Files:**
- Create: `wing_parser/query/__init__.py`
- Create: `wing_parser/query/build_blocks.py`
- Create: `wing_parser/query/build_channel.py`
- Test: `tests/test_query_build_channel.py`

**Interfaces:**
- Consumes: `to_db` (Task 2); all records from Task 3; `proc_chain.decode` / `proc_chain.tap_point` (Task 4); `eq_models.build` (Task 7)
- Produces:
  - `wing_parser.query.build_blocks.MATRIX_PREFIX: str = "MX"`
  - `wing_parser.query.build_blocks.parse_send_key(key: str) -> tuple[str, int] | None` — `"8"` → `("bus", 8)`, `"MX3"` → `("matrix", 3)`, anything else → `None`
  - `wing_parser.query.build_blocks.build_dyn(raw: dict | None) -> Dyn`
  - `wing_parser.query.build_blocks.build_sends(raw: dict | None) -> tuple[tuple[Send, ...], list[Anomaly]]` — buses first, then matrices, each ascending; a key that parses as neither is skipped and reported
  - `wing_parser.query.build_blocks.build_main_sends(raw: dict | None) -> tuple[tuple[MainSend, ...], list[Anomaly]]`
  - `wing_parser.query.build_channel.build(number: int, entry: dict) -> tuple[ChannelData, list[Anomaly]]`

  **Why two modules.** Channels, auxes, buses, mains and matrices all carry a dynamics block and the same two send collections, so those builders live in `build_blocks.py` and both `build_channel.py` and Task 9's `build_bus.py` import from it. Putting them in `build_channel.py` and having the bus builder reach across for them would make the bus builder depend on the channel builder for no reason other than which file was written first. `_filter`, `_gate` and `_insert` stay private in `build_channel.py` — nothing else builds them.

Note: the builder returns `ChannelData`, a plain record. Navigation (`.source`, `.dcas`) arrives in Task 10 as a separate view class, so this module never needs a back-reference to the scene.

- [ ] **Step 1: Write the failing test**

`tests/test_query_build_channel.py`:

```python
import math

import pytest

from wing_parser.core.loader import load_raw
from wing_parser.core.normalizer import NEG_INF
from wing_parser.query.build_channel import build


@pytest.fixture(scope="module")
def ch8(vu_path):
    data, anomalies = build(8, load_raw(vu_path).ae["ch"]["8"])
    assert anomalies == []
    return data


def test_scalar_fields(ch8):
    assert ch8.number == 8
    assert ch8.name == "M8 MC"
    assert ch8.muted is False
    assert ch8.fader_dB == pytest.approx(-7.9, abs=1e-6)
    assert ch8.solo_safe is False


def test_proc_chain_and_tap_point(ch8):
    assert ch8.proc_raw == "GEDI"
    assert ch8.proc_chain == ("GATE", "EQ", "DELAY", "INSERT")
    assert ch8.tap_point == "POST_FDR"


def test_filter_fields(ch8):
    assert ch8.filter.low_cut_on is True
    assert ch8.filter.low_cut_hz == pytest.approx(151.06, abs=0.01)
    assert ch8.filter.low_cut_slope == 24
    assert ch8.filter.high_cut_on is False


def test_gate_fields(ch8):
    assert ch8.gate.on is True
    assert ch8.gate.model == "GATE"
    assert ch8.gate.threshold_dB == pytest.approx(-62.0)
    assert ch8.gate.range_dB == pytest.approx(12.0)


def test_post_insert_carries_the_automix_group_and_weight(ch8):
    assert ch8.post_insert.on is False
    assert ch8.post_insert.automix_group == "X"
    assert ch8.post_insert.automix_weight == pytest.approx(-12.0)
    assert ch8.pre_insert.automix_group is None


def test_source_refs(ch8):
    assert ch8.source_ref.group == "A"
    assert ch8.source_ref.index == 8
    assert ch8.alt_source_ref.is_off is True


def test_trim_and_polarity(ch8):
    assert ch8.trim_dB == pytest.approx(7.0, abs=1e-6)
    assert ch8.polarity_invert is False


def test_sends_are_indexed_by_destination(ch8):
    send8 = next(s for s in ch8.sends if s.dest_kind == "bus" and s.dest == 8)
    assert send8.on is True
    assert send8.mode == "POST"
    assert send8.level_dB == pytest.approx(-19.9, abs=1e-6)

    send2 = next(s for s in ch8.sends if s.dest_kind == "bus" and s.dest == 2)
    assert send2.on is False
    assert send2.level_dB == NEG_INF


def test_matrix_sends_are_kept_and_kept_distinct(ch8):
    # Every send block holds 16 bus keys and 8 "MX<n>" matrix keys.
    # Bus 3 and MX3 are different destinations sharing a number.
    buses = [s for s in ch8.sends if s.dest_kind == "bus"]
    matrices = [s for s in ch8.sends if s.dest_kind == "matrix"]
    assert len(buses) == 16
    assert len(matrices) == 8
    assert {s.dest for s in matrices} == set(range(1, 9))


def test_sends_are_ordered_buses_then_matrices(ch8):
    kinds = [s.dest_kind for s in ch8.sends]
    assert kinds == ["bus"] * 16 + ["matrix"] * 8
    assert [s.dest for s in ch8.sends[:16]] == list(range(1, 17))


def test_silent_fader_uses_negative_infinity(vu_path):
    data, _ = build(13, load_raw(vu_path).ae["ch"]["13"])
    assert math.isinf(data.fader_dB)
    assert data.name == "Kick In "        # trailing space preserved verbatim
    assert data.tags_raw == "#M1"


def test_every_channel_in_both_files_builds(factory_path, vu_path):
    for path in (factory_path, vu_path):
        raw = load_raw(path)
        for key, entry in raw.ae["ch"].items():
            data, anomalies = build(int(key), entry)
            assert data.number == int(key)
            assert all(a.code != "eq_band_incomplete" for a in anomalies)
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m pytest tests/test_query_build_channel.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.query.build_channel'`

- [ ] **Step 3: Implement the channel builder**

Create an empty `wing_parser/query/__init__.py`, then `wing_parser/query/build_channel.py`:

```python
"""Assemble a ChannelData record from one raw ch entry."""

from __future__ import annotations

from typing import Any

from wing_parser.core.models import (
    Anomaly,
    ChannelData,
    Dyn,
    Filter,
    Gate,
    Insert,
    MainSend,
    Send,
    SourceRef,
)
from wing_parser.core.normalizer import to_db
from wing_parser.descriptors import eq_models, proc_chain

AUTOMIX_PREFIX = "AUTO_"


def _filter(raw: dict[str, Any]) -> Filter:
    return Filter(
        low_cut_on=bool(raw.get("lc", False)),
        low_cut_hz=float(raw.get("lcf", 0.0)),
        low_cut_slope=int(raw.get("lcs", 12)),
        high_cut_on=bool(raw.get("hc", False)),
        high_cut_hz=float(raw.get("hcf", 0.0)),
        high_cut_slope=int(raw.get("hcs", 12)),
    )


def _gate(raw: dict[str, Any]) -> Gate:
    return Gate(
        on=bool(raw.get("on", False)),
        model=raw.get("mdl", "UNKNOWN"),
        threshold_dB=float(raw.get("thr", 0.0)),
        range_dB=float(raw.get("range", 0.0)),
        attack_ms=float(raw.get("att", 0.0)),
        hold_ms=float(raw.get("hld", 0.0)),
        release_ms=float(raw.get("rel", 0.0)),
    )


def build_dyn(raw: dict[str, Any] | None) -> Dyn:
    """Public: build_bus.py builds the same block from bus entries."""
    raw = raw or {}
    return Dyn(
        on=bool(raw.get("on", False)),
        model=raw.get("mdl", "NONE"),
        threshold_dB=float(raw.get("thr", 0.0)),
        ratio=float(raw.get("ratio", 1.0)),
        attack_ms=float(raw.get("att", 0.0)),
        release_ms=float(raw.get("rel", 0.0)),
    )


def _insert(raw: dict[str, Any] | None) -> Insert:
    """preins carries {on, ins}; postins adds {mode, w} for automix."""
    raw = raw or {}
    mode = raw.get("mode")
    group = mode[len(AUTOMIX_PREFIX):] if isinstance(mode, str) and mode.startswith(AUTOMIX_PREFIX) else None
    weight = float(raw["w"]) if group is not None and "w" in raw else None
    return Insert(
        on=bool(raw.get("on", False)),
        slot=raw.get("ins", "NONE"),
        automix_group=group,
        automix_weight=weight,
    )


MATRIX_PREFIX = "MX"


def parse_send_key(key: str) -> tuple[str, int] | None:
    """Split a send-block key into its destination kind and number.

    Both real files store 16 numeric bus keys and 8 "MX<n>" matrix keys in
    the same dict — and a main's send block holds *only* matrix keys, so
    discarding the non-numeric ones would leave every main with no sends
    at all.

    Returns None for a key that is neither form. Every sibling in this
    codebase reports malformed input rather than raising, so a corrupt
    key must not abort the whole channel build.
    """
    if key.startswith(MATRIX_PREFIX):
        rest, kind = key[len(MATRIX_PREFIX):], "matrix"
    else:
        rest, kind = key, "bus"
    try:
        return kind, int(rest)
    except ValueError:
        return None


def build_sends(
    raw: dict[str, Any] | None,
) -> tuple[tuple[Send, ...], list[Anomaly]]:
    """Public: shared with build_bus.py."""
    sends: list[Send] = []
    anomalies: list[Anomaly] = []

    for key, value in (raw or {}).items():
        parsed = parse_send_key(key)
        if parsed is None:
            anomalies.append(
                Anomaly(
                    code="malformed_send_key",
                    where=f"send.{key}",
                    detail="neither a bus number nor MX<n>; send skipped",
                )
            )
            continue
        dest_kind, dest = parsed
        sends.append(
            Send(
                dest_kind=dest_kind,
                dest=dest,
                on=bool(value.get("on", False)),
                level_dB=to_db(value.get("lvl")),
                mode=value.get("mode", "GRP"),
                pre_on=bool(value.get("pon", False)),
                pan=float(value.get("pan", 0.0)),
            )
        )

    # Buses first, then matrices, each ascending — a stable order the diff
    # and the rule engine can both rely on.
    return tuple(sorted(sends, key=lambda s: (s.dest_kind, s.dest))), anomalies


def build_main_sends(
    raw: dict[str, Any] | None,
) -> tuple[tuple[MainSend, ...], list[Anomaly]]:
    """Public: shared with build_bus.py. Main keys are always numeric."""
    sends: list[MainSend] = []
    anomalies: list[Anomaly] = []

    for key, value in (raw or {}).items():
        try:
            dest = int(key)
        except ValueError:
            anomalies.append(
                Anomaly(
                    code="malformed_send_key",
                    where=f"main.{key}",
                    detail="not a main number; send skipped",
                )
            )
            continue
        sends.append(
            MainSend(
                dest=dest,
                on=bool(value.get("on", False)),
                level_dB=to_db(value.get("lvl")),
                pre=bool(value.get("pre", False)),
            )
        )

    return tuple(sorted(sends, key=lambda s: s.dest)), anomalies


def build(number: int, entry: dict[str, Any]) -> tuple[ChannelData, list[Anomaly]]:
    eq, found = eq_models.build(entry.get("eq", {}))
    sends, send_found = build_sends(entry.get("send"))
    main_sends, main_found = build_main_sends(entry.get("main"))
    anomalies = [
        Anomaly(a.code, f"ch.{number}.{a.where}", a.detail)
        for a in (*found, *send_found, *main_found)
    ]

    conn = entry.get("in", {}).get("conn", {})
    settings = entry.get("in", {}).get("set", {})

    data = ChannelData(
        number=number,
        name=entry.get("name", ""),
        icon=int(entry.get("icon", 0)),
        color=int(entry.get("col", 0)),
        muted=bool(entry.get("mute", False)),
        fader_dB=to_db(entry.get("fdr")),
        pan=float(entry.get("pan", 0.0)),
        width=float(entry.get("wid", 100.0)),
        solo_safe=bool(entry.get("solosafe", False)),
        proc_raw=entry.get("proc", ""),
        proc_chain=proc_chain.decode(entry.get("proc", "")),
        tap_point=proc_chain.tap_point(entry.get("ptap", "")),
        tags_raw=entry.get("tags", ""),
        trim_dB=float(settings.get("trim", 0.0)),
        polarity_invert=bool(settings.get("inv", False)),
        delay_ms=float(settings.get("dly", 0.0)),
        delay_on=bool(settings.get("dlyon", False)),
        source_ref=SourceRef(conn.get("grp", "OFF"), int(conn.get("in", 0))),
        alt_source_ref=SourceRef(conn.get("altgrp", "OFF"), int(conn.get("altin", 0))),
        filter=_filter(entry.get("flt", {})),
        eq=eq,
        gate=_gate(entry.get("gate", {})),
        dyn=build_dyn(entry.get("dyn")),
        pre_insert=_insert(entry.get("preins")),
        post_insert=_insert(entry.get("postins")),
        sends=sends,
        main_sends=main_sends,
    )
    return data, anomalies
```

`_filter`, `_gate` and `_insert` stay private — they are channel-only. The three `build_*` functions are public because `build_bus.py` builds the same blocks from bus entries.

- [ ] **Step 4: Run the test and verify it passes**

Run: `python -m pytest tests/test_query_build_channel.py -v`
Expected: PASS — 10 tests

- [ ] **Step 5: Commit**

```bash
git add wing_parser/query/__init__.py wing_parser/query/build_channel.py tests/test_query_build_channel.py
git commit -m "Assemble ChannelData from raw ch entries

The builder produces plain records with no back-references; navigation
arrives later as a separate view class. Automix group and weight are
lifted out of postins.mode/postins.w here."
```

---

## Task 9: Source and bus builders

**Files:**
- Create: `wing_parser/query/build_io.py`
- Create: `wing_parser/query/build_bus.py`
- Test: `tests/test_query_build_io.py`

**Interfaces:**
- Consumes: `to_db` (Task 2); `SourceData`, `BusData`, `DcaData`, `MuteGroupData` (Task 3); `eq_models.build` (Task 7); `build_dyn`, `build_sends`, `build_main_sends` (Task 8 — import them from `wing_parser.query.build_blocks`, not from `build_channel`)
- Produces:
  - `wing_parser.query.build_io.build_sources(io_in: dict) -> dict[tuple[str, int], SourceData]` — keyed by `(group, index)`
  - `wing_parser.query.build_io.build_dcas(section: dict) -> dict[int, DcaData]`
  - `wing_parser.query.build_io.build_mute_groups(section: dict) -> dict[int, MuteGroupData]`
  - `wing_parser.query.build_bus.build(kind: str, number: int, entry: dict) -> tuple[BusData, list[Anomaly]]`

- [ ] **Step 1: Write the failing test**

`tests/test_query_build_io.py`:

```python
import pytest

from wing_parser.core.loader import load_raw
from wing_parser.query.build_bus import build as build_bus
from wing_parser.query.build_io import build_dcas, build_mute_groups, build_sources


def test_sources_are_keyed_by_group_and_index(vu_path):
    sources = build_sources(load_raw(vu_path).ae["io"]["in"])
    source = sources[("A", 8)]

    assert source.group == "A"
    assert source.index == 8
    assert source.gain_dB == pytest.approx(5.0)
    assert source.phantom is False
    assert source.polarity is False
    assert source.mode == "M"


def test_all_thirteen_source_groups_are_present(vu_path):
    sources = build_sources(load_raw(vu_path).ae["io"]["in"])
    groups = {group for group, _ in sources}
    assert {"LCL", "AUX", "A", "B", "C", "SC", "USB", "CRD", "AES"} <= groups


def test_dcas_carry_names_and_levels(vu_path):
    dcas = build_dcas(load_raw(vu_path).ae["dca"])
    assert len(dcas) == 16
    assert dcas[1].name == "MIC"
    # The file stores -3.79999876, which is 1.24e-6 away from -3.8 — the
    # console's own encoding artefact, wider than the 1e-6 used elsewhere.
    assert dcas[1].fader_dB == pytest.approx(-3.8, abs=1e-5)


def test_mute_groups(vu_path):
    groups = build_mute_groups(load_raw(vu_path).ae["mgrp"])
    assert len(groups) == 8
    assert groups[1].name == "FBAND"
    assert groups[1].muted is True
    assert groups[3].name == ""


def test_bus_eight_is_mon_vox_with_a_compressor(vu_path):
    data, anomalies = build_bus("bus", 8, load_raw(vu_path).ae["bus"]["8"])

    assert anomalies == []
    assert data.kind == "bus"
    assert data.name == "MON VOX"
    assert data.dyn.model == "COMP"
    assert data.dyn.threshold_dB == pytest.approx(-15.0)
    assert data.dyn.ratio == pytest.approx(3.0)


def test_bus_one_carries_its_dca_tag(vu_path):
    data, _ = build_bus("bus", 1, load_raw(vu_path).ae["bus"]["1"])
    assert data.tags_raw == "#D1"


def test_every_bus_main_and_matrix_builds(vu_path):
    raw = load_raw(vu_path)
    for kind, section in (("bus", "bus"), ("main", "main"), ("matrix", "mtx"), ("aux", "aux")):
        for key, entry in raw.ae[section].items():
            data, _ = build_bus(kind, int(key), entry)
            assert data.kind == kind
            assert data.number == int(key)
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m pytest tests/test_query_build_io.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.query.build_bus'`

- [ ] **Step 3: Implement the IO builder**

`wing_parser/query/build_io.py`:

```python
"""Assemble sources, DCAs and mute groups.

Phantom power, preamp gain and source polarity live on the source, not
the channel. A channel points here via ch.in.conn.{grp,in}.
"""

from __future__ import annotations

from typing import Any

from wing_parser.core.models import DcaData, MuteGroupData, SourceData
from wing_parser.core.normalizer import int_keyed, to_db


def build_sources(io_in: dict[str, Any]) -> dict[tuple[str, int], SourceData]:
    sources: dict[tuple[str, int], SourceData] = {}
    for group, entries in (io_in or {}).items():
        if not isinstance(entries, dict):
            continue
        for key, entry in entries.items():
            try:
                index = int(key)
            except (TypeError, ValueError):
                continue
            sources[(group, index)] = SourceData(
                group=group,
                index=index,
                name=entry.get("name", ""),
                gain_dB=float(entry.get("g", 0.0)),
                phantom=bool(entry.get("vph", False)),
                polarity=bool(entry.get("pol", False)),
                mode=entry.get("mode", "M"),
            )
    return sources


def build_dcas(section: dict[str, Any]) -> dict[int, DcaData]:
    return {
        number: DcaData(
            number=number,
            name=entry.get("name", ""),
            muted=bool(entry.get("mute", False)),
            fader_dB=to_db(entry.get("fdr")),
        )
        for number, entry in int_keyed(section or {}).items()
    }


def build_mute_groups(section: dict[str, Any]) -> dict[int, MuteGroupData]:
    return {
        number: MuteGroupData(
            number=number,
            name=entry.get("name", ""),
            muted=bool(entry.get("mute", False)),
        )
        for number, entry in int_keyed(section or {}).items()
    }
```

Fix wave (2026-08-14): reuses `core.normalizer.int_keyed` — built in
Task 2 for exactly this job — instead of reimplementing the same
string-to-int key conversion inline. Behaviour is preserved (both raise
on a non-numeric key; `int_keyed` additionally sorts ascending and names
the bad key), covered by
`test_dcas_reject_a_non_numeric_key`/`test_mute_groups_reject_a_non_numeric_key`
in `tests/test_query_build_io.py`.

- [ ] **Step 4: Implement the bus builder**

`wing_parser/query/build_bus.py`:

```python
"""Assemble a BusData record for a bus, main, matrix or aux entry.

All four sections share a field layout, so one builder covers them; the
`kind` argument records which section the entry came from.
"""

from __future__ import annotations

from typing import Any

from wing_parser.core.models import Anomaly, BusData
from wing_parser.core.normalizer import to_db
from wing_parser.descriptors import eq_models
from wing_parser.query.build_blocks import build_dyn, build_main_sends, build_sends


def _delay_ms(raw: Any) -> float:
    """Buses store delay as a nested block; matrices sometimes as a bare number."""
    if isinstance(raw, dict):
        return float(raw.get("dly", 0.0))
    return float(raw or 0.0)


def build(kind: str, number: int, entry: dict[str, Any]) -> tuple[BusData, list[Anomaly]]:
    eq, found = eq_models.build(entry.get("eq", {}))
    sends, send_found = build_sends(entry.get("send"))
    main_sends, main_found = build_main_sends(entry.get("main"))
    anomalies = [
        Anomaly(a.code, f"{kind}.{number}.{a.where}", a.detail)
        for a in (*found, *send_found, *main_found)
    ]

    data = BusData(
        number=number,
        kind=kind,
        name=entry.get("name", ""),
        color=int(entry.get("col", 0)),
        muted=bool(entry.get("mute", False)),
        fader_dB=to_db(entry.get("fdr")),
        tags_raw=entry.get("tags", ""),
        eq=eq,
        dyn=build_dyn(entry.get("dyn")),
        delay_ms=_delay_ms(entry.get("dly")),
        sends=sends,
        main_sends=main_sends,
    )
    return data, anomalies
```

- [ ] **Step 5: Run the test and verify it passes**

Run: `python -m pytest tests/test_query_build_io.py -v`
Expected: PASS — 7 tests

- [ ] **Step 6: Commit**

```bash
git add wing_parser/query/build_io.py wing_parser/query/build_bus.py tests/test_query_build_io.py
git commit -m "Assemble sources, DCAs, mute groups and bus-family records

Phantom, preamp gain and source polarity live on the source, keyed by
(group, index); channels reference them through ch.in.conn. Buses,
mains, matrices and auxes share one builder since their field layout
is identical."
```

---

## Task 10: WingScene and the Channel view

**Files:**
- Create: `wing_parser/query/channel.py`
- Create: `wing_parser/query/scene.py`
- Modify: `wing_parser/__init__.py`
- Test: `tests/test_query_scene.py`

**Interfaces:**
- Consumes: everything from Tasks 1–9
- Produces:
  - `wing_parser.query.channel.Channel` — view class. Constructor `Channel(data: ChannelData, scene: WingScene)`. Delegates unknown attributes to `data`, so `ch.name`, `ch.fader_dB`, `ch.eq` all work. Adds: `.data`, `.source`, `.alt_source`, `.effective_polarity`, `.dcas`, `.mute_groups`, `.scene_safe`, `.send_to(dest)`
  - `wing_parser.query.scene.WingScene` — `WingScene.load(path) -> WingScene`; attributes `version`, `path`, `anomalies`, `sources`, `dcas`, `mute_groups`, `safes`; methods `channel(n)`, `channels()`, `raw`
  - `wing_parser.WingScene` re-export

- [ ] **Step 1: Write the failing test**

`tests/test_query_scene.py`:

```python
import pytest

from wing_parser import WingScene


@pytest.fixture(scope="module")
def scene(vu_path):
    return WingScene.load(vu_path)


def test_load_detects_version_and_reports_no_anomalies(scene):
    assert scene.version.type_id == "snapshot.11"
    assert [a for a in scene.anomalies if a.code != "descriptor_missing"] == []


def test_channel_lookup_is_one_based(scene):
    assert scene.channel(8).name == "M8 MC"
    assert scene.channel(1).name == "Mic 1 VOX IEM1"
    assert len(scene.channels()) == 40


def test_unknown_channel_number_raises(scene):
    with pytest.raises(KeyError, match="99"):
        scene.channel(99)


def test_view_delegates_scalar_fields_to_the_record(scene):
    ch = scene.channel(8)
    assert ch.fader_dB == pytest.approx(-7.9, abs=1e-6)
    assert ch.proc_chain == ("GATE", "EQ", "DELAY", "INSERT")
    assert ch.eq.model == "STD"


def test_source_join_reaches_phantom_and_gain(scene):
    source = scene.channel(8).source
    assert source is not None
    assert source.group == "A"
    assert source.index == 8
    assert source.phantom is False
    assert source.gain_dB == pytest.approx(5.0)


def test_alt_source_is_none_when_off(scene):
    assert scene.channel(8).alt_source is None


def test_effective_polarity_is_the_xor_of_channel_and_source(scene):
    # Channel 8: ch.in.set.inv False, source pol False -> False
    assert scene.channel(8).effective_polarity is False


def test_effective_polarity_double_inversion_cancels(vu_path, tmp_path):
    import json

    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"]["8"]["in"]["set"]["inv"] = True
    doc["ae_data"]["io"]["in"]["A"]["8"]["pol"] = True
    flipped = tmp_path / "flipped.snap"
    flipped.write_text(json.dumps(doc), encoding="utf-8")

    scene = WingScene.load(flipped)
    assert scene.channel(8).effective_polarity is False   # both inverted cancels

    doc["ae_data"]["io"]["in"]["A"]["8"]["pol"] = False
    single = tmp_path / "single.snap"
    single.write_text(json.dumps(doc), encoding="utf-8")
    assert WingScene.load(single).channel(8).effective_polarity is True


def test_send_to_returns_the_named_destination(scene):
    send = scene.channel(8).send_to(8)
    assert send.mode == "POST"
    assert send.on is True
    assert scene.channel(8).send_to(999) is None


def test_scene_safe_is_false_for_every_channel_in_this_file(scene):
    assert not any(ch.scene_safe for ch in scene.channels())


def test_unknown_version_surfaces_as_an_anomaly_but_still_loads(vu_path, tmp_path):
    import json

    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["type"] = "snapshot.99"
    future = tmp_path / "future.snap"
    future.write_text(json.dumps(doc), encoding="utf-8")

    scene = WingScene.load(future)
    assert scene.channel(8).name == "M8 MC"
    assert any(a.code == "unknown_version" for a in scene.anomalies)


def test_factory_scene_loads_too(factory_path):
    scene = WingScene.load(factory_path)
    assert scene.version.type_id == "snapshot.10"
    assert len(scene.channels()) == 40


def test_channel_survives_copy_and_deepcopy(scene):
    import copy

    # copy probes __setstate__ on a __new__-built shell whose __dict__ is
    # empty. An unguarded __getattr__ recurses forever looking for `data`.
    shallow = copy.copy(scene.channel(8))
    assert shallow.name == "M8 MC"
    assert copy.deepcopy(scene.channel(8)).data.number == 8


def test_a_property_raising_internally_is_not_reported_as_missing(scene, monkeypatch):
    # If `source` blows up inside, the caller must see that — not a
    # misleading "Channel has no attribute 'source'".
    monkeypatch.setattr(
        type(scene), "source_for",
        lambda self, ref: (_ for _ in ()).throw(AttributeError("boom")),
    )
    with pytest.raises(AttributeError) as caught:
        _ = scene.channel(8).source
    assert "has no attribute 'source'" not in str(caught.value)


def test_unknown_attribute_still_reports_cleanly(scene):
    with pytest.raises(AttributeError, match="no attribute 'not_a_field'"):
        _ = scene.channel(8).not_a_field
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m pytest tests/test_query_scene.py -v`
Expected: FAIL — `ImportError: cannot import name 'WingScene' from 'wing_parser'`

- [ ] **Step 3: Implement the Channel view**

`wing_parser/query/channel.py`:

```python
"""A navigable view over one ChannelData record.

Unknown attributes fall through to the record, so `ch.name` and
`ch.eq` work without restating every field. Everything defined here
needs the scene: it is the cross-object navigation the record
deliberately does not carry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wing_parser.core.models import ChannelData, Send, SourceData
from wing_parser.descriptors import safes, tags

if TYPE_CHECKING:
    from wing_parser.query.scene import WingScene


class Channel:
    def __init__(self, data: ChannelData, scene: "WingScene") -> None:
        self.data = data
        self._scene = scene

    def __getattr__(self, item: str) -> Any:
        """Delegate unknown attributes to the wrapped record.

        Two lookups must be refused rather than delegated:

        A private or dunder name. `copy.copy` and `pickle` probe for
        `__setstate__` and friends on a shell built by `__new__`, whose
        `__dict__` is still empty — delegating would re-enter this method
        looking for `data`, which is also absent, and recurse forever.

        A name already defined on the class. Reaching here for one means a
        property raised `AttributeError` internally; answering "no such
        attribute" would bury the real bug.
        """
        if item.startswith("_") or hasattr(type(self), item):
            raise AttributeError(
                f"{type(self).__name__}.{item} is not resolvable on this instance"
            )
        try:
            return getattr(object.__getattribute__(self, "data"), item)
        except AttributeError as exc:
            raise AttributeError(
                f"{type(self).__name__!r} has no attribute {item!r}"
            ) from exc

    def __repr__(self) -> str:
        return f"<Channel {self.data.number} {self.data.name!r}>"

    @property
    def source(self) -> SourceData | None:
        return self._scene.source_for(self.data.source_ref)

    @property
    def alt_source(self) -> SourceData | None:
        return self._scene.source_for(self.data.alt_source_ref)

    @property
    def effective_polarity(self) -> bool:
        """Channel inversion XOR source inversion. Inverting twice is not inverting."""
        source = self.source
        return bool(self.data.polarity_invert) ^ bool(source.polarity if source else False)

    @property
    def dcas(self) -> tuple[int, ...]:
        return tags.parse(self.data.tags_raw).dcas

    @property
    def mute_groups(self) -> tuple[int, ...]:
        return tags.parse(self.data.tags_raw).mute_groups

    @property
    def scene_safe(self) -> bool:
        return safes.is_safe(self._scene.safes.get("ch", ()), self.data.number)

    def send_to(self, dest: int, kind: str = "bus") -> Send | None:
        """A send block mixes buses and matrices, so the number alone is
        ambiguous: bus 3 and MX3 share a number. Defaults to bus."""
        return next(
            (s for s in self.data.sends if s.dest == dest and s.dest_kind == kind),
            None,
        )
```

- [ ] **Step 4: Implement WingScene**

`wing_parser/query/scene.py`:

```python
"""The public entry point: load a .snap file and query it."""

from __future__ import annotations

from pathlib import Path

from wing_parser.core.loader import RawScene, load_raw
from wing_parser.core.models import Anomaly, DcaData, MuteGroupData, SourceData, SourceRef
from wing_parser.core.validator import validate
from wing_parser.descriptors import safes as safes_descriptor
from wing_parser.query.build_channel import build as build_channel
from wing_parser.query.build_io import build_dcas, build_mute_groups, build_sources
from wing_parser.query.channel import Channel


class WingScene:
    def __init__(self, raw: RawScene) -> None:
        self._raw = raw
        self.path: Path = raw.path
        self.version = raw.version

        anomalies: list[Anomaly] = list(validate(raw))

        self._channels: dict[int, Channel] = {}
        for key, entry in raw.ae.get("ch", {}).items():
            number = int(key)
            data, found = build_channel(number, entry)
            anomalies.extend(found)
            self._channels[number] = Channel(data, self)

        self.sources: dict[tuple[str, int], SourceData] = build_sources(
            raw.ae.get("io", {}).get("in", {})
        )
        self.dcas: dict[int, DcaData] = build_dcas(raw.ae.get("dca", {}))
        self.mute_groups: dict[int, MuteGroupData] = build_mute_groups(
            raw.ae.get("mgrp", {})
        )
        self.safes: dict[str, tuple[bool, ...]] = safes_descriptor.decode_scene(
            raw.ce.get("safes", {})
        )
        self.anomalies: tuple[Anomaly, ...] = tuple(anomalies)

    @classmethod
    def load(cls, path: str | Path) -> "WingScene":
        return cls(load_raw(path))

    @property
    def raw(self) -> RawScene:
        return self._raw

    def channel(self, number: int) -> Channel:
        if number not in self._channels:
            raise KeyError(f"no channel {number} in {self.path.name}")
        return self._channels[number]

    def channels(self) -> tuple[Channel, ...]:
        return tuple(self._channels[n] for n in sorted(self._channels))

    def source_for(self, ref: SourceRef) -> SourceData | None:
        if ref.is_off:
            return None
        return self.sources.get((ref.group, ref.index))

    def __repr__(self) -> str:
        return f"<WingScene {self.path.name} {self.version.type_id}>"
```

- [ ] **Step 5: Export the entry point**

Replace `wing_parser/__init__.py` with:

```python
"""Read and analyse Behringer WING .snap scene files."""

from wing_parser.query.scene import WingScene

__version__ = "0.1.0"
__all__ = ["WingScene", "__version__"]
```

- [ ] **Step 6: Run the test and verify it passes**

Run: `python -m pytest tests/test_query_scene.py -v`
Expected: PASS — 16 tests

- [ ] **Step 7: Commit**

```bash
git add wing_parser/query/channel.py wing_parser/query/scene.py wing_parser/__init__.py tests/test_query_scene.py
git commit -m "Add WingScene entry point and the Channel view

The view resolves what the record deliberately cannot: the join to the
source for phantom, gain and polarity; DCA and mute-group membership
from tags; and the scene-safe flag. Effective polarity is the XOR of
channel and source inversion, since inverting twice is not inverting."
```

---

## Task 11: Bus views and the group reverse index

**Files:**
- Create: `wing_parser/query/bus.py`
- Create: `wing_parser/query/groups.py`
- Modify: `wing_parser/query/scene.py`
- Test: `tests/test_query_bus.py`
- Test: `tests/test_query_groups.py`

These two land together because they are only testable together: in the real file, channels carry mute-group tags but **DCA** tags appear exclusively on buses and auxes, so a DCA reverse index cannot be exercised without bus views.

**Interfaces:**
- Consumes: `BusData` (Task 3), `tags.parse` (Task 5), `safes.is_safe` (Task 6), `build_bus.build` (Task 9), `WingScene` (Task 10)
- Produces:
  - `wing_parser.query.bus.Bus` — view class, same delegation pattern as `Channel`. Adds `.data`, `.dcas`, `.mute_groups`, `.scene_safe`, `.send_to(dest)`
  - `wing_parser.query.groups.GroupMember` — frozen dataclass `kind: str`, `number: int`, `name: str`
  - `wing_parser.query.groups.Dca` / `.MuteGroup` — view classes with `.number`, `.name`, `.muted`, `.fader_dB` (DCA only), `.members: tuple[GroupMember, ...]`
  - `wing_parser.query.groups.build_index(scene) -> tuple[dict[int, tuple[GroupMember, ...]], dict[int, tuple[GroupMember, ...]]]` — `(dca_members, mute_group_members)`
  - New on `WingScene`: `.bus(n)`, `.buses()`, `.aux(n)`, `.auxes()`, `.main(n)`, `.mains()`, `.matrix(n)`, `.matrices()`, `.bus_family()`, `.dca(n)`, `.mute_group(n)`

- [ ] **Step 1: Write the failing tests**

`tests/test_query_bus.py`:

```python
import pytest

from wing_parser import WingScene


@pytest.fixture(scope="module")
def scene(vu_path):
    return WingScene.load(vu_path)


def test_bus_lookup_and_delegation(scene):
    bus = scene.bus(8)
    assert bus.number == 8
    assert bus.name == "MON VOX"
    assert bus.kind == "bus"
    assert bus.dyn.model == "COMP"


def test_section_counts(scene):
    assert len(scene.buses()) == 16
    assert len(scene.auxes()) == 8
    assert len(scene.mains()) == 4
    assert len(scene.matrices()) == 8
    assert len(scene.bus_family()) == 36


def test_bus_family_entries_know_their_kind(scene):
    kinds = {entry.kind for entry in scene.bus_family()}
    assert kinds == {"bus", "aux", "main", "matrix"}


def test_bus_carries_its_dca_tag(scene):
    assert scene.bus(1).dcas == (1,)
    assert scene.bus(1).name == "MIC"


def test_unknown_bus_raises(scene):
    with pytest.raises(KeyError, match="99"):
        scene.bus(99)


def test_bus_scene_safe_reads_the_bus_bitmap(scene):
    assert scene.bus(8).scene_safe is False
```

`tests/test_query_groups.py`:

```python
import pytest

from wing_parser import WingScene


@pytest.fixture(scope="module")
def scene(vu_path):
    return WingScene.load(vu_path)


def test_dca_one_is_named_mic_and_has_bus_one_as_a_member(scene):
    dca = scene.dca(1)
    assert dca.name == "MIC"
    # -3.79999876 in the file, 1.24e-6 off -3.8. Same tolerance as the
    # Task 9 assertion against the same value.
    assert dca.fader_dB == pytest.approx(-3.8, abs=1e-5)
    assert ("bus", 1) in [(m.kind, m.number) for m in dca.members]


def test_dcas_one_to_six_hold_buses(scene):
    for number in range(1, 7):
        members = scene.dca(number).members
        assert members, f"DCA {number} should have members"
        assert all(m.kind == "bus" for m in members)


def test_dcas_eight_to_sixteen_hold_auxes(scene):
    # Every aux carries "#D8,#D<n>", so DCA 8 holds all eight of them.
    assert len(scene.dca(8).members) == 8
    assert all(m.kind == "aux" for m in scene.dca(8).members)


def test_no_input_channel_is_assigned_to_a_dca_in_this_file(scene):
    assigned = {m.number for n in range(1, 17) for m in scene.dca(n).members if m.kind == "channel"}
    assert assigned == set()


def test_mute_group_one_holds_the_band_channels(scene):
    members = scene.mute_group(1).members
    assert scene.mute_group(1).name == "FBAND"
    assert scene.mute_group(1).muted is True
    assert all(m.kind == "channel" for m in members)
    assert 13 in [m.number for m in members]      # "Kick In "


def test_mute_group_two_holds_the_playback_channels(scene):
    numbers = {m.number for m in scene.mute_group(2).members}
    assert {10, 12, 37, 38} <= numbers


def test_members_carry_their_names(scene):
    kick = next(m for m in scene.mute_group(1).members if m.number == 13)
    assert kick.name == "Kick In "


def test_empty_group_returns_an_empty_tuple(scene):
    assert scene.mute_group(7).members == ()
```

- [ ] **Step 2: Run the tests and verify they fail**

Run: `python -m pytest tests/test_query_bus.py tests/test_query_groups.py -v`
Expected: FAIL — `AttributeError: 'WingScene' object has no attribute 'bus'`

- [ ] **Step 3: Implement the Bus view**

`wing_parser/query/bus.py`:

```python
"""A navigable view over one BusData record.

Buses, auxes, mains and matrices share this class; `kind` distinguishes
them. Same delegation pattern as Channel.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wing_parser.core.models import BusData, Send
from wing_parser.descriptors import safes, tags

if TYPE_CHECKING:
    from wing_parser.query.scene import WingScene

SAFES_SECTION = {"bus": "bus", "aux": "aux", "main": "main", "matrix": "mtx"}


class Bus:
    def __init__(self, data: BusData, scene: "WingScene") -> None:
        self.data = data
        self._scene = scene

    def __getattr__(self, item: str) -> Any:
        """Same guarded delegation as Channel — see the note there.

        A private or dunder name would recurse on the copy and pickle
        paths; a name defined on the class means a property raised
        internally and must not be reported as missing.
        """
        if item.startswith("_") or hasattr(type(self), item):
            raise AttributeError(
                f"{type(self).__name__}.{item} is not resolvable on this instance"
            )
        try:
            return getattr(object.__getattribute__(self, "data"), item)
        except AttributeError as exc:
            raise AttributeError(
                f"{type(self).__name__!r} has no attribute {item!r}"
            ) from exc

    def __repr__(self) -> str:
        return f"<Bus {self.data.kind}.{self.data.number} {self.data.name!r}>"

    @property
    def dcas(self) -> tuple[int, ...]:
        return tags.parse(self.data.tags_raw).dcas

    @property
    def mute_groups(self) -> tuple[int, ...]:
        return tags.parse(self.data.tags_raw).mute_groups

    @property
    def scene_safe(self) -> bool:
        section = SAFES_SECTION.get(self.data.kind, self.data.kind)
        return safes.is_safe(self._scene.safes.get(section, ()), self.data.number)

    def send_to(self, dest: int, kind: str = "bus") -> Send | None:
        return next(
            (s for s in self.data.sends if s.dest == dest and s.dest_kind == kind),
            None,
        )
```

- [ ] **Step 4: Implement the group reverse index**

`wing_parser/query/groups.py`:

```python
"""Reverse index for DCA and mute-group membership.

The file records membership on the member ("I am in DCA 8"), so
answering "who is in DCA 8" means walking every channel, aux, bus, main
and matrix once and inverting.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from wing_parser.core.models import DcaData, MuteGroupData

if TYPE_CHECKING:
    from wing_parser.query.scene import WingScene


@dataclass(frozen=True)
class GroupMember:
    kind: str
    number: int
    name: str


Index = dict[int, tuple[GroupMember, ...]]


def build_index(scene: "WingScene") -> tuple[Index, Index]:
    dca_members: dict[int, list[GroupMember]] = {}
    mute_members: dict[int, list[GroupMember]] = {}

    entries = [("channel", ch) for ch in scene.channels()]
    entries += [(entry.kind, entry) for entry in scene.bus_family()]

    for kind, view in entries:
        member = GroupMember(kind=kind, number=view.number, name=view.name)
        for number in view.dcas:
            dca_members.setdefault(number, []).append(member)
        for number in view.mute_groups:
            mute_members.setdefault(number, []).append(member)

    freeze = lambda index: {n: tuple(v) for n, v in index.items()}  # noqa: E731
    return freeze(dca_members), freeze(mute_members)


class Dca:
    def __init__(self, data: DcaData, members: tuple[GroupMember, ...]) -> None:
        self.number = data.number
        self.name = data.name
        self.muted = data.muted
        self.fader_dB = data.fader_dB
        self.members = members

    def __repr__(self) -> str:
        return f"<Dca {self.number} {self.name!r} members={len(self.members)}>"


class MuteGroup:
    def __init__(self, data: MuteGroupData, members: tuple[GroupMember, ...]) -> None:
        self.number = data.number
        self.name = data.name
        self.muted = data.muted
        self.members = members

    def __repr__(self) -> str:
        return f"<MuteGroup {self.number} {self.name!r} members={len(self.members)}>"
```

- [ ] **Step 5: Wire the bus family and groups into WingScene**

In `wing_parser/query/scene.py`, add these imports:

```python
from wing_parser.query.build_bus import build as build_bus
from wing_parser.query.bus import Bus
from wing_parser.query.groups import Dca, MuteGroup, build_index
```

Then, inside `__init__`, immediately after the channel loop and before the `self.sources = ...` line, insert:

```python
        self._bus_family: dict[str, dict[int, Bus]] = {}
        for kind, section in (
            ("bus", "bus"),
            ("aux", "aux"),
            ("main", "main"),
            ("matrix", "mtx"),
        ):
            built: dict[int, Bus] = {}
            for key, entry in raw.ae.get(section, {}).items():
                number = int(key)
                data, found = build_bus(kind, number, entry)
                anomalies.extend(found)
                built[number] = Bus(data, self)
            self._bus_family[kind] = built
```

and at the very end of `__init__`, after `self.anomalies = ...`, append:

```python
        self._dca_index, self._mute_index = build_index(self)
```

Finally add these methods to the class:

```python
    def _family(self, kind: str, number: int) -> Bus:
        section = self._bus_family[kind]
        if number not in section:
            raise KeyError(f"no {kind} {number} in {self.path.name}")
        return section[number]

    def bus(self, number: int) -> Bus:
        return self._family("bus", number)

    def aux(self, number: int) -> Bus:
        return self._family("aux", number)

    def main(self, number: int) -> Bus:
        return self._family("main", number)

    def matrix(self, number: int) -> Bus:
        return self._family("matrix", number)

    def buses(self) -> tuple[Bus, ...]:
        return self._sorted("bus")

    def auxes(self) -> tuple[Bus, ...]:
        return self._sorted("aux")

    def mains(self) -> tuple[Bus, ...]:
        return self._sorted("main")

    def matrices(self) -> tuple[Bus, ...]:
        return self._sorted("matrix")

    def _sorted(self, kind: str) -> tuple[Bus, ...]:
        section = self._bus_family[kind]
        return tuple(section[n] for n in sorted(section))

    def bus_family(self) -> tuple[Bus, ...]:
        return self.buses() + self.auxes() + self.mains() + self.matrices()

    def dca(self, number: int) -> Dca:
        return Dca(self.dcas[number], self._dca_index.get(number, ()))

    def mute_group(self, number: int) -> MuteGroup:
        return MuteGroup(self.mute_groups[number], self._mute_index.get(number, ()))
```

`scene.py` now sits near the 200-line ceiling. If it grows further, move the bus-family construction into a `query/assemble.py` helper.

- [ ] **Step 6: Run the tests and verify they pass**

Run: `python -m pytest tests/test_query_bus.py tests/test_query_groups.py -v`
Expected: PASS — 6 + 8 tests

- [ ] **Step 7: Commit**

```bash
git add wing_parser/query/bus.py wing_parser/query/groups.py wing_parser/query/scene.py tests/test_query_bus.py tests/test_query_groups.py
git commit -m "Add bus-family views and the DCA / mute-group reverse index

Membership is stored on the member, so answering 'who is in DCA 1'
means inverting across channels, auxes, buses, mains and matrices. In
this scene the DCAs hold buses and auxes while the mute groups hold
input channels — no input channel is on a DCA at all."
```

---

## Task 12: Routing query

**Files:**
- Create: `wing_parser/query/routing.py`
- Modify: `wing_parser/query/scene.py`
- Test: `tests/test_query_routing.py`

**Interfaces:**
- Consumes: `WingScene`, `Channel`, `Bus` (Tasks 10–11); `is_silent` (Task 2)
- Produces:
  - `wing_parser.query.routing.Feed` — frozen dataclass `kind: str`, `number: int`, `name: str`, `level_dB: float`, `mode: str`, `on: bool`
  - `wing_parser.query.routing.RoutingSummary` — frozen dataclass `orphan_channels`, `alt_sourced_channels`, `unpatched_channels`, `unnamed_but_live`, `live_channel_count` (all `tuple[int, ...]` except the last, an `int`)
  - `wing_parser.query.routing.feeds_into(scene, kind: str, number: int) -> tuple[Feed, ...]`
  - `wing_parser.query.routing.summarise(scene) -> RoutingSummary`
  - New on `WingScene`: `.routing` property returning a small facade with `.summary()` and `.feeds_into(kind, number)`

- [ ] **Step 1: Write the failing test**

`tests/test_query_routing.py`:

```python
import pytest

from wing_parser import WingScene


@pytest.fixture(scope="module")
def scene(vu_path):
    return WingScene.load(vu_path)


def test_feeds_into_bus_eight_includes_channel_eight(scene):
    feeds = scene.routing.feeds_into("bus", 8)
    channel_eight = next(f for f in feeds if f.kind == "channel" and f.number == 8)

    assert channel_eight.name == "M8 MC"
    assert channel_eight.mode == "POST"
    assert channel_eight.on is True
    assert channel_eight.level_dB == pytest.approx(-19.9, abs=1e-6)


def test_feeds_into_only_returns_enabled_sends(scene):
    for feed in scene.routing.feeds_into("bus", 8):
        assert feed.on is True


def test_bus_and_matrix_of_the_same_number_are_different_destinations(scene):
    # The load-bearing property of this module. A send block holds 16 bus
    # keys and 8 MX keys, so bus 3 and MX3 share a number and nothing but
    # dest_kind separates them. Delete the filter in feeds_into and this
    # test fails; without it, every other test here still passes.
    bus3 = {(f.kind, f.number) for f in scene.routing.feeds_into("bus", 3)}
    mx3 = {(f.kind, f.number) for f in scene.routing.feeds_into("matrix", 3)}

    assert bus3 == {("channel", n) for n in (13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 24)}
    assert mx3 == {("main", 1)}
    assert bus3.isdisjoint(mx3)


def test_main_destinations_read_main_sends_not_the_kind_filter(scene):
    # Mains live in main_sends, which carries no dest_kind. The None entry
    # in SEND_SECTION must disable the filter rather than reject everything.
    assert scene.routing.feeds_into("main", 1) != ()


def test_feeds_into_unused_bus_is_empty_or_small(scene):
    feeds = scene.routing.feeds_into("bus", 16)
    assert isinstance(feeds, tuple)


def test_summary_reports_alt_sourced_channels(scene):
    # No channel in this file uses an ALT source.
    assert scene.routing.summary().alt_sourced_channels == ()


def test_summary_counts_live_channels(scene):
    summary = scene.routing.summary()
    # A channel is live when it is unmuted and its fader is above -inf.
    # Verified against the file: ch 8 (M8 MC, -7.9), ch 10 (LED PLAYBACK,
    # -2.6), ch 12 (My Lap, +0.4). Everything else is at -144 or muted.
    assert summary.live_channel_count == 3
    assert isinstance(summary.orphan_channels, tuple)


def test_unpatched_channels_are_listed(scene):
    summary = scene.routing.summary()
    # Verified against the file: channels 13-32, 36, 39 and 40 are named
    # stage-box presets whose source_ref group is OFF for this show, i.e.
    # never patched to hardware. Channels 1-12, 33-35, 37 and 38 are patched.
    assert summary.unpatched_channels == (
        13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29,
        30, 31, 32, 36, 39, 40,
    )


def test_unnamed_but_live_is_reported(vu_path, tmp_path):
    import json

    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"]["8"]["name"] = ""
    blanked = tmp_path / "blank.snap"
    blanked.write_text(json.dumps(doc), encoding="utf-8")

    summary = WingScene.load(blanked).routing.summary()
    assert 8 in summary.unnamed_but_live


def test_orphan_is_a_live_channel_feeding_nothing(vu_path, tmp_path):
    import json

    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    entry = doc["ae_data"]["ch"]["8"]
    for send in entry["send"].values():
        send["on"] = False
    for main in entry["main"].values():
        main["on"] = False
    orphaned = tmp_path / "orphan.snap"
    orphaned.write_text(json.dumps(doc), encoding="utf-8")

    assert 8 in WingScene.load(orphaned).routing.summary().orphan_channels


def test_factory_scene_has_no_live_channels(factory_path):
    assert WingScene.load(factory_path).routing.summary().live_channel_count == 0
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m pytest tests/test_query_routing.py -v`
Expected: FAIL — `AttributeError: 'WingScene' object has no attribute 'routing'`

- [ ] **Step 3: Implement the routing query**

`wing_parser/query/routing.py`:

```python
"""Who feeds what, and which channels look stranded."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from wing_parser.core.normalizer import is_silent

if TYPE_CHECKING:
    from wing_parser.query.scene import WingScene

# Which collection to read, and which dest_kind within it. Buses and
# matrices share the `sends` tuple and are told apart by dest_kind; mains
# live in their own `main_sends` tuple, which carries no kind.
SEND_SECTION: dict[str, tuple[str, str | None]] = {
    "bus": ("sends", "bus"),
    "matrix": ("sends", "matrix"),
    "main": ("main_sends", None),
}


@dataclass(frozen=True)
class Feed:
    kind: str
    number: int
    name: str
    level_dB: float
    mode: str
    on: bool


@dataclass(frozen=True)
class RoutingSummary:
    orphan_channels: tuple[int, ...]
    alt_sourced_channels: tuple[int, ...]
    unpatched_channels: tuple[int, ...]
    unnamed_but_live: tuple[int, ...]
    live_channel_count: int


def _is_live(view) -> bool:
    return not view.muted and not is_silent(view.fader_dB)


def _feeds_anything(view) -> bool:
    return any(s.on for s in view.sends) or any(m.on for m in view.main_sends)


def feeds_into(scene: "WingScene", kind: str, number: int) -> tuple[Feed, ...]:
    """Every enabled send from any channel or bus into the named destination."""
    if kind not in SEND_SECTION:
        raise ValueError(
            f"unrecognised destination kind {kind!r}; expected one of "
            f"{sorted(SEND_SECTION)}"
        )
    attribute, dest_kind = SEND_SECTION[kind]
    found: list[Feed] = []

    sources = [("channel", ch) for ch in scene.channels()]
    sources += [(entry.kind, entry) for entry in scene.bus_family()]

    for source_kind, view in sources:
        if source_kind == kind and view.number == number:
            continue                      # a bus cannot feed itself
        for send in getattr(view, attribute, ()):
            if dest_kind is not None and send.dest_kind != dest_kind:
                continue                  # bus 3 and MX3 share a number
            if send.dest == number and send.on:
                found.append(
                    Feed(
                        kind=source_kind,
                        number=view.number,
                        name=view.name,
                        level_dB=send.level_dB,
                        mode=getattr(send, "mode", "MAIN"),
                        on=send.on,
                    )
                )
    return tuple(found)


def summarise(scene: "WingScene") -> RoutingSummary:
    orphans: list[int] = []
    alt_sourced: list[int] = []
    unpatched: list[int] = []
    unnamed_live: list[int] = []
    live = 0

    for ch in scene.channels():
        if not ch.data.alt_source_ref.is_off:
            alt_sourced.append(ch.number)
        if ch.data.source_ref.is_off:
            unpatched.append(ch.number)
        if _is_live(ch):
            live += 1
            if not ch.name.strip():
                unnamed_live.append(ch.number)
            if not _feeds_anything(ch):
                orphans.append(ch.number)

    return RoutingSummary(
        orphan_channels=tuple(orphans),
        alt_sourced_channels=tuple(alt_sourced),
        unpatched_channels=tuple(unpatched),
        unnamed_but_live=tuple(unnamed_live),
        live_channel_count=live,
    )


class RoutingFacade:
    """Thin binding so callers can write scene.routing.summary()."""

    def __init__(self, scene: "WingScene") -> None:
        self._scene = scene

    def summary(self) -> RoutingSummary:
        return summarise(self._scene)

    def feeds_into(self, kind: str, number: int) -> tuple[Feed, ...]:
        return feeds_into(self._scene, kind, number)
```

- [ ] **Step 4: Wire it into WingScene**

Add to the imports in `wing_parser/query/scene.py`:

```python
from wing_parser.query.routing import RoutingFacade
```

and add this property to the class:

```python
    @property
    def routing(self) -> RoutingFacade:
        return RoutingFacade(self)
```

- [ ] **Step 5: Run the test and verify it passes**

Run: `python -m pytest tests/test_query_routing.py -v`
Expected: PASS — 9 tests. The count of 3 is verified against the file; if it comes out differently, the bug is in `_is_live`, not in the assertion.

- [ ] **Step 6: Commit**

```bash
git add wing_parser/query/routing.py wing_parser/query/scene.py tests/test_query_routing.py
git commit -m "Add routing queries: feeds-into and scene summary

An orphan is a live channel (unmuted, fader above -inf) that feeds no
bus and no main. Alt-sourced channels are surfaced because they are the
scene-file proxy for externally processed audio."
```

---

## Task 13: Scene diff

**Files:**
- Create: `wing_parser/query/diff.py`
- Modify: `wing_parser/query/scene.py`
- Test: `tests/test_query_diff.py`

**Interfaces:**
- Consumes: `WingScene` (Task 10), `ChannelData` / `BusData` (Task 3)
- Produces:
  - `wing_parser.query.diff.Change` — frozen dataclass `path: str`, `before: Any`, `after: Any`, `magnitude: float | None`
  - `wing_parser.query.diff.compare(a: WingScene, b: WingScene) -> tuple[Change, ...]`
  - New on `WingScene`: `.diff(other) -> tuple[Change, ...]`

- [ ] **Step 1: Write the failing test**

`tests/test_query_diff.py`:

```python
import json

import pytest

from wing_parser import WingScene


def test_a_scene_does_not_differ_from_itself(vu_path):
    assert WingScene.load(vu_path).diff(WingScene.load(vu_path)) == ()


def test_fader_change_is_reported_with_a_magnitude(vu_path, tmp_path):
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"]["8"]["fdr"] = -3.0
    louder = tmp_path / "louder.snap"
    louder.write_text(json.dumps(doc), encoding="utf-8")

    changes = WingScene.load(vu_path).diff(WingScene.load(louder))
    fader = next(c for c in changes if c.path == "ch.8.fader_dB")

    assert fader.before == pytest.approx(-7.9, abs=1e-6)
    assert fader.after == pytest.approx(-3.0)
    assert fader.magnitude == pytest.approx(4.9, abs=1e-6)


def test_boolean_change_has_no_magnitude(vu_path, tmp_path):
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"]["8"]["mute"] = True
    muted = tmp_path / "muted.snap"
    muted.write_text(json.dumps(doc), encoding="utf-8")

    change = next(
        c for c in WingScene.load(vu_path).diff(WingScene.load(muted))
        if c.path == "ch.8.muted"
    )
    assert change.before is False
    assert change.after is True
    assert change.magnitude is None


def test_nested_eq_band_change_is_reported(vu_path, tmp_path):
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"]["8"]["eq"]["2g"] = -3.0
    eqd = tmp_path / "eqd.snap"
    eqd.write_text(json.dumps(doc), encoding="utf-8")

    paths = {c.path for c in WingScene.load(vu_path).diff(WingScene.load(eqd))}
    assert "ch.8.eq.bands.2.gain" in paths


def test_send_change_is_reported(vu_path, tmp_path):
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"]["8"]["send"]["8"]["mode"] = "TAP"
    tapped = tmp_path / "tapped.snap"
    tapped.write_text(json.dumps(doc), encoding="utf-8")

    change = next(
        c for c in WingScene.load(vu_path).diff(WingScene.load(tapped))
        if c.path == "ch.8.sends.8.mode"
    )
    assert change.before == "POST"
    assert change.after == "TAP"


def test_matrix_send_change_keeps_its_own_path(vu_path, tmp_path):
    # A send path uses the destination as the file spells it, so a matrix
    # change cannot be confused with the same-numbered bus.
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"]["8"]["send"]["MX3"]["on"] = True
    mxd = tmp_path / "mxd.snap"
    mxd.write_text(json.dumps(doc), encoding="utf-8")

    paths = {c.path for c in WingScene.load(vu_path).diff(WingScene.load(mxd))}
    assert "ch.8.sends.MX3.on" in paths
    assert "ch.8.sends.3.on" not in paths


def test_bus_change_is_reported(vu_path, tmp_path):
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["bus"]["8"]["name"] = "IEM VOX"
    renamed = tmp_path / "renamed.snap"
    renamed.write_text(json.dumps(doc), encoding="utf-8")

    change = next(
        c for c in WingScene.load(vu_path).diff(WingScene.load(renamed))
        if c.path == "bus.8.name"
    )
    assert change.after == "IEM VOX"


def test_fader_leaving_silence_reports_its_full_travel(vu_path, tmp_path):
    # -inf is the fader on its bottom stop, which the console writes as
    # -144. Silent to audible is the largest change a mix can have and
    # must not rank below a 1 dB trim.
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"]["13"]["fdr"] = -7.9      # was -144
    unmuted = tmp_path / "unmuted.snap"
    unmuted.write_text(json.dumps(doc), encoding="utf-8")

    change = next(
        c for c in WingScene.load(vu_path).diff(WingScene.load(unmuted))
        if c.path == "ch.13.fader_dB"
    )
    assert change.before == float("-inf")
    assert change.after == pytest.approx(-7.9)
    assert change.magnitude == pytest.approx(136.1, abs=1e-3)


def test_two_silent_faders_have_no_travel():
    from wing_parser.query.diff import _magnitude

    assert _magnitude(float("-inf"), float("-inf")) is None


def test_a_record_present_on_one_side_only_is_one_change():
    # Documented limitation: an added or removed record is reported whole,
    # not field by field. Pinned so the behaviour is deliberate.
    from wing_parser.core.models import DcaData
    from wing_parser.query.diff import _walk

    out = []
    _walk("dca.1", None, DcaData(1, "MIC", False, -3.8), out)
    assert len(out) == 1
    assert out[0].path == "dca.1"
    assert out[0].before is None
    assert isinstance(out[0].after, DcaData)


def test_factory_versus_show_produces_many_changes(factory_path, vu_path):
    changes = WingScene.load(factory_path).diff(WingScene.load(vu_path))
    assert len(changes) > 100
    assert all(isinstance(c.path, str) for c in changes)
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m pytest tests/test_query_diff.py -v`
Expected: FAIL — `AttributeError: 'WingScene' object has no attribute 'diff'`

- [ ] **Step 3: Implement the differ**

`wing_parser/query/diff.py`:

```python
"""Field-by-field comparison of two scenes.

Walks the frozen records recursively rather than the raw JSON, so paths
read in decoded terms ("ch.8.fader_dB", "ch.8.eq.bands.2.gain") and
levels compare as dB with the sentinel already resolved.

One documented limitation. A record present in one scene and absent from
the other is reported as a single change whose `before` or `after` is the
whole record object, not as per-field changes. Adding or removing a
channel is one logical edit, and both consoles this parser targets carry
a fixed 40, so the case does not arise in practice — but a caller that
assumes every `Change` holds primitive leaves must handle it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, fields, is_dataclass
from typing import TYPE_CHECKING, Any

from wing_parser.core.normalizer import SENTINEL_MINUS_INF
from wing_parser.query.build_blocks import MATRIX_PREFIX

if TYPE_CHECKING:
    from wing_parser.query.scene import WingScene

# Raw payloads are excluded: eq.raw duplicates the decoded bands, so
# including it would report every EQ change twice.
SKIP_FIELDS = {"raw"}


@dataclass(frozen=True)
class Change:
    path: str
    before: Any
    after: Any
    magnitude: float | None


def _magnitude(before: Any, after: Any) -> float | None:
    """How far a numeric field moved.

    A level at -inf is a fader on its bottom stop, which the console
    writes as -144. Measuring the travel from there gives a real number
    for the largest change a mix can have — silent to audible — instead
    of dropping it to None and ranking it below a 1 dB trim.
    """
    if isinstance(before, bool) or isinstance(after, bool):
        return None
    if not isinstance(before, (int, float)) or not isinstance(after, (int, float)):
        return None

    left, right = float(before), float(after)
    if math.isinf(left) and math.isinf(right):
        return None                       # both silent: no travel
    left = float(SENTINEL_MINUS_INF) if math.isinf(left) else left
    right = float(SENTINEL_MINUS_INF) if math.isinf(right) else right
    return abs(right - left)


def _walk(path: str, before: Any, after: Any, out: list[Change]) -> None:
    if is_dataclass(before) and is_dataclass(after):
        for spec in fields(before):
            if spec.name in SKIP_FIELDS:
                continue
            _walk(
                f"{path}.{spec.name}",
                getattr(before, spec.name),
                getattr(after, spec.name),
                out,
            )
        return

    if isinstance(before, tuple) and isinstance(after, tuple):
        keyed_before = {_key(item, i): item for i, item in enumerate(before)}
        keyed_after = {_key(item, i): item for i, item in enumerate(after)}
        for key in sorted(set(keyed_before) | set(keyed_after), key=str):
            _walk(f"{path}.{key}", keyed_before.get(key), keyed_after.get(key), out)
        return

    if before != after:
        out.append(Change(path, before, after, _magnitude(before, after)))


def _key(item: Any, index: int) -> Any:
    """Match tuple entries by identity where they have one.

    A send's number is not unique on its own — bus 3 and MX3 both report
    dest 3 — so a send keys on the destination as the file itself spells
    it: "3" for bus 3, "MX3" for matrix 3. Those two forms cannot collide
    (buses are 1-16, matrices MX1-MX8), the key doubles as the path
    fragment, and a reader sees the same token the console wrote.
    """
    dest = getattr(item, "dest", None)
    if dest is not None:
        kind = getattr(item, "dest_kind", None)
        return f"{MATRIX_PREFIX}{dest}" if kind == "matrix" else str(dest)
    for attribute in ("name", "number"):
        value = getattr(item, attribute, None)
        if value is not None:
            return value
    return index


def compare(a: "WingScene", b: "WingScene") -> tuple[Change, ...]:
    changes: list[Change] = []

    left_channels, right_channels = a.channel_map(), b.channel_map()
    for number in sorted(set(left_channels) | set(right_channels)):
        left = left_channels.get(number)
        right = right_channels.get(number)
        _walk(
            f"ch.{number}",
            left.data if left else None,
            right.data if right else None,
            changes,
        )

    for kind in ("bus", "aux", "main", "matrix"):
        left_section = {v.number: v.data for v in a.family(kind).values()}
        right_section = {v.number: v.data for v in b.family(kind).values()}
        for number in sorted(set(left_section) | set(right_section)):
            _walk(
                f"{kind}.{number}",
                left_section.get(number),
                right_section.get(number),
                changes,
            )

    return tuple(changes)
```

`compare` reaches into two accessors that Task 11 left private. Add both to `WingScene` now, so the differ needs no underscore access:

```python
    def channel_map(self) -> dict[int, Channel]:
        return dict(self._channels)

    def family(self, kind: str) -> dict[int, Bus]:
        return dict(self._bus_family[kind])
```

and use `a.channel_map()` / `b.channel_map()` in the channel loop above in place of `a._channels`.

- [ ] **Step 4: Wire it into WingScene**

Add to the imports in `wing_parser/query/scene.py`:

```python
from wing_parser.query.diff import Change, compare
```

and add this method:

```python
    def diff(self, other: "WingScene") -> tuple[Change, ...]:
        return compare(self, other)
```

- [ ] **Step 5: Run the test and verify it passes**

Run: `python -m pytest tests/test_query_diff.py -v`
Expected: PASS — 7 tests

- [ ] **Step 6: Run the whole suite**

Run: `python -m pytest --cov=wing_parser.core --cov-report=term-missing`
Expected: all tests pass; `wing_parser/core` coverage at or above 80%.

- [ ] **Step 7: Commit**

```bash
git add wing_parser/query/diff.py wing_parser/query/scene.py tests/test_query_diff.py
git commit -m "Add scene diff over decoded records

Walking the records rather than the raw JSON means paths read in
decoded terms and levels compare as dB with the sentinel resolved.
eq.raw is skipped so EQ changes are not reported twice."
```

**Milestone 2.** A working query library: channels with source joins, bus family, group membership, scene-safe flags, routing, and diff.

---

## Task 14: Name normalization and the pattern matcher

**Files:**
- Create: `wing_parser/classifier/__init__.py`
- Create: `wing_parser/classifier/normalize.py`
- Create: `wing_parser/classifier/matcher.py`
- Create: `wing_parser/classifier/data/patterns.yaml`
- Test: `tests/test_classifier_matcher.py`

Channels and buses share one mechanism and one pattern file; only the pattern set differs. Splitting them would duplicate the scoring code for no reviewer benefit.

**Interfaces:**
- Consumes: nothing from earlier tasks
- Produces:
  - `wing_parser.classifier.normalize.clean(name: str) -> str` — trim, collapse internal whitespace, casefold
  - `wing_parser.classifier.matcher.Classification` — frozen dataclass `kind: str`, `confidence: float`, `origin: str`, `matched: str | None`
  - `wing_parser.classifier.matcher.UNKNOWN: Classification`
  - `wing_parser.classifier.matcher.HIGH: float = 0.8`, `.LOW: float = 0.4`
  - `wing_parser.classifier.matcher.classify(name: str, domain: str) -> Classification` — `domain` is `"channels"` or `"buses"`
  - `wing_parser.classifier.matcher.is_confident(c) -> bool`, `.is_usable(c) -> bool`

- [ ] **Step 1: Write the pattern data**

`wing_parser/classifier/data/patterns.yaml`:

```yaml
# Name -> source-type patterns.
#
# Every `match` is a regular expression applied to the normalized name
# (trimmed, whitespace-collapsed, casefolded). When several patterns hit,
# the highest confidence wins; ties break toward the longest matched
# substring, so "snare bot" beats "snare".
#
# Confidence bands (see spec section 4.3):
#   >= 0.8  classified, conditional rules run normally
#   >= 0.4  low confidence, findings are worded as questions
#   <  0.4  unknown, conditional rules skip the target

channels:
  # Drums
  - { match: 'kick\s*out',      kind: drums.kick.out,      confidence: 0.95 }
  - { match: 'kick\s*in',       kind: drums.kick.in,       confidence: 0.95 }
  - { match: 'kick',            kind: drums.kick,          confidence: 0.9 }
  - { match: 'snare\s*bot',     kind: drums.snare.bottom,  confidence: 0.95 }
  - { match: 'snare\s*top',     kind: drums.snare.top,     confidence: 0.95 }
  - { match: 'snare',           kind: drums.snare,         confidence: 0.9 }
  - { match: '\btom\b|\bfloor\b', kind: drums.tom,         confidence: 0.9 }
  - { match: 'hi\s*hat|\bhh\b', kind: drums.hihat,         confidence: 0.9 }
  - { match: '\boh\b|overhead', kind: drums.overhead,      confidence: 0.9 }
  - { match: '\bride\b',        kind: drums.ride,          confidence: 0.9 }
  - { match: '\bspd\b',         kind: drums.pad,           confidence: 0.75 }

  # Instruments
  - { match: '\bbass\b',        kind: instrument.bass,     confidence: 0.9 }
  - { match: 'a\.?\s*guitar|acoustic', kind: instrument.guitar.acoustic, confidence: 0.9 }
  - { match: 'e\.?\s*guitar|elec.*guit', kind: instrument.guitar.electric, confidence: 0.9 }
  - { match: '\bguitar\b|\bgtr\b', kind: instrument.guitar, confidence: 0.85 }
  - { match: '\bkey\b|\bkeys\b|piano', kind: instrument.keys, confidence: 0.9 }
  - { match: '\bstring',        kind: instrument.strings,  confidence: 0.85 }
  - { match: '\bhorn|\bsax\b|trumpet', kind: instrument.horns, confidence: 0.85 }

  # Voice
  - { match: '\bvox\b|\bvocal', kind: speech.vocal,        confidence: 0.9 }
  - { match: '\bmc\b',          kind: speech.mc,           confidence: 0.85 }
  - { match: 'lectern|podium|gooseneck', kind: speech.lectern, confidence: 0.9 }
  - { match: '\blav\b|lavalier', kind: speech.lav,         confidence: 0.9 }
  # \d* for the same reason as iem below: \bhs\b has no word boundary
  # between S and 4, so HS4 -- channel 11 in the real file -- never matched.
  - { match: 'head\s*set|\bhs\d*\b', kind: speech.headset,  confidence: 0.7 }
  - { match: 'hand\s*held',     kind: speech.handheld,     confidence: 0.85 }
  # More specific than drums.hihat's '\bhh\b' (0.9), so it must outrank it on
  # confidence — `_rank` settles confidence before it ever consults length.
  - { match: '\bhh\s*mic\b',    kind: speech.handheld,     confidence: 0.92 }

  # Non-performance
  - { match: '\bclick\b',       kind: utility.click,       confidence: 0.95 }
  - { match: 'playback|\bpb\b|\btracks?\b', kind: utility.playback, confidence: 0.9 }
  - { match: '\btalk\b|\btak\b|\btb\b', kind: utility.talkback, confidence: 0.8 }
  - { match: 'ambien|audience|\broom mic\b', kind: utility.ambient, confidence: 0.85 }
  - { match: '\bfx\b',          kind: utility.fx_return,   confidence: 0.8 }

  # Vietnamese
  - { match: 'd\.?\s*phoi|du\s*phong', kind: utility.spare, confidence: 0.85 }
  - { match: '\bspare\b|\bbackup\b', kind: utility.spare,  confidence: 0.9 }

  # Weak fallbacks — deliberately below the 0.8 gate.
  - { match: '^mic\s*\d+$',     kind: unknown.bare_mic,    confidence: 0.3 }
  - { match: '^m\d+$',          kind: unknown.bare_mic,    confidence: 0.3 }

buses:
  - { match: '^mon\b|monitor',  kind: monitor,             confidence: 0.9 }
  # \d* matters: there is no word boundary between M and 3, so a bare
  # \biem\b missed IEM1/IEM2/IEM3 -- the commonest way to number them.
  - { match: '\biem\d*\b|in\s*ear', kind: monitor,         confidence: 0.95 }
  - { match: 'wedge|side\s*fill|sidefill', kind: monitor,  confidence: 0.9 }
  # ToanAZ: "Side = sidefill speakers". A sidefill is a monitor -- the band
  # hears it, not the audience -- so a bus named SIDE is a monitor send.
  - { match: '^side\b',         kind: monitor,             confidence: 0.85 }
  - { match: '\bfx\b|reverb|delay|hall|room|chorus|haha', kind: fx, confidence: 0.85 }
  - { match: '\brec\b|record|multitrack', kind: record,    confidence: 0.9 }
  - { match: 'stream|broadcast|encoder|webcast', kind: stream, confidence: 0.9 }
  - { match: '\bfill\b|delay\s*ring|overflow|lobby', kind: matrix_fill, confidence: 0.85 }
  - { match: '\bsub\b|\blfe\b', kind: subgroup,            confidence: 0.85 }
  # ToanAZ: "TB = talkback". Engineer-to-stage, never part of the mix, so
  # level and mute rules that apply to programme material must skip it.
  - { match: '\btb\b|talk\s*back', kind: talkback,         confidence: 0.9 }
  # A bus feeding the house PA. Distinct from the console's main objects.
  - { match: 'main\s*foh|\bfoh\b|^main\b', kind: main,     confidence: 0.85 }
  # ToanAZ: "Flown = Flown Array speaker", "Cen = center speaker". These
  # are house loudspeaker zones fed from a bus, not fills -- matrix_fill
  # already means an actual fill (delay ring, lobby), so they get their
  # own role rather than being lumped in with it.
  - { match: 'flown|\bcen\b|^cent(er|re)\b|\barray\b', kind: pa_zone, confidence: 0.85 }
  # ToanAZ on a bus named HEADSET: "Headset co the la input headset mic,
  # hoac group all headset mic" -- either way it is input-side, so it
  # belongs with the source subgroups below, not with the monitor sends.
  # The monitor reading was wrong, not merely under-confident.
  - { match: 'head\s*set|\bstring', kind: subgroup,        confidence: 0.6 }
  - { match: '\bdrum\b|\bband\b|\bmic\b|\bmusic\b', kind: subgroup, confidence: 0.6 }
```

- [ ] **Step 2: Write the failing test**

`tests/test_classifier_matcher.py`:

```python
import pytest

from wing_parser import WingScene
from wing_parser.classifier.matcher import (
    HIGH,
    LOW,
    classify,
    is_confident,
    is_usable,
)
from wing_parser.classifier.normalize import clean


def test_clean_strips_trailing_space_and_casefolds():
    assert clean("Kick In ") == "kick in"
    assert clean("  A.Guitar  ") == "a.guitar"
    assert clean("MON  VOX") == "mon vox"
    assert clean("") == ""


def test_clean_collapses_internal_whitespace():
    assert clean("Snare\tTop") == "snare top"


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Kick In ", "drums.kick.in"),
        ("Kick Out", "drums.kick.out"),
        ("Snare Bot", "drums.snare.bottom"),
        ("Snare Top", "drums.snare.top"),
        ("Tom 8", "drums.tom"),
        ("Floor 16", "drums.tom"),
        ("Hihat", "drums.hihat"),
        ("OH", "drums.overhead"),
        ("Bass", "instrument.bass"),
        ("A.Guitar ", "instrument.guitar.acoustic"),
        ("E.Guitar 1", "instrument.guitar.electric"),
        ("Key 1", "instrument.keys"),
        ("Click", "utility.click"),
        ("LED PLAYBACK", "utility.playback"),
        ("BOH Talk", "utility.talkback"),
        ("FOH Tak", "utility.talkback"),          # typo in the real file
        ("Mic 1 VOX IEM1", "speech.vocal"),
        ("M8 MC", "speech.mc"),
        ("M6 D.PHOI", "utility.spare"),           # Vietnamese "du phong"
    ],
)
def test_real_channel_names_classify(name, expected):
    result = classify(name, "channels")
    assert result.kind == expected
    assert result.confidence >= HIGH, f"{name!r} scored {result.confidence}"


def test_more_specific_pattern_wins_on_a_tie():
    # "snare bot" and "snare" both match; the specific one must win.
    assert classify("Snare Bot", "channels").kind == "drums.snare.bottom"


def test_equal_confidence_is_broken_by_match_length():
    # "sub" and "fx" are both 0.85, so only len(matched) separates them.
    # This is the ONLY case that exercises _rank's length component --
    # "Snare Bot" above is decided on confidence alone (0.95 > 0.9) and
    # still passes with the length component removed.
    assert classify("SUB FX", "buses").kind == "subgroup"
    assert classify("FX SUB", "buses").kind == "subgroup"


def test_hh_mic_is_a_handheld_not_a_hihat():
    # drums.hihat matches '\bhh\b' at 0.9; the handheld entry must carry a
    # higher confidence to win, because length never gets consulted.
    assert classify("HH MIC", "channels").kind == "speech.handheld"
    assert classify("HH", "channels").kind == "drums.hihat"
    assert classify("Handheld 1", "channels").kind == "speech.handheld"


def test_bare_mic_names_land_below_the_confidence_gate():
    for name in ("Mic 4", "Mic 5", "Mic 7"):
        result = classify(name, "channels")
        assert result.confidence < HIGH
        assert is_confident(result) is False


def test_genuinely_unclassifiable_names_are_unknown():
    result = classify("My Lap", "channels")
    assert result.kind == "unknown"
    assert result.confidence == 0.0
    assert is_usable(result) is False


def test_empty_name_is_unknown():
    assert classify("", "channels").kind == "unknown"


def test_bus_roles():
    assert classify("MON VOX", "buses").kind == "monitor"
    assert classify("MON L", "buses").kind == "monitor"
    assert classify("SIDEFILL", "buses").kind == "monitor"
    assert classify("HALL", "buses").kind == "fx"
    assert classify("DRUM FX", "buses").kind == "fx"
    assert classify("HAHA", "buses").kind == "fx"


def test_confidence_helpers():
    high = classify("Kick In", "channels")
    assert is_confident(high) and is_usable(high)

    weak = classify("Mic 4", "channels")
    assert not is_confident(weak)
    assert is_usable(weak) is (weak.confidence >= LOW)


def test_origin_is_recorded():
    assert classify("Kick In", "channels").origin == "pattern"


def test_monitor_buses_in_the_real_file_are_all_found(vu_path):
    scene = WingScene.load(vu_path)
    monitor_numbers = {
        bus.number
        for bus in scene.buses()
        if classify(bus.name, "buses").kind == "monitor"
        and classify(bus.name, "buses").confidence >= HIGH
    }
    assert {8, 9, 10} <= monitor_numbers      # MON VOX, MON L, MON R


def test_fx_buses_in_the_real_file(vu_path):
    scene = WingScene.load(vu_path)
    fx_numbers = {
        bus.number for bus in scene.buses() if classify(bus.name, "buses").kind == "fx"
    }
    assert {11, 12, 13, 14, 15, 16} <= fx_numbers
```

- [ ] **Step 3: Run the test and verify it fails**

Run: `python -m pytest tests/test_classifier_matcher.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.classifier'`

- [ ] **Step 4: Implement name normalization**

Create an empty `wing_parser/classifier/__init__.py`, then `wing_parser/classifier/normalize.py`:

```python
"""Normalize a channel or bus name before matching.

Real scene files carry trailing spaces ("Kick In "), inconsistent case,
and tabs. Matching against the raw string would miss all of them.
"""

from __future__ import annotations

import re

_WHITESPACE = re.compile(r"\s+")


def clean(name: str) -> str:
    return _WHITESPACE.sub(" ", (name or "").strip()).casefold()
```

- [ ] **Step 5: Implement the matcher**

`wing_parser/classifier/matcher.py`:

```python
"""Pattern-based source-type and bus-role classification.

The file records only the name a human typed, so classification is a
guess. Every guess carries a confidence, and the caller decides what to
do with a weak one — the alternative, silently assuming, is how an
advisory tool starts producing confident nonsense.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from wing_parser.classifier.normalize import clean

HIGH = 0.8
LOW = 0.4

_DATA = Path(__file__).resolve().parent / "data" / "patterns.yaml"


@dataclass(frozen=True)
class Classification:
    kind: str
    confidence: float
    origin: str
    matched: str | None = None


UNKNOWN = Classification(kind="unknown", confidence=0.0, origin="none")


@lru_cache(maxsize=None)
def _compiled(domain: str) -> tuple[tuple[re.Pattern[str], str, float], ...]:
    doc = yaml.safe_load(_DATA.read_text(encoding="utf-8"))
    if domain not in doc:
        raise KeyError(f"no pattern set named {domain!r} in {_DATA}")
    return tuple(
        (re.compile(entry["match"]), entry["kind"], float(entry["confidence"]))
        for entry in doc[domain]
    )


def classify(name: str, domain: str) -> Classification:
    """Best match for a name. Ties break toward the longest matched text."""
    target = clean(name)
    if not target:
        return UNKNOWN

    best: Classification | None = None
    for pattern, kind, confidence in _compiled(domain):
        found = pattern.search(target)
        if found is None:
            continue
        candidate = Classification(
            kind=kind,
            confidence=confidence,
            origin="pattern",
            matched=found.group(0),
        )
        if best is None or _rank(candidate) > _rank(best):
            best = candidate

    return best or UNKNOWN


def _rank(c: Classification) -> tuple[float, int]:
    return (c.confidence, len(c.matched or ""))


def is_confident(c: Classification) -> bool:
    return c.confidence >= HIGH


def is_usable(c: Classification) -> bool:
    return c.confidence >= LOW
```

- [ ] **Step 6: Run the test and verify it passes**

Run: `python -m pytest tests/test_classifier_matcher.py -v`
Expected: PASS. The parametrised case covers 19 real channel names; if any pattern misses, widen that pattern in `patterns.yaml` rather than lowering the assertion.

- [ ] **Step 7: Commit**

```bash
git add wing_parser/classifier/ tests/test_classifier_matcher.py
git commit -m "Add name normalization and the pattern classifier

Channels and buses share one scoring path over one pattern file. Ties
break toward the longest match so 'snare bot' beats 'snare'. Bare names
like 'Mic 4' score deliberately below the 0.8 gate rather than being
guessed at, and 'M6 D.PHOI' is matched as a spare."
```

---

## Task 15: Knowledge directory and classification cache

**Files:**
- Create: `wing_parser/config.py`
- Create: `wing_parser/classifier/cache.py`
- Modify: `pyproject.toml` — add `"ruamel.yaml>=0.18"` to `dependencies`
- Create: `knowledge/toanaz/classifier.yaml`
- Create: `knowledge/toanaz/principles.yaml`
- Create: `knowledge/toanaz/shows/.gitkeep`
- Test: `tests/test_classifier_cache.py`

**Interfaces:**
- Consumes: `Classification` (Task 14)
- Produces:
  - `wing_parser.config.ENV_VAR: str = "WING_KNOWLEDGE_DIR"`
  - `wing_parser.config.SEARCH_ORDER: tuple[Path, ...]`
  - `wing_parser.config.knowledge_dir(override: Path | None = None) -> Path` — first existing location wins; falls back to the in-repo default
  - `wing_parser.classifier.cache.load(directory: Path | None = None) -> dict[str, dict[str, Classification]]` — outer key is the domain
  - `wing_parser.classifier.cache.lookup(name, domain, directory=None) -> Classification | None`
  - `wing_parser.classifier.cache.remember(name, domain, classification, directory=None) -> None`

- [ ] **Step 1: Write the seed knowledge files**

`knowledge/toanaz/classifier.yaml`:

```yaml
# Cached and manually declared classifications.
#
# Keys are normalized names (trimmed, whitespace-collapsed, casefolded).
# Anything written here is read before the pattern matcher runs, so a
# manual entry always wins and a name only ever costs one classification
# in its lifetime.
#
# Comments you add here survive every rewrite -- annotate freely.
#
# origin: manual | llm | pattern
channels: {}
buses: {}
```

This must stay byte-identical to `_SEED` in `cache.py` (Step 5) — the
module falls back to it when the file is absent.

`knowledge/toanaz/principles.yaml`:

```yaml
# ToanAZ's personal mixing principles.
#
# These override the generic base rules. hardness: hard applies always;
# hardness: flexible applies only when every applies_when condition
# matches. supersedes names the base rules switched off while active.
#
# The worked example below is real practice and deliberately contradicts
# base rule G8, which the knowledge base states as an absolute.
principles:
  - id: toanaz.iem-shared-band.guitar-prefader
    principle: "Shared band IEM: guitar sends pre-fader, all other sources post-fader"
    hardness: flexible
    applies_when:
      monitor_bus_count: 1
    supersedes: [G8]
    rationale: >
      The guitarist needs a stable guitar level regardless of FOH moves.
      Everything else should track the FOH balance so the band hears what
      the audience hears.
    source: "ToanAZ, field practice"
    enabled: false
```

`enabled: false` ships it dormant so the base rules are exercised out of the box; Task 19's test flips it on to prove `supersedes` works.

`knowledge/toanaz/shows/.gitkeep` is an empty file.

- [ ] **Step 2: Write the failing test**

`tests/test_classifier_cache.py`:

```python
import os
from pathlib import Path

import pytest
import yaml

from wing_parser import config
from wing_parser.classifier import cache
from wing_parser.classifier.matcher import Classification


@pytest.fixture
def knowledge(tmp_path: Path) -> Path:
    directory = tmp_path / "knowledge"
    directory.mkdir()
    (directory / "classifier.yaml").write_text(
        yaml.safe_dump({"channels": {}, "buses": {}}), encoding="utf-8"
    )
    return directory


def test_env_var_wins_over_every_other_location(tmp_path, monkeypatch):
    override = tmp_path / "elsewhere"
    override.mkdir()
    monkeypatch.setenv(config.ENV_VAR, str(override))
    assert config.knowledge_dir() == override


def test_repo_default_is_used_when_the_env_var_is_unset(monkeypatch):
    monkeypatch.delenv(config.ENV_VAR, raising=False)
    assert config.knowledge_dir().name == "toanaz"


def test_explicit_override_beats_the_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv(config.ENV_VAR, str(tmp_path / "ignored"))
    explicit = tmp_path / "explicit"
    explicit.mkdir()
    assert config.knowledge_dir(override=explicit) == explicit


def test_lookup_misses_on_an_empty_cache(knowledge):
    assert cache.lookup("Kick In", "channels", directory=knowledge) is None


def test_remember_then_lookup_round_trips(knowledge):
    entry = Classification(kind="utility.playback", confidence=0.8, origin="llm")
    cache.remember("My Lap", "channels", entry, directory=knowledge)

    found = cache.lookup("My Lap", "channels", directory=knowledge)
    assert found is not None
    assert found.kind == "utility.playback"
    assert found.confidence == pytest.approx(0.8)
    assert found.origin == "llm"


def test_lookup_is_insensitive_to_case_and_trailing_space(knowledge):
    cache.remember("Kick In ", "channels", Classification("drums.kick.in", 0.95, "manual"), directory=knowledge)
    assert cache.lookup("KICK IN", "channels", directory=knowledge) is not None
    assert cache.lookup("  kick in  ", "channels", directory=knowledge) is not None


def test_domains_do_not_collide(knowledge):
    cache.remember("MON VOX", "buses", Classification("monitor", 0.9, "manual"), directory=knowledge)
    assert cache.lookup("MON VOX", "channels", directory=knowledge) is None
    assert cache.lookup("MON VOX", "buses", directory=knowledge) is not None


def test_remember_persists_to_disk_in_readable_yaml(knowledge):
    cache.remember("My Lap", "channels", Classification("utility.playback", 0.8, "llm"), directory=knowledge)

    doc = yaml.safe_load((knowledge / "classifier.yaml").read_text(encoding="utf-8"))
    assert doc["channels"]["my lap"]["kind"] == "utility.playback"
    assert doc["channels"]["my lap"]["origin"] == "llm"


def test_missing_cache_file_is_created_on_first_write(tmp_path):
    empty = tmp_path / "fresh"
    empty.mkdir()
    cache.remember("Bass", "channels", Classification("instrument.bass", 0.9, "pattern"), directory=empty)
    assert (empty / "classifier.yaml").exists()


ANNOTATED = """\
# ToanAZ's own header. This must survive every write.
channels:
  kick in:            # judged by ear at the Hanoi show, do not re-guess
    kind: drums.kick.in
    confidence: 1.0
    origin: manual
buses: {}
"""


def test_writes_preserve_comments_the_human_wrote(tmp_path):
    directory = tmp_path / "annotated"
    directory.mkdir()
    target = directory / "classifier.yaml"
    target.write_text(ANNOTATED, encoding="utf-8")

    cache.remember("My Lap", "channels", Classification("utility.playback", 0.8, "llm"), directory=directory)
    after_one = target.read_text(encoding="utf-8")
    assert "ToanAZ's own header" in after_one
    assert "do not re-guess" in after_one

    # A second write must not erode what the first one preserved.
    cache.remember("MON VOX", "buses", Classification("monitor", 0.9, "pattern"), directory=directory)
    after_two = target.read_text(encoding="utf-8")
    assert "ToanAZ's own header" in after_two
    assert "do not re-guess" in after_two
    assert cache.lookup("Kick In", "channels", directory=directory).origin == "manual"
    assert cache.lookup("My Lap", "channels", directory=directory) is not None
    assert cache.lookup("MON VOX", "buses", directory=directory) is not None


def test_the_shipped_seed_file_matches_the_module_fallback():
    # cache.py falls back to _SEED when the file is absent; if the two
    # drift, a fresh checkout and a fresh install disagree on the format.
    shipped = (config.knowledge_dir() / "classifier.yaml").read_text(encoding="utf-8")
    assert shipped == cache._SEED


def test_a_hand_edited_entry_missing_a_key_names_the_file_and_the_key(tmp_path):
    directory = tmp_path / "broken"
    directory.mkdir()
    (directory / "classifier.yaml").write_text(
        "channels:\n  kick in:\n    origin: manual\nbuses: {}\n", encoding="utf-8"
    )
    with pytest.raises(ValueError) as excinfo:
        cache.load(directory=directory)

    message = str(excinfo.value)
    assert "classifier.yaml" in message
    assert "kick in" in message
    assert "kind" in message


@pytest.mark.parametrize(
    "body, expected",
    [
        ("- a\n- b\n", "top level"),
        ("just a string\n", "top level"),
        ("channels:\n  - kick\nbuses: {}\n", "channels"),
    ],
)
def test_a_structurally_broken_file_names_what_is_wrong(tmp_path, body, expected):
    # Same principle as the missing-key case: hand-editing this file is
    # the documented override path, so a damaged file must say what is
    # damaged rather than raising AttributeError from deep inside ruamel.
    directory = tmp_path / "wrecked"
    directory.mkdir()
    (directory / "classifier.yaml").write_text(body, encoding="utf-8")
    with pytest.raises(ValueError) as excinfo:
        cache.load(directory=directory)
    assert expected in str(excinfo.value)
    assert "classifier.yaml" in str(excinfo.value)


def test_a_failed_write_leaves_the_previous_file_intact(tmp_path, monkeypatch):
    directory = tmp_path / "atomic"
    directory.mkdir()
    target = directory / "classifier.yaml"
    cache.remember("Bass", "channels", Classification("instrument.bass", 0.9, "pattern"), directory=directory)
    before = target.read_text(encoding="utf-8")

    class Boom(Exception):
        pass

    def explode(self, data, stream):
        raise Boom("disk full")

    monkeypatch.setattr("ruamel.yaml.YAML.dump", explode)
    with pytest.raises(Boom):
        cache.remember("Kick In", "channels", Classification("drums.kick.in", 0.95, "pattern"), directory=directory)

    assert target.read_text(encoding="utf-8") == before
    assert cache.lookup("Bass", "channels", directory=directory) is not None
    leftovers = [p.name for p in directory.iterdir() if p.name != "classifier.yaml"]
    assert leftovers == [], f"temp files not cleaned up: {leftovers}"
```

- [ ] **Step 3: Run the test and verify it fails**

Run: `python -m pytest tests/test_classifier_cache.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.config'`

- [ ] **Step 4: Implement the knowledge-directory resolver**

`wing_parser/config.py`:

```python
"""Where ToanAZ's principles, cache and feedback log live.

First existing location wins. The in-repo default is deliberate: these
principles are a long-lived asset, and git history shows how the
judgement behind them evolved. Setting one environment variable moves
the whole set elsewhere with no code change.
"""

from __future__ import annotations

import os
from pathlib import Path

ENV_VAR = "WING_KNOWLEDGE_DIR"

_REPO_DEFAULT = Path(__file__).resolve().parent.parent / "knowledge" / "toanaz"

SEARCH_ORDER: tuple[Path, ...] = (
    _REPO_DEFAULT,
    Path.home() / ".config" / "wing-skill",
    Path.home() / "wing-skill",
)


def knowledge_dir(override: Path | None = None) -> Path:
    if override is not None:
        return Path(override)

    from_env = os.environ.get(ENV_VAR)
    if from_env:
        return Path(from_env)

    for candidate in SEARCH_ORDER:
        if candidate.is_dir():
            return candidate

    return _REPO_DEFAULT
```

- [ ] **Step 5: Implement the cache**

`wing_parser/classifier/cache.py`:

```python
"""Persist classifications so a name is only ever resolved once.

This is what turns the optional Claude fallback from a running cost into
a one-off: whatever resolves a name — pattern, model, or a human editing
the file — the answer lands here and every later run reads it offline.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from wing_parser import config
from wing_parser.classifier.matcher import Classification
from wing_parser.classifier.normalize import clean

FILENAME = "classifier.yaml"
DOMAINS = ("channels", "buses")

_SEED = """\
# Cached and manually declared classifications.
#
# Keys are normalized names (trimmed, whitespace-collapsed, casefolded).
# Anything written here is read before the pattern matcher runs, so a
# manual entry always wins and a name only ever costs one classification
# in its lifetime.
#
# Comments you add here survive every rewrite -- annotate freely.
#
# origin: manual | llm | pattern
channels: {}
buses: {}
"""


def _yaml() -> YAML:
    """Round-trip mode. safe_dump would erase every comment in the file."""
    engine = YAML()
    engine.preserve_quotes = True
    return engine


def _path(directory: Path | None) -> Path:
    return config.knowledge_dir(directory) / FILENAME


def _read(directory: Path | None) -> Any:
    """The live document, comments and all. Mutate and hand back to _write."""
    path = _path(directory)
    text = path.read_text(encoding="utf-8") if path.exists() else _SEED
    doc = _yaml().load(text)
    if doc is None:
        doc = _yaml().load(_SEED)
    if not hasattr(doc, "get"):
        raise ValueError(
            f"{path}: the top level must be a mapping with a channels: and a "
            f"buses: section, but this file's top level is "
            f"{type(doc).__name__}."
        )
    for domain in DOMAINS:
        if doc.get(domain) is None:
            doc[domain] = {}
        elif not hasattr(doc[domain], "items"):
            raise ValueError(
                f"{path}: section {domain}: must be a mapping of normalized "
                f"name to entry, but it is {type(doc[domain]).__name__}."
            )
    return doc


def _write(doc: Any, directory: Path | None) -> None:
    """Write via a sibling temp file and one atomic rename.

    This file is the durable record of every classification the tool has
    ever paid a model to make, and Task 17 rewrites it once per unresolved
    name. Truncating it in place means a crash mid-write loses the lot.
    """
    path = _path(directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    )
    try:
        with handle:
            _yaml().dump(doc, handle)
        os.replace(handle.name, path)
    except BaseException:
        Path(handle.name).unlink(missing_ok=True)
        raise


def _one(domain: str, key: str, entry: Any, path: Path) -> Classification:
    for required in ("kind", "confidence"):
        if required not in entry:
            raise ValueError(
                f"{path}: entry {domain}.{key!r} is missing required key "
                f"{required!r}. Each entry needs at least kind: and "
                f"confidence:, plus an optional origin: and matched:."
            )
    return Classification(
        kind=str(entry["kind"]),
        confidence=float(entry["confidence"]),
        origin=str(entry.get("origin", "cache")),
        matched=entry.get("matched"),
    )


def load(directory: Path | None = None) -> dict[str, dict[str, Classification]]:
    doc = _read(directory)
    path = _path(directory)
    return {
        domain: {
            key: _one(domain, key, entry, path)
            for key, entry in (doc.get(domain) or {}).items()
        }
        for domain in DOMAINS
    }


def lookup(name: str, domain: str, directory: Path | None = None) -> Classification | None:
    return load(directory).get(domain, {}).get(clean(name))


def remember(
    name: str,
    domain: str,
    classification: Classification,
    directory: Path | None = None,
) -> None:
    doc = _read(directory)
    if doc.get(domain) is None:
        doc[domain] = {}
    doc[domain][clean(name)] = {
        "kind": classification.kind,
        "confidence": round(float(classification.confidence), 3),
        "origin": classification.origin,
        "matched": classification.matched,
    }
    _write(doc, directory)
```

`ruamel.yaml` preserves insertion order rather than sorting, so new
entries append at the end. That is the better behaviour for a file a
human reads: every write produces an append-only diff instead of
reshuffling lines ToanAZ already reviewed.

- [ ] **Step 6: Run the test and verify it passes**

Run: `python -m pytest tests/test_classifier_cache.py -v`
Expected: PASS — 16 tests

- [ ] **Step 7: Commit**

```bash
git add pyproject.toml wing_parser/config.py wing_parser/classifier/cache.py knowledge/ tests/test_classifier_cache.py
git commit -m "Add knowledge-directory resolution and the classification cache

Search order is WING_KNOWLEDGE_DIR, then the in-repo default, then XDG,
then the mastering-engineer layout. Caching every resolved name is what
turns the optional model call into a one-off rather than a running cost.

The cache is written with ruamel.yaml in round-trip mode. This file is
both machine-written and hand-edited, and PyYAML drops comments at parse
time, so safe_dump would erase ToanAZ's own annotations on the first
write."
```

---

## Task 16: Optional Claude fallback

**Files:**
- Create: `wing_parser/classifier/llm.py`
- Test: `tests/test_classifier_llm.py`

**Interfaces:**
- Consumes: `Classification` (Task 14)
- Produces:
  - `wing_parser.classifier.llm.MODEL: str = "claude-opus-5"`
  - `wing_parser.classifier.llm.available() -> bool` — `True` only when the SDK imports **and** a key is present **and** `WING_DISABLE_LLM` is unset
  - `wing_parser.classifier.llm.classify(name: str, domain: str, context: str = "") -> Classification | None` — returns `None` on any failure; never raises

- [ ] **Step 1: Write the failing test**

`tests/test_classifier_llm.py`:

```python
import pytest

from wing_parser.classifier import llm


def test_unavailable_without_a_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("WING_DISABLE_LLM", raising=False)
    assert llm.available() is False


def test_explicit_disable_switch_wins_over_a_present_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    assert llm.available() is False


def test_classify_returns_none_when_unavailable(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert llm.classify("My Lap", "channels") is None


def test_classify_swallows_transport_errors(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.delenv("WING_DISABLE_LLM", raising=False)
    monkeypatch.setattr(llm, "available", lambda: True)

    def explode(*args, **kwargs):
        raise RuntimeError("network is down in the venue")

    monkeypatch.setattr(llm, "_ask", explode)
    assert llm.classify("My Lap", "channels") is None


def test_classify_maps_a_model_answer_onto_a_classification(monkeypatch):
    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(
        llm, "_ask", lambda name, domain, context: ("utility.playback", 0.82)
    )

    result = llm.classify("My Lap", "channels")
    assert result is not None
    assert result.kind == "utility.playback"
    assert result.confidence == pytest.approx(0.82)
    assert result.origin == "llm"


def test_confidence_is_clamped_into_range(monkeypatch):
    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(llm, "_ask", lambda *a: ("utility.playback", 4.0))
    assert llm.classify("My Lap", "channels").confidence == pytest.approx(1.0)

    monkeypatch.setattr(llm, "_ask", lambda *a: ("utility.playback", -1.0))
    assert llm.classify("My Lap", "channels").confidence == pytest.approx(0.0)


def test_model_is_opus_5():
    assert llm.MODEL == "claude-opus-5"


@pytest.mark.parametrize("value", ["0", "false", "no", "off", "", "  "])
def test_a_kill_switch_set_to_something_meaning_no_does_not_disable(monkeypatch, value):
    # Bare truthiness would read WING_DISABLE_LLM=0 as "disable", which is
    # the opposite of what anyone typing that expects.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv(llm.DISABLE_VAR, value)
    monkeypatch.setitem(sys.modules, "anthropic", types.ModuleType("anthropic"))
    assert llm.available() is True


@pytest.mark.parametrize("value", ["1", "true", "yes", "on", "anything"])
def test_a_kill_switch_set_to_anything_else_disables(monkeypatch, value):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv(llm.DISABLE_VAR, value)
    monkeypatch.setitem(sys.modules, "anthropic", types.ModuleType("anthropic"))
    assert llm.available() is False


@pytest.mark.parametrize("bad", [None, "high", object()])
def test_a_non_numeric_confidence_degrades_instead_of_raising(monkeypatch, bad):
    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(llm, "_ask", lambda *a: ("utility.playback", bad))
    assert llm.classify("My Lap", "channels") is None


@pytest.mark.parametrize("kind", ["unknown", "Unknown", "UNKNOWN", " unknown ", "\tUnKnOwN"])
def test_a_refusal_is_caught_whatever_its_casing(monkeypatch, kind):
    # A capitalised "Unknown" that slipped through became a Classification,
    # and Task 17 would have cached it as a real answer.
    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(llm, "_ask", lambda *a: (kind, 0.0))
    assert llm.classify("HS4", "channels") is None


def test_a_kind_is_normalized_to_the_lowercase_taxonomy(monkeypatch):
    # patterns.yaml kinds are lowercase dotted; a model answering
    # "Utility.Playback" must not become a kind no rule can ever match.
    monkeypatch.setattr(llm, "available", lambda: True)
    monkeypatch.setattr(llm, "_ask", lambda *a: ("  Utility.Playback  ", 0.8))
    assert llm.classify("My Lap", "channels").kind == "utility.playback"
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m pytest tests/test_classifier_llm.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.classifier.llm'`

- [ ] **Step 3: Implement the fallback**

`wing_parser/classifier/llm.py`:

```python
"""Optional Claude fallback for names the pattern matcher cannot resolve.

This is the only place in the system where a model participates. The
parser and the rule engine stay deterministic; a model here only turns
one ambiguous human-typed string into a typed guess, and the answer is
cached so it is asked at most once per name.

Every failure path returns None. This tool is used in venues where the
network is unreliable or absent, so an unreachable API must degrade to
"unknown", never to an exception. That covers a safety refusal too:
claude-opus-5 can answer with stop_reason "refusal" and no parsed
output, which surfaces here as an exception and lands on the same
"unknown" path as a dead uplink.
"""

from __future__ import annotations

import os

from wing_parser.classifier.matcher import Classification

MODEL = "claude-opus-5"
DISABLE_VAR = "WING_DISABLE_LLM"

_PROMPT = """You are labelling a mixing-console scene file.

A {domain_word} on a Behringer WING is named: {name!r}
{context}
Reply with the source type and how confident you are.

Use one of these kinds where it fits, or coin a similar dotted kind:
  drums.kick, drums.snare.top, drums.snare.bottom, drums.tom,
  drums.hihat, drums.overhead, instrument.bass, instrument.guitar.acoustic,
  instrument.guitar.electric, instrument.keys, speech.vocal, speech.mc,
  speech.lectern, speech.lav, speech.headset, speech.handheld,
  utility.click, utility.playback, utility.talkback, utility.ambient,
  utility.spare, utility.fx_return
For a bus, use one of: monitor, fx, subgroup, record, stream, matrix_fill.

Engineers abbreviate heavily and sometimes write in languages other than
English. If the name is genuinely uninformative, answer "unknown" with a
confidence of 0. Do not guess to be helpful.
"""

_DOMAIN_WORD = {"channels": "channel", "buses": "bus"}


_OFF = {"", "0", "false", "no", "off"}


def _kill_switch_thrown() -> bool:
    """True unless the variable is unset or set to something meaning "no".

    Bare truthiness would make WING_DISABLE_LLM=0 disable the fallback,
    which is the opposite of what anyone typing that expects.
    """
    return os.environ.get(DISABLE_VAR, "").strip().casefold() not in _OFF


def available() -> bool:
    if _kill_switch_thrown():
        return False
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return False
    try:
        import anthropic  # noqa: F401
    except ImportError:
        return False
    return True


def _ask(name: str, domain: str, context: str) -> tuple[str, float]:
    """Single API call. Split out so tests can replace it."""
    import anthropic
    from pydantic import BaseModel, Field

    class SourceGuess(BaseModel):
        kind: str = Field(description="dotted source type, or 'unknown'")
        confidence: float = Field(description="0.0 to 1.0")

    client = anthropic.Anthropic()
    response = client.messages.parse(
        model=MODEL,
        # Headroom, not appetite. On claude-opus-5 thinking is ON by default
        # -- unlike opus-4-8, where omitting the parameter meant no thinking
        # -- and max_tokens caps thinking PLUS the reply. The answer here is
        # two short fields, but 1024 would truncate the moment the model
        # thinks first, and classify() swallows the resulting exception into
        # a silent None. Overshooting costs nothing: billing is per token
        # emitted, not per token allowed.
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": _PROMPT.format(
                    domain_word=_DOMAIN_WORD.get(domain, "channel"),
                    name=name,
                    context=f"{context}\n" if context else "",
                ),
            }
        ],
        output_format=SourceGuess,
    )
    guess = response.parsed_output
    return guess.kind, guess.confidence


def classify(name: str, domain: str, context: str = "") -> Classification | None:
    if not available():
        return None
    try:
        kind, confidence = _ask(name, domain, context)
        # Coercion belongs inside the guard. A model that answers with a
        # confidence of "high" instead of 0.9 must land on the same
        # "unknown" path as a dead uplink -- float() would otherwise raise
        # straight through the promise this module makes.
        kind = str(kind).strip().casefold()
        score = min(1.0, max(0.0, float(confidence)))
    except Exception:            # noqa: BLE001 - offline must never raise
        return None
    # casefold above is what makes this catch "Unknown" and "UNKNOWN" too.
    # Without it a capitalised refusal became a Classification, and Task 17
    # would have written it into the knowledge file as a real answer.
    if not kind or kind == "unknown":
        return None
    return Classification(kind=kind, confidence=score, origin="llm")
```

- [ ] **Step 4: Run the test and verify it passes**

Run: `python -m pytest tests/test_classifier_llm.py -v`
Expected: PASS — 26 tests (7 base + 19 parametrized cases). No test makes a real API call.

- [ ] **Step 5: Commit**

```bash
git add wing_parser/classifier/llm.py tests/test_classifier_llm.py
git commit -m "Add the optional Claude classifier fallback

The only model call in the system, and only for names the pattern
matcher cannot resolve. Every failure path returns None: this runs in
venues where the network is absent, so an unreachable API degrades to
'unknown' rather than raising."
```

---

## Task 17: Wire classification into the scene

**Files:**
- Create: `wing_parser/classifier/resolve.py`
- Modify: `wing_parser/query/scene.py`
- Modify: `wing_parser/query/channel.py`
- Modify: `wing_parser/query/bus.py`
- Test: `tests/test_classifier_resolve.py`

**Interfaces:**
- Consumes: `matcher` (Task 14), `cache` (Task 15), `llm` (Task 16)
- Produces:
  - `wing_parser.classifier.resolve.Classifier` — `Classifier(directory=None, use_llm=True)`; methods `resolve(name, domain) -> Classification`, `flush() -> None`; properties `unresolved: tuple[str, ...]`, `low_confidence: tuple[str, ...]`
  - New on `WingScene`: `.classifier` (a `Classifier`), `.unclassified() -> tuple[Channel | Bus, ...]`
  - New on `Channel`: `.source_type -> Classification`
  - New on `Bus`: `.role -> Classification`, `.is_monitor -> bool`

- [ ] **Step 1: Write the failing test**

`tests/test_classifier_resolve.py`:

```python
import pytest
import yaml

from wing_parser import WingScene
from wing_parser.classifier.matcher import HIGH, Classification
from wing_parser.classifier.resolve import Classifier


@pytest.fixture
def knowledge(tmp_path):
    directory = tmp_path / "knowledge"
    directory.mkdir()
    (directory / "classifier.yaml").write_text(
        yaml.safe_dump({"channels": {}, "buses": {}}), encoding="utf-8"
    )
    return directory


def test_pattern_hit_is_returned(knowledge):
    result = Classifier(directory=knowledge, use_llm=False).resolve("Kick In ", "channels")
    assert result.kind == "drums.kick.in"
    assert result.origin == "pattern"


def test_cache_entry_beats_the_pattern_matcher(knowledge):
    from wing_parser.classifier import cache

    cache.remember(
        "Kick In ", "channels",
        Classification("drums.kick.trigger", 1.0, "manual"),
        directory=knowledge,
    )
    result = Classifier(directory=knowledge, use_llm=False).resolve("Kick In", "channels")
    assert result.kind == "drums.kick.trigger"
    assert result.origin == "manual"


def test_unresolvable_name_is_unknown_with_llm_off(knowledge):
    classifier = Classifier(directory=knowledge, use_llm=False)
    assert classifier.resolve("My Lap", "channels").kind == "unknown"
    assert "My Lap" in classifier.unresolved


def test_weak_match_is_recorded_as_low_confidence(knowledge):
    classifier = Classifier(directory=knowledge, use_llm=False)
    result = classifier.resolve("Mic 4", "channels")
    assert result.confidence < HIGH
    assert "Mic 4" in classifier.low_confidence


def test_llm_is_consulted_only_below_the_gate(knowledge, monkeypatch):
    calls: list[str] = []

    def fake(name, domain, context=""):
        calls.append(name)
        return Classification("utility.playback", 0.82, "llm")

    monkeypatch.setattr("wing_parser.classifier.resolve.llm.available", lambda: True)
    monkeypatch.setattr("wing_parser.classifier.resolve.llm.classify", fake)

    classifier = Classifier(directory=knowledge, use_llm=True)
    classifier.resolve("Kick In", "channels")      # confident pattern hit
    classifier.resolve("My Lap", "channels")       # nothing matches

    assert calls == ["My Lap"]


def test_llm_answer_is_flushed_to_the_cache(knowledge, monkeypatch):
    monkeypatch.setattr("wing_parser.classifier.resolve.llm.available", lambda: True)
    monkeypatch.setattr(
        "wing_parser.classifier.resolve.llm.classify",
        lambda name, domain, context="": Classification("utility.playback", 0.82, "llm"),
    )

    classifier = Classifier(directory=knowledge, use_llm=True)
    classifier.resolve("My Lap", "channels")
    classifier.flush()

    doc = yaml.safe_load((knowledge / "classifier.yaml").read_text(encoding="utf-8"))
    assert doc["channels"]["my lap"]["origin"] == "llm"


def test_resolution_is_memoised_within_one_classifier(knowledge, monkeypatch):
    calls: list[str] = []
    monkeypatch.setattr("wing_parser.classifier.resolve.llm.available", lambda: True)
    monkeypatch.setattr(
        "wing_parser.classifier.resolve.llm.classify",
        lambda name, domain, context="": (calls.append(name), Classification("x", 0.9, "llm"))[1],
    )

    classifier = Classifier(directory=knowledge, use_llm=True)
    classifier.resolve("My Lap", "channels")
    classifier.resolve("My Lap", "channels")
    assert len(calls) == 1


def test_scene_exposes_source_type_and_bus_role(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    scene = WingScene.load(vu_path)

    assert scene.channel(8).source_type.kind == "speech.mc"
    assert scene.channel(13).source_type.kind == "drums.kick.in"
    assert scene.bus(8).role.kind == "monitor"
    assert scene.bus(8).is_monitor is True
    assert scene.bus(12).is_monitor is False        # HALL is an fx bus


def test_monitor_buses_in_the_real_file(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    scene = WingScene.load(vu_path)
    monitors = {bus.number for bus in scene.buses() if bus.is_monitor}
    assert {8, 9, 10} <= monitors


def test_unclassified_channels_are_listed_not_dropped(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    scene = WingScene.load(vu_path)
    names = {view.name for view in scene.unclassified()}
    assert "My Lap" in names
    assert "Kick In " not in names


def test_offline_run_still_classifies_by_pattern(vu_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    scene = WingScene.load(vu_path)
    assert scene.bus(8).is_monitor is True          # MON VOX resolves offline


def test_a_blank_name_costs_nothing_and_is_not_a_naming_problem(knowledge, monkeypatch):
    # Six channels in the real file are unnamed. An empty slot is not a
    # name that needs improving, and it must never reach the model.
    called: list[str] = []
    monkeypatch.setattr("wing_parser.classifier.resolve.llm.available", lambda: True)
    monkeypatch.setattr(
        "wing_parser.classifier.resolve.llm.classify",
        lambda name, domain, context="": called.append(name) or Classification("x", 0.9, "llm"),
    )

    classifier = Classifier(directory=knowledge, use_llm=True)
    for blank in ("", "   ", "\t"):
        assert classifier.resolve(blank, "channels").kind == "unknown"

    assert called == []
    assert classifier.unresolved == ()
    assert classifier.low_confidence == ()


def test_the_knowledge_file_is_read_once_not_once_per_name(knowledge, monkeypatch):
    # cache.lookup() re-parses the whole file per call, and since Task 15
    # that parse is a ruamel round-trip. Measured on a 200-entry cache:
    # 50 per-name lookups took 3.4 s against 65 ms for one load. The file
    # grows one entry per name ever seen, so per-name reads get slower
    # exactly as the tool gets used.
    from wing_parser.classifier import resolve as resolve_module

    loads: list[object] = []
    real_load = resolve_module.cache.load

    def counted(directory=None):
        loads.append(directory)
        return real_load(directory)

    monkeypatch.setattr(resolve_module.cache, "load", counted)

    classifier = Classifier(directory=knowledge, use_llm=False)
    for name in ("Kick In", "Snare Top", "My Lap", "HS4", "MON VOX"):
        classifier.resolve(name, "channels")

    assert len(loads) == 1


def test_a_classifier_nobody_asks_touches_no_disk(monkeypatch):
    # WingScene builds one unconditionally, including for scenes the
    # caller only wants routing or levels from.
    from wing_parser.classifier import resolve as resolve_module

    def explode(directory=None):
        raise AssertionError("the knowledge file was read on construction")

    monkeypatch.setattr(resolve_module.cache, "load", explode)
    Classifier(directory=None, use_llm=False)       # must not raise
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m pytest tests/test_classifier_resolve.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.classifier.resolve'`

- [ ] **Step 3: Implement the resolver**

`wing_parser/classifier/resolve.py`:

```python
"""Resolution order: cache, then patterns, then the optional model.

Holding the cache in memory and flushing once keeps a parse from writing
to disk 40 times. Names that stay unresolved are collected rather than
discarded, so the report can say "these need better names" instead of
silently skipping them.
"""

from __future__ import annotations

from pathlib import Path

from wing_parser.classifier import cache, llm, matcher
from wing_parser.classifier.matcher import UNKNOWN, Classification
from wing_parser.classifier.normalize import clean


class Classifier:
    def __init__(self, directory: Path | None = None, use_llm: bool = True) -> None:
        self._directory = directory
        self._use_llm = use_llm
        self._memo: dict[tuple[str, str], Classification] = {}
        self._pending: list[tuple[str, str, Classification]] = []
        self._unresolved: list[str] = []
        self._low: list[str] = []
        # Loaded on first use, not here: WingScene builds a Classifier
        # unconditionally, and a scene nobody asks about types for should
        # not touch the disk at all.
        self._disk: dict[str, dict[str, Classification]] | None = None

    def _cached(self, name: str, domain: str) -> Classification | None:
        """One read of the knowledge file per Classifier, not per name.

        cache.lookup() re-reads and re-parses the whole file on every
        call, and since Task 15 that parse is a ruamel round-trip that
        rebuilds the comment tree. Measured on a 200-entry cache: 50
        per-name lookups took 3.4 s, one load plus 50 in-memory lookups
        took 65 ms. The file is designed to grow one entry per name ever
        seen, so the per-name version gets slower exactly as ToanAZ uses
        the tool more -- 17 s at a thousand entries.
        """
        if self._disk is None:
            self._disk = cache.load(self._directory)
        return self._disk.get(domain, {}).get(clean(name))

    def resolve(self, name: str, domain: str) -> Classification:
        target = clean(name)
        # An unnamed channel is an empty slot, not a naming problem. Without
        # this, all six blank channels in the real file would land in
        # `unresolved` as an empty string, and the first one would spend a
        # model call asking what "" is.
        if not target:
            return UNKNOWN

        key = (domain, target)
        if key in self._memo:
            return self._memo[key]

        result = self._first_answer(name, domain)
        self._memo[key] = result

        if result.confidence == 0.0:
            self._unresolved.append(name)
        elif not matcher.is_confident(result):
            self._low.append(name)

        return result

    def _first_answer(self, name: str, domain: str) -> Classification:
        cached = self._cached(name, domain)
        if cached is not None:
            return cached

        found = matcher.classify(name, domain)
        if matcher.is_confident(found):
            return found

        if self._use_llm and llm.available():
            guessed = llm.classify(name, domain)
            if guessed is not None:
                self._pending.append((name, domain, guessed))
                return guessed

        # A weak pattern hit still beats nothing: `found` is already UNKNOWN
        # when nothing matched, so returning it covers both cases.
        return found

    def flush(self) -> None:
        for name, domain, result in self._pending:
            cache.remember(name, domain, result, directory=self._directory)
        self._pending.clear()
        # The in-memory copy is now behind the file. Drop it rather than
        # patch it, so the next read is honest.
        self._disk = None

    @property
    def unresolved(self) -> tuple[str, ...]:
        return tuple(self._unresolved)

    @property
    def low_confidence(self) -> tuple[str, ...]:
        return tuple(self._low)
```

- [ ] **Step 4: Expose it on the views**

Add to `wing_parser/query/channel.py`:

```python
from wing_parser.classifier.matcher import Classification
```

and this property:

```python
    @property
    def source_type(self) -> Classification:
        return self._scene.classifier.resolve(self.data.name, "channels")
```

Add to `wing_parser/query/bus.py`:

```python
from wing_parser.classifier.matcher import Classification, is_confident
```

and these properties:

```python
    @property
    def role(self) -> Classification:
        return self._scene.classifier.resolve(self.data.name, "buses")

    @property
    def is_monitor(self) -> bool:
        found = self.role
        return found.kind == "monitor" and is_confident(found)
```

- [ ] **Step 5: Expose it on WingScene**

Add to the imports in `wing_parser/query/scene.py`:

```python
from wing_parser.classifier.resolve import Classifier
```

At the end of `__init__`:

```python
        self.classifier = Classifier()
```

and add:

```python
    def unclassified(self) -> tuple:
        """Named channels and buses whose type could not be determined."""
        found = []
        for view in self.channels():
            if view.name.strip() and view.source_type.confidence == 0.0:
                found.append(view)
        for view in self.bus_family():
            if view.name.strip() and view.role.confidence == 0.0:
                found.append(view)
        return tuple(found)
```

- [ ] **Step 6: Run the test and verify it passes**

Run: `python -m pytest tests/test_classifier_resolve.py -v`
Expected: PASS — 14 tests. `test_offline_run_still_classifies_by_pattern` is the offline guarantee: with no API key, `MON VOX` still resolves by pattern.

- [ ] **Step 7: Run the whole suite**

Run: `python -m pytest -q`
Expected: everything passes.

- [ ] **Step 8: Commit**

```bash
git add wing_parser/classifier/resolve.py wing_parser/query/ tests/test_classifier_resolve.py
git commit -m "Resolve source types and bus roles on the scene views

Order is cache, patterns, then the optional model, memoised per scene
and flushed once. Names that stay unresolved are collected so the report
can name them rather than silently skipping the channel."
```

**Milestone 3.** Channels carry a source type and buses carry a role, both with confidence, cached, and working with no network.

---

## Task 18: Rule model, loader, and predicates

**Files:**
- Create: `wing_parser/advisory/__init__.py`
- Create: `wing_parser/advisory/models.py`
- Create: `wing_parser/advisory/predicates.py`
- Create: `wing_parser/advisory/loader.py`
- Test: `tests/test_advisory_predicates.py`

**Interfaces:**
- Consumes: `Classification` (Task 14)
- Produces:
  - `wing_parser.advisory.models.Finding` — frozen dataclass `rule_id: str`, `layer: str`, `severity: str`, `target: str`, `message: str`, `evidence: dict[str, Any]`, `confidence: float`
  - `wing_parser.advisory.models.Rule` — frozen dataclass `id`, `title`, `severity`, `source`, `rationale`, `requires_classifier: bool`, `for_each: str`, `where: dict`, `message: str`, `layer: str`, `enabled: bool`, `applies_when: dict`, `supersedes: tuple[str, ...]`, `hardness: str`
  - `wing_parser.advisory.models.SEVERITIES: tuple[str, ...] = ("info", "warning", "error")`
  - `wing_parser.advisory.predicates.resolve_path(context: dict, path: str) -> Any`
  - `wing_parser.advisory.predicates.matches(value: Any, expected: Any) -> bool`
  - `wing_parser.advisory.predicates.all_match(context: dict, where: dict) -> bool`
  - `wing_parser.advisory.predicates.render(template: str, context: dict) -> str`
  - `wing_parser.advisory.loader.load_rules(path: Path, layer: str) -> list[Rule]`
  - `wing_parser.advisory.loader.load_base_rules() -> list[Rule]`

- [ ] **Step 1: Write the failing test**

`tests/test_advisory_predicates.py`:

```python
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from wing_parser.advisory.loader import load_base_rules, load_rules
from wing_parser.advisory.predicates import all_match, matches, render, resolve_path
from wing_parser.classifier.matcher import Classification


@dataclass
class Leaf:
    on: bool = True
    model: str = "COMP"
    role: Classification = Classification("monitor", 0.9, "pattern")


@dataclass
class Node:
    number: int = 8
    name: str = "M8 MC"
    child: Leaf = None


@pytest.fixture
def context():
    return {"channel": Node(child=Leaf()), "send": Leaf(model="POST")}


def test_resolve_path_walks_attributes(context):
    assert resolve_path(context, "channel.number") == 8
    assert resolve_path(context, "channel.child.model") == "COMP"


def test_resolve_path_unwraps_a_classification_to_its_kind(context):
    assert resolve_path(context, "channel.child.role") == "monitor"


def test_resolve_path_returns_none_for_a_missing_branch(context):
    assert resolve_path(context, "channel.nope.deeper") is None


def test_scalar_expectation_is_equality():
    assert matches("POST", "POST") is True
    assert matches("TAP", "POST") is False
    assert matches(True, True) is True


def test_not_operator():
    assert matches("COMP", {"not": "LIM"}) is True
    assert matches("LIM", {"not": "LIM"}) is False


def test_in_and_not_in_operators():
    assert matches("COMP", {"in": ["COMP", "CMB"]}) is True
    assert matches("LIM", {"in": ["COMP", "CMB"]}) is False
    assert matches("LIM", {"not_in": ["COMP", "CMB"]}) is True


def test_numeric_operators():
    assert matches(-9.0, {"lt": -6.0}) is True
    assert matches(-3.0, {"lt": -6.0}) is False
    assert matches(12.0, {"gt": 6.0}) is True
    assert matches(None, {"gt": 6.0}) is False


def test_is_null_operator():
    assert matches(None, {"is_null": True}) is True
    assert matches("x", {"is_null": True}) is False
    assert matches("x", {"is_null": False}) is True


def test_all_match_requires_every_key(context):
    assert all_match(context, {"channel.number": 8, "send.model": "POST"}) is True
    assert all_match(context, {"channel.number": 8, "send.model": "TAP"}) is False


def test_all_match_on_an_empty_where_is_true(context):
    assert all_match(context, {}) is True


def test_render_substitutes_from_the_context(context):
    text = render("Channel {channel.number} ({channel.name}) is wrong", context)
    assert text == "Channel 8 (M8 MC) is wrong"


def test_render_leaves_an_unresolvable_token_visible(context):
    assert "{channel.missing}" in render("x {channel.missing} y", context)


def test_load_rules_reads_every_documented_field(tmp_path: Path):
    path = tmp_path / "r.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "rules": [
                    {
                        "id": "T1",
                        "title": "Test rule",
                        "severity": "warning",
                        "source": "somewhere",
                        "rationale": "because",
                        "requires_classifier": True,
                        "when": {"for_each": "channel", "where": {"muted": True}},
                        "message": "Channel {channel.number} is muted",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    rule = load_rules(path, layer="base")[0]
    assert rule.id == "T1"
    assert rule.layer == "base"
    assert rule.severity == "warning"
    assert rule.requires_classifier is True
    assert rule.for_each == "channel"
    assert rule.where == {"muted": True}
    assert rule.enabled is True


def test_an_explicit_null_optional_field_falls_back_to_its_default(tmp_path: Path):
    """`enabled:` with the value left off must not disable the rule."""
    path = tmp_path / "null.yaml"
    path.write_text(
        "rules:\n"
        "  - id: T4\n"
        "    title: t\n"
        "    severity: warning\n"
        "    source: s\n"
        "    rationale: r\n"
        "    enabled:\n"
        "    hardness:\n"
        "    when:\n"
        "      for_each: channel\n"
        "      where: {}\n"
        "    message: m\n",
        encoding="utf-8",
    )
    rule = load_rules(path, layer="base")[0]
    assert rule.enabled is True
    assert rule.hardness == "hard"


def test_an_explicit_false_still_disables_the_rule(tmp_path: Path):
    """The null fallback must not swallow a deliberate `enabled: false`."""
    path = tmp_path / "off.yaml"
    path.write_text(
        yaml.safe_dump(
            {"rules": [{"id": "T5", "title": "t", "severity": "warning",
                        "source": "s", "rationale": "r", "enabled": False,
                        "when": {"for_each": "channel", "where": {}},
                        "message": "m"}]}
        ),
        encoding="utf-8",
    )
    assert load_rules(path, layer="base")[0].enabled is False


def test_loader_rejects_an_unknown_severity(tmp_path: Path):
    path = tmp_path / "bad.yaml"
    path.write_text(
        yaml.safe_dump(
            {"rules": [{"id": "T2", "title": "t", "severity": "catastrophe",
                        "source": "s", "rationale": "r",
                        "when": {"for_each": "channel", "where": {}},
                        "message": "m"}]}
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="severity"):
        load_rules(path, layer="base")


def test_loader_requires_source_and_rationale(tmp_path: Path):
    path = tmp_path / "nosource.yaml"
    path.write_text(
        yaml.safe_dump(
            {"rules": [{"id": "T3", "title": "t", "severity": "warning",
                        "when": {"for_each": "channel", "where": {}},
                        "message": "m"}]}
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="source"):
        load_rules(path, layer="base")


def test_base_rules_load_from_the_package():
    rules = load_base_rules()
    assert {r.id for r in rules} == {"G8", "G7", "E6"}
    assert all(r.layer == "base" for r in rules)
    assert all(r.source and r.rationale for r in rules)
```

The last test depends on the rule files created in Task 20. Expect it to fail until then; every other test in this file must pass at the end of this task.

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m pytest tests/test_advisory_predicates.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.advisory'`

- [ ] **Step 3: Implement the models**

Create an empty `wing_parser/advisory/__init__.py`, then `wing_parser/advisory/models.py`:

```python
"""Rule and Finding records."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

SEVERITIES: tuple[str, ...] = ("info", "warning", "error")
LAYERS: tuple[str, ...] = ("base", "toanaz", "show")


@dataclass(frozen=True)
class Rule:
    id: str
    title: str
    severity: str
    source: str
    rationale: str
    for_each: str
    where: dict[str, Any]
    message: str
    layer: str
    requires_classifier: bool = False
    enabled: bool = True
    hardness: str = "hard"
    applies_when: dict[str, Any] = field(default_factory=dict)
    supersedes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Finding:
    rule_id: str
    layer: str
    severity: str
    target: str
    message: str
    evidence: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
```

- [ ] **Step 4: Implement the predicates**

`wing_parser/advisory/predicates.py`:

```python
"""The small predicate language rule YAML is written in.

Deliberately small. A rule file should read like a statement about the
console, not like code, and anything that needs real logic belongs in a
Python rule rather than a bigger DSL.
"""

from __future__ import annotations

from string import Formatter
from typing import Any

from wing_parser.classifier.matcher import Classification

_MISSING = object()

# Every operator key `matches()` understands inside a `where` value's
# dict form, e.g. `{"gt": 6.0}`. The loader validates a rule's `where`
# against this set at load time, so an unknown operator is a clean error
# naming the file rather than a `ValueError` raised from mid-run.
OPERATORS: frozenset[str] = frozenset({"not", "in", "not_in", "gt", "lt", "is_null"})


def resolve_path(context: dict[str, Any], path: str) -> Any:
    """Walk a dotted path. A Classification unwraps to its kind."""
    current: Any = context
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part, _MISSING)
        else:
            current = getattr(current, part, _MISSING)
        if current is _MISSING:
            return None
    if isinstance(current, Classification):
        return current.kind
    return current


def matches(value: Any, expected: Any) -> bool:
    if not isinstance(expected, dict):
        return value == expected

    for operator, operand in expected.items():
        if operator == "not":
            if value == operand:
                return False
        elif operator == "in":
            if value not in operand:
                return False
        elif operator == "not_in":
            if value in operand:
                return False
        elif operator == "gt":
            if not isinstance(value, (int, float)) or not value > operand:
                return False
        elif operator == "lt":
            if not isinstance(value, (int, float)) or not value < operand:
                return False
        elif operator == "is_null":
            if (value is None) is not bool(operand):
                return False
        else:
            raise ValueError(
                f"unknown predicate operator {operator!r}; expected one of "
                f"{sorted(OPERATORS)}"
            )
    return True


def all_match(context: dict[str, Any], where: dict[str, Any]) -> bool:
    return all(matches(resolve_path(context, path), expected) for path, expected in where.items())


def render(template: str, context: dict[str, Any]) -> str:
    """Fill {dotted.path} tokens. An unresolvable token is left visible."""
    out: list[str] = []
    for literal, field_name, _spec, _conv in Formatter().parse(template):
        out.append(literal)
        if field_name is None:
            continue
        value = resolve_path(context, field_name)
        out.append(f"{{{field_name}}}" if value is None else str(value))
    return "".join(out).strip()
```

- [ ] **Step 5: Implement the loader**

`wing_parser/advisory/loader.py`:

```python
"""Read rule YAML into Rule records.

`source` and `rationale` are mandatory. Six places in the knowledge base
disagree with each other on thresholds; a rule that cannot say where its
number came from is a rule nobody can re-check later.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from wing_parser.advisory.models import SEVERITIES, Rule
from wing_parser.advisory.predicates import OPERATORS

BASE_RULES_DIR = Path(__file__).resolve().parent / "base_rules"


def _load_yaml(path: Path) -> dict:
    """Parse a rule file, turning a YAML syntax error into the same
    ValueError shape every other load-time problem raises, instead of a
    bare `yaml.YAMLError` no caller here is set up to catch."""
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"{path}: invalid YAML: {exc}") from exc


def _validate_where(where: dict, path: Path, rule_id: str) -> None:
    """Reject an unknown predicate operator at load time.

    `predicates.matches` raises `ValueError` for this too, but only when
    a target happens to reach that `where` clause mid-run -- a rule that
    is rarely evaluated could ship a typo'd operator for a long time
    before it ever surfaces. Checking every operator key up front means a
    hand-edited rule file fails at load, the same moment every other slip
    in it would.
    """
    for field_path, expected in where.items():
        if not isinstance(expected, dict):
            continue
        for operator in expected:
            if operator not in OPERATORS:
                raise ValueError(
                    f"{path}: rule {rule_id} has an unknown predicate "
                    f"operator {operator!r} on {field_path!r}; expected "
                    f"one of {sorted(OPERATORS)}"
                )


def _optional(entry: dict, key: str, default):
    """Read an optional field, treating an explicit YAML null as unset.

    `.get(key, default)` only defaults when the key is absent. A rule file
    is hand-edited, and `enabled:` with the value left off is a plausible
    slip — under `.get` it would come back None, silently disabling a rule
    its author meant to leave on. The sibling fields (`where`,
    `applies_when`, `supersedes`) already collapse null to their default
    via `or`; this keeps the scalar ones consistent with them.
    """
    value = entry.get(key)
    return default if value is None else value


def _rule_from(entry: dict, layer: str, where_from: Path) -> Rule:
    if not isinstance(entry, dict):
        raise ValueError(
            f"{where_from}: each rule entry must be a mapping, not "
            f"{type(entry).__name__} ({entry!r})"
        )

    for required in ("id", "title", "severity", "source", "rationale", "message"):
        if not entry.get(required):
            raise ValueError(f"{where_from}: rule is missing required field {required!r}")

    severity = entry["severity"]
    if severity not in SEVERITIES:
        raise ValueError(
            f"{where_from}: rule {entry['id']} has severity {severity!r}; "
            f"expected one of {SEVERITIES}"
        )

    when = entry.get("when") or {}
    if not when.get("for_each"):
        raise ValueError(f"{where_from}: rule {entry['id']} has no when.for_each")

    where = dict(when.get("where") or {})
    _validate_where(where, where_from, entry["id"])

    return Rule(
        id=entry["id"],
        title=entry["title"],
        severity=severity,
        source=entry["source"],
        rationale=entry["rationale"],
        for_each=when["for_each"],
        where=where,
        message=entry["message"],
        layer=layer,
        requires_classifier=bool(_optional(entry, "requires_classifier", False)),
        enabled=bool(_optional(entry, "enabled", True)),
        hardness=_optional(entry, "hardness", "hard"),
        applies_when=dict(entry.get("applies_when") or {}),
        supersedes=tuple(entry.get("supersedes") or ()),
    )


def load_rules(path: Path, layer: str) -> list[Rule]:
    path = Path(path)
    doc = _load_yaml(path)
    return [_rule_from(entry, layer, path) for entry in (doc.get("rules") or [])]


def load_base_rules() -> list[Rule]:
    rules: list[Rule] = []
    for path in sorted(BASE_RULES_DIR.glob("*.yaml")):
        rules.extend(load_rules(path, layer="base"))
    return rules
```

Fix wave (2026-08-14): closes deferred minors T18-2 and T18-6. A
hand-edited rule file used to reach the CLI as a traceback for six
distinct slips (see `wing_parser/cli/commands.py` below); `_load_yaml`
and `_validate_where` turn a YAML syntax error and an unknown predicate
operator into the same `ValueError(f"{path}: ...")` shape every other
load-time problem here already raises, and `_rule_from` now rejects a
non-mapping entry before indexing into it. Covered by
`test_loader_rejects_an_unknown_predicate_operator`,
`test_loader_reports_a_yaml_syntax_error_by_file_and_reason` and
`test_loader_rejects_a_non_mapping_rule_entry` in
`tests/test_advisory_predicates.py`.

- [ ] **Step 6: Run the test**

Run: `python -m pytest tests/test_advisory_predicates.py -v`
Expected: every test passes except `test_base_rules_load_from_the_package`, which fails with an empty rule set until Task 20 creates the YAML files.

- [ ] **Step 7: Commit**

```bash
git add wing_parser/advisory/ tests/test_advisory_predicates.py
git commit -m "Add the rule record, loader and predicate language

The predicate language is deliberately small: a rule file should read
as a statement about the console, not as code. source and rationale are
mandatory because six places in the knowledge base disagree on
thresholds, and a rule that cannot cite its number cannot be re-checked."
```

---

## Task 19: Rule evaluator

**Files:**
- Create: `wing_parser/advisory/evaluator.py`
- Test: `tests/test_advisory_evaluator.py`

**Interfaces:**
- Consumes: `Rule` / `Finding` (Task 18), `predicates` (Task 18), `WingScene` (Task 10), `LOW` (Task 14)
- Produces:
  - `wing_parser.advisory.evaluator.Target` — frozen dataclass `name: str`, `context: dict[str, Any]`, `confidence: float`
  - `wing_parser.advisory.evaluator.ITERATORS: dict[str, Callable]`
  - `wing_parser.advisory.evaluator.targets_for(scene, for_each: str) -> Iterator[Target]`
  - `wing_parser.advisory.evaluator.evaluate(scene, rule: Rule) -> list[Finding]`
  - `wing_parser.advisory.evaluator.evaluate_all(scene, rules: Iterable[Rule]) -> list[Finding]`

- [ ] **Step 1: Write the failing test**

`tests/test_advisory_evaluator.py`:

```python
import pytest

from wing_parser import WingScene
from wing_parser.advisory.evaluator import evaluate, evaluate_all, targets_for
from wing_parser.advisory.models import Rule


@pytest.fixture(scope="module")
def scene(vu_path):
    return WingScene.load(vu_path)


def rule(**overrides) -> Rule:
    base = dict(
        id="T", title="t", severity="warning", source="test", rationale="test",
        for_each="channel", where={}, message="{channel.number}", layer="base",
    )
    base.update(overrides)
    return Rule(**base)


def test_channel_iterator_yields_every_channel(scene):
    targets = list(targets_for(scene, "channel"))
    assert len(targets) == 40
    assert targets[7].name == "ch.8"
    assert targets[7].context["channel"].name == "M8 MC"


def test_send_iterator_binds_the_destination_bus(scene):
    targets = list(targets_for(scene, "channel.sends"))
    match = next(t for t in targets if t.name == "ch.8.send.8")
    assert match.context["send"].mode == "POST"
    assert match.context["destination_bus"].name == "MON VOX"


def test_bus_iterator_yields_sixteen_buses(scene):
    assert len(list(targets_for(scene, "bus"))) == 16


def test_unknown_iterator_raises(scene):
    with pytest.raises(KeyError, match="cabbage"):
        list(targets_for(scene, "cabbage"))


def test_empty_where_matches_every_target(scene):
    assert len(evaluate(scene, rule())) == 40


def test_scalar_predicate_filters(scene):
    findings = evaluate(scene, rule(where={"channel.number": 8}))
    assert len(findings) == 1
    assert findings[0].target == "ch.8"
    assert findings[0].message == "8"


def test_finding_carries_rule_metadata(scene):
    finding = evaluate(scene, rule(where={"channel.number": 8}))[0]
    assert finding.rule_id == "T"
    assert finding.layer == "base"
    assert finding.severity == "warning"


def test_evidence_records_the_matched_values(scene):
    finding = evaluate(
        scene, rule(where={"channel.number": 8, "channel.muted": False})
    )[0]
    assert finding.evidence["channel.number"] == 8
    assert finding.evidence["channel.muted"] is False


def test_disabled_rule_produces_nothing(scene):
    assert evaluate(scene, rule(enabled=False)) == []


def test_classifier_dependent_rule_carries_the_confidence(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    findings = evaluate(
        scene,
        rule(
            for_each="bus",
            requires_classifier=True,
            where={"bus.role": "monitor"},
            message="{bus.name}",
        ),
    )
    names = {f.message for f in findings}
    assert {"MON VOX", "MON L", "MON R"} <= names
    # The exact value, not a floor. All four monitor buses classify at 0.9,
    # so `>= 0.8` would still pass if evaluate()'s
    # `target.confidence if rule.requires_classifier else 1.0` were dropped
    # and every finding came out at a hardcoded 1.0.
    assert all(f.confidence == pytest.approx(0.9) for f in findings)


def test_classifier_dependent_rule_skips_unclassifiable_targets(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    findings = evaluate(
        scene,
        rule(requires_classifier=True, where={}, message="{channel.name}"),
    )
    names = {f.message for f in findings}
    # Pin the positive case first: a gate that wrongly excluded every
    # target would satisfy the absence check below trivially.
    assert findings
    # "My Lap" cannot be classified, so no rule that depends on the
    # classifier may fire against it.
    assert "My Lap" not in names
    # HS4 classifies speech.headset at 0.7, inside the 0.4-0.8 band. It is
    # the only thing in this file that tells a LOW gate apart from a HIGH
    # one -- "My Lap" sits at 0.0 and is excluded either way, so without
    # this line the test would pass even if the gate skipped at HIGH.
    assert "HS4" in names


def test_evaluate_all_concatenates(scene):
    findings = evaluate_all(
        scene,
        [rule(id="A", where={"channel.number": 8}), rule(id="B", where={"channel.number": 9})],
    )
    assert {f.rule_id for f in findings} == {"A", "B"}
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m pytest tests/test_advisory_evaluator.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.advisory.evaluator'`

- [ ] **Step 3: Implement the evaluator**

`wing_parser/advisory/evaluator.py`:

```python
"""Run rules over a scene and produce findings.

A rule marked requires_classifier is skipped for any target whose
classification is below the usable threshold. Firing a source-dependent
rule against a channel nobody could identify is how an advisory tool
starts producing confident nonsense.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Iterable, Iterator

from wing_parser.advisory.models import Finding, Rule
from wing_parser.advisory.predicates import all_match, render, resolve_path
from wing_parser.classifier.matcher import LOW


@dataclass(frozen=True)
class Target:
    name: str
    context: dict[str, Any]
    confidence: float


def _channels(scene) -> Iterator[Target]:
    for channel in scene.channels():
        yield Target(
            name=f"ch.{channel.number}",
            context={"channel": channel},
            confidence=channel.source_type.confidence,
        )


def _channel_sends(scene) -> Iterator[Target]:
    """One target per bus send.

    Matrix sends live in the same tuple and are skipped here: matrix 3 is
    not bus 3, and binding one to the other would let a bus-role rule fire
    against a matrix destination.
    """
    buses = {bus.number: bus for bus in scene.buses()}
    for channel in scene.channels():
        for send in channel.sends:
            if send.dest_kind != "bus":
                continue
            destination = buses.get(send.dest)
            yield Target(
                name=f"ch.{channel.number}.send.{send.dest}",
                context={
                    "channel": channel,
                    "send": send,
                    "destination_bus": destination,
                },
                confidence=destination.role.confidence if destination else 0.0,
            )


def _buses(scene) -> Iterator[Target]:
    for bus in scene.buses():
        yield Target(
            name=f"bus.{bus.number}",
            context={"bus": bus},
            confidence=bus.role.confidence,
        )


ITERATORS: dict[str, Callable[[Any], Iterator[Target]]] = {
    "channel": _channels,
    "channel.sends": _channel_sends,
    "bus": _buses,
}


def targets_for(scene, for_each: str) -> Iterator[Target]:
    if for_each not in ITERATORS:
        raise KeyError(f"no target iterator named {for_each!r}")
    return ITERATORS[for_each](scene)


def evaluate(scene, rule: Rule) -> list[Finding]:
    if not rule.enabled:
        return []

    findings: list[Finding] = []
    for target in targets_for(scene, rule.for_each):
        if rule.requires_classifier and target.confidence < LOW:
            continue
        if not all_match(target.context, rule.where):
            continue
        findings.append(
            Finding(
                rule_id=rule.id,
                layer=rule.layer,
                severity=rule.severity,
                target=target.name,
                message=render(rule.message, target.context),
                evidence={
                    path: resolve_path(target.context, path) for path in rule.where
                },
                confidence=target.confidence if rule.requires_classifier else 1.0,
            )
        )
    return findings


def evaluate_all(scene, rules: Iterable[Rule]) -> list[Finding]:
    findings: list[Finding] = []
    for rule in rules:
        findings.extend(evaluate(scene, rule))
    return findings
```

- [ ] **Step 4: Run the test and verify it passes**

Run: `python -m pytest tests/test_advisory_evaluator.py -v`
Expected: PASS — 16 tests

- [ ] **Step 5: Commit**

```bash
git add wing_parser/advisory/evaluator.py tests/test_advisory_evaluator.py
git commit -m "Add the rule evaluator

Three target iterators cover the Phase 1 rules: channels, per-send
pairs with the destination bus bound, and buses. A classifier-dependent
rule skips any target below the usable confidence threshold rather than
firing against a channel nobody could identify."
```

---

## Task 20: Three-layer resolver and the base rules

**Files:**
- Create: `wing_parser/advisory/resolver.py`
- Create: `wing_parser/advisory/layers.py` — added in fix round 2: reading and
  validating the hand-edited toanaz/show YAML (`_principles`, `_show_rules`,
  `_as_rules`), split out of `resolver.py` once it grew past the project's
  ~200-line-per-file guideline. `resolver.py` keeps the resolution and
  precedence logic (`CONDITIONS`, `condition_holds`, `_is_active`,
  `active_rules`, `suppressed_ids`, `run`, `AdvisoryFacade`).
- Create: `wing_parser/advisory/base_rules/monitors.yaml`
- Create: `wing_parser/advisory/base_rules/dynamics.yaml`
- Modify: `wing_parser/query/scene.py`
- Test: `tests/test_advisory_rules.py`
- Test: `tests/test_advisory_resolver.py`

**Interfaces:**
- Consumes: `loader` (Task 18), `evaluator` (Task 19), `config.knowledge_dir` (Task 15)
- Produces:
  - `wing_parser.advisory.resolver.active_rules(scene, directory=None) -> list[Rule]` — base rules, minus any superseded by an active higher layer, plus the higher layers' own rules
  - `wing_parser.advisory.resolver.condition_holds(scene, applies_when: dict) -> bool`
  - `wing_parser.advisory.resolver.CONDITIONS: dict[str, Callable]` — currently `monitor_bus_count`, `channel_count`
  - `wing_parser.advisory.resolver.run(scene, directory=None) -> list[Finding]`
  - New on `WingScene`: `.advisory` facade with `.run()`, `.rules()`, `.suppressed()`

- [ ] **Step 1: Write the base rules**

`wing_parser/advisory/base_rules/monitors.yaml`:

```yaml
# Generic monitor-path rules mined from docs/knowledge-base/.
# These are the textbook. ToanAZ's principles override them; see
# knowledge/toanaz/principles.yaml.
rules:
  - id: G8
    title: "Monitor send is post-fader"
    severity: warning
    source: "docs/knowledge-base/02-event-ops-framework/Core-Skills-Overview.md section 3.4 step 2"
    rationale: >
      A post-fader monitor send means a FOH fader move changes what the
      performer hears. The knowledge base calls post-fader monitor sends
      a common and disruptive misconfiguration.
    requires_classifier: true
    when:
      for_each: channel.sends
      where:
        destination_bus.role: monitor
        # Both keys are prefixed `send.`, and must stay that way. The
        # channel.sends context binds three names -- channel, send and
        # destination_bus -- so a bare `mode` resolves against the context
        # dict itself, finds nothing, and the rule silently never fires.
        # The prefix also dodges YAML 1.1: a bare `on:` key parses as the
        # boolean True, and resolve_path then dies on True.split(".").
        send.mode: POST
        send.on: true
    message: >
      Channel {channel.number} ({channel.name}) sends post-fader to bus
      {destination_bus.number} ({destination_bus.name}), which looks like a
      monitor bus. FOH fader moves will change this performer's mix.

  - id: G7
    title: "Monitor bus has no limiter"
    severity: error
    source: >
      docs/knowledge-base/04-templates-and-matrices/Technical-Rider-Spec.md section 4.1;
      docs/knowledge-base/02-event-ops-framework/Core-Skills-Overview.md section 3.4 step 8
    rationale: >
      A feedback burst into in-ear moulds is a hearing injury. Core-Skills-
      Overview section 3.4 step 8 calls a hard limiter on every IEM mix
      non-optional, typically -6 to -10 dBFS. The rider's section 4.1 table
      also lists a limiter as a requirement, but unlike its neighbouring
      "Ambient mics" row it carries no [R] contractual tag and states no
      ceiling -- so only Core-Skills makes the non-optional claim. This rule
      checks only that a limiter is present, because the correct ceiling
      depends on the IEM pack and cannot be read from the scene file.
    requires_classifier: true
    when:
      for_each: bus
      where:
        bus.role: monitor
        bus.dyn.model:
          not_in: [LIM, LIMIT, PRECISION_LIM, BRICK]
    message: >
      Bus {bus.number} ({bus.name}) looks like a monitor bus but its
      dynamics slot holds {bus.dyn.model}, not a limiter. Every in-ear mix
      needs a hard limiter for hearing protection.
```

`wing_parser/advisory/base_rules/dynamics.yaml`:

```yaml
rules:
  - id: E6
    title: "Gate and automix on the same channel"
    severity: warning
    source: >
      docs/knowledge-base/01-live-audio-ai/AI-Plugins-In-Live-Sound.md L383-384;
      docs/knowledge-base/03-event-type-sops/Corporate-B2B-Events.md section 4.4,
      section 4.1 L549
    rationale: >
      The gate opens late, the automixer reads that as speech onset, and the
      first syllable gets a 20-40 ms gain ramp. Note this checks postins.on,
      not just postins.mode: a channel can carry a configured but inactive
      automix assignment, and flagging that would be a false positive.
      AI-Plugins-In-Live-Sound.md L383-384 gives an unconditional "do not
      gate and automix the same channel," with no exception; only
      Corporate-B2B-Events.md section 4.4 grants one, allowing a gate range
      of no more than 6 dB with a 200 ms hold if a channel truly needs both.
      Section 4.1's lectern gate row does not contradict section 4.4: its
      own guidance text says to prefer automix over gating and, if gating,
      keep the range shallow, the same direction as 4.4. But the row's own
      tabulated starting values are range 12 dB, hold 120 ms (L549), so a
      lectern gate built to that table and later assigned to an automix
      group trips this rule anyway -- a tension between the table's
      numbers and the prose ceiling, not a self-contradiction. This rule
      keeps section 4.4's 6 dB range ceiling, because 4.4 is the passage
      that directly addresses a channel running gate and automix together,
      and does not check hold time.
    requires_classifier: false
    when:
      for_each: channel
      where:
        channel.gate.on: true
        channel.post_insert.on: true
        channel.post_insert.automix_group:
          not: null
        channel.gate.range_dB:
          gt: 6.0
    message: >
      Channel {channel.number} ({channel.name}) has both an active gate
      (range {channel.gate.range_dB} dB) and automix group
      {channel.post_insert.automix_group}. The gate opens late and the
      automixer reads that as speech onset, ramping the first syllable.
```

- [ ] **Step 2: Write the failing tests**

`tests/test_advisory_rules.py`:

```python
import json

import pytest

from wing_parser import WingScene
from wing_parser.advisory.loader import load_base_rules


@pytest.fixture(scope="module")
def scene(vu_path):
    return WingScene.load(vu_path)


def test_three_base_rules_ship(scene):
    assert {r.id for r in load_base_rules()} == {"G8", "G7", "E6"}


def test_every_base_rule_cites_a_source_and_a_rationale():
    for rule in load_base_rules():
        assert "docs/knowledge-base/" in rule.source, rule.id
        assert len(rule.rationale) > 40, rule.id


def test_g8_fires_on_channel_eight_into_bus_eight(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    findings = [f for f in scene.advisory.run() if f.rule_id == "G8"]
    match = next(f for f in findings if f.target == "ch.8.send.8")

    assert match.severity == "warning"
    assert match.layer == "base"
    assert "MON VOX" in match.message
    assert match.confidence >= 0.8


def test_g7_fires_on_bus_eight(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    match = next(f for f in scene.advisory.run() if f.rule_id == "G7" and f.target == "bus.8")

    assert match.severity == "error"
    assert "COMP" in match.message


def test_e6_fires_on_the_headset_channel_and_nothing_else(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    findings = [f for f in scene.advisory.run() if f.rule_id == "E6"]
    # Channel 11 (HS4) is the only channel in this file carrying both an
    # active gate over 6 dB and an active automix insert: gate range 40 dB,
    # hold 10 ms, automix group X. This is a real finding on a real show
    # file, not a fixture -- do not "fix" it by weakening the rule.
    assert [f.target for f in findings] == ["ch.11"]
    assert "HS4" in findings[0].message


def test_e6_ignores_an_automix_group_configured_but_switched_off(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    # Channels 1, 2, 3, 5, 6, 7 and 8 all carry automix group X with the
    # post insert switched OFF, and a gate over 6 dB. They are exactly the
    # false positives E6's `channel.post_insert.on` check exists to
    # prevent, so none of them may appear. Drop that check and this test
    # goes red with seven extra targets.
    flagged = {f.target for f in scene.advisory.run() if f.rule_id == "E6"}
    assert flagged.isdisjoint({f"ch.{n}" for n in (1, 2, 3, 5, 6, 7, 8)})


def test_e6_fires_once_the_automix_insert_is_switched_on(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"]["8"]["postins"]["on"] = True
    live = tmp_path / "automix_on.snap"
    live.write_text(json.dumps(doc), encoding="utf-8")

    findings = [f for f in WingScene.load(live).advisory.run() if f.rule_id == "E6"]
    # ch.11 already fires on the unmodified file; switching channel 8's
    # insert on adds it, and targets come out in channel order.
    assert [f.target for f in findings] == ["ch.8", "ch.11"]
    assert "X" in findings[0].message


def test_every_finding_records_its_layer(scene, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    findings = scene.advisory.run()
    # all(...) over an empty list is vacuously True, so an empty findings
    # list would pass this assertion without actually exercising anything.
    assert findings
    assert all(f.layer in {"base", "toanaz", "show"} for f in findings)
```

`tests/test_advisory_resolver.py`:

```python
import pytest
import yaml

from wing_parser import WingScene
from wing_parser.advisory.resolver import (
    AdvisoryFacade,
    active_rules,
    condition_holds,
    run,
    suppressed_ids,
)


@pytest.fixture
def knowledge(tmp_path):
    directory = tmp_path / "knowledge"
    (directory / "shows").mkdir(parents=True)
    (directory / "classifier.yaml").write_text(
        yaml.safe_dump({"channels": {}, "buses": {}}), encoding="utf-8"
    )
    (directory / "principles.yaml").write_text(
        yaml.safe_dump({"principles": []}), encoding="utf-8"
    )
    return directory


@pytest.fixture
def scene(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    return WingScene.load(vu_path)


def test_only_base_rules_are_active_with_an_empty_principles_file(scene, knowledge):
    assert {r.id for r in active_rules(scene, directory=knowledge)} == {"G8", "G7", "E6"}


def test_monitor_bus_count_condition_reads_the_scene(scene):
    # MON VOX, MON L, MON R and SIDEFILL all classify as monitor buses:
    # the real count on the sample scene is 4. Both the failing value (1)
    # and the actual value (4) are pinned so a probe that always returns
    # 0, or any other wrong constant, cannot leave this test green.
    assert condition_holds(scene, {"monitor_bus_count": 1}) is False
    assert condition_holds(scene, {"monitor_bus_count": 4}) is True
    assert condition_holds(scene, {}) is True


def test_channel_count_condition_reads_the_scene(scene):
    # The sample scene has 40 channels. This condition ships in
    # CONDITIONS per the brief but had no test at all -- deleting the
    # entry, or breaking the probe, must go red here.
    assert condition_holds(scene, {"channel_count": 40}) is True
    assert condition_holds(scene, {"channel_count": 1}) is False


def test_unknown_condition_is_false_not_an_error(scene):
    assert condition_holds(scene, {"phase_of_the_moon": "waxing"}) is False


def test_a_matching_hard_principle_supersedes_its_base_rule(scene, knowledge, monkeypatch):
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.always-off-g8",
                        "principle": "G8 does not apply to my rigs",
                        "hardness": "hard",
                        "supersedes": ["G8"],
                        "rationale": "field practice",
                        "source": "ToanAZ",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    ids = {r.id for r in active_rules(scene, directory=knowledge)}
    assert "G8" not in ids
    assert "G7" in ids

    assert [f for f in run(scene, directory=knowledge) if f.rule_id == "G8"] == []


def test_a_matching_flexible_principle_supersedes_its_base_rule(scene, knowledge):
    # This is the path the previous test's name claimed to cover but
    # did not: hardness: flexible, with an applies_when that actually
    # matches this scene (4 monitor buses), so condition_holds runs a
    # real probe and returns True. That is the whole point of the
    # three-layer design -- a base rule switched off only under a
    # stated, checkable condition -- and until now nothing exercised it.
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.four-monitor-rig",
                        "principle": "This rig always runs 4 monitor buses; G8 does not apply",
                        "hardness": "flexible",
                        "applies_when": {"monitor_bus_count": 4},
                        "supersedes": ["G8"],
                        "rationale": "field practice",
                        "source": "ToanAZ",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    ids = {r.id for r in active_rules(scene, directory=knowledge)}
    assert "G8" not in ids
    assert "toanaz.four-monitor-rig" in ids

    assert [f for f in run(scene, directory=knowledge) if f.rule_id == "G8"] == []


def test_a_flexible_principle_whose_condition_fails_does_not_supersede(scene, knowledge):
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.iem-shared-band.guitar-prefader",
                        "principle": "Shared band IEM",
                        "hardness": "flexible",
                        "applies_when": {"monitor_bus_count": 1},
                        "supersedes": ["G8"],
                        "rationale": "field practice",
                        "source": "ToanAZ",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    # This scene has more than one monitor bus, so the condition fails
    # and G8 survives.
    assert "G8" in {r.id for r in active_rules(scene, directory=knowledge)}


def test_a_disabled_principle_supersedes_nothing(scene, knowledge):
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.off",
                        "principle": "x",
                        "hardness": "hard",
                        "supersedes": ["G8"],
                        "rationale": "r",
                        "source": "ToanAZ",
                        "enabled": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    assert "G8" in {r.id for r in active_rules(scene, directory=knowledge)}


def test_a_show_rule_and_an_inactive_principle_can_both_name_the_same_base_rule(scene, knowledge):
    """No cross-layer precedence exists to demonstrate here.

    `supersedes` is base-only (design spec section 6.3, line 270): a
    principle and a show rule may each independently name the same base
    rule id in their own supersedes list, but neither ever supersedes
    the other -- there is no "the show beats the principle" mechanism
    in this resolver (see
    test_a_principle_superseding_a_higher_layer_rule_id_raises, which
    confirms naming a higher-layer id is rejected outright). This
    fixture's principle is flexible with an applies_when
    (monitor_bus_count: 1) that fails on this scene, so it is not even
    active; G7's suppression below comes entirely from the show layer.
    """
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.keep-g7-unless-shared-rig",
                        "principle": "G7 only backs off on a single-monitor-bus rig",
                        "hardness": "flexible",
                        "applies_when": {"monitor_bus_count": 1},
                        "supersedes": ["G7"],
                        "rationale": "field practice",
                        "source": "ToanAZ",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (knowledge / "shows" / "tonight.yaml").write_text(
        yaml.safe_dump(
            {
                "rules": [
                    {
                        "id": "show.no-g7",
                        "title": "Wedges tonight, no IEMs",
                        "severity": "info",
                        "source": "show sheet",
                        "rationale": "no in-ear packs on this show",
                        "supersedes": ["G7"],
                        "when": {"for_each": "bus", "where": {"bus.number": -1}},
                        "message": "never fires",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    ids = {r.id for r in active_rules(scene, directory=knowledge)}
    assert "G7" not in ids
    assert "show.no-g7" in ids
    # The principle's own condition failed, so it is not even active --
    # confirming G7's suppression here comes from the show, not it.
    assert "toanaz.keep-g7-unless-shared-rig" not in ids


def test_a_principle_superseding_an_unknown_rule_id_raises(scene, knowledge):
    # G88 is a typo for G8. Silently ignoring it would leave G8 firing
    # while the author believes it is off, and suppressed_ids() would
    # report a suppression that never happened.
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.typo",
                        "principle": "typo'd rule id",
                        "hardness": "hard",
                        "supersedes": ["G88"],
                        "rationale": "field practice",
                        "source": "ToanAZ",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="G88"):
        active_rules(scene, directory=knowledge)


def test_a_principle_superseding_a_higher_layer_rule_id_raises(scene, knowledge):
    # supersedes may only name a base rule id (design spec section 6.3,
    # line 270). `toanaz.base` is a real id -- not a typo like G88 -- but
    # naming it has no effect, because active_rules only ever filters
    # superseded ids out of the base layer. This must raise too, with a
    # message that tells it apart from an unknown-anywhere id: a misuse
    # of the field, not a typo.
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.base",
                        "principle": "base principle",
                        "hardness": "hard",
                        "supersedes": ["G8"],
                        "rationale": "field practice",
                        "source": "ToanAZ",
                        "enabled": True,
                    },
                    {
                        "id": "toanaz.names-the-other-principle",
                        "principle": "names a real principle id, not a base rule",
                        "hardness": "hard",
                        "supersedes": ["toanaz.base"],
                        "rationale": "field practice",
                        "source": "ToanAZ",
                        "enabled": True,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="higher-layer rule id"):
        active_rules(scene, directory=knowledge)


def test_a_principle_with_hardness_left_blank_still_defaults_to_hard(scene, knowledge):
    # A hand-edited principles.yaml can leave `hardness:` present but
    # blank, which YAML parses as null. `.get(key, default)` only
    # supplies its default when the key is absent, so this used to
    # resolve to hardness=None on the Rule -- not the documented
    # default of "hard". Assert the Rule's own field, not just a side
    # effect, because None and "hard" both make _is_active return True
    # (only "flexible" is special-cased), so a behavioural-only test
    # cannot tell them apart.
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.blank-hardness",
                        "principle": "hardness left blank by mistake",
                        "hardness": None,
                        "supersedes": ["G8"],
                        "rationale": "field practice",
                        "source": "ToanAZ",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    rule = next(
        r for r in active_rules(scene, directory=knowledge) if r.id == "toanaz.blank-hardness"
    )
    assert rule.hardness == "hard"


def test_a_principle_with_source_left_blank_still_defaults_to_toanaz(scene, knowledge):
    # Same hazard as hardness above, on the field that exists purely so a
    # rule can be traced back to where it came from: a blank `source:`
    # parses as YAML null, and plain `.get(key, default)` only supplies
    # its default when the key is absent, not when it is present-but-null.
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.blank-source",
                        "principle": "source left blank by mistake",
                        "hardness": "hard",
                        "source": None,
                        "supersedes": ["G8"],
                        "rationale": "field practice",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    rule = next(
        r for r in active_rules(scene, directory=knowledge) if r.id == "toanaz.blank-source"
    )
    assert rule.source == "ToanAZ"


def test_a_principle_with_rationale_left_blank_still_defaults_to_empty_string(scene, knowledge):
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.blank-rationale",
                        "principle": "rationale left blank by mistake",
                        "hardness": "hard",
                        "rationale": None,
                        "supersedes": ["G8"],
                        "source": "ToanAZ",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    rule = next(
        r for r in active_rules(scene, directory=knowledge) if r.id == "toanaz.blank-rationale"
    )
    assert rule.rationale == ""


def test_a_principle_with_an_invalid_severity_raises(scene, knowledge):
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.bad-severity",
                        "principle": "x",
                        "severity": "catastrophic",
                        "hardness": "hard",
                        "supersedes": ["G8"],
                        "rationale": "field practice",
                        "source": "ToanAZ",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="severity"):
        active_rules(scene, directory=knowledge)


def test_a_principle_with_an_explicit_when_block_missing_for_each_raises(scene, knowledge):
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.broken-when",
                        "principle": "x",
                        "hardness": "hard",
                        "when": {"where": {"channel.number": 1}},
                        "supersedes": ["G8"],
                        "rationale": "field practice",
                        "source": "ToanAZ",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="for_each"):
        active_rules(scene, directory=knowledge)


def test_suppressed_ids_reports_which_higher_layer_rule_switched_off_a_base_rule(scene, knowledge):
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.always-off-g8",
                        "principle": "G8 does not apply to my rigs",
                        "hardness": "hard",
                        "supersedes": ["G8"],
                        "rationale": "field practice",
                        "source": "ToanAZ",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    assert suppressed_ids(scene, directory=knowledge) == {"G8": "toanaz.always-off-g8"}


def test_suppressed_ids_is_empty_with_no_active_higher_layer_rules(scene, knowledge):
    assert suppressed_ids(scene, directory=knowledge) == {}


def test_advisory_facade_suppressed_delegates_to_suppressed_ids(scene, knowledge):
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.always-off-g8",
                        "principle": "G8 does not apply to my rigs",
                        "hardness": "hard",
                        "supersedes": ["G8"],
                        "rationale": "field practice",
                        "source": "ToanAZ",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    facade = AdvisoryFacade(scene, directory=knowledge)
    assert facade.suppressed() == {"G8": "toanaz.always-off-g8"}


def test_show_rules_load_from_a_yml_extension_too(scene, knowledge):
    # A show file saved with the other spelling must not be silently
    # invisible -- indistinguishable from "no overrides tonight".
    (knowledge / "shows" / "tonight.yml").write_text(
        yaml.safe_dump(
            {
                "rules": [
                    {
                        "id": "show.no-g7-yml",
                        "title": "Wedges tonight, no IEMs",
                        "severity": "info",
                        "source": "show sheet",
                        "rationale": "no in-ear packs on this show",
                        "supersedes": ["G7"],
                        "when": {"for_each": "bus", "where": {"bus.number": -1}},
                        "message": "never fires",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    ids = {r.id for r in active_rules(scene, directory=knowledge)}
    assert "G7" not in ids
    assert "show.no-g7-yml" in ids
```

- [ ] **Step 3: Run the tests and verify they fail**

Run: `python -m pytest tests/test_advisory_rules.py tests/test_advisory_resolver.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.advisory.resolver'`

- [ ] **Step 4: Implement the resolver**

Fix round 2 split this step's original single file into two, once `resolver.py` grew
past the project's ~200-line-per-file guideline: `layers.py` reads and validates the
hand-edited toanaz/show YAML, and `resolver.py` keeps only the resolution and
precedence logic. There is no reverse dependency from `layers.py` back into
`resolver.py`.

`wing_parser/advisory/layers.py`:

```python
"""Read hand-edited YAML into Rule records for the toanaz and show layers.

Base rules ship in the package and are validated on load by
`loader.load_rules`. The toanaz principles file and per-show exception
files are the two layers a human edits by hand, and a hand-edited file is
exactly where a slip is most likely and a silent default is most
dangerous -- so this module applies the same validation `load_rules`
already gives the base layer.
"""

from __future__ import annotations

from pathlib import Path

from wing_parser import config
from wing_parser.advisory.loader import _load_yaml, _optional, _validate_where, load_rules
from wing_parser.advisory.models import SEVERITIES, Rule

PRINCIPLES_FILE = "principles.yaml"
SHOWS_DIR = "shows"


def _principles(directory: Path | None) -> list[Rule]:
    path = config.knowledge_dir(directory) / PRINCIPLES_FILE
    if not path.exists():
        return []
    return _as_rules(path, layer="toanaz", key="principles")


def _show_rules(directory: Path | None) -> list[Rule]:
    """A show file may be saved `.yaml` or `.yml`.

    Globbing only `*.yaml` makes a `.yml` file silently invisible --
    not loaded, not warned about, indistinguishable from "no overrides
    tonight." Both extensions are gathered into one sorted list so
    load order stays deterministic regardless of which spelling a show
    file used.
    """
    shows = config.knowledge_dir(directory) / SHOWS_DIR
    if not shows.is_dir():
        return []
    paths = sorted(list(shows.glob("*.yaml")) + list(shows.glob("*.yml")))
    rules: list[Rule] = []
    for path in paths:
        rules.extend(load_rules(path, layer="show"))
    return rules


def _as_rules(path: Path, layer: str, key: str) -> list[Rule]:
    """principles.yaml uses `principles:` and may omit the `when` block.

    A principle whose only job is to switch a base rule off needs no
    target of its own, so a missing `when` becomes a rule that matches
    nothing and exists purely for its `supersedes` list. An explicit
    `when` block with no `for_each` is a different, invalid case and is
    rejected the same way `loader.load_rules` rejects it, rather than
    left to raise a bare `KeyError` a few lines down.

    Every optional field -- `severity`, `source`, `rationale`,
    `requires_classifier`, `enabled`, `hardness` -- routes through
    `loader._optional`, not `.get(key, default)`. `.get` only supplies
    its default when the key is absent entirely; a hand-edited
    principles file can leave a key present but blank, which YAML
    parses as null. A blank `hardness:` would resolve to `None` under
    `.get`, `_is_active` would not recognise it as `"flexible"`, and
    the principle would fall through to unconditionally active --
    silently switching a base rule off on every show from a
    one-character slip. A blank `source:` would resolve to `None`
    instead of the documented `"ToanAZ"` default, the same hazard on a
    field that exists purely for traceability. This is also why this
    layer validates `severity` against `SEVERITIES`: `load_rules`
    already rejects a bad severity for the base layer, and toanaz is
    the one hand-maintained layer, so leaving it unvalidated here would
    make the only human-edited layer the only unchecked one.

    Two more slips a hand-edited file invites, both turned into the
    same `ValueError(f"{path}: ...")` shape `loader._rule_from` already
    uses rather than left to raise a bare `KeyError` or `AttributeError`
    a few lines down: an entry that is not a mapping at all (a bare
    string dropped into the `principles:` list), and an entry missing
    `id:` entirely.
    """
    doc = _load_yaml(path)
    rules: list[Rule] = []
    for entry in doc.get(key) or []:
        if not isinstance(entry, dict):
            raise ValueError(
                f"{path}: each entry under {key!r} must be a mapping, not "
                f"{type(entry).__name__} ({entry!r})"
            )
        if not entry.get("id"):
            raise ValueError(f"{path}: rule is missing required field 'id'")

        severity = _optional(entry, "severity", "info")
        if severity not in SEVERITIES:
            raise ValueError(
                f"{path}: rule {entry['id']} has severity {severity!r}; "
                f"expected one of {SEVERITIES}"
            )
        when = entry.get("when")
        if when is not None:
            if not when.get("for_each"):
                raise ValueError(f"{path}: rule {entry['id']} has no when.for_each")
        else:
            when = {"for_each": "channel", "where": {"channel.number": -1}}

        where = dict(when.get("where") or {})
        _validate_where(where, path, entry["id"])

        rules.append(
            Rule(
                id=entry["id"],
                title=entry.get("principle") or entry.get("title", entry["id"]),
                severity=severity,
                source=_optional(entry, "source", "ToanAZ"),
                rationale=_optional(entry, "rationale", ""),
                for_each=when["for_each"],
                where=where,
                message=entry.get("message", entry.get("principle", entry["id"])),
                layer=layer,
                requires_classifier=bool(_optional(entry, "requires_classifier", False)),
                enabled=bool(_optional(entry, "enabled", True)),
                hardness=_optional(entry, "hardness", "hard"),
                applies_when=dict(entry.get("applies_when") or {}),
                supersedes=tuple(entry.get("supersedes") or ()),
            )
        )
    return rules
```

Fix wave (2026-08-14): `_as_rules` used to index `entry["id"]` directly
and call `.get()` on entries it had not checked were mappings, so a
missing `id:` or a bare-string list entry reached the CLI as a bare
`KeyError`/`AttributeError` instead of naming the file. Also reuses the
new `loader._load_yaml` (a YAML syntax error now raises the same
`ValueError` shape) and `loader._validate_where` (an unknown predicate
operator is now rejected at load time here too, not just for the base
and show layers). Covered by `test_a_principle_missing_id_raises` and
`test_a_bare_string_principle_entry_raises` in
`tests/test_advisory_resolver.py`.

`wing_parser/advisory/resolver.py`:

```python
"""Three-layer rule resolution: base, then ToanAZ, then per-show.

Generic rules are written as absolutes because that is how training
material teaches. Real shows have conditions the textbook never states,
so a higher layer can switch a base rule off under stated conditions and
say why. Every finding records which layer decided it, because otherwise
a false positive is undiagnosable.

Reading and validating the hand-edited YAML for the toanaz and show
layers lives in `layers.py`; this module is the resolution and
precedence logic -- which rules end up active, and why -- and does not
parse a rule file itself.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from wing_parser.advisory.evaluator import evaluate_all
from wing_parser.advisory.layers import _principles, _show_rules
from wing_parser.advisory.loader import load_base_rules
from wing_parser.advisory.models import Finding, Rule


def _monitor_bus_count(scene) -> int:
    return sum(1 for bus in scene.buses() if bus.is_monitor)


CONDITIONS: dict[str, Callable[[Any], Any]] = {
    "monitor_bus_count": _monitor_bus_count,
    "channel_count": lambda scene: len(scene.channels()),
}


def condition_holds(scene, applies_when: dict[str, Any]) -> bool:
    for name, expected in (applies_when or {}).items():
        probe = CONDITIONS.get(name)
        if probe is None:
            return False
        if probe(scene) != expected:
            return False
    return True


def _is_active(scene, rule: Rule) -> bool:
    if not rule.enabled:
        return False
    if rule.hardness == "flexible":
        return condition_holds(scene, rule.applies_when)
    return True


def _validate_applies_when(rule: Rule) -> None:
    """Reject an unknown `applies_when` key on a flexible rule.

    `condition_holds` deliberately treats an unrecognised condition name
    as False rather than an error (see `test_unknown_condition_is_false_
    not_an_error`), which is the right call for a probe that genuinely
    does not apply to a given scene. But it means a typo -- `monitor_
    bus_cnt` for `monitor_bus_count` -- is indistinguishable from that:
    the principle silently never fires and never says why, the same
    failure mode `active_rules`'s `supersedes` check exists to catch on
    the other hand-edited field of the same file. This only stops that
    one confusion; it does not resolve the separate, open design
    question of which conditions the project owner actually needs
    `CONDITIONS` to support -- see the "do not touch" list in the Phase 1
    fix-wave brief.
    """
    if rule.hardness != "flexible":
        return
    for key in rule.applies_when:
        if key not in CONDITIONS:
            raise ValueError(
                f"{rule.id} has an unknown applies_when key {key!r}; "
                f"expected one of {sorted(CONDITIONS)}"
            )


def active_rules(scene, directory: Path | None = None) -> list[Rule]:
    candidates = _principles(directory) + _show_rules(directory)
    for rule in candidates:
        _validate_applies_when(rule)
    higher = [r for r in candidates if _is_active(scene, r)]
    base = load_base_rules()
    base_ids = {r.id for r in base}
    higher_ids = {r.id for r in higher}

    # Design spec section 6.3 (line 270): "`supersedes` names the base
    # rules it switches off while active." shows/ is documented (§6.2) as
    # one-off exceptions, not a layer with authority over principles --
    # there is no cross-layer precedence mechanism, and this resolver does
    # not add one. `active_rules` only ever filters the *base* layer by
    # `suppressed`, so a `supersedes` entry naming a higher-layer rule id
    # would pass a base-or-higher validity check and then silently do
    # nothing. Reject it, and tell the two failure shapes apart: an id in
    # neither layer is a typo (e.g. `G88` for `G8`); an id that names a
    # real higher-layer rule is a misuse of a field the spec defines as
    # base-only.
    for rule in higher:
        for target_id in rule.supersedes:
            if target_id in base_ids:
                continue
            if target_id in higher_ids:
                raise ValueError(
                    f"{rule.id} supersedes {target_id!r}, which is a "
                    "higher-layer rule id, not a base rule id. Per design "
                    "spec section 6.3 (line 270), supersedes names only "
                    "the base rules a rule switches off; naming another "
                    "principle or show rule has no effect and is rejected."
                )
            raise ValueError(f"{rule.id} supersedes unknown rule id {target_id!r}")

    suppressed = {rule_id for r in higher for rule_id in r.supersedes}
    return [r for r in base if r.id not in suppressed] + higher


def suppressed_ids(scene, directory: Path | None = None) -> dict[str, str]:
    """Map each switched-off base rule to the higher-layer rule that did it."""
    higher = [r for r in _principles(directory) + _show_rules(directory) if _is_active(scene, r)]
    return {rule_id: r.id for r in higher for rule_id in r.supersedes}


def run(scene, directory: Path | None = None) -> list[Finding]:
    return evaluate_all(scene, active_rules(scene, directory))


class AdvisoryFacade:
    def __init__(self, scene, directory: Path | None = None) -> None:
        self._scene = scene
        self._directory = directory

    def run(self) -> list[Finding]:
        return run(self._scene, self._directory)

    def rules(self) -> list[Rule]:
        return active_rules(self._scene, self._directory)

    def suppressed(self) -> dict[str, str]:
        return suppressed_ids(self._scene, self._directory)
```

Fix wave (2026-08-14): `active_rules` validates every higher-layer
rule's `applies_when` keys against `CONDITIONS` before filtering by
`_is_active`, the same load-time-not-runtime treatment the `supersedes`
check above already gets. `suppressed_ids` is deliberately left as-is
(it already did not run the `supersedes` check either; this fix wave
does not add that asymmetry, only documents it in the report). Covered
by `test_a_flexible_principle_with_an_unknown_applies_when_key_raises`
and `test_a_hard_principles_stray_applies_when_key_is_not_validated` in
`tests/test_advisory_resolver.py`.

- [ ] **Step 5: Wire it into WingScene**

Add to the imports in `wing_parser/query/scene.py`:

```python
from wing_parser.advisory.resolver import AdvisoryFacade
```

and add:

```python
    @property
    def advisory(self) -> AdvisoryFacade:
        return AdvisoryFacade(self)
```

- [ ] **Step 6: Run the tests and verify they pass**

Run: `python -m pytest tests/test_advisory_rules.py tests/test_advisory_resolver.py tests/test_advisory_predicates.py -v`
Expected: PASS. `test_base_rules_load_from_the_package` from Task 18 now passes too.

- [ ] **Step 7: Commit**

```bash
git add wing_parser/advisory/resolver.py wing_parser/advisory/base_rules/ wing_parser/query/scene.py tests/test_advisory_rules.py tests/test_advisory_resolver.py
git commit -m "Add three-layer rule resolution and the three base rules

G8 and G7 fire on the sample scene; E6 correctly stays silent because
the automix insert is configured but switched off. A ToanAZ principle
with a matching applies_when switches a base rule off and the report
records which layer decided."
```

**Milestone 4.** The advisory engine runs with three layers, three rules, provenance on every finding, and the supersede path proven.

---

## Task 21: Feedback log

**Files:**
- Create: `wing_parser/advisory/feedback.py`
- Create: `knowledge/toanaz/feedback.jsonl`
- Test: `tests/test_advisory_feedback.py`

**Interfaces:**
- Consumes: `Finding` (Task 18), `config.knowledge_dir` (Task 15)
- Produces:
  - `wing_parser.advisory.feedback.VERDICTS: tuple[str, ...] = ("correct", "false-positive", "irrelevant")`
  - `wing_parser.advisory.feedback.finding_id(finding: Finding) -> str` — `"G8:ch.8.send.8"`, stable across runs
  - `wing_parser.advisory.feedback.Verdict` — frozen dataclass `finding_id`, `rule_id`, `layer`, `verdict`, `note`, `scene`, `target`, `recorded_at`
  - `wing_parser.advisory.feedback.record(finding, verdict, note="", scene="", directory=None, now=None) -> Verdict`
  - `wing_parser.advisory.feedback.read_log(directory=None) -> list[Verdict]`
  - `wing_parser.advisory.feedback.summarise(directory=None) -> dict[str, dict[str, int]]` — verdict counts per rule id

- [ ] **Step 1: Create the empty log**

`knowledge/toanaz/feedback.jsonl` — an empty file. It is append-only; each line is one verdict.

- [ ] **Step 2: Write the failing test**

`tests/test_advisory_feedback.py`:

```python
import json
from datetime import datetime, timezone

import pytest

from wing_parser.advisory import feedback
from wing_parser.advisory.models import Finding

FIXED = datetime(2026, 8, 13, 19, 30, tzinfo=timezone.utc)


@pytest.fixture
def knowledge(tmp_path):
    directory = tmp_path / "knowledge"
    directory.mkdir()
    return directory


def a_finding(**overrides) -> Finding:
    base = dict(
        rule_id="G8", layer="base", severity="warning",
        target="ch.8.send.8", message="post-fader monitor send",
        evidence={"mode": "POST"}, confidence=0.9,
    )
    base.update(overrides)
    return Finding(**base)


def test_finding_id_is_stable_and_readable():
    assert feedback.finding_id(a_finding()) == "G8:ch.8.send.8"
    assert feedback.finding_id(a_finding()) == feedback.finding_id(a_finding())


def test_record_appends_one_json_line(knowledge):
    feedback.record(a_finding(), "false-positive", note="shared IEM rig",
                    scene="example-Vu.snap", directory=knowledge, now=FIXED)

    lines = (knowledge / "feedback.jsonl").read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["finding_id"] == "G8:ch.8.send.8"
    assert entry["verdict"] == "false-positive"
    assert entry["note"] == "shared IEM rig"
    assert entry["scene"] == "example-Vu.snap"
    assert entry["layer"] == "base"
    assert entry["recorded_at"] == "2026-08-13T19:30:00+00:00"


def test_record_is_append_only(knowledge):
    feedback.record(a_finding(), "correct", directory=knowledge, now=FIXED)
    feedback.record(a_finding(target="ch.9.send.8"), "correct", directory=knowledge, now=FIXED)

    assert len(feedback.read_log(directory=knowledge)) == 2


def test_unknown_verdict_is_rejected(knowledge):
    with pytest.raises(ValueError, match="verdict"):
        feedback.record(a_finding(), "maybe", directory=knowledge, now=FIXED)


def test_read_log_on_a_missing_file_is_empty(knowledge):
    assert feedback.read_log(directory=knowledge) == []


def test_read_log_skips_a_corrupt_line(knowledge):
    path = knowledge / "feedback.jsonl"
    feedback.record(a_finding(), "correct", directory=knowledge, now=FIXED)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("this is not json\n")
    feedback.record(a_finding(target="ch.9"), "correct", directory=knowledge, now=FIXED)

    assert len(feedback.read_log(directory=knowledge)) == 2


def test_read_log_warns_about_every_line_it_skips(knowledge):
    """A schema change must not discard history in silence."""
    feedback.record(a_finding(), "correct", directory=knowledge, now=FIXED)
    path = knowledge / "feedback.jsonl"
    with path.open("a", encoding="utf-8") as handle:
        handle.write("this is not json\n")
        handle.write(json.dumps({"finding_id": "G8:ch.9", "rule_id": "G8"}) + "\n")

    with pytest.warns(UserWarning, match="skipping unreadable feedback entry") as caught:
        entries = feedback.read_log(directory=knowledge)

    assert len(entries) == 1
    assert len(caught) == 2
    assert "feedback.jsonl:2" in str(caught[0].message)
    assert "feedback.jsonl:3" in str(caught[1].message)


def test_summarise_counts_verdicts_per_rule(knowledge):
    feedback.record(a_finding(), "false-positive", directory=knowledge, now=FIXED)
    feedback.record(a_finding(target="ch.9.send.8"), "false-positive", directory=knowledge, now=FIXED)
    feedback.record(a_finding(rule_id="G7", target="bus.8"), "correct", directory=knowledge, now=FIXED)

    counts = feedback.summarise(directory=knowledge)
    assert counts["G8"]["false-positive"] == 2
    assert counts["G7"]["correct"] == 1
    assert counts["G8"].get("correct", 0) == 0
```

- [ ] **Step 3: Run the test and verify it fails**

Run: `python -m pytest tests/test_advisory_feedback.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.advisory.feedback'`

- [ ] **Step 4: Implement the log**

`wing_parser/advisory/feedback.py`:

```python
"""Append-only verdict log.

There is no machine learning here. The log exists so that, read across
many shows, a pattern becomes visible: seven rejections of G8, all in
scenes with exactly one monitor bus, is the signal that a conditional
principle should be written. A human writes it; Claude only reads the
log and proposes.
"""

from __future__ import annotations

import json
import warnings
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from wing_parser import config
from wing_parser.advisory.models import Finding

FILENAME = "feedback.jsonl"
VERDICTS: tuple[str, ...] = ("correct", "false-positive", "irrelevant")


@dataclass(frozen=True)
class Verdict:
    finding_id: str
    rule_id: str
    layer: str
    verdict: str
    note: str
    scene: str
    target: str
    recorded_at: str


def finding_id(finding: Finding) -> str:
    """Stable across runs for the same rule hitting the same target."""
    return f"{finding.rule_id}:{finding.target}"


def _path(directory: Path | None) -> Path:
    return config.knowledge_dir(directory) / FILENAME


def record(
    finding: Finding,
    verdict: str,
    note: str = "",
    scene: str = "",
    directory: Path | None = None,
    now: datetime | None = None,
) -> Verdict:
    if verdict not in VERDICTS:
        raise ValueError(f"unknown verdict {verdict!r}; expected one of {VERDICTS}")

    entry = Verdict(
        finding_id=finding_id(finding),
        rule_id=finding.rule_id,
        layer=finding.layer,
        verdict=verdict,
        note=note,
        scene=scene,
        target=finding.target,
        recorded_at=(now or datetime.now(timezone.utc)).isoformat(),
    )

    path = _path(directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
    return entry


def read_log(directory: Path | None = None) -> list[Verdict]:
    path = _path(directory)
    if not path.exists():
        return []

    entries: list[Verdict] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(Verdict(**json.loads(line)))
        except (json.JSONDecodeError, TypeError) as unreadable:
            # A hand-edited log should not break the reader, but it must
            # not lose history in silence either. TypeError fires on any
            # well-formed JSON object whose keys no longer match Verdict,
            # so a single schema change would otherwise discard every
            # pre-existing line without a word.
            warnings.warn(
                f"{path}:{number}: skipping unreadable feedback entry ({unreadable})",
                stacklevel=2,
            )
    return entries


def summarise(directory: Path | None = None) -> dict[str, dict[str, int]]:
    counts: dict[str, dict[str, int]] = {}
    for entry in read_log(directory):
        counts.setdefault(entry.rule_id, {}).setdefault(entry.verdict, 0)
        counts[entry.rule_id][entry.verdict] += 1
    return counts
```

- [ ] **Step 5: Run the test and verify it passes**

Run: `python -m pytest tests/test_advisory_feedback.py -v`
Expected: PASS — 8 tests

- [ ] **Step 6: Commit**

```bash
git add wing_parser/advisory/feedback.py knowledge/toanaz/feedback.jsonl tests/test_advisory_feedback.py
git commit -m "Add the append-only verdict log

Finding IDs are stable and readable so the same finding can be marked
across runs. A corrupt line is skipped rather than breaking the reader,
because this file is meant to be hand-editable."
```

---

## Task 22: CLI

**Files:**
- Create: `wing_parser/cli/__init__.py`
- Create: `wing_parser/cli/render.py`
- Create: `wing_parser/cli/commands.py`
- Create: `wing_parser/cli/__main__.py`
- Test: `tests/test_cli.py`

Output rendering is a separate module from command dispatch: rendering is the interface surface, dispatch is the wiring, and mixing them is what makes a CLI file grow past the ceiling.

**Interfaces:**
- Consumes: everything
- Produces:
  - `wing_parser.cli.render.scene_overview(scene) -> str`
  - `wing_parser.cli.render.channel_detail(channel) -> str`
  - `wing_parser.cli.render.findings(items, suppressed: dict) -> str`
  - `wing_parser.cli.render.routing(summary, unclassified) -> str`
  - `wing_parser.cli.render.changes(items, limit: int = 50) -> str`
  - `wing_parser.cli.render.level(db: float) -> str` — `"-inf"` for silence, `"-7.9 dB"` otherwise
  - `wing_parser.cli.commands.analyze / channel / diff / routing / doctor / feedback` — each `(args) -> int` returning an exit code
  - `wing_parser.cli.__main__.build_parser() -> argparse.ArgumentParser`
  - `wing_parser.cli.__main__.main(argv: list[str] | None = None) -> int`

- [ ] **Step 1: Write the failing test**

`tests/test_cli.py`:

```python
import json
import re

import pytest

from wing_parser.classifier.resolve import Classifier
from wing_parser.cli.__main__ import main
from wing_parser.cli.render import level


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")


def test_level_formats_silence_and_real_values():
    assert level(float("-inf")) == "-inf"
    assert level(-7.9) == "-7.9 dB"
    assert level(0.0) == "0.0 dB"


def test_analyze_prints_an_overview(vu_path, capsys):
    assert main(["analyze", str(vu_path)]) == 0
    out = capsys.readouterr().out
    assert "snapshot.11" in out
    assert "M8 MC" in out
    assert "40 channels" in out


def test_analyze_reports_a_directory_without_a_traceback(tmp_path, capsys):
    assert main(["analyze", str(tmp_path)]) == 1
    assert str(tmp_path) in capsys.readouterr().err


def test_analyze_reports_a_non_object_top_level_without_a_traceback(tmp_path, capsys):
    bad = tmp_path / "bad.snap"
    bad.write_text("[1, 2]", encoding="utf-8")
    assert main(["analyze", str(bad)]) == 1
    assert str(bad) in capsys.readouterr().err


def test_channel_prints_detail(vu_path, capsys):
    assert main(["channel", str(vu_path), "8"]) == 0
    out = capsys.readouterr().out
    assert "M8 MC" in out
    assert "-7.9 dB" in out
    assert "POST_FDR" in out
    assert "speech.mc" in out


def test_channel_reports_an_unknown_number_without_a_traceback(vu_path, capsys):
    assert main(["channel", str(vu_path), "99"]) == 1
    assert "99" in capsys.readouterr().err


def test_doctor_lists_the_findings(vu_path, capsys):
    assert main(["doctor", str(vu_path)]) == 0
    out = capsys.readouterr().out
    assert "17 findings" in out
    assert "G8" in out
    assert "G7" in out
    assert "MON VOX" in out


def test_doctor_shows_the_deciding_layer(vu_path, capsys):
    main(["doctor", str(vu_path)])
    assert "base" in capsys.readouterr().out


def test_doctor_orders_findings_naturally_not_lexicographically(vu_path, capsys):
    main(["doctor", str(vu_path)])
    out = capsys.readouterr().out
    targets = re.findall(r"^\s*\[\S+\s*\]\s+\S+\s+(\S+)\s+via base", out, re.MULTILINE)
    assert targets == [
        "bus.7", "bus.8", "bus.9", "bus.10",
        "ch.1.send.8", "ch.2.send.8", "ch.3.send.8",
        "ch.4.send.7", "ch.4.send.8", "ch.5.send.8",
        "ch.7.send.7", "ch.7.send.8", "ch.8.send.7", "ch.8.send.8",
        "ch.10.send.8", "ch.11", "ch.12.send.8",
    ]


def test_routing_prints_the_summary(vu_path, capsys):
    assert main(["routing", str(vu_path)]) == 0
    out = capsys.readouterr().out
    assert "3 live channels" in out
    unpatched_line = next(line for line in out.splitlines() if "unpatched channels" in line)
    assert len(re.findall(r"\d+", unpatched_line)) == 23


def test_routing_lists_unclassified_channels(vu_path, capsys):
    main(["routing", str(vu_path)])
    assert "My Lap" in capsys.readouterr().out


def test_diff_reports_a_changed_fader(vu_path, tmp_path, capsys):
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"]["8"]["fdr"] = -3.0
    other = tmp_path / "other.snap"
    other.write_text(json.dumps(doc), encoding="utf-8")

    assert main(["diff", str(vu_path), str(other)]) == 0
    assert "ch.8.fader_dB" in capsys.readouterr().out


def test_json_output_is_machine_readable(vu_path, capsys):
    assert main(["doctor", str(vu_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert isinstance(payload, list)
    assert {"rule_id", "layer", "severity", "target", "message"} <= set(payload[0])


def test_feedback_appends_a_verdict(vu_path, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    code = main([
        "feedback", "G8:ch.8.send.8",
        "--verdict", "false-positive",
        "--note", "shared IEM rig",
        "--scene", str(vu_path),
    ])
    assert code == 0
    assert (tmp_path / "feedback.jsonl").exists()
    assert "false-positive" in (tmp_path / "feedback.jsonl").read_text(encoding="utf-8")


def test_feedback_rejects_an_unknown_finding_id(vu_path, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    assert main(["feedback", "ZZ:ch.1", "--verdict", "correct", "--scene", str(vu_path)]) == 1
    assert "ZZ:ch.1" in capsys.readouterr().err


def test_missing_file_reports_cleanly(capsys):
    assert main(["analyze", "no-such-file.snap"]) == 1
    assert "no-such-file.snap" in capsys.readouterr().err


FLUSH_CASES = [
    pytest.param("analyze", lambda vu, tmp: ["analyze", str(vu)], 1, id="analyze"),
    pytest.param("channel", lambda vu, tmp: ["channel", str(vu), "8"], 1, id="channel"),
    pytest.param("doctor", lambda vu, tmp: ["doctor", str(vu)], 1, id="doctor"),
    pytest.param("routing", lambda vu, tmp: ["routing", str(vu)], 1, id="routing"),
    pytest.param(
        "feedback",
        lambda vu, tmp: [
            "feedback", "G8:ch.8.send.8", "--verdict", "correct", "--scene", str(vu),
        ],
        1,
        id="feedback",
    ),
    pytest.param("diff", lambda vu, tmp: ["diff", str(vu), str(vu)], 2, id="diff"),
]


@pytest.mark.parametrize("name, build_argv, expected", FLUSH_CASES)
def test_flush_is_called_by_every_command_that_resolves_names(
    name, build_argv, expected, vu_path, tmp_path, capsys, monkeypatch
):
    # A spy on Classifier.flush, not on what it writes (Task 15 covers that
    # already) — the point is to catch a future edit that silently deletes
    # one of the five call sites in commands.py.
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    calls: list[Classifier] = []
    monkeypatch.setattr(Classifier, "flush", lambda self: calls.append(self))

    assert main(build_argv(vu_path, tmp_path)) == 0
    assert len(calls) == expected, (
        f"{name}: expected {expected} flush() call(s), got {len(calls)}"
    )
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m pytest tests/test_cli.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.cli'`

- [ ] **Step 3: Implement rendering**

Create an empty `wing_parser/cli/__init__.py`, then `wing_parser/cli/render.py`:

```python
"""Turn objects into text. No I/O, no argument parsing."""

from __future__ import annotations

import math
import re
from typing import Any, Iterable

BULLET = "  - "


def level(db: float) -> str:
    return "-inf" if math.isinf(db) else f"{db:.1f} dB"


def _natural(target: str) -> tuple[object, ...]:
    """Sort key that orders ch.2 before ch.10 rather than after it."""
    return tuple(int(part) if part.isdigit() else part
                 for part in re.split(r"(\d+)", target))


def scene_overview(scene) -> str:
    lines = [
        f"{scene.path.name}  [{scene.version.type_id} / {scene.version.label}]",
        f"  {len(scene.channels())} channels, {len(scene.buses())} buses, "
        f"{len(scene.mains())} mains, {len(scene.matrices())} matrices",
    ]
    live = scene.routing.summary().live_channel_count
    lines.append(f"  {live} live channels (unmuted, fader above -inf)")

    named = [ch for ch in scene.channels() if ch.name.strip()]
    lines.append(f"  {len(named)} named channels:")
    for ch in named:
        lines.append(
            f"{BULLET}{ch.number:>2}  {ch.name:<20} {level(ch.fader_dB):>9}  "
            f"{ch.source_type.kind}"
        )

    if scene.anomalies:
        lines.append(f"  {len(scene.anomalies)} anomalies:")
        for anomaly in scene.anomalies:
            lines.append(f"{BULLET}{anomaly.code}: {anomaly.where} — {anomaly.detail}")
    return "\n".join(lines)


def channel_detail(channel) -> str:
    source = channel.source
    lines = [
        f"Channel {channel.number}: {channel.name!r}",
        f"  type        {channel.source_type.kind} "
        f"(confidence {channel.source_type.confidence:.2f}, {channel.source_type.origin})",
        f"  fader       {level(channel.fader_dB)}    muted={channel.muted}",
        f"  chain       {' -> '.join(channel.proc_chain) or '(none)'}",
        f"  tap point   {channel.tap_point}",
        f"  scene safe  {channel.scene_safe}",
        f"  DCAs        {channel.dcas or '(none)'}    mute groups {channel.mute_groups or '(none)'}",
    ]
    if source is None:
        lines.append("  source      not patched")
    else:
        lines.append(
            f"  source      {source.group}:{source.index}  gain {source.gain_dB:.1f} dB  "
            f"phantom={source.phantom}  polarity={source.polarity}"
        )
    lines.append(f"  polarity    effective={channel.effective_polarity}")

    filt = channel.filter
    lines.append(
        f"  HPF         {'on' if filt.low_cut_on else 'off'} "
        f"{filt.low_cut_hz:.0f} Hz  {filt.low_cut_slope} dB/oct"
    )

    if channel.eq.bands is None:
        lines.append(f"  EQ          {channel.eq.model} (no descriptor — bands unparsed)")
    else:
        lines.append(f"  EQ          {channel.eq.model}")
        for band in channel.eq.bands:
            lines.append(
                f"{BULLET}band {band.name:<4} {band.gain:>6.1f} dB  "
                f"{band.freq:>8.1f} Hz  Q {band.q:.2f}"
            )

    live = [s for s in channel.sends if s.on]
    lines.append(f"  sends       {len(live)} active")
    for send in live:
        lines.append(f"{BULLET}-> bus {send.dest:<3} {level(send.level_dB):>9}  {send.mode}")
    return "\n".join(lines)


def findings(items: Iterable[Any], suppressed: dict[str, str] | None = None) -> str:
    items = list(items)
    if not items:
        return "No findings."

    order = {"error": 0, "warning": 1, "info": 2}
    lines: list[str] = [f"{len(items)} findings:"]
    for finding in sorted(items, key=lambda f: (order.get(f.severity, 9), _natural(f.target))):
        confidence = "" if finding.confidence >= 1.0 else f"  (confidence {finding.confidence:.2f})"
        lines.append(
            f"  [{finding.severity:<7}] {finding.rule_id:<6} {finding.target:<18} "
            f"via {finding.layer}{confidence}"
        )
        lines.append(f"      {' '.join(finding.message.split())}")

    for rule_id, by in (suppressed or {}).items():
        lines.append(f"  [suppressed] {rule_id} switched off by {by}")
    return "\n".join(lines)


def routing(summary, unclassified: Iterable[Any]) -> str:
    lines = [
        f"{summary.live_channel_count} live channels",
        f"  orphans (live, feeding nothing): {summary.orphan_channels or '(none)'}",
        f"  alt-sourced channels:            {summary.alt_sourced_channels or '(none)'}",
        f"  unpatched channels:              {summary.unpatched_channels or '(none)'}",
        f"  live but unnamed:                {summary.unnamed_but_live or '(none)'}",
    ]
    unclassified = list(unclassified)
    if unclassified:
        lines.append(f"  {len(unclassified)} could not be classified — name them more")
        lines.append("  descriptively, or declare them in knowledge/toanaz/classifier.yaml:")
        for view in unclassified:
            lines.append(f"{BULLET}{view.name!r}")
    return "\n".join(lines)


def changes(items: Iterable[Any], limit: int = 50) -> str:
    items = sorted(items, key=lambda change: _natural(change.path))
    if not items:
        return "No differences."

    lines = [f"{len(items)} differences:"]
    for change in items[:limit]:
        magnitude = f"  (delta {change.magnitude:.2f})" if change.magnitude else ""
        lines.append(f"  {change.path}: {change.before!r} -> {change.after!r}{magnitude}")
    if len(items) > limit:
        lines.append(f"  ... {len(items) - limit} more (raise --limit to see them)")
    return "\n".join(lines)
```

Fix wave (2026-08-14): `findings()` already got the `_natural` sort key
above to fix lexicographic ordering of numbered targets; `changes()`
kept sorting its diff paths lexicographically (send 16 before send 2).
Reuses the same key. Covered by
`test_changes_orders_numbered_sends_naturally_not_lexicographically` in
`tests/test_cli.py`.

- [ ] **Step 4: Implement the commands**

`wing_parser/cli/commands.py`:

```python
"""One function per command. Each returns a process exit code."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

from wing_parser import WingScene
from wing_parser.advisory import feedback as feedback_log
from wing_parser.cli import render


def _load(path: str) -> WingScene | None:
    try:
        return WingScene.load(path)
    except OSError:
        print(f"error: cannot open {path}", file=sys.stderr)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
    return None


def _run_advisory(scene: WingScene) -> list | None:
    """Run the advisory rules, turning a hand-edited rule file's error
    into the same `error: <message>` shape `_load` already gives a bad
    scene file, instead of a traceback. `scene.advisory.run()` reads and
    validates `principles.yaml` and every show file on every call, so a
    typo'd `supersedes` id, a rule missing `id:`, a bare-string list
    entry, an unknown predicate operator, an unknown `for_each`, or a
    YAML syntax error can all still surface here — this is the CLI's
    copy of the same guard the MCP `_guard` decorator already gives
    those tools.
    """
    try:
        return scene.advisory.run()
    except (KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return None


def analyze(args) -> int:
    scene = _load(args.file)
    if scene is None:
        return 1
    print(render.scene_overview(scene))
    scene.classifier.flush()
    return 0


def channel(args) -> int:
    scene = _load(args.file)
    if scene is None:
        return 1
    try:
        view = scene.channel(args.number)
    except KeyError as exc:
        print(f"error: {exc.args[0]}", file=sys.stderr)
        return 1
    print(render.channel_detail(view))
    scene.classifier.flush()
    return 0


def doctor(args) -> int:
    scene = _load(args.file)
    if scene is None:
        return 1
    found = _run_advisory(scene)
    if found is None:
        return 1
    if getattr(args, "json", False):
        print(json.dumps([asdict(f) for f in found], indent=2, ensure_ascii=False))
    else:
        print(render.findings(found, scene.advisory.suppressed()))
    scene.classifier.flush()
    return 0


def routing(args) -> int:
    scene = _load(args.file)
    if scene is None:
        return 1
    print(render.routing(scene.routing.summary(), scene.unclassified()))
    scene.classifier.flush()
    return 0


def diff(args) -> int:
    before, after = _load(args.before), _load(args.after)
    if before is None or after is None:
        return 1
    print(render.changes(before.diff(after), limit=args.limit))
    before.classifier.flush()
    after.classifier.flush()
    return 0


def feedback(args) -> int:
    scene = _load(args.scene)
    if scene is None:
        return 1

    findings = _run_advisory(scene)
    if findings is None:
        return 1

    match = next(
        (f for f in findings if feedback_log.finding_id(f) == args.finding_id),
        None,
    )
    if match is None:
        print(
            f"error: no finding {args.finding_id!r} in {Path(args.scene).name}; "
            "run `wing doctor` to list current findings",
            file=sys.stderr,
        )
        scene.classifier.flush()
        return 1

    entry = feedback_log.record(
        match, args.verdict, note=args.note, scene=Path(args.scene).name
    )
    print(f"recorded {entry.verdict} for {entry.finding_id}")
    scene.classifier.flush()
    return 0
```

Fix wave (2026-08-14): `scene.advisory.run()` used to sit outside every
CLI handler's try/except, so a hand-edited `principles.yaml` or show
file reached the user as a traceback for six distinct slips (a typo'd
`supersedes` id, a rule missing `id:`, a bare-string list entry, an
unknown predicate operator, an unknown `for_each`, a YAML syntax error).
`doctor` and `feedback` now route through `_run_advisory` above, closing
deferred minors T18-2 and T18-6 — the CLI and the MCP `_guard` in
`wing_parser/mcp/tools.py` are once again the same idea in two places
instead of a drifted copy. Covered by
`test_doctor_reports_a_typo_d_supersedes_id_without_a_traceback` and
`test_feedback_reports_a_yaml_syntax_error_without_a_traceback` in
`tests/test_cli.py`, plus the load-time validation tests in
`tests/test_advisory_predicates.py` and `tests/test_advisory_resolver.py`.

- [ ] **Step 5: Implement the argument parser**

`wing_parser/cli/__main__.py`:

```python
"""Argument wiring only. Behaviour lives in commands.py, text in render.py."""

from __future__ import annotations

import argparse
import sys

from wing_parser import __version__
from wing_parser.advisory.feedback import VERDICTS
from wing_parser.cli import commands


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wing", description="Read and analyse Behringer WING .snap scene files"
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("analyze", "overview of a scene"),
        ("routing", "routing map, orphans and unclassified channels"),
    ):
        node = sub.add_parser(name, help=help_text)
        node.add_argument("file")
        node.set_defaults(handler=getattr(commands, name))

    node = sub.add_parser("channel", help="full detail for one channel")
    node.add_argument("file")
    node.add_argument("number", type=int)
    node.set_defaults(handler=commands.channel)

    node = sub.add_parser("doctor", help="advisory findings only")
    node.add_argument("file")
    node.add_argument("--json", action="store_true", help="machine-readable output")
    node.set_defaults(handler=commands.doctor)

    node = sub.add_parser("diff", help="compare two scenes")
    node.add_argument("before")
    node.add_argument("after")
    node.add_argument("--limit", type=int, default=50)
    node.set_defaults(handler=commands.diff)

    node = sub.add_parser("feedback", help="record a verdict on a finding")
    node.add_argument("finding_id", help="for example G8:ch.8.send.8")
    node.add_argument("--verdict", required=True, choices=VERDICTS)
    node.add_argument("--scene", required=True, help="the .snap the finding came from")
    node.add_argument("--note", default="")
    node.set_defaults(handler=commands.feedback)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 6: Run the test and verify it passes**

Run: `python -m pytest tests/test_cli.py -v`
Expected: PASS — 22 tests (13 from the original pass; 3 added in fix round 1:
a directory input, a non-object top-level JSON input, and natural-order
sorting of `doctor` findings; 6 added in fix round 2, one parametrized case
per command, spying on `Classifier.flush` to prove each command that
resolves names actually persists the cache)

- [ ] **Step 7: Try it by hand**

Run: `python -m wing_parser.cli doctor user-files/example-Vu.snap`
Expected: G8 fires on `ch.8.send.8` and G7 on `bus.8`, each tagged `via base`.

- [ ] **Step 8: Commit**

```bash
git add wing_parser/cli/ tests/test_cli.py
git commit -m "Add the CLI

Six commands. Rendering is a separate module from dispatch: text is the
interface surface, argparse is wiring, and mixing them is what makes a
CLI file grow. Missing files and unknown channel numbers report cleanly
instead of raising a traceback."
```

---

## Task 23: MCP server

**Files:**
- Create: `wing_parser/mcp/__init__.py`
- Create: `wing_parser/mcp/tools.py`
- Create: `wing_parser/mcp/server.py`
- Test: `tests/test_mcp.py`

Tool bodies live in `tools.py` as plain functions so they are testable without a running server; `server.py` only registers them with FastMCP.

**Interfaces:**
- Consumes: `WingScene` (Task 10), `render` (Task 22)
- Produces:
  - `wing_parser.mcp.tools.TOOLS: dict[str, Callable[..., str]]`
  - `wing_parser.mcp.tools.analyze(path) / channel(path, number) / diff(before, after) / routing(path) / doctor(path)` — each returns a string, each catches its own failures
  - `wing_parser.mcp.server.build() -> FastMCP`
  - `wing_parser.mcp.server.main() -> None` — runs over stdio

- [ ] **Step 1: Write the failing test**

`tests/test_mcp.py`:

```python
import inspect
import json

import pytest

from wing_parser.mcp import tools


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")


def test_five_tools_are_registered():
    assert set(tools.TOOLS) == {
        "wing_analyze", "wing_channel", "wing_diff", "wing_routing", "wing_doctor"
    }


def test_every_tool_has_a_docstring_claude_can_read():
    for name, function in tools.TOOLS.items():
        assert function.__doc__, f"{name} has no docstring"
        assert len(function.__doc__.strip()) > 60, f"{name} docstring is too thin"


def test_analyze_returns_text(vu_path):
    out = tools.analyze(str(vu_path))
    assert "snapshot.11" in out


def test_channel_returns_detail(vu_path):
    out = tools.channel(str(vu_path), 8)
    assert "M8 MC" in out
    assert "speech.mc" in out


def test_doctor_returns_the_findings(vu_path):
    out = tools.doctor(str(vu_path))
    assert "G8" in out and "G7" in out


def test_routing_returns_the_summary(vu_path):
    # "live" alone also appears in scene_overview's "N live channels
    # (unmuted, ...)" line, so a miswired tool calling the wrong renderer
    # would still pass that check. Assert text only routing() produces.
    out = tools.routing(str(vu_path))
    assert "3 live channels" in out
    assert "unpatched channels" in out


def test_diff_returns_changes(vu_path, tmp_path):
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"]["8"]["fdr"] = -3.0
    other = tmp_path / "other.snap"
    other.write_text(json.dumps(doc), encoding="utf-8")

    assert "ch.8.fader_dB" in tools.diff(str(vu_path), str(other))


def test_a_missing_file_returns_a_message_not_an_exception():
    out = tools.analyze("no-such-file.snap")
    assert "no-such-file.snap" in out
    assert out.lower().startswith("error")


def test_an_unknown_channel_returns_a_message(vu_path):
    out = tools.channel(str(vu_path), 99)
    assert "99" in out
    assert out.lower().startswith("error")


def test_a_directory_returns_a_message_not_an_exception(tmp_path):
    # analyze() opens a directory path, which raises PermissionError (an
    # OSError subclass) rather than FileNotFoundError — Task 22's own
    # loader guard covers this one layer up in cli/commands.py, and the
    # MCP tools need the same net so nothing crosses the MCP boundary.
    out = tools.analyze(str(tmp_path))
    assert out.lower().startswith("error")


def test_every_tool_keeps_the_signature_fastmcp_introspects():
    """FastMCP builds each tool's input schema from the signature, so a
    *args/**kwargs wrapper would register five tools with no parameters."""
    assert list(inspect.signature(tools.channel).parameters) == ["path", "number"]
    assert list(inspect.signature(tools.diff).parameters) == ["before", "after"]
    for name, function in tools.TOOLS.items():
        parameters = inspect.signature(function).parameters
        assert parameters, f"{name} exposes no parameters"
        assert "args" not in parameters and "kwargs" not in parameters, name


def test_server_builds_when_the_mcp_package_is_installed():
    pytest.importorskip("mcp")
    from wing_parser.mcp.server import build

    assert build() is not None
```

- [ ] **Step 2: Run the test and verify it fails**

Run: `python -m pytest tests/test_mcp.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.mcp'`

- [ ] **Step 3: Implement the tool bodies**

Create an empty `wing_parser/mcp/__init__.py`, then `wing_parser/mcp/tools.py`:

```python
"""Tool bodies, as plain functions.

Kept out of server.py so they are testable without a running server.
Each returns a string and swallows its own failures: an exception
crossing the MCP boundary is far less useful to Claude than a sentence
saying what went wrong.

Docstrings here are the tool descriptions Claude reads to decide which
tool to call, so they say when to use each one, not just what it does.
"""

from __future__ import annotations

import functools
from typing import Callable

from wing_parser import WingScene
from wing_parser.cli import render


def _guard(function):
    @functools.wraps(function)
    def wrapper(*args, **kwargs) -> str:
        try:
            return function(*args, **kwargs)
        except OSError as exc:
            # exc.filename is always set: every OSError caught here comes
            # from Path.read_text (via WingScene.load), which sets it on
            # every failure mode. args[0] would be wrong for diff(before,
            # after) if it were ever needed, since the failing path is not
            # necessarily the first argument -- correct even though the
            # fallback cannot fire today.
            return f"error: cannot open {exc.filename}"
        except (KeyError, ValueError) as exc:
            return f"error: {exc}"

    return wrapper


@_guard
def analyze(path: str) -> str:
    """Overview of a WING .snap scene file.

    Use this first when asked anything general about a scene: how many
    channels are in use, what they are named, what the file's firmware
    version is, and whether the parser found anomalies. Returns a
    channel list with levels and inferred source types.
    """
    scene = WingScene.load(path)
    out = render.scene_overview(scene)
    scene.classifier.flush()
    return out


@_guard
def channel(path: str, number: int) -> str:
    """Full detail for one input channel, 1 to 40.

    Use when a question is about a specific channel: its EQ curve, gate
    and dynamics settings, high-pass filter, preamp gain, phantom power,
    polarity, tap point, DCA and mute-group membership, or which buses
    it feeds.
    """
    scene = WingScene.load(path)
    out = render.channel_detail(scene.channel(number))
    scene.classifier.flush()
    return out


@_guard
def diff(before: str, after: str) -> str:
    """Field-by-field comparison of two scene files.

    Use when asked what changed between two scenes, for example a
    factory default and a show file, or last night's file and tonight's.
    Paths read in decoded terms such as ch.8.fader_dB, and level changes
    carry a magnitude in dB.
    """
    before_scene = WingScene.load(before)
    after_scene = WingScene.load(after)
    out = render.changes(before_scene.diff(after_scene))
    # compare() walks raw dataclasses today and never resolves a name, so
    # these flushes are inert — but the CLI's diff command flushes both
    # scenes (and is spy-tested for it), and the day diff output gains a
    # classified field this keeps the two surfaces from silently diverging.
    before_scene.classifier.flush()
    after_scene.classifier.flush()
    return out


@_guard
def routing(path: str) -> str:
    """Routing summary for a scene.

    Use when asked how signal flows: which live channels feed nothing,
    which use an ALT input, which are unpatched or unnamed. Also lists
    channels and buses whose source type could not be inferred from
    their names.
    """
    scene = WingScene.load(path)
    out = render.routing(scene.routing.summary(), scene.unclassified())
    scene.classifier.flush()
    return out


@_guard
def doctor(path: str) -> str:
    """Run the advisory rules and report likely misconfigurations.

    Use when asked to check, review, or find problems in a scene. Each
    finding names the rule, the target, and which rule layer decided it
    (base for generic industry practice, toanaz for personal principles,
    show for one-off overrides). Rules switched off by a higher layer are
    listed too.
    """
    scene = WingScene.load(path)
    out = render.findings(scene.advisory.run(), scene.advisory.suppressed())
    scene.classifier.flush()
    return out


TOOLS: dict[str, Callable[..., str]] = {
    "wing_analyze": analyze,
    "wing_channel": channel,
    "wing_diff": diff,
    "wing_routing": routing,
    "wing_doctor": doctor,
}
```

Fix wave (2026-08-14): `_guard`'s OSError handler dropped the
`or args[0]` fallback, which would have misattributed the path for the
two-argument `diff` tool had it ever fired. Covered by
`test_diff_names_the_second_file_when_it_is_the_one_missing` in
`tests/test_mcp.py`.

- [ ] **Step 4: Implement the server**

`wing_parser/mcp/server.py`:

```python
"""FastMCP wiring over stdio. Registration only — behaviour is in tools.py."""

from __future__ import annotations

import sys

from wing_parser.mcp import tools


def build():
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("wing-parser")
    for name, function in tools.TOOLS.items():
        server.add_tool(function, name=name, description=function.__doc__ or "")
    return server


def main() -> None:
    try:
        server = build()
    except ImportError:
        print(
            'error: the mcp extra is not installed. Run: pip install "wing-parser[mcp]"',
            file=sys.stderr,
        )
        raise SystemExit(1)
    server.run()


if __name__ == "__main__":
    main()
```

If `add_tool` is not present on the installed FastMCP version, register with the decorator form instead — `server.tool(name=name, description=...)(function)` — and keep the loop otherwise unchanged. Check `python -c "from mcp.server.fastmcp import FastMCP; print([m for m in dir(FastMCP) if 'tool' in m])"` before editing.

Confirmed against the MCP Python SDK source during review: `ToolManager.add_tool(fn, name=None, title=None, description=None, ...)` exists, and `FastMCP.tool()` is itself implemented as a decorator that calls exactly that — so the `add_tool(function, name=name, description=...)` form above is correct as written and does not need to fall back to the decorator form.

Fix wave (2026-08-14): `main()` used to let a bare `ImportError` from
`build()` (raised when the optional `mcp` extra is not installed)
propagate straight out of the `wing-mcp` console script. It now catches
that specific case and prints the fix (`pip install "wing-parser[mcp]"`)
instead. Covered by `test_main_names_the_fix_when_the_mcp_extra_is_missing`
in `tests/test_mcp.py`, which only runs when `mcp` is genuinely absent
(it is, deliberately, in this project's own test environment).

- [ ] **Step 5: Add the console script**

In `pyproject.toml`, under `[project.scripts]`, add:

```toml
wing-mcp = "wing_parser.mcp.server:main"
```

- [ ] **Step 6: Run the test and verify it passes**

Run: `python -m pytest tests/test_mcp.py -v`
Expected: PASS — 12 tests. The last one skips if `mcp` is not installed.

- [ ] **Step 7: Commit**

```bash
git add wing_parser/mcp/ pyproject.toml tests/test_mcp.py
git commit -m "Add the MCP server

Five tools rather than one with an action parameter, so Claude selects
by reading each description instead of guessing a parameter value. Tool
bodies are plain functions in tools.py, testable without a server, and
each swallows its own failures — an exception crossing the MCP boundary
tells Claude less than a sentence saying what went wrong."
```

---

## Task 24: Skills, examples, and README

**Files:**
- Create: `skills/wing-analyze/SKILL.md`
- Create: `skills/wing-channel/SKILL.md`
- Create: `skills/wing-diff/SKILL.md`
- Create: `skills/wing-routing/SKILL.md`
- Create: `skills/wing-doctor/SKILL.md`
- Create: `examples/analyze_vu.py`
- Create: `examples/diff_factory_vs_vu.py`
- Create: `examples/advisory_check.py`
- Create: `README.md`
- Test: `tests/test_examples.py`

**Interfaces:**
- Consumes: the CLI (Task 22)
- Produces: no importable API — documentation and runnable examples

- [ ] **Step 1: Write the skills**

Each `SKILL.md` uses the same shape. `skills/wing-doctor/SKILL.md`:

```markdown
---
name: wing-doctor
description: Use when asked to check, review, audit, or find problems in a Behringer WING .snap scene file — runs the advisory rules and reports likely misconfigurations with the rule layer that decided each one.
---

# Checking a WING scene for problems

Run:

```bash
python -m wing_parser.cli doctor <path-to-.snap>
```

Add `--json` when you need to process the findings rather than show them.

## Reading the output

Each finding carries:

- **rule id** — `G8`, `G7`, `E6`
- **target** — `ch.8.send.8`, `bus.8`
- **layer** — which rule layer decided:
  - `base` — generic industry practice mined from the knowledge base
  - `toanaz` — ToanAZ's personal principles, which override base rules
  - `show` — a one-off override for this specific show
- **confidence** — present only when the rule depended on inferring what a
  channel or bus is from its name. Below 1.0, word the finding as a
  question rather than an assertion.

Rules switched off by a higher layer are listed as `[suppressed]` with the
rule that switched them off. That line is information, not a problem.

## What this does not check

The advisory reads the scene file only. Anything needing measurement —
gain staging in dBFS, LUFS, RT60, real-world latency, gain-reduction
meters — is out of scope and is deliberately not reported. Do not infer
from a clean report that those are fine.

## Recording a verdict

When ToanAZ says a finding is wrong, record it:

```bash
python -m wing_parser.cli feedback G8:ch.8.send.8 --verdict false-positive \
  --scene <path-to-.snap> --note "shared band IEM, guitar is the exception"
```

Verdicts are `correct`, `false-positive`, `irrelevant`. They append to
`knowledge/toanaz/feedback.jsonl`. Read that log across several shows to
spot a pattern worth turning into a principle in
`knowledge/toanaz/principles.yaml`.
```

The other four follow the same template with these front-matter descriptions and command lines:

| Skill | `description` | Command |
|---|---|---|
| `wing-analyze` | Use when asked for an overview of a Behringer WING .snap scene file — channel count, names, levels, inferred source types, firmware version, and parser anomalies. | `python -m wing_parser.cli analyze <file>` |
| `wing-channel` | Use when asked about one specific channel in a WING .snap file — its EQ, gate, dynamics, high-pass filter, preamp gain, phantom power, polarity, tap point, group membership, or sends. | `python -m wing_parser.cli channel <file> <n>` |
| `wing-diff` | Use when asked what changed between two WING .snap scene files. | `python -m wing_parser.cli diff <before> <after>` |
| `wing-routing` | Use when asked how signal flows through a WING scene — orphaned channels, ALT-sourced channels, unpatched or unnamed channels, and anything the classifier could not identify. | `python -m wing_parser.cli routing <file>` |

Each body explains how to read that command's output and repeats the "what this does not check" caveat.

- [ ] **Step 2: Write the examples**

`examples/analyze_vu.py`:

```python
"""Print an overview of the sample show scene."""

from pathlib import Path

from wing_parser import WingScene

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    scene = WingScene.load(REPO / "user-files" / "example-Vu.snap")
    print(f"{scene.path.name}: {scene.version.label}")

    for channel in scene.channels():
        if not channel.name.strip():
            continue
        guess = channel.source_type
        print(
            f"{channel.number:>3}  {channel.name:<20} "
            f"{guess.kind:<28} {guess.confidence:.2f}"
        )

    scene.classifier.flush()


if __name__ == "__main__":
    main()
```

`examples/diff_factory_vs_vu.py`:

```python
"""Show what a real show scene changed relative to the factory default."""

from pathlib import Path

from wing_parser import WingScene

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    factory = WingScene.load(REPO / "user-files" / "factory-scene.snap")
    show = WingScene.load(REPO / "user-files" / "example-Vu.snap")

    changes = factory.diff(show)
    print(f"{len(changes)} differences")

    faders = [c for c in changes if c.path.endswith(".fader_dB") and c.magnitude]
    print(f"\n{len(faders)} fader moves, largest first:")
    for change in sorted(faders, key=lambda c: -c.magnitude)[:10]:
        print(f"  {change.path:<24} {change.before} -> {change.after}")


if __name__ == "__main__":
    main()
```

`examples/advisory_check.py`:

```python
"""Run the advisory rules and show which layer decided each finding."""

from pathlib import Path

from wing_parser import WingScene

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    scene = WingScene.load(REPO / "user-files" / "example-Vu.snap")

    print("active rules:")
    for rule in scene.advisory.rules():
        print(f"  {rule.id:<8} [{rule.layer}] {rule.title}")

    suppressed = scene.advisory.suppressed()
    for rule_id, by in suppressed.items():
        print(f"  {rule_id:<8} suppressed by {by}")

    print("\nfindings:")
    for finding in scene.advisory.run():
        print(f"  [{finding.severity}] {finding.rule_id} at {finding.target} via {finding.layer}")
        print(f"      {' '.join(finding.message.split())}")

    scene.classifier.flush()


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Write the failing test**

`tests/test_examples.py`:

```python
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
EXAMPLES = REPO / "examples"


@pytest.mark.parametrize(
    "script", ["analyze_vu.py", "diff_factory_vs_vu.py", "advisory_check.py"]
)
def test_example_runs_cleanly(script, tmp_path, monkeypatch):
    env = {
        **dict(__import__("os").environ),
        "WING_DISABLE_LLM": "1",
        "WING_KNOWLEDGE_DIR": str(tmp_path),
        "PYTHONPATH": str(REPO),
    }
    result = subprocess.run(
        [sys.executable, str(EXAMPLES / script)],
        capture_output=True, text=True, env=env, cwd=REPO,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip()


def test_every_skill_has_front_matter_and_a_command():
    for skill_dir in sorted((REPO / "skills").iterdir()):
        body = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        assert body.startswith("---"), skill_dir.name
        assert "description:" in body, skill_dir.name
        assert "python -m wing_parser.cli" in body, skill_dir.name


def test_five_skills_ship():
    assert len(list((REPO / "skills").iterdir())) == 5
```

- [ ] **Step 4: Write the README**

`README.md` covers, in this order: what the tool does and its Phase 1 scope; install (`pip install -e ".[dev,llm,mcp]"`); the six CLI commands with one example each; the three-layer advisory model and where `knowledge/toanaz/` lives, including the `WING_KNOWLEDGE_DIR` search order; the offline guarantee and what degrades without an API key; how to add a rule, a principle, and a descriptor without touching Python; and a pointer to the spec at `docs/superpowers/specs/2026-08-13-wing-scene-skill-design.md`.

- [ ] **Step 5: Run the test and verify it passes**

Run: `python -m pytest tests/test_examples.py -v`
Expected: PASS — 5 tests

- [ ] **Step 6: Run the entire suite with coverage**

Run: `python -m pytest --cov=wing_parser --cov=wing_parser.core --cov-report=term-missing`
Expected: every test passes; `wing_parser/core` coverage at or above 80%.

- [ ] **Step 7: Walk the spec's success criteria**

Open `docs/superpowers/specs/2026-08-13-wing-scene-skill-design.md` section 13 and confirm each of the seventeen checkboxes against the code. Anything unproven gets a test now, not a note.

- [ ] **Step 8: Commit**

```bash
git add skills/ examples/ README.md tests/test_examples.py
git commit -m "Add the five Claude Skills, runnable examples and the README

Each skill description says when to reach for it and how to read the
output, and each repeats what the advisory cannot check — a clean report
does not mean gain staging or room acoustics are fine, only that nothing
in the file looked wrong."
```

**Milestone 5. Phase 1 complete.**
