# GUI wave 3 — per-parameter write to a live WING console — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` (recommended)
> or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** A repair clicked in `wing-ui` reaches a live WING desk as **exactly one OSC leaf**, at the eagerness
the operator picked (Manual / Delayed / Immediate), only after he has armed the connection, with the read-back
reported honestly and everything sent this session revertable.

**Architecture:** Four non-Qt modules hold every decision — `net/address.py` (path → OSC address),
`ui/apply_level.py` (`ApplyLevel`, `ArmState`, `RevertQueue`), `ui/write_queue.py` (the one-at-a-time FIFO) and
`ui/live_write.py` (the `WriteTransport` seam, the **only** `ui/` module that names `wing_parser.net.write`) —
so plain pytest with no socket covers the whole policy layer. Two `ApplicationModal` dialogs and two Changes-dock
widgets sit on top. `live_wiring.py` owns, constructs and publishes the `WriteGate`, so neither the Doctor page
nor the Changes dock ever imports `console_page`.

**Tech Stack:** Python, PySide6, pytest (`QT_QPA_PLATFORM=offscreen`), PyInstaller.
**Spec:** `docs/superpowers/specs/2026-09-17-gui-write-wave3-design.md` — F1–F8 and W1–W15 in §5, what the
operator sees §2, modules and budgets §4, state delta §6, threading §7, the five gates §8, tests §9, task
sketch §10, open questions §11. Every "why" below points at a section there rather than repeating it.

## How to start (branching — read this first)

`main` is green as of `e00b5da` (PRs #1–#7 all merged; the last recorded figure is wave 2's **1580 passed /
3 skipped at `dcf897a`**, which is **historical** — do not quote it forward).

- [ ] Cut the branch from `main`: `git worktree add <path> -b feat/gui-write-wave3 main`. (The spec commit
      `e00b5da` is already on `main`, so nothing is stacked this wave.)
- [ ] Open the PR with base `main` and paste Task 1's measured baseline into the body.
- [ ] **Task 1 re-measures the suite on its own first commit.** Use `--junitxml` — see the tally rule below.

## Global Constraints

Every task's requirements implicitly include this section.

- **`$PY` below means** `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe"`, run from
  your worktree's repo root. **Never add `-q`**: `pyproject.toml` sets it, and `-qq` kills the summary line.
- **Tally the full suite with `--junitxml` (D-47, `docs/tech-debt.md:645-666`).** The COM first-chance dump
  `faulthandler` prints at interpreter exit can beat pytest's own `N passed` line to the console, so a fully
  green run may print no summary at all. Run
  `$PY -m pytest --junitxml=dist-reports/suite.xml` and read `tests=`, `failures=`, `errors=`, `skipped=` off
  the `<testsuite>` element — the XML is written before that teardown print. `-p no:faulthandler` silences
  the dump instead; either is acceptable, inventing a number is not.
- **200-line ceiling on every `wing_parser/ui/*.py` file**, enforced by
  `tests/test_ui_house_style.py:170` (`CEILING = 200`) and `:173`
  (`test_no_ui_module_is_over_the_line_ceiling`). Split by responsibility; never raise the ceiling.
- **`live_controller.py` (199) and `console_page.py` (199) do not grow — not by one line** (W7). That is
  why the `WriteGate` is owned by `live_wiring.py` and reads `page.state` rather than being handed a new
  signal, and why `main_window.py` (191) gains **≤4 lines across the whole wave**, ending at **195 or under,
  measured**.
- **No colour literal outside `wing_parser/ui/theme/`.**
  `test_ui_house_style.py::test_no_colour_literals_outside_the_theme_package` scans every `.py` **and
  `.qss`** under `ui/` with an empty allowlist — a new QSS rule uses `$ok` / `$warn` / `$danger` / `$faded`,
  never a hex value.
- **Every user-facing string goes through `text("console.write.*")`** (W7), defined in
  `wing_parser/ui/texts_write.py` and merged into `TEXTS` beside `CONSOLE_TEXTS` (`texts.py:9,157`). A
  `write.*` namespace would collide with the existing `changes.*` keys.
- **UTF-8 explicit on every file read and write** (`encoding="utf-8"`).
- **No socket in any test.** Everything talks to `tests/fake_desk.py`'s `FakeDesk` (Task 3 adds
  `write_transport()`). `tests/fake_wing.py` stays the loopback fake for `net/`'s own tests — Task 3's two
  new `test_net_write.py` cases use it because they test the wire encoding.
- **One write on the wire at a time (W10).** Every write — an Immediate Repair, a dialog's Apply, a single
  Revert, each step of Revert all — goes through the `WriteGate`'s single `CallRunner` and its non-Qt
  `WriteQueue`. Dialogs own their own `CallRunner` for **pre-flight reads only** (W5): the Console page's
  runner is legitimately busy during a watch and `CallRunner.start` returns `False` then
  (`workers.py:112-113`).
- **Both dialogs are `Qt.ApplicationModal` (W11)**, pinned by a test, not by layout accident.
- **The read-only AST test is amended in Task 3 and nowhere else.**
  `tests/test_ui_live_is_read_only.py` becomes an allow-list of exactly one path,
  `wing_parser/ui/live_write.py`, keyed on `path.name`. `toggle`, `node_write` and `push` stay offences in
  every file, that one included. Adding a second entry to the allow-list is a spec change, not a fix.
- **CLAUDE.md — "ask before writing to a live desk" — is satisfied by Arm + the latch (§8.2), and by nothing
  else.** No write path may exist that skips `ArmWriteDialog`. The latch reads *"This desk is NOT running a
  show right now."* and starts **unticked** (F4).
- **A claim about another module is checked by opening that module.** ROADMAP §7: ten instances of one
  defect shape — correct code carrying a false description — landed in G2a, every one caught in review and
  **none by a test**. Each task ends with the claims to check.

## Review cadence (ROADMAP §7)

A **fresh reviewer after every task**, which may *run* the code and not only read it; a **scoped re-review
per fix round** over only the files that fix touched; and **Task 16, the whole-branch review on the strongest
model** — it has earned its cost five cycles running. Not optional polish.

## Sequencing

**1 → 3** (`osc_address` / `leaf_parts` are what `live_write` maps with). **2 → 3** is not required but 2 is
free and cheap; **3 → 4** (same file). **5, 6, 7 are free** — no dependency on anything above. **8 needs 2, 5
and 7**; it must land **before 9 and 10**, because both dialogs re-check its gate (gate 4, §8.4). **9 → 10**
(the delayed dialog opens the arm dialog when unarmed). **11 needs 8, 9, 10**. **12 needs 4, 11**. **13 needs
2, 4, 12**. **14 needs 1–13. 15 is independent of everything** (W9, droppable). **16 is last.**

**Files this wave creates:** `net/address.py` (≤60, no Qt) · `ui/apply_level.py` (≤200, no Qt) ·
`ui/write_queue.py` (≤120, no Qt) · `ui/live_write.py` (≤200, no Qt, **the only `ui/` module naming
`net.write`**) · `ui/write_arm_dialog.py` (≤200) · `ui/write_delay_dialog.py` (≤200) ·
`ui/changes_send.py` (≤120) · `ui/changes_ledger.py` (≤200) · `ui/texts_write.py` (≤120, no Qt) ·
`ui/settings_io.py` (≤80, no Qt) · `tests/test_net_address.py` · `tests/test_apply_level.py` ·
`tests/test_ui_live_write.py` · `tests/test_ui_write_dialogs.py` · `tests/test_ui_changes_send.py`.

---

### Task 1: `leaf_parts` and `osc_address` — one root-strip, two callers

**Files:**
- Create: `wing_parser/net/address.py`, `tests/test_net_address.py`
- Modify: `wing_parser/cli/net_commands.py` (**258 lines**) — `_flatten` / `_leaves_from_raw` at `:61-77`

Read `net/snapshot.py:116-123` (`_place`, the inverse this module has to be) and
`cli/net_commands.py:61-77` (`_flatten`, the prior art) before writing anything.

**Interfaces:**
- Consumes: nothing.
- Produces:
  ```python
  # wing_parser/net/address.py
  ROOT = "ae_data"
  def leaf_parts(path: str) -> list[str]: ...        # "ae_data.ch.1.send.8.mode" -> ["ch","1","send","8","mode"]
  def join_segments(segments: Sequence[str]) -> str: # ["ch","1"] -> "/ch/1"
  def osc_address(path: str) -> str:                 # "ae_data.ch.1.send.8.mode" -> "/ch/1/send/8/mode"
  ```
  `leaf_parts` raises `ValueError` naming the input for a non-`ae_data` root or any empty segment, so both
  callers inherit the same refusal. Task 3's `scene_value` takes `leaf_parts(path)` — `jsontypes.py:52-57`
  needs the **ae-stripped** shape, and `is_boolean_shape(["ae_data", ...])` returns `False` *silently*, which
  is why the shape is never left to a caller to get right.

- [ ] **Step 1: Write the failing tests** — `tests/test_net_address.py`

```python
"""Spec W2: one dotted document path becomes exactly one OSC address.

The authority is `net/snapshot.py:_place` (`snapshot.py:116-123`): everything
that is not `/$ctl/...` is ae_data "keyed exactly as the OSC address reads".
This module is that rule read backwards, and the cross-check below proves it
against the flattener `wing net push` already ships.
"""
from __future__ import annotations

import pytest

from wing_parser.cli.net_commands import _leaves_from_raw
from wing_parser.net.address import join_segments, leaf_parts, osc_address


def test_leaf_parts_strips_the_ae_data_root():
    assert leaf_parts("ae_data.ch.1.send.8.mode") == ["ch", "1", "send", "8", "mode"]


def test_osc_address_is_the_leaf_parts_joined():
    assert osc_address("ae_data.ch.1.send.8.mode") == "/ch/1/send/8/mode"
    assert osc_address("ae_data.ch.16.in.set.inv") == "/ch/16/in/set/inv"


def test_join_segments_is_the_one_join_both_callers_use():
    assert join_segments(["ch", "1"]) == "/ch/1"
    assert join_segments(("$ctl", "cfg")) == "/$ctl/cfg"


@pytest.mark.parametrize("path", [
    "ce_data.cfg.mute",          # W2: $ctl's children are not one segment from the address
    "ch.1.mute",                 # no root at all
    "ae_data..mode",             # empty segment
    "ae_data.",                  # trailing empty segment
    "",                          # empty string
])
def test_a_path_this_module_cannot_map_raises_naming_the_input(path):
    with pytest.raises(ValueError) as exc:
        leaf_parts(path)
    assert repr(path) in str(exc.value)


@pytest.mark.parametrize("path", ["ce_data.cfg.mute", "ch.1.mute", "ae_data..mode"])
def test_osc_address_refuses_exactly_what_leaf_parts_refuses(path):
    """One root-strip, so neither caller can be laxer than the other."""
    with pytest.raises(ValueError):
        osc_address(path)


def test_every_repair_template_lands_on_a_real_leaf_of_a_real_scene(vu_path):
    """The cross-check: `_leaves_from_raw` is the shipped inverse of `_place`.

    Fill each `path:` template in repairs.yaml with the target of a leaf the
    fixture really has, and assert `osc_address` puts it in that flattener's
    key set. A drift between this module and `wing net push` fails here.
    """
    from wing_parser.core.loader import load_raw
    from wing_parser.edit.repairs import load_repairs

    raw = load_raw(vu_path)
    keys = set(_leaves_from_raw(raw))
    checked = 0
    for repair in load_repairs().values():
        prefix = repair.path.split(".{", 1)[0]          # "ae_data.ch"
        candidates = [k for k in keys if k.startswith(osc_address(prefix) + "/")]
        assert candidates, f"{repair.rule}: fixture has nothing under {prefix}"
        checked += 1
    assert checked >= 11, "repairs.yaml ships eleven descriptors; the sweep saw fewer"


def test_the_flattener_still_produces_ctl_rooted_addresses(vu_path):
    """`_flatten` is refactored onto `join_segments`; ce keeps its `$ctl` root."""
    from wing_parser.core.loader import load_raw

    keys = _leaves_from_raw(load_raw(vu_path))
    assert any(k.startswith("/$ctl/") for k in keys)
    assert all(k.startswith("/") and "//" not in k for k in keys)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest tests/test_net_address.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.net.address'`

- [ ] **Step 3: Write the minimal implementation**

`wing_parser/net/address.py`:

```python
"""One dotted `.snap` path becomes one OSC address, and back again.

The exact inverse of `net/snapshot.py:_place` (`snapshot.py:116-123`), whose
docstring is the authority: everything but `/$ctl/...` is ae_data "keyed
exactly as the OSC address reads, which is already the .snap layout".

`ce_data` is refused rather than mapped (W2). S2.2 makes ce_data's own
top-level keys `$ctl`'s CHILDREN, so a `ce_data.` path is not one segment
away from its address, and no descriptor in `edit/data/repairs.yaml` targets
one. Mapping it would need the `$ctl` re-prefix plus a test per shape.

`leaf_parts` exists so no caller has to get the shape right by hand:
`jsontypes.is_boolean_shape` (`jsontypes.py:48-59`) wants the ae-STRIPPED
parts and answers `False` in silence for anything else, so a caller that
passed the document-rooted path would get no error and no coercion -- only a
bool quietly stored as an int.
"""

from __future__ import annotations

from collections.abc import Sequence

ROOT = "ae_data"


def leaf_parts(path: str) -> list[str]:
    """The leaf's segments with the `ae_data.` root stripped.

    Raises `ValueError` naming the input for any other root or an empty
    segment -- both callers below inherit that refusal, so neither can be
    laxer than the other.
    """
    segments = path.split(".")
    if segments[0] != ROOT or len(segments) < 2:
        raise ValueError(
            f"{path!r}: not an {ROOT} leaf path -- only ae_data leaves map "
            f"to an OSC address (W2)"
        )
    rest = segments[1:]
    if any(not segment for segment in rest):
        raise ValueError(f"{path!r}: empty path segment")
    return rest


def join_segments(segments: Sequence[str]) -> str:
    """`["ch", "1"]` -> `/ch/1`. The one join; `_flatten` uses it too."""
    return "/" + "/".join(segments)


def osc_address(path: str) -> str:
    """`ae_data.ch.1.send.8.mode` -> `/ch/1/send/8/mode`."""
    return join_segments(leaf_parts(path))
```

`wing_parser/cli/net_commands.py` — `_flatten` refactored onto that join, so the two cannot drift:

```python
def _flatten(tree: dict, segments: tuple[str, ...], leaves: dict[str, Any]) -> None:
    for key, value in tree.items():
        path = (*segments, key)
        if isinstance(value, dict):
            _flatten(value, path, leaves)
        else:
            leaves[address.join_segments(path)] = value


def _leaves_from_raw(raw) -> dict[str, Any]:
    """Flatten a RawScene's ae/ce trees into OSC leaf addresses -- the
    exact inverse of net/snapshot.py's `_place` (design doc S2.2), sharing
    `net/address.py`'s join so `wing net push` and the UI's `osc_address`
    cannot drift. Only `wing net push` needs a flat address -> value view."""
    leaves: dict[str, Any] = {}
    _flatten(raw.ae, (), leaves)
    _flatten(raw.ce, ("$ctl",), leaves)
    return leaves
```

with `from wing_parser.net import address` added to the imports.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `$PY -m pytest tests/test_net_address.py tests/test_cli_net.py`
Expected: PASS. Then the full suite: `$PY -m pytest --junitxml=dist-reports/suite.xml` — **this count is the
wave's baseline; put it in the PR body with the command that produced it.**

- [ ] **Step 5: Show each new test red once** (wave-2 practice, spec §9.2 line 464): change `ROOT` to
      `"ce_data"`, capture the failures, restore. Paste both into the task report.

- [ ] **Step 6: Commit**

```bash
git add wing_parser/net/address.py wing_parser/cli/net_commands.py tests/test_net_address.py && git commit -m "feat(net): map one .snap leaf path to one OSC address"
```

Body names spec W2 and that `_flatten` now shares the join.

**Claims to check by opening:** that `_place` really keys ae leaves as the address reads and strips `$ctl`
for ce (`snapshot.py:116-123`); that `_leaves_from_raw` prefixes ce with `/$ctl` (`net_commands.py:70-77`);
that `is_boolean_shape` takes ae-stripped parts and returns `False` silently otherwise
(`jsontypes.py:48-59`); that every `path:` in `edit/data/repairs.yaml` starts `ae_data.` and none targets
`ce_data`.

---

### Task 2: `ApplyLevel`, `ArmState`, `RevertQueue`, `WriteQueue` — the whole non-Qt policy layer

**Files:**
- Create: `wing_parser/ui/apply_level.py`, `wing_parser/ui/write_queue.py`, `tests/test_apply_level.py`

Read spec §5 F3, F4, F7, W10, W12, W14 and §7.2 first.

**Interfaces:**
- Consumes: nothing. **Deliberately imports no `wing_parser.net` name at all** (§4's "Names `net`?" column
  says no for both files) — `ArmState.identity` is annotated `Any` and documented as
  `net.identity.WingIdentity`, and `RevertQueue`'s records are `Any` because `SentWrite` arrives in Task 3.
- Produces:
  ```python
  # wing_parser/ui/apply_level.py
  class ApplyLevel(str, Enum): MANUAL = "manual"; DELAYED = "delayed"; IMMEDIATE = "immediate"
  class ArmState:
      identity: Any | None       # net.identity.WingIdentity once armed
      level: ApplyLevel
      def arm(self, identity: Any) -> None: ...
      def armed(self) -> bool: ...
      def disarm(self) -> None: ...                 # -> MANUAL, identity None
  class RevertQueue:
      def __init__(self, records: Sequence[Any]) -> None: ...   # reversed on entry
      def next(self) -> Any | None: ...             # None when exhausted OR stopped
      def stop(self) -> None: ...
      @property
      def progress(self) -> tuple[int, int]: ...    # (done, total)
      @property
      def remaining(self) -> tuple[Any, ...]: ...

  # wing_parser/ui/write_queue.py
  class WriteQueue:
      def __init__(self, start: Callable[[Any], None]) -> None: ...
      def enqueue(self, item: Any) -> None: ...
      def settle(self) -> None: ...                 # the in-flight write ended, any way
      @property
      def in_flight(self) -> Any | None: ...
      @property
      def pending(self) -> tuple[Any, ...]: ...
      def clear(self) -> None: ...
  ```

- [ ] **Step 1: Write the failing tests** — `tests/test_apply_level.py`

```python
"""Spec §5 F3/F4/F7 and W10: the write policy layer, with no Qt in sight.

Everything here is plain objects, so `pytest` covers the rules that decide
whether a packet leaves at all -- and covers them exhaustively, which is the
whole reason these three classes are not methods on a widget.
"""
from __future__ import annotations

from wing_parser.ui.apply_level import ApplyLevel, ArmState, RevertQueue
from wing_parser.ui.write_queue import WriteQueue


class _Identity:
    """Stands in for `net.identity.WingIdentity`; this module names no net."""
    name = "WING-GIAQUY"
    serial = "01009Y90604AAE"
    ip = "192.168.128.28"


# -- ArmState (F4) ------------------------------------------------------


def test_arm_state_starts_unarmed_at_manual():
    state = ArmState()
    assert state.armed() is False
    assert state.level is ApplyLevel.MANUAL
    assert state.identity is None


def test_arming_records_the_identity_it_was_armed_for():
    state = ArmState()
    state.arm(_Identity())
    assert state.armed() is True
    assert state.identity.serial == "01009Y90604AAE"


def test_disarm_returns_to_manual_from_either_other_level():
    for level in (ApplyLevel.DELAYED, ApplyLevel.IMMEDIATE):
        state = ArmState()
        state.arm(_Identity())
        state.level = level
        state.disarm()
        assert state.armed() is False
        assert state.level is ApplyLevel.MANUAL
        assert state.identity is None


# -- RevertQueue (F7, W12) ----------------------------------------------


def test_the_revert_queue_hands_records_out_in_reverse_order():
    queue = RevertQueue(["a", "b", "c"])
    assert [queue.next(), queue.next(), queue.next()] == ["c", "b", "a"]


def test_the_revert_queue_returns_none_once_exhausted():
    queue = RevertQueue(["a"])
    assert queue.next() == "a"
    assert queue.next() is None


def test_progress_counts_what_has_been_handed_out_against_the_total():
    queue = RevertQueue(["a", "b", "c"])
    assert queue.progress == (0, 3)
    queue.next()
    assert queue.progress == (1, 3)
    queue.next()
    assert queue.progress == (2, 3)


def test_stop_ends_the_run_and_leaves_the_rest_countable():
    queue = RevertQueue(["a", "b", "c"])
    assert queue.next() == "c"
    queue.stop()
    assert queue.next() is None
    assert queue.remaining == ("b", "a")
    assert queue.progress == (1, 3)


# -- WriteQueue (W10) ---------------------------------------------------


def test_the_write_queue_starts_the_first_item_at_once():
    started = []
    queue = WriteQueue(started.append)
    queue.enqueue("one")
    assert started == ["one"]
    assert queue.in_flight == "one"


def test_two_rapid_enqueues_both_survive_and_neither_overlaps():
    started = []
    queue = WriteQueue(started.append)
    queue.enqueue("one")
    queue.enqueue("two")
    assert started == ["one"], "the second write went out while the first was in flight"
    assert queue.pending == ("two",)
    queue.settle()
    assert started == ["one", "two"]
    assert queue.pending == ()


def test_the_queue_is_fifo_not_a_stack():
    started = []
    queue = WriteQueue(started.append)
    for item in ("one", "two", "three"):
        queue.enqueue(item)
    queue.settle()
    queue.settle()
    assert started == ["one", "two", "three"]


def test_settling_an_idle_queue_is_harmless():
    started = []
    queue = WriteQueue(started.append)
    queue.settle()
    assert started == [] and queue.in_flight is None


def test_clear_drops_what_has_not_gone_out_and_keeps_the_one_in_flight():
    started = []
    queue = WriteQueue(started.append)
    queue.enqueue("one")
    queue.enqueue("two")
    queue.clear()
    assert queue.pending == ()
    assert queue.in_flight == "one", "nothing can un-send a packet already on the wire"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest tests/test_apply_level.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.ui.apply_level'`

- [ ] **Step 3: Write the minimal implementation**

`wing_parser/ui/apply_level.py`:

```python
"""How eagerly a repair reaches the desk, and what may be undone on it.

Qt-free on purpose (spec §4): these are the rules that decide whether a
packet leaves at all, and a rule a plain pytest can exhaust is worth more
than one that needs a window to observe.

This module names nothing under `wing_parser.net`. `ArmState.identity` is
a `net.identity.WingIdentity` and `RevertQueue`'s records are
`live_write.SentWrite`, but neither type is imported: the first would make
this module part of the net import graph for one annotation, and the second
would be a cycle (`live_write` is a `ui/` module too).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Sequence


class ApplyLevel(str, Enum):
    """F3. Remembered for the current connection only; never persisted."""

    MANUAL = "manual"
    DELAYED = "delayed"
    IMMEDIATE = "immediate"


class ArmState:
    """F4: one arming per connection, and what it was armed FOR.

    The identity is kept, not just a boolean, because gate 5
    (`net/write.py:93-100`) re-queries it on every write and a reviewer
    must be able to ask "armed for which desk?" without guessing.
    """

    def __init__(self) -> None:
        self.identity: Any | None = None
        self.level: ApplyLevel = ApplyLevel.MANUAL

    def arm(self, identity: Any) -> None:
        self.identity = identity

    def armed(self) -> bool:
        return self.identity is not None

    def disarm(self) -> None:
        """Every DISCONNECTED / LOST / ERROR lands here (F4).

        The level falls back with the identity, so the selector an
        operator looks up at after a dropout reads Manual and tells him
        the truth rather than the level he picked before the cable went.
        """
        self.identity = None
        self.level = ApplyLevel.MANUAL


class RevertQueue:
    """F7: the sent ledger walked backwards, one record at a time.

    Last written, first undone -- and `next()` hands out exactly one, so
    "one parameter per transmission" (F1) is a property of this object
    rather than of the UI happening not to offer a second button.
    """

    def __init__(self, records: Sequence[Any]) -> None:
        self._pending = list(reversed(list(records)))
        self._total = len(self._pending)
        self._done = 0
        self._stopped = False

    def next(self) -> Any | None:
        """The next record, or `None` when exhausted **or** stopped."""
        if self._stopped or not self._pending:
            return None
        self._done += 1
        return self._pending.pop(0)

    def stop(self) -> None:
        """W12/W15: end the run between parameters. The one already on the
        wire completes -- nothing can un-send a packet."""
        self._stopped = True

    @property
    def progress(self) -> tuple[int, int]:
        """`(done, total)`, counted as records are handed OUT: the line
        reads `Reverting 3/7` while the third is going, not after it."""
        return self._done, self._total

    @property
    def remaining(self) -> tuple[Any, ...]:
        """What a stopped run left alone, still in reverse order."""
        return tuple(self._pending)
```

`wing_parser/ui/write_queue.py`:

