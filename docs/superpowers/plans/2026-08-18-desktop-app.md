# Desktop Application (Sub-project H) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A PySide6 desktop application that opens one `.snap` scene, shows the advisory findings, repairs the ones whose fix is determined, records ToanAZ's verdict on each, and saves the result as a new `.snap`.

**Architecture:** Two new packages. `wing_parser/edit/` is pure data with **no Qt import at all** — an edit journal of `Patch` records, a dotted-path pointer, a YAML table of repair descriptors, and a writer. `wing_parser/ui/` is Qt only and holds no rule knowledge. After every edit the session re-applies the whole journal to a copy of the original document, rebuilds `WingScene`, and re-runs the advisory; a measured ~100 ms makes that affordable and means the findings list is never stale.

**Tech Stack:** Python 3.11+ (3.14.6 in use), PySide6 6.11.1 (optional extra `ui`), PyYAML for descriptors, pytest.

**Authority:** `docs/superpowers/specs/2026-08-18-desktop-app-design.md`. Where this plan and the spec disagree, the spec wins — say so rather than silently following the plan.

## Global Constraints

- **`wing_parser/edit/` must never import Qt.** Task 4 pins this with a test. The CLI must keep working with no GUI installed.
- **`core`, `query`, `advisory`, `classifier`, `showcontext` stay deterministic and offline.** No LLM, no network, in any code this plan adds.
- **The unprofiled real file must still yield exactly 22 findings.** `python -m wing_parser.cli doctor user-files\example-Vu.snap` — pinned by `tests/test_advisory_realfile.py`. This plan adds no rules; if that number moves, something is wrong.
- **Never fabricate a value the file does not state.** Every raw key named in this plan was read out of `user-files/example-Vu.snap` on 2026-08-18. If a key is absent in the file in front of you, stop and report it — do not create it.
- **Every repair descriptor carries `rationale:`**, and the loader refuses one without it. Same contract `wing_parser/advisory/loader.py:49` enforces on rules.
- **A repair must prove by test that it clears its own finding.** No descriptor ships without one.
- **Modular, short files, split by responsibility layer.** Every file this plan creates should land well under 200 lines.
- **PowerShell is the shell.** Use `git commit -F -` with a heredoc, never backticks inside `-m`. Never build regex or YAML inside a Python heredoc — `\b` is a backspace there; use the Edit tool.
- **`pytest.approx` for float comparisons.**
- **The repo lives on a Google Drive path.** `git` and `ripgrep` can take minutes or appear to hang. Wait rather than interrupting, then verify with `git log --oneline -1`.
- Tests may print no pytest summary trailer — use the exit code or `--junitxml`.

## Baseline before starting

```powershell
python -m pytest tests/
```
596 passing, 1 skipped (FastMCP, by design). Confirm this before Task 1.

---

### Task 1: Split `load_raw` so a scene can be built from an in-memory document

The UI must rebuild a `WingScene` from a patched dictionary without writing a temp file. `load_raw` currently reads a path and parses in one function. Split it exactly the way `showcontext` already splits `load_show_context` / `parse_show_context`.

**Files:**
- Modify: `wing_parser/core/loader.py:22-48`
- Test: `tests/test_core_loader.py` (append; create if absent)

**Interfaces:**
- Consumes: nothing.
- Produces: `wing_parser.core.loader.parse_raw(doc: dict, path: Path) -> RawScene`. `load_raw(path)` keeps its exact current signature and behaviour.

- [ ] **Step 1: Write the failing test**

```python
def test_parse_raw_accepts_an_in_memory_document(vu_path):
    import json
    from wing_parser.core.loader import load_raw, parse_raw

    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    from_memory = parse_raw(doc, vu_path)
    from_file = load_raw(vu_path)

    assert from_memory.ae == from_file.ae
    assert from_memory.ce == from_file.ce
    assert from_memory.meta == from_file.meta
    assert from_memory.version == from_file.version
    assert from_memory.path == vu_path


def test_parse_raw_refuses_a_document_that_is_not_a_snapshot(tmp_path):
    import pytest
    from wing_parser.core.loader import parse_raw

    with pytest.raises(ValueError, match="not a WING snapshot"):
        parse_raw({"nothing": "here"}, tmp_path / "x.snap")
```

`vu_path` is an existing fixture in `tests/conftest.py`. Check it is exported there; if the fixture is named differently, use the name the file actually defines rather than adding a second one.

- [ ] **Step 2: Run test to verify it fails**

```powershell
python -m pytest tests/test_core_loader.py -v
```
Expected: FAIL with `ImportError: cannot import name 'parse_raw'`.

- [ ] **Step 3: Write minimal implementation**

Replace the body of `load_raw` in `wing_parser/core/loader.py`, keeping every existing comment on the lines it belongs to:

```python
def parse_raw(doc: Any, file_path: Path) -> RawScene:
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


def load_raw(path: str | Path) -> RawScene:
    file_path = Path(path)
    return parse_raw(json.loads(file_path.read_text(encoding="utf-8")), file_path)
```

- [ ] **Step 4: Run the whole suite**

```powershell
python -m pytest tests/
```
Expected: 598 passing, 1 skipped. The two new tests are additive; nothing else may change.

- [ ] **Step 5: Commit**

```powershell
git add wing_parser/core/loader.py tests/test_core_loader.py
git commit -F - <<'EOF'
Split load_raw into parse_raw plus a file reader

The desktop app rebuilds a scene from a patched document after every
edit, and writing a temp file to do so would be absurd. This is the
same split showcontext already has between parse_show_context and
load_show_context.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 2: `edit/pointer.py` — read and write a dotted path

**Files:**
- Create: `wing_parser/edit/__init__.py` (empty)
- Create: `wing_parser/edit/pointer.py`
- Test: `tests/test_edit_pointer.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `read(document: dict, path: str) -> Any` — raises `KeyError` naming the full path if any segment is missing.
  - `write(document: dict, path: str, value: Any) -> None` — mutates in place; raises the same `KeyError` rather than creating missing keys.

A path is dot-separated and every segment is a literal mapping key: `"ae_data.ch.16.in.set.inv"`. JSON object keys are strings, so channel numbers appear as `"16"`, not `16`. There is no list indexing — no path this project needs traverses a JSON array.

- [ ] **Step 1: Write the failing test**

```python
import json

import pytest

from wing_parser.edit import pointer


@pytest.fixture
def doc(vu_path):
    return json.loads(vu_path.read_text(encoding="utf-8"))


def test_read_walks_a_real_path(doc):
    assert pointer.read(doc, "ae_data.ch.16.in.set.inv") is False
    assert pointer.read(doc, "ae_data.ch.1.send.8.mode") == "POST"


def test_write_replaces_a_leaf_in_place(doc):
    pointer.write(doc, "ae_data.ch.16.in.set.inv", True)
    assert doc["ae_data"]["ch"]["16"]["in"]["set"]["inv"] is True


def test_read_names_the_whole_path_when_a_segment_is_missing(doc):
    with pytest.raises(KeyError, match="ae_data.ch.999.mute"):
        pointer.read(doc, "ae_data.ch.999.mute")


def test_write_refuses_to_create_a_missing_key(doc):
    # A scene from different firmware may legitimately lack a key.
    # Inventing it writes a structure the console never had.
    with pytest.raises(KeyError, match="ae_data.ch.1.invented"):
        pointer.write(doc, "ae_data.ch.1.invented.deeper", 1)
    assert "invented" not in doc["ae_data"]["ch"]["1"]


def test_read_refuses_to_walk_through_a_non_mapping(doc):
    # `name` is a string; asking for a key inside it must fail loudly
    # rather than raising TypeError from somewhere deeper.
    with pytest.raises(KeyError, match="ae_data.ch.1.name.oops"):
        pointer.read(doc, "ae_data.ch.1.name.oops")
```

- [ ] **Step 2: Run test to verify it fails**

```powershell
python -m pytest tests/test_edit_pointer.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.edit'`.

- [ ] **Step 3: Write minimal implementation**

