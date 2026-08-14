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


@pytest.mark.xfail(strict=True, reason="base_rules/*.yaml land in Task 20; strict xfail turns green again into a failure, forcing this marker's removal then")
def test_base_rules_load_from_the_package():
    rules = load_base_rules()
    assert {r.id for r in rules} == {"G8", "G7", "E6"}
    assert all(r.layer == "base" for r in rules)
    assert all(r.source and r.rationale for r in rules)
