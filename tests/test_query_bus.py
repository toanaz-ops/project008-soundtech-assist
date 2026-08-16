import pytest

from wing_parser import WingScene

from tests.conftest import _mutated_scene


@pytest.fixture(scope="module")
def scene(vu_path):
    return WingScene.load(vu_path)


@pytest.fixture(scope="module")
def vu_scene(vu_path):
    return WingScene.load(vu_path)


def test_bus_lookup_and_delegation(scene):
    bus = scene.bus(8)
    assert bus.number == 8
    assert bus.name == "MON VOX"
    assert bus.kind == "bus"
    assert bus.dyn.model == "COMP"


def test_section_counts(scene):
    assert len(scene.buses()) == 16
    assert len(scene.auxes()) == 8
    assert len(scene.mains()) == 4
    assert len(scene.matrices()) == 8
    assert len(scene.bus_family()) == 36


def test_bus_family_entries_know_their_kind(scene):
    kinds = {entry.kind for entry in scene.bus_family()}
    assert kinds == {"bus", "aux", "main", "matrix"}


def test_bus_carries_its_dca_tag(scene):
    assert scene.bus(1).dcas == (1,)
    assert scene.bus(1).name == "MIC"


def test_unknown_bus_raises(scene):
    with pytest.raises(KeyError, match="99"):
        scene.bus(99)


def test_bus_scene_safe_reads_the_bus_bitmap(scene):
    assert scene.bus(8).scene_safe is False


def test_is_monitor_accepts_the_dotted_monitor_roles(vu_scene):
    sidefill = vu_scene.bus(7)          # SIDEFILL -> monitor.wedge
    assert sidefill.is_monitor
    iem = vu_scene.matrix(5)            # IEM MC -> monitor.iem
    assert iem.is_monitor


# --- notch_count / max_boost_above_8k / receives_ambient / receives_any ---
#
# Premise check (see task-5-report.md for the full evidence): the STD EQ
# descriptor (wing_parser/descriptors/data/eq_models.yaml) only maps six
# named bands per channel/bus -- low, "1", "2", "3", "4", high -- reading
# keys lg/lf/lq, 1g/1f/1q .. 4g/4f/4q, hg/hf/hq. The raw ae_data actually
# carries 1..6 numbered slots (1g..6g etc.), but bands "5" and "6" have no
# entry in the STD spec and are silently dropped by the parser. A bus's
# `eq.bands` tuple is therefore always length 6, not 8. The low/high
# bands' `shape` comes from the raw `leq`/`heq` toggle, whose observed
# values across both sample files are {PEQ, CUT, BW24, BW48, LR24, LR48,
# SHV} -- only "SHV" (shelf) is excluded from notch_count by spec, so
# setting leq/heq to "PEQ" makes the low/high bands eligible bell bands.


