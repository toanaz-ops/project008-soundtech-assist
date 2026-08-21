import pytest

from wing_parser.core.loader import load_raw
from wing_parser.core.versions import load_registry, resolve


def test_registry_holds_every_known_version():
    registry = load_registry()
    assert set(registry) == {"snapshot.9", "snapshot.10", "snapshot.11"}
    assert registry["snapshot.9"].label == "Wing-Edit 3.0.x"
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


def test_top_level_array_is_an_error(tmp_path):
    bad = tmp_path / "bad.snap"
    bad.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(ValueError, match="list"):
        load_raw(bad)


def test_snapshot_9_is_a_known_schema():
    """WING Edit 3.0 files were being parsed under the 3.3 layout with an
    `unknown_version` anomaly. The payload is identical across versions --
    only the envelope differs -- so recognising 3.0 is a data entry, which
    is exactly what this registry exists for.
    """
    registry = load_registry()
    nine = registry["snapshot.9"]
    assert nine.known is True
    assert nine.has_globals is False
    assert nine.cards == ("wlive",)
    # The 3.0 marker: WING-Edit's layer layout sat beside ae_data/ce_data
    # rather than inside ce_data as `layer.WEDIT`, where 3.3 put it.
    assert "wedit_layer" in nine.meta_keys


def test_a_snapshot_9_envelope_raises_no_unknown_version_anomaly():
    from wing_parser.core.loader import RawScene
    from wing_parser.core.validator import validate
    from wing_parser.core.versions import resolve

    version = resolve("snapshot.9", load_registry())
    raw = RawScene(
        version=version,
        ae={s: {} for s in ("cfg", "io", "ch", "aux", "bus", "main", "mtx", "dca", "mgrp")},
        ce={"cfg": {}, "safes": {}},
        meta={"type": "snapshot.9", "wedit_layer": {}},
        source="synthetic",
    )
    assert not [a for a in validate(raw) if a.code == "unknown_version"]