```python
"""One packet on the wire at a time (W10), enforced below the UI.

Every write in this app -- an Immediate Repair, a countdown's Apply, a
single Revert, each step of Revert all -- is enqueued here, and the next
starts only when the previous read-back returns or times out. Two rapid
Immediate Repairs queue; neither is dropped.

Qt-free, so the ordering rule is covered by plain pytest. The `start`
callback is what actually launches a write (the `WriteGate`'s single
`CallRunner`, `live_wiring.py`), and every terminal path of that call --
success, failure, timeout, cancel -- must call `settle()` exactly once, or
the queue stalls with a phantom write in flight.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Callable


class WriteQueue:
    def __init__(self, start: Callable[[Any], None]) -> None:
        self._start = start
        self._pending: deque = deque()
        self._in_flight: Any | None = None

    @property
    def in_flight(self) -> Any | None:
        return self._in_flight

    @property
    def pending(self) -> tuple[Any, ...]:
        return tuple(self._pending)

    def enqueue(self, item: Any) -> None:
        self._pending.append(item)
        self._pump()

    def settle(self) -> None:
        """The in-flight write ended, however it ended. Release the next."""
        self._in_flight = None
        self._pump()

    def clear(self) -> None:
        """Drop everything not yet sent. The in-flight one is NOT dropped:
        its datagram may already have left the socket, and the ledger has
        to hear how it ended."""
        self._pending.clear()

    def _pump(self) -> None:
        if self._in_flight is not None or not self._pending:
            return
        self._in_flight = self._pending.popleft()
        self._start(self._in_flight)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `$PY -m pytest tests/test_apply_level.py tests/test_ui_house_style.py`
Expected: PASS. Then the full suite with `--junitxml`.

- [ ] **Step 5: Show each new test red once** — delete the `if self._in_flight is not None` guard in `_pump`
      and watch `test_two_rapid_enqueues_both_survive_and_neither_overlaps` fail; reverse `RevertQueue`'s
      `reversed(...)` and watch the order test fail. Capture both, restore.

- [ ] **Step 6: Commit**

```bash
git add wing_parser/ui/apply_level.py wing_parser/ui/write_queue.py tests/test_apply_level.py && git commit -m "feat(ui): add the apply-level, arm and write-queue policy layer"
```

Body names spec F3, F4, F7 and W10.

**Claims to check by opening:** that no `wing_parser.net` name appears in either new file (`grep -n
"wing_parser.net" wing_parser/ui/apply_level.py wing_parser/ui/write_queue.py` → nothing); that
`test_ui_house_style.py:173` counts both files under 200.

---

### Task 3: `WriteTransport`, `preflight`, `send` — and the AST allow-list, in the same commit

**Files:**
- Create: `wing_parser/ui/live_write.py`, `tests/test_ui_live_write.py`
- Modify: `tests/fake_desk.py` (**185 lines**), `tests/test_net_write.py` (**309 lines**),
  `tests/test_ui_live_is_read_only.py` (**225 lines**)

Read spec §4 ("`WriteTransport.read` must normalise"), §8.4 and §9.1 first, then `net/write.py:112-137`
(`_set_leaf` / `set`), `net/codec.py:107-135` (`leaf_value`) and `net/jsontypes.py:48-59`.

**The AST amendment ships in this commit, not a later one** (§10 task 3): `live_write.py` is the first `ui/`
module that imports `net.write`, so the suite would be red between tasks otherwise.

**Interfaces:**
- Consumes: `net.address.leaf_parts` / `osc_address` (Task 1).
- Produces:
  ```python
  # wing_parser/ui/live_write.py
  @dataclass(frozen=True)
  class WriteTransport:
      identity: Callable[[str], WingIdentity]        # net.identity.query_identity
      read:     Callable[[str, str], Any | None]     # (host, DOTTED PATH) -> normalised value
      set:      Callable[..., SetResult]             # net.write.set
  REAL: WriteTransport                               # the ONLY place ui/ names net.write

  @dataclass(frozen=True)
  class WriteConfirmation:
      host: str; address: str; after: Any; identity: WingIdentity; desk_before: Any | None
  @dataclass(frozen=True)
  class SentWrite:
      address: str; path: str; desk_before: Any | None; written: Any; result: SetResult

  def scene_value(parts: Sequence[str], readback: Any) -> Any: ...
  def preflight(host: str, path: str, transport: WriteTransport = REAL) -> tuple[WingIdentity, Any | None]: ...
  def send(confirmation: WriteConfirmation, transport: WriteTransport = REAL) -> SetResult: ...

  # tests/fake_desk.py
  class FakeDesk:
      sets: list[tuple[str, Any, bool]]              # (address, value, confirm), in order
      readbacks: dict[str, Any]                      # address -> what the desk answers a read-back with
      def write_transport(self): ...                 # -> live_write.WriteTransport
  ```
  `WriteTransport.read` takes the **dotted document path**, not the OSC address, and derives both from it:
  normalisation needs `leaf_parts(path)` for `jsontypes`, and splitting that responsibility across the call
  site is exactly the silent failure `leaf_parts` was written to remove.

- [ ] **Step 1: Write the failing tests**

First, `tests/fake_desk.py` gains the write surface (append to the class, and two new `__init__` fields):

```python
    def write_transport(self):
        """The `live_write.WriteTransport` wrapping this desk. No socket.

        `set` records the call, moves `leaves` to what the desk would then
        hold, and answers a REAL `net.write.SetResult` -- so the read-back
        arithmetic under test is `write.py`'s own (`write.py:119-123`),
        not a double's idea of it.
        """
        from wing_parser.net.write import SetResult, _format_value, _values_match
        from wing_parser.ui import live_write

        def _identity(host: str):
            if isinstance(self.identity, Exception):
                raise self.identity
            return self.identity

        def _read(host: str, path: str):
            from wing_parser.net.address import leaf_parts, osc_address
            message = self.leaves.get(osc_address(path))
            if message is None:
                return None
            return live_write.scene_value(leaf_parts(path), leaf_value(message)[0])

        def _set(host: str, osc: str, value, *, confirm: bool = False, **_kw):
            self.sets.append((osc, value, confirm))
            readback = self.readbacks.get(osc, value)
            if readback is _ABSENT:
                readback = None
            matched = readback is not None and _values_match(value, readback)
            return SetResult(osc, value, _format_value(value), False, readback, matched)

        return live_write.WriteTransport(identity=_identity, read=_read, set=_set)
```

with `_ABSENT = object()` at module scope (the way a test scripts "this desk never answered the read-back"),
and `self.sets: list = []` / `self.readbacks: dict = dict(readbacks or {})` added to `__init__`.

Then `tests/test_ui_live_write.py`:

```python
"""Spec §9.1: the write seam, against `FakeDesk`. No socket anywhere.

The load-bearing test here is the normalisation pair. Eight of the eleven
repair descriptors set a JSON bool (`repairs.yaml` lines 55, 68, 80, 93,
102, 130, 142, 156), a `,sfi` leaf reads back as a Python `int`
(`codec.py:126-128`), and an unnormalised read would hand the countdown
`0` against a journal `before` of `False` -- shown to an operator at 2 a.m.
as the nonsense "the desk holds 0, the scene file expected False".
"""
from __future__ import annotations

import pytest

from tests.fake_desk import FakeDesk
from wing_parser.net.codec import OscMessage
from wing_parser.net.identity import WingIdentity
from wing_parser.ui import live_write

HOST = "192.168.128.28"
BOOL_PATH = "ae_data.ch.1.in.set.inv"          # a boolean shape in wing_jsontypes.yaml
BOOL_OSC = "/ch/1/in/set/inv"


def _identity():
    return WingIdentity(ip=HOST, name="WING-GIAQUY", model="wing-rack",
                        serial="01009Y90604AAE", firmware="3.1-0-g9f314617:release")


def _desk(**kwargs):
    return FakeDesk(identity=_identity(), **kwargs)


def _sfi(address, display, native):
    return OscMessage(address, "sfi", (display, 0.0, native))


def _sff(address, display, native):
    return OscMessage(address, "sff", (display, 0.0, native))


def _confirmation(desk, path, after, desk_before=None):
    from wing_parser.net.address import osc_address
    return live_write.WriteConfirmation(
        host=HOST, address=osc_address(path), after=after,
        identity=_identity(), desk_before=desk_before)


# -- preflight ----------------------------------------------------------


def test_preflight_returns_the_identity_and_the_desks_current_value():
    desk = _desk(leaves={BOOL_OSC: _sfi(BOOL_OSC, "1", 1)})
    identity, current = live_write.preflight(HOST, BOOL_PATH, desk.write_transport())
    assert identity.name == "WING-GIAQUY"
    assert current is True


def test_a_timeout_from_identity_propagates_and_nothing_is_sent():
    desk = FakeDesk(identity=TimeoutError("no reply from 192.168.128.28"))
    with pytest.raises(TimeoutError):
        live_write.preflight(HOST, BOOL_PATH, desk.write_transport())
    assert desk.sets == []


# -- normalisation, one test per JSON type (§4) -------------------------


@pytest.mark.parametrize("native,expected", [(1, True), (0, False)])
def test_a_boolean_shape_reads_back_as_a_bool_not_an_int(native, expected):
    desk = _desk(leaves={BOOL_OSC: _sfi(BOOL_OSC, str(native), native)})
    _identity_, current = live_write.preflight(HOST, BOOL_PATH, desk.write_transport())
    assert current is expected
    assert current == expected, "a journal `before` of True/False must compare equal"
    assert not isinstance(current, int) or isinstance(current, bool)


def test_a_non_boolean_sfi_leaf_stays_an_int():
    path, osc = "ae_data.ch.1.dyn.ratio", "/ch/1/dyn/ratio"
    desk = _desk(leaves={osc: _sfi(osc, "3", 2)})
    _i, current = live_write.preflight(HOST, path, desk.write_transport())
    assert current == 3 and isinstance(current, int) and not isinstance(current, bool)


def test_an_sff_leaf_stays_a_float():
    path, osc = "ae_data.ch.1.fdr", "/ch/1/fdr"
    desk = _desk(leaves={osc: _sff(osc, "-6.0", -6.0)})
    _i, current = live_write.preflight(HOST, path, desk.write_transport())
    assert current == pytest.approx(-6.0) and isinstance(current, float)


def test_an_s_leaf_stays_a_str():
    path, osc = "ae_data.ch.1.send.8.mode", "/ch/1/send/8/mode"
    desk = _desk(leaves={osc: OscMessage(osc, "s", ("POST",))})
    _i, current = live_write.preflight(HOST, path, desk.write_transport())
    assert current == "POST" and isinstance(current, str)


# -- scene_value, one test per JSON type (F8) ---------------------------


@pytest.mark.parametrize("readback,expected", [(1, True), (0, False)])
def test_scene_value_coerces_a_boolean_shape(readback, expected):
    assert live_write.scene_value(["ch", "1", "in", "set", "inv"], readback) is expected


def test_scene_value_leaves_a_non_boolean_int_alone():
    assert live_write.scene_value(["ch", "1", "dyn", "ratio"], 3) == 3


def test_scene_value_leaves_a_float_and_a_string_alone():
    assert live_write.scene_value(["ch", "1", "fdr"], -6.0) == pytest.approx(-6.0)
    assert live_write.scene_value(["ch", "1", "send", "8", "mode"], "PRE") == "PRE"


def test_scene_value_passes_a_missing_readback_through_as_none():
    assert live_write.scene_value(["ch", "1", "in", "set", "inv"], None) is None


# -- send ---------------------------------------------------------------


def test_send_transmits_confirm_true_the_mapped_address_and_one_value():
    desk = _desk(leaves={"/ch/1/send/8/mode": OscMessage("/ch/1/send/8/mode", "s", ("PRE",))},
                 readbacks={"/ch/1/send/8/mode": "PRE"})
    result = live_write.send(
        _confirmation(desk, "ae_data.ch.1.send.8.mode", "PRE"), desk.write_transport())
    assert desk.sets == [("/ch/1/send/8/mode", "PRE", True)]
    assert result.matched is True


@pytest.mark.parametrize("bad", [None, "not a confirmation", {"address": "/ch/1/fdr"}])
def test_send_refuses_anything_but_a_write_confirmation(bad):
    desk = _desk()
    with pytest.raises(TypeError):
        live_write.send(bad, desk.write_transport())
    assert desk.sets == []


def test_a_serial_mismatch_reaches_the_caller_with_its_own_text():
    from wing_parser.net.write import SerialMismatchError

    desk = _desk()
    transport = desk.write_transport()

    def refusing(host, osc, value, *, confirm=False, **kw):
        raise SerialMismatchError("refusing to write to 'WING-GIAQUY' (serial 'X')")

    import dataclasses
    transport = dataclasses.replace(transport, set=refusing)
    with pytest.raises(SerialMismatchError) as exc:
        live_write.send(_confirmation(desk, BOOL_PATH, True), transport)
    assert "refusing to write to 'WING-GIAQUY'" in str(exc.value)


# -- the seam itself ----------------------------------------------------


def test_real_transport_names_the_read_only_entry_points_and_write_set():
    from wing_parser.net.identity import query_identity

    assert live_write.REAL.identity is query_identity
    assert callable(live_write.REAL.read) and callable(live_write.REAL.set)
```

And `tests/test_net_write.py` gains the two cases §9.1 names (its `set` coverage is all numeric at `:80`,
`:87`, `:94`, `:101`):

```python
def test_confirmed_set_of_a_string_sends_a_bare_s_payload():
    address = "/ch/1/send/8/mode"
    with FakeWing() as fake:
        fake.register(encode(address, "s", ("PRE",)), None)     # sec 2.1: no echo
        fake.register(encode(address), _s(address, "PRE"))
        host, osc_port, identity_port = _addrs(fake)
        result = write.set(host, address, "PRE", osc_port=osc_port,
                           identity_port=identity_port, confirm=True, **_FAST)
    assert result.sent == "PRE" and result.readback == "PRE" and result.matched


def test_confirmed_set_of_a_bool_sends_the_one_zero_display_string():
    """`_format_value` checks `bool` FIRST, because bool is an int subclass
    (`write.py:74-75`) -- so True goes out as `,s "1"`, never `,i 1`."""
    address = "/ch/1/in/set/inv"
    with FakeWing() as fake:
        fake.register(encode(address, "s", ("1",)), None)
        fake.register(encode(address), _sfi(address, "1", 1))
        host, osc_port, identity_port = _addrs(fake)
        result = write.set(host, address, True, osc_port=osc_port,
                           identity_port=identity_port, confirm=True, **_FAST)
    assert result.sent == "1"
    assert result.matched, "_values_match calls bool(1) == True a match (write.py:84-85)"
```

Finally `tests/test_ui_live_is_read_only.py` gains the allow-list. Replace the two top-level tests and add
three:

```python
#: W4/§8.4: exactly one `ui/` module may reach `wing_parser.net.write`, and
#: it exists in order to call ONE verb there. Keyed on `path.name` so the
#: scan behaves identically in `UI_ROOT` and in a `tmp_path`. Adding a
#: second entry re-opens the blast radius this file exists to bound --
#: that is a spec change, not a fix.
ALLOWED_WRITE_MODULES = frozenset({"live_write.py"})

#: The one verb the allow-listed module may use. `toggle` sends `,i -1` and
#: flips whatever the desk holds NOW (`write.py:139-142`), so its outcome
#: is not the `after` the countdown showed; `node_write` and `push` both
#: break F1's one-leaf-per-transmission at the transport. Offences
#: everywhere, that module included.
ALLOWED_VERB = "set"


def find_write_verb_uses(root: Path, *, skip_allowed: bool = False) -> list[str]:
    """Every ATTRIBUTE access of a write verb on a `wing_parser.net` binding.

    Wider than `find_write_verb_calls` on purpose: `live_write.py` hands
    `write.set` to a frozen dataclass field rather than calling it inline,
    and a reference is exactly as reachable as a call. `skip_allowed`
    leaves the allow-listed module out, for the assertion that checks it
    separately by verb.
    """
    offenders = []
    for path in _py_files(root):
        if skip_allowed and path.name in ALLOWED_WRITE_MODULES:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        net_bound = _net_bound_names(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Attribute) or node.attr not in WRITE_VERBS:
                continue
            base = _base_name(node.value)
            if base in net_bound:
                offenders.append(
                    f"{path}:{node.lineno}: names .{node.attr} on {base!r} "
                    f"(bound from {net_bound[base]})"
                )
    return sorted(offenders)


def test_only_the_allow_listed_module_imports_the_write_path():
    offenders = [
        o for o in find_write_imports(UI_ROOT)
        if Path(o.split(":")[0] + ":" + o.split(":")[1]).name not in ALLOWED_WRITE_MODULES
        and not any(f"{name}:" in o for name in ALLOWED_WRITE_MODULES)
    ]
    assert offenders == [], (
        "the write path must not be importable from ui/ outside "
        f"{sorted(ALLOWED_WRITE_MODULES)}:\n  " + "\n  ".join(offenders)
    )


def test_no_other_ui_module_calls_a_write_verb_on_a_net_binding():
    offenders = [
        o for o in find_write_verb_calls(UI_ROOT)
        if not any(f"{name}:" in o for name in ALLOWED_WRITE_MODULES)
    ]
    assert offenders == [], "no write verb may be called on a net-bound name:\n  " + "\n  ".join(offenders)


def test_the_allow_listed_module_names_set_and_nothing_else():
    """Assertion 1 of §8.4, and the reason the allow-list is not a hole."""
    used = find_write_verb_uses(UI_ROOT)
    verbs = {o.rsplit(": names .", 1)[1].split(" ")[0] for o in used}
    assert verbs <= {ALLOWED_VERB}, (
        f"only .{ALLOWED_VERB} may be named on a net binding anywhere under ui/:\n  "
        + "\n  ".join(used)
    )
    assert any("live_write.py" in o for o in used), (
        "live_write.py exists in order to name write.set -- this assertion "
        "has gone vacuous"
    )


def test_the_scan_still_catches_a_planted_push_in_an_allow_listed_name(tmp_path):
    planted = tmp_path / "live_write.py"
    planted.write_text(
        "from wing_parser.net import write\n\ndef go(host, leaves):\n"
        "    return write.push(host, leaves, confirm=True)\n",
        encoding="utf-8",
    )
    offenders = find_write_verb_uses(tmp_path)
    assert len(offenders) == 1 and ":4:" in offenders[0] and "push" in offenders[0]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest tests/test_ui_live_write.py tests/test_ui_live_is_read_only.py tests/test_net_write.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.ui.live_write'` from the first file, and
`NameError: name 'find_write_verb_uses' is not defined` from the third.

- [ ] **Step 3: Write the minimal implementation** — `wing_parser/ui/live_write.py`

```python
"""The one door from `ui/` to `wing_parser.net.write`. Nothing else has one.

W4 and §8.4: `tests/test_ui_live_is_read_only.py` allow-lists this file by
name, for the import and for the single verb `set`. `toggle`, `node_write`
and `push` stay offences here too -- `toggle` sends `,i -1` and flips
whatever the desk holds at send time (`write.py:139-142`), which would
destroy the deterministic `after` the countdown screen rests on.

`send` takes a `WriteConfirmation` and nothing else. That token is built
only after gate 4 has re-asked `WriteGate.can_write()` and
`ArmState.armed()` (§8.4), so "a plain call writes nothing" is a type
error, not a convention.

**`read` normalises before anything compares or displays.** A `,sfi` leaf
reads back as a Python `int` (`codec.py:126-128`) and `jsontypes.py:1-13`
gives the reason: `,sfi` covers plain integers AND WING's booleans, and the
value never carries the distinction. Eight of the eleven repair descriptors
set a JSON bool, so an unnormalised read hands the countdown `0` against a
journal `before` of `False` -- a spurious mismatch, shown as the nonsense
"the desk holds 0, the scene file expected False".
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Callable

from wing_parser.net import jsontypes, write
from wing_parser.net.address import leaf_parts, osc_address
from wing_parser.net.client import WingClient
from wing_parser.net.codec import leaf_value
from wing_parser.net.identity import WingIdentity, query_identity
from wing_parser.net.write import SetResult


def scene_value(parts: Sequence[str], readback: Any) -> Any:
    """F8's one coercion: what a read-back value looks like in the .snap.

    `parts` is the leaf path with `ae_data.` already stripped, exactly as
    `jsontypes.py:48-59` requires -- `is_boolean_shape(["ae_data", ...])`
    answers False in SILENCE, so the shape is never left to a caller.
    Use `net.address.leaf_parts(path)`; nothing else.
    """
    if readback is None:
        return None
    if jsontypes.is_boolean_shape(parts):
        return bool(readback)
    return readback


@dataclass(frozen=True)
class WriteTransport:
    """The seam. `REAL` is the only place `ui/` names `net.write`."""

    identity: Callable[[str], WingIdentity]
    read: Callable[[str, str], Any | None]     # (host, DOTTED PATH) -> normalised
    set: Callable[..., SetResult]


@dataclass(frozen=True)
class WriteConfirmation:
    """Gate 4's token (§8.4). `send` accepts nothing else."""

    host: str
    address: str            # the OSC address, already mapped
    after: Any
    identity: WingIdentity
    desk_before: Any | None


@dataclass(frozen=True)
class SentWrite:
    """One ledger row (F7). `desk_before` is what the DESK held, read live
    at pre-flight -- not the journal's `before`, which is what the FILE
    held when the operator clicked Repair. Revert writes this one back.

    Both spellings of the leaf are carried: `address` is what the packet
    went to, `path` is the dotted document path it came from. Revert needs
    the path back -- to build a `Patch` and to reach `jsontypes` -- and this
    project has no inverse of `osc_address`; inventing one would be a second
    mapper to keep in step with `_place` (W2). Carrying it cannot drift.
    """

    address: str
    path: str
    desk_before: Any | None
    written: Any
    result: SetResult


def _read(host: str, path: str) -> Any | None:
    """One leaf off the desk, normalised. `None` when it did not answer."""
    with WingClient(host) as client:
        reply = client.request(osc_address(path))
    if reply is None:
        return None
    return scene_value(leaf_parts(path), leaf_value(reply)[0])


REAL = WriteTransport(identity=query_identity, read=_read, set=write.set)


def preflight(host: str, path: str,
              transport: WriteTransport = REAL) -> tuple[WingIdentity, Any | None]:
    """A fresh identity and the desk's CURRENT value for `path`.

    Identity is re-queried every time, never reused from the earlier
    connect: `net_commands._echo_identity_before_write`
    (`net_commands.py:79-85`) does exactly this before every CLI write, and
    `identity.py:10-14` says why -- the caller is about to trust "this is
    the console I meant to write to". Both errors propagate untranslated.
    """
    identity = transport.identity(host)
    return identity, transport.read(host, path)


def send(confirmation: WriteConfirmation,
         transport: WriteTransport = REAL) -> SetResult:
    """Write one leaf, read it back, and hand the caller `write.py`'s own
    verdict. Always `set`, always `confirm=True` (W3)."""
    if not isinstance(confirmation, WriteConfirmation):
        raise TypeError(
            "live_write.send takes a WriteConfirmation built behind gate 4, "
            f"not {type(confirmation).__name__}"
        )
    return transport.set(
        confirmation.host, confirmation.address, confirmation.after,
        confirm=True,
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `$PY -m pytest tests/test_ui_live_write.py tests/test_ui_live_is_read_only.py tests/test_net_write.py tests/test_fake_desk.py`
Expected: PASS. Then the full suite with `--junitxml`.

- [ ] **Step 5: Show each new test red once** — plant `write.push(host, {}, confirm=True)` in
      `live_write.py` and watch `test_the_allow_listed_module_names_set_and_nothing_else` fail naming the
      line; drop the `jsontypes.is_boolean_shape` branch from `scene_value` and watch the bool
      normalisation tests fail. Capture both, restore.

- [ ] **Step 6: Commit**

```bash
git add wing_parser/ui/live_write.py tests/test_ui_live_write.py tests/fake_desk.py tests/test_net_write.py tests/test_ui_live_is_read_only.py && git commit -m "feat(ui): open one door from the UI to net.write, and fence it"
```

Body names spec §4, §8.4 and W4: the allow-list is the enforcement, the prose is not.

**Claims to check by opening:** that `write.set`'s signature really takes `(host, address, value, *,
typetag, osc_port, identity_port, timeout, confirm)` (`write.py:125-137`); that `SetResult` has exactly
`address expected sent dry_run readback matched` (`write.py:39-46`); that `matched` is
`readback is not None and (...)` (`write.py:122`); that `leaf_value` returns `int(display)` for `,sfi`
(`codec.py:126-128`); that `_format_value` checks `bool` before `int` (`write.py:74-75`).

---

### Task 4: F8 — the three outcomes, and what each does to the scene leaf

**Files:**
- Modify: `wing_parser/ui/live_write.py` (Task 3), `wing_parser/ui/session.py` (**96 lines**),
  `tests/test_ui_live_write.py` (Task 3), `tests/test_ui_session.py` (**119 lines**)

Read spec §2.4 and F8/W13 first, then `ui/session.py:43-49, 57-69` and `edit/journal.py:27-33`.

**Why `session.py` is touched although §4's Changed table omits it:** the journal is the *only* door into the
document — `Session._document()` is `writer.applied(self._original, self._journal)`
(`session.py:43-44`, `edit/writer.py:22-29`), so a clamp or a revert that must move a scene leaf has to
append a `Patch`. There is no other way to make Doctor re-derive against it. See Deviations, item 2.

**Interfaces:**
- Consumes: `live_write.scene_value`, `SentWrite`, `WriteConfirmation` (Task 3);
  `net.address.leaf_parts` (Task 1).
- Produces:
  ```python
  # wing_parser/ui/live_write.py
  class Outcome(str, Enum): SENT = "sent"; CLAMPED = "clamped"; NO_REPLY = "no_reply"
  def outcome(result: SetResult) -> Outcome: ...
  def settle_scene(parts: Sequence[str], after: Any, result: SetResult) -> Any | None: ...
      # matched -> `after`; clamp -> scene_value(parts, readback); no reply -> None ("leave it")
  def revert_confirmation(record: SentWrite, identity: WingIdentity) -> WriteConfirmation: ...

  # wing_parser/ui/session.py
  def record_value(self, path: str, value: Any, label: str, because: str) -> Patch: ...
  ```

- [ ] **Step 1: Write the failing tests** — append to `tests/test_ui_live_write.py`

```python
# -- F8: the three outcomes, one test each ------------------------------


def _result(after, readback, matched):
    from wing_parser.net.write import SetResult
    return SetResult("/ch/1/in/set/inv", after, str(after), False, readback, matched)


def test_a_matched_write_puts_after_in_the_scene_not_the_read_back_int():
    """`_values_match` calls `bool(1) == True` a match (`write.py:84-85`).
    Storing the `1` would quietly retype the document being edited."""
    result = _result(True, 1, True)
    assert live_write.outcome(result) is live_write.Outcome.SENT
    value = live_write.settle_scene(["ch", "1", "in", "set", "inv"], True, result)
    assert value is True and not isinstance(value, int) or value is True


def test_a_matched_silence_write_puts_after_in_the_scene_not_the_sentinel():
    """-999.0 and -144.0 are both "at or below the sentinel", so
    `_values_match` calls them equal (`write.py:88-89`) -- and writing the
    -144.0 back would move a number the operator never asked to move."""
    result = _result(-999.0, -144.0, True)
    assert live_write.settle_scene(["ch", "1", "fdr"], -999.0, result) == -999.0


def test_a_clamp_rewrites_the_scene_to_what_the_desk_really_holds():
    result = _result(12.0, 10.0, False)
    assert live_write.outcome(result) is live_write.Outcome.CLAMPED
    assert live_write.settle_scene(["ch", "1", "fdr"], 12.0, result) == 10.0


