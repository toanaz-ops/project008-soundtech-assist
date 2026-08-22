"""Pin the whole pipeline against the generated fixture.

Regenerate the fixture with:
    python docs/probes/probe12_make_ingest_fixture.py

Regenerate this file's expectation by running the command and reading the
output. Do not adjust an expectation to match a change you did not intend.
"""

from pathlib import Path

import yaml

from wing_parser.cli.__main__ import main

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
    assert "carrying 2 expectation(s)" in text
    assert "1 row(s) and 3 performer fragment(s) kept as comments" in text
    assert "1 blank row(s) skipped" in text


def test_a_mapping_with_no_performers_is_visible_in_the_counts(tmp_path, capsys):
    """`performers:` is optional (spec section 4), and omitting it gives
    every segment `expects: []`.

    Rows alone cannot show that: this import and the correct one produce
    identical row counts, an identical summary line, and -- because
    nothing expects anything -- the same 22 findings a `doctor` run with
    no --show at all produces. The expectation count is what tells a
    fully imported file apart from one that will never say anything.
    """
    mapping = tmp_path / "no-performers.yaml"
    mapping.write_text(
        'sheet: "KỊCH BẢN"\nheader_row: 4\ncolumns:\n  id: A\n  title: C\n',
        encoding="utf-8",
    )
    out = tmp_path / "quiet.yaml"
    assert main(["showcontext", "import", str(DATA / "ingest-fixture.xlsx"),
                 "--map", str(mapping), "-o", str(out)]) == 0

    text = out.read_text(encoding="utf-8")
    assert "4 segment(s) carrying 0 expectation(s)" in text
    assert "4 segment(s) carrying 0 expectation(s)" in capsys.readouterr().err

    correct = tmp_path / "tonight.yaml"
    main(["showcontext", "import", str(DATA / "ingest-fixture.xlsx"),
          "--map", str(DATA / "ingest-fixture-map.yaml"), "-o", str(correct)])
    assert "4 segment(s) carrying 2 expectation(s)" in correct.read_text(
        encoding="utf-8"
    )


def test_doctor_runs_against_the_imported_file(tmp_path, vu_path, monkeypatch):
    """The imported file must be usable, not merely parseable."""
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
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
