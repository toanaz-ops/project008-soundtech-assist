# Live console watch (C2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Report what changes on a running WING console, continuously, without displacing any other client talking to that console.

**Architecture:** A new `wing_parser/net/watch/` package polls a small watch-list of read-only (`$`) leaves over the existing OSC transport and reports differences between rounds. It subscribes to nothing, so it consumes no console-wide exclusive resource. The watch-list is derived from `net/schema.py`'s walk (which reports what it could not resolve) rather than by probing addresses upward, because probing fails rarely and silently.

**Tech Stack:** Python 3.11+, PyYAML (read), `wing_parser.net.client`/`codec`/`schema`, pytest with the existing `tests/fake_wing.py` UDP fake.

**Design authority:** `docs/superpowers/specs/2026-08-21-live-watch-design.md`. Section numbers below (§2.2, §3.2, …) refer to it. Read it before Task 1.

## Global Constraints

Copy these into every task dispatch. They come from the spec and from
`docs/handoff/2026-08-21-next-session-prompt.md` §6.

- **Never assert an unverified claim as fact.** A citation is not verification — re-read the cited line at the moment of writing, and open the file it actually names.
- **Modular code, ~200-line files, split by responsibility layer.**
- **PowerShell, not bash**, for anything handed to ToanAZ. An OSC address starts with `/`, and MSYS rewrites it into a Windows path, so `/ch/1/fdr` silently becomes `C:/Program Files/Git/ch/1/fdr`.
- **`core`/`query`/`advisory`/`showcontext`/`net` stay deterministic.** No LLM anywhere in this work.
- **Offline:** `mcp` and `anthropic` stay uninstalled; the FastMCP test keeps skipping.
- **Never fabricate a value the file or the console does not state.**
- **PyYAML reads, ruamel writes.**
- **`pytest.approx` for floats.**
- **Do NOT modify `net/client.py`, `net/codec.py` or `net/schema.py`** (spec §8). Polling is a new consumer of a tested transport.
- **The unprofiled real file must still yield exactly 22 findings.** `python -m wing_parser.cli doctor user-files/example-Vu.snap` — verify before every commit.
- **Baseline to preserve:** 996 passed, 1 skipped. Every task adds tests; none may remove or weaken one.
- **Value interpretation is already decided:** use `codec.leaf_value(message)`. It encodes the measured rule — `,sff` → native float, `,sfi` → display string parsed to int, `,s` → the string. Do not re-derive it.

---

### Task 1: The watch-list builder

**Files:**
- Create: `wing_parser/net/watch/__init__.py`
- Create: `wing_parser/net/watch/data/watchlist.yaml`
- Create: `wing_parser/net/watch/list.py`
- Modify: `pyproject.toml:26` — add the new package-data glob
- Test: `tests/test_watch_list.py`

**Interfaces:**
- Consumes: `wing_parser.net.schema.walk_schema(host, port, batch_size, retry_rounds, idle_timeout, client) -> SchemaResult`, where `SchemaResult` has `.leaves: dict[str, str]` and `.unresolved_nodes: tuple[str, ...]`.
- Produces:
  - `WatchList` frozen dataclass with `.addresses: tuple[str, ...]`, `.unresolved: tuple[str, ...]`, `.strips: dict[str, int]`
  - `load_watch_keys(path: Path | None = None) -> dict[str, tuple[str, ...]]`
  - `build_watch_list(host: str, *, port: int = 2223, client: WingClient | None = None, keys: dict[str, tuple[str, ...]] | None = None, **walk_kwargs) -> WatchList`

**Why the derivation is indirect — read this before writing code.** `schema._expand` contains `if name.startswith("$"): continue`, so the walk never lists a `$` key. The `$` keys are exactly what this sub-project watches. So the walk supplies the **strip set**, and the `$` keys come from the YAML. Measured 2026-08-21 (`docs/probes/probe9_stripset.py`): the walk took 1.00 s, returned 25 062 leaves and 0 unresolved nodes, and implied exactly 40 channels, 16 buses, 4 mains, 8 matrices, 16 DCAs, contiguous from 1.

- [ ] **Step 1: Create the package and its data file**

`wing_parser/net/watch/__init__.py`:

```python
"""Watch a running console for changes, by polling.

Deliberately not a subscription: only one OSC subscription exists
console-wide and it expires after 10s (design doc S3.1), so subscribing
would displace WING-Edit, Companion or any other client. Polling
consumes nothing another client can lose.
"""
```

`wing_parser/net/watch/data/watchlist.yaml`:

```yaml
# What a watch session polls, per strip family.
#
# These are EFFECTIVE values (design doc S2.2): $fdr and $mute already
# fold in DCA contribution and mute-override, so pulling a DCA down
# surfaces on every channel it governs without this package modelling
# DCA membership at all.
#
# Widening coverage is a data edit, not a code change. Adding $name
# catches renames; adding an /io family would catch preamp moves.
families:
  ch:   ["$fdr", "$mute", "$solo"]
  bus:  ["$fdr", "$mute", "$solo"]
  main: ["$fdr", "$mute", "$solo"]
  mtx:  ["$fdr", "$mute", "$solo"]
  dca:  ["$solo"]
```

- [ ] **Step 2: Write the failing tests**

`tests/test_watch_list.py`:

```python
"""Tests for wing_parser.net.watch.list, driven against tests/fake_wing.py.

No test here touches a real console.
"""

from __future__ import annotations

import pytest

from tests.fake_wing import FakeWing
from wing_parser.net.codec import encode
from wing_parser.net.watch.list import build_watch_list, load_watch_keys

FAST = dict(batch_size=200, retry_rounds=1, idle_timeout=0.03)


def _schema_tx(address: str) -> bytes:
    return encode(address, "s", ("?",))


def _schema_rx(address: str, body: str) -> bytes:
    return encode(address, "s", (body,))


def _tiny_desk(fake: FakeWing) -> None:
    """Two channels and one bus, each owning one ordinary leaf and one
    $ leaf. The $ leaf is present in the reply on purpose: the walk must
    skip it, and the builder must add it back from config."""
    fake.register(_schema_tx("/ch"), _schema_rx("/ch", "  1  (node)\n  2  (node)\n"))
    for number in (1, 2):
        fake.register(
            _schema_tx(f"/ch/{number}"),
            _schema_rx(f"/ch/{number}", "  fdr  fader [-oo .. 10.0 dB]\n  $fdr  fader\n"),
        )
    fake.register(_schema_tx("/bus"), _schema_rx("/bus", "  1  (node)\n"))
    fake.register(
        _schema_tx("/bus/1"),
        _schema_rx("/bus/1", "  fdr  fader [-oo .. 10.0 dB]\n"),
    )


def test_addresses_are_the_dollar_keys_of_every_strip_the_walk_found():
    with FakeWing() as fake:
        _tiny_desk(fake)
        host, port = fake.osc_address
        result = build_watch_list(
            host,
            port=port,
            keys={"ch": ("$fdr", "$mute"), "bus": ("$fdr",)},
            **FAST,
        )

    assert result.addresses == (
        "/ch/1/$fdr",
        "/ch/1/$mute",
        "/ch/2/$fdr",
        "/ch/2/$mute",
        "/bus/1/$fdr",
    )
    assert result.strips == {"ch": 2, "bus": 1}


def test_a_family_the_console_does_not_have_contributes_nothing():
    """The 20x cost of an absent address (design doc S2.5) is avoided by
    never emitting one, not by tolerating it."""
    with FakeWing() as fake:
        _tiny_desk(fake)
        host, port = fake.osc_address
        result = build_watch_list(
            host, port=port, keys={"ch": ("$fdr",), "mtx": ("$fdr",)}, **FAST
        )

    assert result.addresses == ("/ch/1/$fdr", "/ch/2/$fdr")
    assert "mtx" not in result.strips
    assert not any("/mtx/" in address for address in result.addresses)


def test_an_unresolved_node_is_reported_and_never_folded_into_absent():
    """Design doc S2.7/S3.2: a builder that cannot say what it failed to
    resolve fails silently, and a watch-list quietly missing four mains
    never reports a main fader move while looking fine doing it."""
    with FakeWing() as fake:
        _tiny_desk(fake)
        # /main answers with a child that then never answers at all.
        fake.register(_schema_tx("/main"), _schema_rx("/main", "  1  (node)\n"))
        fake.register(_schema_tx("/main/1"), None)
        host, port = fake.osc_address
        result = build_watch_list(
            host, port=port, keys={"ch": ("$fdr",), "main": ("$fdr",)}, **FAST
        )

    assert "/main/1" in result.unresolved


def test_the_shipped_yaml_loads_and_names_the_measured_families():
    keys = load_watch_keys()
    assert set(keys) == {"ch", "bus", "main", "mtx", "dca"}
    # S2.1 measured that /dca exposes only $solo and $sololed -- it has no
    # $fdr, so asking for one would emit an address that cannot answer.
    assert keys["dca"] == ("$solo",)
    assert keys["ch"] == ("$fdr", "$mute", "$solo")


def test_a_family_named_in_config_but_absent_from_the_address_map_is_refused():
    """A typo in watchlist.yaml must fail loudly at build time, not
    produce a watch-list that silently omits what the engineer asked for."""
    with FakeWing() as fake:
        _tiny_desk(fake)
        host, port = fake.osc_address
        with pytest.raises(ValueError, match="chn"):
            build_watch_list(host, port=port, keys={"chn": ("$fdr",)}, **FAST)
```

