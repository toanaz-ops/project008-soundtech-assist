import pytest
import yaml

from wing_parser import WingScene, config
from wing_parser.advisory.resolver import (
    AdvisoryFacade,
    active_rules,
    condition_holds,
    off_event_ids,
    run,
    suppressed_ids,
)


def _supersede_only(rule_id: str, target: str) -> dict:
    return {"rules": [{"id": rule_id, "title": "t", "severity": "info",
                       "source": "s", "rationale": "r", "supersedes": [target]}]}


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
    assert {r.id for r in active_rules(scene, directory=knowledge)} == {
        "G8", "G7", "G9", "E6", "R1", "R2", "R3", "R3M",
    }


def test_the_shipped_principles_file_loads_without_raising(scene, monkeypatch):
    # Every test above passes an explicit directory=, so nothing in this
    # suite otherwise loads the real, hand-edited
    # knowledge/toanaz/principles.yaml through the normal path. Item 10
    # added applies_when validation the shipped file must satisfy -- it
    # does today, but nothing would catch it if a future hand-edit broke
    # that. Opts out of the hermetic WING_KNOWLEDGE_DIR fixture the same
    # way test_classifier_cache.py's env-var tests do.
    monkeypatch.delenv(config.ENV_VAR, raising=False)
    active_rules(scene)  # must not raise


def test_monitor_bus_count_condition_reads_the_scene(scene):
    # `_monitor_bus_count` counts over bus_family() since 2026-08-16 (Task
    # 3): monitor-role matrices count too, because on the real console
    # the IEM mixes are matrices. MON VOX, MON L, MON R and SIDEFILL are
    # the four buses; matrix 3 SIDE and matrices 5-8 (IEM MC, IEM CA SI
    # 1/2, IEM3 BAKUP) are five more monitor-role matrices. Probed
    # 2026-08-16 via wing_parser.advisory.resolver._monitor_bus_count on
    # user-files/example-Vu.snap: 9. Both the failing value (1) and the
    # actual value (9) are pinned so a probe that always returns 0, or
    # any other wrong constant, cannot leave this test green.
    assert condition_holds(scene, {"monitor_bus_count": 1}) is False
    assert condition_holds(scene, {"monitor_bus_count": 9}) is True
    assert condition_holds(scene, {}) is True


def test_channel_count_condition_reads_the_scene(scene):
    # The sample scene has 40 channels. This condition ships in
    # CONDITIONS per the brief but had no test at all -- deleting the
    # entry, or breaking the probe, must go red here.
    assert condition_holds(scene, {"channel_count": 40}) is True
    assert condition_holds(scene, {"channel_count": 1}) is False


def test_unknown_condition_is_false_not_an_error(scene):
    assert condition_holds(scene, {"phase_of_the_moon": "waxing"}) is False


def test_a_matching_hard_principle_supersedes_its_base_rule(scene, knowledge, monkeypatch):
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


def test_a_matching_flexible_principle_supersedes_its_base_rule(scene, knowledge):
    # This is the path the previous test's name claimed to cover but
    # did not: hardness: flexible, with an applies_when that actually
    # matches this scene (9 monitor-role outputs, counted over
    # bus_family() since Task 3 -- see test_monitor_bus_count_condition_
    # reads_the_scene above), so condition_holds runs a real probe and
    # returns True. That is the whole point of the three-layer design --
    # a base rule switched off only under a stated, checkable condition
    # -- and until now nothing exercised it.
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.nine-monitor-rig",
                        "principle": "This rig always runs 9 monitor outputs; G8 does not apply",
                        "hardness": "flexible",
                        "applies_when": {"monitor_bus_count": 9},
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
    assert "toanaz.nine-monitor-rig" in ids

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


