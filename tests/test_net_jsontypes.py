"""Tests for wing_parser.net.jsontypes -- the boolean-shape oracle lookup.

Offline: the oracle is a static file under net/data/, generated ahead of
time by examples/generate_jsontypes.py (design doc S5). No test here
regenerates it or touches a console.
"""

from __future__ import annotations

from wing_parser.net.jsontypes import is_boolean_shape


def test_known_boolean_shape_is_reported_boolean():
    # ch/*/eq/on is one of the 342 shapes the oracle carries -- an EQ's
    # on/off toggle, boolean in both reference files.
    assert is_boolean_shape(["ch", "1", "eq", "on"]) is True


def test_known_non_boolean_int_shape_is_not_reported_boolean():
    # ch/*/col is a colour index (int [1..18], S2.3's own example of a
    # ,sfi leaf that is a plain int, never a boolean).
    assert is_boolean_shape(["ch", "1", "col"]) is False


def test_numeric_segments_collapse_to_the_same_shape():
    # design doc S5: ch/7/eq/on and ch/31/eq/on are the same shape path,
    # ch/*/eq/on, and must answer identically regardless of channel number.
    assert is_boolean_shape(["ch", "7", "eq", "on"]) == is_boolean_shape(
        ["ch", "31", "eq", "on"]
    )
    assert is_boolean_shape(["ch", "7", "eq", "on"]) is True


def test_ce_shapes_are_looked_up_rooted_at_ctl():
    # The oracle was generated with ce_data rooted at $ctl (S2.2/S5), so a
    # ce leaf's caller must include that segment for the lookup to match.
    assert is_boolean_shape(["$ctl", "cfg", "dcacc"]) is True
    # Without the root segment it is simply a different, unknown shape.
    assert is_boolean_shape(["cfg", "dcacc"]) is False


def test_unknown_shape_is_not_boolean():
    assert is_boolean_shape(["not", "a", "real", "shape"]) is False