- [ ] **Step 3: Run the tests to verify they fail**

```bash
python -m pytest tests/test_watch_list.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.net.watch'`

- [ ] **Step 4: Write the implementation**

`wing_parser/net/watch/list.py`:

```python
"""Build the concrete address list a watch session polls.

The derivation is indirect on purpose. `schema._expand` drops every "$"
child (S2.2: read-only keys are absent from .snap), and the "$" keys are
exactly what a watch session wants -- S2.2 again: $fdr and $mute are the
EFFECTIVE values, already folding in DCA and mute-override. So the walk
supplies the strip SET, and the keys come from watchlist.yaml.

The alternative -- probe /ch/1, /ch/2, ... and stop at the first silence
-- is what S2.7 measured and rejected: it lost a whole family once and
then reproduced correctly 30 times out of 30. Rare and silent is the
dangerous combination, and `walk_schema` is the path that reports what it
could not resolve instead of folding it into "absent".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from wing_parser.net.client import OSC_PORT, WingClient
from wing_parser.net.schema import walk_schema

_DATA = Path(__file__).resolve().parent / "data" / "watchlist.yaml"

# The families a strip address can name. Kept explicit rather than
# inferred so a typo in watchlist.yaml is refused (see build_watch_list)
# rather than silently contributing nothing.
FAMILIES = ("ch", "bus", "main", "mtx", "dca")

_STRIP_RE = re.compile(rf"^/({'|'.join(FAMILIES)})/(\d+)/")


@dataclass(frozen=True)
class WatchList:
    """`unresolved` is a field rather than an omission for the same reason
    `SchemaResult.unresolved_nodes` is: a node that never answered must
    stay visible to the caller."""

    addresses: tuple[str, ...]
    unresolved: tuple[str, ...]
    strips: dict[str, int]


@lru_cache(maxsize=1)
def _load_yaml() -> dict[str, tuple[str, ...]]:
    document = yaml.safe_load(_DATA.read_text(encoding="utf-8")) or {}
    families = document.get("families") or {}
    return {name: tuple(keys) for name, keys in families.items()}


def load_watch_keys(path: Path | None = None) -> dict[str, tuple[str, ...]]:
    """The shipped config, or one read from `path` for a caller that
    wants to watch something else."""
    if path is None:
        return dict(_load_yaml())
    document = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    families = document.get("families") or {}
    return {name: tuple(keys) for name, keys in families.items()}


def build_watch_list(
    host: str,
    *,
    port: int = OSC_PORT,
    client: WingClient | None = None,
    keys: dict[str, tuple[str, ...]] | None = None,
    **walk_kwargs,
) -> WatchList:
    """Walk the console, then emit one address per (strip, key) pair.

    Fresh every call, like `walk_schema` itself: the tree's shape depends
    on live values, so a cached list would miss what a loaded desk holds.
    """
    wanted = load_watch_keys() if keys is None else keys

    unknown = sorted(set(wanted) - set(FAMILIES))
    if unknown:
        raise ValueError(
            f"watch config names {', '.join(unknown)}, which is not a strip "
            f"family; expected one of {', '.join(FAMILIES)}"
        )

    schema = walk_schema(host, port=port, client=client, **walk_kwargs)

    present: dict[str, set[int]] = {}
    for address in schema.leaves:
        match = _STRIP_RE.match(address)
        if match:
            present.setdefault(match.group(1), set()).add(int(match.group(2)))

    addresses: list[str] = []
    strips: dict[str, int] = {}
    for family in FAMILIES:
        if family not in wanted or family not in present:
            continue
        numbers = sorted(present[family])
        strips[family] = len(numbers)
        for number in numbers:
            addresses.extend(f"/{family}/{number}/{key}" for key in wanted[family])

    return WatchList(
        addresses=tuple(addresses),
        unresolved=schema.unresolved_nodes,
        strips=strips,
    )
```

- [ ] **Step 5: Add the package data glob**

In `pyproject.toml`, the `[tool.setuptools.package-data]` line currently reads:

```toml
wing_parser = ["descriptors/data/*.yaml", "classifier/data/*.yaml", "advisory/base_rules/*.yaml"]
```

Change it to:

```toml
wing_parser = ["descriptors/data/*.yaml", "classifier/data/*.yaml", "advisory/base_rules/*.yaml", "net/watch/data/*.yaml"]
```

- [ ] **Step 6: Run the tests to verify they pass**

```bash
python -m pytest tests/test_watch_list.py -v
```

Expected: 5 passed.

- [ ] **Step 7: Prove one test can fail**

Temporarily change `list.py`'s `unresolved=schema.unresolved_nodes` to `unresolved=()`, re-run, and confirm `test_an_unresolved_node_is_reported_and_never_folded_into_absent` goes red. Restore the line. A test never seen red may assert nothing.

- [ ] **Step 8: Verify the finding contract and commit**

```bash
python -m wing_parser.cli doctor user-files/example-Vu.snap
```

Expected: `22 findings:` on the first line.

```bash
git add wing_parser/net/watch tests/test_watch_list.py pyproject.toml
git commit -m "Build the watch-list from the schema walk, not by probing"
```

---

### Task 2: The change record

**Files:**
- Create: `wing_parser/net/watch/events.py`
- Test: `tests/test_watch_events.py`

