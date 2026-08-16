import json

import pytest

from wing_parser import WingScene
from tests.conftest import _mutated_scene


@pytest.fixture()
def vu_scene(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    return WingScene.load(vu_path)


class TestIemSendCount:
    def test_counts_only_on_sends_to_iem_roles(self, vu_path, tmp_path, monkeypatch):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            ae["ch"]["20"]["name"] = "CLICK"
            for mx in ("MX5", "MX6", "MX7"):        # IEM MC, IEM CA SI 1/2
                ae["ch"]["20"]["send"][mx]["on"] = True
            ae["ch"]["20"]["send"]["MX1"]["on"] = True   # FLOWN -> pa_zone, not IEM
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert scene.channel(20).iem_send_count == 3

    def test_no_on_sends_gives_zero(self, vu_scene):
        # Sanity: an untouched channel has nothing routed to an IEM bus.
        assert vu_scene.channel(20).iem_send_count == 0


class TestEqShapes:
    def test_lowmid_cut_seen(self, vu_path, tmp_path, monkeypatch):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            eq = ae["ch"]["20"]["eq"]
            eq["on"] = True
            eq["1g"], eq["1f"], eq["1q"] = -3.0, 300.0, 1.4
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert scene.channel(20).eq_has_lowmid_cut

    def test_boost_in_the_lowmid_is_not_a_cut(self, vu_path, tmp_path, monkeypatch):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            eq = ae["ch"]["20"]["eq"]
            eq["on"] = True
            for i in range(1, 5):
                eq[f"{i}g"], eq[f"{i}f"] = 2.0, 300.0
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert not scene.channel(20).eq_has_lowmid_cut

    def test_presence_lift_seen(self, vu_path, tmp_path, monkeypatch):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            eq = ae["ch"]["20"]["eq"]
            eq["on"] = True
            eq["2g"], eq["2f"], eq["2q"] = 2.5, 3000.0, 1.0
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert scene.channel(20).eq_has_presence_lift

    def test_no_bands_in_range_gives_no_presence_lift(self, vu_scene):
        assert not vu_scene.channel(20).eq_has_presence_lift

    def test_lowmid_cut_lower_boundary_is_inclusive(self, vu_path, tmp_path, monkeypatch):
        # freq == 200.0 exactly must count -- pins the `>=` boundary.
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            eq = ae["ch"]["20"]["eq"]
            eq["on"] = True
            eq["1g"], eq["1f"], eq["1q"] = -2.0, 200.0, 1.4
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert scene.channel(20).eq_has_lowmid_cut

    def test_lowmid_cut_upper_boundary_is_inclusive(self, vu_path, tmp_path, monkeypatch):
        # freq == 500.0 exactly must count -- pins the `<=` boundary.
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            eq = ae["ch"]["20"]["eq"]
            eq["on"] = True
            eq["1g"], eq["1f"], eq["1q"] = -2.0, 500.0, 1.4
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert scene.channel(20).eq_has_lowmid_cut

    def test_freq_just_outside_lowmid_band_does_not_count(self, vu_path, tmp_path, monkeypatch):
        # freq == 500.1 is just past the upper boundary -- would pass under `<`.
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            eq = ae["ch"]["20"]["eq"]
            eq["on"] = True
            eq["1g"], eq["1f"], eq["1q"] = -2.0, 500.1, 1.4
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert not scene.channel(20).eq_has_lowmid_cut

    def test_gain_exactly_zero_is_not_a_cut(self, vu_path, tmp_path, monkeypatch):
        # gain == 0.0 must not count as a cut -- pins the strict `< 0.0`.
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            eq = ae["ch"]["20"]["eq"]
            eq["on"] = True
            eq["1g"], eq["1f"], eq["1q"] = 0.0, 300.0, 1.4
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert not scene.channel(20).eq_has_lowmid_cut

    def test_presence_lift_lower_boundary_is_inclusive(self, vu_path, tmp_path, monkeypatch):
        # freq == 2000.0 exactly must count -- pins the `>=` boundary.
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            eq = ae["ch"]["20"]["eq"]
            eq["on"] = True
            eq["2g"], eq["2f"], eq["2q"] = 2.0, 2000.0, 1.0
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert scene.channel(20).eq_has_presence_lift

    def test_presence_lift_upper_boundary_is_inclusive(self, vu_path, tmp_path, monkeypatch):
        # freq == 4000.0 exactly must count -- pins the `<=` boundary.
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            eq = ae["ch"]["20"]["eq"]
            eq["on"] = True
            eq["2g"], eq["2f"], eq["2q"] = 2.0, 4000.0, 1.0
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert scene.channel(20).eq_has_presence_lift

    def test_freq_just_outside_presence_band_does_not_count(self, vu_path, tmp_path, monkeypatch):
        # freq == 4000.1 is just past the upper boundary -- would pass under `<`.
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            eq = ae["ch"]["20"]["eq"]
            eq["on"] = True
            eq["2g"], eq["2f"], eq["2q"] = 2.0, 4000.1, 1.0
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert not scene.channel(20).eq_has_presence_lift

    def test_gain_exactly_zero_is_not_a_lift(self, vu_path, tmp_path, monkeypatch):
        # gain == 0.0 must not count as a lift -- pins the strict `> 0.0`.
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            eq = ae["ch"]["20"]["eq"]
            eq["on"] = True
            eq["2g"], eq["2f"], eq["2q"] = 0.0, 3000.0, 1.0
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert not scene.channel(20).eq_has_presence_lift


class TestInUse:
    def test_factory_scene_has_no_channel_in_use(self, factory_path, monkeypatch):
        # The spec's acceptance constraint: factory defaults are the
        # reference nothing-configured state. Faders there sit at -144.
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        scene = WingScene.load(factory_path)
        assert [c.number for c in scene.channels() if c.in_use] == []

    def test_a_patched_unmuted_routed_channel_with_fader_up_is_in_use(
        self, vu_path, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            ch = ae["ch"]["20"]
            ch["fdr"] = 0
            ch["mute"] = False
            ch["main"]["1"]["on"] = True
            ch["in"]["conn"]["grp"] = "A"
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert scene.channel(20).in_use

    def test_fader_exactly_at_floor_is_not_in_use(self, vu_path, tmp_path, monkeypatch):
        # fader_dB == -90.0 exactly must NOT count -- pins the strict `> -90.0`.
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            ch = ae["ch"]["20"]
            ch["fdr"] = -90.0
            ch["mute"] = False
            ch["main"]["1"]["on"] = True
            ch["in"]["conn"]["grp"] = "A"
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert not scene.channel(20).in_use

    def test_fader_just_above_floor_is_in_use(self, vu_path, tmp_path, monkeypatch):
        # fader_dB just above -90.0 must count -- pins the boundary from the other side.
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            ch = ae["ch"]["20"]
            ch["fdr"] = -89.9
            ch["mute"] = False
            ch["main"]["1"]["on"] = True
            ch["in"]["conn"]["grp"] = "A"
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert scene.channel(20).in_use

    def test_muted_channel_is_not_in_use(self, vu_path, tmp_path, monkeypatch):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            ch = ae["ch"]["20"]
            ch["fdr"] = 0
            ch["mute"] = True
            ch["main"]["1"]["on"] = True
            ch["in"]["conn"]["grp"] = "A"
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert not scene.channel(20).in_use

    def test_no_active_send_or_main_is_not_in_use(self, vu_path, tmp_path, monkeypatch):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            ch = ae["ch"]["20"]
            ch["fdr"] = 0
            ch["mute"] = False
            ch["in"]["conn"]["grp"] = "A"
            for mx in ch["send"]:
                ch["send"][mx]["on"] = False
            for m in ch["main"]:
                ch["main"][m]["on"] = False
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert not scene.channel(20).in_use

    def test_off_source_is_not_in_use(self, vu_path, tmp_path, monkeypatch):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        def mutate(ae):
            ch = ae["ch"]["20"]
            ch["fdr"] = 0
            ch["mute"] = False
            ch["main"]["1"]["on"] = True
            ch["in"]["conn"]["grp"] = "OFF"
        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert not scene.channel(20).in_use
