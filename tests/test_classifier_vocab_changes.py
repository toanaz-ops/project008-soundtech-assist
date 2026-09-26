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


def test_validate_and_apply_agree_on_the_default_match(loaded, directory):
    """Fix round 2, minor 3: validate's default ("exact", checked against
    VALID_MATCH) and apply's default (passed to put_term) must be the
    SAME value, and both must match put_term's own default -- a change
    that never mentions "match" at all validates clean and, once
    applied, is stored with match: exact, not "word" (an earlier draft
    of apply used "word" here; both sites already say "exact", pinned so
    a future edit cannot quietly split them again)."""
    change = vocab_changes.Change(op="add", target="term", key="cajon", before=None,
                                  after={"kinds": ["drums.pad"]}, reason="no match given")
    assert vocab_changes.validate(change, loaded).valid
    vocab_changes.apply(change, loaded)
    reloaded = vocab.Vocabulary.load(directory)
    assert {t.key: t for t in reloaded.terms()}["cajon"].match == "exact"


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


# -- fix round 1 (e): a malformed reply must classify as BAD_REPLY, not
# OTHER -- MalformedReplyError is also a ProviderError -----------------


def test_a_malformed_changes_json_classifies_as_bad_reply():
    from wing_parser.classifier import provider_errors

    try:
        vocab_changes.propose_changes(
            _FakeProvider({"changes_json": "not json"}), vocabulary=None, known_kinds=())
    except Exception as exc:  # noqa: BLE001 - classifying it IS the point
        assert provider_errors.classify(exc)[0] == provider_errors.BAD_REPLY
    else:
        raise AssertionError("expected vocab_changes.MalformedReplyError")


def test_a_non_list_changes_json_also_classifies_as_bad_reply():
    from wing_parser.classifier import provider_errors

    try:
        vocab_changes.propose_changes(
            _FakeProvider({"changes_json": "{}"}), vocabulary=None, known_kinds=())
    except Exception as exc:  # noqa: BLE001 - classifying it IS the point
        assert provider_errors.classify(exc)[0] == provider_errors.BAD_REPLY
    else:
        raise AssertionError("expected vocab_changes.MalformedReplyError")


# -- fix round 1, I2: validate must be total against untrusted model
# output -- a shape violation becomes a row problem, never an exception --


def test_after_as_a_string_is_invalid_not_a_crash(loaded):
    change = vocab_changes.Change(op="add", target="term", key="x", before=None,
                                  after="not an object", reason="oops")
    result = vocab_changes.validate(change, loaded)
    assert not result.valid and result.problems


def test_after_as_a_list_is_invalid_not_a_crash(loaded):
    change = vocab_changes.Change(op="add", target="term", key="x", before=None,
                                  after=["not", "a", "dict"], reason="oops")
    result = vocab_changes.validate(change, loaded)
    assert not result.valid and result.problems


def test_kinds_with_a_non_string_item_is_invalid(loaded):
    change = vocab_changes.Change(op="add", target="term", key="x", before=None,
                                  after={"kinds": [{"k": 1}]}, reason="oops")
    result = vocab_changes.validate(change, loaded)
    assert not result.valid


def test_sets_that_is_not_a_list_is_invalid(loaded):
    change = vocab_changes.Change(op="add", target="term", key="x", before=None,
                                  after={"kinds": ["speech.mc"], "sets": "band"}, reason="oops")
    result = vocab_changes.validate(change, loaded)
    assert not result.valid


def test_ignore_as_a_truthy_string_does_not_become_true(loaded):
    """fix round 1, I4: bool("false") is True in Python -- ignore must be
    a real bool, not truthy-coerced."""
    change = vocab_changes.Change(op="add", target="term", key="x", before=None,
                                  after={"ignore": "false"}, reason="oops")
    result = vocab_changes.validate(change, loaded)
    assert not result.valid
    assert any("ignore" in p for p in result.problems)


def test_match_outside_exact_or_word_is_invalid(loaded):
    change = vocab_changes.Change(op="add", target="term", key="x", before=None,
                                  after={"kinds": ["speech.mc"], "match": "fuzzy"}, reason="oops")
    result = vocab_changes.validate(change, loaded)
    assert not result.valid
    assert any("match" in p for p in result.problems)


def test_propose_changes_turns_a_bad_item_into_an_invalid_row_but_keeps_the_rest(loaded):
    import json

    reply = {"changes_json": json.dumps([
        {"op": "add", "target": "term", "key": "x"},   # missing after/reason
        {"op": "add", "target": "term", "key": "cajon", "before": None,
         "after": {"kinds": ["drums.pad"]}, "reason": "a hand drum"},
    ])}
    changes = vocab_changes.propose_changes(
        _FakeProvider(reply), vocabulary=loaded, known_kinds=("drums.pad",))
    assert len(changes) == 2
    validated = [vocab_changes.validate(c, loaded) for c in changes]
    assert not validated[0].valid
    assert validated[1].valid and validated[1].change.key == "cajon"


# -- fix round 1, I3: the Before column (current_before) must be the real
# stored entry, and add-of-existing / edit-of-missing are problems -------


def test_add_of_an_existing_key_is_invalid(loaded):
    change = vocab_changes.Change(op="add", target="term", key="mc", before=None,
                                  after={"kinds": ["speech.mc"]}, reason="dup")
    result = vocab_changes.validate(change, loaded)
    assert not result.valid
    assert any("mc" in p for p in result.problems)


def test_edit_of_a_missing_key_is_invalid(loaded):
    change = vocab_changes.Change(op="edit", target="term", key="no such term",
                                  before=None, after={"kinds": ["speech.mc"]}, reason="oops")
    result = vocab_changes.validate(change, loaded)
    assert not result.valid


def test_current_before_returns_the_real_entry_not_the_models_claim(loaded):
    change = vocab_changes.Change(op="edit", target="term", key="mc",
                                  before={"kinds": ["bogus.claim"]},
                                  after={"kinds": ["speech.mc"]}, reason="x")
    before = vocab_changes.current_before(change, loaded)
    assert before is not None and before.kinds == ("speech.mc",)


def test_current_before_is_none_for_a_genuinely_new_key(loaded):
    change = vocab_changes.Change(op="add", target="term", key="brand new",
                                  before=None, after={"kinds": ["speech.mc"]}, reason="x")
    assert vocab_changes.current_before(change, loaded) is None


def test_current_before_shows_an_existing_default_for_a_delete(loaded):
    change = vocab_changes.Change(op="delete", target="term", key="mc",
                                  before=None, after=None, reason="x")
    before = vocab_changes.current_before(change, loaded)
    assert before is not None and before.key == "mc"