**Interfaces:**
- Consumes: nothing from Task 1 at runtime — this module is pure data and formatting, so it can be written and reviewed independently.
- Produces:
  - `Change` frozen dataclass: `.address: str`, `.strip: str`, `.key: str`, `.label: str`, `.before: object`, `.after: object`, `.elapsed: float`
  - `split_address(address: str) -> tuple[str, str]` returning `(strip, key)`
  - `format_change(change: Change) -> str`
  - `change_as_dict(change: Change) -> dict`

- [ ] **Step 1: Write the failing tests**

`tests/test_watch_events.py`:

```python
from __future__ import annotations

from wing_parser.net.watch.events import (
    Change,
    change_as_dict,
    format_change,
    split_address,
)


def _change(**overrides) -> Change:
    fields = dict(
        address="/ch/8/$fdr",
        strip="/ch/8",
        key="$fdr",
        label="M8 MC",
        before=-144.0,
        after=-7.9,
        elapsed=12.25,
    )
    fields.update(overrides)
    return Change(**fields)


def test_split_address_separates_the_strip_from_the_key():
    assert split_address("/ch/8/$fdr") == ("/ch/8", "$fdr")
    assert split_address("/dca/16/$solo") == ("/dca/16", "$solo")


def test_a_named_strip_shows_its_name():
    assert "M8 MC" in format_change(_change())


def test_an_unnamed_strip_falls_back_to_its_address_not_an_empty_gap():
    """A blank name is normal -- example-Vu.snap has six blank-named
    channels and factory-scene.snap has forty. Rendering "" would produce
    a line with a hole in it."""
    line = format_change(_change(label=""))
    assert "/ch/8" in line
    assert "  ''" not in line


def test_the_line_carries_elapsed_address_before_and_after():
    line = format_change(_change())
    assert "12.25" in line or "12.2" in line
    assert "$fdr" in line
    assert "-144.0" in line
    assert "-7.9" in line


def test_the_dict_form_is_json_safe_and_keeps_every_field():
    import json

    payload = change_as_dict(_change())
    assert payload["address"] == "/ch/8/$fdr"
    assert payload["label"] == "M8 MC"
    assert payload["before"] == -144.0
    assert payload["after"] == -7.9
    json.dumps(payload)  # raises if anything is not serialisable
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
python -m pytest tests/test_watch_events.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.net.watch.events'`

- [ ] **Step 3: Write the implementation**

`wing_parser/net/watch/events.py`:

```python
"""One change, and how it reads.

Kept apart from the poller so the loop owns timing and the record owns
presentation, and so a change can be constructed in a test without a
socket anywhere near it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Change:
    address: str
    strip: str
    key: str
    label: str
    before: object
    after: object
    elapsed: float


def split_address(address: str) -> tuple[str, str]:
    """"/ch/8/$fdr" -> ("/ch/8", "$fdr")."""
    strip, _, key = address.rpartition("/")
    return strip, key


def _shown(change: Change) -> str:
    """A blank name is ordinary -- factory-scene.snap names no channel at
    all -- so fall back to the address rather than leaving a gap."""
    return change.label if change.label else change.strip


def format_change(change: Change) -> str:
    return (
        f"[{change.elapsed:7.2f}s] {_shown(change):<20s} "
        f"{change.key:<8s} {change.before!r} -> {change.after!r}"
    )


def change_as_dict(change: Change) -> dict:
    return {
        "elapsed": round(change.elapsed, 3),
        "address": change.address,
        "strip": change.strip,
        "key": change.key,
        "label": change.label,
        "before": change.before,
        "after": change.after,
    }
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
python -m pytest tests/test_watch_events.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add wing_parser/net/watch/events.py tests/test_watch_events.py
git commit -m "Add the change record and how a change reads"
```

---

### Task 3: The polling loop

**Files:**
- Create: `wing_parser/net/watch/poller.py`
- Test: `tests/test_watch_poller.py`

**Interfaces:**
- Consumes:
  - Task 1: `WatchList` with `.addresses`, `.unresolved`, `.strips`
  - Task 2: `Change`, `split_address`
  - `wing_parser.net.client.WingClient.get_many(addresses, batch_size, retry_rounds, typetag, args) -> BatchResult` with `.replies: dict[str, OscMessage]` and `.unresolved: tuple[str, ...]`
  - `wing_parser.net.codec.leaf_value(message) -> tuple[object, str]`
- Produces:
  - `read_labels(client: WingClient, strips: Iterable[str]) -> dict[str, str]`
  - `sample(client: WingClient, addresses: Sequence[str]) -> dict[str, object]`
  - `watch(client: WingClient, watch_list: WatchList, *, interval: float = 0.25, duration: float | None = None, max_rounds: int | None = None, clock=time.monotonic, sleep=time.sleep) -> Iterator[Change]`

**Why `max_rounds` exists.** `duration` cannot bound a test deterministically:
the loop calls `clock()` twice per round *plus once per change*, so how many
ticks a run consumes depends on the data. A scripted clock would run dry
mid-generator, and an exhausted `next()` inside a generator surfaces as
`RuntimeError`, not `StopIteration` — a red test for a reason unrelated to what
it checks. `max_rounds` bounds rounds directly. Production uses `duration`.

**The rule that prevents false events.** A leaf that answered last round and is absent this round has NOT changed — it failed to answer. Reporting `-7.9 -> None` would be a fabricated value, which the global constraints forbid. Carry the previous value forward and say nothing.

- [ ] **Step 1: Write the failing tests**

`tests/test_watch_poller.py`:

```python
"""Tests for the polling loop. No socket: a stub client returns scripted
rounds, so the loop's behaviour is examined without timing flakiness."""

from __future__ import annotations

from wing_parser.net.client import BatchResult
from wing_parser.net.codec import OscMessage
from wing_parser.net.watch.list import WatchList
from wing_parser.net.watch.poller import sample, watch


def _fdr(value: float) -> OscMessage:
    display = "-oo" if value == -144.0 else f"{value}"
    return OscMessage(address="", typetag="sff", args=(display, 0.0, value))


def _name(text: str) -> OscMessage:
    return OscMessage(address="", typetag="s", args=(text,))


class StubClient:
    """Replays a scripted list of {address: OscMessage} rounds."""

    def __init__(self, rounds, labels=None):
        self._rounds = list(rounds)
        self._labels = labels or {}
        self.calls = 0

    def get_many(self, addresses, **kwargs):
        addresses = list(addresses)
        if addresses and addresses[0].endswith("/name"):
            replies = {a: _name(self._labels.get(a, "")) for a in addresses}
            return BatchResult(replies=replies, unresolved=())
        index = min(self.calls, len(self._rounds) - 1)
        self.calls += 1
        replies = dict(self._rounds[index])
        missing = tuple(a for a in addresses if a not in replies)
        return BatchResult(replies=replies, unresolved=missing)


def _list(*addresses) -> WatchList:
    return WatchList(addresses=tuple(addresses), unresolved=(), strips={"ch": 1})


def _run(client, watch_list, rounds):
    """Drive the loop for an exact number of rounds, with a clock that
    advances on every call and never runs dry, and a sleep that does not.

    Bounded by max_rounds rather than duration: the loop calls clock()
    twice per round plus once per change, so a scripted tick list would
    run out at a data-dependent point.
    """
    state = {"now": 0.0}

    def clock() -> float:
        state["now"] += 0.01
        return state["now"]

    return list(
        watch(
            client,
            watch_list,
            interval=0.0,
            max_rounds=rounds,
            clock=clock,
            sleep=lambda _seconds: None,
        )
    )


def test_sample_reads_the_native_float_for_an_sff_leaf():
    client = StubClient([{"/ch/1/$fdr": _fdr(-7.9)}])
    assert sample(client, ["/ch/1/$fdr"]) == {"/ch/1/$fdr": -7.9}


def test_a_changed_value_produces_one_change_naming_before_and_after():
    client = StubClient(
        [
            {"/ch/1/$fdr": _fdr(-144.0)},
            {"/ch/1/$fdr": _fdr(-7.9)},
            {"/ch/1/$fdr": _fdr(-7.9)},
        ]
    )
    changes = _run(client, _list("/ch/1/$fdr"), 3)
    assert len(changes) == 1
    assert changes[0].before == -144.0
    assert changes[0].after == -7.9
    assert changes[0].address == "/ch/1/$fdr"


def test_a_steady_value_produces_nothing():
    client = StubClient([{"/ch/1/$fdr": _fdr(-7.9)}])
    assert _run(client, _list("/ch/1/$fdr"), 4) == []


def test_a_leaf_that_stops_answering_is_not_reported_as_a_change():
    """It failed to answer; it did not move. Reporting -7.9 -> None would
    invent a value the console never stated."""
    client = StubClient(
        [
            {"/ch/1/$fdr": _fdr(-7.9)},
            {},                      # silent round
            {"/ch/1/$fdr": _fdr(-7.9)},
        ]
    )
    assert _run(client, _list("/ch/1/$fdr"), 3) == []


def test_a_value_that_moves_while_a_leaf_is_silent_is_still_caught_afterwards():
    client = StubClient(
        [
            {"/ch/1/$fdr": _fdr(-144.0)},
            {},
            {"/ch/1/$fdr": _fdr(0.0)},
            {"/ch/1/$fdr": _fdr(0.0)},
        ]
    )
    changes = _run(client, _list("/ch/1/$fdr"), 4)
    assert len(changes) == 1
    assert changes[0].before == -144.0
    assert changes[0].after == 0.0


def test_the_change_carries_the_strips_name():
    client = StubClient(
        [
            {"/ch/1/$fdr": _fdr(-144.0)},
            {"/ch/1/$fdr": _fdr(-7.9)},
        ],
        labels={"/ch/1/name": "Kick In"},
    )
    changes = _run(client, _list("/ch/1/$fdr"), 2)
    assert changes[0].label == "Kick In"
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
python -m pytest tests/test_watch_poller.py -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.net.watch.poller'`

- [ ] **Step 3: Write the implementation**

`wing_parser/net/watch/poller.py`:

```python
"""The loop: sample, compare with the previous sample, yield differences.

`clock` and `sleep` are parameters so a test can drive many rounds
without waiting for any of them. The loop paces itself rather than
spinning: S2.4 measured a 208-leaf round at well under the default
interval, so a quiet desk should leave the network almost entirely idle
between rounds.
"""

from __future__ import annotations

import time
from typing import Callable, Iterable, Iterator, Sequence

from wing_parser.net.client import WingClient
from wing_parser.net.codec import leaf_value
from wing_parser.net.watch.events import Change, split_address
from wing_parser.net.watch.list import WatchList

DEFAULT_INTERVAL = 0.25


def read_labels(client: WingClient, strips: Iterable[str]) -> dict[str, str]:
    """One batch for every strip's name, read once at startup.

    Names are read from the ordinary `name` leaf, not `$name`: both exist
    (measured 2026-08-21), and `name` is the one the .snap carries, so a
    label here matches what every other command prints.
    """
    wanted = [f"{strip}/name" for strip in strips]
    if not wanted:
        return {}
    result = client.get_many(wanted)
    labels: dict[str, str] = {}
    for address, message in result.replies.items():
        strip = address.rpartition("/")[0]
        try:
            value, _display = leaf_value(message)
        except ValueError:
            continue
        labels[strip] = str(value)
    return labels


def sample(client: WingClient, addresses: Sequence[str]) -> dict[str, object]:
    """One round. Absent addresses are simply missing from the result --
    never present with a fabricated value."""
    result = client.get_many(list(addresses))
    values: dict[str, object] = {}
    for address, message in result.replies.items():
        try:
            value, _display = leaf_value(message)
        except ValueError:
            # A reply that is not a leaf triplet is not a value. Skipping
            # it keeps a malformed round from looking like a change.
            continue
        values[address] = value
    return values


def watch(
    client: WingClient,
    watch_list: WatchList,
    *,
    interval: float = DEFAULT_INTERVAL,
    duration: float | None = None,
    max_rounds: int | None = None,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
) -> Iterator[Change]:
    """Yield a Change for every difference between consecutive rounds.

    `duration` bounds a real session in seconds. `max_rounds` bounds one
    in rounds, which is what a test needs: this loop calls `clock()`
    twice per round plus once per change, so how much simulated time a
    run consumes depends on the data, and a wall-clock bound would make
    a test's round count data-dependent too.
    """
    addresses = list(watch_list.addresses)
    strips = sorted({split_address(a)[0] for a in addresses})
    labels = read_labels(client, strips)

    previous = sample(client, addresses)
    started = clock()
    rounds = 0

    while True:
        if max_rounds is not None and rounds >= max_rounds:
            return
        now = clock()
        if duration is not None and now - started >= duration:
            return
        rounds += 1

        round_started = now
        current = sample(client, addresses)

        for address, after in current.items():
            before = previous.get(address)
            if before is None or before == after:
                continue
            strip, key = split_address(address)
            yield Change(
                address=address,
                strip=strip,
                key=key,
                label=labels.get(strip, ""),
                before=before,
                after=after,
                elapsed=clock() - started,
            )

        # Carry forward, never overwrite with a gap: an address that went
        # silent keeps its last known value, so the next answer is
        # compared against a real reading rather than against nothing.
        previous.update(current)

        remaining = interval - (clock() - round_started)
        if remaining > 0:
            sleep(remaining)
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
python -m pytest tests/test_watch_poller.py -v
```

Expected: 6 passed.

- [ ] **Step 5: Prove the silent-leaf test can fail**

Temporarily change `previous.update(current)` to `previous = current`, re-run, and confirm `test_a_value_that_moves_while_a_leaf_is_silent_is_still_caught_afterwards` goes red — with `previous = current`, the silent round wipes the baseline and the later move compares against nothing. Restore the line.

- [ ] **Step 6: Commit**

```bash
git add wing_parser/net/watch/poller.py tests/test_watch_poller.py
git commit -m "Add the polling loop, carrying a silent leaf's value forward"
```

---

### Task 4: `wing net watch`

**Files:**
- Modify: `wing_parser/cli/net_commands.py` — append `net_watch`
- Modify: `wing_parser/cli/__main__.py:135` — add the subparser after `push`
- Test: `tests/test_watch_cli.py`

**Interfaces:**
- Consumes: Task 1 `build_watch_list`, Task 2 `format_change`/`change_as_dict`, Task 3 `watch`.
- Produces: `net_watch(args) -> int`, reached as `wing net watch <ip>`.

**Read this before writing.** The last two cycles each shipped a whole-branch bug of exactly this shape: `doctor --show --json` emitted non-JSON because the anomaly print sat before the `--json` branch — the flag lived in `__main__.py`, the print in `commands.py`, and no single task's diff held both. This task holds both. **In `--json` mode nothing but JSON may reach stdout.** The unresolved report goes to stderr in text mode and into the first JSON object in `--json` mode.

- [ ] **Step 1: Write the failing tests**