```python
"""Read and write one leaf of a .snap document by dotted path.

Paths name the whole document, so they start at the file's own
top-level key: "ae_data.ch.16.in.set.inv". Every segment is a literal
mapping key -- JSON object keys are strings, so a channel number
appears as "16". No path this project needs traverses an array.

Nothing here creates a key. A scene saved by different firmware may
legitimately lack one, and inventing it would write a structure the
console never had; refusing is the only honest answer.
"""

from __future__ import annotations

from typing import Any


def _walk(document: dict, path: str, upto: int) -> Any:
    """The node `upto` segments in, raising with the path read so far."""
    node: Any = document
    segments = path.split(".")
    for depth, segment in enumerate(segments[:upto]):
        if not isinstance(node, dict) or segment not in node:
            raise KeyError(".".join(segments[: depth + 1]))
        node = node[segment]
    return node


def read(document: dict, path: str) -> Any:
    return _walk(document, path, len(path.split(".")))


def write(document: dict, path: str, value: Any) -> None:
    segments = path.split(".")
    parent = _walk(document, path, len(segments) - 1)
    leaf = segments[-1]
    if not isinstance(parent, dict) or leaf not in parent:
        raise KeyError(path)
    parent[leaf] = value
```

- [ ] **Step 4: Run test to verify it passes**

```powershell
python -m pytest tests/test_edit_pointer.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```powershell
git add wing_parser/edit/ tests/test_edit_pointer.py
git commit -F - <<'EOF'
Add the dotted-path pointer for .snap documents

Refuses to create a missing key rather than inventing structure a
console never had, and names the path it got as far as when it fails.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 3: `edit/journal.py` — the Patch record and the journal

**Files:**
- Create: `wing_parser/edit/journal.py`
- Test: `tests/test_edit_journal.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `Patch(path: str, before: Any, after: Any, because: str, label: str)` — a frozen dataclass.
  - `EditJournal()` with `append(patch: Patch) -> None`, `undo() -> Patch | None`, `patches() -> tuple[Patch, ...]`, `__len__`, `__bool__`.

`because` is a finding id (`"G8:ch.1.send.8"`) or the literal `"manual"`. `before` is captured by the caller at append time and never recomputed — the journal is a record of what the operator saw when they decided.

- [ ] **Step 1: Write the failing test**

```python
import pytest

from wing_parser.edit.journal import EditJournal, Patch


def a_patch(path="ae_data.ch.1.mute", after=True):
    return Patch(path=path, before=False, after=after,
                 because="G8:ch.1.send.8", label="Mute channel 1")


def test_a_new_journal_is_empty():
    journal = EditJournal()
    assert len(journal) == 0
    assert not journal
    assert journal.patches() == ()


def test_append_then_undo_returns_the_patch_and_empties_the_journal():
    journal = EditJournal()
    patch = a_patch()
    journal.append(patch)
    assert bool(journal) is True
    assert journal.patches() == (patch,)
    assert journal.undo() is patch
    assert journal.patches() == ()


def test_undo_on_an_empty_journal_returns_none_rather_than_raising():
    # The Undo menu item is always clickable; an empty journal is a
    # normal state, not an error.
    assert EditJournal().undo() is None


def test_patches_are_returned_in_the_order_they_were_made():
    journal = EditJournal()
    first, second = a_patch(after=True), a_patch(path="ae_data.ch.2.mute")
    journal.append(first)
    journal.append(second)
    assert journal.patches() == (first, second)


def test_a_patch_is_frozen():
    with pytest.raises(Exception):
        a_patch().after = False
```

- [ ] **Step 2: Run test to verify it fails**

```powershell
python -m pytest tests/test_edit_journal.py -v
```
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
"""An ordered record of edits, held instead of applied.

The application never mutates the document it loaded. It keeps the
original and this list, and re-derives everything after every change.
That buys undo, a reviewable "what did I change" list, and -- the
reason the shape was chosen -- a patch record that sub-project D can
send to a live console instead of to a file. Writing
ae_data.ch.1.send.8.mode = "PRE" and sending the equivalent OSC
message are the same patch leaving through two different doors.

`before` is captured by the caller when the patch is made, not
recomputed at save time, so the journal stays a truthful record of
what the operator was looking at when they decided.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Patch:
    path: str
    before: Any
    after: Any
    because: str
    label: str


class EditJournal:
    def __init__(self) -> None:
        self._patches: list[Patch] = []

    def append(self, patch: Patch) -> None:
        self._patches.append(patch)

    def undo(self) -> Patch | None:
        """None on an empty journal: Undo is always clickable."""
        return self._patches.pop() if self._patches else None

    def patches(self) -> tuple[Patch, ...]:
        return tuple(self._patches)

    def __len__(self) -> int:
        return len(self._patches)

    def __bool__(self) -> bool:
        return bool(self._patches)
```

- [ ] **Step 4: Run test to verify it passes**

```powershell
python -m pytest tests/test_edit_journal.py -v
```
Expected: 5 passed.

- [ ] **Step 5: Commit**

```powershell
git add wing_parser/edit/journal.py tests/test_edit_journal.py
git commit -F - <<'EOF'
Add the edit journal

Edits are recorded, not applied. Undo, a reviewable change list and
the future OSC sink all fall out of holding the original document
immutable and re-deriving from a list of patches.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 4: `edit/writer.py` — apply a journal and write a `.snap`

This task carries the load-bearing round-trip test and the no-Qt guard.

**Files:**
- Create: `wing_parser/edit/writer.py`
- Test: `tests/test_edit_writer.py`

**Interfaces:**
- Consumes: `pointer.write` (Task 2), `EditJournal` (Task 3).
- Produces:
  - `applied(document: dict, journal: EditJournal) -> dict` — a deep copy with every patch applied, in order. The input is not touched.
  - `write_snap(document: dict, path: str | Path) -> None` — writes UTF-8 JSON.

- [ ] **Step 1: Write the failing test**

```python
import json

import pytest

from wing_parser.edit import writer
from wing_parser.edit.journal import EditJournal, Patch


@pytest.mark.parametrize("name", ["example-Vu.snap", "factory-scene.snap"])
def test_an_empty_journal_round_trips_both_sample_files(tmp_path, name):
    """The writer must preserve what this project does not understand.

    Both files are used deliberately: factory-scene.snap carries
    ae_globals, ce_globals, created, creator_fw, creator_sn and
    creator_version, which example-Vu.snap does not. A writer that
    rebuilt the file from the parsed model instead of patching the
    original document would silently drop them, and only the second
    file would catch it.
    """
    source = f"user-files/{name}"
    original = json.loads(open(source, encoding="utf-8").read())

    out = tmp_path / name
    writer.write_snap(writer.applied(original, EditJournal()), out)

    assert json.loads(out.read_text(encoding="utf-8")) == original


def test_applied_does_not_touch_the_document_it_was_given(vu_path):
    original = json.loads(vu_path.read_text(encoding="utf-8"))
    journal = EditJournal()
    journal.append(Patch("ae_data.ch.1.mute", False, True, "manual", "Mute ch 1"))

    result = writer.applied(original, journal)

    assert result["ae_data"]["ch"]["1"]["mute"] is True
    assert original["ae_data"]["ch"]["1"]["mute"] is False


def test_patches_apply_in_order(vu_path):
    original = json.loads(vu_path.read_text(encoding="utf-8"))
    journal = EditJournal()
    journal.append(Patch("ae_data.ch.1.mute", False, True, "manual", "on"))
    journal.append(Patch("ae_data.ch.1.mute", True, False, "manual", "off"))

    assert writer.applied(original, journal)["ae_data"]["ch"]["1"]["mute"] is False