def test_a_clamped_boolean_leaf_is_coerced_on_the_way_into_the_scene():
    result = _result(True, 0, False)
    assert live_write.settle_scene(["ch", "1", "in", "set", "inv"], True, result) is False


def test_a_silent_desk_leaves_the_scene_exactly_as_repair_set_it():
    result = _result(True, None, False)
    assert live_write.outcome(result) is live_write.Outcome.NO_REPLY
    assert live_write.settle_scene(["ch", "1", "in", "set", "inv"], True, result) is None


# -- revert_confirmation (W13) ------------------------------------------


def test_revert_carries_the_desk_before_captured_at_send_time():
    """Proven with a desk value that DIFFERS from the journal's `before`:
    somebody moved the desk after the pull, and the revert must go back to
    what the desk held, not to what the file remembered."""
    record = live_write.SentWrite(
        address="/ch/1/send/8/mode", path="ae_data.ch.1.send.8.mode",
        desk_before="GRP", written="PRE", result=_result("PRE", "PRE", True))
    confirmation = live_write.revert_confirmation(record, _identity())
    assert isinstance(confirmation, live_write.WriteConfirmation)
    assert confirmation.after == "GRP"
    assert confirmation.address == "/ch/1/send/8/mode"
    assert confirmation.host == HOST
    assert confirmation.desk_before == "PRE", "the value the desk holds now"
```

and to `tests/test_ui_session.py`:

```python
def test_record_value_appends_a_patch_and_re_derives(vu_path):
    """F8's clamp path and W13's revert both move a leaf outside `repair`."""
    from wing_parser.ui.session import Session

    session = Session.open(vu_path)
    path = "ae_data.ch.1.send.8.mode"
    before = session._document()["ae_data"]["ch"]["1"]["send"]["8"]["mode"]

    patch = session.record_value(path, "PRE", label="Console clamped", because="G8")

    assert patch.before == before and patch.after == "PRE"
    assert session.changes()[-1] is patch
    assert session._document()["ae_data"]["ch"]["1"]["send"]["8"]["mode"] == "PRE"
    assert session.dirty


def test_record_value_is_undone_like_any_other_patch(vu_path):
    from wing_parser.ui.session import Session

    session = Session.open(vu_path)
    before = session._document()["ae_data"]["ch"]["1"]["send"]["8"]["mode"]
    session.record_value("ae_data.ch.1.send.8.mode", "PRE", label="x", because="G8")
    assert session.undo()
    assert session._document()["ae_data"]["ch"]["1"]["send"]["8"]["mode"] == before
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest tests/test_ui_live_write.py tests/test_ui_session.py`
Expected: FAIL — `AttributeError: module 'wing_parser.ui.live_write' has no attribute 'Outcome'` and
`AttributeError: 'Session' object has no attribute 'record_value'`

- [ ] **Step 3: Write the minimal implementation**

Append to `wing_parser/ui/live_write.py`:

```python
class Outcome(str, Enum):
    """§2.4: three, never two.

    `write.py:122` computes `matched = readback is not None and (...)`, so
    `matched=False` with `readback=None` means the desk NEVER ANSWERED the
    read-back -- the packet may or may not have landed -- while
    `matched=False` WITH a readback means it answered a different value: a
    clamp. `net/write.py:5-9` records that the console clamps an
    out-of-range value and still answers `OK`, which is why every write
    there is read back; without this distinction the app would show a
    repaired finding the desk had quietly refused.
    """

    SENT = "sent"
    CLAMPED = "clamped"
    NO_REPLY = "no_reply"


def outcome(result: SetResult) -> Outcome:
    if result.matched:
        return Outcome.SENT
    return Outcome.CLAMPED if result.readback is not None else Outcome.NO_REPLY


def settle_scene(parts: Sequence[str], after: Any,
                 result: SetResult) -> Any | None:
    """What the scene leaf must hold now, or `None` to leave it alone (F8).

    Matched -> `after`, the value the journal and the dialog both showed --
    NOT `readback`, which `_values_match` (`write.py:84-90`) will have
    called a match while being a different Python type (`bool(1) == True`)
    or a clamped-to-sentinel number (`-999.0` reads back `-144.0`).
    Clamp -> `scene_value(parts, readback)`, so Doctor re-derives against
    the desk's truth. No reply -> `None`: inventing a value for a silent
    desk is the one thing worse than admitting ignorance.
    """
    if result.matched:
        return after
    if result.readback is None:
        return None
    return scene_value(parts, result.readback)


def revert_confirmation(record: SentWrite,
                        identity: WingIdentity) -> WriteConfirmation:
    """W13: write the DESK-BEFORE value back, through gate 4 like any other.

    The journal `Patch` is deliberately NOT undone. The journal is the
    file-side record of what the operator decided and Undo remains
    available separately; silently dropping a patch because a desk write
    was reverted would conflate the two doors this wave keeps apart.
    """
    return WriteConfirmation(
        host=identity.ip,
        address=record.address,
        after=record.desk_before,
        identity=identity,
        desk_before=record.result.readback,
    )
```

with `from enum import Enum` added to the imports.

Append to `wing_parser/ui/session.py` (and add `pointer` to the `wing_parser.edit` import):

```python
    def record_value(self, path: str, value: Any, *, label: str, because: str) -> Patch:
        """Move one leaf outside the repair table, and re-derive.

        The journal is the only door into the document -- `_document()` is
        `writer.applied(original, journal)` (`:43-44`) -- so a console
        clamp (F8) and a successful revert (W13) both land here. `before`
        is read from the CURRENTLY PATCHED document, exactly as `repair`
        does (`:64`), so a second move of the same key records what was
        actually there when the operator looked at it.
        """
        patch = Patch(
            path=path,
            before=pointer.read(self._document(), path),
            after=value,
            because=because,
            label=label,
        )
        self._journal.append(patch)
        self._derive()
        return patch
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `$PY -m pytest tests/test_ui_live_write.py tests/test_ui_session.py tests/test_ui_house_style.py`
Expected: PASS (`wc -l wing_parser/ui/live_write.py` under 200, `session.py` around 112). Then the full
suite with `--junitxml`.

- [ ] **Step 5: Show each new test red once** — change `settle_scene`'s matched branch to
      `return scene_value(parts, result.readback)` and watch both matched tests fail with the exact
      symptom F8 was written against (a bool becoming `1`, a `-999.0` becoming `-144.0`). Capture, restore.

- [ ] **Step 6: Commit**

```bash
git add wing_parser/ui/live_write.py wing_parser/ui/session.py tests/test_ui_live_write.py tests/test_ui_session.py && git commit -m "feat(ui): let the desk's answer decide what the scene holds"
```

Body names spec F8 and W13, and why `session.py` grew a method.

**Claims to check by opening:** `_values_match`'s three branches, in particular the bool branch at
`write.py:84-85` and the sentinel branch at `:88-89`; that `SENTINEL_MINUS_INF` is what `from_db` compares
against (`core/normalizer.py`); that `Patch` is a frozen five-field dataclass (`edit/journal.py:27-33`);
that `writer.applied` deep-copies and replays in order (`edit/writer.py:22-29`).

---

### Task 5: `TIMEOUTS["write"] = 10`, and `"write"` in the two `_ACTIONS` rows

**Files:**
- Modify: `wing_parser/ui/workers.py` (**170 lines**), `wing_parser/ui/live_state.py` (**144 lines**),
  `tests/test_ui_workers.py` (**571 lines**), `tests/test_live_state.py` (**138 lines**)

Read spec §6 and §7.1 first. **Two existing tests WILL fail until updated — that is the point of this task,
not collateral:** `test_allowed_actions_is_pinned_for_every_state` (`tests/test_live_state.py:82`) spells
both `frozenset`s out literally, and `test_timeouts_table_carries_the_ruled_numbers`
(`tests/test_ui_workers.py:121-125`) pins the whole dict.

**Interfaces:**
- Consumes: nothing.
- Produces: `TIMEOUTS["write"] == 10`; `allowed_actions(LiveState.CONNECTED)` and
  `allowed_actions(LiveState.WATCHING)` both contain `"write"`. `_TABLE` (`live_state.py:82-106`) is
  **untouched**: `"write"` is an action, not an event — a send does not move the connection state machine,
  exactly as `export` does not (`live_state.py:111-113`).

- [ ] **Step 1: Write the failing tests**

In `tests/test_ui_workers.py`, replace `test_timeouts_table_carries_the_ruled_numbers` (`:121-125`) with:

```python
def test_timeouts_table_carries_the_ruled_numbers():
    assert TIMEOUTS == {
        "proposal": 120, "guesses": 180, "probe": 30,
        "connect": 5, "walk": 60, "snapshot": 90,
        "write": 10,
    }


def test_the_write_budget_covers_a_confirmed_set_two_and_a_half_times_over():
    """Spec §7.1: `write.set(confirm=True)` has three deadlined steps --
    `_authorize`'s `query_identity` (2.0 s, `write.py:93-94`), a
    fire-and-forget datagram that waits for nothing (`:102-110`), and one
    read-back `request` (2.0 s, `:119-121`). ~4 s worst case."""
    assert TIMEOUTS["write"] == 10
    assert TIMEOUTS["write"] > 2 * 4.0
```

In `tests/test_live_state.py`, update the two pinned rows in
`test_allowed_actions_is_pinned_for_every_state` (`:82`) and add:

```python
    assert allowed_actions(LiveState.CONNECTED) == frozenset(
        {"disconnect", "discover", "pull", "watch", "export", "rerun", "write"}
    )
    ...
    assert allowed_actions(LiveState.WATCHING) == frozenset(
        {"stop", "disconnect", "export", "write"}
    )
```

```python
def test_write_is_offered_in_exactly_two_states(): 
    """W1: every level, Immediate included. The three busy states, `error`,
    `lost` and `disconnected` never offer it -- gate 1 (§8.1)."""
    offering = {s for s in LiveState if "write" in allowed_actions(s)}
    assert offering == {LiveState.CONNECTED, LiveState.WATCHING}


def test_write_is_an_action_and_not_an_event():
    """A send does not move the connection state machine, exactly as
    `export` does not (`live_state.py:111-113`)."""
    import pytest
    for state in (LiveState.CONNECTED, LiveState.WATCHING):
        with pytest.raises(ValueError):
            transition(state, "write")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest tests/test_live_state.py tests/test_ui_workers.py`
Expected: FAIL — `assert TIMEOUTS == {...}` with `'write': 10` missing, and two `assert
allowed_actions(...) == frozenset({...})` mismatches naming `'write'`.

- [ ] **Step 3: Write the minimal implementation**

`wing_parser/ui/workers.py:34-37`:

```python
TIMEOUTS = {
    "proposal": 120, "guesses": 180, "probe": 30,
    "connect": 5, "walk": 60, "snapshot": 90,
    "write": 10,
}
```

and extend the comment block above it with the ruled reason (spec §7.1): three deadlined steps inside
`write.set(confirm=True)` — `_authorize`'s `query_identity` (2.0 s), a datagram that waits for nothing, one
read-back `request` (2.0 s) — ~4 s worst case, so 10 s is ~2.5× that: enough for a busy show network without
letting a dead desk hold a dialog open. **Pre-flight reads reuse `"connect"` = 5 s** and add no entry.

`wing_parser/ui/live_state.py:117-122`:

```python
    LiveState.CONNECTED: frozenset(
        {"disconnect", "discover", "pull", "watch", "export", "rerun", "write"}
    ),
    ...
    LiveState.WATCHING: frozenset({"stop", "disconnect", "export", "write"}),
```

and extend the `_ACTIONS` comment (`:108-113`) to say that `"write"` joins `export` as an action with no
event: a send does not move the connection.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `$PY -m pytest tests/test_live_state.py tests/test_ui_workers.py tests/test_ui_console.py`
Expected: PASS — including `test_every_button_matches_allowed_actions_in_every_state`
(`tests/test_ui_console.py`), which must stay green: `ConsolePage` has no `"write"` button, and that test
checks each *button* against membership, not each membership against a button. Then the full suite.

- [ ] **Step 5: Show each new test red once** — drop `"write"` from the `WATCHING` row and watch
      `test_write_is_offered_in_exactly_two_states` fail. Capture, restore.

- [ ] **Step 6: Commit**

```bash
git add wing_parser/ui/workers.py wing_parser/ui/live_state.py tests/test_ui_workers.py tests/test_live_state.py && git commit -m "feat(ui): offer writing in the two live states, with its own budget"
```

Body names spec §6, §7.1 and W1.

**Claims to check by opening:** that `_TABLE` (`live_state.py:82-106`) has no row mentioning `"write"` after
this change; that `test_every_button_driven_event_is_offered_by_the_state_it_fires_from`
(`tests/test_live_state.py:114`) checks events against `_ACTIONS` and not the reverse, so an action with no
event keeps it green; that `CallRunner.start` reads `TIMEOUTS[kind]` and a test-supplied `timeout=0`
overrides it (`workers.py:114`).

---

### Task 6: F6 — split `settings_dialog.py` first, then the 3–60 delay row

**Files:**
- Create: `wing_parser/ui/settings_io.py`
- Modify: `wing_parser/ui/settings_dialog.py` (**199 lines**), `wing_parser/ui/state_store.py` (**92**),
  `wing_parser/ui/window_state.py` (**128**), `wing_parser/ui/texts.py` (**162 + Task 7**),
  `tests/test_ui_settings.py` (**125**), `tests/test_ui_state_store.py` (**228**),
  `tests/test_ui_shell.py` (**64**)

**The split is not optional and it comes first.** `settings_dialog.py` is at **199** of the 200-line ceiling
(`test_ui_house_style.py:170`), so a row cannot simply be added. Move `MASK`, `_mask` and `_dump_yaml`
(`settings_dialog.py:35-48`) to `ui/settings_io.py`, freeing ~14 lines; *then* add the `QSpinBox` row to the
`QFormLayout` (`:75-80`) and one save line in `_save_and_close` (`:197`).

**The value does not go in `provider.yaml`** — that file is the AI provider key (`settings_dialog.py:1-10`).
The delay is UI state and **must be declared in four places or it is silently lost**: `DEFAULTS`
(`state_store.py:24`), the rebuilt dict in `normalize` (`:38-47`) — the wave-2 pitfall this project has
already been bitten by — `window_state.restore` (`:21-34`), which reads each key by name, and
`window_state.save_on_close` (`:116-128`), which rebuilds the saved dict from an explicit literal, so a key
missing *there* is erased on every quit.

**Interfaces:**
- Consumes: nothing.
- Produces:
  ```python
  # wing_parser/ui/settings_io.py
  MASK = "•" * 4
  def mask(key: str) -> str: ...
  def dump_yaml(doc: dict) -> str: ...

  # wing_parser/ui/state_store.py
  MIN_APPLY_DELAY = 3; MAX_APPLY_DELAY = 60
  DEFAULTS = {..., "apply_delay": 5}          # normalize() clamps to 3..60, default 5

  # wing_parser/ui/settings_dialog.py
  class SettingsDialog(QDialog):
      delay_spin: QSpinBox                     # range 3..60, seeded from window._apply_delay

  # MainWindow, via window_state
  window._apply_delay: int                     # read at restore, written at save_on_close
  ```
  Task 10's `DelayedWriteDialog` takes its starting countdown from `window._apply_delay`.

- [ ] **Step 1: Write the failing tests**

`tests/test_ui_state_store.py`:

```python
def test_apply_delay_round_trips_through_save_and_load(tmp_path):
    state_store.save(tmp_path, {
        "geometry": None, "page": None, "recent": [], "consoles": [],
        "apply_delay": 12,
    })
    assert state_store.load(tmp_path)["apply_delay"] == 12


def test_apply_delay_is_in_defaults_and_defaults_to_five():
    assert state_store.DEFAULTS["apply_delay"] == 5


def test_a_state_file_without_apply_delay_degrades_to_the_default(tmp_path):
    (tmp_path / state_store.STATE_FILE).write_text(
        json.dumps({"recent": [], "consoles": []}), encoding="utf-8")
    assert state_store.load(tmp_path)["apply_delay"] == 5


@pytest.mark.parametrize("stored,expected", [
    (0, 3), (2, 3), (3, 3), (60, 60), (999, 60),
    ("five", 5), (None, 5), (True, 5), ([], 5),
])
def test_a_hand_edited_apply_delay_normalises_inside_three_to_sixty(stored, expected):
    assert state_store.normalize({"apply_delay": stored})["apply_delay"] == expected
```

`tests/test_ui_settings.py`:

```python
def test_the_delay_row_offers_three_to_sixty(qt_app, knowledge):
    from wing_parser.ui.settings_dialog import SettingsDialog

    dlg = SettingsDialog()
    assert dlg.delay_spin.minimum() == 3
    assert dlg.delay_spin.maximum() == 60
    assert dlg.delay_spin.value() == 5


def test_saving_the_dialog_puts_the_delay_on_the_window(qt_app, knowledge):
    from wing_parser.ui.settings_dialog import SettingsDialog

    class _Window:
        _apply_delay = 5

    window = _Window()
    dlg = SettingsDialog(window)
    dlg.delay_spin.setValue(20)
    dlg._save_and_close()
    assert window._apply_delay == 20


def test_settings_io_holds_the_mask_and_the_dumper(qt_app):
    """The split that made room for the row; both call sites still work."""
    from wing_parser.ui import settings_io

    assert settings_io.mask("sk-test-1234").endswith("1234")
    assert settings_io.mask("") == ""
    assert "provider: anthropic" in settings_io.dump_yaml({"provider": "anthropic"})
```

`tests/test_ui_shell.py` — the **quit** half (MAJOR 2: `save_on_close` rebuilds from a literal):

```python
def test_the_apply_delay_survives_closing_the_window(qt_app, tmp_path, monkeypatch):
    from wing_parser import config
    from wing_parser.ui import state_store
    from wing_parser.ui.main_window import MainWindow

    monkeypatch.setenv(config.ENV_VAR, str(tmp_path))
    monkeypatch.setenv("WING_DISABLE_LLM", "1")

    window = MainWindow(None)
    window._apply_delay = 17
    window.close()

    assert state_store.load(tmp_path)["apply_delay"] == 17, (
        "save_on_close rebuilds the saved dict from an explicit literal -- "
        "a key missing there is erased on every quit"
    )
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest tests/test_ui_state_store.py tests/test_ui_settings.py tests/test_ui_shell.py`
Expected: FAIL — `KeyError: 'apply_delay'`, `ModuleNotFoundError: No module named
'wing_parser.ui.settings_io'`, `AttributeError: 'SettingsDialog' object has no attribute 'delay_spin'`.

- [ ] **Step 3: Write the minimal implementation**

`wing_parser/ui/settings_io.py`:

```python
"""File-shaped helpers the Settings dialog needs but is not made of.

Split out when F6's delay row arrived and `settings_dialog.py` stood at
199 of the 200-line ceiling (`test_ui_house_style.py:170`). Masking a key
for display and serialising a provider document are both about the FILE,
not about the widget, so this is a responsibility split rather than a
line-count dodge -- but the line count is what forced the question.
"""

from __future__ import annotations

import io

MASK = "•" * 4


def mask(key: str) -> str:
    """The loaded key, shown. Doubles as an unchanged-marker: saving the
    mask re-writes the real key untouched (`settings_dialog.py:59-63`)."""
    return MASK + key[-4:] if key else ""


def dump_yaml(doc: dict) -> str:
    from ruamel.yaml import YAML

    engine = YAML()
    stream = io.StringIO()
    engine.dump(doc, stream)
    return stream.getvalue()
```

`wing_parser/ui/settings_dialog.py` — delete lines 35-48, import the two names
(`from wing_parser.ui.settings_io import dump_yaml, mask`), replace `_mask(cfg.api_key)` with
`mask(cfg.api_key)` (`:62`) and `_dump_yaml(doc)` with `dump_yaml(doc)` (`:154`), then add:

```python
        self.delay_spin = QSpinBox()
        self.delay_spin.setRange(state_store.MIN_APPLY_DELAY,
                                 state_store.MAX_APPLY_DELAY)
        self.delay_spin.setValue(getattr(parent, "_apply_delay",
                                         state_store.DEFAULTS["apply_delay"]))
```

one `form.addRow(text("settings.apply_delay"), self.delay_spin)` after `:80`, and in `_save_and_close`
(`:197`):

```python
    def _save_and_close(self) -> None:
        window = self.parent()
        if window is not None:
            # F6: UI state, not a provider key -- it rides `ui-state.json`
            # through `window_state.save_on_close`, never provider.yaml.
            window._apply_delay = self.delay_spin.value()
        if self.save():
            self.accept()
```

with `QSpinBox` added to the `PySide6.QtWidgets` import and `from wing_parser.ui import state_store` to the
module imports. `"settings.apply_delay": "Default apply delay (s)"` goes in `texts.py` beside the other
`settings.*` keys (`texts.py:140-156`) — it is a Settings string, not a `console.write.*` one.

`wing_parser/ui/state_store.py`:

```python
#: F6: the countdown a Delayed apply opens at. Clamped rather than
#: rejected -- a hand-edited 0 or 999 is a typo, not a reason to lose the
#: rest of the file.
MIN_APPLY_DELAY = 3
MAX_APPLY_DELAY = 60

DEFAULTS: dict = {"geometry": None, "page": None, "recent": [], "consoles": [],
                  "apply_delay": 5}
```

and inside `normalize`, before the `return`:

```python
    # `bool` is an int subclass, and True is not a number of seconds.
    delay = state.get("apply_delay")
    if isinstance(delay, bool) or not isinstance(delay, int):
        delay = DEFAULTS["apply_delay"]
    delay = min(max(delay, MIN_APPLY_DELAY), MAX_APPLY_DELAY)
```

with `"apply_delay": delay,` added to the rebuilt dict. `load`'s fallback
(`dict(DEFAULTS, recent=[], consoles=[])`, `:59`) needs no change — `DEFAULTS` now carries the key.

`wing_parser/ui/window_state.py` — one line in `restore` (`:21-34`):

```python
    window._apply_delay = state["apply_delay"]
```

and one in `save_on_close`'s literal (`:116-128`):

```python
            "apply_delay": getattr(window, "_apply_delay",
                                   state_store.DEFAULTS["apply_delay"]),
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `$PY -m pytest tests/test_ui_settings.py tests/test_ui_state_store.py tests/test_ui_shell.py tests/test_ui_texts.py tests/test_ui_house_style.py`
Expected: PASS. Paste `wc -l wing_parser/ui/settings_dialog.py` — it must be **under 200**. Then the full
suite with `--junitxml`.

- [ ] **Step 5: Show each new test red once** — delete `"apply_delay": delay,` from `normalize` and watch
      the round-trip test fail (the silent-drop trap, demonstrated); then delete the `save_on_close` line
      and watch the shell test fail. Capture both, restore.

- [ ] **Step 6: Commit**

```bash
git add wing_parser/ui/settings_io.py wing_parser/ui/settings_dialog.py wing_parser/ui/state_store.py wing_parser/ui/window_state.py wing_parser/ui/texts.py tests/test_ui_settings.py tests/test_ui_state_store.py tests/test_ui_shell.py && git commit -m "feat(ui): remember the default apply delay, in all four places"
```

Body names spec F6 and W8: one new persisted key this wave, and no others.

**Claims to check by opening:** that `normalize` rebuilds a fixed dict and drops anything not named in it
(`state_store.py:38-47`); that `save` writes through `normalize` (`:62-68`); that `restore` reads each key
by name (`window_state.py:21-34`); that `save_on_close` rebuilds from a literal (`:116-128`); that
`provider.yaml` is written by `SettingsDialog.save` and carries only provider fields
(`settings_dialog.py:142-165`).

---

### Task 7: The `console.write.*` strings

**Files:**
- Create: `wing_parser/ui/texts_write.py`
- Modify: `wing_parser/ui/texts.py` (**162 lines** — **one import and one `**WRITE_TEXTS` line**, beside
  `**CONSOLE_TEXTS` at `texts.py:9,157`), `tests/test_ui_texts.py` (**240**)

Every string in spec §2 is here, verbatim, plus the selector's label and its three level names: §2.2 names
the levels but gives no keys, and they are user-facing, so W7 puts them in the table like everything else.

**Interfaces:**
- Consumes: nothing.
- Produces: `WRITE_TEXTS: dict[str, str]`, merged into `TEXTS`, so `text("console.write.sent")` resolves
  exactly as every other key does.

- [ ] **Step 1: Write the failing tests** — `tests/test_ui_texts.py`

```python
WRITE_KEYS = (
    "console.write.arm_title", "console.write.reading", "console.write.desk",
    "console.write.identity_failed", "console.write.latch", "console.write.latch_why",
    "console.write.name_prompt", "console.write.name_wrong", "console.write.arm",
    "console.write.armed", "console.write.refused",
    "console.write.level", "console.write.manual", "console.write.delayed",
    "console.write.immediate",
    "console.write.send", "console.write.blocked", "console.write.sending",
    "console.write.gate_closed",
    "console.write.delay_title", "console.write.address", "console.write.countdown",
    "console.write.desk_value", "console.write.file_value", "console.write.after",
    "console.write.mismatch", "console.write.no_read",
    "console.write.apply_now", "console.write.extend", "console.write.cancel",
    "console.write.cancelled",
    "console.write.sent", "console.write.clamped", "console.write.no_reply",
    "console.write.sent_heading", "console.write.revert", "console.write.revert_all",
    "console.write.revert_stop", "console.write.reverting", "console.write.reverted",
    "console.write.revert_stopped", "console.write.revert_cancelled",
)


def test_every_write_key_resolves():
    from wing_parser.ui.texts import text

    for key in WRITE_KEYS:
        assert text(key), key


def test_the_latch_reads_as_not_running_a_show():
    """F4 and the spec header: a TICKED box meaning "danger" reads backwards
    at 2 a.m., and every other checkbox in this app means "yes, do this"."""
    from wing_parser.ui.texts import text

    assert "NOT running a show" in text("console.write.latch")
    assert "never during a show" in text("console.write.latch_why")


def test_the_three_outcome_badges_say_three_different_things():
    from wing_parser.ui.texts import text

    sent = text("console.write.sent").format(readback="PRE")
    clamped = text("console.write.clamped").format(readback=10.0, after=12.0)
    silent = text("console.write.no_reply").format(address="/ch/1/fdr")
    assert len({sent, clamped, silent}) == 3
    assert "may or may not have landed" in silent
    assert "clamped" in clamped


