from wing_parser.core.loader import load_raw
from wing_parser.descriptors.tags import parse


def test_empty_string_yields_no_membership():
    m = parse("")
    assert m.dcas == ()
    assert m.mute_groups == ()
    assert m.unknown == ()


def test_single_mute_group():
    assert parse("#M1").mute_groups == (1,)


def test_single_dca():
    assert parse("#D1").dcas == (1,)


def test_multiple_dcas_comma_separated():
    # Real value from example-Vu.snap aux 1
    m = parse("#D8,#D9")
    assert m.dcas == (8, 9)
    assert m.mute_groups == ()


def test_mixed_kinds():
    m = parse("#D8,#M2,#D10")
    assert m.dcas == (8, 10)
    assert m.mute_groups == (2,)


def test_results_are_sorted_and_deduplicated():
    assert parse("#D10,#D2,#D2").dcas == (2, 10)


def test_whitespace_is_tolerated():
    m = parse(" #D8 , #M1 ")
    assert m.dcas == (8,)
    assert m.mute_groups == (1,)


def test_out_of_range_index_is_unknown_not_silently_accepted():
    m = parse("#M99")
    assert m.mute_groups == ()
    assert m.unknown == ("#M99",)


def test_unrecognised_prefix_is_reported():
    assert parse("#Z3").unknown == ("#Z3",)


def test_real_file_tag_distribution(vu_path):
    raw = load_raw(vu_path)

    channel_tags = {e["tags"] for e in raw.ae["ch"].values() if e["tags"]}
    assert channel_tags == {"#M1", "#M2"}

    bus_dcas = set()
    for entry in raw.ae["bus"].values():
        bus_dcas.update(parse(entry["tags"]).dcas)
    assert bus_dcas == {1, 2, 3, 4, 5, 6}

    # No tag anywhere in the file fails to parse.
    for section in ("ch", "aux", "bus", "main", "mtx"):
        for entry in raw.ae[section].values():
            assert parse(entry.get("tags", "")).unknown == ()


def test_longer_prefix_is_not_shadowed_by_a_shorter_one(monkeypatch):
    # The grammar must not depend on key order in tags.yaml. A nested
    # prefix declared after its own leading substring still has to win.
    from wing_parser.descriptors import registry, tags

    monkeypatch.setattr(
        tags.registry,
        "load",
        lambda name: {
            "separator": ",",
            "prefixes": {
                "#D": {"kind": "dca", "max": 16},
                "#DX": {"kind": "mute_group", "max": 8},
            },
        },
    )
    result = tags.parse("#DX5")
    assert result.mute_groups == (5,)
    assert result.dcas == ()
    assert result.unknown == ()
