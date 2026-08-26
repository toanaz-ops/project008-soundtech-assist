"""Structured diff rows for the Diff page."""

import json

from wing_parser import WingScene
from wing_parser.cli.diffcore import diff_rows


def _scene(path):
    return WingScene.load(path)


def test_a_mutation_yields_rows(vu_path, tmp_path):
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"]["8"]["fdr"] = -13.0  # any visible change
    out = tmp_path / "mutated.snap"
    out.write_text(json.dumps(doc), encoding="utf-8")

    rows = diff_rows(_scene(vu_path), _scene(out))
    assert rows
    assert all(row.before != row.after for row in rows)
    paths = [row.path for row in rows]
    assert paths == sorted(paths)


def test_natural_order_survives_two_digit_channel_numbers(vu_path, tmp_path):
    """Lexicographic reads ch.10 before ch.2; the natural key must not."""
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"]["2"]["fdr"] = -100.0
    doc["ae_data"]["ch"]["10"]["fdr"] = -5.0
    out = tmp_path / "wide.snap"
    out.write_text(json.dumps(doc), encoding="utf-8")

    rows = diff_rows(_scene(vu_path), _scene(out))
    assert [row.path for row in rows] == [
        "ch.2.fader_dB",
        "ch.10.fader_dB",
    ]


def test_identical_scenes_yield_no_rows(vu_path):
    scene = _scene(vu_path)
    assert diff_rows(scene, scene) == ()
