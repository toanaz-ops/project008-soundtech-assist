from pathlib import Path

import pytest

from wing_parser.showcontext.ingest import mapping as mapping_module

DATA = Path(__file__).resolve().parent / "data"
HEADERS = {
    "A": "STT",
    "B": "Thời gian",
    "C": "Tên tiết mục",
    "D": "Nghệ sĩ / Thành phần",
    "E": "Ghi chú",
}


def _write(tmp_path, text):
    path = tmp_path / "map.yaml"
    path.write_text(text, encoding="utf-8")
    return path


def test_both_blocks_resolve_into_one_field_table():
    raw = mapping_module.load_mapping(DATA / "ingest-fixture-map.yaml")
    resolved = mapping_module.resolve_columns(raw, HEADERS)
    assert resolved.fields == {
        "id": "A", "time": "B", "title": "C", "performers": "D", "note": "E",
    }


def test_a_field_in_both_blocks_is_refused_naming_both(tmp_path):
    """STT is why the two blocks exist. Never resolve this by picking."""
    path = _write(tmp_path, (
        "sheet: 1\nheader_row: 4\n"
        "columns:\n  title: C\n  id: A\n"
        "headers:\n  id: \"STT\"\n"
    ))
    raw = mapping_module.load_mapping(path)
    with pytest.raises(ValueError) as caught:
        mapping_module.resolve_columns(raw, HEADERS)
    message = str(caught.value)
    assert "id" in message
    assert "columns" in message and "headers" in message


def test_a_missing_title_is_refused(tmp_path):
    path = _write(tmp_path, "sheet: 1\nheader_row: 4\ncolumns:\n  time: B\n")
    raw = mapping_module.load_mapping(path)
    with pytest.raises(ValueError) as caught:
        mapping_module.resolve_columns(raw, HEADERS)
    assert "title" in str(caught.value)


def test_an_unknown_field_name_lists_the_valid_ones(tmp_path):
    path = _write(tmp_path, "sheet: 1\nheader_row: 4\ncolumns:\n  titel: C\n")
    raw = mapping_module.load_mapping(path)
    with pytest.raises(ValueError) as caught:
        mapping_module.resolve_columns(raw, HEADERS)
    for field in mapping_module.FIELDS:
        assert field in str(caught.value)


def test_a_header_that_is_absent_lists_the_headers_that_are_present(tmp_path):
    """More useful than a guess: he copies the right one back."""
    path = _write(tmp_path, (
        "sheet: 1\nheader_row: 4\ncolumns:\n  title: C\n"
        "headers:\n  note: \"Chú thích\"\n"
    ))
    raw = mapping_module.load_mapping(path)
    with pytest.raises(ValueError) as caught:
        mapping_module.resolve_columns(raw, HEADERS)
    assert "Ghi chú" in str(caught.value)


def test_header_matching_ignores_case_and_extra_whitespace(tmp_path):
    path = _write(tmp_path, (
        "sheet: 1\nheader_row: 4\ncolumns:\n  title: C\n"
        "headers:\n  note: \"  ghi   CHÚ \"\n"
    ))
    raw = mapping_module.load_mapping(path)
    resolved = mapping_module.resolve_columns(raw, HEADERS)
    assert resolved.fields["note"] == "E"


def test_a_header_appearing_twice_is_refused_naming_both_columns(tmp_path):
    path = _write(tmp_path, (
        "sheet: 1\nheader_row: 4\ncolumns:\n  title: C\n"
        "headers:\n  note: \"Ghi chú\"\n"
    ))
    raw = mapping_module.load_mapping(path)
    with pytest.raises(ValueError) as caught:
        mapping_module.resolve_columns(raw, {**HEADERS, "F": "Ghi chú"})
    message = str(caught.value)
    assert "E" in message and "F" in message


def test_a_column_letter_that_is_not_in_the_sheet_is_refused(tmp_path):
    path = _write(tmp_path, "sheet: 1\nheader_row: 4\ncolumns:\n  title: Z\n")
    raw = mapping_module.load_mapping(path)
    with pytest.raises(ValueError) as caught:
        mapping_module.resolve_columns(raw, HEADERS)
    assert "Z" in str(caught.value)


def test_a_sheet_named_with_digits_stays_a_name(tmp_path):
    """YAML types carry the whole distinction: 3 is an index, "3" is a name."""
    path = _write(tmp_path, "sheet: \"3\"\nheader_row: 4\ncolumns:\n  title: C\n")
    assert mapping_module.load_mapping(path).sheet == "3"
    path = _write(tmp_path, "sheet: 3\nheader_row: 4\ncolumns:\n  title: C\n")
    assert mapping_module.load_mapping(path).sheet == 3


def test_a_missing_header_row_is_refused(tmp_path):
    path = _write(tmp_path, "sheet: 1\ncolumns:\n  title: C\n")
    with pytest.raises(ValueError) as caught:
        mapping_module.load_mapping(path)
    assert "header_row" in str(caught.value)