`tests/test_watch_cli.py`:

```python
"""The CLI surface for `wing net watch`.

The last two cycles each shipped a bug where a non-JSON line reached
stdout in --json mode, because the flag and the print lived in different
files. These tests hold both halves.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from wing_parser.cli import net_commands
from wing_parser.cli.__main__ import build_parser
from wing_parser.net.watch.events import Change
from wing_parser.net.watch.list import WatchList


def _args(**overrides) -> SimpleNamespace:
    fields = dict(host="10.0.0.1", json=False, interval=0.25, until=1.0)
    fields.update(overrides)
    return SimpleNamespace(**fields)


def _change() -> Change:
    return Change(
        address="/ch/8/$fdr",
        strip="/ch/8",
        key="$fdr",
        label="M8 MC",
        before=-144.0,
        after=-7.9,
        elapsed=1.5,
    )


@pytest.fixture
def stubbed(monkeypatch):
    """Replace the network entirely: a fixed watch-list and one change."""
    state = {"list": WatchList(("/ch/8/$fdr",), (), {"ch": 40}), "changes": [_change()]}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

    monkeypatch.setattr(net_commands, "WingClient", FakeClient)
    monkeypatch.setattr(
        net_commands, "build_watch_list", lambda *a, **k: state["list"]
    )
    monkeypatch.setattr(
        net_commands, "watch", lambda *a, **k: iter(state["changes"])
    )
    return state


def test_the_parser_accepts_net_watch_with_an_ip():
    args = build_parser().parse_args(["net", "watch", "10.0.0.1"])
    assert args.host == "10.0.0.1"
    assert args.handler is net_commands.net_watch


def test_text_mode_prints_the_change_with_its_name(stubbed, capsys):
    assert net_commands.net_watch(_args()) == 0
    out = capsys.readouterr().out
    assert "M8 MC" in out
    assert "$fdr" in out


def test_json_mode_emits_only_json_on_stdout(stubbed, capsys):
    """Every stdout line must parse. This is the exact defect that
    shipped twice before."""
    assert net_commands.net_watch(_args(json=True)) == 0
    out = capsys.readouterr().out
    lines = [line for line in out.splitlines() if line.strip()]
    assert lines
    for line in lines:
        json.loads(line)


def test_an_unresolved_node_is_reported_on_stderr_in_text_mode(stubbed, capsys):
    stubbed["list"] = WatchList(("/ch/8/$fdr",), ("/main/1",), {"ch": 40})
    net_commands.net_watch(_args())
    captured = capsys.readouterr()
    assert "/main/1" in captured.err
    assert "/main/1" not in captured.out


def test_an_unresolved_node_travels_in_the_json_header(stubbed, capsys):
    stubbed["list"] = WatchList(("/ch/8/$fdr",), ("/main/1",), {"ch": 40})
    net_commands.net_watch(_args(json=True))
    out = capsys.readouterr().out
    header = json.loads(out.splitlines()[0])
    assert header["unresolved"] == ["/main/1"]


def test_a_network_failure_reports_and_returns_one(monkeypatch, capsys):
    class Boom:
        def __init__(self, *args, **kwargs):
            raise OSError("no route to host")

    monkeypatch.setattr(net_commands, "WingClient", Boom)
    assert net_commands.net_watch(_args()) == 1
    assert "no route to host" in capsys.readouterr().err
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
python -m pytest tests/test_watch_cli.py -v
```

Expected: FAIL — `AttributeError: module 'wing_parser.cli.net_commands' has no attribute 'net_watch'`

- [ ] **Step 3: Add the command**

At the top of `wing_parser/cli/net_commands.py`, add to the existing imports:

```python
from wing_parser.net.watch.list import build_watch_list
from wing_parser.net.watch.events import change_as_dict, format_change
from wing_parser.net.watch.poller import watch
```

`WingClient` is already imported in that module; if it is not, add
`from wing_parser.net.client import WingClient`.

Append to `wing_parser/cli/net_commands.py`:

```python
def net_watch(args) -> int:
    """Report what changes on a running console, by polling.

    Subscribes to nothing (design doc S3.1), so it runs alongside
    WING-Edit, Companion or anything else without displacing them.

    In --json mode stdout carries JSON and nothing else: the first line
    is a header naming the watch-list, then one object per change. The
    unresolved report goes to stderr in text mode and into that header in
    --json mode -- never as a bare line on stdout, which is the defect
    that shipped twice in earlier cycles.
    """
    try:
        with WingClient(args.host) as client:
            watch_list = build_watch_list(args.host, client=client)

            if args.json:
                header = {
                    "watching": len(watch_list.addresses),
                    "strips": watch_list.strips,
                    "unresolved": list(watch_list.unresolved),
                }
                print(json.dumps(header), flush=True)
            else:
                inventory = ", ".join(
                    f"{count} {family}" for family, count in watch_list.strips.items()
                )
                print(f"watching {len(watch_list.addresses)} leaves ({inventory})")
                if watch_list.unresolved:
                    # S3.2: an incomplete list must say so. A bare total
                    # while four mains are missing is the exact failure
                    # this line exists to prevent.
                    print(
                        f"warning: {len(watch_list.unresolved)} node(s) did not "
                        f"resolve and are NOT being watched: "
                        f"{', '.join(watch_list.unresolved)}",
                        file=sys.stderr,
                    )
                print("watching -- Ctrl+C to stop")

            for change in watch(
                client,
                watch_list,
                interval=args.interval,
                duration=args.until,
            ):
                if args.json:
                    print(json.dumps(change_as_dict(change)), flush=True)
                else:
                    print(format_change(change), flush=True)
    except KeyboardInterrupt:
        # Stopping a watch is how it ends, not a failure.
        if not args.json:
            print("\nstopped", file=sys.stderr)
        return 0
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0
```

Confirm `json` and `sys` are imported at the top of `net_commands.py`; add
whichever is missing.

- [ ] **Step 4: Wire the subparser**

In `wing_parser/cli/__main__.py`, immediately after the block ending
`push.set_defaults(handler=net_commands.net_push)`, add:

```python
    watch = net_sub.add_parser("watch", help="report changes on a running console")
    watch.add_argument("host", metavar="IP")
    watch.add_argument("--json", action="store_true", help="machine-readable output")
    watch.add_argument(
        "--interval",
        type=float,
        default=0.25,
        help="seconds between rounds (default 0.25; a 208-leaf round measured 0.022s)",
    )
    watch.add_argument(
        "--until",
        type=float,
        default=None,
        metavar="SECONDS",
        help="stop after this long; without it, runs until interrupted",
    )
    watch.set_defaults(handler=net_commands.net_watch)
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
python -m pytest tests/test_watch_cli.py -v
```

Expected: 6 passed.

- [ ] **Step 6: Run the whole suite and the finding contract**

```bash
python -m pytest tests/
```

Expected: exit code 0, 1 skipped.

```bash
python -m wing_parser.cli doctor user-files/example-Vu.snap
```

Expected: `22 findings:`

- [ ] **Step 7: Commit**

```bash
git add wing_parser/cli/net_commands.py wing_parser/cli/__main__.py tests/test_watch_cli.py
git commit -m "Add wing net watch, with JSON output that stays JSON"
```

---

### Task 5: MCP gains `show` and `live`

**Files:**
- Modify: `wing_parser/mcp/tools.py` — `analyze`, `channel`, `routing`, `doctor`
- Test: `tests/test_mcp.py` — append