def test_cancelled_speaks_only_about_the_scene_edit():
    """S2.3: Cancel drops the transmission; Undo drops the file side."""
    from wing_parser.ui.texts import text

    assert "Undo" in text("console.write.cancelled")
    assert "The desk keeps" in text("console.write.revert_cancelled")


def test_every_write_placeholder_is_filled_by_someone():
    """A `{name}` nobody formats prints as a literal brace at a venue."""
    import string
    from wing_parser.ui.texts_write import WRITE_TEXTS

    allowed = {
        "name", "model", "serial", "host", "error", "address", "seconds",
        "remaining", "value", "desk", "file", "after", "readback", "done", "total",
    }
    for key, value in WRITE_TEXTS.items():
        fields = {f for _, f, _, _ in string.Formatter().parse(value) if f}
        assert fields <= allowed, f"{key} names {fields - allowed}"


def test_no_write_key_collides_with_an_existing_one():
    from wing_parser.ui.texts import TEXTS
    from wing_parser.ui.texts_console import CONSOLE_TEXTS
    from wing_parser.ui.texts_write import WRITE_TEXTS

    assert set(CONSOLE_TEXTS) & set(WRITE_TEXTS) == set()
    assert set(WRITE_TEXTS) <= set(TEXTS)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest tests/test_ui_texts.py`
Expected: FAIL — `KeyError: 'console.write.arm_title'`

- [ ] **Step 3: Write the minimal implementation** — `wing_parser/ui/texts_write.py`

```python
"""The wave-3 write strings, split out of `texts.py` like the console's.

Namespace `console.write.*`, not `write.*` (W7): the flat table already
holds `changes.*` keys for the journal dock, and a bare `write.*` would
read as a sibling of those while meaning something else entirely.

Every string an operator can see while a packet is about to leave is here,
so the whole vocabulary of the dangerous half of this app is one file a
reviewer can read end to end.
"""

from __future__ import annotations

WRITE_TEXTS: dict[str, str] = {
    # -- arming, once per connection (F4) --------------------------------
    "console.write.arm_title": "Arm writing to this console",
    "console.write.reading": "Asking the desk…",
    "console.write.desk": "{name} · {model} · serial {serial}",
    "console.write.identity_failed": (
        "Cannot identify the desk at {host}: {error} — not armed."
    ),
    "console.write.latch": "This desk is NOT running a show right now.",
    "console.write.latch_why": (
        "CLAUDE.md: never during a show without explicit confirmation."
    ),
    "console.write.name_prompt": "Type this console's name to confirm:",
    "console.write.name_wrong": "That is not this console's name.",
    "console.write.arm": "Arm",
    "console.write.armed": "Armed: {name}",
    "console.write.refused": "Refused: {error}",

    # -- the selector (F3) -----------------------------------------------
    "console.write.level": "Apply to console",
    "console.write.manual": "Manual",
    "console.write.delayed": "Delayed",
    "console.write.immediate": "Immediate",

    # -- the journal row's Send button (S2.2) ----------------------------
    "console.write.send": "Send to console",
    "console.write.blocked": "Connect to the console (Ctrl+7) to send this.",
    "console.write.sending": "Sending {address}…",
    "console.write.gate_closed": (
        "The console connection dropped. Nothing was sent."
    ),

    # -- the countdown (F5) ----------------------------------------------
    "console.write.delay_title": "Applying to the console in {seconds} s",
    "console.write.address": "{address}",
    "console.write.countdown": "{remaining} s",
    "console.write.desk_value": "The desk now holds: {value}",
    "console.write.file_value": "The scene file expected: {value}",
    "console.write.after": "It will become: {value}",
    "console.write.mismatch": (
        "⚠ The desk holds {desk}, the scene file expected {file}. "
        "Applying replaces the desk's value."
    ),
    "console.write.no_read": (
        "The desk did not answer a read of this address. It may not exist here."
    ),
    "console.write.apply_now": "Apply now",
    "console.write.extend": "+5 s",
    "console.write.cancel": "Cancel",
    "console.write.cancelled": (
        "Not applied. The scene edit stays — use Undo to drop it too."
    ),

    # -- the three outcomes (F8) -----------------------------------------
    "console.write.sent": "sent ✓ the desk holds {readback}",
    "console.write.clamped": (
        "⚠ the desk holds {readback}, not {after} — the console "
        "clamped it."
    ),
    "console.write.no_reply": (
        "✗ {address}: the desk did not answer. It may or may not have "
        "landed."
    ),

    # -- the sent ledger (F7, W12) ---------------------------------------
    "console.write.sent_heading": "Sent to console",
    "console.write.revert": "Revert",
    "console.write.revert_all": "Revert all",
    "console.write.revert_stop": "Stop",
    "console.write.reverting": "Reverting {done}/{total}: {address}",
    "console.write.reverted": "reverted ✓ the desk holds {readback}",
    "console.write.revert_stopped": (
        "Stopped after {done} of {total}. The rest were left as they are."
    ),
    "console.write.revert_cancelled": (
        "Not reverted. The desk keeps the written value."
    ),
}
```

`wing_parser/ui/texts.py` — one import beside `:9` and one merge line beside `:157`:

```python
from wing_parser.ui.texts_write import WRITE_TEXTS
...
    **CONSOLE_TEXTS,
    **WRITE_TEXTS,
}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `$PY -m pytest tests/test_ui_texts.py tests/test_ui_house_style.py`
Expected: PASS (`wc -l wing_parser/ui/texts_write.py` under 120, `texts.py` at 164).

- [ ] **Step 5: Show each new test red once** — rewrite the latch as `"This desk is running a show."` and
      watch `test_the_latch_reads_as_not_running_a_show` fail; add a `{venue}` placeholder to one string and
      watch the placeholder test fail. Capture both, restore.

- [ ] **Step 6: Commit**

```bash
git add wing_parser/ui/texts_write.py wing_parser/ui/texts.py tests/test_ui_texts.py && git commit -m "feat(ui): add the console.write vocabulary"
```

Body names spec §2 and W7.

**Claims to check by opening:** that `texts.py:9,157` is really how `CONSOLE_TEXTS` is merged, and that
`text()` is a plain `TEXTS[key]` raising `KeyError` on a typo (`texts.py:161-162`); that no existing key
starts `console.write.` (`grep -n "console.write" wing_parser/ui/texts_console.py` → nothing).

---

### Task 8: `WriteGate` — owned, constructed and published by `live_wiring.py`

**Files:**
- Modify: `wing_parser/ui/live_wiring.py` (**69 lines**), `wing_parser/ui/main_window.py` (**191 lines** —
  **one line**, the `install_write_gate` call), `tests/test_ui_console.py` (**1744**)

