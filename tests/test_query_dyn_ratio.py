"""A dynamics ratio is a number for compressor models and the string "1:3"
for gate models.

Neither sample .snap exercises the string form -- both carry only CMB and
COMP -- so this went unnoticed until a live console was read. A WING
defaults its aux dynamics to GATE, so a scene saved from a desk nobody had
touched contained a ratio `float()` could not parse, and building the scene
raised instead of reporting.
"""

from __future__ import annotations

import pytest

from wing_parser.query.build_blocks import build_dyn


def test_a_compressor_ratio_is_read_as_a_number():
    assert build_dyn({"mdl": "COMP", "ratio": 3.0}).ratio == pytest.approx(3.0)


def test_a_numeric_string_ratio_is_still_read_as_a_number():
    """WING sends the ascii form for every parameter; a bare number in a
    string must not be discarded just because it arrived as text."""
    assert build_dyn({"mdl": "COMP", "ratio": "3.0"}).ratio == pytest.approx(3.0)


@pytest.mark.parametrize("token", ["1:3", "1:2", ""])
def test_a_gate_ratio_token_yields_none_rather_than_raising(token):
    dyn = build_dyn({"mdl": "GATE", "ratio": token})
    assert dyn.ratio is None
    assert dyn.model == "GATE"


def test_a_missing_dyn_block_still_builds():
    assert build_dyn(None).model == "NONE"


def test_the_rest_of_the_block_survives_an_unparseable_ratio():
    """The ratio is the only field that can carry the a:b form. Losing it
    must not cost the threshold or the timing values around it."""
    dyn = build_dyn(
        {"mdl": "GATE", "ratio": "1:3", "thr": -40.0, "att": 10.0, "rel": 199.4, "on": True}
    )
    assert dyn.ratio is None
    assert dyn.on is True
    assert dyn.threshold_dB == pytest.approx(-40.0)
    assert dyn.attack_ms == pytest.approx(10.0)
    assert dyn.release_ms == pytest.approx(199.4)