**Interfaces:**
- Consumes: `wing_parser.cli.commands._load(path, show, live) -> WingScene | None` — the existing loader that already handles the live branch.
- Produces: `doctor(path=None, profile=None, show=None, live=None)`, and `analyze`/`routing`(`path=None, live=None`), `channel(path=None, number=..., live=None)`.

**Why this closes an open question.** Spec §6.1: a Claude session on the MCP surface can see neither Q1–Q7 nor a console, because `doctor` takes only `path` and `profile`. The CLI is the authority; MCP is mirroring it.

**Two facts to hold while writing this.**

1. **`_load` writes to stderr, and that is safe here.** An MCP stdio server uses **stdout** as its protocol channel, so a stray `print()` to stdout would corrupt the session — but `_load`'s failure path is `print(..., file=sys.stderr)` (`wing_parser/cli/commands.py:36`), which is inert. Do not "improve" it into a stdout print, and do not add one of your own.
2. **`_guard` already turns a raised `ValueError` into a returned string.** It catches `(KeyError, ValueError)` and returns `f"error: {exc}"`, so `_scene` raising `ValueError` when a scene cannot be read produces the sentence Claude should see rather than an exception crossing the boundary. That is why `_scene` raises instead of returning `None`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_mcp.py`:

```python
def test_doctor_accepts_a_show_context_and_reports_its_findings(vu_path):
    """Spec S6.1: without this, a Claude session on MCP cannot see
    Q1-Q7 at all."""
    from wing_parser.mcp import tools

    plain = tools.doctor(str(vu_path))
    with_show = tools.doctor(
        str(vu_path), show="tests/data/example-Vu-show.yaml"
    )
    assert "Q1" not in plain
    assert "Q1" in with_show


def test_every_tool_that_reads_a_scene_now_offers_live():
    import inspect

    from wing_parser.mcp import tools

    for name in ("analyze", "routing", "channel", "doctor"):
        signature = inspect.signature(getattr(tools, name))
        assert "live" in signature.parameters, f"{name} has no live parameter"


def test_doctor_still_reports_the_pinned_count_for_the_real_file(vu_path):
    from wing_parser.mcp import tools

    assert tools.doctor(str(vu_path)).startswith("22 findings")
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
python -m pytest tests/test_mcp.py -v
```

Expected: FAIL — `doctor() got an unexpected keyword argument 'show'`

- [ ] **Step 3: Rewrite the four tools to use the shared loader**

Replace the four functions in `wing_parser/mcp/tools.py`. Each currently
calls `WingScene.load(path)` directly; each now delegates to the CLI's
`_load`, which already knows how to read a console and how to attach a
show context.

```python
from wing_parser.cli.commands import _load


def _scene(path: str | None, show: str | None = None, live: str | None = None):
    """One loader for every tool, so MCP cannot drift from the CLI on
    what a scene is or where it may come from."""
    scene = _load(path, show, live)
    if scene is None:
        raise ValueError(
            "could not read a scene: pass either a .snap path or live=<ip>"
        )
    return scene


@_guard
def analyze(path: str | None = None, live: str | None = None) -> str:
    """Overview of a scene: channels, buses, names, levels, inferred
    source types, firmware version and parser anomalies.

    Pass `live` with a console's IP to read a running desk instead of a
    file.
    """
    scene = _scene(path, live=live)
    out = render.scene_overview(scene)
    scene.classifier.flush()
    return out


@_guard
def routing(path: str | None = None, live: str | None = None) -> str:
    """Routing map: orphans, ALT-sourced channels and anything the
    classifier could not identify.

    Pass `live` with a console's IP to read a running desk instead of a
    file.
    """
    scene = _scene(path, live=live)
    out = render.routing(scene.routing.summary(), scene.unclassified())
    scene.classifier.flush()
    return out


@_guard
def doctor(
    path: str | None = None,
    profile: str | None = None,
    show: str | None = None,
    live: str | None = None,
) -> str:
    """Run the advisory rules and report likely misconfigurations.

    Use when asked to check, review, or find problems in a scene. Each
    finding names the rule, the target, and which rule layer decided it
    (base for generic industry practice, toanaz for personal principles,
    show for one-off overrides). Rules switched off by a higher layer are
    listed too.

    Pass `profile` to apply one show profile from the knowledge
    directory. Pass `show` with a show-context YAML to also report where
    the cue sheet and the console disagree (rules Q1-Q7). Pass `live`
    with a console's IP to read a running desk instead of a file.
    """
    scene = _scene(path, show=show, live=live)
    found = scene.advisory.run(profile)
    text = render.findings(found, scene.advisory.suppressed(profile))
    scene.classifier.flush()
    return text
```

For `channel`, keep its existing body and signature shape, changing only
the loading line and the signature:

```python
@_guard
def channel(path: str | None = None, number: int = 1, live: str | None = None) -> str:
```

with `scene = _scene(path, live=live)` in place of its `WingScene.load(path)`.

Leave `diff` unchanged: it compares two files, and spec §6.2 handles the
live case on the CLI only.

- [ ] **Step 4: Run the tests to verify they pass**

```bash
python -m pytest tests/test_mcp.py -v
```

Expected: all pass, with the FastMCP test still skipping.

- [ ] **Step 5: Run the whole suite**

```bash
python -m pytest tests/
```

Expected: exit code 0.

- [ ] **Step 6: Commit**

```bash
git add wing_parser/mcp/tools.py tests/test_mcp.py
git commit -m "Give the MCP tools show and live, closing a question from G1"
```

---

### Task 6: `diff --live`

**Files:**
- Modify: `wing_parser/cli/__main__.py:58-62` — the `diff` subparser
- Modify: `wing_parser/cli/commands.py:122-129` — `diff`
- Test: `tests/test_cli.py` — append

**Interfaces:**
- Consumes: `_load(path, show, live)`, already present in `commands.py`.
- Produces: `wing diff [FILE ...] [--live-before IP] [--live-after IP]`, and a helper `_diff_sides(args) -> tuple[tuple[str | None, str | None], tuple[str | None, str | None]]` returning `((before_path, before_live), (after_path, after_live))`.

**Read this before writing — the obvious design does not work.** The natural
shape is two positionals, `before` and `after`, each in a mutually-exclusive
group with its own `--live-*` flag. **Measured 2026-08-21: argparse rejects it.**

```
diff --live-before 10.0.0.1 saved.snap
  -> error: argument before: not allowed with argument --live-before
```

Positionals are filled left to right, so the single remaining file lands in
`before` — the side already supplied by the flag — and the group conflict
fires. `wing diff saved.snap --live-after IP` happens to work, which makes the
bug look like it is not there.

So the positionals become **one list**, and arity is checked in the command.
Measured with that shape, all seven cases parse as intended: two files; a file
with either `--live-*`; both live; one file alone; none; three files.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_cli.py` (the module already imports `pytest`; confirm
before relying on it):

