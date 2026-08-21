"""A console that never answered must not read as a clean desk.

`wing doctor --live <dead ip>` printed `No findings.` and exited 0 before
this: take_snapshot reports what did not resolve, and _load discarded the
report, so an empty scene reached the advisory engine and it truthfully
found nothing wrong with nothing.

No test here touches a real socket -- take_snapshot is replaced.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from wing_parser.cli import commands
from wing_parser.core.loader import RawScene
from wing_parser.core.versions import load_registry, resolve
from wing_parser.net.snapshot import SnapshotResult

DEAD_ROOTS = (
    "/cfg", "/io", "/ch", "/aux", "/bus", "/main", "/mtx",
    "/dca", "/mgrp", "/fx", "/cards", "/play", "/$ctl",
)


def _raw(ae: dict, ce: dict) -> RawScene:
    return RawScene(
        version=resolve("snapshot.11", load_registry()),
        ae=ae,
        ce=ce,
        meta={},
        path=None,
        source="wing://10.0.0.1",
    )


def _stub(monkeypatch, result: SnapshotResult) -> None:
    """Replace take_snapshot where _load imports it FROM.

    _load does `from wing_parser.net.snapshot import take_snapshot` inside
    the function body, so the name is looked up on the module at call
    time -- patching the module attribute is what takes effect.
    """
    monkeypatch.setattr(
        "wing_parser.net.snapshot.take_snapshot", lambda *a, **k: result
    )


def test_a_console_that_answered_nothing_is_an_error_not_an_empty_scene(
    monkeypatch, capsys
):
    _stub(
        monkeypatch,
        SnapshotResult(
            raw=_raw({}, {}), unresolved_nodes=DEAD_ROOTS, unresolved_leaves=()
        ),
    )

    assert commands._load(None, live="10.0.0.1") is None

    captured = capsys.readouterr()
    assert "10.0.0.1" in captured.err
    assert captured.out == ""


def test_doctor_on_an_unreachable_console_does_not_say_no_findings(
    monkeypatch, capsys
):
    """The whole point. `No findings.` on a desk nobody reached is the
    most dangerous sentence this tool can print."""
    from types import SimpleNamespace

    _stub(
        monkeypatch,
        SnapshotResult(
            raw=_raw({}, {}), unresolved_nodes=DEAD_ROOTS, unresolved_leaves=()
        ),
    )

    args = SimpleNamespace(
        file=None, live="10.0.0.1", json=False, profile=None, show=None
    )
    assert commands.doctor(args) == 1

    captured = capsys.readouterr()
    assert "No findings" not in captured.out
    assert "10.0.0.1" in captured.err


def test_a_partial_read_still_builds_a_scene_but_says_what_is_missing(
    monkeypatch, capsys, factory_path
):
    """Reaching most of a console is not the same failure as reaching
    none of it, and only one of them is fatal."""
    import json

    real = json.loads(Path(factory_path).read_text(encoding="utf-8"))

    _stub(
        monkeypatch,
        SnapshotResult(
            raw=_raw(real["ae_data"], real["ce_data"]),
            unresolved_nodes=("/fx/1",),
            unresolved_leaves=("/ch/1/fdr", "/ch/2/fdr"),
        ),
    )

    scene = commands._load(None, live="10.0.0.1")
    assert scene is not None

    complaint = capsys.readouterr().err
    assert "/fx/1" in complaint or "1 node" in complaint
    assert "2" in complaint          # the two unresolved leaves are counted


def test_a_complete_read_says_nothing_at_all(monkeypatch, capsys, factory_path):
    """A clean live read must stay silent -- a warning printed every time
    trains the reader to ignore it."""
    import json

    real = json.loads(Path(factory_path).read_text(encoding="utf-8"))

    _stub(
        monkeypatch,
        SnapshotResult(
            raw=_raw(real["ae_data"], real["ce_data"]),
            unresolved_nodes=(),
            unresolved_leaves=(),
        ),
    )

    scene = commands._load(None, live="10.0.0.1")
    assert scene is not None
    assert capsys.readouterr().err == ""