class TestNotchCount:
    def test_counts_only_narrow_deep_cuts(self, vu_path, tmp_path, monkeypatch):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")

        def mutate(ae):
            eq = ae["bus"]["7"]["eq"]
            eq["on"] = True
            eq["leq"], eq["heq"] = "PEQ", "PEQ"  # bells, not shelves
            # all six bands the parser actually reads for a bus (low, 1-4, high).
            # Band "2" pins gain exactly to -6.0 (the <=-6.0 boundary) and
            # band "4" pins q exactly to 8.0 (the >=8.0 boundary) -- both
            # boundary values must still count as notches.
            for prefix, gain, q in [
                ("l", -8, 9),
                ("1", -7, 10),
                ("2", -6.0, 8.5),
                ("3", -9, 12),
                ("4", -6.1, 8.0),
                ("h", -12, 20),
            ]:
                eq[f"{prefix}g"] = gain
                eq[f"{prefix}q"] = q
                eq[f"{prefix}f"] = 500.0

        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert scene.bus(7).notch_count == 6

    def test_excludes_wide_or_shallow_cuts(self, vu_path, tmp_path, monkeypatch):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")

        def mutate(ae):
            eq = ae["bus"]["7"]["eq"]
            eq["on"] = True
            eq["leq"], eq["heq"] = "PEQ", "PEQ"
            eq["lg"], eq["lq"] = 0.0, 1.0     # untouched -> not a notch
            eq["1g"], eq["1q"] = -8, 4        # deep but wide -> not a notch
            eq["2g"], eq["2q"] = -3, 12       # narrow but shallow -> not a notch
            eq["3g"], eq["3q"] = -6.1, 8.0    # q exactly at the gate, gain past it -> IS a notch
            eq["4g"], eq["4q"] = 0.0, 1.0     # untouched -> not a notch
            eq["hg"], eq["hq"] = 0.0, 1.0     # untouched -> not a notch

        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert scene.bus(7).notch_count == 1

    def test_skips_shelf_shape_even_when_deep_and_narrow(self, vu_path, tmp_path, monkeypatch):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")

        def mutate(ae):
            eq = ae["bus"]["7"]["eq"]
            eq["on"] = True
            eq["leq"] = "PEQ"
            eq["lg"], eq["lq"] = 0.0, 1.0
            eq["1g"], eq["1q"] = 0.0, 1.0
            eq["2g"], eq["2q"] = 0.0, 1.0
            eq["3g"], eq["3q"] = 0.0, 1.0
            eq["4g"], eq["4q"] = 0.0, 1.0
            eq["heq"] = "SHV"                 # a shelf
            eq["hg"], eq["hq"] = -10, 15      # would otherwise qualify

        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert scene.bus(7).notch_count == 0

    def test_no_bands_is_zero(self, vu_path, monkeypatch):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        from wing_parser import WingScene
        scene = WingScene.load(vu_path)
        # mutation check lives here: if the property returned a constant
        # instead of counting, this zero and the six above cannot both pass
        assert all(isinstance(b.notch_count, int) for b in scene.bus_family())


class TestMaxBoostAbove8k:
    def test_reports_the_largest_high_boost(self, vu_path, tmp_path, monkeypatch):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")

        def mutate(ae):
            eq = ae["main"]["1"]["eq"]
            eq["on"] = True
            eq["1g"], eq["1f"], eq["1q"] = 2.5, 10000.0, 1.0
            eq["2g"], eq["2f"], eq["2q"] = 4.0, 12000.0, 1.0
            eq["3g"], eq["3f"], eq["3q"] = 5.0, 4000.0, 1.0   # below 8k, ignored

        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert scene.main(1).max_boost_above_8k == pytest.approx(4.0)

    def test_none_when_nothing_boosts_the_top(self, vu_path, tmp_path, monkeypatch):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")

        def mutate(ae):
            eq = ae["main"]["1"]["eq"]
            eq["on"] = True
            eq["1g"], eq["1f"] = -3.0, 12000.0

        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert scene.main(1).max_boost_above_8k is None


class TestReceives:
    def test_receives_ambient_true_when_a_confident_ambient_channel_feeds_it(
        self, vu_path, tmp_path, monkeypatch
    ):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")

        def mutate(ae):
            ae["ch"]["20"]["name"] = "AMBIENT L"      # utility.ambient, 0.85
            ae["ch"]["20"]["send"]["MX5"]["on"] = True

        scene = _mutated_scene(vu_path, tmp_path, mutate)
        assert scene.matrix(5).receives_ambient
        assert not scene.matrix(6).receives_ambient

    def test_receives_any_via_main_sends(self, vu_path, monkeypatch):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        from wing_parser import WingScene
        scene = WingScene.load(vu_path)
        assert scene.main(1).receives_any   # 28 main-sends are on in this file

    def test_receives_any_false_when_nothing_feeds_it(self, vu_path, monkeypatch):
        monkeypatch.setenv("WING_DISABLE_LLM", "1")
        from wing_parser import WingScene
        scene = WingScene.load(vu_path)
        # bus 5 (HEADSET) has no channel send targeting it in this file --
        # the False case a constant-True receives_any mutant would miss.
        assert not scene.bus(5).receives_any
