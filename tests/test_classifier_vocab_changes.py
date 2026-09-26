"""Spec §8.2: validate a proposed change before anything is written.
Nothing here calls a model -- propose_changes is exercised with a fake
Provider (see the assistant's own Qt test for the worker-threaded path).
"""
from __future__ import annotations

import pytest

from wing_parser.classifier import vocab_changes, vocabulary as vocab


@pytest.fixture
def directory(tmp_path):
    return tmp_path


@pytest.fixture
def loaded(directory):
    return vocab.Vocabulary.load(directory)


# -- parse --------------------------------------------------------------


def test_parse_reads_every_field():
    change = vocab_changes.parse({
        "op": "add", "target": "term", "key": "cajon",
        "before": None, "after": {"kinds": ["drums.pad"]}, "reason": "a hand drum",
    })
    assert change.op == "add" and change.key == "cajon" and change.after["kinds"] == ["drums.pad"]


def test_parse_raises_naming_a_missing_field():
    with pytest.raises(ValueError, match="reason"):
        vocab_changes.parse({"op": "add", "target": "term", "key": "x"})


# -- validate: add/edit ---------------------------------------------------


def test_a_valid_add_term_validates_clean(loaded):
    change = vocab_changes.Change(op="add", target="term", key="cajon", before=None,
                                  after={"kinds": ["drums.pad"]}, reason="a hand drum")
    result = vocab_changes.validate(change, loaded)
    assert result.valid and result.problems == ()


def test_an_unknown_kind_is_invalid_with_a_problem_named(loaded):
    change = vocab_changes.Change(op="add", target="term", key="x", before=None,
                                  after={"kinds": ["nonsense.kind"]}, reason="oops")
    result = vocab_changes.validate(change, loaded)
    assert not result.valid
    assert any("nonsense.kind" in p for p in result.problems)


def test_a_cycle_making_edit_is_invalid(loaded):
    loaded.put_set("loop a", label="Loop A", sets=("band",))
    change = vocab_changes.Change(op="edit", target="set", key="band", before=None,
                                  after={"label": "Band", "kinds": [], "sets": ["drum kit", "loop a"]},
                                  reason="oops")
    result = vocab_changes.validate(change, loaded)
    assert not result.valid


def test_an_empty_term_is_invalid(loaded):
    change = vocab_changes.Change(op="add", target="term", key="x", before=None,
                                  after={}, reason="oops")
    result = vocab_changes.validate(change, loaded)
    assert not result.valid


# -- validate: delete -----------------------------------------------------


def test_deleting_an_existing_term_is_valid(loaded):
    change = vocab_changes.Change(op="delete", target="term", key="mc", before=None,
                                  after=None, reason="unused")
    assert vocab_changes.validate(change, loaded).valid


def test_deleting_a_missing_key_is_invalid(loaded):
    change = vocab_changes.Change(op="delete", target="term", key="no such term",
                                  before=None, after=None, reason="unused")
    result = vocab_changes.validate(change, loaded)
    assert not result.valid


# -- apply ----------------------------------------------------------------


def test_apply_writes_an_add_with_ai_approved_origin(loaded, directory):
    change = vocab_changes.Change(op="add", target="term", key="cajon", before=None,
                                  after={"kinds": ["drums.pad"]}, reason="a hand drum")
    vocab_changes.apply(change, loaded)
    reloaded = vocab.Vocabulary.load(directory)
    terms = {t.key: t for t in reloaded.terms()}
    assert terms["cajon"].kinds == ("drums.pad",)
    assert terms["cajon"].origin == "ai-approved"
    assert terms["cajon"].match == "exact"


def test_apply_writes_a_delete(loaded, directory):
    change = vocab_changes.Change(op="delete", target="term", key="hoa tươi",
                                  before=None, after=None, reason="unused")
    vocab_changes.apply(change, loaded)
    reloaded = vocab.Vocabulary.load(directory)
    assert "hoa tươi" not in {t.key for t in reloaded.terms()}


# -- propose_changes (fake provider, no model) -----------------------------


class _FakeProvider:
    def __init__(self, reply):
        self._reply = reply

    def complete_json(self, system, user, schema):
        return self._reply


def test_propose_changes_parses_the_json_string_field(loaded):
    import json

    reply = {"changes_json": json.dumps([
        {"op": "add", "target": "term", "key": "cajon", "before": None,
         "after": {"kinds": ["drums.pad"]}, "reason": "a hand drum"},
    ])}
    changes = vocab_changes.propose_changes(
        _FakeProvider(reply), vocabulary=loaded, known_kinds=("drums.pad",))
    assert len(changes) == 1 and changes[0].key == "cajon"


def test_propose_changes_raises_on_a_non_json_string():
    with pytest.raises(ValueError, match="did not parse"):
        vocab_changes.propose_changes(
            _FakeProvider({"changes_json": "not json"}),
            vocabulary=None,
            known_kinds=(),
        )