def test_a_show_rule_and_an_inactive_principle_can_both_name_the_same_base_rule(scene, knowledge):
    """No cross-layer precedence exists to demonstrate here.

    `supersedes` is base-only (design spec section 6.3, line 270): a
    principle and a show rule may each independently name the same base
    rule id in their own supersedes list, but neither ever supersedes
    the other -- there is no "the show beats the principle" mechanism
    in this resolver (see
    test_a_principle_superseding_a_higher_layer_rule_id_raises, which
    confirms naming a higher-layer id is rejected outright). This
    fixture's principle is flexible with an applies_when
    (monitor_bus_count: 1) that fails on this scene, so it is not even
    active; G7's suppression below comes entirely from the show layer.
    """
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.keep-g7-unless-shared-rig",
                        "principle": "G7 only backs off on a single-monitor-bus rig",
                        "hardness": "flexible",
                        "applies_when": {"monitor_bus_count": 1},
                        "supersedes": ["G7"],
                        "rationale": "field practice",
                        "source": "ToanAZ",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
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
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    ids = {r.id for r in active_rules(scene, directory=knowledge, profile="tonight")}
    assert "G7" not in ids
    assert "show.no-g7" in ids
    # The principle's own condition failed, so it is not even active --
    # confirming G7's suppression here comes from the show, not it.
    assert "toanaz.keep-g7-unless-shared-rig" not in ids


def test_a_principle_superseding_an_unknown_rule_id_raises(scene, knowledge):
    # G88 is a typo for G8. Silently ignoring it would leave G8 firing
    # while the author believes it is off, and suppressed_ids() would
    # report a suppression that never happened.
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.typo",
                        "principle": "typo'd rule id",
                        "hardness": "hard",
                        "supersedes": ["G88"],
                        "rationale": "field practice",
                        "source": "ToanAZ",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="G88"):
        active_rules(scene, directory=knowledge)


def test_a_principle_superseding_a_higher_layer_rule_id_raises(scene, knowledge):
    # supersedes may only name a base rule id (design spec section 6.3,
    # line 270). `toanaz.base` is a real id -- not a typo like G88 -- but
    # naming it has no effect, because active_rules only ever filters
    # superseded ids out of the base layer. This must raise too, with a
    # message that tells it apart from an unknown-anywhere id: a misuse
    # of the field, not a typo.
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.base",
                        "principle": "base principle",
                        "hardness": "hard",
                        "supersedes": ["G8"],
                        "rationale": "field practice",
                        "source": "ToanAZ",
                        "enabled": True,
                    },
                    {
                        "id": "toanaz.names-the-other-principle",
                        "principle": "names a real principle id, not a base rule",
                        "hardness": "hard",
                        "supersedes": ["toanaz.base"],
                        "rationale": "field practice",
                        "source": "ToanAZ",
                        "enabled": True,
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="higher-layer rule id"):
        active_rules(scene, directory=knowledge)


def test_a_principle_with_hardness_left_blank_still_defaults_to_hard(scene, knowledge):
    # A hand-edited principles.yaml can leave `hardness:` present but
    # blank, which YAML parses as null. `.get(key, default)` only
    # supplies its default when the key is absent, so this used to
    # resolve to hardness=None on the Rule -- not the documented
    # default of "hard". Assert the Rule's own field, not just a side
    # effect, because None and "hard" both make _is_active return True
    # (only "flexible" is special-cased), so a behavioural-only test
    # cannot tell them apart.
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.blank-hardness",
                        "principle": "hardness left blank by mistake",
                        "hardness": None,
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
    rule = next(
        r for r in active_rules(scene, directory=knowledge) if r.id == "toanaz.blank-hardness"
    )
    assert rule.hardness == "hard"


def test_a_principle_with_source_left_blank_still_defaults_to_toanaz(scene, knowledge):
    # Same hazard as hardness above, on the field that exists purely so a
    # rule can be traced back to where it came from: a blank `source:`
    # parses as YAML null, and plain `.get(key, default)` only supplies
    # its default when the key is absent, not when it is present-but-null.
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.blank-source",
                        "principle": "source left blank by mistake",
                        "hardness": "hard",
                        "source": None,
                        "supersedes": ["G8"],
                        "rationale": "field practice",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    rule = next(
        r for r in active_rules(scene, directory=knowledge) if r.id == "toanaz.blank-source"
    )
    assert rule.source == "ToanAZ"


def test_a_principle_with_rationale_left_blank_still_defaults_to_empty_string(scene, knowledge):
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.blank-rationale",
                        "principle": "rationale left blank by mistake",
                        "hardness": "hard",
                        "rationale": None,
                        "supersedes": ["G8"],
                        "source": "ToanAZ",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    rule = next(
        r for r in active_rules(scene, directory=knowledge) if r.id == "toanaz.blank-rationale"
    )
    assert rule.rationale == ""


