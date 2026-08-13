import math

import pytest

from wing_parser.core.normalizer import (
    NEG_INF,
    from_db,
    int_keyed,
    is_silent,
    to_db,
)


def test_sentinel_becomes_negative_infinity():
    assert to_db(-144) == NEG_INF
    assert to_db(-144.0) == NEG_INF
    assert math.isinf(to_db(-144))


def test_real_levels_pass_through_as_floats():
    assert to_db(-7.899999619) == pytest.approx(-7.9, abs=1e-6)
    assert to_db(0) == 0.0
    assert isinstance(to_db(0), float)


def test_values_below_the_sentinel_are_still_silent_not_passed_through():
    # The console never writes below -144, but a corrupt file might.
    assert to_db(-200) == NEG_INF


def test_none_is_silent():
    assert to_db(None) == NEG_INF


def test_from_db_round_trips():
    assert from_db(NEG_INF) == -144.0
    assert from_db(-7.9) == pytest.approx(-7.9)


def test_int_keyed_converts_and_sorts():
    section = {"10": "j", "2": "b", "1": "a"}
    assert list(int_keyed(section).items()) == [(1, "a"), (2, "b"), (10, "j")]


def test_int_keyed_rejects_non_numeric_keys():
    with pytest.raises(ValueError, match="non-numeric"):
        int_keyed({"1": "a", "oops": "b"})


def test_is_silent():
    assert is_silent(NEG_INF) is True
    assert is_silent(-7.9) is False
