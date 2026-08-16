import pytest

from wing_parser import WingScene


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