```python
def test_diff_parses_a_live_before_with_one_file():
    """The two-positional shape rejects this; the file list does not."""
    from wing_parser.cli.__main__ import build_parser

    args = build_parser().parse_args(
        ["diff", "--live-before", "10.0.0.1", "saved.snap"]
    )
    assert args.live_before == "10.0.0.1"
    assert args.files == ["saved.snap"]


def test_diff_sides_puts_the_lone_file_opposite_the_live_side():
    from types import SimpleNamespace

    from wing_parser.cli.commands import _diff_sides

    before, after = _diff_sides(
        SimpleNamespace(files=["saved.snap"], live_before="10.0.0.1", live_after=None)
    )
    assert before == (None, "10.0.0.1")
    assert after == ("saved.snap", None)

    before, after = _diff_sides(
        SimpleNamespace(files=["saved.snap"], live_before=None, live_after="10.0.0.1")
    )
    assert before == ("saved.snap", None)
    assert after == (None, "10.0.0.1")


def test_diff_sides_maps_two_files_in_order():
    from types import SimpleNamespace

    from wing_parser.cli.commands import _diff_sides

    before, after = _diff_sides(
        SimpleNamespace(files=["a.snap", "b.snap"], live_before=None, live_after=None)
    )
    assert before == ("a.snap", None)
    assert after == ("b.snap", None)


def test_diff_sides_accepts_two_live_consoles_and_no_files():
    from types import SimpleNamespace

    from wing_parser.cli.commands import _diff_sides

    before, after = _diff_sides(
        SimpleNamespace(files=[], live_before="10.0.0.1", live_after="10.0.0.2")
    )
    assert before == (None, "10.0.0.1")
    assert after == (None, "10.0.0.2")


@pytest.mark.parametrize(
    "files,live_before,live_after",
    [
        (["only.snap"], None, None),          # one file, neither side live
        ([], None, None),                     # nothing at all
        (["a", "b", "c"], None, None),        # three files
        (["a", "b"], "10.0.0.1", None),       # two files and a live side
        ([], "10.0.0.1", None),               # live side but nothing opposite
    ],
)
def test_diff_sides_refuses_an_arity_that_cannot_name_two_sides(
    files, live_before, live_after
):
    from types import SimpleNamespace

    from wing_parser.cli.commands import _diff_sides

    with pytest.raises(ValueError):
        _diff_sides(
            SimpleNamespace(
                files=files, live_before=live_before, live_after=live_after
            )
        )


def test_diff_of_two_files_still_works(vu_path, factory_path, capsys):
    from types import SimpleNamespace

    from wing_parser.cli import commands

    args = SimpleNamespace(
        files=[str(factory_path), str(vu_path)],
        limit=5,
        live_before=None,
        live_after=None,
    )
    assert commands.diff(args) == 0
    assert capsys.readouterr().out.strip()


def test_diff_reports_a_bad_arity_instead_of_raising(capsys):
    from types import SimpleNamespace

    from wing_parser.cli import commands

    args = SimpleNamespace(
        files=["only.snap"], limit=5, live_before=None, live_after=None
    )
    assert commands.diff(args) == 1
    assert "two sides" in capsys.readouterr().err
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
python -m pytest tests/test_cli.py -v -k diff
```

Expected: FAIL — `ImportError: cannot import name '_diff_sides'`

- [ ] **Step 3: Change the subparser**

Replace the `diff` block in `wing_parser/cli/__main__.py`:

```python
    node = sub.add_parser("diff", help="compare two scenes")
    # One file LIST, not two positionals. Two positionals -- each in a
    # mutually-exclusive group with its own --live-* flag -- is the
    # obvious shape and argparse rejects it: positionals fill left to
    # right, so `diff --live-before IP saved.snap` puts saved.snap into
    # `before`, the side the flag already supplied, and the group
    # conflict fires. Measured 2026-08-21. Arity is checked in
    # commands._diff_sides instead, which can also say what was wrong.
    node.add_argument(
        "files",
        nargs="*",
        metavar="FILE",
        help="one or two .snap files; one per side not supplied by --live-*",
    )
    node.add_argument(
        "--live-before", metavar="IP", help="read this console as the BEFORE side"
    )
    node.add_argument(
        "--live-after", metavar="IP", help="read this console as the AFTER side"
    )
    node.add_argument("--limit", type=int, default=50)
    node.set_defaults(handler=commands.diff)
```

- [ ] **Step 4: Change the command**

Replace `diff` in `wing_parser/cli/commands.py`, and add the helper above it:

```python
def _diff_sides(args) -> tuple[tuple[str | None, str | None], ...]:
    """Work out which side is a file and which is a console.

    Returns ((before_path, before_live), (after_path, after_live)).

    A lone file belongs to whichever side `--live-*` did not claim --
    that is what lets `diff --live-before IP saved.snap` mean what it
    reads like, given argparse cannot express it positionally.
    """
    files = list(args.files)
    live_before = args.live_before
    live_after = args.live_after
    wanted = (live_before is None) + (live_after is None)

    if len(files) != wanted:
        raise ValueError(
            f"diff needs two sides: {wanted} file(s) and got {len(files)}. "
            f"Supply one .snap per side not given by --live-before/--live-after."
        )

    before_path = None if live_before is not None else files.pop(0)
    after_path = None if live_after is not None else files.pop(0)
    return (before_path, live_before), (after_path, live_after)


def diff(args) -> int:
    try:
        (before_path, before_live), (after_path, after_live) = _diff_sides(args)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    before = _load(before_path, live=before_live)
    after = _load(after_path, live=after_live)
    if before is None or after is None:
        return 1
    print(render.changes(before.diff(after), limit=args.limit))
    before.classifier.flush()
    after.classifier.flush()
    return 0
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
python -m pytest tests/test_cli.py -v -k diff
```

Expected: all pass, including the five parametrised arity refusals.

- [ ] **Step 6: Check the real command still behaves**

```bash
python -m wing_parser.cli diff user-files/factory-scene.snap user-files/example-Vu.snap --limit 3
python -m wing_parser.cli diff user-files/factory-scene.snap
```

Expected: the first prints changes; the second prints
`error: diff needs two sides: 2 file(s) and got 1. ...` and exits 1.

- [ ] **Step 7: Run the whole suite and commit**

```bash
python -m pytest tests/
```

Expected: exit code 0.

```bash
git add wing_parser/cli/__main__.py wing_parser/cli/commands.py tests/test_cli.py
git commit -m "Let diff read a console on either side"
```

---

### Task 7: The five real scenes as a test corpus

**Files:**
- Add: `user-files/CAI LUONG.snap`, `user-files/GIAQUY_WING.snap`, `user-files/LIVE.snap`, `user-files/OCHESTRA.snap`, `user-files/Snapshot1.snap`
- Test: `tests/test_corpus_realfiles.py`

**Interfaces:** none — this task adds data and one test module.