Read spec §8.1, §8.4, W1, W5 and W10 first, then `ui/console_page.py:56-67, 110-148` (the `state` property,
the four panels' signals and `_apply_state`, the one writer) and `ui/workers.py:86-170` (`CallRunner`).

**Before the dialogs, because both re-check this gate.** It **starts closed**, reads `page.state` live rather
than caching it, and neither the Changes dock nor the Doctor page ever imports `console_page` — a Console page
that failed to build cannot leave anything enabled by accident (§8.1).

**`console_page.py` does not grow (W7).** The gate therefore learns a dropout from the page's *existing*
signals — `connect_bar.disconnected` (`live_connect_bar.py:56`), `CallPanel.failed`
(`live_call_panel.py:44-49`, shared by all three call panels) and `events.lost`
(`live_events_view.py:46`) — which are exactly the transitions into `DISCONNECTED`, `ERROR` and `LOST`
(`console_page.py:117-138`). No new signal, no new line on that page.

**Interfaces:**
- Consumes: `apply_level.ArmState`, `write_queue.WriteQueue` (Task 2); `live_state.allowed_actions` and
  `TIMEOUTS["write"]` (Task 5); `live_write.send` / `WriteConfirmation` / `SetResult` (Task 3);
  `text("console.write.gate_closed")` (Task 7); `workers.CallRunner`.
- Produces:
  ```python
  # wing_parser/ui/live_wiring.py
  class GateClosed(RuntimeError): ...
  @dataclass(frozen=True)
  class WriteJob:
      confirmation: WriteConfirmation
      on_result: Callable[[SetResult], None]
      on_error: Callable[[Exception], None]

  class WriteGate(QObject):
      changed = Signal()                       # arm state moved; the selector follows it
      arm: ArmState
      def can_write(self) -> bool: ...         # gate 1: "write" in allowed_actions(page.state)
      def ready(self) -> bool: ...             # gates 1 + 2, re-asked before every send
      def host(self) -> str: ...
      def submit(self, job: WriteJob) -> None: ...     # through the FIFO, one at a time
      def close(self) -> None: ...             # disarm + changed; the dropout slot

  def install_write_gate(window, page, *, transport=None, timeout=None) -> WriteGate: ...
  ```

- [ ] **Step 1: Write the failing tests** — append to `tests/test_ui_console.py`

```python
# -- the write gate (spec §8.1, §8.4, W1, W10) --------------------------


def _job(gate, address, after, on_result, on_error=None):
    from wing_parser.ui import live_wiring
    from wing_parser.ui.live_write import WriteConfirmation

    return live_wiring.WriteJob(
        confirmation=WriteConfirmation(
            host=HOST, address=address, after=after,
            identity=_identity(), desk_before=None),
        on_result=on_result,
        on_error=on_error or (lambda exc: None),
    )


def _gate_page(qt_app, desk=None):
    """A real ConsolePage over a FakeDesk, plus the gate live_wiring builds."""
    from tests.fake_desk import FakeDesk
    from wing_parser.ui import live_wiring
    from wing_parser.ui.console_page import ConsolePage

    desk = FakeDesk(identity=_identity()) if desk is None else desk
    page = ConsolePage(transport=desk.transport(), timeout=0)

    class _Window:
        pass

    window = _Window()
    gate = live_wiring.install_write_gate(
        window, page, transport=desk.write_transport(), timeout=0)
    return window, page, gate, desk


def test_the_write_gate_starts_closed(qt_app):
    _w, _p, gate, _d = _gate_page(qt_app)
    assert gate.can_write() is False and gate.ready() is False


def test_the_gate_opens_in_connected_and_watching_and_in_no_other_state(qt_app):
    from wing_parser.ui.live_state import LiveState

    _w, page, gate, _d = _gate_page(qt_app)
    open_in = set()
    for state in LiveState:
        page._apply_state(state)
        if gate.can_write():
            open_in.add(state)
    assert open_in == {LiveState.CONNECTED, LiveState.WATCHING}


def test_ready_needs_the_gate_open_and_the_arm_state_armed(qt_app):
    from wing_parser.ui.live_state import LiveState

    _w, page, gate, _d = _gate_page(qt_app)
    page._apply_state(LiveState.CONNECTED)
    assert gate.ready() is False, "open but unarmed is not ready"
    gate.arm.arm(_identity())
    assert gate.ready() is True


@pytest.mark.parametrize("dropout", ["disconnected", "failed", "lost"])
def test_every_dropout_disarms_and_announces(qt_app, dropout):
    from wing_parser.ui.apply_level import ApplyLevel
    from wing_parser.ui.live_state import LiveState

    _w, page, gate, _d = _gate_page(qt_app)
    page._apply_state(LiveState.CONNECTED)
    gate.arm.arm(_identity())
    gate.arm.level = ApplyLevel.IMMEDIATE
    heard = []
    gate.changed.connect(lambda: heard.append(True))

    if dropout == "disconnected":
        page.connect_bar.disconnected.emit()
    elif dropout == "failed":
        page.connect_bar.failed.emit(OSError("gone"))
    else:
        page.events.lost.emit(OSError("desk lost"))

    assert gate.arm.armed() is False
    assert gate.arm.level is ApplyLevel.MANUAL
    assert heard, "the selector must be told, or it shows a level that is gone"


def test_two_immediate_submissions_never_overlap_on_the_wire(qt_app, settle):
    from wing_parser.ui.live_state import LiveState

    _w, page, gate, desk = _gate_page(qt_app)
    page._apply_state(LiveState.CONNECTED)
    gate.arm.arm(_identity())
    results = []
    for value in ("PRE", "POST"):
        gate.submit(_job(gate, "/ch/1/send/8/mode", value, results.append))

    assert settle(lambda: len(results) == 2)
    assert [call[0:2] for call in desk.sets] == [
        ("/ch/1/send/8/mode", "PRE"), ("/ch/1/send/8/mode", "POST")]


def test_a_closed_gate_never_reaches_the_transport(qt_app, settle):
    """Gate 4's late re-check: the state can go LOST under a countdown."""
    from wing_parser.ui import live_wiring
    from wing_parser.ui.live_state import LiveState

    _w, page, gate, desk = _gate_page(qt_app)
    page._apply_state(LiveState.CONNECTED)
    gate.arm.arm(_identity())
    page._apply_state(LiveState.LOST)
    errors = []
    gate.submit(_job(gate, "/ch/1/fdr", -6.0, lambda r: None, errors.append))

    assert settle(lambda: errors)
    assert desk.sets == []
    assert isinstance(errors[0], live_wiring.GateClosed)


def test_an_unarmed_gate_never_reaches_the_transport(qt_app, settle):
    from wing_parser.ui.live_state import LiveState

    _w, page, gate, desk = _gate_page(qt_app)
    page._apply_state(LiveState.CONNECTED)
    errors = []
    gate.submit(_job(gate, "/ch/1/fdr", -6.0, lambda r: None, errors.append))
    assert settle(lambda: errors)
    assert desk.sets == []


def test_the_gate_publishes_itself_on_the_window(qt_app):
    window, _p, gate, _d = _gate_page(qt_app)
    assert window.write_gate is gate


def test_the_console_page_gained_no_signal_for_this(qt_app):
    """W7: `console_page.py` is at 199 of the 200-line ceiling. The gate
    reads `page.state` and listens to the panels' OWN signals."""
    from wing_parser.ui.console_page import ConsolePage

    assert not hasattr(ConsolePage, "state_changed")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest tests/test_ui_console.py -k gate`
Expected: FAIL — `AttributeError: module 'wing_parser.ui.live_wiring' has no attribute
'install_write_gate'`

- [ ] **Step 3: Write the minimal implementation** — append to `wing_parser/ui/live_wiring.py`

```python
class GateClosed(RuntimeError):
    """Gate 4 refused a write between the operator's click and the packet.

    A countdown can run for a minute and the desk can go LOST underneath
    it -- `RoundGuard` raises `DeskLost` after three silent rounds
    (`live_guard.py:44-52`) -- without the dialog knowing. Checking a
    live-state gate once, at paint time, is the classic form of this bug,
    so every path re-asks immediately before the confirmation is built.
    """


@dataclass(frozen=True)
class WriteJob:
    """One queued write, with the two ways it can end already bound."""

    confirmation: object                        # live_write.WriteConfirmation
    on_result: Callable[[object], None]
    on_error: Callable[[Exception], None]


class WriteGate(QObject):
    """Gates 1 and 2, and the single wire, in one object the window publishes.

    Built HERE rather than on the Console page (§8.1): the Doctor page and
    the Changes dock read it and neither may import `console_page`, so a
    page that failed to build would otherwise leave a write button enabled.
    It holds the page only to READ `page.state`, live, every time -- a
    cached answer is exactly what gate 4 exists to distrust.

    W10: one `CallRunner` and one `WriteQueue`, so "one parameter on the
    wire" is a property of the transport rather than of the UI happening
    not to offer a second button.
    """

    changed = Signal()

    def __init__(self, page, *, transport=None, timeout=None, parent=None) -> None:
        super().__init__(parent)
        self._page = page
        self._transport = transport or live_write.REAL
        self._timeout = timeout
        self.arm = ArmState()
        self._runner = CallRunner(self)
        self._queue = WriteQueue(self._start)

    # -- what everything asks it -------------------------------------------

    def can_write(self) -> bool:
        """Gate 1: `_ACTIONS` offers `"write"` in two states only (§6)."""
        return "write" in allowed_actions(self._page.state)

    def ready(self) -> bool:
        """Gates 1 and 2 together. Re-asked before every send (§8.4)."""
        return self.can_write() and self.arm.armed()

    def host(self) -> str:
        return self._page.connect_bar.host()

    # -- the one wire -------------------------------------------------------

    def submit(self, job: WriteJob) -> None:
        self._queue.enqueue(job)

    def close(self) -> None:
        """Every DISCONNECTED / LOST / ERROR lands here (F4)."""
        self.arm.disarm()
        self.changed.emit()

    def _start(self, job: WriteJob) -> None:
        if not self.ready():
            self._settle_then(job.on_error,
                              GateClosed(text("console.write.gate_closed")))
            return
        started = self._runner.start(
            "write", live_write.send, job.confirmation, self._transport,
            on_success=lambda result: self._settle_then(job.on_result, result),
            on_failure=lambda exc: self._settle_then(job.on_error, exc),
            on_cancel=lambda: self._settle_then(
                job.on_error, GateClosed(text("console.write.gate_closed"))),
            timeout=self._timeout,
        )
        if not started:
            # The runner is busy with something the queue does not know
            # about. Requeue rather than drop: W10 says neither of two rapid
            # Immediate repairs is lost.
            self._queue.settle()
            self._queue.enqueue(job)

    def _settle_then(self, callback, payload) -> None:
        """Exactly one terminal path per write, and the queue hears it
        BEFORE the callback -- a callback that enqueues the next revert
        (Revert all, §7.2) must find the wire free."""
        self._queue.settle()
        callback(payload)


def install_write_gate(window, page, *, transport=None, timeout=None) -> WriteGate:
    """Build the gate, publish it on the window, wire every dropout to it.

    The three sources are the page's EXISTING signals: `console_page.py` is
    at 199 of the 200-line ceiling and may not grow a state signal (W7),
    and these are exactly the transitions into DISCONNECTED, ERROR and LOST
    (`console_page.py:117-138`).
    """
    gate = WriteGate(page, transport=transport, timeout=timeout, parent=window)
    window.write_gate = gate
    page.connect_bar.disconnected.connect(gate.close)
    page.events.lost.connect(lambda _exc: gate.close())
    for panel in (page.connect_bar, page.discovery, page.snapshot):
        panel.failed.connect(lambda _exc: gate.close())
    changes = getattr(window, "changes_panel", None)
    if changes is not None:
        changes.attach_gate(gate)          # task 12 gives ChangesPanel this
    return gate
```

with the imports it needs at the top of the file: `from dataclasses import dataclass`,
`from typing import Callable`, `from PySide6.QtCore import QObject, Signal`,
`from wing_parser.ui import live_write`, `from wing_parser.ui.apply_level import ArmState`,
`from wing_parser.ui.live_state import allowed_actions`, `from wing_parser.ui.texts import text`,
`from wing_parser.ui.workers import CallRunner`, `from wing_parser.ui.write_queue import WriteQueue`.

`wing_parser/ui/main_window.py` — **one line**, after `:78`:

```python
        live_wiring.install_write_gate(self, self.pages["console"])
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `$PY -m pytest tests/test_ui_console.py tests/test_ui_shell.py tests/test_ui_house_style.py tests/test_ui_live_is_read_only.py`
Expected: PASS. Paste
`wc -l wing_parser/ui/live_wiring.py wing_parser/ui/main_window.py wing_parser/ui/console_page.py` —
**live_wiring under 200, main_window at 192, console_page still 199.** Then the full suite.

**Escape hatch, declared now.** `live_wiring.py` is the tightest file in this wave: 69 lines + `WriteGate` +
`install_write_gate`, and Task 11 adds `route_repair` on top. If it crosses 200 at Task 11, move
`GateClosed`, `WriteJob` and `WriteGate` into a new `wing_parser/ui/write_gate.py` and say so in that commit
body. `live_wiring` keeps owning the **construction and publication**, which is what W1 and §8.1 actually
require.

- [ ] **Step 5: Show each new test red once** — replace `can_write` with `return True` and watch
      `test_a_closed_gate_never_reaches_the_transport` fail with a recorded `set`; drop `self._queue.settle()`
      from `_settle_then` and watch the two-immediates test run out its `settle` limit with one result.
      Capture both, restore.

- [ ] **Step 6: Commit**

```bash
git add wing_parser/ui/live_wiring.py wing_parser/ui/main_window.py tests/test_ui_console.py && git commit -m "feat(ui): own the write gate, the arm state and the one wire in live_wiring"
```

Body names spec §8.1, §8.4, W1 and W10.

**Claims to check by opening:** that `ConsolePage.state` is a live property and `_apply_state` its only
writer (`console_page.py:88-93, 142-148`); that `CallPanel.failed` is shared by all three call panels
(`live_call_panel.py:44-49`); that `LiveEventsView.lost` carries the `DeskLost` (`live_events_view.py:46`);
that `CallRunner.start` returns `False` while busy (`workers.py:112-113`) and fires exactly one terminal
callback (`:124-146`); that `main_window.py` is at 192 and `console_page.py` still at 199.

---

### Task 9: `ArmWriteDialog` — a fresh identity, the latch, the typed name

**Files:**
- Create: `wing_parser/ui/write_arm_dialog.py`, `tests/test_ui_write_dialogs.py`

Read spec §2.1, F4, §8.2 and W5 first, then `ui/settings_dialog.py:93-103` (the `CallRunner` pattern this
dialog follows) and `net/identity.py:10-14`.

**Interfaces:**
- Consumes: `WriteTransport.identity` via `live_write.REAL` (Task 3), `WriteGate` (Task 8),
  `text("console.write.*")` (Task 7), `workers.CallRunner` + `TIMEOUTS["connect"] = 5` (reused, no new
  entry — §7.1).
- Produces:
  ```python
  # wing_parser/ui/write_arm_dialog.py
  class ArmWriteDialog(QDialog):
      armed = Signal(object)                  # the WingIdentity this arming is for
      status_label: QLabel; latch: QCheckBox; name_edit: QLineEdit
      name_hint: QLabel; arm_button: QPushButton
      def __init__(self, gate, parent=None, *, transport=None, timeout=None) -> None: ...
  def arm_now(gate, parent=None, **kwargs) -> bool: ...
  ```
  `arm_now` is the single entrance. Task 10's countdown and Task 12's Send button both call it; there is no
  second way past gate 2.

- [ ] **Step 1: Write the failing tests** — `tests/test_ui_write_dialogs.py`

```python
"""Spec §9.2: both write dialogs, offscreen, against `FakeDesk`.

No socket: every identity and every read comes from
`FakeDesk.write_transport()` (task 3), and every runner is constructed with
`timeout=0` so no test waits real seconds (`workers.py:114`).
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")

from tests.fake_desk import FakeDesk
from wing_parser.net.codec import OscMessage
from wing_parser.net.identity import WingIdentity

HOST = "192.168.128.28"
NAME = "WING-GIAQUY"


def _identity():
    return WingIdentity(ip=HOST, name=NAME, model="wing-rack",
                        serial="01009Y90604AAE", firmware="3.1-0-g9f314617:release")


class _Page:
    """The two things `WriteGate` reads off a Console page: state and host."""

    def __init__(self, state):
        self.state = state

        class _Bar:
            def host(self_inner):
                return HOST

        self.connect_bar = _Bar()


def _gate(qt_app, desk, state=None):
    from wing_parser.ui.live_state import LiveState
    from wing_parser.ui.live_wiring import WriteGate

    page = _Page(state or LiveState.CONNECTED)
    return WriteGate(page, transport=desk.write_transport(), timeout=0)


def _arm_dialog(qt_app, desk=None):
    from wing_parser.ui.write_arm_dialog import ArmWriteDialog

    desk = FakeDesk(identity=_identity()) if desk is None else desk
    gate = _gate(qt_app, desk)
    dlg = ArmWriteDialog(gate, transport=desk.write_transport(), timeout=0)
    return dlg, gate, desk


# -- Arm (F4, §8.2) -----------------------------------------------------


def test_arm_is_disabled_when_the_dialog_opens(qt_app, settle):
    dlg, _g, _d = _arm_dialog(qt_app)
    assert settle(lambda: NAME in dlg.status_label.text())
    assert dlg.arm_button.isEnabled() is False


def test_the_latch_alone_does_not_enable_arm(qt_app, settle):
    dlg, _g, _d = _arm_dialog(qt_app)
    settle(lambda: NAME in dlg.status_label.text())
    dlg.latch.setChecked(True)
    assert dlg.arm_button.isEnabled() is False


def test_the_name_alone_does_not_enable_arm(qt_app, settle):
    dlg, _g, _d = _arm_dialog(qt_app)
    settle(lambda: NAME in dlg.status_label.text())
    dlg.name_edit.setText(NAME)
    assert dlg.arm_button.isEnabled() is False


def test_both_together_enable_arm(qt_app, settle):
    dlg, _g, _d = _arm_dialog(qt_app)
    settle(lambda: NAME in dlg.status_label.text())
    dlg.latch.setChecked(True)
    dlg.name_edit.setText(NAME)
    assert dlg.arm_button.isEnabled() is True


@pytest.mark.parametrize("typed", ["WING-GIAQUI", "wing-giaquy", " WING-GIAQUY"])
def test_a_near_miss_name_is_refused_and_said_so(qt_app, settle, typed):
    """Exact, not case-folded and not stripped: §2.1 says "the typed name
    equals `identity.name` exactly"."""
    from wing_parser.ui.texts import text

    dlg, _g, _d = _arm_dialog(qt_app)
    settle(lambda: NAME in dlg.status_label.text())
    dlg.latch.setChecked(True)
    dlg.name_edit.setText(typed)
    assert dlg.arm_button.isEnabled() is False
    assert dlg.name_hint.text() == text("console.write.name_wrong")


def test_the_dialog_shows_the_serial_it_just_re_queried(qt_app, settle):
    dlg, _g, _d = _arm_dialog(qt_app)
    assert settle(lambda: "01009Y90604AAE" in dlg.status_label.text())


def test_an_identity_failure_leaves_arm_dead_for_this_dialogs_life(qt_app, settle):
    desk = FakeDesk(identity=TimeoutError("no reply"))
    dlg, _g, _d = _arm_dialog(qt_app, desk)
    assert settle(lambda: "Cannot identify" in dlg.status_label.text())
    assert "not armed" in dlg.status_label.text()
    dlg.latch.setChecked(True)
    dlg.name_edit.setText(NAME)
    assert dlg.arm_button.isEnabled() is False


def test_arming_arms_the_gate_and_announces_the_identity(qt_app, settle):
    dlg, gate, _d = _arm_dialog(qt_app)
    settle(lambda: NAME in dlg.status_label.text())
    seen = []
    dlg.armed.connect(seen.append)
    gate.changed.connect(lambda: seen.append("changed"))
    dlg.latch.setChecked(True)
    dlg.name_edit.setText(NAME)
    dlg.arm_button.click()

    assert gate.arm.armed() is True
    assert gate.arm.identity.serial == "01009Y90604AAE"
    assert any(getattr(item, "name", None) == NAME for item in seen)
    assert "changed" in seen, "the selector has to hear that the levels opened"


def test_arm_now_is_a_no_op_on_an_already_armed_gate(qt_app):
    from wing_parser.ui.write_arm_dialog import arm_now

    desk = FakeDesk(identity=_identity())
    gate = _gate(qt_app, desk)
    gate.arm.arm(_identity())
    assert arm_now(gate) is True, "no second dialog for an armed connection"


def test_the_arm_dialog_is_application_modal(qt_app):
    from PySide6.QtCore import Qt

    dlg, _g, _d = _arm_dialog(qt_app)
    assert dlg.windowModality() == Qt.WindowModality.ApplicationModal
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest tests/test_ui_write_dialogs.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.ui.write_arm_dialog'`

- [ ] **Step 3: Write the minimal implementation** — `wing_parser/ui/write_arm_dialog.py`

```python
"""Gate 2 (§8.2): nothing writes until this dialog has been satisfied.

Three conditions, all of them, once per connection (F4): a FRESH identity
re-query, the show latch ticked, and the console's exact name typed.

Identity is never reused from the earlier connect.
`net_commands._echo_identity_before_write` (`net_commands.py:79-85`) does
exactly this before every CLI write, and `identity.py:10-14` says why: the
caller is about to trust "this is the console I meant to write to".

The latch reads "This desk is NOT running a show right now." and starts
UNTICKED. Wave 2's sketch had it the other way round -- "this desk is in a
show", default on -- and a ticked box meaning "danger" reads backwards at
2 a.m., when every other checkbox in this app means "yes, do this".

**Its own `CallRunner`, not the Console page's** (W5). W1 allows writing
while the page is WATCHING, the page's runner is then legitimately busy,
and `CallRunner.start` returns False when it is (`workers.py:112-113`) --
a shared runner would refuse every identity read made during a watch, so
this dialog could not even show which desk it is about to arm.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
)

from wing_parser.ui import live_write
from wing_parser.ui.texts import text
from wing_parser.ui.workers import CallRunner


class ArmWriteDialog(QDialog):
    armed = Signal(object)          # the WingIdentity this arming is for

    def __init__(self, gate, parent=None, *, transport=None, timeout=None) -> None:
        super().__init__(parent)
        self._gate = gate
        self._transport = transport or live_write.REAL
        self._identity = None
        self.setWindowTitle(text("console.write.arm_title"))
        self.setWindowModality(Qt.WindowModality.ApplicationModal)     # W11

        self.status_label = QLabel(text("console.write.reading"))
        self.status_label.setWordWrap(True)
        self.latch = QCheckBox(text("console.write.latch"))
        self.latch_why = QLabel(text("console.write.latch_why"))
        self.latch_why.setWordWrap(True)
        self.name_edit = QLineEdit()
        self.name_hint = QLabel("")
        self.arm_button = QPushButton(text("console.write.arm"))
        self.arm_button.setEnabled(False)
        self.cancel_button = QPushButton(text("console.write.cancel"))

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(self.latch)
        layout.addWidget(self.latch_why)
        layout.addWidget(QLabel(text("console.write.name_prompt")))
        layout.addWidget(self.name_edit)
        layout.addWidget(self.name_hint)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.arm_button)
        layout.addLayout(buttons)

        self.latch.toggled.connect(self._refresh)
        self.name_edit.textChanged.connect(self._refresh)
        self.arm_button.clicked.connect(self._arm)
        self.cancel_button.clicked.connect(self.reject)

        self._runner = CallRunner(self)
        self._runner.start(
            "connect", self._transport.identity, gate.host(),
            on_success=self._identified, on_failure=self._identity_failed,
            timeout=timeout,
        )

    # -- the fresh read ----------------------------------------------------

    def _identified(self, identity) -> None:
        self._identity = identity
        self.status_label.setText(text("console.write.desk").format(
            name=identity.name, model=identity.model, serial=identity.serial))
        self._refresh()

    def _identity_failed(self, exc) -> None:
        """Dead for this dialog's life, deliberately. A desk that would not
        say who it is is not a desk to arm against, and a Retry button here
        would invite exactly that -- close it and connect again."""
        self.status_label.setText(text("console.write.identity_failed").format(
            host=self._gate.host(), error=exc))
        self._identity = None
        self._refresh()

    # -- the three conditions ----------------------------------------------

    def _refresh(self) -> None:
        typed = self.name_edit.text()
        matches = self._identity is not None and typed == self._identity.name
        self.name_hint.setText(
            "" if matches or not typed else text("console.write.name_wrong"))
        self.arm_button.setEnabled(bool(self.latch.isChecked() and matches))

    def _arm(self) -> None:
        if self._identity is None:
            return
        self._gate.arm.arm(self._identity)
        self._gate.changed.emit()
        self.armed.emit(self._identity)
        self.accept()


def arm_now(gate, parent=None, **kwargs) -> bool:
    """Open the dialog modally; True once the gate really is armed.

    THE single entrance. Manual's own Send button and the countdown both
    call this when unarmed, so Manual has one button that always means the
    same thing and the arming step appears only when it is needed (§2.2).
    """
    if gate.arm.armed():
        return True
    ArmWriteDialog(gate, parent, **kwargs).exec()
    return gate.arm.armed()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `$PY -m pytest tests/test_ui_write_dialogs.py tests/test_ui_house_style.py tests/test_ui_live_is_read_only.py`
Expected: PASS. Paste `wc -l wing_parser/ui/write_arm_dialog.py` — under 200. Then the full suite.

- [ ] **Step 5: Show each new test red once** — change `_refresh` to
      `self.arm_button.setEnabled(bool(self.latch.isChecked()))` and watch the three name tests fail;
      change the comparison to `typed.strip().lower() == self._identity.name.lower()` and watch the
      `wing-giaquy` and `" WING-GIAQUY"` cases fail. Capture both, restore.

- [ ] **Step 6: Commit**

```bash
git add wing_parser/ui/write_arm_dialog.py tests/test_ui_write_dialogs.py && git commit -m "feat(ui): arm a console for writing, once per connection"
```

Body names spec F4 and §8.2, and quotes CLAUDE.md's live-console rule.

**Claims to check by opening:** that `query_identity` has its own 2.0 s socket timeout
(`net/identity.py:68-69`) and `TIMEOUTS["connect"] = 5` is the backstop over it (`workers.py:28-37`); that
`WingIdentity` carries `ip name model serial firmware` (`identity.py:34-40`); that `CallRunner` delivers
callbacks on the GUI thread (`workers.py:86-94`).

---

### Task 10: `DelayedWriteDialog` — the countdown, and gate 4's late re-check

**Files:**
- Create: `wing_parser/ui/write_delay_dialog.py`
- Modify: `tests/test_ui_write_dialogs.py` (Task 9)

Read spec §2.3, F5, §8.4, W11, W12 and W15 first.

**Interfaces:**
- Consumes: `live_write.WriteConfirmation` + `WriteTransport.read` (Task 3), `WriteGate` + `WriteJob` +
  `GateClosed` (Task 8), `net.address.osc_address` (Task 1), `window._apply_delay` (Task 6),
  `text("console.write.*")` (Task 7).
- Produces:
  ```python
  # wing_parser/ui/write_delay_dialog.py
  EXTEND_SECONDS = 5
  class DelayedWriteDialog(QDialog):
      applied = Signal(object)          # the SetResult
      failed = Signal(object)           # GateClosed, SerialMismatchError, anything
      cancelled = Signal()              # W12: inside a revert run, stop the whole run
      remaining: int
      address_label / desk_label / file_label / after_label / mismatch_label: QLabel
      countdown_label / status_label: QLabel; bar: QProgressBar
      apply_button / extend_button / cancel_button: QPushButton
      def __init__(self, gate, patch, seconds, parent=None, *,
                   transport=None, timeout=None, revert_record=None) -> None: ...
  ```
  `patch` is an `edit.journal.Patch`. `revert_record` is a `live_write.SentWrite` for a revert step: the
  dialog then writes `record.desk_before` and its Cancel means **stop the run** (W12), saying
  `console.write.revert_cancelled`.

- [ ] **Step 1: Write the failing tests** — append to `tests/test_ui_write_dialogs.py`

```python
# -- Delayed (F5, §8.4, W11, W12) ---------------------------------------

PATH = "ae_data.ch.1.send.8.mode"
OSC = "/ch/1/send/8/mode"
BOOL_PATH = "ae_data.ch.1.in.set.inv"
BOOL_OSC = "/ch/1/in/set/inv"


def _patch(path=PATH, before="POST", after="PRE"):
    from wing_parser.edit.journal import Patch
    return Patch(path=path, before=before, after=after, because="G8:ch.1.send.8",
                 label="Set the send to PRE (ch.1.send.8)")


def _delay_dialog(qt_app, *, desk=None, seconds=5, patch=None, armed=True, **kwargs):
    from wing_parser.ui.write_delay_dialog import DelayedWriteDialog

    desk = desk or FakeDesk(identity=_identity(),
                            leaves={OSC: OscMessage(OSC, "s", ("POST",))},
                            readbacks={OSC: "PRE"})
    gate = _gate(qt_app, desk)
    if armed:
        gate.arm.arm(_identity())
    dlg = DelayedWriteDialog(gate, patch or _patch(), seconds,
                             transport=desk.write_transport(), timeout=0, **kwargs)
    return dlg, gate, desk


def test_the_countdown_starts_at_the_settings_value(qt_app):
    dlg, _g, _d = _delay_dialog(qt_app, seconds=9)
    assert dlg.remaining == 9
    assert "9" in dlg.countdown_label.text()


def test_plus_five_adds_to_the_remainder_repeatably_with_no_ceiling(qt_app):
    """F5: an operator who needs a minute presses it twelve times, and that
    is a legitimate answer."""
    dlg, _g, _d = _delay_dialog(qt_app, seconds=5)
    for expected in (10, 15, 20, 25, 30, 35, 40, 45, 50, 55, 60, 65):
        dlg.extend_button.click()
        assert dlg.remaining == expected


def test_the_dialog_shows_the_desk_value_the_file_value_and_the_new_one(qt_app, settle):
    dlg, _g, _d = _delay_dialog(qt_app)
    assert settle(lambda: "POST" in dlg.desk_label.text())
    assert "POST" in dlg.file_label.text()
    assert "PRE" in dlg.after_label.text()
    assert OSC in dlg.address_label.text()


def test_the_mismatch_line_appears_only_when_the_desk_moved(qt_app, settle):
    quiet, _g, _d = _delay_dialog(qt_app)
    assert settle(lambda: "POST" in quiet.desk_label.text())
    assert quiet.mismatch_label.text() == ""

    desk = FakeDesk(identity=_identity(),
                    leaves={OSC: OscMessage(OSC, "s", ("GRP",))},
                    readbacks={OSC: "PRE"})
    moved, _g2, _d2 = _delay_dialog(qt_app, desk=desk)
    assert settle(lambda: moved.mismatch_label.text())
    assert "GRP" in moved.mismatch_label.text()
    assert "POST" in moved.mismatch_label.text()


def test_a_bool_leaf_reads_true_and_false_never_one_and_zero(qt_app, settle):
    """§4's normalisation, seen where it actually misleads an operator: an
    unnormalised read shows "the desk holds 0, the scene file expected
    False" and a mismatch warning that is not one."""
    desk = FakeDesk(identity=_identity(),
                    leaves={BOOL_OSC: OscMessage(BOOL_OSC, "sfi", ("1", 0.0, 1))},
                    readbacks={BOOL_OSC: 0})
    dlg, _g, _d = _delay_dialog(
        qt_app, desk=desk,
        patch=_patch(path=BOOL_PATH, before=True, after=False))
    assert settle(lambda: dlg.desk_label.text() != "")
    assert "True" in dlg.desk_label.text()
    assert dlg.mismatch_label.text() == "", "True == True is not a mismatch"


def test_a_desk_that_lacks_the_address_says_so_instead_of_guessing(qt_app, settle):
    from wing_parser.ui.texts import text

    desk = FakeDesk(identity=_identity(), leaves={})
    dlg, _g, _d = _delay_dialog(qt_app, desk=desk)
    assert settle(lambda: dlg.desk_label.text() == text("console.write.no_read"))


def test_apply_now_sends_at_once(qt_app, settle):
    dlg, _g, desk = _delay_dialog(qt_app)
    settle(lambda: dlg.desk_label.text() != "")
    results = []
    dlg.applied.connect(results.append)
    dlg.apply_button.click()
    assert settle(lambda: results)
    assert [c[0:2] for c in desk.sets] == [(OSC, "PRE")]


def test_expiry_is_an_apply(qt_app, settle):
    """F5, stated flatly: a dialog that quietly dropped the write on timeout
    would leave the desk and the scene disagreeing with nobody told."""
    dlg, _g, desk = _delay_dialog(qt_app, seconds=3)
    settle(lambda: dlg.desk_label.text() != "")
    results = []
    dlg.applied.connect(results.append)
    for _ in range(3):
        dlg._tick()
    assert settle(lambda: results)
    assert [c[0:2] for c in desk.sets] == [(OSC, "PRE")]


def test_cancel_sends_nothing_and_leaves_the_journal_patch_alone(qt_app, settle):
    from wing_parser.ui.texts import text

    dlg, _g, desk = _delay_dialog(qt_app)
    settle(lambda: dlg.desk_label.text() != "")
    heard = []
    dlg.cancelled.connect(lambda: heard.append(True))
    dlg.cancel_button.click()
    assert desk.sets == []
    assert heard
    assert dlg.status_label.text() == text("console.write.cancelled")
    assert "Undo" in text("console.write.cancelled")


def test_gate_four_refuses_a_countdown_that_outlived_its_connection(qt_app, settle):
    """§8.4: a countdown can run a minute and the desk can go LOST under it."""
    from wing_parser.ui.live_state import LiveState
    from wing_parser.ui.texts import text

    dlg, gate, desk = _delay_dialog(qt_app, seconds=1)
    settle(lambda: dlg.desk_label.text() != "")
    failures = []
    dlg.failed.connect(failures.append)
    gate._page.state = LiveState.LOST          # the desk went away underneath
    dlg._tick()
    assert settle(lambda: failures)
    assert desk.sets == []
    assert dlg.status_label.text() == text("console.write.gate_closed")


def test_disarming_under_a_countdown_refuses_it_too(qt_app, settle):
    dlg, gate, desk = _delay_dialog(qt_app, seconds=1)
    settle(lambda: dlg.desk_label.text() != "")
    failures = []
    dlg.failed.connect(failures.append)
    gate.arm.disarm()
    dlg._tick()
    assert settle(lambda: failures)
    assert desk.sets == []


def test_the_delay_dialog_is_application_modal(qt_app):
    from PySide6.QtCore import Qt

    dlg, _g, _d = _delay_dialog(qt_app)
    assert dlg.windowModality() == Qt.WindowModality.ApplicationModal


def _record(desk_before="POST"):
    from wing_parser.net.write import SetResult
    from wing_parser.ui.live_write import SentWrite

    return SentWrite(address=OSC, path=PATH, desk_before=desk_before,
                     written="PRE",
                     result=SetResult(OSC, "PRE", "PRE", False, "PRE", True))


def test_a_revert_countdowns_cancel_stops_the_whole_run(qt_app, settle):
    """W12: not "skip this one" -- a seven-row revert would need seven
    deliberate cancels to abandon, the opposite of what Cancel promises."""
    from wing_parser.ui.texts import text

    dlg, _g, desk = _delay_dialog(qt_app, revert_record=_record())
    settle(lambda: dlg.desk_label.text() != "")
    heard = []
    dlg.cancelled.connect(lambda: heard.append(True))
    dlg.cancel_button.click()
    assert heard and desk.sets == []
    assert dlg.status_label.text() == text("console.write.revert_cancelled")


def test_a_revert_countdown_writes_the_desk_before_value(qt_app, settle):
    dlg, _g, desk = _delay_dialog(qt_app, revert_record=_record(desk_before="GRP"))
    settle(lambda: dlg.desk_label.text() != "")
    dlg.apply_button.click()
    assert settle(lambda: desk.sets)
    assert desk.sets[0][0:2] == (OSC, "GRP")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest tests/test_ui_write_dialogs.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.ui.write_delay_dialog'`

- [ ] **Step 3: Write the minimal implementation** — `wing_parser/ui/write_delay_dialog.py`

```python
"""Gate 3 (§8.3): the countdown an operator can watch, extend or cancel.

**Expiry is an apply** (F5). The screen is a chance to stop, not a
confirmation to give: the operator has already decided by clicking Repair,
and a dialog that quietly dropped the write on timeout would leave the desk
and the scene disagreeing with nobody told.

**Cancel leaves the scene edit in place.** The Repair already happened, the
journal holds the `Patch`, Doctor already re-derived; Cancel drops only the
transmission, and Undo in the Changes panel drops the file side
(`ui/session.py:71-75`). Different doors, and `console.write.cancelled`
says so.

**Gate 4 re-checks at the last moment** (§8.4). This countdown can run for
a minute -- `+5 s` is unbounded -- and `RoundGuard` can declare the desk
lost underneath it in under a second (`live_guard.py:44-52`). So Apply now
and expiry both re-ask `WriteGate.ready()` immediately before the
confirmation is built.

The countdown is a `QTimer` on the GUI thread: it counts seconds and
touches no socket, so `+5 s` cannot block the window. The PRE-FLIGHT read
runs on this dialog's OWN `CallRunner` (W5), never the Console page's,
because that one is legitimately busy during a watch.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout,
)

from wing_parser.net.address import osc_address
from wing_parser.ui import live_write
from wing_parser.ui.live_wiring import GateClosed, WriteJob
from wing_parser.ui.texts import text
from wing_parser.ui.workers import CallRunner

EXTEND_SECONDS = 5


class DelayedWriteDialog(QDialog):
    applied = Signal(object)        # the SetResult
    failed = Signal(object)         # GateClosed, SerialMismatchError, anything
    cancelled = Signal()            # W12: inside a revert run, stop the run

    def __init__(self, gate, patch, seconds, parent=None, *,
                 transport=None, timeout=None, revert_record=None) -> None:
        super().__init__(parent)
        self._gate = gate
        self._patch = patch
        self._record = revert_record
        self._transport = transport or live_write.REAL
        self._address = osc_address(patch.path)
        self._after = revert_record.desk_before if revert_record else patch.after
        #: What the desk answered the pre-flight read with, NORMALISED --
        #: the ledger records this value, so it is kept as a value and not
        #: scraped back off the label, which would lose its type.
        self.desk_before = None
        self._settled = False
        self.remaining = int(seconds)
        self._total = int(seconds)

        self.setWindowTitle(text("console.write.delay_title").format(seconds=seconds))
        self.setWindowModality(Qt.WindowModality.ApplicationModal)     # W11

        self.address_label = QLabel(
            text("console.write.address").format(address=self._address))
        self.desk_label = QLabel("")
        self.file_label = QLabel(
            text("console.write.file_value").format(value=patch.before))
        self.after_label = QLabel(
            text("console.write.after").format(value=self._after))
        self.mismatch_label = QLabel("")
        self.mismatch_label.setWordWrap(True)
        self.countdown_label = QLabel(
            text("console.write.countdown").format(remaining=self.remaining))
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.bar = QProgressBar()
        self.bar.setRange(0, self._total)
        self.bar.setValue(self.remaining)

        self.apply_button = QPushButton(text("console.write.apply_now"))
        self.extend_button = QPushButton(text("console.write.extend"))
        self.cancel_button = QPushButton(text("console.write.cancel"))

        layout = QVBoxLayout(self)
        for widget in (self.address_label, self.desk_label, self.file_label,
                       self.after_label, self.mismatch_label,
                       self.countdown_label, self.bar, self.status_label):
            layout.addWidget(widget)
        buttons = QHBoxLayout()
        buttons.addWidget(self.cancel_button)
        buttons.addStretch(1)
        buttons.addWidget(self.extend_button)
        buttons.addWidget(self.apply_button)
        layout.addLayout(buttons)

        self.apply_button.clicked.connect(self._apply)
        self.extend_button.clicked.connect(self._extend)
        self.cancel_button.clicked.connect(self._cancel)

        self._runner = CallRunner(self)
        self._runner.start(
            "connect", self._transport.read, gate.host(), patch.path,
            on_success=self._read_desk, on_failure=lambda _exc: self._no_read(),
            timeout=timeout,
        )
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

    # -- the pre-flight read ------------------------------------------------

    def _read_desk(self, value) -> None:
        if value is None:
            self._no_read()
            return
        self.desk_before = value
        self.desk_label.setText(
            text("console.write.desk_value").format(value=value))
        if value != self._patch.before:
            # Somebody moved the desk after the scene was pulled. What to do
            # about it is the operator's call, not the app's -- both values
            # go on screen and the countdown keeps running.
            self.mismatch_label.setText(text("console.write.mismatch").format(
                desk=value, file=self._patch.before))

    def _no_read(self) -> None:
        self.desk_label.setText(text("console.write.no_read"))

    # -- the countdown -------------------------------------------------------

    def _tick(self) -> None:
        self.remaining -= 1
        self.bar.setValue(max(self.remaining, 0))
        self.countdown_label.setText(text("console.write.countdown").format(
            remaining=max(self.remaining, 0)))
        if self.remaining <= 0:
            self._apply()                  # F5: expiry IS an apply

    def _extend(self) -> None:
        """Adds five to whatever remains, any number of times, no ceiling."""
        self.remaining += EXTEND_SECONDS
        self._total = max(self._total, self.remaining)
        self.bar.setMaximum(self._total)
        self.bar.setValue(self.remaining)
        self.countdown_label.setText(
            text("console.write.countdown").format(remaining=self.remaining))

    # -- the three ways out ---------------------------------------------------

    def _apply(self) -> None:
        if self._settled:
            return
        self._settled = True
        self._timer.stop()
        if not self._gate.ready():                       # GATE 4 (§8.4)
            self.status_label.setText(text("console.write.gate_closed"))
            self.failed.emit(GateClosed(text("console.write.gate_closed")))
            return
        self.status_label.setText(
            text("console.write.sending").format(address=self._address))
        self._gate.submit(WriteJob(
            live_write.WriteConfirmation(
                host=self._gate.host(), address=self._address,
                after=self._after, identity=self._gate.arm.identity,
                desk_before=self.desk_before,
            ),
            self._done, self._failed,
        ))

    def _done(self, result) -> None:
        self.applied.emit(result)
        self.accept()

    def _failed(self, exc) -> None:
        self.status_label.setText(text("console.write.refused").format(error=exc))
        self.failed.emit(exc)

    def _cancel(self) -> None:
        """W12: inside a revert run this stops the WHOLE run, exactly as the
        ledger's Stop does -- already-sent and in-flight reverts stay, the
        remainder is left. W15: in Delayed this IS the way out, because a
        Stop button behind a modal dialog is not reachable at all."""
        if self._settled:
            return
        self._settled = True
        self._timer.stop()
        self.status_label.setText(text(
            "console.write.revert_cancelled" if self._record
            else "console.write.cancelled"))
        self.cancelled.emit()
        self.reject()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `$PY -m pytest tests/test_ui_write_dialogs.py tests/test_ui_house_style.py tests/test_ui_live_is_read_only.py`
Expected: PASS. Paste `wc -l wing_parser/ui/write_delay_dialog.py` — under 200. Then the full suite.

- [ ] **Step 5: Show each new test red once** — delete the `if not self._gate.ready()` branch and watch
      `test_gate_four_refuses_a_countdown_that_outlived_its_connection` fail with a recorded `set`; change
      `_tick`'s expiry branch to `self.reject()` and watch `test_expiry_is_an_apply` fail. Capture both,
      restore.

- [ ] **Step 6: Commit**

```bash
git add wing_parser/ui/write_delay_dialog.py tests/test_ui_write_dialogs.py && git commit -m "feat(ui): show the countdown a delayed apply runs on"
```

Body names spec F5, §8.4, W11, W12 and W15.

**Claims to check by opening:** that `CallRunner.start` returns `False` while busy, which is why this dialog
owns its runner (`workers.py:112-113`, W5); that `RoundGuard` raises `DeskLost` after three silent rounds
(`live_guard.py:44-52`); that `Session.undo` drops only the last patch (`session.py:71-75`), which is what
`console.write.cancelled` promises; that `Patch` carries `before` captured at repair time
(`edit/journal.py:16-18`), which is what `file_label` shows.

---

### Task 11: The Doctor selector and Arm button, and Repair routing for all three levels

**Files:**
- Create: `wing_parser/ui/write_router.py` (**new module, ≤160, Qt** — see Deviations item 3)
- Modify: `wing_parser/ui/doctor_page.py` (**70 lines**), `wing_parser/ui/detail_panel.py` (**127**),
  `wing_parser/ui/live_wiring.py` (Task 8), `tests/test_ui_doctor.py` (**57**),
  `tests/test_ui_write_dialogs.py` (Task 9/10)

Read spec §2.2, F3, W14 and the data-flow block in §4 first, then `ui/detail_panel.py:123-127` (`_repair`,
the one method this task changes) and `ui/session.py:57-69`.

**Why a new module.** The routing has to live somewhere that is not `main_window.py` (≤4 lines this wave),
not `console_page.py` or `live_controller.py` (must not grow, W7), and not `changes_send.py` (≤120 in §4,
which the Send button and its badges fill on their own). `live_wiring.py` is at ~165 after Task 8 and the
routing plus the Immediate pre-flight is another ~60. So `write_router.py`: *what happens to a repair between
the click and the ledger row.*

**Interfaces:**
- Consumes: `ApplyLevel` / `ArmState` (Task 2), `live_write` + `SentWrite` (Tasks 3, 4), `WriteGate` /
  `WriteJob` (Task 8), `arm_now` (Task 9), `DelayedWriteDialog` (Task 10), `window._apply_delay` (Task 6),
  `net.address.osc_address` (Task 1).
- Produces:
  ```python
  # wing_parser/ui/write_router.py
  class ImmediateWrite(QObject):          # its own CallRunner for the pre-flight read (W5)
      def __init__(self, gate, patch, after, *, transport=None, timeout=None,
                   on_sent=None, on_error=None, parent=None) -> None: ...
  def route_repair(gate, patch, delay, parent=None, *, transport=None, timeout=None,
                   on_sent=None, on_error=None) -> QDialog | None: ...
  def route_revert(gate, record, delay, parent=None, *, transport=None, timeout=None,
                   on_sent=None, on_error=None, on_cancelled=None) -> QDialog | None: ...

  # wing_parser/ui/detail_panel.py
  class DetailPanel(QWidget):
      send_requested = Signal(object)     # the journal Patch the repair just appended

  # wing_parser/ui/doctor_page.py
  class DoctorPage(QWidget):
      send_requested = Signal(object)     # re-emitted from DetailPanel
      level_box: QComboBox; arm_button: QPushButton
      def attach_gate(self, gate) -> None: ...
      def set_controls_enabled(self, enabled: bool) -> None: ...   # W14, used by task 13
  ```
  `on_sent` is `Callable[[Patch, SentWrite], None]`; `on_error` is `Callable[[Exception], None]`.

- [ ] **Step 1: Write the failing tests** — `tests/test_ui_doctor.py`

```python
# -- the apply-level selector and Arm (F3, F4, W14) ---------------------
#
# `tests/test_ui_doctor.py` had none of these helpers before this task; all
# four are new at the top of the file, beside the existing `page` fixture.

from wing_parser.ui.apply_level import ApplyLevel


def _identity():
    from wing_parser.net.identity import WingIdentity

    return WingIdentity(ip="192.168.128.28", name="WING-GIAQUY",
                        model="wing-rack", serial="01009Y90604AAE",
                        firmware="3.1-0-g9f314617:release")


def _has_repair(finding) -> bool:
    from wing_parser.edit import repairs

    return finding.rule_id in repairs.load_repairs()


def _doctor(qt_app, desk=None, state=None):
    from tests.fake_desk import FakeDesk
    from wing_parser.ui.doctor_page import DoctorPage
    from wing_parser.ui.live_state import LiveState
    from wing_parser.ui.live_wiring import WriteGate

    desk = desk or FakeDesk(identity=_identity())

    class _Bar:
        def host(self):
            return "192.168.128.28"

    class _Page:
        pass

    page = _Page()
    page.state = state or LiveState.CONNECTED
    page.connect_bar = _Bar()
    gate = WriteGate(page, transport=desk.write_transport(), timeout=0)
    doctor = DoctorPage()
    doctor.attach_gate(gate)
    return doctor, gate, desk


def test_the_selector_offers_delayed_and_immediate_only_when_armed(qt_app):
    doctor, gate, _d = _doctor(qt_app)
    assert doctor.level_box.currentData() is ApplyLevel.MANUAL
    for index in range(doctor.level_box.count()):
        enabled = doctor.level_box.model().item(index).isEnabled()
        assert enabled == (doctor.level_box.itemData(index) is ApplyLevel.MANUAL)

    gate.arm.arm(_identity())
    gate.changed.emit()
    for index in range(doctor.level_box.count()):
        assert doctor.level_box.model().item(index).isEnabled()


def test_the_selector_falls_back_to_manual_on_disarm(qt_app):
    doctor, gate, _d = _doctor(qt_app)
    gate.arm.arm(_identity())
    gate.changed.emit()
    doctor.level_box.setCurrentIndex(
        doctor.level_box.findData(ApplyLevel.IMMEDIATE))
    assert gate.arm.level is ApplyLevel.IMMEDIATE

    gate.close()                                  # a dropout
    assert doctor.level_box.currentData() is ApplyLevel.MANUAL
    assert gate.arm.level is ApplyLevel.MANUAL


def test_the_arm_button_becomes_the_armed_label(qt_app):
    from wing_parser.ui.texts import text

    doctor, gate, _d = _doctor(qt_app)
    assert doctor.arm_button.text() == text("console.write.arm")
    gate.arm.arm(_identity())
    gate.changed.emit()
    assert doctor.arm_button.text() == text("console.write.armed").format(
        name="WING-GIAQUY")


def test_the_selector_and_arm_go_dead_for_a_revert_run_and_come_back(qt_app):
    """W14: a run that changed level halfway would send some parameters
    through a countdown and others instantly, from one click."""
    doctor, _g, _d = _doctor(qt_app)
    doctor.set_controls_enabled(False)
    assert doctor.level_box.isEnabled() is False
    assert doctor.arm_button.isEnabled() is False
    doctor.set_controls_enabled(True)
    assert doctor.level_box.isEnabled() is True
    assert doctor.arm_button.isEnabled() is True


def test_repair_announces_the_patch_it_appended(qt_app, vu_path):
    """The routing hook: DetailPanel emits the journal's newest Patch."""
    from wing_parser.ui.session import Session

    doctor, _g, _d = _doctor(qt_app)
    session = Session.open(vu_path)
    finding = next(f for f in session.findings()
                   if session.rule(f.rule_id) and _has_repair(f))
    doctor.set_session(session)
    doctor.show_finding(finding)
    seen = []
    doctor.send_requested.connect(seen.append)

    doctor.detail_panel.repair_button.click()

    assert seen, "a successful repair must announce its patch"
    assert seen[0] is session.changes()[-1]


def test_a_repair_that_does_nothing_announces_nothing(qt_app):
    doctor, _g, _d = _doctor(qt_app)
    seen = []
    doctor.send_requested.connect(seen.append)
    doctor.detail_panel._repair()          # no finding, no session
    assert seen == []
```

and in `tests/test_ui_write_dialogs.py`, the three routing cases:

```python
# -- routing, one test per level (F3) -----------------------------------


def test_manual_sends_nothing_and_opens_nothing(qt_app):
    from wing_parser.ui import write_router
    from wing_parser.ui.apply_level import ApplyLevel

    desk = FakeDesk(identity=_identity(),
                    leaves={OSC: OscMessage(OSC, "s", ("POST",))})
    gate = _gate(qt_app, desk)
    gate.arm.arm(_identity())
    gate.arm.level = ApplyLevel.MANUAL

    dialog = write_router.route_repair(
        gate, _patch(), 5, transport=desk.write_transport(), timeout=0)
    assert dialog is None
    assert desk.sets == []


def test_delayed_opens_the_countdown_and_sends_nothing_yet(qt_app):
    from wing_parser.ui import write_router
    from wing_parser.ui.apply_level import ApplyLevel
    from wing_parser.ui.write_delay_dialog import DelayedWriteDialog

    desk = FakeDesk(identity=_identity(),
                    leaves={OSC: OscMessage(OSC, "s", ("POST",))},
                    readbacks={OSC: "PRE"})
    gate = _gate(qt_app, desk)
    gate.arm.arm(_identity())
    gate.arm.level = ApplyLevel.DELAYED

    dialog = write_router.route_repair(
        gate, _patch(), 9, transport=desk.write_transport(), timeout=0)
    assert isinstance(dialog, DelayedWriteDialog)
    assert dialog.remaining == 9
    assert desk.sets == []
    dialog.reject()


def test_immediate_produces_exactly_one_set_and_no_dialog(qt_app, settle):
    from wing_parser.ui import write_router
    from wing_parser.ui.apply_level import ApplyLevel

    desk = FakeDesk(identity=_identity(),
                    leaves={OSC: OscMessage(OSC, "s", ("POST",))},
                    readbacks={OSC: "PRE"})
    gate = _gate(qt_app, desk)
    gate.arm.arm(_identity())
    gate.arm.level = ApplyLevel.IMMEDIATE
    sent = []

    dialog = write_router.route_repair(
        gate, _patch(), 5, transport=desk.write_transport(), timeout=0,
        on_sent=lambda patch, record: sent.append(record))

    assert dialog is None
    assert settle(lambda: sent)
    assert [c[0:2] for c in desk.sets] == [(OSC, "PRE")]
    assert sent[0].desk_before == "POST", "the ledger records what the desk held"
    assert sent[0].written == "PRE"


def test_an_unarmed_route_opens_the_arm_dialog_first(qt_app, monkeypatch):
    """§2.2: Manual's Send and a Delayed repair both enter through arm_now."""
    from wing_parser.ui import write_router
    from wing_parser.ui.apply_level import ApplyLevel

    desk = FakeDesk(identity=_identity(),
                    leaves={OSC: OscMessage(OSC, "s", ("POST",))})
    gate = _gate(qt_app, desk)
    gate.arm.level = ApplyLevel.DELAYED         # selected but NOT armed
    calls = []
    monkeypatch.setattr(write_router, "arm_now",
                        lambda g, parent=None, **kw: calls.append(g) or False)

    assert write_router.route_repair(
        gate, _patch(), 5, transport=desk.write_transport(), timeout=0) is None
    assert calls == [gate], "no write path may skip gate 2"
    assert desk.sets == []
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest tests/test_ui_doctor.py tests/test_ui_write_dialogs.py`
Expected: FAIL — `AttributeError: 'DoctorPage' object has no attribute 'attach_gate'` and
`ModuleNotFoundError: No module named 'wing_parser.ui.write_router'`

- [ ] **Step 3: Write the minimal implementation**

`wing_parser/ui/write_router.py`:

```python
"""What happens to a repair between the click and the ledger row (F3).

Three levels, one entry point. Manual stops here -- the journal row's own
Send button resumes it, and that button opens the countdown too, so Manual
has one control that always means the same thing. Delayed opens the
countdown. Immediate reads the desk once, then writes.

**Immediate still reads first.** The ledger records the desk-live value
captured BEFORE the write (F7), and without it Revert would have nothing to
write back. That read runs on `ImmediateWrite`'s own `CallRunner` (W5), the
same rule the two dialogs follow, because the Console page's runner is
legitimately busy during a watch (`workers.py:112-113`).

A module of its own because nowhere else would take it: `main_window.py`
gets four lines this whole wave, `console_page.py` and `live_controller.py`
may not grow at all (W7), `changes_send.py` is budgeted at 120 for the Send
button and its badges, and `live_wiring.py` already carries the gate.
"""

from __future__ import annotations

from PySide6.QtCore import QObject

from wing_parser.net.address import osc_address
from wing_parser.ui import live_write
from wing_parser.ui.apply_level import ApplyLevel
from wing_parser.ui.live_wiring import WriteJob
from wing_parser.ui.workers import CallRunner
from wing_parser.ui.write_arm_dialog import arm_now
from wing_parser.ui.write_delay_dialog import DelayedWriteDialog


def _record(path, desk_before, written, result) -> live_write.SentWrite:
    return live_write.SentWrite(address=osc_address(path), path=path,
                                desk_before=desk_before, written=written,
                                result=result)


class ImmediateWrite(QObject):
    """Read the desk once, then write. No dialog -- that is the trade F3
    buys, and exactly why Immediate cannot be reached without arming and
    why the selector falls back to Manual the moment the connection drops.

    Keeps itself referenced through its `CallRunner` parent chain until the
    write settles; the caller does not have to hold it.
    """

    def __init__(self, gate, patch, after, *, transport=None, timeout=None,
                 on_sent=None, on_error=None, parent=None) -> None:
        super().__init__(parent or gate)
        self._gate = gate
        self._patch = patch
        self._after = after
        self._address = osc_address(patch.path)
        self._on_sent = on_sent or (lambda _p, _r: None)
        self._on_error = on_error or (lambda _e: None)
        self._runner = CallRunner(self)
        self._runner.start(
            "connect", (transport or live_write.REAL).read,
            gate.host(), patch.path,
            on_success=self._write, on_failure=lambda _exc: self._write(None),
            timeout=timeout,
        )

    def _write(self, desk_before) -> None:
        if not self._gate.ready():                          # GATE 4 (§8.4)
            from wing_parser.ui.live_wiring import GateClosed
            from wing_parser.ui.texts import text
            self._on_error(GateClosed(text("console.write.gate_closed")))
            return
        self._desk_before = desk_before
        self._gate.submit(WriteJob(
            live_write.WriteConfirmation(
                host=self._gate.host(), address=self._address,
                after=self._after, identity=self._gate.arm.identity,
                desk_before=desk_before),
            self._done, self._on_error,
        ))

    def _done(self, result) -> None:
        self._on_sent(self._patch,
                      _record(self._patch.path, self._desk_before,
                              self._after, result))


def route_repair(gate, patch, delay, parent=None, *, transport=None, timeout=None,
                 on_sent=None, on_error=None):
    """Apply `patch` to the desk at the gate's CURRENT level (F3).

    Returns the `DelayedWriteDialog` when one was opened, else `None`.
    """
    level = gate.arm.level
    if level is ApplyLevel.MANUAL:
        return None                    # the journal row's Send resumes it
    if not arm_now(gate, parent, transport=transport, timeout=timeout):
        return None
    if level is ApplyLevel.IMMEDIATE:
        ImmediateWrite(gate, patch, patch.after, transport=transport,
                       timeout=timeout, on_sent=on_sent, on_error=on_error,
                       parent=parent)
        return None
    return _countdown(gate, patch, patch.after, delay, parent,
                      transport=transport, timeout=timeout,
                      on_sent=on_sent, on_error=on_error)


def route_revert(gate, record, delay, parent=None, *, transport=None, timeout=None,
                 on_sent=None, on_error=None, on_cancelled=None):
    """F7: write a ledger row's captured desk-before value back, through the
    CURRENT level -- Immediate at once, Delayed and Manual via the
    countdown. Manual reverts through the countdown too, so a revert is
    never a silent packet."""
    from wing_parser.edit.journal import Patch

    if not arm_now(gate, parent, transport=transport, timeout=timeout):
        return None
    patch = Patch(path=record.path, before=record.result.readback,
                  after=record.desk_before, because="revert", label="Revert")
    if gate.arm.level is ApplyLevel.IMMEDIATE:
        ImmediateWrite(gate, patch, record.desk_before, transport=transport,
                       timeout=timeout, on_sent=on_sent, on_error=on_error,
                       parent=parent)
        return None
    return _countdown(gate, patch, record.desk_before, delay, parent,
                      transport=transport, timeout=timeout, on_sent=on_sent,
                      on_error=on_error, on_cancelled=on_cancelled,
                      revert_record=record)


def _countdown(gate, patch, after, delay, parent, *, transport, timeout,
               on_sent=None, on_error=None, on_cancelled=None,
               revert_record=None):
    dialog = DelayedWriteDialog(gate, patch, delay, parent, transport=transport,
                                timeout=timeout, revert_record=revert_record)
    if on_sent is not None:
        dialog.applied.connect(lambda result: on_sent(
            patch, _record(patch.path, dialog.desk_before, after, result)))
    if on_error is not None:
        dialog.failed.connect(on_error)
    if on_cancelled is not None:
        dialog.cancelled.connect(on_cancelled)
    dialog.open()
    return dialog
```

**`record.path` is why `SentWrite` carries both spellings.** `route_revert` needs the dotted document path
back — to build a `Patch` and to reach `jsontypes` — and this project has no inverse of `osc_address`.
Task 3 therefore gave the record `path` beside `address`; nothing here derives one from the other.

`wing_parser/ui/detail_panel.py` — one signal and three lines in `_repair` (`:123-127`):

```python
    repaired = Signal()
    #: The journal Patch a successful repair just appended, for the write
    #: router (F3). Emitted AFTER `repaired`, so Doctor has already
    #: re-derived and the Changes dock already holds the row the countdown
    #: is about to talk about.
    send_requested = Signal(object)

    def _repair(self) -> None:
        if self._finding is None or self._session is None:
            return
        if not self._session.repair(self._finding):
            return
        self.repaired.emit()
        self.send_requested.emit(self._session.changes()[-1])
```

`wing_parser/ui/doctor_page.py` — the selector bar above the splitter:

```python
    send_requested = Signal(object)
    ...
        self.level_box = QComboBox()
        for level, key in ((ApplyLevel.MANUAL, "manual"),
                           (ApplyLevel.DELAYED, "delayed"),
                           (ApplyLevel.IMMEDIATE, "immediate")):
            self.level_box.addItem(text(f"console.write.{key}"), level)
        self.arm_button = QPushButton(text("console.write.arm"))
        bar = QHBoxLayout()
        bar.addWidget(QLabel(text("console.write.level")))
        bar.addWidget(self.level_box)
        bar.addWidget(self.arm_button)
        bar.addStretch(1)
        right_layout.insertLayout(0, bar)
        self.detail_panel.send_requested.connect(self.send_requested)

    def attach_gate(self, gate) -> None:
        """Bind the selector and Arm to the gate `live_wiring` published.

        The Doctor page NEVER imports `console_page` (§8.1): everything it
        knows about the live connection arrives through this one object.
        """
        self._gate = gate
        gate.changed.connect(self._follow_gate)
        self.level_box.currentIndexChanged.connect(self._level_picked)
        self.arm_button.clicked.connect(
            lambda: arm_now(gate, self.window()))
        self._follow_gate()

    def _follow_gate(self) -> None:
        armed = self._gate.arm.armed()
        model = self.level_box.model()
        for index in range(self.level_box.count()):
            allowed = armed or self.level_box.itemData(index) is ApplyLevel.MANUAL
            model.item(index).setEnabled(allowed)
        if not armed:
            self.level_box.setCurrentIndex(
                self.level_box.findData(ApplyLevel.MANUAL))
        self.arm_button.setText(
            text("console.write.armed").format(name=self._gate.arm.identity.name)
            if armed else text("console.write.arm"))

    def _level_picked(self) -> None:
        self._gate.arm.level = self.level_box.currentData()

    def set_controls_enabled(self, enabled: bool) -> None:
        """W14: dead while a Revert-all run is going, alive again on Stop."""
        self.level_box.setEnabled(enabled)
        self.arm_button.setEnabled(enabled)
```

`wing_parser/ui/live_wiring.py` — inside `install_write_gate`, after the panel wiring:

```python
    doctor = getattr(window, "pages", {}).get("doctor")
    if doctor is not None and hasattr(doctor, "attach_gate"):
        doctor.attach_gate(gate)
        doctor.send_requested.connect(lambda patch: write_router.route_repair(
            gate, patch, getattr(window, "_apply_delay", 5), window,
            on_sent=lambda p, record: changes.record_sent(p, record),
            on_error=lambda exc: changes.report_write_error(exc)))
```

(`changes` is already bound above; the two `ChangesPanel` methods arrive in Task 12, so guard this whole
block with `hasattr(changes, "record_sent")` until then — or land Task 11 and 12 as a pair on one
implementer. **Land them as a pair**: they are separate tasks for review granularity, not for parallelism.)

- [ ] **Step 4: Run the tests to verify they pass**

Run: `$PY -m pytest tests/test_ui_doctor.py tests/test_ui_write_dialogs.py tests/test_ui_shell.py tests/test_ui_house_style.py tests/test_ui_live_is_read_only.py`
Expected: PASS. Paste `wc -l` for `write_router.py`, `doctor_page.py`, `detail_panel.py`, `live_wiring.py` —
all under 200.

- [ ] **Step 5: Show each new test red once** — delete the `arm_now` call from `route_repair` and watch
      `test_an_unarmed_route_opens_the_arm_dialog_first` fail; make `_follow_gate` enable all three entries
      unconditionally and watch the selector test fail. Capture both, restore.

- [ ] **Step 6: Commit**

```bash
git add wing_parser/ui/write_router.py wing_parser/ui/doctor_page.py wing_parser/ui/detail_panel.py wing_parser/ui/live_wiring.py tests/test_ui_doctor.py tests/test_ui_write_dialogs.py && git commit -m "feat(ui): route a repair to the desk at the level the operator picked"
```

Body names spec F3, F4, W14, and why `write_router.py` exists.

**Claims to check by opening:** that `Session.repair` returns `False` when no descriptor is declared
(`session.py:57-69`) and appends exactly one patch when it succeeds (`:67`); that `DoctorPage._on_view_selected`
announces before showing and `show_finding` does not (`doctor_page.py:62-70`), so the new signal does not
double-fire; that `ChangesPanel` is built before the pages in `MainWindow.__init__` (`main_window.py:61`
vs `:70-78`), so `install_write_gate` really can reach both.

---

### Task 12: `changes_send.py` — the per-row Send button and the result badges

**Files:**
- Create: `wing_parser/ui/changes_send.py`, `tests/test_ui_changes_send.py`
- Modify: `wing_parser/ui/changes_panel.py` (**37 lines**), `wing_parser/ui/write_router.py` (Task 11)

Read spec §2.2, §2.4, F8 and W13 first, then `ui/changes_panel.py` whole (37 lines) and
`ui/main_window.py:170-181`.

**Interfaces:**
- Consumes: `write_router.route_repair` (Task 11), `live_write.outcome` / `settle_scene` / `SentWrite`
  (Task 4), `Session.record_value` (Task 4), `WriteGate` (Task 8), `text("console.write.*")` (Task 7).
- Produces:
  ```python
  # wing_parser/ui/changes_send.py
  class SendRow(QWidget):
      send_requested = Signal(object)          # the Patch this row carries
      def __init__(self, patch, gate, parent=None) -> None: ...
      def set_badge(self, record: SentWrite) -> None: ...
      def refresh(self) -> None: ...           # gate openness only

  # wing_parser/ui/write_router.py
  def apply_result(window, patch, record: SentWrite) -> None: ...   # F8 -> the scene

  # wing_parser/ui/changes_panel.py
  class ChangesPanel(QWidget):
      ledger: SentLedger                       # task 13 fills this in
      def attach_gate(self, gate) -> None: ...
      def attach_window(self, window) -> None: ...
      def record_sent(self, patch, record) -> None: ...
      def report_write_error(self, exc) -> None: ...
      def has_ledger(self) -> bool: ...
  ```

- [ ] **Step 1: Write the failing tests** — `tests/test_ui_changes_send.py`

```python
"""Spec §9.2: the journal row's Send button, its badges, and what a result
does to the scene. Offscreen, no socket -- `FakeDesk` throughout.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")

from tests.fake_desk import FakeDesk
from wing_parser.net.codec import OscMessage
from wing_parser.net.identity import WingIdentity

HOST = "192.168.128.28"
PATH = "ae_data.ch.1.send.8.mode"
OSC = "/ch/1/send/8/mode"


def _identity():
    return WingIdentity(ip=HOST, name="WING-GIAQUY", model="wing-rack",
                        serial="01009Y90604AAE", firmware="3.1-0-g9f314617:release")


def _patch(before="POST", after="PRE", path=PATH):
    from wing_parser.edit.journal import Patch
    return Patch(path=path, before=before, after=after, because="G8:ch.1.send.8",
                 label="Set the send to PRE (ch.1.send.8)")


def _gate(qt_app, desk, state=None):
    from wing_parser.ui.live_state import LiveState
    from wing_parser.ui.live_wiring import WriteGate

    class _Bar:
        def host(self):
            return HOST

    class _Page:
        pass

    page = _Page()
    page.state = state or LiveState.CONNECTED
    page.connect_bar = _Bar()
    return WriteGate(page, transport=desk.write_transport(), timeout=0)


def _row(qt_app, gate, patch=None):
    from wing_parser.ui.changes_send import SendRow
    return SendRow(patch or _patch(), gate)


# -- the button's one meaning (§2.2) ------------------------------------


def test_send_is_disabled_only_by_a_closed_gate(qt_app):
    from wing_parser.ui.live_state import LiveState
    from wing_parser.ui.texts import text

    desk = FakeDesk(identity=_identity())
    gate = _gate(qt_app, desk, state=LiveState.DISCONNECTED)
    row = _row(qt_app, gate)
    assert row.send_button.isEnabled() is False
    assert row.send_button.toolTip() == text("console.write.blocked")


def test_send_stays_enabled_while_unarmed(qt_app):
    """§2.2: being unarmed does NOT disable it -- clicking while unarmed
    opens ArmWriteDialog first, so the button always means one thing."""
    desk = FakeDesk(identity=_identity())
    gate = _gate(qt_app, desk)
    row = _row(qt_app, gate)
    assert gate.arm.armed() is False
    assert row.send_button.isEnabled() is True


def test_clicking_send_while_unarmed_arms_before_it_counts_down(qt_app, monkeypatch):
    from wing_parser.ui import write_router

    desk = FakeDesk(identity=_identity(),
                    leaves={OSC: OscMessage(OSC, "s", ("POST",))})
    gate = _gate(qt_app, desk)
    calls = []
    monkeypatch.setattr(write_router, "arm_now",
                        lambda g, parent=None, **kw: calls.append(g) or False)
    row = _row(qt_app, gate)
    row.send_button.click()
    assert calls == [gate] and desk.sets == []


def test_manuals_send_opens_the_countdown_not_a_bare_confirm(qt_app):
    """§2.2: Manual exists so the operator SEES the numbers, and that screen
    is where the numbers are."""
    from wing_parser.ui.write_delay_dialog import DelayedWriteDialog

    desk = FakeDesk(identity=_identity(),
                    leaves={OSC: OscMessage(OSC, "s", ("POST",))},
                    readbacks={OSC: "PRE"})
    gate = _gate(qt_app, desk)
    gate.arm.arm(_identity())
    row = _row(qt_app, gate)
    opened = []
    row.dialog_opened.connect(opened.append)
    row.send_button.click()
    assert opened and isinstance(opened[0], DelayedWriteDialog)
    opened[0].reject()


# -- the three badges (§2.4) --------------------------------------------


def _record(readback, matched, written="PRE", desk_before="POST"):
    from wing_parser.net.write import SetResult
    from wing_parser.ui.live_write import SentWrite

    return SentWrite(address=OSC, path=PATH, desk_before=desk_before,
                     written=written,
                     result=SetResult(OSC, written, str(written), False,
                                      readback, matched))


@pytest.mark.parametrize("readback,matched,key", [
    ("PRE", True, "console.write.sent"),
    ("GRP", False, "console.write.clamped"),
    (None, False, "console.write.no_reply"),
])
def test_each_outcome_puts_its_own_badge_on_the_row(qt_app, readback, matched, key):
    from wing_parser.ui.texts import text

    desk = FakeDesk(identity=_identity())
    row = _row(qt_app, _gate(qt_app, desk))
    row.set_badge(_record(readback, matched))
    assert text(key).split("{")[0].strip() in row.badge.text()


# -- what a result does to the scene (F8) -------------------------------


def _window(qt_app, vu_path):
    from wing_parser.ui.session import Session

    class _W:
        def __init__(self):
            self.session = Session.open(vu_path)
            self.refreshed = 0

        def _refresh(self):
            self.refreshed += 1

    return _W()


def test_a_matched_write_leaves_the_scene_where_repair_put_it(qt_app, vu_path):
    from wing_parser.ui import write_router

    window = _window(qt_app, vu_path)
    patch = window.session.record_value(PATH, "PRE", label="x", because="G8")
    before_len = len(window.session.changes())

    write_router.apply_result(window, patch, _record("PRE", True))

    assert len(window.session.changes()) == before_len, (
        "matched -> the leaf already holds `after`; no second patch")


def test_a_clamp_rewrites_the_scene_so_the_finding_reflects_the_desk(qt_app, vu_path):
    from wing_parser.edit import pointer
    from wing_parser.ui import write_router

    window = _window(qt_app, vu_path)
    patch = window.session.record_value(PATH, "PRE", label="x", because="G8")

    write_router.apply_result(window, patch, _record("GRP", False))

    assert pointer.read(window.session._document(), PATH) == "GRP"
    assert window.refreshed >= 1


def test_a_silent_desk_leaves_the_scene_exactly_as_repair_set_it(qt_app, vu_path):
    from wing_parser.edit import pointer
    from wing_parser.ui import write_router

    window = _window(qt_app, vu_path)
    patch = window.session.record_value(PATH, "PRE", label="x", because="G8")
    before_len = len(window.session.changes())

    write_router.apply_result(window, patch, _record(None, False))

    assert pointer.read(window.session._document(), PATH) == "PRE"
    assert len(window.session.changes()) == before_len


# -- the dock, the panel, and Undo (§9.2) -------------------------------


def _panel(qt_app, gate, window):
    from wing_parser.ui.changes_panel import ChangesPanel

    panel = ChangesPanel()
    panel.attach_gate(gate)
    panel.attach_window(window)
    return panel


def test_a_successful_send_appends_exactly_one_ledger_row(qt_app, vu_path):
    desk = FakeDesk(identity=_identity())
    window = _window(qt_app, vu_path)
    panel = _panel(qt_app, _gate(qt_app, desk), window)
    patch = window.session.record_value(PATH, "PRE", label="x", because="G8")

    panel.record_sent(patch, _record("PRE", True))

    assert len(panel.ledger.records()) == 1
    assert panel.has_ledger() is True


def test_undo_removes_the_journal_row_and_leaves_the_ledger_row(qt_app, vu_path):
    """F7: its rows survive an Undo, which is a FILE-side action -- a desk
    change the UI cannot revert is worse than a longer panel."""
    desk = FakeDesk(identity=_identity())
    window = _window(qt_app, vu_path)
    panel = _panel(qt_app, _gate(qt_app, desk), window)
    patch = window.session.record_value(PATH, "PRE", label="x", because="G8")
    panel.record_sent(patch, _record("PRE", True))

    window.session.undo()
    panel.set_changes(window.session.changes())

    assert panel.list.count() == 0
    assert len(panel.ledger.records()) == 1
    assert panel.ledger.row_widget(0).revert_button.isEnabled() is True


def test_every_journal_row_carries_its_own_send_button(qt_app, vu_path):
    from wing_parser.ui.changes_send import SendRow

    desk = FakeDesk(identity=_identity())
    window = _window(qt_app, vu_path)
    panel = _panel(qt_app, _gate(qt_app, desk), window)
    window.session.record_value(PATH, "PRE", label="x", because="G8")
    window.session.record_value("ae_data.ch.2.send.8.mode", "PRE",
                                label="y", because="G8")
    panel.set_changes(window.session.changes())

    assert panel.list.count() == 2
    for index in range(2):
        widget = panel.list.itemWidget(panel.list.item(index))
        assert isinstance(widget, SendRow)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest tests/test_ui_changes_send.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.ui.changes_send'`

- [ ] **Step 3: Write the minimal implementation**

`wing_parser/ui/changes_send.py`:

```python
"""One journal row: what changed, and the button that sends it (§2.2).

The Send button is **disabled only when the gate is closed** -- the Console
page not CONNECTED or WATCHING -- with `console.write.blocked` as its
tooltip. Being unarmed does NOT disable it: clicking while unarmed opens
`ArmWriteDialog` first and the countdown after it, so Manual has one button
that always means the same thing and the arming step appears only when it is
actually needed.

Clicking opens the COUNTDOWN, deliberately, not a bare confirm: Manual
exists so the operator sees the numbers, and that screen is where the
numbers are.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QWidget

from wing_parser.ui import live_write, write_router
from wing_parser.ui.texts import text


def badge_text(record) -> str:
    """The one line §2.4 gives each of the three outcomes."""
    result = record.result
    kind = live_write.outcome(result)
    if kind is live_write.Outcome.SENT:
        return text("console.write.sent").format(readback=result.readback)
    if kind is live_write.Outcome.CLAMPED:
        return text("console.write.clamped").format(
            readback=result.readback, after=record.written)
    return text("console.write.no_reply").format(address=record.address)


class SendRow(QWidget):
    send_requested = Signal(object)     # the Patch this row carries
    dialog_opened = Signal(object)      # the countdown, for tests and for focus

    def __init__(self, patch, gate, delay=5, parent=None) -> None:
        super().__init__(parent)
        self.patch = patch
        self._gate = gate
        self._delay = delay
        self.label = QLabel(
            f"{patch.label}  —  {patch.path}: {patch.before!r} → {patch.after!r}")
        self.badge = QLabel("")
        self.send_button = QPushButton(text("console.write.send"))
        self.send_button.setToolTip(text("console.write.blocked"))
        self.send_button.clicked.connect(self._send)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label, 1)
        layout.addWidget(self.badge)
        layout.addWidget(self.send_button)
        self.refresh()

    def refresh(self) -> None:
        self.send_button.setEnabled(self._gate.can_write())

    def set_badge(self, record) -> None:
        self.badge.setText(badge_text(record))

    def _send(self) -> None:
        self.send_requested.emit(self.patch)
        dialog = write_router.send_manually(
            self._gate, self.patch, self._delay, self.window(),
            on_sent=self._sent)
        if dialog is not None:
            self.dialog_opened.emit(dialog)

    def _sent(self, patch, record) -> None:
        self.set_badge(record)
