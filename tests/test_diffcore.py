"""Structured diff rows for the Diff page."""

from wing_parser.cli.diffcore import diff_rows


def _scene(path):
    from wing_parser import WingScene

    return WingScene.load(path)


def test_a_mutation_yields_rows(vu_path, tmp_path):
    import json

    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"]["8"]["fdr"] = -13.0  # any visible change
    out = tmp_path / "mutated.snap"
    out.write_text(json.dumps(doc), encoding="utf-8")

    rows = diff_rows(_scene(vu_path), _scene(out))
    assert rows
    assert all(row.before != row.after for row in rows)
    paths = [row.path for row in rows]
    assert paths == sorted(paths)


def test_identical_scenes_yield_no_rows(vu_path):
    scene = _scene(vu_path)
    assert diff_rows(scene, scene) == ()
