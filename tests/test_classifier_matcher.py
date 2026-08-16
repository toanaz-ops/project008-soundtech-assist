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


def test_equal_confidence_is_broken_by_match_length():
    # "sub" and "fx" are both 0.85, so only len(matched) separates them.
    # This is the ONLY case that exercises _rank's length component --
    # "Snare Bot" above is decided on confidence alone (0.95 > 0.9) and
    # still passes with the length component removed.
    assert classify("SUB FX", "buses").kind == "subgroup"
    assert classify("FX SUB", "buses").kind == "subgroup"


def test_hh_mic_is_a_handheld_not_a_hihat():
    # drums.hihat matches '\bhh\b' at 0.9; the handheld entry must carry a
    # higher confidence to win, because length never gets consulted.
    assert classify("HH MIC", "channels").kind == "speech.handheld"
    assert classify("HH", "channels").kind == "drums.hihat"
    assert classify("Handheld 1", "channels").kind == "speech.handheld"


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
    # SIDEFILL split 2026-08-16 into its own monitor.wedge kind; see
    # test_wedge_and_sidefill_classify_as_monitor_wedge below.
    assert classify("SIDEFILL", "buses").kind == "monitor.wedge"
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


@pytest.mark.parametrize(
    "name", ["IEM", "IEM 1", "IEM1", "IEM2", "IEM-1", "IEM3 BAKUP", "In Ear 2"]
)
def test_an_iem_bus_is_a_monitor_however_it_is_numbered(name):
    # \biem\b has no word boundary between M and 3, so IEM1/IEM2/IEM3 --
    # the commonest numbering -- silently missed. Rule G8 fires on any
    # `monitor`-prefixed role; G7 (error) and G9 (warning) split on this
    # kind since 2026-08-16, so a missed IEM bus is a skipped bus.
    result = classify(name, "buses")
    assert result.kind == "monitor.iem"
    assert result.confidence == pytest.approx(0.95)


def test_a_sidefill_bus_is_a_monitor_even_when_named_just_side():
    # ToanAZ: "Side = sidefill speakers". The band hears a sidefill, not
    # the audience, so it is a monitor send rather than a house zone.
    # Split 2026-08-16: sidefills carry the monitor.wedge kind now.
    assert classify("SIDE", "buses").kind == "monitor.wedge"
    assert classify("SIDEFILL", "buses").kind == "monitor.wedge"


@pytest.mark.parametrize(
    "name, kind",
    [
        ("TB OUT", "talkback"),
        ("Talkback", "talkback"),
        ("MAIN FOH", "main"),
        ("FLOWN", "pa_zone"),
        ("CEN", "pa_zone"),
    ],
)
def test_the_roles_toanaz_named_from_the_real_file(name, kind):
    assert classify(name, "buses").kind == kind


def test_a_misspelling_stays_unknown_rather_than_being_guessed_at():
    # "RECODING" is a real typo in example-Vu.snap. Reporting it as
    # unresolved is the honest answer; pattern-matching typos is not.
    assert classify("RECODING", "buses").kind == "unknown"


@pytest.mark.parametrize("name", ["HS", "HS 4", "HS4", "HS1", "HS-4", "Headset"])
def test_a_headset_mic_is_found_however_it_is_numbered(name):
    # Same word-boundary flaw as the IEM one: \bhs\b has no boundary
    # between S and 4, so HS4 -- channel 11 in the real file -- missed.
    assert classify(name, "channels").kind == "speech.headset"


def test_iem_buses_classify_as_monitor_iem():
    for name in ("IEM1", "IEM MC", "in ear 2", "iem3 bakup"):
        assert classify(name, "buses").kind == "monitor.iem", name


def test_wedge_and_sidefill_classify_as_monitor_wedge():
    for name in ("WEDGE 1", "SIDEFILL", "side fill L", "SIDE"):
        assert classify(name, "buses").kind == "monitor.wedge", name


def test_generic_monitor_names_stay_plain_monitor():
    for name in ("MON VOX", "MON L", "Monitor 3"):
        assert classify(name, "buses").kind == "monitor", name


def test_a_headset_bus_groups_mics_and_is_not_a_monitor_send():
    # ToanAZ: "Headset co the la input headset mic, hoac group all headset
    # mic". Both readings are input-side. Classifying it monitor was wrong
    # about the category, not just under-confident -- and it put a source
    # subgroup in front of rules written for monitor sends.
    assert classify("HEADSET", "buses").kind == "subgroup"
    assert classify("STRING", "buses").kind == "subgroup"
