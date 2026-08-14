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
