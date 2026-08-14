from wing_parser.core.loader import load_raw
from wing_parser.descriptors import registry
from wing_parser.descriptors.proc_chain import (
    decode,
    source_group_label,
    tap_point,
)


def test_decodes_the_gedi_chain():
    assert decode("GEDI") == ("GATE", "EQ", "DELAY", "INSERT")


def test_decode_preserves_order():
    assert decode("EGID") == ("EQ", "GATE", "INSERT", "DELAY")


def test_empty_chain_is_empty_tuple():
    assert decode("") == ()


def test_unknown_letter_is_flagged_not_dropped():
    assert decode("GZ") == ("GATE", "UNKNOWN_Z")


def test_tap_point_accepts_the_string_form_the_file_uses():
    assert tap_point("5") == "POST_FDR"
    assert tap_point(5) == "POST_FDR"
    assert tap_point("1") == "INPUT"


def test_unknown_tap_point_is_named_not_crashed():
    assert tap_point("99") == "UNKNOWN_TAP"


def test_source_group_label():
    assert source_group_label("A") == "AES50-A"
    assert source_group_label("OFF") == "Not patched"
    assert source_group_label("ZZ") == "ZZ"


def test_registry_caches():
    assert registry.load("proc_chain") is registry.load("proc_chain")


def test_every_channel_in_the_real_file_decodes(vu_path):
    raw = load_raw(vu_path)
    for entry in raw.ae["ch"].values():
        chain = decode(entry["proc"])
        assert all(not block.startswith("UNKNOWN_") for block in chain), entry["proc"]
        assert tap_point(entry["ptap"]) != "UNKNOWN_TAP"
