from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

from wing_parser.advisory.loader import load_base_rules, load_rules
from wing_parser.advisory.predicates import all_match, matches, render, resolve_path
from wing_parser.classifier.matcher import Classification


@dataclass
class Leaf:
    on: bool = True
    model: str = "COMP"
    role: Classification = Classification("monitor", 0.9, "pattern")


@dataclass
class Node:
    number: int = 8
    name: str = "M8 MC"
    child: Leaf = None


@pytest.fixture
def context():
    return {"channel": Node(child=Leaf()), "send": Leaf(model="POST")}


def test_resolve_path_walks_attributes(context):
    assert resolve_path(context, "channel.number") == 8
    assert resolve_path(context, "channel.child.model") == "COMP"


def test_resolve_path_unwraps_a_classification_to_its_kind(context):
    assert resolve_path(context, "channel.child.role") == "monitor"


def test_resolve_path_returns_none_for_a_missing_branch(context):
    assert resolve_path(context, "channel.nope.deeper") is None


def test_scalar_expectation_is_equality():
    assert matches("POST", "POST") is True
    assert matches("TAP", "POST") is False
    assert matches(True, True) is True


def test_not_operator():
    assert matches("COMP", {"not": "LIM"}) is True
    assert matches("LIM", {"not": "LIM"}) is False


def test_in_and_not_in_operators():
    assert matches("COMP", {"in": ["COMP", "CMB"]}) is True
    assert matches("LIM", {"in": ["COMP", "CMB"]}) is False
    assert matches("LIM", {"not_in": ["COMP", "CMB"]}) is True


def test_numeric_operators():
    assert matches(-9.0, {"lt": -6.0}) is True
    assert matches(-3.0, {"lt": -6.0}) is False
    assert matches(12.0, {"gt": 6.0}) is True
    assert matches(None, {"gt": 6.0}) is False


def test_is_null_operator():
    assert matches(None, {"is_null": True}) is True
    assert matches("x", {"is_null": True}) is False
    assert matches("x", {"is_null": False}) is True


def test_all_match_requires_every_key(context):
    assert all_match(context, {"channel.number": 8, "send.model": "POST"}) is True
    assert all_match(context, {"channel.number": 8, "send.model": "TAP"}) is False


def test_all_match_on_an_empty_where_is_true(context):
    assert all_match(context, {}) is True


def test_render_substitutes_from_the_context(context):
    text = render("Channel {channel.number} ({channel.name}) is wrong", context)
    assert text == "Channel 8 (M8 MC) is wrong"


def test_render_leaves_an_unresolvable_token_visible(context):
    assert "{channel.missing}" in render("x {channel.missing} y", context)


