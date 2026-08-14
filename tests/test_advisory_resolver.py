import pytest
import yaml

from wing_parser import WingScene
from wing_parser.advisory.resolver import active_rules, condition_holds, run


@pytest.fixture
def knowledge(tmp_path):
    directory = tmp_path / "knowledge"
    (directory / "shows").mkdir(parents=True)
    (directory / "classifier.yaml").write_text(
        yaml.safe_dump({"channels": {}, "buses": {}}), encoding="utf-8"
    )
    (directory / "principles.yaml").write_text(
        yaml.safe_dump({"principles": []}), encoding="utf-8"
    )
    return directory


@pytest.fixture
def scene(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    return WingScene.load(vu_path)


def test_only_base_rules_are_active_with_an_empty_principles_file(scene, knowledge):
    assert {r.id for r in active_rules(scene, directory=knowledge)} == {"G8", "G7", "E6"}


def test_monitor_bus_count_condition_reads_the_scene(scene):
    # MON VOX, MON L, MON R and SIDEFILL all classify as monitor buses.
    assert condition_holds(scene, {"monitor_bus_count": 1}) is False
    assert condition_holds(scene, {}) is True


def test_unknown_condition_is_false_not_an_error(scene):
    assert condition_holds(scene, {"phase_of_the_moon": "waxing"}) is False


def test_a_matching_flexible_principle_supersedes_its_base_rule(scene, knowledge, monkeypatch):
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.always-off-g8",
                        "principle": "G8 does not apply to my rigs",
                        "hardness": "hard",
                        "supersedes": ["G8"],
                        "rationale": "field practice",
                        "source": "ToanAZ",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    ids = {r.id for r in active_rules(scene, directory=knowledge)}
    assert "G8" not in ids
    assert "G7" in ids

    assert [f for f in run(scene, directory=knowledge) if f.rule_id == "G8"] == []


def test_a_flexible_principle_whose_condition_fails_does_not_supersede(scene, knowledge):
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.iem-shared-band.guitar-prefader",
                        "principle": "Shared band IEM",
                        "hardness": "flexible",
                        "applies_when": {"monitor_bus_count": 1},
                        "supersedes": ["G8"],
                        "rationale": "field practice",
                        "source": "ToanAZ",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    # This scene has more than one monitor bus, so the condition fails
    # and G8 survives.
    assert "G8" in {r.id for r in active_rules(scene, directory=knowledge)}


def test_a_disabled_principle_supersedes_nothing(scene, knowledge):
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.off",
                        "principle": "x",
                        "hardness": "hard",
                        "supersedes": ["G8"],
                        "rationale": "r",
                        "source": "ToanAZ",
                        "enabled": False,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    assert "G8" in {r.id for r in active_rules(scene, directory=knowledge)}


def test_a_show_override_beats_a_principle(scene, knowledge):
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump({"principles": []}), encoding="utf-8"
    )
    (knowledge / "shows" / "tonight.yaml").write_text(
        yaml.safe_dump(
            {
                "rules": [
                    {
                        "id": "show.no-g7",
                        "title": "Wedges tonight, no IEMs",
                        "severity": "info",
                        "source": "show sheet",
                        "rationale": "no in-ear packs on this show",
                        "supersedes": ["G7"],
                        "when": {"for_each": "bus", "where": {"bus.number": -1}},
                        "message": "never fires",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    ids = {r.id for r in active_rules(scene, directory=knowledge)}
    assert "G7" not in ids
    assert "show.no-g7" in ids