**Before starting.** These five files are **not** in this worktree; untracked
files do not propagate across git worktrees. They live in the main worktree at
`Z:\My Drive\CLAUDE WORKS\DEV CAVE 2026\SOUNDTECH PLAYGROUND\user-files\`.
Copy them in.

**The consent that authorises this.** ToanAZ was told on 2026-08-21 that
committing writes these permanently into git history, including channel and
artist names, and confirmed the repo is private and he wants them in. Spec §6.3.

**Why it is worth doing.** The last cycle found a real parser bug — `build_dyn`
could not read a gate's `"1:3"` ratio — only because a live console exposed
what two reference files never did. A fivefold wider corpus is how that class
of bug gets found earlier.

- [ ] **Step 1: Copy the files in**

```powershell
$source = "Z:\My Drive\CLAUDE WORKS\DEV CAVE 2026\SOUNDTECH PLAYGROUND\user-files"
$target = "Z:\My Drive\CLAUDE WORKS\DEV CAVE 2026\SOUNDTECH PLAYGROUND\.claude\worktrees\project-capabilities-next-steps-8ec61c\user-files"
foreach ($name in @("CAI LUONG.snap", "GIAQUY_WING.snap", "LIVE.snap", "OCHESTRA.snap", "Snapshot1.snap")) {
    Copy-Item -Path (Join-Path $source $name) -Destination (Join-Path $target $name)
}
```

- [ ] **Step 2: Measure each file's finding count — do not assume the handoff's numbers**

```powershell
foreach ($name in @("CAI LUONG", "GIAQUY_WING", "LIVE", "OCHESTRA", "Snapshot1")) {
    $out = python -m wing_parser.cli doctor "user-files\$name.snap" | Select-Object -First 1
    Write-Output "$name : $out"
}
```

The handoff records 0, 13, 13, 1 and 17. **Use what this command prints**, not
those numbers. If any differs, that difference is itself a finding — say so in
the commit message rather than quietly writing the new number down.

- [ ] **Step 3: Write the test with the measured numbers**

`tests/test_corpus_realfiles.py`:

```python
"""Pinned finding counts for ToanAZ's five real scenes.

These are snapshot.9 files from WING Edit 3.0. They exist as a test
corpus because two reference files proved too narrow: the previous cycle
found that `build_dyn` could not read a gate's "1:3" ratio only when a
live console produced one, since neither reference file contains a gate
on a strip.

A change to any number here is a real behaviour change and must be
explained, not re-pinned.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from wing_parser.query.scene import WingScene

USER_FILES = Path(__file__).resolve().parent.parent / "user-files"

# Replace each count with what Step 2 actually printed.
EXPECTED = {
    "CAI LUONG": 0,
    "GIAQUY_WING": 13,
    "LIVE": 13,
    "OCHESTRA": 1,
    "Snapshot1": 17,
}


@pytest.mark.parametrize("name,count", sorted(EXPECTED.items()))
def test_each_real_scene_yields_its_pinned_finding_count(name, count):
    scene = WingScene.load(USER_FILES / f"{name}.snap")
    assert len(scene.advisory.run(None)) == count


@pytest.mark.parametrize("name", sorted(EXPECTED))
def test_each_real_scene_parses_as_a_recognised_schema(name):
    """WING Edit 3.0 writes snapshot.9. If a file ever stops being
    recognised, that is a versions.yaml regression, not a bad file."""
    scene = WingScene.load(USER_FILES / f"{name}.snap")
    assert scene.version.type_id == "snapshot.9"
```

If Step 2's output disagrees with the `EXPECTED` values above, edit them
to match the measurement. If `type_id` is not the attribute name on
`SceneVersion`, open `wing_parser/core/versions.py` and use the real one —
do not guess.

- [ ] **Step 4: Run the new tests**

```bash
python -m pytest tests/test_corpus_realfiles.py -v
```

Expected: 10 passed.

- [ ] **Step 5: Confirm .gitignore does not exclude them**

```bash
git check-ignore -v "user-files/CAI LUONG.snap"
```

Expected: no output (exit 1) — meaning the file is not ignored. If it *is*
ignored, report which `.gitignore` rule matched and stop; changing an ignore
rule is a separate decision.

- [ ] **Step 6: Run the whole suite and commit**

```bash
python -m pytest tests/
```

Expected: exit code 0.

```bash
git add "user-files/CAI LUONG.snap" user-files/GIAQUY_WING.snap user-files/LIVE.snap user-files/OCHESTRA.snap user-files/Snapshot1.snap tests/test_corpus_realfiles.py
git commit -m "Add five real scenes as a test corpus, with pinned counts"
```

---

### Task 8: Documentation, and the two live acceptance tests

**Files:**
- Modify: `README.md` — the live-console section
- Create: `skills/wing-watch/SKILL.md`
- Create: `docs/handoff/2026-08-21-live-watch-complete.md`

**Interfaces:** none.

- [ ] **Step 1: Run the two live acceptance experiments (spec §4.4)**

These need the lab console and a human. They are the two things the design
probes could **not** establish (spec §2.6). Record the actual output.

**Experiment 1 — detection.** Closes §2.6(2).

```powershell
python -m wing_parser.cli net watch 192.168.128.28 --until 60
```

While it runs, move one fader on the desk. Record: was the change reported,
which address, and how long after the move.

**Experiment 2 — coexistence.** Closes §2.6(3) and tests ToanAZ's hard
requirement directly.

Connect WING-Edit to the same console, then run:

```powershell
python -m wing_parser.cli net watch 192.168.128.28 --until 300
```

Drive the desk from WING-Edit throughout. Record whether either disturbed the
other.

**A negative result is written up, not retried into silence.** The
limiter-token probe is the precedent.

- [ ] **Step 2: Write the skill**

`skills/wing-watch/SKILL.md`, matching the five existing skills' shape:

```markdown
---
name: wing-watch
description: Use when asked what is changing on a live Behringer WING right now — which fader moved, what was muted or soloed — as opposed to reading a saved .snap file.
---

# Watching a live WING console

`wing net watch <ip>` reports changes on a running console by polling. It
subscribes to nothing, so it runs alongside WING-Edit, Companion or any
other controller without displacing them.

```
python -m wing_parser.cli net watch 192.168.128.28
python -m wing_parser.cli net watch 192.168.128.28 --json --until 120
```

It watches the effective values — `$fdr` and `$mute` already fold in DCA
contribution and mute-override, so pulling a DCA down shows up on every
channel it governs.

**What it cannot do.** It samples rather than streams, so a change that
appears and reverts inside one round is missed. There are no meters: the
WING exposes none over OSC (`docs/superpowers/specs/2026-08-21-live-watch-design.md` §2.3).

If the startup line warns that nodes did not resolve, those are not being
watched. Say so rather than reporting a quiet desk.
```

- [ ] **Step 3: Update the README**

Add `wing net watch` to the live-console section, alongside the existing
`net` commands, with one line on why it polls rather than subscribes.

- [ ] **Step 4: Write the handoff**

`docs/handoff/2026-08-21-live-watch-complete.md`, following the shape of
`2026-08-21-wing-net-complete.md`: what shipped, what each experiment in
Step 1 actually returned, what is still open, and what the cycle taught.

Carry forward, unchanged, the open questions from
`docs/handoff/2026-08-21-next-session-prompt.md` §5 that this cycle did not
close, and record that §5.4 (MCP `show`/`live`) **is** now closed by Task 5.

- [ ] **Step 5: Final whole-suite run**

```bash
python -m pytest tests/
python -m wing_parser.cli doctor user-files/example-Vu.snap
python -m wing_parser.cli doctor user-files/example-Vu.snap --profile small
python -m wing_parser.cli doctor user-files/example-Vu.snap --show tests/data/example-Vu-show.yaml
```

Expected: exit 0; then `22 findings`, `6 findings`, `27 findings`.

- [ ] **Step 6: Commit**

```bash
git add README.md skills/wing-watch docs/handoff/2026-08-21-live-watch-complete.md
git commit -m "Document the watch surface and record the live experiments"
```

---

## After every task

Per `docs/handoff/2026-08-21-next-session-prompt.md` §7: one fresh implementer
per task, a reviewer after each, scoped re-review per fix round, and **one final
whole-branch review on the strongest model**.

That last review is not ceremony. It caught `doctor --show --json` emitting
non-JSON one cycle, and `wing channel` labelling a matrix send as "bus" the
cycle before. Both were invisible to every per-task review by construction: the
flag and the print lived in different files, and no single task's diff held
both. Task 4 is this plan's candidate for exactly that shape of bug.
