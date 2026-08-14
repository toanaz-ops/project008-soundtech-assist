import pytest

from wing_parser.core.loader import load_raw
from wing_parser.descriptors.eq_models import build


def test_std_model_yields_six_bands(vu_path):
    eq, anomalies = build(load_raw(vu_path).ae["ch"]["8"]["eq"])

    assert anomalies == []
    assert eq.on is True
    assert eq.model == "STD"
    assert eq.bands is not None
    assert [b.name for b in eq.bands] == ["low", "1", "2", "3", "4", "high"]


def test_std_band_values_match_the_file(vu_path):
    eq, _ = build(load_raw(vu_path).ae["ch"]["8"]["eq"])
    band2 = next(b for b in eq.bands if b.name == "2")

    assert band2.gain == pytest.approx(-8.9, abs=1e-6)
    assert band2.freq == pytest.approx(241.1459, abs=1e-3)
    assert band2.q == pytest.approx(3.7243, abs=1e-3)


def test_shelf_shape_is_captured(vu_path):
    eq, _ = build(load_raw(vu_path).ae["ch"]["8"]["eq"])
    assert next(b for b in eq.bands if b.name == "low").shape == "SHV"
    assert next(b for b in eq.bands if b.name == "1").shape is None


def test_unknown_model_yields_no_bands_and_an_anomaly():
    eq, anomalies = build({"on": True, "mdl": "PULSAR", "lowboost": 3.0})

    assert eq.model == "PULSAR"
    assert eq.bands is None
    assert eq.raw["lowboost"] == 3.0
    assert len(anomalies) == 1
    assert anomalies[0].code == "descriptor_missing"
    assert "PULSAR" in anomalies[0].detail


def test_unknown_model_never_borrows_the_std_layout():
    # STD-shaped keys under a foreign model must still be refused.
    eq, anomalies = build({"on": True, "mdl": "SOUL", "1g": 3.0, "1f": 100.0, "1q": 1.0})
    assert eq.bands is None
    assert anomalies[0].code == "descriptor_missing"


def test_missing_band_key_is_reported_not_guessed():
    eq, anomalies = build({"on": True, "mdl": "STD", "lg": 0.0, "lf": 100.0, "lq": 1.0})
    assert eq.bands is None
    assert anomalies[0].code == "eq_band_incomplete"


def test_every_eq_in_both_files_either_builds_or_is_flagged(factory_path, vu_path):
    seen: dict[str, int] = {}
    for path in (factory_path, vu_path):
        raw = load_raw(path)
        for section in ("ch", "aux", "bus", "main", "mtx"):
            for entry in raw.ae[section].values():
                if "eq" not in entry:
                    continue
                eq, anomalies = build(entry["eq"])
                seen[eq.model] = seen.get(eq.model, 0) + 1
                if eq.model == "STD":
                    assert eq.bands is not None and anomalies == []
                else:
                    assert eq.bands is None and anomalies

    assert seen["STD"] == 150
    assert seen["PULSAR"] == 2
