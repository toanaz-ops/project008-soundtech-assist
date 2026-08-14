import pytest

from wing_parser import WingScene


@pytest.fixture(scope="module")
def scene(vu_path):
    return WingScene.load(vu_path)


def test_dca_one_is_named_mic_and_has_bus_one_as_a_member(scene):
    dca = scene.dca(1)
    assert dca.name == "MIC"
    assert dca.fader_dB == pytest.approx(-3.8, abs=1e-5)
    assert ("bus", 1) in [(m.kind, m.number) for m in dca.members]


def test_dcas_one_to_six_hold_buses(scene):
    for number in range(1, 7):
        members = scene.dca(number).members
        assert members, f"DCA {number} should have members"
        assert all(m.kind == "bus" for m in members)


def test_dcas_eight_to_sixteen_hold_auxes(scene):
    # Every aux carries "#D8,#D<n>", so DCA 8 holds all eight of them.
    assert len(scene.dca(8).members) == 8
    assert all(m.kind == "aux" for m in scene.dca(8).members)


def test_no_input_channel_is_assigned_to_a_dca_in_this_file(scene):
    assigned = {m.number for n in range(1, 17) for m in scene.dca(n).members if m.kind == "channel"}
    assert assigned == set()


def test_mute_group_one_holds_the_band_channels(scene):
    members = scene.mute_group(1).members
    assert scene.mute_group(1).name == "FBAND"
    assert scene.mute_group(1).muted is True
    assert all(m.kind == "channel" for m in members)
    assert 13 in [m.number for m in members]      # "Kick In "


def test_mute_group_two_holds_the_playback_channels(scene):
    numbers = {m.number for m in scene.mute_group(2).members}
    assert {10, 12, 37, 38} <= numbers


def test_members_carry_their_names(scene):
    kick = next(m for m in scene.mute_group(1).members if m.number == 13)
    assert kick.name == "Kick In "


def test_empty_group_returns_an_empty_tuple(scene):
    assert scene.mute_group(7).members == ()
