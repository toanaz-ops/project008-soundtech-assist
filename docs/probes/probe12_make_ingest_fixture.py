"""Generate tests/data/ingest-fixture.xlsx.

Read-only with respect to the repo's real data: it writes one file under
tests/data/ and touches nothing else. Re-run it if the fixture is lost or
the contract test's expectations change.

    python docs/probes/probe12_make_ingest_fixture.py

The awkwardness is the point. A fixture that looks like a tidy table would
pass while the real thing failed.
"""

from pathlib import Path

from openpyxl import Workbook

OUT = Path(__file__).resolve().parents[2] / "tests" / "data" / "ingest-fixture.xlsx"

ROWS = [
    ("1", "19:00", "Đón khách",            "nhạc nền",            ""),
    ("2", "19:30", "MC khai mạc",          "MC",                  "2 mic không dây"),
    ("",  "",      "",                     "",                    ""),
    ("3", "19:45", "Tiết mục 3 — Guitar",  "guitar, ca sĩ nữ",    "Chuẩn bị backline"),
    ("4", "20:10", "",                     "trống",               "dòng thiếu tên"),
    ("5", "20:30", "Tiết mục 5",           "tốp múa",             ""),
]


def main() -> None:
    book = Workbook()
    sheet = book.active
    sheet.title = "KỊCH BẢN"

    sheet["B1"] = "CÔNG TY ABC"
    sheet["B2"] = "KỊCH BẢN CHƯƠNG TRÌNH"

    for column, heading in zip("ABCDE", ["STT", "Thời gian", "Tên tiết mục",
                                         "Nghệ sĩ / Thành phần", "Ghi chú"]):
        sheet[f"{column}4"] = heading

    for offset, row in enumerate(ROWS, start=5):
        for column, value in zip("ABCDE", row):
            if value:
                sheet[f"{column}{offset}"] = value

    OUT.parent.mkdir(parents=True, exist_ok=True)
    book.save(OUT)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
