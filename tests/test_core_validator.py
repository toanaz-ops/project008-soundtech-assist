import json

import pytest

from wing_parser.core.loader import load_raw
from wing_parser.core.validator import EXPECTED_COUNTS, validate


def test_real_files_produce_no_anomalies(factory_path, vu_path):
    assert validate(load_raw(factory_path)) == []
    assert validate(load_raw(vu_path)) == []


def test_expected_counts_match_the_console():
    assert EXPECTED_COUNTS == {
        "ch": 40, "aux": 8, "bus": 16, "main": 4,
        "mtx": 8, "dca": 16, "mgrp": 8,
    }


def test_short_section_is_reported_not_raised(vu_path, tmp_path):
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"].pop("40")
    truncated = tmp_path / "short.snap"
    truncated.write_text(json.dumps(doc), encoding="utf-8")

    anomalies = validate(load_raw(truncated))
    codes = {a.code for a in anomalies}
    assert "count_mismatch" in codes
    assert any("ch" in a.where for a in anomalies)


def test_missing_section_is_reported(vu_path, tmp_path):
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    del doc["ae_data"]["dca"]
    stripped = tmp_path / "nodca.snap"
    stripped.write_text(json.dumps(doc), encoding="utf-8")

    anomalies = validate(load_raw(stripped))
    assert any(a.code == "missing_section" and a.where == "ae_data.dca" for a in anomalies)


def test_unknown_version_is_reported_as_an_anomaly(vu_path, tmp_path):
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["type"] = "snapshot.99"
    future = tmp_path / "future.snap"
    future.write_text(json.dumps(doc), encoding="utf-8")

    anomalies = validate(load_raw(future))
    assert any(a.code == "unknown_version" for a in anomalies)
