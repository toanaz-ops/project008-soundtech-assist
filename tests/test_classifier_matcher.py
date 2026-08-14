import pytest

from wing_parser import WingScene
from wing_parser.classifier.matcher import (
    HIGH,
    LOW,
    classify,
    is_confident,
    is_usable,
)
from wing_parser.classifier.normalize import clean


def test_clean_strips_trailing_space_and_casefolds():
    assert clean("Kick In ") == "kick in"
    assert clean("  A.Guitar  ") == "a.guitar"
    assert clean("MON  VOX") == "mon vox"
    assert clean("") == ""


def test_clean_collapses_internal_whitespace():
    assert clean("Snare\tTop") == "snare top"


@pytest.mark.parametrize(
    "name,expected",
    [
        ("Kick In ", "drums.kick.in"),
        ("Kick Out", "drums.kick.out"),
        ("Snare Bot", "drums.snare.bottom"),
        ("Snare Top", "drums.snare.top"),
        ("Tom 8", "drums.tom"),
        ("Floor 16", "drums.tom"),
        ("Hihat", "drums.hihat"),
        ("OH", "drums.overhead"),
        ("Bass", "instrument.bass"),
        ("A.Guitar ", "instrument.guitar.acoustic"),
        ("E.Guitar 1", "instrument.guitar.electric"),
        ("Key 1", "instrument.keys"),
        ("Click", "utility.click"),
        ("LED PLAYBACK", "utility.playback"),
        ("BOH Talk", "utility.talkback"),
        ("FOH Tak", "utility.talkback"),          # typo in the real file
        ("Mic 1 VOX IEM1", "speech.vocal"),
        ("M8 MC", "speech.mc"),
        ("M6 D.PHOI", "utility.spare"),           # Vietnamese "du phong"
    ],
)
def test_real_channel_names_classify(name, expected):
    result = classify(name, "channels")
    assert result.kind == expected
    assert result.confidence >= HIGH, f"{name!r} scored {result.confidence}"


def test_more_specific_pattern_wins_on_a_tie():
    # "snare bot" and "snare" both match; the specific one must win.
    assert classify("Snare Bot", "channels").kind == "drums.snare.bottom"


def test_bare_mic_names_land_below_the_confidence_gate():
    for name in ("Mic 4", "Mic 5", "Mic 7"):
        result = classify(name, "channels")
        assert result.confidence < HIGH
        assert is_confident(result) is False


def test_genuinely_unclassifiable_names_are_unknown():
    result = classify("My Lap", "channels")
    assert result.kind == "unknown"
    assert result.confidence == 0.0
    assert is_usable(result) is False


def test_empty_name_is_unknown():
    assert classify("", "channels").kind == "unknown"


def test_bus_roles():
    assert classify("MON VOX", "buses").kind == "monitor"
    assert classify("MON L", "buses").kind == "monitor"
    assert classify("SIDEFILL", "buses").kind == "monitor"
    assert classify("HALL", "buses").kind == "fx"
    assert classify("DRUM FX", "buses").kind == "fx"
    assert classify("HAHA", "buses").kind == "fx"


def test_confidence_helpers():
    high = classify("Kick In", "channels")
    assert is_confident(high) and is_usable(high)

    weak = classify("Mic 4", "channels")
    assert not is_confident(weak)
    assert is_usable(weak) is (weak.confidence >= LOW)


def test_origin_is_recorded():
    assert classify("Kick In", "channels").origin == "pattern"


def test_monitor_buses_in_the_real_file_are_all_found(vu_path):
    scene = WingScene.load(vu_path)
    monitor_numbers = {
        bus.number
        for bus in scene.buses()
        if classify(bus.name, "buses").kind == "monitor"
        and classify(bus.name, "buses").confidence >= HIGH
    }
    assert {8, 9, 10} <= monitor_numbers      # MON VOX, MON L, MON R


def test_fx_buses_in_the_real_file(vu_path):
    scene = WingScene.load(vu_path)
    fx_numbers = {
        bus.number for bus in scene.buses() if classify(bus.name, "buses").kind == "fx"
    }
    assert {11, 12, 13, 14, 15, 16} <= fx_numbers
