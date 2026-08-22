# Sub-project G2a — assisted ingest (deterministic half) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn an event producer's Excel running order into a show-context YAML
file that ToanAZ reads and edits, entirely offline, without ever inventing a
value the sheet does not state.

**Architecture:** Four one-way modules under
`wing_parser/showcontext/ingest/` — `sheet.py` reads cells and interprets
nothing, `mapping.py` turns a hand-written per-client mapping file into resolved
column letters, `build.py` turns rows into `Segment` records with no I/O at all,
and `emit.py` writes YAML with comments through `ruamel`. Vietnamese cue-sheet
terms resolve through a new third domain in the existing
`knowledge/toanaz/classifier.yaml`, reusing its atomic write and
comment-preserving round-trip. Nothing here calls a model.

**Tech Stack:** Python 3.11+ · `openpyxl` (new, as an extra) · `ruamel.yaml`
(already a core dependency) · PyYAML (already a core dependency) · pytest.

**Design authority:** `docs/superpowers/specs/2026-08-22-assisted-ingest-design.md`
(commits `16c965f`, `608dfd4`). Where this plan and the spec disagree, the spec
wins — report the disagreement rather than choosing silently.

## Global Constraints

Every task's requirements implicitly include all of these.

- **Deterministic.** `core`, `query`, `advisory`, `showcontext`, `net` may not
  call an LLM. **No task in this plan adds a model call anywhere.**
- **Offline.** `anthropic` and `mcp` stay uninstalled. The FastMCP test keeps
  skipping — that is by design, not a regression.
- **Never fabricate a value the source does not state.** Anything unreadable
  becomes a verbatim comment in the output; nothing is dropped and nothing is
  guessed.
- **Modular, roughly 200-line files, split by responsibility layer.** If a file
  in this plan grows past ~200 lines, stop and report it rather than continuing.
- **PyYAML reads, `ruamel` writes.**
- **UTF-8 explicitly on every read and write.** `encoding="utf-8"` on every
  `open`, `read_text` and `write_text`. Vietnamese corrupts silently otherwise
  and the corruption survives into git.
- **`docs/knowledge-base/` is read-only.**
- **`pytest.approx` for computed floats; exact comparison for a value that
  round-trips unchanged.**
- **The unprofiled real file must still yield exactly 22 findings.** Pinned in
  `tests/test_advisory_realfile.py`.
- **Measured baseline before Task 1: 1056 tests collected, `pytest` exit code
  0** (1055 passing, 1 skipped by design). This suite frequently prints no
  summary trailer — **judge by the exit code**, not by looking for a "N passed"
  line.
- **PowerShell, not Git Bash.** An OSC address starts with `/` and MSYS rewrites
  it into a Windows path. Commands in this plan are written for PowerShell.
- **Never put backticks inside `git commit -m`.** PowerShell evaluates the
  enclosed word and silently deletes it from the message. Use `git commit -F -`
  with a here-string, as every command block below does.

---

## File Structure

**Created:**

| path | responsibility |
|---|---|
| `wing_parser/showcontext/ingest/__init__.py` | public surface of the importer |
| `wing_parser/showcontext/ingest/sheet.py` | spreadsheet → cell text. Interprets nothing. The only module that knows `openpyxl` exists. |
| `wing_parser/showcontext/ingest/mapping.py` | mapping file → resolved column letters. Refuses every ambiguity. |
| `wing_parser/showcontext/ingest/build.py` | rows + a vocabulary lookup → `Segment` records and comments. No I/O. |
| `wing_parser/showcontext/ingest/emit.py` | records + comments → YAML text via `ruamel` |
| `docs/probes/probe12_make_ingest_fixture.py` | generates the `.xlsx` test fixture, so the fixture is reproducible |
| `tests/data/ingest-fixture.xlsx` | the generated fixture |
| `tests/data/ingest-fixture-map.yaml` | the mapping for that fixture |
| `tests/test_ingest_sheet.py` · `test_ingest_mapping.py` · `test_ingest_build.py` · `test_ingest_emit.py` · `test_ingest_contract.py` | one test module per module, plus the end-to-end contract |

**Modified:**

| path | change |
|---|---|
| `wing_parser/classifier/cache.py:22` | add `"cuesheet"` to `DOMAINS` |
| `wing_parser/classifier/cache.py:24-36` | add a `cuesheet: {}` section to `_SEED` with a comment saying what it is for |
| `wing_parser/classifier/cache.py:59-63` | derive the error message from `DOMAINS` so it cannot go stale again |
| `wing_parser/showcontext/view.py:138` | rename `_channels_of` → `channels_of`; update `:183` and `:187` |
| `wing_parser/cli/__main__.py:98-104` | register `showcontext import` beside `showcontext lint` |
| `wing_parser/cli/commands.py` | add the `showcontext_import` handler |
| `wing_parser/cli/render.py` | add the importer's human-facing lines |
| `pyproject.toml:15-18` | add an `ingest` extra, and `openpyxl` to `dev` |
| `README.md` | document the command, and that only Q4 and Q5 fire on an imported file |

---

### Task 1: The `cuesheet` domain in the classifier cache

Vietnamese cue-sheet terms need somewhere to live. `cache.py` already provides
atomic writes, comment-preserving round-trip, and "a hand-written entry wins" —
so this adds a domain rather than a second store.

**Files:**
- Modify: `wing_parser/classifier/cache.py:22`, `:24-36`, `:59-63`
- Test: `tests/test_classifier_cache.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `cache.DOMAINS` now contains `"cuesheet"`.
  `cache.lookup(name: str, domain: str, directory: Path | None = None) ->
  Classification | None` and
  `cache.remember(name: str, domain: str, classification: Classification,
  directory: Path | None = None) -> None` both accept `"cuesheet"`. Signatures
  are unchanged; only the accepted domain set grows.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_classifier_cache.py`:

```python
def test_cuesheet_domain_round_trips(tmp_path):
    """A Vietnamese cue-sheet term is stored and read back like any other."""
    from wing_parser.classifier import cache
    from wing_parser.classifier.matcher import Classification

    cache.remember(
        "Ca sĩ nữ",
        "cuesheet",
        Classification(kind="speech.vocal", confidence=0.9, origin="manual"),
        directory=tmp_path,
    )
    found = cache.lookup("ca sĩ nữ", "cuesheet", directory=tmp_path)
    assert found is not None
    assert found.kind == "speech.vocal"
    assert found.origin == "manual"


def test_a_file_without_a_cuesheet_section_still_loads(tmp_path):
    """Files written before this domain existed must keep working."""
    from wing_parser.classifier import cache

    (tmp_path / "classifier.yaml").write_text(
        "channels: {}\nbuses: {}\n", encoding="utf-8"
    )
    loaded = cache.load(directory=tmp_path)
    assert loaded["cuesheet"] == {}


def test_the_top_level_error_names_every_domain(tmp_path):
    """The message must not go stale when a domain is added.

    It was hard-coded to 'a channels: and a buses: section'. No test runs an
    error message, so a fourth domain would silently make it false again.
    """
    from wing_parser.classifier import cache

    (tmp_path / "classifier.yaml").write_text("- not a mapping\n", encoding="utf-8")
    with pytest.raises(ValueError) as caught:
        cache.load(directory=tmp_path)
    for domain in cache.DOMAINS:
        assert f"{domain}:" in str(caught.value)
```

- [ ] **Step 2: Run the tests to verify they fail**

```powershell
python -m pytest tests\test_classifier_cache.py -k "cuesheet or every_domain" -v
```

Expected: `test_cuesheet_domain_round_trips` and
`test_a_file_without_a_cuesheet_section_still_loads` FAIL with a `KeyError` on
`"cuesheet"`; `test_the_top_level_error_names_every_domain` FAILS on the
assertion for `cuesheet:`.

- [ ] **Step 3: Add the domain**

In `wing_parser/classifier/cache.py`, change line 22:

```python
DOMAINS = ("channels", "buses", "cuesheet")
```

- [ ] **Step 4: Extend the seed**

In `_SEED`, after the `buses: {}` line, add:

```python
# cuesheet: terms as they appear on a printed running order, in any
# language, mapped to the same kinds the channels domain uses. A cue
# sheet and a console strip are different naming domains -- nobody
# labels a strip "ca si nu", and no director writes "HS4" -- so a term
# lives here and not in channels.
cuesheet: {}
```