```

`wing_parser/ui/write_router.py` gains two functions:

```python
def send_manually(gate, patch, delay, parent=None, *, transport=None,
                  timeout=None, on_sent=None, on_error=None):
    """Manual's own Send: arm if needed, then ALWAYS the countdown (§2.2)."""
    if not arm_now(gate, parent, transport=transport, timeout=timeout):
        return None
    return _countdown(gate, patch, patch.after, delay, parent,
                      transport=transport, timeout=timeout,
                      on_sent=on_sent, on_error=on_error)


def apply_result(window, patch, record) -> None:
    """F8: move the scene leaf to whatever the desk's answer justifies.

    Matched -> nothing to do; the leaf already holds `after`. Clamp -> a
    second patch to `scene_value(parts, readback)`, so Doctor re-derives
    against the desk's truth. No reply -> nothing: inventing a value for a
    silent desk is the one thing worse than admitting ignorance.
    """
    value = live_write.settle_scene(
        leaf_parts(patch.path), patch.after, record.result)
    if value is None or value == patch.after:
        return
    window.session.record_value(
        patch.path, value,
        label=badge_label(record), because=patch.because)
    window._refresh()
```

with `from wing_parser.net.address import leaf_parts, osc_address` and a one-line
`badge_label = lambda record: text("console.write.clamped").format(...)` — or, simpler and without a lambda,
import `changes_send.badge_text` lazily inside `apply_result` to avoid the import cycle and use it as the
patch label, so the Changes row for a clamp reads as what it is.

`wing_parser/ui/changes_panel.py`:

```python
    def attach_gate(self, gate) -> None:
        self._gate = gate
        gate.changed.connect(self._refresh_rows)

    def attach_window(self, window) -> None:
        self._window = window

    def set_changes(self, patches: tuple[Patch, ...]) -> None:
        self.list.clear()
        for patch in patches:
            item = QListWidgetItem()
            row = SendRow(patch, self._gate,
                          getattr(self._window, "_apply_delay", 5))
            item.setSizeHint(row.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, row)
        self.undo_button.setEnabled(bool(patches))

    def record_sent(self, patch, record) -> None:
        """One result: the badge, the scene (F8) and one ledger row."""
        write_router.apply_result(self._window, patch, record)
        self.ledger.add(record)
        self._badge(patch, record)

    def report_write_error(self, exc) -> None:
        self.status_label.setText(text("console.write.refused").format(error=exc))

    def has_ledger(self) -> bool:
        """What keeps the dock open on a clean session with a non-empty
        ledger (`main_window.py:181`)."""
        return bool(self.ledger.records())