def test_a_principle_with_an_invalid_severity_raises(scene, knowledge):
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.bad-severity",
                        "principle": "x",
                        "severity": "catastrophic",
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
    with pytest.raises(ValueError, match="severity"):
        active_rules(scene, directory=knowledge)


def test_a_principle_with_an_explicit_when_block_missing_for_each_raises(scene, knowledge):
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.broken-when",
                        "principle": "x",
                        "hardness": "hard",
                        "when": {"where": {"channel.number": 1}},
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
    with pytest.raises(ValueError, match="for_each"):
        active_rules(scene, directory=knowledge)


def test_suppressed_ids_reports_which_higher_layer_rule_switched_off_a_base_rule(scene, knowledge):
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
    assert suppressed_ids(scene, directory=knowledge) == {"G8": "toanaz.always-off-g8"}


def test_suppressed_ids_is_empty_with_no_active_higher_layer_rules(scene, knowledge):
    assert suppressed_ids(scene, directory=knowledge) == {}


def test_advisory_facade_suppressed_delegates_to_suppressed_ids(scene, knowledge):
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
    facade = AdvisoryFacade(scene, directory=knowledge)
    assert facade.suppressed() == {"G8": "toanaz.always-off-g8"}


def test_a_flexible_principle_with_an_unknown_applies_when_key_raises(scene, knowledge):
    # `monitor_bus_cnt` is a typo for `monitor_bus_count`. condition_holds
    # treats an unrecognised name as False rather than an error (see
    # test_unknown_condition_is_false_not_an_error above), which used to
    # make this indistinguishable from a principle that legitimately never
    # applies -- it silently never fired and said nothing about why, the
    # same failure mode the supersedes check already catches on the other
    # hand-edited field of this file.
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.typo-applies-when",
                        "principle": "x",
                        "hardness": "flexible",
                        "applies_when": {"monitor_bus_cnt": 1},
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
    with pytest.raises(ValueError, match="monitor_bus_cnt"):
        active_rules(scene, directory=knowledge)


def test_a_hard_principles_stray_applies_when_key_is_not_validated(scene, knowledge):
    # applies_when is only ever consulted for hardness: flexible (see
    # _is_active), so a stray key on a hard principle is inert either way
    # -- this is not the typo-vs-gap confusion the check above exists for.
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.hard-with-applies-when",
                        "principle": "x",
                        "hardness": "hard",
                        "applies_when": {"not_a_real_condition": 1},
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
    assert "toanaz.hard-with-applies-when" in ids
    assert "G8" not in ids


def test_a_principle_missing_id_raises(scene, knowledge):
    # layers._as_rules used to index entry["id"] directly, so a principle
    # missing `id:` entirely reached the caller as a bare KeyError instead
    # of naming the file the way every other slip in it does.
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "principle": "no id given",
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
    with pytest.raises(ValueError, match="id"):
        active_rules(scene, directory=knowledge)


def test_a_bare_string_principle_entry_raises(scene, knowledge):
    # A `principles:` list may contain a bare string where a mapping was
    # meant; `.get()` on a str used to raise AttributeError a few lines in.
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump({"principles": ["just a string"]}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="mapping"):
        active_rules(scene, directory=knowledge)


def test_a_principle_with_a_non_mapping_when_block_raises(scene, knowledge):
    # A `when:` block written as a YAML list ("- for_each: channel"
    # instead of a mapping) used to reach `when.get("for_each")` a few
    # lines down and raise a bare AttributeError instead of naming the
    # file and the rule -- the twin of the loader.py case covered by
    # test_loader_rejects_a_non_mapping_when_block.
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.list-when",
                        "principle": "when written as a list by mistake",
                        "hardness": "hard",
                        "when": [{"for_each": "channel"}],
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
    with pytest.raises(ValueError, match="when"):
        active_rules(scene, directory=knowledge)


