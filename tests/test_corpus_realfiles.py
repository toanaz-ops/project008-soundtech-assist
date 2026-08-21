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

# Measured directly via `python -m wing_parser.cli doctor` and via
# `scene.advisory.run(None)` on 2026-08-22; both agree.
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
    recognised, that is a versions.yaml regression, not a bad file.

    `known` is the half that catches a regression. `resolve()` keeps the
    id it was given and only flips `known` to False for an unrecognised
    one (core/versions.py: `replace(fallback, type_id=type_id,
    known=False)`), so asserting the id alone would stay true even with
    snapshot.9 deleted from the registry.
    """
    scene = WingScene.load(USER_FILES / f"{name}.snap")
    assert scene.version.type_id == "snapshot.9"
    assert scene.version.known is True
