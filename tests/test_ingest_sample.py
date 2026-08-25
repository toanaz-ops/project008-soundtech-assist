"""Sampler output shape, truncation, junk-sheet tolerance."""
from pathlib import Path

import openpyxl

from wing_parser.showcontext.ingest.sample import sample_workbook

FIXTURE = Path("tests/data/BIDV TPHCM - KỊCH BẢN SK YEP 2025..xlsx")


def test_real_bidv_sheet_produces_lettered_lines():
    samples = sample_workbook(FIXTURE, sample_rows=8)
    bidv = [s for s in samples if "KB 8.1" in s.name]
    assert bidv, [s.name for s in samples]
    joined = "\n".join(bidv[0].lines)
    assert "A5='TT'" in joined          # header row found by letter+row
    assert "B5='Thời gian" in joined    # newline in header preserved enough


def test_row_cap_respected():
    samples = sample_workbook(FIXTURE, sample_rows=3)
    for s in samples:
        assert len(s.lines) <= 3 * 10  # 3 rows, generous cells-per-row cap


def test_long_cells_truncated(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "X"
    ws["A1"] = "x" * 100
    path = tmp_path / "long.xlsx"
    wb.save(path)
    samples = sample_workbook(path)
    assert all(len(line) <= 60 for s in samples for line in s.lines)