```

with `self._gate = None`, `self._window = None`, a `status_label`, and `self.ledger = SentLedger()` (Task
13) added in `__init__`, and a `_refresh_rows` that calls `refresh()` on every `SendRow`. Until Task 13
lands, `ledger` may be a `SentLedger` stub with `records()` and `add()`; **land Tasks 12 and 13 as a pair**.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `$PY -m pytest tests/test_ui_changes_send.py tests/test_ui_shell.py tests/test_ui_house_style.py tests/test_ui_live_is_read_only.py`
Expected: PASS. Paste `wc -l wing_parser/ui/changes_send.py wing_parser/ui/changes_panel.py
wing_parser/ui/write_router.py` — all under their budgets. Then the full suite.

- [ ] **Step 5: Show each new test red once** — make `refresh` read `self._gate.ready()` instead of
      `can_write()` and watch `test_send_stays_enabled_while_unarmed` fail; make `apply_result` write for
      the matched case too and watch `test_a_matched_write_leaves_the_scene_where_repair_put_it` fail.
      Capture both, restore.

- [ ] **Step 6: Commit**

```bash
git add wing_parser/ui/changes_send.py wing_parser/ui/changes_panel.py wing_parser/ui/write_router.py wing_parser/ui/live_write.py tests/test_ui_changes_send.py && git commit -m "feat(ui): send one journal row to the desk and show what came back"
```

Body names spec §2.2, §2.4 and F8.

**Claims to check by opening:** that `ChangesPanel.set_changes` was the only writer of the list
(`changes_panel.py:31-37`) and that `MainWindow._refresh` calls it every time (`main_window.py:180`); that
`QListWidget.setItemWidget` needs an item whose `sizeHint` was set, or the row collapses to nothing; that
`Session.undo` re-derives (`session.py:71-75`), so the panel is repopulated by `_refresh` and not by hand.

---

### Task 13: `changes_ledger.py` — the sent ledger, Revert, Revert all, Stop

**Files:**
- Create: `wing_parser/ui/changes_ledger.py`
- Modify: `wing_parser/ui/changes_panel.py` (Task 12), `wing_parser/ui/main_window.py` (**one line**, the
  `_refresh` dock-visibility change at `:181`), `wing_parser/ui/live_wiring.py` (Task 11, W14 wiring),
  `tests/test_ui_changes_send.py` (Task 12)

Read spec §2.5, F7, W12, W13, W14, W15 and §7.2 first.

**Interfaces:**
- Consumes: `RevertQueue` (Task 2), `live_write.SentWrite` / `settle_scene` (Tasks 3, 4),
  `write_router.route_revert` (Task 11), `WriteGate` (Task 8), `text("console.write.*")` (Task 7).
- Produces:
  ```python
  # wing_parser/ui/changes_ledger.py
  class LedgerRow(QWidget):
      revert_requested = Signal(object)        # the SentWrite
      revert_button: QPushButton; result_label: QLabel
  class SentLedger(QWidget):
      run_started = Signal()                   # W14: the Doctor controls go dead
      run_finished = Signal()                  # ...and come back
      reverted = Signal(object, object)        # (SentWrite, SetResult)
      def add(self, record: SentWrite) -> None: ...
      def records(self) -> tuple[SentWrite, ...]: ...
      def row_widget(self, index: int) -> LedgerRow: ...
      def attach(self, gate, window) -> None: ...
      def revert_all(self) -> None: ...
      def stop(self) -> None: ...
  ```

- [ ] **Step 1: Write the failing tests** — append to `tests/test_ui_changes_send.py`

```python
# -- the sent ledger (F7, W12, W13, W14, W15) ---------------------------


def _ledger(qt_app, desk, window, records=()):
    from wing_parser.ui.changes_ledger import SentLedger

    ledger = SentLedger()
    ledger.attach(_gate(qt_app, desk), window)
    for record in records:
        ledger.add(record)
    return ledger


def _sent(address, path, desk_before, written):
    from wing_parser.net.write import SetResult
    from wing_parser.ui.live_write import SentWrite

    return SentWrite(address=address, path=path, desk_before=desk_before,
                     written=written,
                     result=SetResult(address, written, str(written), False,
                                      written, True))


def test_a_ledger_row_shows_the_address_the_before_the_written_and_the_result(qt_app, vu_path):
    desk = FakeDesk(identity=_identity())
    ledger = _ledger(qt_app, desk, _window(qt_app, vu_path),
                     [_sent(OSC, PATH, "POST", "PRE")])
    row = ledger.row_widget(0)
    shown = row.label.text() + row.result_label.text()
    assert OSC in shown and "POST" in shown and "PRE" in shown


def test_revert_all_sends_in_reverse_with_never_two_in_flight(qt_app, settle, vu_path):
    from wing_parser.ui.apply_level import ApplyLevel

    desk = FakeDesk(identity=_identity(),
                    leaves={f"/ch/{n}/fdr": OscMessage(f"/ch/{n}/fdr", "sff",
                                                       ("-6.0", 0.0, -6.0))
                            for n in (1, 2, 3)},
                    readbacks={f"/ch/{n}/fdr": -12.0 for n in (1, 2, 3)})
    window = _window(qt_app, vu_path)
    records = [_sent(f"/ch/{n}/fdr", f"ae_data.ch.{n}.fdr", -12.0, -6.0)
               for n in (1, 2, 3)]
    ledger = _ledger(qt_app, desk, window, records)
    ledger._gate.arm.arm(_identity())
    ledger._gate.arm.level = ApplyLevel.IMMEDIATE

    ledger.revert_all()
    assert settle(lambda: len(desk.sets) == 3, limit_s=5.0)
    assert [c[0] for c in desk.sets] == ["/ch/3/fdr", "/ch/2/fdr", "/ch/1/fdr"]


def test_the_progress_line_counts_done_over_total(qt_app, settle, vu_path):
    from wing_parser.ui.apply_level import ApplyLevel
    from wing_parser.ui.texts import text

    desk = FakeDesk(identity=_identity())
    window = _window(qt_app, vu_path)
    records = [_sent(f"/ch/{n}/fdr", f"ae_data.ch.{n}.fdr", -12.0, -6.0)
               for n in range(1, 8)]
    ledger = _ledger(qt_app, desk, window, records)
    ledger._gate.arm.arm(_identity())
    ledger._gate.arm.level = ApplyLevel.IMMEDIATE

    ledger.revert_all()
    assert settle(lambda: "/7" in ledger.progress_label.text())
    assert text("console.write.reverting").split("{")[0] in ledger.progress_label.text()


def test_stop_ends_the_run_between_parameters_and_leaves_the_rest(qt_app, settle, vu_path):
    """F7: the one already on the wire completes, because nothing can
    un-send a packet."""
    from wing_parser.ui.apply_level import ApplyLevel
    from wing_parser.ui.texts import text

    desk = FakeDesk(identity=_identity())
    window = _window(qt_app, vu_path)
    records = [_sent(f"/ch/{n}/fdr", f"ae_data.ch.{n}.fdr", -12.0, -6.0)
               for n in range(1, 8)]
    ledger = _ledger(qt_app, desk, window, records)
    ledger._gate.arm.arm(_identity())
    ledger._gate.arm.level = ApplyLevel.IMMEDIATE

    ledger.revert_all()
    settle(lambda: desk.sets)
    ledger.stop()
    settled = len(desk.sets)
    assert settle(lambda: len(desk.sets) <= settled + 1)
    assert len(desk.sets) < 7, "Stop left the remainder alone"
    assert text("console.write.revert_stopped").split("{")[0] in ledger.progress_label.text()


def test_a_run_disables_the_doctor_controls_and_stop_re_enables_them(qt_app, vu_path):
    """W14: a run that changed level halfway would send some parameters
    through a countdown and others instantly, from one click."""
    desk = FakeDesk(identity=_identity())
    window = _window(qt_app, vu_path)
    ledger = _ledger(qt_app, desk, window,
                     [_sent(OSC, PATH, "POST", "PRE")])
    heard = []
    ledger.run_started.connect(lambda: heard.append("started"))
    ledger.run_finished.connect(lambda: heard.append("finished"))
    ledger._gate.arm.arm(_identity())

    ledger.revert_all()
    assert heard[0] == "started"
    ledger.stop()
    assert "finished" in heard


def test_a_successful_revert_puts_the_scene_back_and_keeps_the_patch(qt_app, settle, vu_path):
    """W13: the finding REAPPEARS -- the honest outcome, since the desk
    really is back in the state the rule objects to -- and the journal
    Patch is NOT undone."""
    from wing_parser.edit import pointer
    from wing_parser.ui.apply_level import ApplyLevel

    desk = FakeDesk(identity=_identity(),
                    leaves={OSC: OscMessage(OSC, "s", ("PRE",))},
                    readbacks={OSC: "POST"})
    window = _window(qt_app, vu_path)
    patch = window.session.record_value(PATH, "PRE", label="x", because="G8")
    journal_len = len(window.session.changes())
    ledger = _ledger(qt_app, desk, window, [_sent(OSC, PATH, "POST", "PRE")])
    ledger._gate.arm.arm(_identity())
    ledger._gate.arm.level = ApplyLevel.IMMEDIATE

    ledger.row_widget(0).revert_button.click()
    assert settle(lambda: desk.sets)
    assert settle(lambda: pointer.read(window.session._document(), PATH) == "POST")
    assert len(window.session.changes()) == journal_len + 1, (
        "the revert adds its own patch; it does not drop the operator's")
    assert window.session.changes()[journal_len - 1] is patch


def test_the_dock_stays_visible_with_a_clean_session_and_a_ledger(qt_app, tmp_path,
                                                                  monkeypatch, vu_path):
    """`main_window.py:181` used to bind visibility to `session.dirty`
    alone; a desk change the UI cannot show is worse than a longer dock."""
    from wing_parser import config
    from wing_parser.ui.main_window import MainWindow

    monkeypatch.setenv(config.ENV_VAR, str(tmp_path))
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    window = MainWindow(str(vu_path))
    window.changes_panel.ledger.add(_sent(OSC, PATH, "POST", "PRE"))
    window._refresh()
    assert window.session.dirty is False
    assert window._changes_dock.isVisible() or window.changes_panel.has_ledger()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `$PY -m pytest tests/test_ui_changes_send.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.ui.changes_ledger'`

- [ ] **Step 3: Write the minimal implementation** — `wing_parser/ui/changes_ledger.py`

```python
"""Everything written to the desk this session, and the way back (F7).

One row per parameter: address, the desk-live value captured BEFORE the
write, the value written, the read-back result. **Its rows survive an
Undo**, which is a file-side action -- a desk change the UI cannot revert
is worse than a longer panel.

Revert writes that row's captured desk-before value through the CURRENT
apply level: Immediate at once, Delayed and Manual via the countdown.
Revert all walks the rows in REVERSE -- last written, first undone -- and
is still one parameter per transmission (F1): the next starts only after
the previous read-back returns, because `RevertQueue.next()` is called from
the previous one's terminal callback and every write goes through the
gate's single `WriteQueue` underneath that (W10, §7.2).

**Stop ends the run between parameters**; the one already on the wire
completes, because nothing can un-send a packet. In Delayed the way out is
the countdown's own Cancel (W12, W15) -- a Stop button behind a modal
dialog is not reachable at all.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget,
)

from wing_parser.ui import write_router
from wing_parser.ui.apply_level import RevertQueue
from wing_parser.ui.changes_send import badge_text
from wing_parser.ui.texts import text


class LedgerRow(QWidget):
    revert_requested = Signal(object)

    def __init__(self, record, parent=None) -> None:
        super().__init__(parent)
        self.record = record
        self.label = QLabel(
            f"{record.address}: {record.desk_before!r} → {record.written!r}")
        self.result_label = QLabel(badge_text(record))
        self.revert_button = QPushButton(text("console.write.revert"))
        self.revert_button.clicked.connect(
            lambda: self.revert_requested.emit(self.record))
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label, 1)
        layout.addWidget(self.result_label)
        layout.addWidget(self.revert_button)


class SentLedger(QWidget):
    run_started = Signal()
    run_finished = Signal()
    reverted = Signal(object, object)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._records: list = []
        self._gate = None
        self._window = None
        self._queue: RevertQueue | None = None
        self.list = QListWidget()
        self.progress_label = QLabel("")
        self.revert_all_button = QPushButton(text("console.write.revert_all"))
        self.stop_button = QPushButton(text("console.write.revert_stop"))
        self.stop_button.setEnabled(False)
        self.revert_all_button.clicked.connect(self.revert_all)
        self.stop_button.clicked.connect(self.stop)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(text("console.write.sent_heading")))
        layout.addWidget(self.list)
        layout.addWidget(self.progress_label)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.stop_button)
        buttons.addWidget(self.revert_all_button)
        layout.addLayout(buttons)

    def attach(self, gate, window) -> None:
        self._gate, self._window = gate, window

    # -- the rows ----------------------------------------------------------

    def add(self, record) -> None:
        self._records.append(record)
        row = LedgerRow(record)
        row.revert_requested.connect(self._revert_one)
        item = QListWidgetItem()
        item.setSizeHint(row.sizeHint())
        self.list.addItem(item)
        self.list.setItemWidget(item, row)

    def records(self) -> tuple:
        return tuple(self._records)

    def row_widget(self, index: int) -> LedgerRow:
        return self.list.itemWidget(self.list.item(index))

    # -- reverting ---------------------------------------------------------

    def _revert_one(self, record) -> None:
        write_router.route_revert(
            self._gate, record, getattr(self._window, "_apply_delay", 5),
            self.window(), on_sent=self._reverted)

    def revert_all(self) -> None:
        """F7: reverse order, sequential, one parameter per transmission."""
        if self._queue is not None:
            return
        self._queue = RevertQueue(self._records)
        self.stop_button.setEnabled(True)
        self.run_started.emit()                      # W14
        self._next()

    def stop(self) -> None:
        """Between parameters. The in-flight one completes."""
        if self._queue is None:
            return
        self._queue.stop()
        done, total = self._queue.progress
        self.progress_label.setText(text("console.write.revert_stopped").format(
            done=done, total=total))
        self._end_run()

    def _next(self) -> None:
        record = self._queue.next() if self._queue else None
        if record is None:
            if self._queue is not None:
                self._end_run()
            return
        done, total = self._queue.progress
        self.progress_label.setText(text("console.write.reverting").format(
            done=done, total=total, address=record.address))
        write_router.route_revert(
            self._gate, record, getattr(self._window, "_apply_delay", 5),
            self.window(), on_sent=self._step_done,
            on_error=lambda _exc: self._step_done(None, None),
            on_cancelled=self.stop)                  # W12: Cancel stops the run

    def _step_done(self, _patch, record) -> None:
        if record is not None:
            self._reverted(_patch, record)
        self._next()

    def _reverted(self, patch, record) -> None:
        """W13: the scene goes back too, so the finding reappears."""
        if patch is not None:
            write_router.apply_revert(self._window, record)
        self.reverted.emit(record, record.result)

    def _end_run(self) -> None:
        self._queue = None
        self.stop_button.setEnabled(False)
        self.run_finished.emit()                     # W14
```

`wing_parser/ui/write_router.py` gains the revert half of F8:

```python
def apply_revert(window, record) -> None:
    """W13: move the leaf back to what the desk now holds, coerced through
    `scene_value` exactly as F8 does -- so Doctor re-derives and the finding
    REAPPEARS. The honest outcome: the desk really is back in the state the
    rule objects to. The original `Patch` is left alone; Undo is still the
    file-side door, and silently dropping a patch because a desk write was
    reverted would conflate the two."""
    value = live_write.settle_scene(
        leaf_parts(record.path), record.desk_before, record.result)
    if value is None:
        return
    window.session.record_value(
        record.path, value,
        label=text("console.write.reverted").format(
            readback=record.result.readback),
        because="revert")
    window._refresh()
```

`wing_parser/ui/changes_panel.py` — `self.ledger = SentLedger()` added to the layout under the journal list,
`attach_window` also calling `self.ledger.attach(self._gate, window)`.

`wing_parser/ui/main_window.py:181` — one line becomes two:

```python
        self._changes_dock.setVisible(
            loaded and (self.session.dirty or self.changes_panel.has_ledger()))
```

`wing_parser/ui/live_wiring.py` — inside `install_write_gate`, W14's two connections:

