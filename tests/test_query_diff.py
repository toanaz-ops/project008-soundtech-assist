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


def test_factory_versus_show_produces_many_changes(factory_path, vu_path):
    changes = WingScene.load(factory_path).diff(WingScene.load(vu_path))
    assert len(changes) > 100
    assert all(isinstance(c.path, str) for c in changes)
