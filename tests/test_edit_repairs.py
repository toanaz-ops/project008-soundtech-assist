"""Repair descriptors: loading them, and turning a finding into a patch."""

import json

import pytest

from wing_parser.edit import repairs
from wing_parser.query.scene import WingScene


@pytest.fixture
def findings(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    return WingScene.load(vu_path).advisory.run()


@pytest.fixture
def document(vu_path):
    return json.loads(vu_path.read_text(encoding="utf-8"))


def one(findings, rule_id):
    matched = [f for f in findings if f.rule_id == rule_id]
    assert matched, f"{rule_id} does not fire on the sample file"
    return matched[0]


def test_every_shipped_descriptor_carries_a_rationale():
    for rule_id, repair in repairs.load_repairs().items():
        assert repair.rationale.strip(), f"{rule_id} has no rationale"


def test_a_descriptor_without_a_rationale_is_refused():
    with pytest.raises(ValueError, match="rationale"):
        repairs.parse_repairs({"repairs": [
            {"rule": "X1", "kind": "set", "path": "a.b", "to": 1, "label": "x"}
        ]})


def test_an_unknown_kind_is_refused():
    with pytest.raises(ValueError, match="kind"):
        repairs.parse_repairs({"repairs": [
            {"rule": "X1", "kind": "sprinkle", "path": "a.b", "to": 1,
             "label": "x", "rationale": "y"}
        ]})


def test_a_set_descriptor_without_a_value_is_refused():
    # `to: null` is a legitimate value, so the check must be for the
    # key's presence, not its truthiness.
    with pytest.raises(ValueError, match="no 'to' value"):
        repairs.parse_repairs({"repairs": [
            {"rule": "X1", "kind": "set", "path": "a.b",
             "label": "x", "rationale": "y"}
        ]})


def test_parts_of_pairs_the_target_segments():
    assert repairs.parts_of("ch.1.send.8") == {"ch": "1", "send": "8"}
    assert repairs.parts_of("ch.16") == {"ch": "16"}
    assert repairs.parts_of("matrix.5") == {"matrix": "5"}


def test_g8_becomes_a_patch_naming_the_real_key(findings, document):
    patch = repairs.patch_for(one(findings, "G8"), document)

    assert patch.path.startswith("ae_data.ch.")
    assert patch.path.endswith(".mode")
    assert patch.before == "POST"
    assert patch.after == "PRE"
    assert patch.because.startswith("G8:")


def test_pb1_toggles_rather_than_setting_true(findings, document):
    patch = repairs.patch_for(one(findings, "PB1"), document)

    assert patch.path == "ae_data.ch.16.in.set.inv"
    assert patch.before is False
    assert patch.after is True


def test_a_toggle_flips_a_true_value_back(findings, document):
    # The half the sample file cannot show: PB1 fires when `inv` equals
    # the source polarity, so on a channel whose source is inverted the
    # rule fires with `inv` already True. A `set true` descriptor would
    # be a no-op there. Simulated by flipping the stored value first.
    document["ae_data"]["ch"]["16"]["in"]["set"]["inv"] = True
    patch = repairs.patch_for(one(findings, "PB1"), document)
    assert patch.before is True
    assert patch.after is False


def test_a_rule_with_no_descriptor_yields_no_patch(findings, document):
    # G10 states an absence -- no ambient mic anywhere in the scene --
    # and no single key edit answers it.
    assert repairs.patch_for(one(findings, "G10"), document) is None