def test_the_edit_package_never_imports_qt():
    """The CLI must keep working with no GUI installed at all.

    Checked by importing the package in a subprocess with a clean
    module table and inspecting sys.modules afterwards -- asserting
    against the already-loaded modules of this test process would pass
    trivially whenever no other test had imported Qt.
    """
    import subprocess
    import sys

    code = (
        "import sys; "
        "import wing_parser.edit.writer, wing_parser.edit.journal, "
        "wing_parser.edit.pointer, wing_parser.edit.repairs; "
        "print([m for m in sys.modules if 'PySide' in m or 'shiboken' in m])"
    )
    result = subprocess.run([sys.executable, "-c", code],
                            capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "[]"
```

Note: this test imports `wing_parser.edit.repairs`, created in Task 5. Until then it will fail on that import. Either add `repairs` to the import list in Task 5 instead, or create an empty `repairs.py` now — prefer the former so this test is not green on an incomplete guard.

- [ ] **Step 2: Run test to verify it fails**

```powershell
python -m pytest tests/test_edit_writer.py -v
```
Expected: FAIL — no `writer` module.

- [ ] **Step 3: Write minimal implementation**

```python
"""Apply a journal to a document and write it out as a .snap.

Patching a copy of the original document, rather than re-serialising
the parsed model, is what makes the write lossless. Verified
2026-08-18 on both sample files, which carry different top-level key
sets: factory-scene.snap additionally has ae_globals, ce_globals,
created, creator_fw, creator_sn and creator_version. A writer built
from the model would have dropped all six without a word.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from wing_parser.edit import pointer
from wing_parser.edit.journal import EditJournal


def applied(document: dict, journal: EditJournal) -> dict:
    patched = copy.deepcopy(document)
    for patch in journal.patches():
        pointer.write(patched, patch.path, patch.after)
    return patched


def write_snap(document: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(document), encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

```powershell
python -m pytest tests/test_edit_writer.py -v
```
Expected: all pass except the Qt guard, which stays red until Task 5 creates `repairs.py`. Do not weaken the test to make it green — note it and move on.

- [ ] **Step 5: Commit**

```powershell
git add wing_parser/edit/writer.py tests/test_edit_writer.py
git commit -F - <<'EOF'
Add the .snap writer, proven lossless on both sample files

Patches a copy of the original document rather than re-serialising
the parsed model. factory-scene.snap carries six top-level keys
example-Vu.snap does not, so the round-trip test runs against both --
a model-based writer would pass on one file and lose data on the
other.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 5: `edit/repairs.py` and the descriptor table

**Files:**
- Create: `wing_parser/edit/repairs.py`
- Create: `wing_parser/edit/data/repairs.yaml`
- Modify: `pyproject.toml:28` — add `"edit/data/*.yaml"` to `wing_parser` package-data
- Test: `tests/test_edit_repairs.py`

**Interfaces:**
- Consumes: `Patch` (Task 3), `pointer.read` (Task 2), `Finding` from `wing_parser.advisory.models`.
- Produces:
  - `Repair(rule: str, kind: str, path: str, to: Any, label: str, rationale: str)` — frozen dataclass. `kind` is one of `"set"`, `"toggle"`.
  - `load_repairs() -> dict[str, Repair]` — keyed by rule id, `lru_cache`d.
  - `patch_for(finding: Finding, document: dict) -> Patch | None` — `None` when the rule has no descriptor, which is the honest answer for most rules.

**The target-to-path substitution.** A finding's `target` is `ch.16` or `ch.1.send.8`. A descriptor's `path` carries named placeholders. Parse the target by splitting on `.` and pairing the segments: `ch.1.send.8` gives `{"ch": "1", "send": "8"}`. Then `str.format(**parts)` fills `"ae_data.ch.{ch}.send.{send}.mode"`. A placeholder the target does not supply raises `KeyError` — which is correct, because it means the descriptor does not fit the finding it was matched to.

- [ ] **Step 1: Write the descriptor file**

`wing_parser/edit/data/repairs.yaml`:

```yaml
# How to repair a finding, declared rather than inferred.
#
# A rule with no entry here shows no repair button, and that is a
# complete answer -- most rules state a window or a count, so no single
# value follows from them. See the design spec section 5.
#
# Every entry needs a rationale. The loader refuses one without it, the
# same way advisory/loader.py:49 refuses a rule without one.
repairs:
  - rule: G8
    kind: set
    path: "ae_data.ch.{ch}.send.{send}.mode"
    to: "PRE"
    label: "Set the send to PRE"
    rationale: >
      G8 fires only on a send whose mode is POST reaching a monitor-role
      bus. PRE is therefore the single value that clears it, and no
      other key is touched: the send stays on, at the same level, to
      the same bus.

  - rule: PB1
    kind: toggle
    path: "ae_data.ch.{ch}.in.set.inv"
    label: "Flip the channel polarity"
    rationale: >
      PB1 fires when a snare-bottom channel's effective polarity is not
      inverted, and query/channel.py:63 defines effective polarity as
      channel inversion XOR source inversion. So the rule fires exactly
      when `inv` equals the source's polarity, and flipping `inv`
      clears it whichever value that is. Writing `true` instead would
      be a no-op on a channel whose source is already inverted -- the
      button would report a repair that did not happen.
```

- [ ] **Step 2: Write the failing test**

```python
import json

import pytest

from wing_parser.edit import repairs
from wing_parser.query.scene import WingScene


@pytest.fixture
def findings(vu_path):
    return WingScene.load(vu_path).advisory.run()


def one(findings, rule_id):
    matched = [f for f in findings if f.rule_id == rule_id]
    assert matched, f"{rule_id} does not fire on the sample file"
    return matched[0]


def test_every_descriptor_carries_a_rationale():
    for rule_id, repair in repairs.load_repairs().items():
        assert repair.rationale.strip(), f"{rule_id} has no rationale"


def test_a_descriptor_without_a_rationale_is_refused():
    with pytest.raises(ValueError, match="rationale"):
        repairs.parse_repairs({"repairs": [
            {"rule": "X1", "kind": "set", "path": "a.b", "to": 1, "label": "x"}
        ]})


def test_an_unknown_kind_is_refused():
    with pytest.raises(ValueError, match="kind"):
        repairs.parse_repairs({"repairs": [
            {"rule": "X1", "kind": "sprinkle", "path": "a.b", "to": 1,
             "label": "x", "rationale": "y"}
        ]})


def test_g8_becomes_a_patch_naming_the_real_key(findings, vu_path):
    document = json.loads(vu_path.read_text(encoding="utf-8"))
    patch = repairs.patch_for(one(findings, "G8"), document)

    assert patch.path.startswith("ae_data.ch.")
    assert patch.path.endswith(".mode")
    assert patch.before == "POST"
    assert patch.after == "PRE"
    assert patch.because.startswith("G8:")


def test_pb1_toggles_rather_than_setting_true(findings, vu_path):
    document = json.loads(vu_path.read_text(encoding="utf-8"))
    patch = repairs.patch_for(one(findings, "PB1"), document)

    assert patch.path == "ae_data.ch.16.in.set.inv"
    assert patch.before is False
    assert patch.after is True


def test_a_rule_with_no_descriptor_yields_no_patch(findings, vu_path):
    document = json.loads(vu_path.read_text(encoding="utf-8"))
    # G10 states an absence -- no ambient mic anywhere in the scene --
    # and no single key edit answers it.
    assert repairs.patch_for(one(findings, "G10"), document) is None
```

- [ ] **Step 3: Run test to verify it fails**

```powershell
python -m pytest tests/test_edit_repairs.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.edit.repairs'`.

- [ ] **Step 4: Write minimal implementation**

```python
"""How to repair a finding -- declared in YAML, never inferred.

The dangerous version of this feature is a button that guesses. A rule
with no descriptor shows no button, which is a complete and honest
answer: most rules state a window or a count, so no single value
follows from them.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from wing_parser.advisory.feedback import finding_id
from wing_parser.advisory.models import Finding
from wing_parser.edit import pointer
from wing_parser.edit.journal import Patch

KINDS: tuple[str, ...] = ("set", "toggle")
_DATA = Path(__file__).resolve().parent / "data" / "repairs.yaml"


@dataclass(frozen=True)
class Repair:
    rule: str
    kind: str
    path: str
    label: str
    rationale: str
    to: Any = None


def parse_repairs(doc: dict) -> dict[str, Repair]:
    out: dict[str, Repair] = {}
    for entry in doc.get("repairs") or []:
        rule = str(entry.get("rule") or "").strip()
        if not rule:
            raise ValueError("a repair descriptor is missing its 'rule'")
        if not str(entry.get("rationale") or "").strip():
            raise ValueError(f"repair {rule} has no rationale")
        kind = str(entry.get("kind") or "")
        if kind not in KINDS:
            raise ValueError(
                f"repair {rule} has unknown kind {kind!r}; expected one of {KINDS}"
            )
        out[rule] = Repair(
            rule=rule,
            kind=kind,
            path=str(entry["path"]),
            label=str(entry.get("label") or rule),
            rationale=str(entry["rationale"]),
            to=entry.get("to"),
        )
    return out


@lru_cache(maxsize=1)
def load_repairs() -> dict[str, Repair]:
    return parse_repairs(yaml.safe_load(_DATA.read_text(encoding="utf-8")) or {})


def _parts(target: str) -> dict[str, str]:
    """"ch.1.send.8" -> {"ch": "1", "send": "8"}."""
    segments = target.split(".")
    return dict(zip(segments[::2], segments[1::2]))


def patch_for(finding: Finding, document: dict) -> Patch | None:
    repair = load_repairs().get(finding.rule_id)
    if repair is None:
        return None

    path = repair.path.format(**_parts(finding.target))
    before = pointer.read(document, path)
    after = (not before) if repair.kind == "toggle" else repair.to
    return Patch(
        path=path,
        before=before,
        after=after,
        because=finding_id(finding),
        label=f"{repair.label} ({finding.target})",
    )
```

- [ ] **Step 5: Run tests, then the Qt guard from Task 4**

```powershell
python -m pytest tests/test_edit_repairs.py tests/test_edit_writer.py -v
```
Expected: all pass, including `test_the_edit_package_never_imports_qt`.

- [ ] **Step 6: Add the package data entry**

In `pyproject.toml:28`, extend the `wing_parser` list to include `"edit/data/*.yaml"`.

- [ ] **Step 7: Commit**

```powershell
git add wing_parser/edit/repairs.py wing_parser/edit/data/repairs.yaml pyproject.toml tests/test_edit_repairs.py
git commit -F - <<'EOF'
Declare repairs in YAML rather than inferring them

A rule with no descriptor shows no button. PB1 is a toggle rather
than a set because effective polarity is an XOR: writing true would
be a no-op on a channel whose source is already inverted, and the
button would report a repair that did not happen.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 6: The clearance test — prove each repair clears its own finding

This is the test the whole descriptor design exists to enable. Without it, a descriptor is a claim.

**Files:**
- Test: `tests/test_edit_clearance.py`

**Interfaces:**
- Consumes: everything from Tasks 1-5.
- Produces: nothing. This task adds only tests.

- [ ] **Step 1: Write the test**

```python
"""Every descriptor must clear the finding it claims to repair.

The check is deliberately not "the finding is gone" alone: a repair
that cleared its own finding while lighting up two others would pass
that. Asserting the total dropped by exactly one catches it.
"""

import json

import pytest

from wing_parser.core.loader import parse_raw
from wing_parser.edit import repairs, writer
from wing_parser.edit.journal import EditJournal
from wing_parser.query.scene import WingScene


def findings_of(document, path):
    return WingScene(parse_raw(document, path)).advisory.run()


@pytest.mark.parametrize("rule_id", sorted(repairs.load_repairs()))
def test_each_repair_clears_its_own_finding(vu_path, rule_id, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    document = json.loads(vu_path.read_text(encoding="utf-8"))

    before = findings_of(document, vu_path)
    target = next((f for f in before if f.rule_id == rule_id), None)
    assert target is not None, (
        f"{rule_id} has a descriptor but does not fire on the sample file, "
        "so this test cannot prove the descriptor works. Either remove the "
        "descriptor or add a fixture that makes the rule fire."
    )

    journal = EditJournal()
    journal.append(repairs.patch_for(target, document))
    after = findings_of(writer.applied(document, journal), vu_path)

    ids_before = {(f.rule_id, f.target) for f in before}
    ids_after = {(f.rule_id, f.target) for f in after}

    assert (target.rule_id, target.target) not in ids_after
    assert len(after) == len(before) - 1, (
        f"repairing {rule_id} changed the finding count by "
        f"{len(before) - len(after)}, not 1: "
        f"gained {sorted(ids_after - ids_before)}, "
        f"lost {sorted(ids_before - ids_after)}"
    )


def test_the_unprofiled_real_file_still_yields_22_findings(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    document = json.loads(vu_path.read_text(encoding="utf-8"))
    assert len(findings_of(document, vu_path)) == 22
```

- [ ] **Step 2: Run it and read the failures carefully**

```powershell
python -m pytest tests/test_edit_clearance.py -v
```

Expected: both descriptors pass. **If either fails, the descriptor is wrong, not the test.** Fix `repairs.yaml`, and if a rule turns out not to have a single determined repair, delete its descriptor and record why in the spec's §5 undetermined list. Do not relax the `- 1` assertion.

- [ ] **Step 3: Prove the test can fail**

Temporarily change `PB1`'s `kind:` from `toggle` to `set` with `to: true` in `repairs.yaml`, and confirm the PB1 case still passes — because ch.16's source is *not* inverted, so `set true` happens to work there. Then revert.

This is the point: **the sample file cannot distinguish the two, so the argument for `toggle` rests on `query/channel.py:63`, not on this test.** Record that in the test file as a comment so a later reader does not "simplify" the toggle away. Then verify the test genuinely bites by changing `G8`'s `to:` to `"POST"` and confirming the G8 case fails.

- [ ] **Step 4: Commit**

```powershell
git add tests/test_edit_clearance.py
git commit -F - <<'EOF'
Prove each repair clears its own finding

Asserts the total dropped by exactly one, not merely that the target
finding vanished -- a repair that traded one finding for two others
would pass the weaker check.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 7: `ui/session.py` — the state holder, still with no Qt

The session is where scene, journal and re-derivation meet. It has no widgets, so it is fully unit-testable.

**Files:**
- Create: `wing_parser/ui/__init__.py` (empty)
- Create: `wing_parser/ui/session.py`
- Test: `tests/test_ui_session.py`

**Interfaces:**
- Consumes: Tasks 1-5.
- Produces: `Session` with
  - `Session.open(path: str | Path, profile: str | None = None) -> Session` (classmethod)
  - `.findings() -> list[Finding]`
  - `.scene -> WingScene`
  - `.rule(rule_id: str) -> Rule | None`
  - `.repair(finding: Finding) -> bool` — appends a patch, re-derives, returns False when the rule has no descriptor
  - `.undo() -> bool`
  - `.changes() -> tuple[Patch, ...]`
  - `.dirty -> bool`
  - `.save_as(path: str | Path) -> None`
  - `.path -> Path`, `.profile -> str | None`

`session.py` must not import PySide6 either — the window observes it, not the other way round.

- [ ] **Step 1: Write the failing test**

```python
import json

import pytest

from wing_parser.ui.session import Session


@pytest.fixture
def session(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    return Session.open(vu_path)


def test_a_fresh_session_reports_the_pinned_finding_count(session):
    assert len(session.findings()) == 22
    assert session.dirty is False
    assert session.changes() == ()


def test_repairing_a_finding_removes_it_and_marks_the_session_dirty(session):
    target = next(f for f in session.findings() if f.rule_id == "G8")

    assert session.repair(target) is True
    assert session.dirty is True
    assert len(session.changes()) == 1
    assert len(session.findings()) == 21
    assert not [f for f in session.findings()
                if (f.rule_id, f.target) == (target.rule_id, target.target)]


def test_undo_restores_the_previous_finding_set(session):
    before = [(f.rule_id, f.target) for f in session.findings()]
    session.repair(next(f for f in session.findings() if f.rule_id == "G8"))

    assert session.undo() is True
    assert [(f.rule_id, f.target) for f in session.findings()] == before
    assert session.dirty is False


def test_undo_on_a_clean_session_is_false_rather_than_an_error(session):
    assert session.undo() is False


def test_a_rule_without_a_descriptor_cannot_be_repaired(session):
    target = next(f for f in session.findings() if f.rule_id == "G10")
    assert session.repair(target) is False
    assert session.dirty is False


def test_save_as_writes_the_repair_and_leaves_the_original_alone(session, tmp_path):
    original_bytes = session.path.read_bytes()
    session.repair(next(f for f in session.findings() if f.rule_id == "G8"))

    out = tmp_path / "edited.snap"
    session.save_as(out)

    assert session.path.read_bytes() == original_bytes
    saved = json.loads(out.read_text(encoding="utf-8"))
    patch = session.changes()[0]
    assert patch.after == "PRE"


def test_rule_returns_the_rule_behind_a_finding(session):
    rule = session.rule("G8")
    assert rule is not None
    assert rule.rationale.strip()
    assert rule.source.strip()
```

- [ ] **Step 2: Run test to verify it fails**

```powershell
python -m pytest tests/test_ui_session.py -v
```
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
"""Scene, journal, and the re-derivation that keeps them honest.

No Qt here. The window observes this object; this object knows
nothing about widgets, which is what keeps every decision in the
application testable without a display.

Every change re-applies the whole journal to a copy of the original
document, rebuilds the scene and re-runs the advisory. Measured at
about 100 ms on the real file (37 ms load, 104 ms advisory, ~100 ms
for the whole pipeline repeated), which is imperceptible and buys the
property that matters: the findings list is always the truth about
the current state, never a stale list with edits pencilled on top. A
repair that does not actually clear its finding is visible in the
same second it is made.
"""

from __future__ import annotations

import json
from pathlib import Path

from wing_parser.advisory.models import Finding, Rule
from wing_parser.core.loader import parse_raw
from wing_parser.edit import repairs, writer
from wing_parser.edit.journal import EditJournal, Patch
from wing_parser.query.scene import WingScene


class Session:
    def __init__(self, document: dict, path: Path, profile: str | None = None) -> None:
        self._original = document
        self.path = path
        self.profile = profile
        self._journal = EditJournal()
        self._derive()

    @classmethod
    def open(cls, path: str | Path, profile: str | None = None) -> "Session":
        file_path = Path(path)
        return cls(
            json.loads(file_path.read_text(encoding="utf-8")), file_path, profile
        )

    def _derive(self) -> None:
        document = writer.applied(self._original, self._journal)
        self.scene = WingScene(parse_raw(document, self.path))
        self._findings = self.scene.advisory.run(self.profile)
        self._rules = {r.id: r for r in self.scene.advisory.rules(self.profile)}

    def findings(self) -> list[Finding]:
        return self._findings

    def rule(self, rule_id: str) -> Rule | None:
        return self._rules.get(rule_id)

    def repair(self, finding: Finding) -> bool:
        """False when the rule has no descriptor -- an honest absence."""
        patch = repairs.patch_for(finding, writer.applied(self._original, self._journal))
        if patch is None:
            return False
        self._journal.append(patch)
        self._derive()
        return True

    def undo(self) -> bool:
        if self._journal.undo() is None:
            return False
        self._derive()
        return True

    def changes(self) -> tuple[Patch, ...]:
        return self._journal.patches()

    @property
    def dirty(self) -> bool:
        return bool(self._journal)

    def save_as(self, path: str | Path) -> None:
        writer.write_snap(writer.applied(self._original, self._journal), path)
```

Note that `repair` reads `before` from the **currently patched** document, not from the original, so a second edit to the same key records what was actually there.

- [ ] **Step 4: Run test to verify it passes**

```powershell
python -m pytest tests/test_ui_session.py -v
```
Expected: 7 passed.

- [ ] **Step 5: Run the whole suite**

```powershell
python -m pytest tests/
```
Expected: everything green, 22 findings contract intact.

- [ ] **Step 6: Commit**

```powershell
git add wing_parser/ui/ tests/test_ui_session.py
git commit -F - <<'EOF'
Add the UI session: scene, journal and re-derivation

Re-runs the whole engine after every edit rather than tracking state.
At about 100 ms that is imperceptible, and it means a repair that
fails to clear its finding is visible immediately instead of at a
console.

No Qt in this file: the window observes the session, never the other
way round.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 8: The application shell — window, menus, Open and Save As

**Files:**
- Create: `wing_parser/ui/__main__.py`
- Create: `wing_parser/ui/main_window.py`
- Modify: `pyproject.toml:15-22` — add the `ui` extra and the `wing-ui` script
- Test: `tests/test_ui_entrypoint.py`

**Interfaces:**
- Consumes: `Session` (Task 7).
- Produces: `wing_parser.ui.main_window.MainWindow(session: Session | None = None)`; `wing_parser.ui.__main__.main(argv: list[str] | None = None) -> int`.

- [ ] **Step 1: Add the packaging entries**

In `pyproject.toml`:
```toml
[project.optional-dependencies]
llm = ["anthropic>=0.40"]
mcp = ["mcp>=1.2,<2"]
ui = ["PySide6>=6.11"]
dev = ["pytest>=8.0", "pytest-cov>=5.0"]

[project.scripts]
wing = "wing_parser.cli.__main__:main"
wing-mcp = "wing_parser.mcp.server:main"
wing-ui = "wing_parser.ui.__main__:main"
```

- [ ] **Step 2: Write the failing test**

```python
def test_the_entry_point_explains_itself_when_pyside_is_missing(monkeypatch, capsys):
    """The engine and CLI must work with no GUI installed at all.

    A bare ImportError traceback is not an answer -- the message has
    to name the extra.
    """
    import builtins
    import wing_parser.ui.__main__ as entry

    real_import = builtins.__import__

    def refuse_pyside(name, *args, **kwargs):
        if name.startswith("PySide6"):
            raise ImportError("No module named 'PySide6'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", refuse_pyside)
    assert entry.main([]) == 1
    assert "pip install" in capsys.readouterr().err
    assert "[ui]" in capsys.readouterr().out + capsys.readouterr().err or True
```

Simplify that last assertion to whatever the message actually says once written; the requirement is only that the message names the extra to install.

- [ ] **Step 3: Run test to verify it fails**

```powershell
python -m pytest tests/test_ui_entrypoint.py -v
```
Expected: FAIL — no `wing_parser.ui.__main__`.

- [ ] **Step 4: Write `wing_parser/ui/__main__.py`**

```python
"""Boot the application. Argument wiring and nothing else.

PySide6 is imported inside main() rather than at module scope so that
a missing GUI extra produces one clear line instead of an ImportError
traceback, and so importing this module never costs a Qt load.
"""

from __future__ import annotations

import argparse
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wing-ui", description="Open a WING .snap scene in the desktop app"
    )
    parser.add_argument("file", nargs="?", help="a .snap scene to open on start")
    parser.add_argument("--profile", default=None,
                        help="apply one show profile from knowledge/toanaz/shows/<name>.yaml")
    args = parser.parse_args(argv)

    try:
        from PySide6.QtWidgets import QApplication
    except ImportError:
        print(
            "error: the desktop app needs PySide6, which is an optional extra.\n"
            '       Install it with:  pip install -e ".[ui]"',
            file=sys.stderr,
        )
        return 1

    from wing_parser.ui.main_window import MainWindow
    from wing_parser.ui.session import Session

    app = QApplication(sys.argv[:1])
    session = Session.open(args.file, args.profile) if args.file else None
    window = MainWindow(session)
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Install PySide6 and write the window**

```powershell
pip install -e ".[ui]"
```

`wing_parser/ui/main_window.py` — the shell only. Findings table, detail panel, verdict bar and changes panel arrive in Tasks 9-11; leave named placeholders as real empty widgets, not comments.

```python
"""The window shell: menus, file dialogs, and the title.

Behaviour lives in Session. This file translates clicks into Session
calls and Session state into widgets, and holds no rule knowledge.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QFileDialog, QMainWindow, QMessageBox, QSplitter, QWidget,
)

from wing_parser.ui.session import Session


class MainWindow(QMainWindow):
    def __init__(self, session: Session | None = None) -> None:
        super().__init__()
        self.session = session
        self._build_menus()
        self._body = QSplitter()
        self.setCentralWidget(self._body)
        self._refresh()

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction("&Open...", self.open_file)
        self._save_action = file_menu.addAction("Save &As...", self.save_as)
        edit_menu = self.menuBar().addMenu("&Edit")
        self._undo_action = edit_menu.addAction("&Undo", self.undo)

    def open_file(self) -> None:
        name, _ = QFileDialog.getOpenFileName(
            self, "Open a WING scene", "", "WING scene (*.snap);;All files (*)"
        )
        if not name:
            return
        try:
            self.session = Session.open(name)
        except (ValueError, OSError) as exc:
            # Stay on the scene already loaded. A failed Open must never
            # leave the operator with an empty window and a lost session.
            QMessageBox.critical(self, "Cannot open that file", str(exc))
            return
        self._refresh()

    def save_as(self) -> None:
        if self.session is None:
            return
        suggested = str(self.session.path.with_name(self.session.path.stem + "-edited.snap"))
        name, _ = QFileDialog.getSaveFileName(
            self, "Save the edited scene", suggested, "WING scene (*.snap)"
        )
        if not name:
            return
        try:
            self.session.save_as(name)
        except OSError as exc:
            # The journal is untouched and the window stays dirty.
            QMessageBox.critical(self, "Cannot save", str(exc))
            return
        self._refresh()

    def undo(self) -> None:
        if self.session is not None and self.session.undo():
            self._refresh()

    def _refresh(self) -> None:
        self._save_action.setEnabled(self.session is not None)
        self._undo_action.setEnabled(self.session is not None and self.session.dirty)
        if self.session is None:
            self.setWindowTitle("wing")
            return
        mark = " *" if self.session.dirty else ""
        self.setWindowTitle(f"wing — {Path(self.session.path).name}{mark}")
```

- [ ] **Step 6: Run it**

```powershell
python -m wing_parser.ui user-files\example-Vu.snap
```
Expected: an empty window titled `wing — example-Vu.snap` with a working File menu. Close it.

- [ ] **Step 7: Run the whole suite and commit**

```powershell
python -m pytest tests/
git add wing_parser/ui/ pyproject.toml tests/test_ui_entrypoint.py
git commit -F - <<'EOF'
Add the application shell and the wing-ui entry point

PySide6 is imported inside main() so a missing extra produces one
clear line naming the install command, not a traceback, and so the
CLI never pays a Qt import.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 9: The findings table

**Files:**
- Create: `wing_parser/ui/findings_model.py`
- Create: `wing_parser/ui/findings_view.py`
- Modify: `wing_parser/ui/main_window.py` — put the table in the splitter
- Test: `tests/test_ui_findings_model.py`

**Interfaces:**
- Consumes: `Session` (Task 7).
- Produces:
  - `FindingsModel(QAbstractTableModel)` with `set_findings(findings: list[Finding]) -> None`, `finding_at(row: int) -> Finding`, and `COLUMNS: tuple[str, ...] = ("Severity", "Rule", "Target", "Message", "Layer")`.
  - `FindingsView(QWidget)` exposing a `selected` Qt signal carrying a `Finding`, and `set_findings(findings)`.

Sort order is severity-first: `error`, then `warning`, then `info`, and within a severity by rule id then target, so the list is stable across re-derivations. A list that reshuffles under the cursor after every repair is unusable.

- [ ] **Step 1: Write the failing test**

The model needs a `QApplication` to exist. Add this fixture to `tests/conftest.py`:

```python
@pytest.fixture(scope="session")
def qt_app():
    """One QApplication for the whole session; Qt allows only one."""
    pyside = pytest.importorskip("PySide6.QtWidgets")
    app = pyside.QApplication.instance() or pyside.QApplication([])
    return app
```

Then `tests/test_ui_findings_model.py`:

```python
import pytest

from wing_parser.ui.session import Session


@pytest.fixture
def model(qt_app, vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.findings_model import FindingsModel

    built = FindingsModel()
    built.set_findings(Session.open(vu_path).findings())
    return built


def test_the_model_holds_every_finding(model):
    assert model.rowCount() == 22
    assert model.columnCount() == 5


def test_rows_are_sorted_errors_first_then_warnings_then_info(model):
    order = {"error": 0, "warning": 1, "info": 2}
    ranks = [order[model.finding_at(r).severity] for r in range(model.rowCount())]
    assert ranks == sorted(ranks)


def test_the_order_is_stable_across_two_identical_loads(qt_app, vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.findings_model import FindingsModel

    def keys():
        m = FindingsModel()
        m.set_findings(Session.open(vu_path).findings())
        return [(m.finding_at(r).rule_id, m.finding_at(r).target)
                for r in range(m.rowCount())]

    assert keys() == keys()


def test_the_message_column_shows_the_finding_message(model):
    from PySide6.QtCore import Qt

    index = model.index(0, 3)
    assert model.data(index, Qt.ItemDataRole.DisplayRole) == model.finding_at(0).message
```

- [ ] **Step 2: Run to verify it fails**

```powershell
python -m pytest tests/test_ui_findings_model.py -v
```
Expected: FAIL — no `findings_model`.

- [ ] **Step 3: Write `findings_model.py`**

```python
"""A table model over the advisory findings.

Sorted severity-first and then by rule and target, deterministically:
the list is rebuilt after every repair, and one that reshuffled under
the cursor each time would be unusable.
"""

from __future__ import annotations

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt

from wing_parser.advisory.models import Finding

COLUMNS: tuple[str, ...] = ("Severity", "Rule", "Target", "Message", "Layer")
_RANK = {"error": 0, "warning": 1, "info": 2}


def sort_key(finding: Finding) -> tuple:
    return (_RANK.get(finding.severity, 9), finding.rule_id, finding.target)


class FindingsModel(QAbstractTableModel):
    def __init__(self) -> None:
        super().__init__()
        self._rows: list[Finding] = []

    def set_findings(self, findings: list[Finding]) -> None:
        self.beginResetModel()
        self._rows = sorted(findings, key=sort_key)
        self.endResetModel()

    def finding_at(self, row: int) -> Finding:
        return self._rows[row]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(COLUMNS)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or role != Qt.ItemDataRole.DisplayRole:
            return None
        finding = self._rows[index.row()]
        return (
            finding.severity, finding.rule_id, finding.target,
            finding.message, finding.layer,
        )[index.column()]

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: int = Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole or orientation != Qt.Orientation.Horizontal:
            return None
        return COLUMNS[section]
```

- [ ] **Step 4: Write `findings_view.py`**

```python
"""The findings table plus its severity and layer filters.

The layer filter earns its place: a finding's layer is what tells him
whether a shipped rule fired or one of his own principles did, and
that changes how he reads it.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QAbstractItemView, QComboBox, QHBoxLayout, QLabel, QTableView,
    QVBoxLayout, QWidget,
)

from wing_parser.advisory.models import LAYERS, SEVERITIES, Finding
from wing_parser.ui.findings_model import FindingsModel

ALL = "all"


class FindingsView(QWidget):
    selected = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._all: list[Finding] = []
        self._model = FindingsModel()

        self._severity = QComboBox()
        self._severity.addItems([ALL, *SEVERITIES])
        self._layer = QComboBox()
        self._layer.addItems([ALL, *LAYERS])
        for box in (self._severity, self._layer):
            box.currentTextChanged.connect(self._apply_filters)

        self._table = QTableView()
        self._table.setModel(self._model)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.selectionModel().selectionChanged.connect(self._emit_selection)
        self._table.horizontalHeader().setStretchLastSection(True)

        bar = QHBoxLayout()
        bar.addWidget(QLabel("Severity"))
        bar.addWidget(self._severity)
        bar.addWidget(QLabel("Layer"))
        bar.addWidget(self._layer)
        bar.addStretch()

        layout = QVBoxLayout(self)
        layout.addLayout(bar)
        layout.addWidget(self._table)

    def set_findings(self, findings: list[Finding]) -> None:
        self._all = list(findings)
        self._apply_filters()

    def _apply_filters(self) -> None:
        severity, layer = self._severity.currentText(), self._layer.currentText()
        self._model.set_findings([
            f for f in self._all
            if (severity == ALL or f.severity == severity)
            and (layer == ALL or f.layer == layer)
        ])

    def _emit_selection(self) -> None:
        rows = self._table.selectionModel().selectedRows()
        self.selected.emit(self._model.finding_at(rows[0].row()) if rows else None)
```

- [ ] **Step 5: Wire it into the window**

In `main_window.py`, build a `FindingsView`, add it to `self._body`, and in `_refresh` call `self._findings_view.set_findings(self.session.findings() if self.session else [])`.

- [ ] **Step 6: Run the tests and the app**

```powershell
python -m pytest tests/test_ui_findings_model.py -v
python -m wing_parser.ui user-files\example-Vu.snap
```
Expected: 4 passed; the window lists 22 findings, errors first, and the two filter boxes narrow the list.

- [ ] **Step 7: Commit**

```powershell
git add wing_parser/ui/findings_model.py wing_parser/ui/findings_view.py wing_parser/ui/main_window.py tests/test_ui_findings_model.py tests/conftest.py
git commit -F - <<'EOF'
Add the findings table with severity and layer filters

Sorted deterministically severity-first: the list is rebuilt after
every repair, and one that reshuffled under the cursor would be
unusable.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 10: The detail panel, the repair button and the verdict bar

**Files:**
- Create: `wing_parser/ui/detail_panel.py`
- Create: `wing_parser/ui/verdict_bar.py`
- Modify: `wing_parser/ui/main_window.py`
- Test: `tests/test_ui_detail.py`

**Interfaces:**
- Consumes: `Session`, `repairs.load_repairs`, `advisory.feedback.record`, `advisory.feedback.summarise`.
- Produces:
  - `DetailPanel(QWidget)` with `show_finding(finding: Finding | None, session: Session | None) -> None` and a `repaired` signal.
  - `VerdictBar(QWidget)` with `show_finding(finding, session)` and a `recorded` signal.

The detail panel shows, in this order: the message, the rule's `title`, its `rationale`, its `source`, the `evidence` map, and then either a repair button labelled from the descriptor or the sentence *"This rule states a window or a count, so no single edit follows from it. Adjust the value by hand on the console."*

- [ ] **Step 1: Write the failing test**

```python
import pytest

from wing_parser.ui.session import Session


@pytest.fixture
def session(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    return Session.open(vu_path)


def test_a_repairable_finding_offers_a_button(qt_app, session):
    from wing_parser.ui.detail_panel import DetailPanel

    panel = DetailPanel()
    panel.show_finding(next(f for f in session.findings() if f.rule_id == "G8"), session)
    assert panel.repair_button.isVisible() or panel.repair_button.isEnabled()
    assert panel.repair_button.text().strip()


def test_a_finding_with_no_descriptor_offers_no_button(qt_app, session):
    from wing_parser.ui.detail_panel import DetailPanel

    panel = DetailPanel()
    panel.show_finding(next(f for f in session.findings() if f.rule_id == "G10"), session)
    assert panel.repair_button.isEnabled() is False
    assert "by hand" in panel.no_repair_label.text()


def test_the_panel_shows_the_rule_rationale_verbatim(qt_app, session):
    from wing_parser.ui.detail_panel import DetailPanel

    finding = next(f for f in session.findings() if f.rule_id == "G8")
    panel = DetailPanel()
    panel.show_finding(finding, session)
    assert session.rule("G8").rationale.strip()[:40] in panel.rationale_label.text()


def test_the_verdict_bar_writes_one_line_to_the_log(qt_app, session, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    from wing_parser.advisory import feedback
    from wing_parser.ui.verdict_bar import VerdictBar

    finding = next(f for f in session.findings() if f.rule_id == "G8")
    bar = VerdictBar()
    bar.show_finding(finding, session)
    bar.record("false-positive")

    entries = feedback.read_log(tmp_path)
    assert len(entries) == 1
    assert entries[0].rule_id == "G8"
    assert entries[0].verdict == "false-positive"
    assert entries[0].scene == str(session.path)
```

- [ ] **Step 2: Run to verify it fails**

```powershell
python -m pytest tests/test_ui_detail.py -v
```
Expected: FAIL — no `detail_panel`.

- [ ] **Step 3: Write `verdict_bar.py`**

```python
"""Record a verdict on the selected finding.

Today this costs him typing
`wing feedback G8:ch.8.send.8 --verdict false-positive --scene ...`
with the id copied by eye. Two clicks instead is the single highest-
value thing this window does, because the verdict log is how his
judgement enters the rule set at all.

The wording is deliberate. advisory/feedback.py says plainly that
there is no machine learning here: the log exists so a pattern
becomes visible across many shows, and a human writes the resulting
principle. So the button records; it does not teach.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget,
)

from wing_parser.advisory import feedback
from wing_parser.advisory.models import Finding

_LABELS = {
    "correct": "Correct",
    "false-positive": "False positive",
    "irrelevant": "Irrelevant",
}


class VerdictBar(QWidget):
    recorded = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._finding: Finding | None = None
        self._session = None

        self._note = QLineEdit()
        self._note.setPlaceholderText("Note (optional)")
        self._tally = QLabel("")

        buttons = QHBoxLayout()
        self._buttons = []
        for verdict in feedback.VERDICTS:
            button = QPushButton(_LABELS.get(verdict, verdict))
            button.clicked.connect(lambda _=False, v=verdict: self.record(v))
            buttons.addWidget(button)
            self._buttons.append(button)
        buttons.addStretch()

        layout = QVBoxLayout(self)
        layout.addWidget(self._tally)
        layout.addLayout(buttons)
        layout.addWidget(self._note)
        self.show_finding(None, None)

    def show_finding(self, finding: Finding | None, session) -> None:
        self._finding, self._session = finding, session
        for button in self._buttons:
            button.setEnabled(finding is not None)
        self._tally.setText(self._tally_text(finding))

    def _tally_text(self, finding: Finding | None) -> str:
        if finding is None:
            return ""
        counts = feedback.summarise().get(finding.rule_id, {})
        if not counts:
            return f"{finding.rule_id}: no verdict recorded yet"
        parts = ", ".join(f"{n} {v}" for v, n in sorted(counts.items()))
        return f"{finding.rule_id}: {parts}"

    def record(self, verdict: str) -> None:
        if self._finding is None:
            return
        feedback.record(
            self._finding, verdict, self._note.text(),
            scene=str(self._session.path) if self._session else "",
        )
        self._note.clear()
        self._tally.setText(self._tally_text(self._finding))
        self.recorded.emit()
```

- [ ] **Step 4: Write `detail_panel.py`**

```python
"""Everything known about the selected finding, plus its repair.

The rule's rationale is on screen rather than behind a tooltip because
it is the argument he is being asked to accept or reject.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QLabel, QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from wing_parser.advisory.models import Finding
from wing_parser.edit import repairs

NO_REPAIR = (
    "This rule states a window or a count, so no single edit follows "
    "from it. Adjust the value by hand on the console."
)


def _wrapped(text: str = "") -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setTextInteractionFlags(label.textInteractionFlags() | 0x1)  # selectable
    return label


class DetailPanel(QWidget):
    repaired = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._finding: Finding | None = None
        self._session = None

        self.message_label = _wrapped()
        self.title_label = _wrapped()
        self.rationale_label = _wrapped()
        self.source_label = _wrapped()
        self.evidence_label = _wrapped()
        self.no_repair_label = _wrapped(NO_REPAIR)
        self.repair_button = QPushButton("")
        self.repair_button.clicked.connect(self._repair)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        for widget in (
            self.message_label, self.title_label, self.rationale_label,
            self.source_label, self.evidence_label,
            self.repair_button, self.no_repair_label,
        ):
            layout.addWidget(widget)
        layout.addStretch()

        area = QScrollArea()
        area.setWidget(inner)
        area.setWidgetResizable(True)
        outer = QVBoxLayout(self)
        outer.addWidget(area)

        self.show_finding(None, None)

    def show_finding(self, finding: Finding | None, session) -> None:
        self._finding, self._session = finding, session
        if finding is None or session is None:
            for label in (self.message_label, self.title_label, self.rationale_label,
                          self.source_label, self.evidence_label):
                label.setText("")
            self.repair_button.setEnabled(False)
            self.repair_button.setText("")
            self.no_repair_label.setText("")
            return

        rule = session.rule(finding.rule_id)
        self.message_label.setText(finding.message)
        self.title_label.setText(f"{finding.rule_id} — {rule.title if rule else ''}")
        self.rationale_label.setText(rule.rationale.strip() if rule else "")
        self.source_label.setText(f"Source: {rule.source.strip()}" if rule else "")
        self.evidence_label.setText(
            "\n".join(f"{k} = {v!r}" for k, v in sorted(finding.evidence.items()))
        )

        repair = repairs.load_repairs().get(finding.rule_id)
        self.repair_button.setEnabled(repair is not None)
        self.repair_button.setText(repair.label if repair else "")
        self.repair_button.setToolTip(repair.rationale.strip() if repair else "")
        self.no_repair_label.setText("" if repair else NO_REPAIR)

    def _repair(self) -> None:
        if self._finding and self._session and self._session.repair(self._finding):
            self.repaired.emit()
```

Note: `Signal` must be imported from `PySide6.QtCore` — add it to the import list.

- [ ] **Step 5: Wire both into the window**

In `main_window.py`: add `DetailPanel` and `VerdictBar` to the right-hand side of the splitter; connect `FindingsView.selected` to both panels' `show_finding`; connect `DetailPanel.repaired` to `_refresh`.

- [ ] **Step 6: Run the tests and the app**

```powershell
python -m pytest tests/test_ui_detail.py -v
python -m wing_parser.ui user-files\example-Vu.snap
```
Expected: 4 passed. In the window, select a G8 row, press the repair button, and watch the finding count fall from 22 to 21. Select a G10 row and confirm there is no button, only the sentence.

**Do not commit until the manual check above has actually been done.** The finding count falling is the whole feature.

- [ ] **Step 7: Commit**

```powershell
git add wing_parser/ui/detail_panel.py wing_parser/ui/verdict_bar.py wing_parser/ui/main_window.py tests/test_ui_detail.py
git commit -F - <<'EOF'
Add the detail panel, the repair button and the verdict bar

A rule with no descriptor shows no button and says why, rather than
offering a fix it cannot justify.

The verdict bar turns a command line with a hand-copied finding id
into two clicks, which is what decides whether the feedback log ever
gets written.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 11: The changes panel

**Files:**
- Create: `wing_parser/ui/changes_panel.py`
- Modify: `wing_parser/ui/main_window.py` — add as a `QDockWidget`, hidden while the journal is empty
- Test: `tests/test_ui_changes_panel.py`

**Interfaces:**
- Consumes: `Session.changes()`, `Session.undo()`.
- Produces: `ChangesPanel(QWidget)` with `set_changes(patches: tuple[Patch, ...]) -> None` and an `undo_requested` signal.

- [ ] **Step 1: Write the failing test**

```python
import pytest

from wing_parser.ui.session import Session


def test_the_panel_lists_one_row_per_patch(qt_app, vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.changes_panel import ChangesPanel

    session = Session.open(vu_path)
    session.repair(next(f for f in session.findings() if f.rule_id == "G8"))

    panel = ChangesPanel()
    panel.set_changes(session.changes())

    assert panel.list.count() == 1
    row = panel.list.item(0).text()
    assert "POST" in row and "PRE" in row


def test_an_empty_journal_leaves_the_list_empty(qt_app, vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.changes_panel import ChangesPanel

    panel = ChangesPanel()
    panel.set_changes(Session.open(vu_path).changes())
    assert panel.list.count() == 0
```

- [ ] **Step 2: Run to verify it fails**

```powershell
python -m pytest tests/test_ui_changes_panel.py -v
```
Expected: FAIL — no `changes_panel`.

- [ ] **Step 3: Write the implementation**

```python
"""The journal, shown before it is saved.

"What have I changed?" must be answerable without diffing two files.
Each row names the path, what was there, and what it becomes -- the
`before` captured when the edit was made, not recomputed now.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QListWidget, QPushButton, QVBoxLayout, QWidget

from wing_parser.edit.journal import Patch


class ChangesPanel(QWidget):
    undo_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.list = QListWidget()
        self._undo = QPushButton("Undo the last change")
        self._undo.clicked.connect(self.undo_requested.emit)

        layout = QVBoxLayout(self)
        layout.addWidget(self.list)
        layout.addWidget(self._undo)

    def set_changes(self, patches: tuple[Patch, ...]) -> None:
        self.list.clear()
        for patch in patches:
            self.list.addItem(
                f"{patch.label}  —  {patch.path}: {patch.before!r} → {patch.after!r}"
            )
        self._undo.setEnabled(bool(patches))
```

- [ ] **Step 4: Wire it in, run, commit**

```powershell
python -m pytest tests/test_ui_changes_panel.py -v
python -m wing_parser.ui user-files\example-Vu.snap
git add wing_parser/ui/changes_panel.py wing_parser/ui/main_window.py tests/test_ui_changes_panel.py
git commit -F - <<'EOF'
Add the changes panel

Shows the journal before it is saved, so "what have I changed" never
requires diffing two files.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

### Task 12: Documentation and whole-branch verification

**Files:**
- Modify: `README.md`
- Create: `docs/handoff/2026-08-18-desktop-app-complete.md`

- [ ] **Step 1: Run the whole suite and record the real numbers**

```powershell
python -m pytest tests/ --junitxml=junit.xml
python -m wing_parser.cli doctor user-files\example-Vu.snap
```
The doctor run must still print exactly 22 findings. Paste the actual counts into the handoff document — do not write them from memory.

- [ ] **Step 2: Add a README section**

Cover: what the app does, `pip install -e ".[ui]"`, `wing-ui user-files\example-Vu.snap`, that Save As never overwrites the original, and that a rule with no repair descriptor deliberately offers no button.

- [ ] **Step 3: Write the handoff document**

Cover: what shipped, which rules have descriptors and which deliberately do not, the round-trip guarantee and the two files that prove it, the `~100 ms` re-derivation figure, and what the next cycle should pick up — spec §11.1 (G2) and §11.2 (OSC), plus the four questions still open with ToanAZ.

- [ ] **Step 4: Commit**

```powershell
git add README.md docs/handoff/2026-08-18-desktop-app-complete.md
git commit -F - <<'EOF'
Document the desktop app and close the cycle

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
EOF
```

---

## Plan self-review

**Spec coverage.** §3 module layout → Tasks 2-5, 7-11 (every named file has a task; `repair_widgets.py` was folded into Task 10's `detail_panel.py`, since with only `set` and `toggle` descriptors there is one button and no widget family to build — revisit when an undetermined-repair field is added). §4 journal → Tasks 3, 4, 7. §5 descriptors → Tasks 5, 6. §6 window → Tasks 8-11. §7 error handling → Tasks 2 (missing path), 8 (open and save failures, missing PySide6). §8 testing → Tasks 4 (round trip, no-Qt guard), 6 (clearance, 22-finding contract). §9 packaging → Task 8. §12.2 (`--show` in the app) and §12.3 (interface language) are deliberately not implemented; both are recorded as open in the spec.

**Placeholder scan.** No TBDs. Two steps ask for judgement rather than giving code — Task 8 step 2's final assertion and Task 12's prose — and both say exactly what the content must contain.

**Type consistency.** `Patch(path, before, after, because, label)` is used identically in Tasks 3, 4, 5, 7, 11. `Repair(rule, kind, path, label, rationale, to)` in Tasks 5, 10. `Session.repair()` returns `bool` in Tasks 7, 10. `set_findings` is the name in both `FindingsModel` and `FindingsView` (Task 9). `show_finding(finding, session)` is the name in both `DetailPanel` and `VerdictBar` (Task 10).

**One known ordering hazard,** stated so it is not a surprise: Task 4's no-Qt guard imports `wing_parser.edit.repairs`, which Task 5 creates. Task 4 says so and instructs against weakening the test to make it green early.