def test_load_rules_reads_every_documented_field(tmp_path: Path):
    path = tmp_path / "r.yaml"
    path.write_text(
        yaml.safe_dump(
            {
                "rules": [
                    {
                        "id": "T1",
                        "title": "Test rule",
                        "severity": "warning",
                        "source": "somewhere",
                        "rationale": "because",
                        "requires_classifier": True,
                        "when": {"for_each": "channel", "where": {"muted": True}},
                        "message": "Channel {channel.number} is muted",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    rule = load_rules(path, layer="base")[0]
    assert rule.id == "T1"
    assert rule.layer == "base"
    assert rule.severity == "warning"
    assert rule.requires_classifier is True
    assert rule.for_each == "channel"
    assert rule.where == {"muted": True}
    assert rule.enabled is True


def test_an_explicit_null_optional_field_falls_back_to_its_default(tmp_path: Path):
    """`enabled:` with the value left off must not disable the rule."""
    path = tmp_path / "null.yaml"
    path.write_text(
        "rules:\n"
        "  - id: T4\n"
        "    title: t\n"
        "    severity: warning\n"
        "    source: s\n"
        "    rationale: r\n"
        "    enabled:\n"
        "    hardness:\n"
        "    when:\n"
        "      for_each: channel\n"
        "      where: {}\n"
        "    message: m\n",
        encoding="utf-8",
    )
    rule = load_rules(path, layer="base")[0]
    assert rule.enabled is True
    assert rule.hardness == "hard"


def test_an_explicit_false_still_disables_the_rule(tmp_path: Path):
    """The null fallback must not swallow a deliberate `enabled: false`."""
    path = tmp_path / "off.yaml"
    path.write_text(
        yaml.safe_dump(
            {"rules": [{"id": "T5", "title": "t", "severity": "warning",
                        "source": "s", "rationale": "r", "enabled": False,
                        "when": {"for_each": "channel", "where": {}},
                        "message": "m"}]}
        ),
        encoding="utf-8",
    )
    assert load_rules(path, layer="base")[0].enabled is False


def test_loader_rejects_an_unknown_severity(tmp_path: Path):
    path = tmp_path / "bad.yaml"
    path.write_text(
        yaml.safe_dump(
            {"rules": [{"id": "T2", "title": "t", "severity": "catastrophe",
                        "source": "s", "rationale": "r",
                        "when": {"for_each": "channel", "where": {}},
                        "message": "m"}]}
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="severity"):
        load_rules(path, layer="base")


def test_loader_requires_source_and_rationale(tmp_path: Path):
    path = tmp_path / "nosource.yaml"
    path.write_text(
        yaml.safe_dump(
            {"rules": [{"id": "T3", "title": "t", "severity": "warning",
                        "when": {"for_each": "channel", "where": {}},
                        "message": "m"}]}
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="source"):
        load_rules(path, layer="base")


def test_base_rules_load_from_the_package():
    rules = load_base_rules()
    assert {r.id for r in rules} == {
        "G8", "G7", "G9", "E6", "R1", "R2", "R3", "R3M",
    }
    assert all(r.layer == "base" for r in rules)
    assert all(r.source and r.rationale for r in rules)


def test_loader_rejects_an_unknown_predicate_operator(tmp_path: Path):
    # A typo'd operator (`gtt` for `gt`) used to reach `predicates.matches`
    # mid-run and raise there; it must be caught at load time instead, the
    # same moment every other slip in this file would be.
    path = tmp_path / "bad_operator.yaml"
    path.write_text(
        yaml.safe_dump(
            {"rules": [{"id": "T6", "title": "t", "severity": "warning",
                        "source": "s", "rationale": "r",
                        "when": {"for_each": "channel", "where": {"fader_dB": {"gtt": -6}}},
                        "message": "m"}]}
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="gtt"):
        load_rules(path, layer="base")


def test_loader_reports_a_yaml_syntax_error_by_file_and_reason(tmp_path: Path):
    path = tmp_path / "broken.yaml"
    path.write_text("rules:\n  - id: T7\n    title: [unterminated\n", encoding="utf-8")
    with pytest.raises(ValueError) as excinfo:
        load_rules(path, layer="base")
    assert "broken.yaml" in str(excinfo.value)


def test_loader_rejects_a_non_mapping_rule_entry(tmp_path: Path):
    # A bare string dropped into `rules:` where a mapping was meant.
    path = tmp_path / "bare_string.yaml"
    path.write_text("rules:\n  - just a string\n", encoding="utf-8")
    with pytest.raises(ValueError, match="mapping"):
        load_rules(path, layer="base")


def test_loader_rejects_a_non_mapping_when_block(tmp_path: Path):
    # `when: "for_each channel"` (a scalar, the single most common
    # YAML hand-edit slip) used to reach `when.get("for_each")` a few
    # lines down and raise a bare AttributeError instead of naming the
    # file and the rule.
    path = tmp_path / "scalar_when.yaml"
    path.write_text(
        yaml.safe_dump(
            {"rules": [{"id": "T8", "title": "t", "severity": "warning",
                        "source": "s", "rationale": "r",
                        "when": "for_each channel",
                        "message": "m"}]}
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="when"):
        load_rules(path, layer="base")


def _rule_doc(**when_extra):
    when = {"for_each": "channel", "where": {"channel.muted": True}}
    when.update(when_extra)
    return {"rules": [{"id": "T", "title": "t", "severity": "warning",
                       "source": "s", "rationale": "r", "when": when,
                       "message": "m"}]}


def test_any_of_clauses_are_read_into_the_rule(tmp_path: Path):
    path = tmp_path / "r.yaml"
    path.write_text(
        yaml.safe_dump(_rule_doc(any_of=[{"channel.number": 8},
                                         {"channel.name": "HS4"}])),
        encoding="utf-8",
    )
    rule = load_rules(path, layer="base")[0]
    assert rule.any_of == ({"channel.number": 8}, {"channel.name": "HS4"})


def test_an_empty_any_of_is_rejected(tmp_path: Path):
    """`any_of:` with the value left off would leave the rule with no OR at
    all, firing on every target that satisfies `where` -- the same
    present-but-null shape as `enabled:`."""
    path = tmp_path / "empty.yaml"
    path.write_text(
        "rules:\n"
        "  - id: T\n    title: t\n    severity: warning\n    source: s\n"
        "    rationale: r\n    message: m\n"
        "    when:\n      for_each: channel\n      where: {}\n"
        "      any_of:\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="any_of"):
        load_rules(path, layer="base")


def test_an_any_of_that_is_a_list_but_empty_is_rejected(tmp_path: Path):
    path = tmp_path / "empty-list.yaml"
    path.write_text(yaml.safe_dump(_rule_doc(any_of=[])), encoding="utf-8")
    with pytest.raises(ValueError, match="any_of"):
        load_rules(path, layer="base")


def test_a_non_list_any_of_is_rejected(tmp_path: Path):
    path = tmp_path / "scalar.yaml"
    path.write_text(yaml.safe_dump(_rule_doc(any_of="channel.number")), encoding="utf-8")
    with pytest.raises(ValueError, match="any_of"):
        load_rules(path, layer="base")


def test_a_non_mapping_any_of_clause_is_rejected(tmp_path: Path):
    """Each element of `any_of:` must itself be a mapping. A bare string
    dropped into the list (design spec section 4.2's table) used to reach
    `_validate_where` a few lines down and fail confusingly instead of
    naming the file, the rule and the offending clause directly."""
    path = tmp_path / "clause-string.yaml"
    path.write_text(
        yaml.safe_dump(_rule_doc(any_of=["channel.number"])), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="mapping"):
        load_rules(path, layer="base")


def test_a_nested_any_of_is_rejected(tmp_path: Path):
    """One level only. The predicate language stays small on purpose."""
    path = tmp_path / "nested.yaml"
    path.write_text(
        yaml.safe_dump(_rule_doc(any_of=[{"any_of": [{"channel.number": 8}]}])),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="nest"):
        load_rules(path, layer="base")


def test_an_unknown_operator_inside_an_any_of_clause_is_rejected(tmp_path: Path):
    """Operator validation stopped at `where` and must reach in here too."""
    path = tmp_path / "op.yaml"
    path.write_text(
        yaml.safe_dump(_rule_doc(any_of=[{"channel.number": {"greater": 8}}])),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="greater"):
        load_rules(path, layer="base")


def test_a_principle_may_also_carry_any_of(tmp_path: Path):
    """layers._as_rules reads the same when: block and must validate it
    the same way; the toanaz layer is the hand-edited one."""
    directory = tmp_path / "knowledge"
    directory.mkdir()
    (directory / "principles.yaml").write_text(
        "principles:\n"
        "  - id: p1\n    principle: x\n    source: s\n    rationale: r\n"
        "    when:\n      for_each: channel\n      where: {}\n"
        "      any_of:\n",
        encoding="utf-8",
    )
    from wing_parser.advisory.layers import _principles
    with pytest.raises(ValueError, match="any_of"):
        _principles(directory)


def test_a_supersede_only_rule_needs_no_when_or_message(tmp_path: Path):
    path = tmp_path / "show.yaml"
    path.write_text(
        yaml.safe_dump(
            {"rules": [{"id": "show.off", "title": "Wedges tonight",
                        "severity": "info", "source": "show sheet",
                        "rationale": "no in-ear packs", "supersedes": ["G8"]}]}
        ),
        encoding="utf-8",
    )
    rule = load_rules(path, layer="show")[0]
    assert rule.for_each == "none"
    assert rule.where == {}
    assert rule.supersedes == ("G8",)


def test_a_rule_with_a_when_block_still_needs_for_each(tmp_path: Path):
    """Omitting `when` entirely is the supersede-only case. Writing one
    with no for_each is a different thing and stays an error."""
    path = tmp_path / "bad.yaml"
    path.write_text(
        yaml.safe_dump(
            {"rules": [{"id": "T", "title": "t", "severity": "warning",
                        "source": "s", "rationale": "r", "message": "m",
                        "when": {"where": {}}}]}
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="for_each"):
        load_rules(path, layer="show")


def test_a_blank_when_is_not_treated_as_supersede_only(tmp_path: Path):
    """A `when:` key present but left blank (a plausible hand-edit slip)
    parses as YAML null, the same value `entry.get("when")` returns for a
    key that is simply absent. Testing key presence rather than the
    resolved value is what tells these apart: the blank case must still
    raise, not silently become a match-nothing supersede-only rule that
    also drops the `message` requirement with it."""
    path = tmp_path / "blank_when.yaml"
    path.write_text(
        "rules:\n"
        "  - id: T9\n    title: t\n    severity: warning\n    source: s\n"
        "    rationale: r\n    message: m\n    supersedes: [G8]\n"
        "    when:\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="NoneType"):
        load_rules(path, layer="show")


def test_a_rule_with_a_target_still_needs_a_message(tmp_path: Path):
    path = tmp_path / "nomsg.yaml"
    path.write_text(
        yaml.safe_dump(
            {"rules": [{"id": "T", "title": "t", "severity": "warning",
                        "source": "s", "rationale": "r",
                        "when": {"for_each": "channel", "where": {}}}]}
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="message"):
        load_rules(path, layer="show")


class TestStartsWith:
    def test_matches_a_prefix(self):
        assert matches("monitor.iem", {"starts_with": "monitor"})

    def test_exact_value_counts_as_its_own_prefix(self):
        assert matches("monitor", {"starts_with": "monitor"})

    def test_rejects_a_non_prefix(self):
        assert not matches("subgroup", {"starts_with": "monitor"})

    def test_none_is_false_not_an_error(self):
        assert not matches(None, {"starts_with": "monitor"})

    def test_a_number_is_false_not_an_error(self):
        assert not matches(7, {"starts_with": "monitor"})

    def test_registered_in_operators(self):
        from wing_parser.advisory.predicates import OPERATORS
        assert "starts_with" in OPERATORS