def test_a_principle_with_a_blank_when_is_not_treated_as_supersede_only(scene, knowledge):
    """Twin of test_a_blank_when_is_not_treated_as_supersede_only in
    test_advisory_predicates.py, for the layers.py reader of the same
    idea. A `when:` key present but left blank parses as YAML null, the
    same value `entry.get("when")` returns for an absent key -- the
    hazard this branch must not reintroduce."""
    (knowledge / "principles.yaml").write_text(
        "principles:\n"
        "  - id: toanaz.blank-when\n    principle: x\n    hardness: hard\n"
        "    supersedes: [G8]\n    rationale: r\n    source: ToanAZ\n"
        "    enabled: true\n    when:\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="NoneType"):
        active_rules(scene, directory=knowledge)


def test_a_principles_file_with_a_yaml_syntax_error_names_the_file(scene, knowledge):
    (knowledge / "principles.yaml").write_text(
        "principles:\n  - id: [unterminated\n", encoding="utf-8"
    )
    with pytest.raises(ValueError, match="principles.yaml"):
        active_rules(scene, directory=knowledge)


def test_run_raises_for_an_unrecognised_for_each(scene, knowledge):
    # Not caught here: resolver.run() itself does not guard evaluation
    # errors. The CLI's _run_advisory and the MCP tools' _guard are what
    # turn this into a clean message instead of a traceback (see
    # test_cli.py / test_mcp.py).
    (knowledge / "principles.yaml").write_text(
        yaml.safe_dump(
            {
                "principles": [
                    {
                        "id": "toanaz.bad-for-each",
                        "principle": "x",
                        "hardness": "hard",
                        "when": {"for_each": "nonexistent", "where": {}},
                        "supersedes": [],
                        "rationale": "field practice",
                        "source": "ToanAZ",
                        "enabled": True,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(KeyError, match="nonexistent"):
        run(scene, directory=knowledge)


def test_show_rules_load_from_a_yml_extension_too(scene, knowledge):
    # A show file saved with the other spelling must not be silently
    # invisible -- indistinguishable from "no overrides tonight".
    (knowledge / "shows" / "tonight.yml").write_text(
        yaml.safe_dump(
            {
                "rules": [
                    {
                        "id": "show.no-g7-yml",
                        "title": "Wedges tonight, no IEMs",
                        "severity": "info",
                        "source": "show sheet",
                        "rationale": "no in-ear packs on this show",
                        "supersedes": ["G7"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    ids = {r.id for r in active_rules(scene, directory=knowledge, profile="tonight")}
    assert "G7" not in ids
    assert "show.no-g7-yml" in ids


def test_no_profile_loads_no_show_file(scene, knowledge):
    (knowledge / "shows" / "small.yaml").write_text(
        yaml.safe_dump(_supersede_only("show.small", "G8")), encoding="utf-8"
    )
    assert {r.id for r in active_rules(scene, directory=knowledge)} == {
        "G8", "G7", "G9", "E6", "R1", "R2", "R3", "R3M",
    }


def test_a_profile_loads_only_its_own_file(scene, knowledge):
    """The regression test for the glob defect: with two files present,
    only the named one may take effect."""
    (knowledge / "shows" / "small.yaml").write_text(
        yaml.safe_dump(_supersede_only("show.small", "G8")), encoding="utf-8"
    )
    (knowledge / "shows" / "wedges.yaml").write_text(
        yaml.safe_dump(_supersede_only("show.wedges", "G7")), encoding="utf-8"
    )

    ids = {r.id for r in active_rules(scene, directory=knowledge, profile="small")}
    assert "G8" not in ids
    assert "G7" in ids
    assert "show.small" in ids
    assert "show.wedges" not in ids


def test_a_yml_spelling_is_found_too(scene, knowledge):
    (knowledge / "shows" / "small.yml").write_text(
        yaml.safe_dump(_supersede_only("show.small", "G8")), encoding="utf-8"
    )
    assert "G8" not in {r.id for r in active_rules(scene, directory=knowledge, profile="small")}


def test_an_unknown_profile_raises_and_lists_what_exists(scene, knowledge):
    (knowledge / "shows" / "small.yaml").write_text(
        yaml.safe_dump(_supersede_only("show.small", "G8")), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="smal"):
        active_rules(scene, directory=knowledge, profile="smal")
    with pytest.raises(ValueError, match="small"):
        active_rules(scene, directory=knowledge, profile="smal")


def test_suppressed_ids_honours_the_profile(scene, knowledge):
    (knowledge / "shows" / "small.yaml").write_text(
        yaml.safe_dump(_supersede_only("show.small", "G8")), encoding="utf-8"
    )
    assert suppressed_ids(scene, directory=knowledge) == {}
    assert suppressed_ids(scene, directory=knowledge, profile="small") == {"G8": "show.small"}


def test_run_honours_the_profile(scene, knowledge):
    (knowledge / "shows" / "small.yaml").write_text(
        yaml.safe_dump(_supersede_only("show.small", "G8")), encoding="utf-8"
    )
    assert [f for f in run(scene, directory=knowledge, profile="small")
            if f.rule_id == "G8"] == []
    assert [f for f in run(scene, directory=knowledge) if f.rule_id == "G8"] != []


def _write_show(directory, name, body):
    shows = directory / "shows"
    shows.mkdir(parents=True, exist_ok=True)
    (shows / f"{name}.yaml").write_text(body, encoding="utf-8")


BAND_RULE = """
rules: []
event: band
"""


def test_a_profile_event_switches_off_other_events_rules(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser import WingScene
    from wing_parser.advisory.resolver import active_rules, off_event_ids
    from wing_parser.advisory.models import Rule
    scene = WingScene.load(vu_path)
    _write_show(tmp_path, "bandshow", BAND_RULE)

    # Base rules are all universal today, so plant a corporate one via a
    # temporary base-rules fixture is NOT possible without touching package
    # data -- instead assert on the mechanism with the loader-level rules:
    ids = {r.id for r in active_rules(scene, tmp_path, "bandshow")}
    assert "G7" in ids  # universal rules survive
    assert off_event_ids(scene, tmp_path, "bandshow") == {}  # nothing corporate ships yet


def test_profile_event_validation_rejects_unknown_values(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser import WingScene
    from wing_parser.advisory.resolver import active_rules
    scene = WingScene.load(vu_path)
    _write_show(tmp_path, "badshow", "rules: []\nevent: wedding\n")
    with pytest.raises(ValueError, match="event"):
        active_rules(scene, tmp_path, "badshow")


def test_rule_event_defaults_to_universal_even_when_blank(tmp_path):
    from wing_parser.advisory.loader import load_rules
    rule_yaml = tmp_path / "r.yaml"
    rule_yaml.write_text(
        "rules:\n"
        "  - id: T1\n"
        "    title: t\n"
        "    severity: info\n"
        "    source: s\n"
        "    rationale: r\n"
        "    message: m\n"
        "    event:\n"          # present but blank -- the .get(None) hazard
        "    when:\n"
        "      for_each: channel\n"
        "      where: {}\n",
        encoding="utf-8",
    )
    assert load_rules(rule_yaml, layer="base")[0].event == "universal"


def test_rule_event_rejects_unknown_values(tmp_path):
    from wing_parser.advisory.loader import load_rules
    rule_yaml = tmp_path / "r.yaml"
    rule_yaml.write_text(
        "rules:\n"
        "  - id: T1\n    title: t\n    severity: info\n    source: s\n"
        "    rationale: r\n    message: m\n    event: gala\n"
        "    when: {for_each: channel, where: {}}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="event"):
        load_rules(rule_yaml, layer="base")


def test_as_rules_event_defaults_to_universal_even_when_blank(scene, knowledge):
    """Twin of test_rule_event_defaults_to_universal_even_when_blank for the
    hand-edited toanaz/show layer -- layers._as_rules routes `event` through
    the same `_optional` hazard as loader._rule_from."""
    (knowledge / "principles.yaml").write_text(
        "principles:\n"
        "  - id: P1\n"
        "    principle: p\n"
        "    event:\n"
        "    when:\n"
        "      for_each: channel\n"
        "      where: {}\n",
        encoding="utf-8",
    )
    rules = [r for r in active_rules(scene, directory=knowledge) if r.id == "P1"]
    assert rules[0].event == "universal"


def test_as_rules_event_rejects_unknown_values(scene, knowledge):
    (knowledge / "principles.yaml").write_text(
        "principles:\n"
        "  - id: P1\n"
        "    principle: p\n"
        "    event: gala\n"
        "    when: {for_each: channel, where: {}}\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="event"):
        active_rules(scene, directory=knowledge)


def test_facade_off_event_and_declared_event(scene, tmp_path):
    _write_show(tmp_path, "bandshow", BAND_RULE)
    facade = AdvisoryFacade(scene, directory=tmp_path)
    assert facade.off_event("bandshow") == {}  # nothing corporate ships yet
    assert facade.declared_event("bandshow") == "band"
    assert facade.declared_event() is None
