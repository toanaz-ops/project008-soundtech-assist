"""The validator checks proposals against the workbook, not the model."""
from pathlib import Path

from wing_parser.showcontext.ingest.suggest import check_proposal

VIVO = Path("tests/data/05102022_vivo_ Event Rundown.xlsx")


def good_proposal():
    return {"sheet": "Rundown", "header_row": 4,
            "columns": {"id": "B", "time": "C", "title": "F"},
            "headers": {"performers": "On stage", "note": "CHUẨN BỊ"}}


def test_good_vivo_proposal_is_clean():
    assert list(check_proposal(good_proposal(), VIVO)) == []


def test_junk_first_sheet_named_is_caught():
    bad = good_proposal() | {"sheet": "LIST"}
    problems = check_proposal(bad, VIVO)
    assert any("LIST" in p for p in problems)


def test_wrong_header_row_caught():
    bad = good_proposal() | {"header_row": 1}
    assert check_proposal(bad, VIVO)


def test_column_past_extent_caught():
    bad = good_proposal()
    bad["columns"]["title"] = "ZZ"
    assert any("ZZ" in p for p in check_proposal(bad, VIVO))


def test_missing_title_refused():
    bad = good_proposal()
    del bad["columns"]["title"]
    assert any("title" in p for p in check_proposal(bad, VIVO))