Keep it inside the existing triple-quoted string, matching its indentation
(column 0 — the seed is written with `"""\` so its lines are unindented).

- [ ] **Step 4b: Add the section to the shipped knowledge file too**

Add `cuesheet: {}` to `knowledge/toanaz/classifier.yaml`, with the same
explanatory comment.

This is not cosmetic. `tests/conftest.py:38`'s `_isolated_knowledge_dir`
docstring states that this file *"ships with `channels: {}` and `buses: {}`"* —
leaving the shipped file alone makes that sentence false, which is the same
"correct code, false description" shape §6.2 of the spec exists to close. Update
that docstring in the same commit to name all three sections.

It also matters for a human reason: the section is where ToanAZ sees that he can
add a term at all.

- [ ] **Step 5: Make the error message derive from `DOMAINS`**

Replace the message at `cache.py:59-63`:

```python
        raise ValueError(
            f"{path}: the top level must be a mapping with "
            + ", ".join(f"{domain}:" for domain in DOMAINS)
            + f" sections, but this file's top level is {type(doc).__name__}."
        )
```

Deriving it is the actual fix. Hard-coding three names instead of two would
leave the same trap armed for the next domain.

- [ ] **Step 6: Run the tests to verify they pass**

```powershell
python -m pytest tests\test_classifier_cache.py -v
```

Expected: PASS, including every pre-existing test in that file.

- [ ] **Step 7: Prove the stale-message test would catch a regression**

Temporarily revert the message to the hard-coded two-domain sentence, re-run
`test_the_top_level_error_names_every_domain`, and confirm it goes **red**. Then
restore the fix. Do not skip this — the C2 cycle found three green tests in this
repo that asserted nothing.

- [ ] **Step 8: Run the whole suite**

```powershell
python -m pytest tests\
```

Expected: exit code 0. (This suite often prints no summary trailer; check
`$LASTEXITCODE`.)

- [ ] **Step 9: Commit**

```powershell
git add wing_parser/classifier/cache.py knowledge/toanaz/classifier.yaml tests/conftest.py tests/test_classifier_cache.py
git commit -F - <<'EOF'
Add a cuesheet domain to the classifier cache

Cue-sheet terms and console strip labels are different naming domains.
Nobody labels a strip "ca si nu" and no director writes "HS4", so a
Vietnamese running-order term gets its own section rather than
polluting channels.

Adding the domain is backward-compatible: _read already fills a missing
section with an empty mapping, so files written before this keep
loading.

Also derives the top-level error message from DOMAINS. It was hard-coded
to "a channels: and a buses: section", which this change would have made
false, and no test runs an error message.
EOF
```

---

### Task 2: `sheet.py` — read cells, interpret nothing

**Files:**
- Create: `wing_parser/showcontext/ingest/__init__.py`,
  `wing_parser/showcontext/ingest/sheet.py`,
  `docs/probes/probe12_make_ingest_fixture.py`, `tests/data/ingest-fixture.xlsx`
- Modify: `pyproject.toml:15-18`
- Test: `tests/test_ingest_sheet.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `RawRow` — frozen dataclass, fields `number: int` (1-based worksheet row),
    `cells: dict[str, str]` (column letter → stripped cell text).
  - `SheetRead` — frozen dataclass, fields `headers: dict[str, str]` (column
    letter → header text), `rows: tuple[RawRow, ...]`, `blank_rows: int`.
  - `read_sheet(path: str | Path, sheet: str | int | None, header_row: int)
    -> SheetRead`.
  - `MissingExtra` — a `RuntimeError` subclass raised when `openpyxl` is absent.

- [ ] **Step 1: Write the fixture generator**

Create `docs/probes/probe12_make_ingest_fixture.py`. Everything awkward about a
real running order is deliberate here — a header on row 4, an `STT` column, a
blank row mid-table, a row with no title, and a performer fragment that resolves
to nothing.

```python
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
```

- [ ] **Step 2: Run the generator**

```powershell
python docs/probes/probe12_make_ingest_fixture.py
```

Expected: prints the path, and `tests\data\ingest-fixture.xlsx` exists.

- [ ] **Step 3: Add the generator to the probes README**

Append a row to `docs/probes/README.md` in the same shape as its existing
entries, naming `probe12_make_ingest_fixture.py` and the claim it supports:
*"the ingest fixture is reproducible; a measurement nobody can re-run is not
evidence."*

- [ ] **Step 4: Write the failing tests**

Create `tests/test_ingest_sheet.py`:

```python
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
```

- [ ] **Step 5: Run the tests to verify they fail**

```powershell
python -m pytest tests\test_ingest_sheet.py -v
```

Expected: FAIL at collection — `ModuleNotFoundError: wing_parser.showcontext.ingest`.

- [ ] **Step 6: Create the package and the reader**

Create `wing_parser/showcontext/ingest/__init__.py`:

```python
"""Assisted ingest: a producer's running order becomes a show context.

Four modules, one direction: sheet -> mapping -> build -> emit. Nothing
here calls a model; the half that does lives in G2b.
"""
```

Create `wing_parser/showcontext/ingest/sheet.py`:

```python
"""Spreadsheet to cell text. This module interprets nothing.

It is the only module that knows openpyxl exists, which is what makes a
later CSV, PDF or photo reader a sibling of this file rather than a
change to the three modules downstream.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

EXTRA_HINT = (
    "reading a spreadsheet needs openpyxl, which is not installed. "
    "Install it with:  pip install -e .[ingest]"
)


class MissingExtra(RuntimeError):
    """openpyxl is absent. Mirrors how classifier/llm.py treats anthropic."""


@dataclass(frozen=True)
class RawRow:
    number: int
    cells: dict[str, str]


@dataclass(frozen=True)
class SheetRead:
    headers: dict[str, str]
    rows: tuple[RawRow, ...]
    blank_rows: int


def _text(value) -> str:
    """Every cell becomes stripped text.

    A time cell arrives as datetime.time, a numbered column as int. Both
    become text here because nothing downstream does arithmetic on a cell
    -- see the design spec section 5.1 on why times are not converted.
    """
    if value is None:
        return ""
    return str(value).strip()


def _worksheet(book, sheet: str | int | None):
    if sheet is None:
        return book.worksheets[0]
    if isinstance(sheet, int):
        if not 1 <= sheet <= len(book.worksheets):
            raise ValueError(
                f"sheet index {sheet} is out of range; the workbook has "
                f"{len(book.worksheets)} sheet(s)."
            )
        return book.worksheets[sheet - 1]
    if sheet not in book.sheetnames:
        raise ValueError(
            f"no sheet named {sheet!r}; this workbook has: "
            + ", ".join(repr(name) for name in book.sheetnames)
        )
    return book[sheet]


def read_sheet(path: str | Path, sheet: str | int | None, header_row: int) -> SheetRead:
    try:
        from openpyxl import load_workbook
        from openpyxl.utils import get_column_letter
    except ImportError as exc:                # pragma: no cover - env-dependent
        raise MissingExtra(EXTRA_HINT) from exc

    if header_row < 1:
        raise ValueError(f"header_row must be 1 or more, not {header_row}.")

    book = load_workbook(Path(path), data_only=True, read_only=True)
    try:
        worksheet = _worksheet(book, sheet)
        grid = [
            {get_column_letter(index): _text(cell)
             for index, cell in enumerate(row, start=1)}
            for row in worksheet.iter_rows(values_only=True)
        ]
    finally:
        book.close()

    if header_row > len(grid):
        raise ValueError(
            f"header_row {header_row} is past the end of the sheet, which has "
            f"{len(grid)} row(s)."
        )

    headers = {letter: text for letter, text in grid[header_row - 1].items() if text}
    if not headers:
        raise ValueError(f"row {header_row} is empty, so it cannot be the header row.")

    rows: list[RawRow] = []
    blank = 0
    for offset, cells in enumerate(grid[header_row:], start=header_row + 1):
        if any(cells.values()):
            rows.append(RawRow(number=offset, cells=cells))
        else:
            blank += 1

    return SheetRead(headers=headers, rows=tuple(rows), blank_rows=blank)
```

- [ ] **Step 7: Declare the dependency**

In `pyproject.toml`, under `[project.optional-dependencies]`:

```toml
llm = ["anthropic>=0.40"]
mcp = ["mcp>=1.2,<2"]
ingest = ["openpyxl>=3.1"]
dev = ["pytest>=8.0", "pytest-cov>=5.0", "openpyxl>=3.1"]
```

`openpyxl` appears in `dev` as well as `ingest` on purpose: the contract test in
Task 8 must never skip on a developer machine, because a skipped test hides a
regression exactly as well as a missing one.

- [ ] **Step 8: Run the tests to verify they pass**

```powershell
python -m pytest tests\test_ingest_sheet.py -v
```

Expected: all seven PASS.

- [ ] **Step 9: Prove the blank-row test would catch a regression**

Change `if any(cells.values())` to `if True`, re-run
`test_a_blank_row_inside_the_table_is_counted_not_emitted`, confirm it goes
**red**, then restore.

- [ ] **Step 10: Commit**

```powershell
git add wing_parser/showcontext/ingest/ tests/test_ingest_sheet.py tests/data/ingest-fixture.xlsx docs/probes/probe12_make_ingest_fixture.py docs/probes/README.md pyproject.toml
git commit -F - <<'EOF'
Read a spreadsheet into rows, interpreting nothing

sheet.py is the only module that knows openpyxl exists, so a later CSV,
PDF or photo reader becomes a sibling of it rather than a change to the
three modules downstream.

Every cell becomes stripped text, including times and numbers, because
nothing downstream does arithmetic on a cell.

The fixture is generated by a probe rather than committed by hand. Its
awkwardness is deliberate: a header on row 4, an STT column, a blank row
mid-table, a row with no title, and a performer fragment that resolves
to nothing. A tidy fixture would pass while the real thing failed.

Declares openpyxl as an ingest extra, and in dev too so the contract
test can never skip.
EOF
```

---

### Task 3: `mapping.py` — resolve columns, refuse every ambiguity

**Files:**
- Create: `wing_parser/showcontext/ingest/mapping.py`,
  `tests/data/ingest-fixture-map.yaml`
- Test: `tests/test_ingest_mapping.py`

**Interfaces:**
- Consumes: `sheet.SheetRead.headers` (a `dict[str, str]`) from Task 2.
- Produces:
  - `FIELDS: tuple[str, ...]` = `("id", "title", "time", "performers", "note")`
  - `RawMapping` — frozen dataclass, fields `source: str`,
    `sheet: str | int | None`, `header_row: int`,
    `columns: dict[str, str]`, `headers: dict[str, str]`, `path: Path | None`
  - `SheetMapping` — frozen dataclass, fields `source: str`,
    `fields: dict[str, str]` (field name → column letter)
  - `load_mapping(path: str | Path) -> RawMapping`
  - `resolve_columns(raw: RawMapping, headers: dict[str, str]) -> SheetMapping`

Two functions rather than one because the CLI must read `sheet` and `header_row`
**before** it can open the workbook, and it cannot resolve `headers:` until
after. This is also why `mapping.py` never opens a file of its own.

- [ ] **Step 1: Write the fixture's mapping file**

Create `tests/data/ingest-fixture-map.yaml`:

```yaml
# Mapping for tests/data/ingest-fixture.xlsx, regenerate that file with:
#   python docs/probes/probe12_make_ingest_fixture.py
# Uses both blocks on purpose, so the contract test exercises each.
source: "Công ty ABC — ROS template 2026"
sheet: "KỊCH BẢN"
header_row: 4
columns:
  id: A
  time: B
  title: C
headers:
  performers: "Nghệ sĩ / Thành phần"
  note: "Ghi chú"
```

- [ ] **Step 2: Write the failing tests**

Create `tests/test_ingest_mapping.py`:

```python
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
```

- [ ] **Step 3: Run the tests to verify they fail**

```powershell
python -m pytest tests\test_ingest_mapping.py -v
```

Expected: FAIL at collection — no module named `mapping`.

- [ ] **Step 4: Write the module**

Create `wing_parser/showcontext/ingest/mapping.py`:

```python
"""A hand-written per-client mapping file, resolved to column letters.

Two blocks, never one. A single block would have to decide whether STT
means "column STT" or "the header cell reading STT", and Vietnamese
running orders head their first column STT often enough that either
answer is silently wrong on real sheets. Ambiguity is refused here, the
way showcontext/vocabulary.py refuses a tie rather than picking a side.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

FIELDS: tuple[str, ...] = ("id", "title", "time", "performers", "note")
REQUIRED: tuple[str, ...] = ("title",)

_LETTERS = re.compile(r"^[A-Z]{1,3}$")
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class RawMapping:
    source: str
    sheet: str | int | None
    header_row: int
    columns: dict[str, str]
    headers: dict[str, str]
    path: Path | None = None


@dataclass(frozen=True)
class SheetMapping:
    source: str
    fields: dict[str, str]


def _normalise(text: str) -> str:
    return _WHITESPACE.sub(" ", (text or "").strip()).casefold()


def _section(doc, name: str, where: str) -> dict[str, str]:
    section = doc.get(name)
    if section is None:
        return {}
    if not isinstance(section, dict):
        raise ValueError(
            f"{where}: {name}: must be a mapping of field name to value, "
            f"but it is {type(section).__name__}."
        )
    return {str(key): str(value) for key, value in section.items()}


def load_mapping(path: str | Path) -> RawMapping:
    """Shape only. Column resolution needs the header row and happens later."""
    where_from = Path(path)
    doc = yaml.safe_load(where_from.read_text(encoding="utf-8"))
    where = str(where_from)

    if not isinstance(doc, dict):
        raise ValueError(
            f"{where}: the top level must be a mapping with header_row: and "
            f"at least one of columns: or headers:, but it is "
            f"{type(doc).__name__}."
        )

    header_row = doc.get("header_row")
    if not isinstance(header_row, int) or isinstance(header_row, bool) or header_row < 1:
        raise ValueError(
            f"{where}: header_row: is required and must be a whole number of "
            f"1 or more, counted the way Excel shows it. Got {header_row!r}."
        )

    sheet = doc.get("sheet")
    if sheet is not None and not isinstance(sheet, (str, int)):
        raise ValueError(
            f"{where}: sheet: must be a name in quotes or a 1-based number, "
            f"not {type(sheet).__name__}."
        )
    if isinstance(sheet, bool):
        raise ValueError(f"{where}: sheet: must be a name or a number, not a boolean.")

    return RawMapping(
        source=str(doc.get("source", "")),
        sheet=sheet,
        header_row=header_row,
        columns=_section(doc, "columns", where),
        headers=_section(doc, "headers", where),
        path=where_from,
    )


def _by_header(name: str, wanted: str, headers: dict[str, str], where: str) -> str:
    target = _normalise(wanted)
    found = sorted(
        letter for letter, text in headers.items() if _normalise(text) == target
    )
    if len(found) == 1:
        return found[0]
    if len(found) > 1:
        raise ValueError(
            f"{where}: headers: {name}: {wanted!r} appears in more than one "
            f"column ({', '.join(found)}). Use columns: with a letter instead."
        )
    raise ValueError(
        f"{where}: headers: {name}: no column on the header row reads "
        f"{wanted!r}. That row reads: "
        + ", ".join(f"{letter}={text!r}" for letter, text in sorted(headers.items()))
        + ". Matching is exact after trimming and case-folding; it is not "
        "repaired, because the distance between real header cells has never "
        "been measured."
    )


def resolve_columns(raw: RawMapping, headers: dict[str, str]) -> SheetMapping:
    where = str(raw.path) if raw.path else "<mapping>"

    both = sorted(set(raw.columns) & set(raw.headers))
    if both:
        raise ValueError(
            f"{where}: {', '.join(both)} named in both columns: and headers:. "
            "Pick one block; naming a field twice is not resolved by choosing."
        )

    for name in sorted(set(raw.columns) | set(raw.headers)):
        if name not in FIELDS:
            raise ValueError(
                f"{where}: unknown field {name!r}; expected one of: "
                + ", ".join(FIELDS)
            )

    fields: dict[str, str] = {}
    for name, letter in raw.columns.items():
        upper = letter.strip().upper()
        if not _LETTERS.match(upper):
            raise ValueError(
                f"{where}: columns: {name}: {letter!r} is not a column letter. "
                "Use the letter Excel shows above the column, such as C."
            )
        if upper not in headers:
            raise ValueError(
                f"{where}: columns: {name}: column {upper} has no header on the "
                f"header row. Columns with a heading are: "
                + ", ".join(sorted(headers))
            )
        fields[name] = upper

    for name, wanted in raw.headers.items():
        fields[name] = _by_header(name, wanted, headers, where)

    missing = [name for name in REQUIRED if name not in fields]
    if missing:
        raise ValueError(
            f"{where}: {', '.join(missing)} must be mapped, in columns: or "
            "headers:. Without it a row has no title and cannot become a "
            "segment."
        )

    return SheetMapping(source=raw.source, fields=fields)
```

- [ ] **Step 5: Run the tests to verify they pass**

```powershell
python -m pytest tests\test_ingest_mapping.py -v
```

Expected: all ten PASS.

- [ ] **Step 6: Prove the both-blocks test would catch a regression**

Delete the `both` check, re-run
`test_a_field_in_both_blocks_is_refused_naming_both`, confirm it goes **red**,
then restore.

- [ ] **Step 7: Commit**

```powershell
git add wing_parser/showcontext/ingest/mapping.py tests/test_ingest_mapping.py tests/data/ingest-fixture-map.yaml
git commit -F - <<'EOF'
Resolve mapping columns, refusing every ambiguity

Two blocks rather than one. A single block would have to decide whether
STT means a column reference or the header cell reading STT, and
Vietnamese running orders head their first column STT often enough that
either answer is silently wrong on a real sheet.

Header matching is exact after normalisation and is never repaired. The
G1 vocabulary's repair radius rests on a measurement of that
vocabulary's minimum pairwise distance; the distance between real header
cells has never been measured, so there is no radius to justify. When a
header is absent the error prints the header row verbatim, which he can
copy from.

load_mapping and resolve_columns are separate because the CLI needs
sheet and header_row before it can open the workbook, and cannot resolve
headers until after.
EOF
```

---

### Task 4: `build.py` — rows into segments, with no I/O

**Files:**
- Create: `wing_parser/showcontext/ingest/build.py`
- Test: `tests/test_ingest_build.py`

**Interfaces:**
- Consumes: `sheet.RawRow` (Task 2), `mapping.SheetMapping` (Task 3),
  `wing_parser.showcontext.models.Segment`,
  `wing_parser.classifier.matcher.classify` / `is_confident`,
  `wing_parser.classifier.normalize.clean`.
- Produces:
  - `BuiltSegment` — frozen dataclass, fields `segment: Segment`,
    `comments: tuple[str, ...]`
  - `BuildResult` — frozen dataclass, fields
    `segments: tuple[BuiltSegment, ...]`, `loose_comments: tuple[str, ...]`,
    `data_rows: int`, `comment_rows: int`, `blank_rows: int`
  - `resolve_fragment(fragment: str, lookup) -> str | None`
  - `build(rows, mapping, lookup, blank_rows: int = 0) -> BuildResult`

`lookup` is a callable `(str) -> Classification | None`, injected rather than
imported, so this module performs no I/O and its tests need no filesystem. Task 7
passes `lambda term: cache.lookup(term, "cuesheet")`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_ingest_build.py`:

```python
import pytest

from wing_parser.classifier.matcher import Classification
from wing_parser.showcontext.ingest import build as builder
from wing_parser.showcontext.ingest.mapping import SheetMapping
from wing_parser.showcontext.ingest.sheet import RawRow

MAPPING = SheetMapping(
    source="test",
    fields={"id": "A", "time": "B", "title": "C", "performers": "D", "note": "E"},
)

VOCABULARY = {"ca sĩ nữ": "speech.vocal", "trống": "drums.kick"}


def lookup(term):
    kind = VOCABULARY.get(term)
    if kind is None:
        return None
    return Classification(kind=kind, confidence=0.95, origin="manual")


def row(number, **cells):
    return RawRow(number=number, cells={"A": "", "B": "", "C": "", "D": "", "E": "",
                                        **cells})


def test_a_row_becomes_one_segment():
    result = builder.build([row(5, A="1", C="Đón khách")], MAPPING, lookup)
    assert len(result.segments) == 1
    assert result.segments[0].segment.id == "1"
    assert result.segments[0].segment.title == "Đón khách"


def test_an_absent_id_is_generated_in_file_order():
    rows = [row(5, C="Một"), row(6, C="Hai")]
    mapping = SheetMapping(source="t", fields={"title": "C"})
    result = builder.build(rows, mapping, lookup)
    assert [b.segment.id for b in result.segments] == ["S1", "S2"]


def test_the_vocabulary_is_consulted_before_the_pattern_matcher():
    result = builder.build([row(5, C="x", D="ca sĩ nữ")], MAPPING, lookup)
    assert result.segments[0].segment.expects == ("speech.vocal",)


def test_a_loanword_falls_through_to_the_pattern_matcher():
    """guitar is in patterns.yaml, not in the cuesheet vocabulary."""
    result = builder.build([row(5, C="x", D="guitar")], MAPPING, lookup)
    assert result.segments[0].segment.expects == ("instrument.guitar",)


def test_performers_split_on_commas_slashes_semicolons_and_newlines():
    result = builder.build(
        [row(5, C="x", D="guitar, ca sĩ nữ; trống\nbass")], MAPPING, lookup
    )
    assert set(result.segments[0].segment.expects) == {
        "instrument.guitar", "speech.vocal", "drums.kick", "instrument.bass",
    }


def test_expects_is_deduplicated_and_keeps_first_seen_order():
    result = builder.build([row(5, C="x", D="guitar, gtr, bass")], MAPPING, lookup)
    assert result.segments[0].segment.expects == ("instrument.guitar",
                                                  "instrument.bass")


def test_an_unresolvable_fragment_becomes_a_verbatim_comment():
    result = builder.build([row(5, C="x", D="tốp múa")], MAPPING, lookup)
    assert result.segments[0].segment.expects == ()
    assert any("tốp múa" in note for note in result.segments[0].comments)


def test_a_weak_pattern_hit_does_not_satisfy_an_expectation():
    """A weak guess in expects would make Q4 stop catching what it exists for.

    'spd' is confidence 0.75 in patterns.yaml, below the confident band.
    """
    result = builder.build([row(5, C="x", D="spd")], MAPPING, lookup)
    assert result.segments[0].segment.expects == ()
    assert any("spd" in note for note in result.segments[0].comments)


def test_note_and_time_become_comments_not_fields():
    result = builder.build(
        [row(5, C="x", B="19:45", E="Chuẩn bị backline")], MAPPING, lookup
    )
    built = result.segments[0]
    assert built.segment.time is None
    assert any("19:45" in note for note in built.comments)
    assert any("Chuẩn bị backline" in note for note in built.comments)


def test_a_row_without_a_title_becomes_a_loose_comment_not_a_segment():
    result = builder.build([row(5, C="", D="trống", E="thiếu tên")], MAPPING, lookup)
    assert result.segments == ()
    assert result.comment_rows == 1
    assert any("trống" in note for note in result.loose_comments)
    assert any("5" in note for note in result.loose_comments)


def test_the_counts_reconcile():
    rows = [row(5, C="Một"), row(6, C=""), row(7, C="Ba")]
    result = builder.build(rows, MAPPING, lookup, blank_rows=2)
    assert result.data_rows == 3
    assert len(result.segments) + result.comment_rows == result.data_rows
    assert result.blank_rows == 2


def test_every_comment_names_its_source_row():
    result = builder.build([row(9, C="x", D="tốp múa")], MAPPING, lookup)
    assert all("row 9" in note for note in result.segments[0].comments)
```

- [ ] **Step 2: Run the tests to verify they fail**

```powershell
python -m pytest tests\test_ingest_build.py -v
```

Expected: FAIL at collection — no module named `build`.

- [ ] **Step 3: Write the module**

Create `wing_parser/showcontext/ingest/build.py`:

```python
"""Rows and a vocabulary become Segment records. No I/O happens here.

The vocabulary lookup arrives as a callable rather than an import, which
is what keeps every interpretation decision in this file testable without
a filesystem -- and what keeps the module honest about performing no
reads of its own.

Nothing is ever guessed. A fragment that does not resolve confidently
becomes a verbatim comment, because a weak guess entering `expects:`
would make Q4 stop catching the thing it exists for -- the same argument
Q4's own rationale makes about channel classification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from wing_parser.classifier import matcher
from wing_parser.classifier.normalize import clean
from wing_parser.showcontext.models import Segment

_SPLIT = re.compile(r"[,/;\n]+")


@dataclass(frozen=True)
class BuiltSegment:
    segment: Segment
    comments: tuple[str, ...]


@dataclass(frozen=True)
class BuildResult:
    segments: tuple[BuiltSegment, ...]
    loose_comments: tuple[str, ...]
    data_rows: int
    comment_rows: int
    blank_rows: int


def resolve_fragment(fragment: str, lookup) -> str | None:
    """Vocabulary first, pattern matcher second, nothing third."""
    target = clean(fragment)
    if not target:
        return None

    remembered = lookup(target)
    if remembered is not None and matcher.is_confident(remembered):
        return remembered.kind

    found = matcher.classify(fragment, "channels")
    if matcher.is_confident(found):
        return found.kind

    return None


def _cell(row, mapping, field: str) -> str:
    letter = mapping.fields.get(field)
    if letter is None:
        return ""
    return row.cells.get(letter, "")


def _expectations(text: str, lookup, row_number: int) -> tuple[tuple[str, ...],
                                                               tuple[str, ...]]:
    kinds: list[str] = []
    comments: list[str] = []
    for fragment in _SPLIT.split(text):
        stripped = fragment.strip()
        if not stripped:
            continue
        kind = resolve_fragment(stripped, lookup)
        if kind is None:
            comments.append(
                f"row {row_number}: could not read performer {stripped!r}"
            )
        elif kind not in kinds:
            kinds.append(kind)
    return tuple(kinds), tuple(comments)


def build(rows, mapping, lookup, blank_rows: int = 0) -> BuildResult:
    built: list[BuiltSegment] = []
    loose: list[str] = []
    generated = 0

    for row in rows:
        title = _cell(row, mapping, "title").strip()
        performers = _cell(row, mapping, "performers")
        note = _cell(row, mapping, "note").strip()
        written_time = _cell(row, mapping, "time").strip()

        if not title:
            parts = [
                f"{name}={value!r}"
                for name, value in (
                    ("performers", performers.strip()),
                    ("note", note),
                    ("time", written_time),
                )
                if value
            ]
            loose.append(
                f"row {row.number}: no title, kept as a comment"
                + (" -- " + ", ".join(parts) if parts else "")
            )
            continue

        kinds, comments = _expectations(performers, lookup, row.number)
        notes = list(comments)
        if written_time:
            notes.insert(0, f"row {row.number}: time {written_time!r}")
        if note:
            notes.append(f"row {row.number}: note {note!r}")

        written_id = _cell(row, mapping, "id").strip()
        if not written_id:
            generated += 1
            written_id = f"S{generated}"

        built.append(
            BuiltSegment(
                segment=Segment(id=written_id, title=title, expects=kinds),
                comments=tuple(notes),
            )
        )

    return BuildResult(
        segments=tuple(built),
        loose_comments=tuple(loose),
        data_rows=len(rows),
        comment_rows=len(loose),
        blank_rows=blank_rows,
    )
```

- [ ] **Step 4: Run the tests to verify they pass**

```powershell
python -m pytest tests\test_ingest_build.py -v
```

Expected: all twelve PASS. If
`test_a_loanword_falls_through_to_the_pattern_matcher` or
`test_a_weak_pattern_hit_does_not_satisfy_an_expectation` fails, **do not adjust
the test to match the code** — re-read
`wing_parser/classifier/data/patterns.yaml`, confirm the kind and confidence for
that token, and report the discrepancy. The plan's expectations were read from
that file, but a confidence there may have moved.

- [ ] **Step 5: Prove the weak-hit test would catch a regression**

Change `matcher.is_confident(found)` to `matcher.is_usable(found)`, re-run
`test_a_weak_pattern_hit_does_not_satisfy_an_expectation`, confirm it goes
**red**, then restore.

- [ ] **Step 6: Commit**

```powershell
git add wing_parser/showcontext/ingest/build.py tests/test_ingest_build.py
git commit -F - <<'EOF'
Turn rows into segments, guessing nothing

The vocabulary lookup arrives as a callable, not an import, so this
module performs no I/O and every interpretation decision is testable
without a filesystem.

A fragment resolves through the cue-sheet vocabulary first and the
pattern matcher second, and only at or above the confident band. A weak
pattern hit is treated as unresolved, because a weak guess entering
expects: would make Q4 stop catching the thing it exists for.

Anything unresolved becomes a verbatim comment naming its source row.
A row with no title becomes a comment rather than a segment, and its
other cells go into that comment so nothing disappears.
EOF
```

---

### Task 5: `emit.py` — YAML with the comments as payload

**Files:**
- Create: `wing_parser/showcontext/ingest/emit.py`
- Test: `tests/test_ingest_emit.py`

**Interfaces:**
- Consumes: `build.BuildResult` (Task 4).
- Produces: `render(show: str, result, proposals: dict[str, tuple[str, ...]] |
  None = None) -> str` — the complete YAML document as text.
  `proposals` maps a segment id to the comment lines Task 6 generates; `None`
  means `--scene` was not used.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_ingest_emit.py`:

```python
import yaml

from wing_parser.showcontext.ingest import emit
from wing_parser.showcontext.ingest.build import BuildResult, BuiltSegment
from wing_parser.showcontext.models import Segment


def _result(**overrides):
    base = dict(
        segments=(
            BuiltSegment(
                segment=Segment(id="S1", title="Đón khách",
                                expects=("instrument.keys",)),
                comments=("row 5: time '19:00'",),
            ),
        ),
        loose_comments=("row 9: no title, kept as a comment -- note='x'",),
        data_rows=2,
        comment_rows=1,
        blank_rows=1,
    )
    base.update(overrides)
    return BuildResult(**base)


def test_the_output_is_valid_yaml_and_round_trips():
    text = emit.render("Test show", _result())
    doc = yaml.safe_load(text)
    assert doc["show"] == "Test show"
    assert doc["segments"][0]["id"] == "S1"
    assert doc["segments"][0]["expects"] == ["instrument.keys"]


def test_every_segment_carries_an_empty_cues_list():
    """It is true, the loader reads it, and it anchors the --scene comment."""
    doc = yaml.safe_load(emit.render("t", _result()))
    assert doc["segments"][0]["cues"] == []


def test_a_row_comment_survives_into_the_text():
    text = emit.render("t", _result())
    assert "row 5: time '19:00'" in text


def test_a_loose_comment_survives_into_the_text():
    """The whole point: an unreadable row must not vanish."""
    text = emit.render("t", _result())
    assert "row 9: no title" in text


def test_the_reconciliation_line_states_the_counts():
    text = emit.render("t", _result())
    assert "2 data row" in text
    assert "1 segment" in text
    assert "1 row" in text and "comment" in text


def test_a_title_with_yaml_punctuation_survives():
    """A colon, a hash and a quote in one Vietnamese title."""
    nasty = 'Tiết mục: "Nắng" #1'
    result = _result(segments=(
        BuiltSegment(segment=Segment(id="S1", title=nasty), comments=()),
    ))
    doc = yaml.safe_load(emit.render("t", result))
    assert doc["segments"][0]["title"] == nasty


def test_a_scene_proposal_appears_above_the_cues_key():
    result = _result()
    text = emit.render("t", result, proposals={"S1": ("ch 13 \"GTR\" is keys",)})
    lines = [line.strip() for line in text.splitlines()]
    proposal_at = next(i for i, line in enumerate(lines) if "ch 13" in line)
    cues_at = next(i for i, line in enumerate(lines) if line.startswith("cues:"))
    assert proposal_at < cues_at


def test_the_document_loads_through_the_show_context_loader(tmp_path):
    """The real contract: what this writes, load_show_context must read."""
    from wing_parser.showcontext import load_show_context

    path = tmp_path / "out.yaml"
    path.write_text(emit.render("Test show", _result()), encoding="utf-8")
    context = load_show_context(path)
    assert context.show == "Test show"
    assert len(context.segments) == 1
    assert context.segments[0].expects == ("instrument.keys",)
    assert context.anomalies == ()
```

- [ ] **Step 2: Run the tests to verify they fail**

```powershell
python -m pytest tests\test_ingest_emit.py -v
```

Expected: FAIL at collection — no module named `emit`.

- [ ] **Step 3: Write the module**

Create `wing_parser/showcontext/ingest/emit.py`:

```python
"""Records and comments become a YAML document.

ruamel rather than a hand-rolled emitter: the comments are the payload
here, and a hand-rolled one would need its own YAML scalar quoting, which
has silent edge cases (U+2028, an all-whitespace scalar) in new code
where existing code will do.

Every segment carries a real `cues: []`. It is true -- the sheet has no
cues -- the loader reads it as empty, and it gives a --scene proposal a
key to attach a comment before. Without it a segment has no key after
`expects:`, and ruamel has nothing to anchor to.
"""

from __future__ import annotations

import io

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

_INDENT = 4

_HEADER = """\
Generated by `wing showcontext import`. Read it before you use it.

Times and notes from the sheet are comments, not fields: nothing in this
tool reads a segment time, and a sheet's wall-clock time is not the
show-relative form `time:` accepts.

Only Q4 and Q5 fire on a file with no cues. Uncomment a proposed cue to
bring Q1, Q2 and Q6 to life (and Q3 once a DCA is named; Q7 ships disabled) for that segment.
"""


def _flow(values) -> CommentedSeq:
    seq = CommentedSeq(values)
    seq.fa.set_flow_style()
    return seq


def _segment(built, proposal: tuple[str, ...]) -> CommentedMap:
    item = CommentedMap()
    item["id"] = built.segment.id
    item["title"] = built.segment.title
    item["expects"] = _flow(list(built.segment.expects))
    item["cues"] = _flow([])
    if proposal:
        item.yaml_set_comment_before_after_key(
            "cues", before="\n".join(proposal), indent=_INDENT
        )
    return item


def render(show: str, result, proposals: dict[str, tuple[str, ...]] | None = None) -> str:
    proposals = proposals or {}

    doc = CommentedMap()
    doc["show"] = show
    doc.yaml_set_start_comment(_HEADER)

    segments = CommentedSeq()
    for index, built in enumerate(result.segments):
        segments.append(_segment(built, proposals.get(built.segment.id, ())))
        if built.comments:
            segments.yaml_set_comment_before_after_key(
                index, before="\n".join(built.comments), indent=_INDENT
            )
    doc["segments"] = segments

    engine = YAML()
    engine.indent(mapping=2, sequence=4, offset=2)
    engine.preserve_quotes = True
    engine.width = 4096
    buffer = io.StringIO()
    engine.dump(doc, buffer)
    text = buffer.getvalue()

    trailer = [""]
    if result.loose_comments:
        trailer.append("# rows kept as comments, not imported:")
        trailer.extend(f"# {line}" for line in result.loose_comments)
    trailer.append(
        f"# imported {result.data_rows} data row(s) -> "
        f"{len(result.segments)} segment(s), "
        f"{result.comment_rows} row(s) kept as comments, "
        f"{result.blank_rows} blank row(s) skipped"
    )
    return text + "\n".join(trailer) + "\n"
```

- [ ] **Step 4: Run the tests and read the actual output**

```powershell
python -m pytest tests\test_ingest_emit.py -v
```

Then look at a real document, because `ruamel`'s comment placement has to be
seen rather than assumed:

```powershell
python -c "from tests.test_ingest_emit import _result; from wing_parser.showcontext.ingest import emit; print(emit.render('Demo', _result(), proposals={'S1': ('ch 13 GTR is keys',)}))"
```

Expected: PASS, and the printed document has each row comment above its segment
and the proposal directly above `cues: []`. If `yaml_set_comment_before_after_key`
places a comment somewhere else, adjust the `indent` argument until the printed
output is right — then let the tests pin whatever it actually produces. **Do not
weaken an assertion to match a wrong placement.**

- [ ] **Step 5: Prove the loose-comment test would catch a regression**

Delete the `if result.loose_comments:` block, re-run
`test_a_loose_comment_survives_into_the_text`, confirm it goes **red**, then
restore. This is the assertion that guards the failure the whole feature exists
to prevent.

- [ ] **Step 6: Commit**

```powershell
git add wing_parser/showcontext/ingest/emit.py tests/test_ingest_emit.py
git commit -F - <<'EOF'
Emit a show-context document with the comments as payload

ruamel rather than a hand-rolled emitter: a hand-rolled one would need
its own YAML scalar quoting, which has silent edge cases in new code
where existing code will do.

Every segment carries a real cues: []. It is true, the loader reads it
as empty, and it gives a --scene proposal a key to attach a comment
before -- without it a segment has no key after expects: and ruamel has
nothing to anchor to.

The document ends with a reconciliation line. Never dropping a row is
not enough on its own; the count has to be checkable at a glance, or a
sheet that looks fully imported and is missing three rows still reads as
complete.
EOF
```

---

### Task 6: `--scene` — propose a cue skeleton, as comments only

**Files:**
- Modify: `wing_parser/showcontext/view.py:138`, `:183`, `:187`
- Create: `wing_parser/showcontext/ingest/propose.py`
- Test: `tests/test_ingest_propose.py`

**Interfaces:**
- Consumes: `build.BuildResult` (Task 4), a `WingScene`.
- Produces:
  - `wing_parser.showcontext.view.channels_of(scene, kind) -> tuple` — the
    former `_channels_of`, now public.
  - `propose.for_segments(result, scene) -> dict[str, tuple[str, ...]]` — segment
    id → comment lines, in the shape `emit.render`'s `proposals` expects.

`propose.py` is a fifth small module rather than part of `build.py` because
`build.py` performs no I/O and takes no scene; keeping the scene out of it is
what makes its tests filesystem-free.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_ingest_propose.py`:

```python
import pytest

from wing_parser import WingScene
from wing_parser.showcontext.ingest import propose
from wing_parser.showcontext.ingest.build import BuildResult, BuiltSegment
from wing_parser.showcontext.models import Segment
from wing_parser.showcontext.view import channels_of


@pytest.fixture(scope="module")
def scene(vu_path):
    """conftest.py provides vu_path (a Path), not a loaded scene."""
    return WingScene.load(vu_path)


def _result(expects):
    return BuildResult(
        segments=(BuiltSegment(segment=Segment(id="S1", title="t", expects=expects),
                               comments=()),),
        loose_comments=(), data_rows=1, comment_rows=0, blank_rows=0,
    )


def _a_confident_kind(scene):
    for channel in scene.channels():
        if channel.source_type.confidence >= 0.8:
            return channel.source_type.kind
    pytest.fail("the sample scene must classify at least one channel confidently")


def test_a_matched_kind_proposes_a_cue_naming_the_channel(scene):
    kind = _a_confident_kind(scene)
    numbers = [c.data.number for c in channels_of(scene, kind)]

    lines = propose.for_segments(_result((kind,)), scene)["S1"]
    body = "\n".join(lines)
    assert kind in body
    assert str(numbers[0]) in body
    assert "action: open" in body


def test_the_proposal_carries_every_matching_channel(scene):
    """A kind on three channels must propose all three, not just the first."""
    kind = max(
        {c.source_type.kind for c in scene.channels()
         if c.source_type.confidence >= 0.8},
        key=lambda k: len(channels_of(scene, k)),
    )
    numbers = sorted({c.data.number for c in channels_of(scene, kind)})
    body = "\n".join(propose.for_segments(_result((kind,)), scene)["S1"])
    for number in numbers:
        assert str(number) in body


def test_an_unmatched_kind_proposes_nothing(scene):
    assert propose.for_segments(_result(("instrument.theremin",)), scene) == {}


def test_a_segment_with_no_expects_proposes_nothing(scene):
    assert propose.for_segments(_result(()), scene) == {}


def test_channels_of_is_public_and_the_private_name_is_gone():
    from wing_parser.showcontext import view

    assert hasattr(view, "channels_of")
    assert not hasattr(view, "_channels_of")
```

`vu_path` is the session-scoped fixture already in `tests/conftest.py:35`. There
is **no** `vu_scene` fixture — do not add one; the module-scoped `scene` above
loads it once for this file, which is what the rest of the suite does.

- [ ] **Step 2: Run the tests to verify they fail**

```powershell
python -m pytest tests\test_ingest_propose.py -v
```

Expected: FAIL — no module named `propose`, and `view.channels_of` missing.

- [ ] **Step 3: Make `channels_of` public**

In `wing_parser/showcontext/view.py`, rename `_channels_of` at line 138 to
`channels_of` and update both call sites (lines 183 and 187). Add one line to its
docstring:

```python
    Public because the ingest layer joins an imported `expects:` against
    the same channels, and the two must not drift apart.
```

- [ ] **Step 4: Write the module**

Create `wing_parser/showcontext/ingest/propose.py`:

```python
"""Join an imported `expects:` against a scene, as a commented-out cue.

Nothing is ever written outside a comment. This is a join between two
things already computed -- the kinds build.py resolved and the
classifications the scene already carries -- so it adds no new
name-guessing layer, and this project has exactly one of those on
purpose.

The proposal is a whole cue rather than a channel list because `channels`
is a Cue field, not a Segment field. Uncommenting it does more than fill
in a number: it brings Q1, Q2 and Q6 to life (and Q3 once a DCA is named; Q7 ships disabled) for that segment.
"""

from __future__ import annotations

from wing_parser.showcontext.view import channels_of


def for_segments(result, scene) -> dict[str, tuple[str, ...]]:
    proposals: dict[str, tuple[str, ...]] = {}

    for built in result.segments:
        numbers: list[int] = []
        found: list[str] = []
        for kind in built.segment.expects:
            matches = channels_of(scene, kind)
            if not matches:
                continue
            for channel in matches:
                numbers.append(channel.data.number)
                found.append(
                    f"--scene: ch {channel.data.number} "
                    f"{channel.data.name!r} is {kind}"
                )

        if not numbers:
            continue

        listed = ", ".join(str(number) for number in sorted(set(numbers)))
        proposals[built.segment.id] = tuple(found) + (
            "uncomment to make this a cue:",
            f"  - id: \"{built.segment.id} cue 1\"",
            "    action: open",
            f"    channels: [{listed}]",
        )

    return proposals
```

- [ ] **Step 5: Run the tests to verify they pass**

```powershell
python -m pytest tests\test_ingest_propose.py tests\test_showcontext_view.py tests\test_showcontext_rules.py -v
```

Expected: PASS. The two existing modules are included because Step 3 renamed a
function they depend on.

- [ ] **Step 6: Run the whole suite**

```powershell
python -m pytest tests\
```

Expected: exit code 0. A rename that misses a call site shows up here.

- [ ] **Step 7: Commit**

```powershell
git add wing_parser/showcontext/view.py wing_parser/showcontext/ingest/propose.py tests/test_ingest_propose.py tests/conftest.py
git commit -F - <<'EOF'
Propose a cue skeleton from the scene, as comments only

channels is a Cue field, not a Segment field, so an importer that emits
no cues has nowhere to put a channel number at all. The proposal is
therefore a whole commented-out cue, which is the better shape anyway:
uncommenting it brings Q1, Q2 and Q6 to life (and Q3 once a DCA is named; Q7 ships disabled) for that segment.

The join reuses view._channels_of, promoted to a public channels_of so
the ingest layer and Q4/Q5 cannot drift apart on what counts as a
confidently-classified channel.
EOF
```

---

### Task 7: `showcontext import` on the CLI

**Files:**
- Modify: `wing_parser/cli/__main__.py:98-104`, `wing_parser/cli/commands.py`,
  `wing_parser/cli/render.py`
- Test: `tests/test_cli_showcontext.py`

**Interfaces:**
- Consumes: every module from Tasks 2–6.
- Produces: `commands.showcontext_import(args) -> int`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_cli_showcontext.py`. That file already imports
`main` from `wing_parser.cli.__main__` and calls it directly with an argument
list — keep that style. It has **no** `DATA` constant, so add one at the top
beside the existing imports:

```python
from pathlib import Path

DATA = Path(__file__).resolve().parent / "data"
```

```python
def test_import_writes_a_file_that_the_loader_reads(tmp_path, capsys):
    from wing_parser.cli.__main__ import main
    from wing_parser.showcontext import load_show_context

    out = tmp_path / "tonight.yaml"
    code = main([
        "showcontext", "import",
        str(DATA / "ingest-fixture.xlsx"),
        "--map", str(DATA / "ingest-fixture-map.yaml"),
        "-o", str(out),
    ])
    assert code == 0
    context = load_show_context(out)
    assert context.anomalies == ()
    assert len(context.segments) == 4


def test_import_without_output_prints_to_stdout(capsys):
    from wing_parser.cli.__main__ import main

    code = main([
        "showcontext", "import",
        str(DATA / "ingest-fixture.xlsx"),
        "--map", str(DATA / "ingest-fixture-map.yaml"),
    ])
    assert code == 0
    assert "segments:" in capsys.readouterr().out


def test_import_refuses_to_overwrite_without_force(tmp_path):
    from wing_parser.cli.__main__ import main

    out = tmp_path / "tonight.yaml"
    out.write_text("do not lose me\n", encoding="utf-8")
    code = main([
        "showcontext", "import",
        str(DATA / "ingest-fixture.xlsx"),
        "--map", str(DATA / "ingest-fixture-map.yaml"),
        "-o", str(out),
    ])
    assert code == 1
    assert out.read_text(encoding="utf-8") == "do not lose me\n"


def test_force_overwrites(tmp_path):
    from wing_parser.cli.__main__ import main

    out = tmp_path / "tonight.yaml"
    out.write_text("replace me\n", encoding="utf-8")
    code = main([
        "showcontext", "import",
        str(DATA / "ingest-fixture.xlsx"),
        "--map", str(DATA / "ingest-fixture-map.yaml"),
        "-o", str(out), "--force",
    ])
    assert code == 0
    assert "segments:" in out.read_text(encoding="utf-8")


def test_a_bad_mapping_reports_the_problem_and_exits_one(tmp_path, capsys):
    from wing_parser.cli.__main__ import main

    bad = tmp_path / "map.yaml"
    bad.write_text("header_row: 4\ncolumns:\n  time: B\n", encoding="utf-8")
    code = main([
        "showcontext", "import",
        str(DATA / "ingest-fixture.xlsx"), "--map", str(bad),
    ])
    assert code == 1
    assert "title" in capsys.readouterr().err
```

- [ ] **Step 2: Run the tests to verify they fail**

```powershell
python -m pytest tests\test_cli_showcontext.py -k import -v
```

Expected: FAIL — `invalid choice: 'import'`.

- [ ] **Step 3: Register the subcommand**

In `wing_parser/cli/__main__.py`, immediately after the `lint` block that ends at
line 104:

```python
    importer = inner.add_parser(
        "import", help="build a show-context file from a producer's spreadsheet"
    )
    importer.add_argument("sheet", help="the .xlsx file")
    importer.add_argument(
        "--map", dest="mapping", required=True,
        help="the mapping file for this producer's template",
    )
    importer.add_argument("-o", "--output", default=None,
                          help="write here instead of printing")
    importer.add_argument("--scene", default=None,
                          help="propose cues from this scene, as comments")
    importer.add_argument("--force", action="store_true",
                          help="overwrite an existing output file")
    importer.set_defaults(handler=commands.showcontext_import)
```

`--map` uses `dest="mapping"` because `args.map` would shadow nothing but reads
badly beside the builtin; the dest is what the handler uses.

- [ ] **Step 4: Add the handler**

In `wing_parser/cli/commands.py`, after `showcontext_lint`:

```python
def showcontext_import(args) -> int:
    from wing_parser.classifier import cache
    from wing_parser.showcontext.ingest import build, emit, mapping, propose, sheet

    destination = Path(args.output) if args.output else None
    if destination is not None and destination.exists() and not args.force:
        print(
            f"error: {destination} already exists. Pass --force to replace it.",
            file=sys.stderr,
        )
        return 1

    try:
        raw = mapping.load_mapping(args.mapping)
        read = sheet.read_sheet(args.sheet, raw.sheet, raw.header_row)
        resolved = mapping.resolve_columns(raw, read.headers)
    except (OSError, ValueError, sheet.MissingExtra) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    result = build.build(
        read.rows,
        resolved,
        lambda term: cache.lookup(term, "cuesheet"),
        blank_rows=read.blank_rows,
    )

    proposals = None
    if args.scene is not None:
        scene = _load(args.scene)
        if scene is None:
            return 1
        proposals = propose.for_segments(result, scene)

    text = emit.render(Path(args.sheet).stem, result, proposals)

    if destination is None:
        print(text)
    else:
        destination.write_text(text, encoding="utf-8")
        print(render.import_summary(destination, result), file=sys.stderr)
    return 0
```

- [ ] **Step 5: Add the summary line**

In `wing_parser/cli/render.py`, matching that module's existing style:

```python
def import_summary(destination, result) -> str:
    return (
        f"wrote {destination}: {len(result.segments)} segment(s) from "
        f"{result.data_rows} data row(s), {result.comment_rows} row(s) kept as "
        f"comments. Only Q4 and Q5 fire until you uncomment a cue."
    )
```

The summary goes to **stderr** so that `wing showcontext import ... | ...` still
pipes clean YAML.

- [ ] **Step 6: Run the tests to verify they pass**

```powershell
python -m pytest tests\test_cli_showcontext.py -v
```

Expected: PASS. If the segment count in
`test_import_writes_a_file_that_the_loader_reads` is not 4, count the fixture's
titled rows in `docs/probes/probe12_make_ingest_fixture.py` — five data rows, one
with an empty title — and correct the **test** only after confirming the code is
right.

- [ ] **Step 7: Prove the overwrite guard would catch a regression**

Delete the `destination.exists()` check, re-run
`test_import_refuses_to_overwrite_without_force`, confirm it goes **red**, then
restore.

- [ ] **Step 8: Commit**

```powershell
git add wing_parser/cli/ tests/test_cli_showcontext.py
git commit -F - <<'EOF'
Add showcontext import to the CLI

Without -o the document goes to stdout so it can be read before anything
touches disk. With -o an existing file is never replaced without
--force.

The summary goes to stderr, so piping the command yields clean YAML.
It states that only Q4 and Q5 fire until a cue is uncommented, because a
file producing two rules' worth of findings must not read as one that
produced all seven.
EOF
```

---

### Task 8: The end-to-end contract, the invariance check, and the README

**Files:**
- Create: `tests/test_ingest_contract.py`
- Modify: `README.md`
- Test: the whole suite

**Interfaces:**
- Consumes: everything.
- Produces: nothing new.

- [ ] **Step 1: Write the contract test**

Create `tests/test_ingest_contract.py`:

```python
"""Pin the whole pipeline against the generated fixture.

Regenerate the fixture with:
    python docs/probes/probe12_make_ingest_fixture.py

Regenerate this file's expectation by running the command and reading the
output. Do not adjust an expectation to match a change you did not intend.
"""

from pathlib import Path

import yaml

from wing_parser.cli.__main__ import main
from wing_parser.showcontext import load_show_context

DATA = Path(__file__).resolve().parent / "data"


def test_the_fixture_imports_to_exactly_this(tmp_path):
    out = tmp_path / "tonight.yaml"
    assert main([
        "showcontext", "import", str(DATA / "ingest-fixture.xlsx"),
        "--map", str(DATA / "ingest-fixture-map.yaml"), "-o", str(out),
    ]) == 0

    doc = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert [(s["id"], s["title"], tuple(s["expects"])) for s in doc["segments"]] == [
        ("1", "Đón khách", ()),
        ("2", "MC khai mạc", ("speech.mc",)),
        ("3", "Tiết mục 3 — Guitar", ("instrument.guitar",)),
        ("5", "Tiết mục 5", ()),
    ]


def test_the_row_with_no_title_is_present_as_a_comment(tmp_path):
    out = tmp_path / "tonight.yaml"
    main(["showcontext", "import", str(DATA / "ingest-fixture.xlsx"),
          "--map", str(DATA / "ingest-fixture-map.yaml"), "-o", str(out)])
    text = out.read_text(encoding="utf-8")
    assert "row 9" in text
    assert "dòng thiếu tên" in text


def test_the_unresolvable_performer_is_present_as_a_comment(tmp_path):
    out = tmp_path / "tonight.yaml"
    main(["showcontext", "import", str(DATA / "ingest-fixture.xlsx"),
          "--map", str(DATA / "ingest-fixture-map.yaml"), "-o", str(out)])
    assert "tốp múa" in out.read_text(encoding="utf-8")


def test_the_counts_reconcile_in_the_written_file(tmp_path):
    out = tmp_path / "tonight.yaml"
    main(["showcontext", "import", str(DATA / "ingest-fixture.xlsx"),
          "--map", str(DATA / "ingest-fixture-map.yaml"), "-o", str(out)])
    text = out.read_text(encoding="utf-8")
    assert "imported 5 data row(s) -> 4 segment(s)" in text
    assert "1 row(s) kept as comments" in text
    assert "1 blank row(s) skipped" in text


def test_doctor_runs_against_the_imported_file(tmp_path, vu_path):
    """The imported file must be usable, not merely parseable."""
    out = tmp_path / "tonight.yaml"
    main(["showcontext", "import", str(DATA / "ingest-fixture.xlsx"),
          "--map", str(DATA / "ingest-fixture-map.yaml"), "-o", str(out)])
    assert main(["doctor", str(vu_path), "--show", str(out)]) == 0


def test_ca_si_nu_resolves_once_it_is_in_the_vocabulary(tmp_path, monkeypatch):
    """Proves the cuesheet domain is actually consulted end to end.

    conftest.py's session-scoped _isolated_knowledge_dir already points the
    suite at a throwaway directory; monkeypatch.setenv overrides it for this
    test only and restores it afterwards.
    """
    from wing_parser import config
    from wing_parser.classifier import cache
    from wing_parser.classifier.matcher import Classification

    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    cache.remember(
        "ca sĩ nữ", "cuesheet",
        Classification(kind="speech.vocal", confidence=0.95, origin="manual"),
        directory=knowledge,
    )
    monkeypatch.setenv(config.ENV_VAR, str(knowledge))

    out = tmp_path / "tonight.yaml"
    main(["showcontext", "import", str(DATA / "ingest-fixture.xlsx"),
          "--map", str(DATA / "ingest-fixture-map.yaml"), "-o", str(out)])
    doc = yaml.safe_load(out.read_text(encoding="utf-8"))
    guitar_row = next(s for s in doc["segments"] if s["id"] == "3")
    assert "speech.vocal" in guitar_row["expects"]
```

- [ ] **Step 2: Run it and reconcile against reality**

```powershell
python -m pytest tests\test_ingest_contract.py -v
```

The expectations above were derived by hand from the fixture and
`patterns.yaml`. Where one disagrees with the real output, **read the output,
decide which is right, and say which you changed and why.** The `("2", "MC khai
mạc", ("speech.mc",))` row in particular depends on `\bmc\b` matching the
performers cell `MC` — confirm it does rather than assuming.

- [ ] **Step 3: Confirm the invariance that guards everything else**

```powershell
python -m pytest tests\test_advisory_realfile.py -v
python -m pytest tests\test_corpus_realfiles.py -v
```

Expected: PASS. The unprofiled real file must still yield exactly **22**
findings, and the five real scenes still **0, 13, 13, 1, 17**. If either moved,
this feature has leaked into existing behaviour — **stop and report**, do not
re-pin the number.

- [ ] **Step 4: Run the whole suite and compare to the baseline**

```powershell
python -m pytest tests\
python -c "import subprocess,sys; print(subprocess.run([sys.executable,'-m','pytest','tests/','--collect-only','-q'],capture_output=True,text=True).stdout.strip().splitlines()[-1])"
```

Expected: exit code 0, and a collected count of 1056 plus the tests this plan
added. Record the actual number in the commit message.

- [ ] **Step 5: Document it in the README**

Add a section next to the existing show-context documentation:

````markdown
### Building a show context from a producer's spreadsheet

```powershell
python -m wing_parser.cli showcontext import ros.xlsx --map knowledge\toanaz\sheets\abc.yaml -o tonight.yaml
python -m wing_parser.cli showcontext import ros.xlsx --map ...\abc.yaml --scene tonight.snap -o tonight.yaml
```

Write one mapping file per producer, naming the sheet, the header row, and
which column means what. Columns are given either by letter (`columns:`) or by
the text in the header cell (`headers:`) — never both for the same field.

**An imported file has no cues**, because a running order does not carry them.
Only **Q4** ("show expects a source with no channel for it") and **Q5** ("...
whose channels are all parked") fire on it. With `--scene`, each segment gets a
commented-out cue naming the channels that match its expected kinds;
uncommenting one brings Q1, Q2 and Q6 to life (and Q3 once a DCA is named; Q7 ships disabled) for that segment.

Anything the importer cannot read — a row with no title, a performer it does not
recognise — is kept in the file as a comment, and the last line reconciles the
counts. Nothing is dropped and nothing is guessed.

Vietnamese cue-sheet terms live in the `cuesheet:` section of
`knowledge/toanaz/classifier.yaml`. Add a term once and every later import knows
it.
````

- [ ] **Step 6: Commit**

```powershell
git add tests/test_ingest_contract.py README.md
git commit -F - <<'EOF'
Pin the ingest pipeline end to end, and document it

The contract test asserts what the fixture actually becomes, that the
untitled row and the unreadable performer are both present as comments,
and that the reconciliation counts add up. It also proves the cuesheet
domain is consulted end to end rather than merely existing.

The invariance that guards everything else still holds: the unprofiled
real file yields exactly 22 findings, and the five real scenes still
yield 0, 13, 13, 1, 17.

The README says plainly that only Q4 and Q5 fire on an imported file. A
file producing two rules' worth of findings must not read as one that
produced all seven.
EOF
```

---

## Self-Review

**Spec coverage.** Every numbered section of the design maps to a task:
§3's two-of-seven consequence → Task 7 Step 5 and Task 8 Step 5 · §4 mapping
contract, §4.1 two blocks, §4.2 exact header matching, §4.3 letters → Task 3 ·
§5 row-to-segment table and §5.1 comments-not-fields → Task 4 · §6 the
`cuesheet` domain, §6.2 the stale message, §6.3 resolution order → Tasks 1 and
4 · §7 `--scene` and the `channels_of` promotion → Task 6 · §8 modules and §8.1
CLI → Tasks 2–7 · §8.2 dependencies → Task 2 Step 7 · §9 error table → Tasks 2,
3, 4, 7 · §10 testing, fixture and probe → Tasks 2 and 8 · §11 rejected
approaches → nothing to build, by definition · §12 open questions → carried
below · §13 multi-provider → explicitly out of scope, no task.

**Two spec items deliberately have no task**, and both are ToanAZ's calls, not
omissions:

- **§12.1 — no real cue sheet has been read.** The fixture in Task 2 is
  invented from his description. If he supplies a real `.xlsx` before Task 1,
  regenerate the fixture from it and re-derive Task 8's expectations; the
  structure of every task survives, only the fixture data changes.
- **§12.2 — the `cuesheet` vocabulary ships empty.** Task 1 creates the section;
  what goes in it is his judgement about his own work. Until he seeds it, only
  the loanwords `patterns.yaml` already covers will resolve, and everything else
  becomes a comment — which is the correct, honest behaviour, not a bug.

**Placeholder scan.** No "TBD", no "add appropriate error handling", no "similar
to Task N". Every code step carries the actual code; every test step carries the
actual assertions.

**Type consistency.** `RawRow(number, cells)` and `SheetRead(headers, rows,
blank_rows)` are defined in Task 2 and used unchanged in Tasks 3, 4, 7 and 8.
`SheetMapping(source, fields)` is defined in Task 3 and consumed in Task 4 via
`mapping.fields.get(field)`. `BuildResult(segments, loose_comments, data_rows,
comment_rows, blank_rows)` is defined in Task 4 and consumed by name in Tasks 5,
6, 7 and 8. `emit.render(show, result, proposals)` in Task 5 takes exactly what
`propose.for_segments` in Task 6 returns — `dict[str, tuple[str, ...]]` keyed by
segment id. `channels_of` is named identically in Tasks 6's rename, its
docstring, `propose.py` and the test that asserts the private name is gone.
