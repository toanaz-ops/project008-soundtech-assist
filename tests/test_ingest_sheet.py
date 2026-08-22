from pathlib import Path

import pytest

from wing_parser.showcontext.ingest import sheet as sheet_reader

FIXTURE = Path(__file__).resolve().parent / "data" / "ingest-fixture.xlsx"


def test_headers_come_from_the_declared_row_not_row_one():
    """Row 1 holds a company name, not headings. Reading row 1 would give
    a single cell in column B and every later lookup would miss."""
    read = sheet_reader.read_sheet(FIXTURE, "KỊCH BẢN", header_row=4)
    assert read.headers["A"] == "STT"
    assert read.headers["C"] == "Tên tiết mục"
    assert read.headers["E"] == "Ghi chú"


def test_data_starts_after_the_header_row():
    read = sheet_reader.read_sheet(FIXTURE, "KỊCH BẢN", header_row=4)
    assert read.rows[0].number == 5
    assert read.rows[0].cells["C"] == "Đón khách"


def test_a_blank_row_inside_the_table_is_counted_not_emitted():
    read = sheet_reader.read_sheet(FIXTURE, "KỊCH BẢN", header_row=4)
    assert read.blank_rows == 1
    assert all(any(text for text in row.cells.values()) for row in read.rows)


def test_a_row_with_no_title_is_still_a_row():
    """Dropping it here would hide it. build.py decides what to do with it."""
    read = sheet_reader.read_sheet(FIXTURE, "KỊCH BẢN", header_row=4)
    titles = [row.cells.get("C", "") for row in read.rows]
    assert "" in titles


def test_a_column_with_a_blank_header_is_still_inside_the_sheet(tmp_path):
    """headers: drops it, so only the reported extent can reach it.

    An unlabelled notes or STT column is common on a real running order,
    and it is the one case headers: cannot express -- so the letter has
    to work, which means mapping.py has to be told the sheet is that
    wide.
    """
    from openpyxl import Workbook

    book = Workbook()
    page = book.active
    page.append(["STT", "Tên tiết mục", None])
    page.append(["1", "Đón khách", "chú thích"])
    path = tmp_path / "blank-header.xlsx"
    book.save(path)

    read = sheet_reader.read_sheet(path, None, header_row=1)
    assert "C" not in read.headers
    assert read.last_column == "C"
    assert read.rows[0].cells["C"] == "chú thích"


def test_an_unknown_sheet_name_lists_the_names_that_exist():
    with pytest.raises(ValueError) as caught:
        sheet_reader.read_sheet(FIXTURE, "KHÔNG CÓ", header_row=4)
    assert "KỊCH BẢN" in str(caught.value)


def test_a_sheet_index_is_one_based():
    by_index = sheet_reader.read_sheet(FIXTURE, 1, header_row=4)
    by_name = sheet_reader.read_sheet(FIXTURE, "KỊCH BẢN", header_row=4)
    assert by_index.headers == by_name.headers


def test_a_header_row_past_the_end_says_how_many_rows_there_are():
    with pytest.raises(ValueError) as caught:
        sheet_reader.read_sheet(FIXTURE, "KỊCH BẢN", header_row=999)
    assert "999" in str(caught.value)
