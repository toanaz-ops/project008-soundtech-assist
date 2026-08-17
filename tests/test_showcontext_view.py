"""Derived counts, resolved against the real sample scene.

Every expected number below was read off user-files/example-Vu.snap,
not assumed: channel 29 is "Key 1" (instrument.keys), channel 41 is
absent from the file entirely (the scene only has channels 1-40), and
channel 4 is named "Mic 4".
"""
import pytest

from wing_parser import WingScene
from wing_parser.showcontext import view
from wing_parser.showcontext.models import Cue, Segment, ShowContext


@pytest.fixture
def scene(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    return WingScene.load(vu_path)


def _context(*segments):
    return ShowContext(show="t", segments=tuple(segments))


def test_a_cue_naming_an_absent_channel_counts_it(scene):
    context = _context(Segment(id="S1", cues=(
        Cue(id="SQ 1", action="open", channels=(29, 41)),)))
    cue = view.build(context, scene)[0].cues[0]
    assert cue.missing_channel_count == 1
    assert "41" in cue.missing_channels_text
    assert cue.unnamed_channel_count == 0


def test_a_cue_naming_a_present_but_unnamed_channel_counts_it(scene):
    # Channel 41 is absent; some channels in range are present but blank.
    # Use a channel the file has with an empty name -- probe before
    # pinning if this changes.
    named = {c.number for c in scene.channels() if c.name.strip()}
    blank = sorted({c.number for c in scene.channels()} - named)
    assert blank, "sample file has no unnamed channel; re-probe this test"
    context = _context(Segment(id="S1", cues=(
        Cue(id="SQ 1", action="open", channels=(blank[0],)),)))
    cue = view.build(context, scene)[0].cues[0]
    assert cue.unnamed_channel_count == 1
    assert cue.missing_channel_count == 0


def test_a_cue_naming_an_absent_dca_counts_it(scene):
    highest = max(scene.dcas) if scene.dcas else 0
    context = _context(Segment(id="S1", cues=(
        Cue(id="SQ 1", action="open", dcas=(highest + 1,)),)))
    assert view.build(context, scene)[0].cues[0].missing_dca_count == 1


def test_opening_an_already_open_channel_is_a_contradiction(scene):
    context = _context(Segment(id="S1", cues=(
        Cue(id="SQ 1", action="open", channels=(29,)),
        Cue(id="SQ 2", action="open", channels=(29,)),)))
    cues = view.build(context, scene)[0].cues
    assert cues[0].contradiction_count == 0
    assert cues[1].contradiction_count == 1
    assert "29" in cues[1].contradictions_text


def test_a_level_move_does_not_touch_the_open_book(scene):
    context = _context(Segment(id="S1", cues=(
        Cue(id="SQ 1", action="up", channels=(29,)),
        Cue(id="SQ 2", action="open", channels=(29,)),)))
    assert [c.contradiction_count for c in view.build(context, scene)[0].cues] == [0, 0]


def test_state_carries_across_segments(scene):
    context = _context(
        Segment(id="S1", cues=(Cue(id="SQ 1", action="open", channels=(29,)),)),
        Segment(id="S2", cues=(Cue(id="SQ 2", action="open", channels=(29,)),)),
    )
    segments = view.build(context, scene)
    assert segments[1].cues[0].contradiction_count == 1


def test_an_expected_kind_with_no_channel_is_unmet(scene):
    context = _context(Segment(id="S1", expects=("instrument.horns",)))
    segment = view.build(context, scene)[0]
    assert segment.unmet_expect_count == 1
    assert "instrument.horns" in segment.unmet_expects_text


def test_an_expected_kind_whose_channels_are_all_parked_is_dark(scene):
    # Channel 29 "Key 1" classifies instrument.keys and is at -inf on
    # this file, so the kind is present but not in use.
    context = _context(Segment(id="S1", expects=("instrument.keys",)))
    segment = view.build(context, scene)[0]
    assert segment.unmet_expect_count == 0
    assert segment.dark_expect_count == 1


def test_seconds_between_timed_cues(scene):
    context = _context(Segment(id="S1", cues=(
        Cue(id="SQ 1", action="open", channels=(29,), time="T+00:18:00"),
        Cue(id="SQ 2", action="close", channels=(29,), time="T+00:18:04"),)))
    cues = view.build(context, scene)[0].cues
    assert cues[0].seconds_after_previous is None
    assert cues[1].seconds_after_previous == pytest.approx(4.0)


def test_an_untimed_cue_yields_no_gap(scene):
    context = _context(Segment(id="S1", cues=(
        Cue(id="SQ 1", action="open", channels=(29,), time="T+00:18:00"),
        Cue(id="SQ 2", action="close", channels=(29,)),)))
    assert view.build(context, scene)[0].cues[1].seconds_after_previous is None
