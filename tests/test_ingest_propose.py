import pytest

from wing_parser import WingScene
from wing_parser.showcontext.ingest import propose
from wing_parser.showcontext.ingest.build import BuildResult, BuiltSegment
from wing_parser.showcontext.models import Segment
from wing_parser.showcontext.view import channels_of


@pytest.fixture(scope="module")
def scene(vu_path):
    """conftest.py provides vu_path (a Path), not a loaded scene."""
    return WingScene.load(vu_path)


def _results(pairs):
    """A BuildResult from (id, expects) pairs, so a multi-segment test is free.

    Every test in this file used to build one segment with id S1, and that
    shape is exactly why a duplicate-id collision -- one segment's channels
    proposed above another's -- passed eight gates unseen.
    """
    return BuildResult(
        segments=tuple(
            BuiltSegment(
                segment=Segment(id=segment_id, title="t", expects=expects),
                comments=(),
            )
            for segment_id, expects in pairs
        ),
        loose_comments=(), data_rows=len(pairs), comment_rows=0, blank_rows=0,
    )


def _result(expects):
    return _results([("S1", expects)])


def _a_confident_kind(scene):
    for channel in scene.channels():
        if channel.source_type.confidence >= 0.8:
            return channel.source_type.kind
    pytest.fail("the sample scene must classify at least one channel confidently")


def test_a_matched_kind_proposes_a_cue_naming_the_channel(scene):
    kind = _a_confident_kind(scene)
    numbers = [c.data.number for c in channels_of(scene, kind)]

    lines = propose.for_segments(_result((kind,)), scene)["S1"]
    body = "\n".join(lines)
    assert kind in body
    assert str(numbers[0]) in body
    assert "action: open" in body


def test_the_proposal_carries_every_matching_channel(scene):
    """A kind on three channels must propose all three, not just the first."""
    kind = max(
        {c.source_type.kind for c in scene.channels()
         if c.source_type.confidence >= 0.8},
        key=lambda k: len(channels_of(scene, k)),
    )
    numbers = sorted({c.data.number for c in channels_of(scene, kind)})
    body = "\n".join(propose.for_segments(_result((kind,)), scene)["S1"])
    for number in numbers:
        assert str(number) in body


def _two_confident_kinds(scene):
    kinds = sorted(
        {c.source_type.kind for c in scene.channels()
         if c.source_type.confidence >= 0.8},
        key=lambda k: (-len(channels_of(scene, k)), k),
    )
    if len(kinds) < 2:
        pytest.fail("the sample scene must classify two kinds confidently")
    return kinds[0], kinds[1]


def test_each_segment_gets_its_own_channels_and_not_another_segments(scene):
    """Two segments, because one segment cannot show a mixed-up key.

    A proposal naming a channel a segment does not expect is a statement
    the source never made, printed in the one place it is meant to be
    read literally.
    """
    first, second = _two_confident_kinds(scene)
    proposals = propose.for_segments(
        _results([("S1", (first,)), ("S2", (second,))]), scene
    )

    assert set(proposals) == {"S1", "S2"}
    one, two = "\n".join(proposals["S1"]), "\n".join(proposals["S2"])
    assert first in one and second not in one
    assert second in two and first not in two

    for number in {c.data.number for c in channels_of(scene, second)}:
        assert f"ch {number} " not in one


def test_an_unmatched_kind_proposes_nothing(scene):
    assert propose.for_segments(_result(("instrument.theremin",)), scene) == {}


def test_a_segment_with_no_expects_proposes_nothing(scene):
    assert propose.for_segments(_result(()), scene) == {}


def test_channels_of_is_public_and_the_private_name_is_gone():
    from wing_parser.showcontext import view

    assert hasattr(view, "channels_of")
    assert not hasattr(view, "_channels_of")
