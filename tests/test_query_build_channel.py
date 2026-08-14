import math

import pytest

from wing_parser.core.loader import load_raw
from wing_parser.core.normalizer import NEG_INF
from wing_parser.query.build_channel import build


@pytest.fixture(scope="module")
def ch8(vu_path):
    data, anomalies = build(8, load_raw(vu_path).ae["ch"]["8"])
    assert anomalies == []
    return data


def test_scalar_fields(ch8):
    assert ch8.number == 8
    assert ch8.name == "M8 MC"
    assert ch8.muted is False
    assert ch8.fader_dB == pytest.approx(-7.9, abs=1e-6)
    assert ch8.solo_safe is False


def test_proc_chain_and_tap_point(ch8):
    assert ch8.proc_raw == "GEDI"
    assert ch8.proc_chain == ("GATE", "EQ", "DELAY", "INSERT")
    assert ch8.tap_point == "POST_FDR"


def test_filter_fields(ch8):
    assert ch8.filter.low_cut_on is True
    assert ch8.filter.low_cut_hz == pytest.approx(151.06, abs=0.01)
    assert ch8.filter.low_cut_slope == 24
    assert ch8.filter.high_cut_on is False


def test_gate_fields(ch8):
    assert ch8.gate.on is True
    assert ch8.gate.model == "GATE"
    assert ch8.gate.threshold_dB == pytest.approx(-62.0)
    assert ch8.gate.range_dB == pytest.approx(12.0)


def test_post_insert_carries_the_automix_group_and_weight(ch8):
    assert ch8.post_insert.on is False
    assert ch8.post_insert.automix_group == "X"
    assert ch8.post_insert.automix_weight == pytest.approx(-12.0)
    assert ch8.pre_insert.automix_group is None


def test_source_refs(ch8):
    assert ch8.source_ref.group == "A"
    assert ch8.source_ref.index == 8
    assert ch8.alt_source_ref.is_off is True


def test_trim_and_polarity(ch8):
    assert ch8.trim_dB == pytest.approx(7.0, abs=1e-6)
    assert ch8.polarity_invert is False


def test_sends_are_indexed_by_destination(ch8):
    send8 = next(s for s in ch8.sends if s.dest_kind == "bus" and s.dest == 8)
    assert send8.on is True
    assert send8.mode == "POST"
    assert send8.level_dB == pytest.approx(-19.9, abs=1e-6)

    send2 = next(s for s in ch8.sends if s.dest_kind == "bus" and s.dest == 2)
    assert send2.on is False
    assert send2.level_dB == NEG_INF


def test_matrix_sends_are_kept_and_kept_distinct(ch8):
    # Every send block holds 16 bus keys and 8 "MX<n>" matrix keys.
    # Bus 3 and MX3 are different destinations sharing a number.
    buses = [s for s in ch8.sends if s.dest_kind == "bus"]
    matrices = [s for s in ch8.sends if s.dest_kind == "matrix"]
    assert len(buses) == 16
    assert len(matrices) == 8
    assert {s.dest for s in matrices} == set(range(1, 9))


def test_sends_are_ordered_buses_then_matrices(ch8):
    kinds = [s.dest_kind for s in ch8.sends]
    assert kinds == ["bus"] * 16 + ["matrix"] * 8
    assert [s.dest for s in ch8.sends[:16]] == list(range(1, 17))


def test_parse_send_key():
    from wing_parser.query.build_channel import parse_send_key

    assert parse_send_key("8") == ("bus", 8)
    assert parse_send_key("16") == ("bus", 16)
    assert parse_send_key("MX1") == ("matrix", 1)
    assert parse_send_key("MX8") == ("matrix", 8)


def test_parse_send_key_returns_none_for_a_key_of_neither_form():
    from wing_parser.query.build_channel import parse_send_key

    assert parse_send_key("") is None
    assert parse_send_key("MXfoo") is None
    assert parse_send_key("bus7") is None


def test_malformed_send_key_is_reported_not_raised():
    from wing_parser.query.build_channel import build_sends

    sends, anomalies = build_sends({"8": {"on": True}, "MXfoo": {"on": True}})
    assert [(s.dest_kind, s.dest) for s in sends] == [("bus", 8)]
    assert len(anomalies) == 1
    assert anomalies[0].code == "malformed_send_key"
    assert "MXfoo" in anomalies[0].where


def test_silent_fader_uses_negative_infinity(vu_path):
    data, _ = build(13, load_raw(vu_path).ae["ch"]["13"])
    assert math.isinf(data.fader_dB)
    assert data.name == "Kick In "        # trailing space preserved verbatim
    assert data.tags_raw == "#M1"


def test_every_channel_in_both_files_builds(factory_path, vu_path):
    for path in (factory_path, vu_path):
        raw = load_raw(path)
        for key, entry in raw.ae["ch"].items():
            data, anomalies = build(int(key), entry)
            assert data.number == int(key)
            assert all(a.code != "eq_band_incomplete" for a in anomalies)
