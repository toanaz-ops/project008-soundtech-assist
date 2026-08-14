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
