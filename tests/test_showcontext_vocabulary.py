"""The typo repair is the one piece here with a correctness argument.

Spec section 3.1: repair radius 1 with a uniqueness requirement is safe
only because no two valid kinds sit closer than 2 apart. The first test
pins that premise so the radius cannot go unsafe when the vocabulary
grows.
"""
import itertools

import pytest

from wing_parser.classifier.matcher import known_kinds
from wing_parser.showcontext import vocabulary


def test_the_channel_vocabulary_stays_at_least_two_apart():
    kinds = known_kinds("channels")
    assert len(kinds) >= 30
    closest = min(
        (vocabulary.levenshtein(a, b), a, b)
        for a, b in itertools.combinations(kinds, 2)
    )
    # Measured 2026-08-17: 35 kinds, minimum 2 -- speech.lav <-> speech.qa
    # and speech.mc <-> speech.qa. A minimum of 1 would make radius-1
    # repair ambiguous for a pair of real kinds; re-argue the radius
    # before lowering this.
    assert closest[0] >= 2, f"{closest[1]} and {closest[2]} are {closest[0]} apart"


def test_known_kinds_reads_both_domains_and_is_sorted():
    assert "instrument.keys" in known_kinds("channels")
    assert "monitor.iem" in known_kinds("buses")
    assert list(known_kinds("channels")) == sorted(known_kinds("channels"))
    with pytest.raises(KeyError, match="cymbals"):
        known_kinds("cymbals")


@pytest.mark.parametrize(
    "written",
    ["Instrument.Keys", "  instrument keys  ", "instrument-keys", "INSTRUMENT_KEYS"],
)
def test_normalising_is_not_a_repair(written):
    resolved = vocabulary.resolve(written, known_kinds("channels"), what="kind")
    assert resolved.value == "instrument.keys"
    assert resolved.repaired is False


@pytest.mark.parametrize(
    "typo,expected",
    [
        ("instrument.kyes", "instrument.keys"),
        ("speech.lecturn", "speech.lectern"),
        ("drums.snare.tp", "drums.snare.top"),
    ],
)
def test_a_unique_near_miss_is_repaired_and_flagged(typo, expected):
    resolved = vocabulary.resolve(typo, known_kinds("channels"), what="kind")
    assert resolved.value == expected
    assert resolved.original == typo
    assert resolved.repaired is True


def test_a_tie_refuses_and_names_both_candidates():
    # speech.ma is one edit from speech.mc and one from speech.qa.
    with pytest.raises(ValueError) as caught:
        vocabulary.resolve("speech.ma", known_kinds("channels"), what="kind")
    message = str(caught.value)
    assert "speech.mc" in message and "speech.qa" in message


def test_a_miss_refuses_and_lists_the_vocabulary():
    with pytest.raises(ValueError) as caught:
        vocabulary.resolve("trombone", known_kinds("channels"), what="kind")
    assert "instrument.horns" in str(caught.value)


def test_short_tokens_are_never_repaired():
    # 'fx' is 2 characters; one edit is half the token, so 'fa' must
    # refuse rather than repair. Guards the buses domain and actions.
    with pytest.raises(ValueError):
        vocabulary.resolve("fa", known_kinds("buses"), what="role")


def test_actions_resolve_through_the_same_path():
    assert vocabulary.resolve("Open", vocabulary.KNOWN_ACTIONS, what="action").value == "open"
    assert vocabulary.resolve("recal", vocabulary.KNOWN_ACTIONS, what="action").repaired is True
    with pytest.raises(ValueError):
        vocabulary.resolve("up2", vocabulary.KNOWN_ACTIONS, what="action")