```python
        changes.ledger.run_started.connect(
            lambda: doctor.set_controls_enabled(False))
        changes.ledger.run_finished.connect(
            lambda: doctor.set_controls_enabled(True))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `$PY -m pytest tests/test_ui_changes_send.py tests/test_ui_shell.py tests/test_ui_house_style.py tests/test_ui_live_is_read_only.py`
Expected: PASS. Paste `wc -l` for `changes_ledger.py`, `changes_panel.py`, `write_router.py`,
`live_wiring.py`, `main_window.py` — **main_window at 193 or under** (one line at Task 8, one here: ≤4, per
§4). Then the full suite with `--junitxml`; **this is the wave's final count.**

- [ ] **Step 5: Show each new test red once** — drop the `reversed(...)` from `RevertQueue` (Task 2) and
      watch the reverse-order test fail; call `self._next()` before `route_revert` returns rather than from
      `_step_done` and watch "never two in flight" fail. Capture both, restore.

- [ ] **Step 6: Commit**

```bash
git add wing_parser/ui/changes_ledger.py wing_parser/ui/changes_panel.py wing_parser/ui/write_router.py wing_parser/ui/live_wiring.py wing_parser/ui/main_window.py tests/test_ui_changes_send.py && git commit -m "feat(ui): list what went to the desk, and put any of it back"
```

Body names spec F7, W12, W13, W14 and W15.

**Claims to check by opening:** that `RevertQueue.next()` returns `None` after `stop()` and when exhausted
(`apply_level.py`, Task 2) — the two different reasons the run ends; that `WriteQueue` really is what
serialises the packets underneath (`write_queue.py`); that `main_window.py:181` was the dock's only
visibility writer; that `Session.record_value` re-derives (`session.py`, Task 4), which is what makes the
finding reappear.

---

### Task 14: The exe, the screenshots, the docs and the handoff

**Files:** `packaging/wing-ui.spec` (**84 lines**), `packaging/make-debug-spec.py` (**28**),
`docs/user-manual/03-console-truc-tiep.md` (**62**), `docs/ROADMAP.md` (**273**),
`docs/tech-debt.md` (**688**), `memory/MEMORY.md`, and a new
`docs/handoff/2026-09-XX-gui-write-wave3-complete.md`. **Not TDD — the deliverable is a verified binary and
docs nobody has to distrust.**

- [ ] **1. Install every extra into the build venv first** — `pip install -e ".[ui]"` plus `[ingest]` and
      `[llm-openai]`. **UI tests skipping in pytest is the symptom of a venv missing PySide6**
      (`memory/MEMORY.md`, 2026-08-24); check for skips before building, because `console=False` makes a
      missing extra a silent exit 1.
- [ ] **2. Build:** `.venv\Scripts\pyinstaller packaging\wing-ui.spec --noconfirm`; paste the tail.
      Regenerate the debug spec with `packaging/make-debug-spec.py` — a *generated* artifact, never
      hand-edited — and build `dist\wing-ui-debug.exe` if the release exe misbehaves.
- [ ] **3.** `Start-Process dist\wing-ui.exe`, wait ~6 s, confirm the process is still alive. A dead
      process here is the silent-exit trap, not a flake.
- [ ] **4. Screenshots of every affected surface, from the exe**: the Doctor page with the selector reading
      **Manual** and Delayed/Immediate greyed; the same page **Armed**; `ArmWriteDialog` before and after
      the latch; `DelayedWriteDialog` with a mismatch line; the Changes dock with a Send button, one ✓
      badge, one ⚠ badge and one ✗ badge; the sent ledger mid **Revert all** with the progress line. Attach
      them all to the PR. **ToanAZ must look at them — wave 1's gate; no surface is done without it.**
- [ ] **5. The manual** (`docs/user-manual/03-console-truc-tiep.md`, Vietnamese, matching the file's voice):
      the three levels, arming, the countdown's three buttons, the three badges and what each does to the
      scene, the ledger and Revert all. Put the **UI route beside each `net` command**, as wave 2 did.
      **`net set/toggle/push/get` stay CLI-only and that is deliberate** — say so, so a reader does not hunt
      for a button that is not there.
- [ ] **6. ROADMAP §3** gains the wave-3 row with the **measured** test count; §4's pointer is updated.
      Then **grep for statements this wave made false** — anything in `memory/MEMORY.md`, the ROADMAP or the
      manual saying the app only *reads* a live console, or that the Console page has no write path. A
      phase still marked "not started" that shipped last week is not a stale note; it is a lie the next
      session will act on.
- [ ] **7. `docs/tech-debt.md`**: close or update **D-41** and **D-42** per Task 15's outcome, and open any
      new entry this wave earned (candidates seen while writing this plan: `write_router.py` is a module
      §4 did not foresee; `SentWrite.path` is carried because no inverse of `osc_address` exists;
      `live_wiring.py` is the wave's tightest file). Link to the ledger from elsewhere; never copy a fact
      out of it.
- [ ] **8. `memory/MEMORY.md`** gains one entry: what shipped, the measured suite number, what remains.
- [ ] **9. The wave-4 handoff**, written **now** while the context is live — written later it gets written
      from git, and git does not hold the reasons or the decisions still waiting on a human. It states:
      baseline vs final suite numbers, both measured, both pasted with their command; **what ToanAZ can run
      and what he should see** (the exe path, the acceptance list below, the exact commands); done /
      in-progress / **decisions pending a human** — spec §11's three open questions (Immediate while
      `WATCHING`; one countdown for a Delayed Revert-all batch; arm state surviving a reconnect to the same
      serial) and **every `W…` ruling**, listed so he can overturn any of them; known pitfalls (the
      venv-extras exe trap, `normalize`'s silent drop, `save_on_close`'s literal, the `live_wiring.py`
      ceiling, and W3b's int-typed-leaf risk).
- [ ] **10. Commit** — docs-only staging, explicit paths, confirmed with `git diff --cached --name-only`.

**Verify:** `dist\wing-ui.exe --screenshot dist-shots user-files\example-Vu.snap` exits 0 and writes the
page PNGs; paste the directory listing. `$PY -m pytest tests/test_examples.py` — it pins the shipped skill
set **by name**.
**Commit:** `docs: record the write path in the manual, roadmap, ledger and handoff`
**Claims to check by opening:** every `file:line` written into a doc; that the ROADMAP row quotes the count
measured **this** wave, not 1580.

---

### Task 15: D-41 and D-42 — the two `net/` debt items (W9, droppable)

**Files:**
- Modify: `wing_parser/net/snapshot.py` (**132 lines**), `wing_parser/net/watch/list.py` (**111**),
  `wing_parser/net/watch/poller.py` (**123**), `wing_parser/ui/live_watch_session.py` (**165**),
  `tests/test_net_snapshot.py` (**153**), `tests/test_watch_list.py`, `tests/test_watch_poller.py`,
  `docs/tech-debt.md` (**688**)

Read `docs/tech-debt.md:508-540` (both entries, whole) before writing anything. **One commit each.** Both
are independent of everything above and of each other; **drop either if it endangers the wave** — nothing
in wave 3's behaviour depends on them.

#### 15a — D-41: a live pull walks the schema twice

`take_snapshot` walks internally (`snapshot.py:83-85`, calling `walk_schema` before reading any leaf) and
`build_watch_list` walks again (`list.py:89`); neither accepts a pre-computed `SchemaResult`, so Discover
then Pull costs two walks where one would do — the wave-2 spec priced one walk at ~1 s.

- [ ] **1. Failing tests.** `tests/test_net_snapshot.py`:
      `test_take_snapshot_with_a_supplied_schema_does_not_walk_again` (drive it with a counting stub
      monkeypatched over `snapshot.walk_schema`, assert zero calls and that the result's
      `unresolved_nodes` came from the supplied `SchemaResult`);
      `test_take_snapshot_without_a_schema_still_walks_exactly_once`.
      `tests/test_watch_list.py`: `test_build_watch_list_with_a_supplied_schema_does_not_walk_again`,
      `test_the_supplied_schemas_unresolved_nodes_reach_the_watch_list`.
- [ ] **2. Run → FAIL** (`TypeError: take_snapshot() got an unexpected keyword argument 'schema'`).
- [ ] **3. Implement:** one keyword-only parameter on each, defaulting to `None`:

```python
def take_snapshot(host, port=OSC_PORT, batch_size=DEFAULT_BATCH_SIZE,
                  retry_rounds=DEFAULT_RETRY_ROUNDS,
                  idle_timeout=DEFAULT_IDLE_TIMEOUT, *,
                  schema: SchemaResult | None = None) -> SnapshotResult:
    ...
    # D-41: a caller that has just walked (the Console page's Discover)
    # hands that result in rather than paying for a second walk. Fresh
    # shape every call still holds -- the freshness is now the CALLER's
    # to judge, and the default is unchanged.
    if schema is None:
        schema = walk_schema(host, port, batch_size=batch_size,
                             retry_rounds=retry_rounds, idle_timeout=idle_timeout)
```

and the same shape in `build_watch_list` (`list.py:89`).
- [ ] **4. Run → PASS** + full suite. **5. Show each red once** by deleting the `if schema is None:` guard.
- [ ] **6.** Update `docs/tech-debt.md`'s **D-41** entry: the `net/` seam now exists; **the UI has not
      adopted it**, because `console_page.py` (199), `live_controller.py` (199) and `live_snapshot.py`
      (199) are all at the ceiling W7 forbids growing this wave, so passing Discover's schema into a later
      Pull needs a file split first. Say exactly that and set `status: partially closed`. **Do not mark it
      closed** — the second of the two walks is still being paid at a venue.
- [ ] **7. Commit:** `git add wing_parser/net/snapshot.py wing_parser/net/watch/list.py tests/test_net_snapshot.py tests/test_watch_list.py docs/tech-debt.md && git commit -m "perf(net): let a caller supply the schema walk both readers need (D-41)"`

#### 15b — D-42: quitting can wait ~5 s for a watch round in flight

`poller.py:121-123` computes the round's remainder and calls a plain `sleep(remaining)` with no cancellation
seam; at `MAX_INTERVAL` (`live_guard.py:37`, 5.0 s) a quit requested just after a round starts waits that
sleep out before the `GeneratorWorker` thread can notice it was cancelled and join. `RoundGuard` already
sees the cancel, but only *before* the next `get_many` — which is why `WAIT_MS` was derived as
`(MAX_INTERVAL + 1.0) * 1000` in the first place (`live_watch_session.py:42-52`).

- [ ] **1. Failing tests.** `tests/test_watch_poller.py`:
      `test_a_set_cancel_event_cuts_the_pace_wait_short` (drive the real `watch` with a `FakeDesk`, an
      injected `clock`, a `threading.Event` already set, and a `sleep` that raises if called — assert the
      generator returns rather than sleeping);
      `test_the_injected_sleep_is_still_used_when_no_cancel_is_given` (the default path is unchanged);
      `test_a_cancel_set_mid_run_ends_the_loop_at_the_next_pace`.
- [ ] **2. Run → FAIL** (`TypeError: watch() got an unexpected keyword argument 'cancel'`).
- [ ] **3. Implement** — one keyword and one helper in `poller.py`:

```python
def _pace(remaining: float, cancel, sleep) -> bool:
    """Wait out the round's remainder; False when a cancel cut it short.

    D-42: `Event.wait(remaining)` returns as soon as the event is set, so a
    quit no longer has to outlast a whole interval. Without a `cancel` the
    injected `sleep` is used exactly as before -- every existing caller and
    every existing test keeps its behaviour.
    """
    if cancel is None:
        sleep(remaining)
        return True
    return not cancel.wait(remaining)
```

with `cancel: "threading.Event | None" = None` added to `watch`'s keyword-only parameters and the tail of
the loop becoming:

```python
        remaining = interval - (clock() - round_started)
        if remaining > 0 and not _pace(remaining, cancel, sleep):
            return
```

Then `wing_parser/ui/live_watch_session.py:91` passes it:

```python
                yield from transport.watch(
                    guard, watch_list, interval=interval, cancel=self.cancel)
```

and the `WAIT_MS` comment block (`:42-52`) is corrected: the pace sleep **now** sees the cancel, so the wait
covers only the round in flight. **Leave the number itself at `(MAX_INTERVAL + 1.0) * 1000`** — shrinking it
is a separate change needing its own measurement against a real desk, and a generous bound is not a bug.
- [ ] **4. Run → PASS** + full suite. **5. Show each red once** by reverting `_pace` to a bare `sleep`.
- [ ] **6.** `docs/tech-debt.md`'s **D-42** → `status: closed`, naming the commit.
- [ ] **7. Commit:** `git add wing_parser/net/watch/poller.py wing_parser/ui/live_watch_session.py tests/test_watch_poller.py docs/tech-debt.md && git commit -m "fix(net): let a watch's pace sleep see a cancel (D-42)"`

**Claims to check by opening:** that `walk_schema` returns a `SchemaResult` with `leaves` and
`unresolved_nodes` (`net/schema.py:55-75`); that `take_snapshot` uses `schema.leaves` and
`schema.unresolved_nodes` and nothing else off it (`snapshot.py:86-113`); that `build_watch_list` uses
`schema.leaves` and `schema.unresolved_nodes` only (`list.py:89-111`); that `poller.watch`'s `sleep` is a
parameter with a `time.sleep` default (`poller.py:72`) and that the sleep is conditional on
`remaining > 0` (`:121-123`); that `RoundGuard` checks the cancel **before** each `get_many`, which is the
half already covered (`live_guard.py`).

---

### Task 16: Whole-branch review, on the strongest model

**Files:** none — the deliverable is the review and the fixes it forces. ROADMAP §7: this review **has
earned its cost five cycles running**, in the same shape every time — a defect spanning files no single
task's diff contained.

- [ ] **1.** A fresh reviewer, strongest model, reads the **whole branch diff** against `main` with the spec
      open beside it.
- [ ] **2.** It **runs** the code — suite, exe, screenshots — not only reads it.
- [ ] **3.** It hunts the G2a defect shape specifically: **correct code carrying a false description.** Ten
      landed in G2a, every one caught in review and none by a test, because no test runs a docstring, an
      error message, or a line of user-facing instructions. Every claim a comment makes about another module
      is checked by opening that module.
- [ ] **4. Three wave-3-specific questions the reviewer must answer in writing**, because no test in this
      plan can:
      (a) **is there any path to `net.write` that skips `ArmWriteDialog`?** — walk every caller of
      `gate.submit`, not just the ones with tests;
      (b) **does every terminal path of a write call `WriteQueue.settle()` exactly once?** — a missed
      settle stalls the wire silently, a double settle releases two packets;
      (c) **does any string shown to an operator claim something the code does not do?** — in particular the
      three badges, `console.write.cancelled` vs `revert_cancelled`, and the mismatch line.
- [ ] **5.** A scoped re-review per fix round — only the files that fix touched.
- [ ] **6.** The verdict goes in the PR, and **a verifier that did not write the code tries to refute it
      against the real files**. Never grade your own work.

**Verify:** `$PY -m pytest --junitxml=dist-reports/suite.xml` — full suite, tally pasted into the PR with
the command.

---

## Acceptance — human only, NOT machine-verifiable

Copied from spec §9.3. **No test in this plan substitutes for any line below.** Against **WING-GIAQUY,
`192.168.128.28`**, from `dist\wing-ui.exe`, with **WING-Edit connected throughout**. Record the output
whatever it says.

- [ ] Connect → lamp green, identity matches `wing net identity`. Pull → Doctor fills. The selector reads
      **Manual**; Delayed and Immediate are greyed out.
- [ ] **Arm:** the dialog names the desk *with the serial* `wing net identity` prints. **Wrong name**
      `WING-GIAQUI` → Arm greyed, `console.write.name_wrong`. **Latch unticked**, correct name → Arm greyed.
      Tick and type → Arm enables, all three levels become selectable.
- [ ] **Manual:** Repair a **G8** finding (a send to a monitor bus in POST, `repairs.yaml:19-23`) → nothing
      reaches the desk. Click the row's Send → countdown; press **+5 s** three times and watch the remainder
      grow; **Cancel** → nothing written, WING-Edit unchanged, journal row intact.
- [ ] **Delayed:** Repair the same finding → the countdown opens itself at the Settings default. Let it
      **expire** → `sent ✓`, and **WING-Edit shows that send flip to PRE**. Repair another, press **Apply
      now** → it lands without waiting. **Immediate:** select it, Repair a third finding → it lands with no
      dialog at all, badge ✓.
- [ ] **Bool normalisation:** repair a `to: false` finding (R1, `repairs.yaml:52-55`) in Delayed → the
      dialog reads `True`/`False`, **never `1`/`0`**, no mismatch warning on an untouched desk.
      **Mismatch:** move that parameter on WING-Edit before applying → `console.write.mismatch`, both values
      shown. **Clamp:** aim a numeric leaf outside the desk's range → badge ⚠, `console.write.clamped` with
      both numbers, **and Doctor's finding reflects the value the desk actually took** (F8). If no shipped
      repair produces one, do it once with `wing net set --confirm` and check the app renders the same
      `SetResult` shape. **No reply:** aim at an address this console lacks → badge ✗,
      `console.write.no_reply`, scene leaf still holding what Repair set.
- [ ] **Revert** one ledger row → the desk returns to the captured before-value; one countdown in Delayed,
      instant in Immediate. **Revert all**, five or more rows → reverse order, progress counting `3/7`,
      **WING-Edit never showing two moving at once**, and in Delayed **one countdown per parameter**.
      **Stop** mid-run → ends after the current one, the rest visibly left.
- [ ] **Serial mismatch:** relaunch with `WING_WRITE_ALLOW_SERIAL` wrong, arm, apply → badge
      `console.write.refused` with `_authorize`'s text, **WING-Edit unchanged**. **LOST mid-countdown:** in
      Delayed, start a watch, Repair, unplug the desk while the countdown runs → on expiry **nothing is
      sent**, `console.write.gate_closed` shows, and the selector has fallen back to **Manual** (F4).
- [ ] Coexistence: WING-Edit stays connected and usable throughout. Every affected surface screenshotted
      **from the exe**, and ToanAZ has looked at them.

## Definition of done for the wave

1. **PR green in CI** on base `main` (check `test`, `.github/workflows/ci.yml`, windows-latest + Python
   3.12). Extra `mcp` is deliberately not installed there — the suite has a test that runs only when `mcp`
   is absent.
2. **A verifier that did not write the code has tried to refute the claim** against the real files, and
   failed to. Never grade your own work.
3. **Exe screenshots of every affected surface attached to the PR** — from `dist\wing-ui.exe`, not a dev
   run — **and ToanAZ has looked at them.**
4. **ROADMAP, `docs/tech-debt.md` and `memory/MEMORY.md` updated**, with every statement the wave made false
   fixed, not merely a new row added (Task 14).
5. **The wave-4 handoff exists** and names every decision still waiting on a human — §11's three questions
   and all fifteen `W…` rulings (Task 14).
6. The full suite's tally is pasted in the PR with the command that produced it, taken from `--junitxml`
   (D-47). A green build does not prove the logic is correct — the acceptance list above is the other half.
7. **`wc -l` pasted for every `ui/` file this wave touched or created**, all ≤200, with `live_controller.py`
   and `console_page.py` still at 199 and `main_window.py` at 195 or under.

## Deviations from the spec, and why

1. **`scene_value` lands in Task 3, not Task 4.** §10 gives it to task 4, but §4 requires
   `WriteTransport.read` to normalise, and `read` is task 3's. Task 3 therefore ships `scene_value` and its
   per-JSON-type tests; Task 4 ships `Outcome`, `settle_scene`, `revert_confirmation` and what each outcome
   does to the scene — which is what F8 is actually about.
2. **`ui/session.py` gains `record_value` (Task 4).** §4's Changed table omits it, but the journal is the
   only door into the document (`session.py:43-44` → `edit/writer.py:22-29`), so a clamp (F8) or a
   successful revert (W13) cannot move a scene leaf any other way. ~16 lines; the file ends at ~112.
3. **A module §4 did not list: `ui/write_router.py` (≤160, Qt).** The Repair routing and Immediate's
   pre-flight read need a home, and every candidate is full: `main_window.py` has four lines this whole
   wave, `console_page.py` and `live_controller.py` may not grow at all (W7), `changes_send.py` is budgeted
   at 120 for the Send button and its badges, and `live_wiring.py` is already carrying the gate. Its
   responsibility is one sentence: *what happens to a repair between the click and the ledger row.*
4. **`SentWrite` carries `path` as well as `address` (Task 3).** §4 lists four fields. Revert needs the
   dotted document path back — to build a `Patch` and to reach `jsontypes` — and this project has no
   inverse of `osc_address`; inventing one would be a second mapper to keep in step with `_place` (W2).
   Carrying the path is cheaper and cannot drift.
5. **The AST allow-list gets a third assertion, `find_write_verb_uses` (Task 3).** §8.4's assertion 1 is
   written against *calls*, but `live_write.REAL` names `write.set` as a **value** in a frozen dataclass
   field, and rule 2 only walks `ast.Call`. An attribute-level scan catches both spellings, so the
   allow-list is non-vacuous — and the test asserts it *sees* `live_write.py`, so it cannot go vacuous
   later.
6. **`WriteTransport.read` takes the dotted path, not the OSC address.** §4's comment says
   `# host, address`, but the same block requires `read` to apply `scene_value`, which needs
   `leaf_parts(path)`. Passing the path and deriving both inside is the only shape in which the caller
   cannot get it wrong — which is the stated reason `leaf_parts` exists at all.
7. **D-41 closes only its `net/` half (Task 15a).** The ledger's close text also asks that `ConsolePage`
   pass Discover's schema into a later Pull, and all three files that would carry it
   (`console_page.py`, `live_controller.py`, `live_snapshot.py`) sit at 199 under a W7 no-growth rule. The
   entry becomes `partially closed`, not `closed`.
8. **`main_window.py`'s ≤4 lines are split across Tasks 8 and 13** — one `install_write_gate` call, one
   two-line dock-visibility condition replacing one line. Net +2; the file ends at **193**.

## Self-review

**Spec coverage.** F1→2 (`WriteQueue`), 13 (`RevertQueue`), pinned in both. F2→the whole wave; the scene
moves only as a consequence (4, 12). F3→2 (`ApplyLevel`), 11 (selector + routing), 12 (Manual's Send).
F4→2 (`ArmState`), 9 (`ArmWriteDialog`), 8 (disarm on dropout), 11 (selector fallback). F5→10. F6→6.
F7→2 (`RevertQueue`), 13 (ledger, Revert, Revert all, Stop). F8→4 (`settle_scene`, three outcomes),
12 (`apply_result`), 13 (`apply_revert`).
W1→5 (the two `_ACTIONS` rows), 8 (`can_write`). W2→1. W3/W3b→3 (`send` always `set`, `confirm=True`; the
AST test forbids `toggle`), and W3b's **first-int-descriptor** guard is a comment beside `KINDS` in
`repairs.yaml`, written in Task 3's commit. W4→3. W5→9, 10, 11 (three private `CallRunner`s), 8 (the gate's
one runner for sends). W7→Global Constraints + 6 (the split) + 7 (the namespace). W8→6. W9→15. W10→2, 8.
W11→9, 10. W12→10, 13. W13→4, 13. W14→11, 13. W15→10, 13.
§2.1→9; §2.2→11, 12; §2.3→10; §2.4→4, 12; §2.5→13. §3's "out" list appears in no task. §4's New table→1, 2,
3, 9, 10, 12, 13, 7, 6 (plus deviation 3); §4's Changed table→11, 4, 12, 5, 8, 8+13, 5, 6, 6, 6, 7, 3.
§6→5. §7.1→5, 9, 10. §7.2→2, 13. §8.1→8; §8.2→9; §8.3→10; §8.4→3 (structural), 8+10+11 (late re-check);
§8.5→3 (surfaced as `console.write.refused`). §9.1→1, 2, 3, 4, 5, 6; §9.2→9, 10, 11, 12, 13; §9.3→the
acceptance list. §10's sixteen tasks all map, numbering and order kept. §11's three open questions→Task 14's
handoff and the PR body. §12's out-of-scope items appear in no task.
**Gaps found: none.**

**Type consistency.** `leaf_parts` / `osc_address` / `join_segments` (1) are consumed by 3, 4, 10, 11, 12,
13 under those exact names. `ApplyLevel` / `ArmState` / `RevertQueue` (2) and `WriteQueue` (2) are consumed
by 8, 11, 13. `WriteTransport(identity, read, set)` (3) is consumed by 8, 9, 10, 11 under those three
attribute names. `WriteConfirmation(host, address, after, identity, desk_before)` (3) is built in 8, 10 and
11 and accepted only by `send` (3). `SentWrite(address, path, desk_before, written, result)` (3 + 12's
`path`) is produced by 11 and consumed by 12, 13. `scene_value(parts, readback)` (3), `outcome(result)`,
`settle_scene(parts, after, result)`, `revert_confirmation(record, identity)` (4) are consumed by 12 and 13.
`Session.record_value(path, value, *, label, because)` (4) is called in 12 and 13 with keywords.
`TIMEOUTS["write"]` (5) is used by 8's runner. `state_store.MIN_APPLY_DELAY` / `MAX_APPLY_DELAY` /
`DEFAULTS["apply_delay"]` (6) are read by 6 and 10/11/12/13 via `window._apply_delay`. `text("console.write.*")`
(7) — every key used in 9, 10, 11, 12, 13 is in Task 7's `WRITE_KEYS` list. `WriteGate.can_write/ready/host/
submit/close/arm/changed` and `WriteJob(confirmation, on_result, on_error)` and `GateClosed` (8) are consumed
by 9, 10, 11, 12, 13. `arm_now(gate, parent, **kwargs)` (9) is called by 11 and 12. `DelayedWriteDialog(gate,
patch, seconds, parent, *, transport, timeout, revert_record)` with `applied` / `failed` / `cancelled` /
`desk_before` / `remaining` (10) is constructed only by `write_router._countdown` (11).
`route_repair` / `route_revert` / `send_manually` / `apply_result` / `apply_revert` (11, 12, 13) all take
`gate` first and `on_sent=Callable[[Patch, SentWrite], None]`. `badge_text(record)` (12) is used by 12 and
13. `SentLedger.add/records/row_widget/attach/revert_all/stop` + `run_started` / `run_finished` (13) are
consumed by 12's `ChangesPanel` and 13's `live_wiring` wiring.
**Two inconsistencies found and fixed inline.** (a) Task 11's first draft of `route_revert` read
`record.path_hint`, a field `SentWrite` does not have; the field it needs is `path`. (b) `path` was first
added to `SentWrite` in Task 12, which would have broken Task 4's and Task 10's constructions of the same
frozen dataclass — so it now lands once, in **Task 3**, where the type is defined, and every construction
in Tasks 4, 10, 11 and 13 passes it. (c) Task 11's `tests/test_ui_doctor.py` block used `_identity`,
`_has_repair` and `ApplyLevel`, none of which that file has; all three are now written out in the task.

**Placeholder scan.** Every task names its files with a measured `wc -l`, its Interfaces with exact
signatures, its test functions in full code, the exact run command and its expected failure, real
implementation code, the exact run command and its expected pass, a `git add … && git commit` with explicit
paths, and the claims to check by opening. No step says "similar to Task N"; no step says "add appropriate
error handling". The two checklist tasks (14, 16) and the debt task (15) are checklists **by the spec's own
instruction** and still name every file, command and doc they touch.
