import pytest

from wing_parser.core.loader import load_raw
from wing_parser.core.versions import load_registry, resolve


def test_registry_has_both_known_versions():
    registry = load_registry()
    assert set(registry) == {"snapshot.10", "snapshot.11"}
    assert registry["snapshot.10"].label == "Wing-Edit 3.2.x"
    assert registry["snapshot.10"].has_globals is True
    assert registry["snapshot.11"].has_globals is False
    assert registry["snapshot.11"].cards == ("wlive", "wmadi")


def test_unknown_version_falls_back_to_newest_and_is_marked_unknown():
    registry = load_registry()
    resolved = resolve("snapshot.99", registry)
    assert resolved.type_id == "snapshot.99"
    assert resolved.known is False
    assert resolved.cards == registry["snapshot.11"].cards


def test_loads_factory_as_snapshot_10(factory_path):
    raw = load_raw(factory_path)
    assert raw.version.type_id == "snapshot.10"
    assert raw.version.known is True
    assert set(raw.ae) >= {"cfg", "io", "ch", "aux", "bus", "main", "mtx", "dca", "mgrp"}
    assert list(raw.ae["cards"]) == ["wlive"]


def test_loads_vu_as_snapshot_11(vu_path):
    raw = load_raw(vu_path)
    assert raw.version.type_id == "snapshot.11"
    assert raw.version.known is True
    assert list(raw.ae["cards"]) == ["wlive", "wmadi"]
    assert raw.meta["creator_model"]


def test_missing_type_field_is_an_error(tmp_path):
    bad = tmp_path / "bad.snap"
    bad.write_text('{"ae_data": {}, "ce_data": {}}', encoding="utf-8")
    with pytest.raises(ValueError, match="type"):
        load_raw(bad)
