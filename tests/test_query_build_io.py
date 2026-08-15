import pytest

from wing_parser.core.loader import load_raw
from wing_parser.query.build_bus import build as build_bus
from wing_parser.query.build_io import build_dcas, build_mute_groups, build_sources


def test_sources_are_keyed_by_group_and_index(vu_path):
    sources = build_sources(load_raw(vu_path).ae["io"]["in"])
    source = sources[("A", 8)]

    assert source.group == "A"
    assert source.index == 8
    assert source.gain_dB == pytest.approx(5.0)
    assert source.phantom is False
    assert source.polarity is False
    assert source.mode == "M"


def test_all_thirteen_source_groups_are_present(vu_path):
    sources = build_sources(load_raw(vu_path).ae["io"]["in"])
    groups = {group for group, _ in sources}
    assert {"LCL", "AUX", "A", "B", "C", "SC", "USB", "CRD", "AES"} <= groups


def test_dcas_carry_names_and_levels(vu_path):
    dcas = build_dcas(load_raw(vu_path).ae["dca"])
    assert len(dcas) == 16
    assert dcas[1].name == "MIC"
    assert dcas[1].fader_dB == pytest.approx(-3.8, abs=1e-5)


def test_mute_groups(vu_path):
    groups = build_mute_groups(load_raw(vu_path).ae["mgrp"])
    assert len(groups) == 8
    assert groups[1].name == "FBAND"
    assert groups[1].muted is True
    assert groups[3].name == ""


def test_dcas_reject_a_non_numeric_key():
    # build_dcas reuses core.normalizer.int_keyed rather than reimplementing
    # the same string-to-int conversion inline; this pins that it still
    # names the bad key rather than raising a bare ValueError from int().
    with pytest.raises(ValueError, match="oops"):
        build_dcas({"1": {"name": "a"}, "oops": {"name": "b"}})


def test_mute_groups_reject_a_non_numeric_key():
    with pytest.raises(ValueError, match="oops"):
        build_mute_groups({"1": {"name": "a"}, "oops": {"name": "b"}})


def test_bus_eight_is_mon_vox_with_a_compressor(vu_path):
    data, anomalies = build_bus("bus", 8, load_raw(vu_path).ae["bus"]["8"])

    assert anomalies == []
    assert data.kind == "bus"
    assert data.name == "MON VOX"
    assert data.dyn.model == "COMP"
    assert data.dyn.threshold_dB == pytest.approx(-15.0)
    assert data.dyn.ratio == pytest.approx(3.0)


def test_bus_one_carries_its_dca_tag(vu_path):
    data, _ = build_bus("bus", 1, load_raw(vu_path).ae["bus"]["1"])
    assert data.tags_raw == "#D1"


def test_every_bus_main_and_matrix_builds(vu_path):
    raw = load_raw(vu_path)
    for kind, section in (("bus", "bus"), ("main", "main"), ("matrix", "mtx"), ("aux", "aux")):
        for key, entry in raw.ae[section].items():
            data, _ = build_bus(kind, int(key), entry)
            assert data.kind == kind
            assert data.number == int(key)
