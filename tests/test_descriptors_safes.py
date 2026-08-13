from wing_parser.core.loader import load_raw
from wing_parser.descriptors.safes import decode, decode_scene, is_safe


def test_all_spaces_means_nothing_is_safe():
    assert decode("    ") == (False, False, False, False)


def test_non_space_marks_safe():
    assert decode(" X  X") == (False, True, False, False, True)


def test_is_safe_uses_one_based_numbering():
    flags = decode(" X ")
    assert is_safe(flags, 1) is False
    assert is_safe(flags, 2) is True
    assert is_safe(flags, 3) is False


def test_out_of_range_lookup_is_false_not_an_error():
    flags = decode(" X ")
    assert is_safe(flags, 99) is False
    assert is_safe(flags, 0) is False


def test_short_bitmap_is_padded_to_expected_length():
    assert decode("X", expected=4) == (True, False, False, False)


def test_real_file_has_nothing_scene_safe(vu_path):
    sections = decode_scene(load_raw(vu_path).ce["safes"])
    assert len(sections["ch"]) == 40
    assert not any(sections["ch"])
    assert not any(sections["bus"])


def test_decode_scene_skips_nested_sections(vu_path):
    sections = decode_scene(load_raw(vu_path).ce["safes"])
    assert "source" not in sections
    assert set(sections) <= {"ch", "aux", "bus", "main", "mtx", "dca", "mute", "fx"}
