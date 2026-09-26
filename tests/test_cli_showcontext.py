# tests/test_cli_showcontext.py
import json
from pathlib import Path

import yaml

from wing_parser.cli.__main__ import main

DATA = Path(__file__).resolve().parent / "data"


def _show(tmp_path):
    path = tmp_path / "tonight.yaml"
    path.write_text(yaml.safe_dump({"show": "t", "segments": [
        {"id": "S1", "cues": [{"id": "SQ 1", "action": "open", "channels": [99]}]}]}),
        encoding="utf-8")
    return path


def test_doctor_with_show_reports_a_q_finding(vu_path, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    assert main(["doctor", str(vu_path), "--show", str(_show(tmp_path))]) == 0
    assert "Q1" in capsys.readouterr().out


def test_doctor_without_show_reports_no_q_finding(vu_path, capsys, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    assert main(["doctor", str(vu_path)]) == 0
    assert "Q1" not in capsys.readouterr().out


def test_a_bad_show_path_exits_one_and_names_the_file(vu_path, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    assert main(["doctor", str(vu_path), "--show", str(tmp_path / "nope.yaml")]) == 1
    assert "nope.yaml" in capsys.readouterr().err


def test_show_anomalies_are_printed(vu_path, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    path = tmp_path / "typo.yaml"
    path.write_text(yaml.safe_dump({"show": "t", "segments": [
        {"id": "S1", "expects": ["instrument.kyes"]}]}), encoding="utf-8")
    main(["doctor", str(vu_path), "--show", str(path)])
    err = capsys.readouterr().err
    assert "instrument.kyes" in err and "instrument.keys" in err


def test_doctor_show_json_keeps_stdout_pure_json(vu_path, tmp_path, capsys, monkeypatch):
    """`--show` plus `--json` is the combination Finding 1 caught: show
    anomalies used to print to stdout ahead of the JSON envelope, so
    `json.loads` on stdout broke the moment a --show file had a repairable
    typo. Anomalies belong on stderr, same as every other diagnostic in
    this module."""
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    path = tmp_path / "typo.yaml"
    path.write_text(yaml.safe_dump({"show": "t", "segments": [
        {"id": "S1", "expects": ["instrument.kyes"]}]}), encoding="utf-8")
    assert main(["doctor", str(vu_path), "--show", str(path), "--json"]) == 0
    captured = capsys.readouterr()
    findings = json.loads(captured.out)
    assert isinstance(findings, list)
    assert "instrument.kyes" in captured.err and "instrument.keys" in captured.err


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


def test_a_syntactically_broken_mapping_reports_the_problem_and_exits_one(tmp_path, capsys):
    from wing_parser.cli.__main__ import main

    bad = tmp_path / "broken.yaml"
    bad.write_text("header_row: [unbalanced\n", encoding="utf-8")
    code = main([
        "showcontext", "import",
        str(DATA / "ingest-fixture.xlsx"), "--map", str(bad),
    ])
    assert code == 1
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert str(bad) in err


def test_a_non_workbook_sheet_reports_the_problem_and_exits_one(tmp_path, capsys):
    from wing_parser.cli.__main__ import main

    fake = tmp_path / "not-a-workbook.xlsx"
    fake.write_text("this is not a real spreadsheet\n", encoding="utf-8")
    code = main([
        "showcontext", "import",
        str(fake), "--map", str(DATA / "ingest-fixture-map.yaml"),
    ])
    assert code == 1
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert str(fake) in err


def _knowledge(tmp_path, monkeypatch, body):
    """Point the importer at a hand-edited classifier.yaml of our own.

    conftest.py's session-scoped _isolated_knowledge_dir already redirects
    the suite; monkeypatch.setenv overrides it for this test only.
    """
    from wing_parser import config

    directory = tmp_path / "knowledge"
    directory.mkdir()
    (directory / "classifier.yaml").write_text(body, encoding="utf-8")
    monkeypatch.setenv(config.ENV_VAR, str(directory))
    return directory


def test_a_hand_edited_classifier_file_is_an_error_not_a_traceback(
    tmp_path, capsys, monkeypatch
):
    """The README tells him to hand-edit this exact file.

    build.build is what reads it, lazily, through the injected lookup, so
    it has to sit inside the CLI's own try -- outside it, a malformed
    cuesheet: section reached the user as a stack trace.
    """
    _knowledge(tmp_path, monkeypatch,
               "channels: {}\nbuses: {}\ncuesheet:\n  - ca sĩ nữ\n")
    code = main([
        "showcontext", "import",
        str(DATA / "ingest-fixture.xlsx"),
        "--map", str(DATA / "ingest-fixture-map.yaml"),
    ])
    assert code == 1
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert "classifier.yaml" in err
    assert "cuesheet" in err


def test_a_syntax_error_in_the_classifier_file_is_an_error_too(
    tmp_path, capsys, monkeypatch
):
    """A typo is the likeliest hand-edit failure, and ruamel's YAMLError
    is not a ValueError, so nothing caught it."""
    _knowledge(tmp_path, monkeypatch,
               "channels: {}\nbuses: {}\ncuesheet: [unbalanced\n")
    code = main([
        "showcontext", "import",
        str(DATA / "ingest-fixture.xlsx"),
        "--map", str(DATA / "ingest-fixture-map.yaml"),
    ])
    assert code == 1
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert "classifier.yaml" in err


def test_vocabulary_problems_are_printed_as_warnings_before_the_summary(
    tmp_path, capsys, monkeypatch
):
    """Vocabulary.load never raises on a hand-edit mistake -- an unknown
    kind, a dangling set -- it reports it through .problems and excludes
    the broken entry instead. That must not vanish silently: showcontext
    import prints each problem as one warning line on stderr, before the
    summary (fix round 1, controller ruling R2)."""
    _knowledge(
        tmp_path, monkeypatch,
        "channels: {}\nbuses: {}\n"
        "cuesheet:\n  bad term:\n    kinds: [nonexistent.kind]\n"
        "    match: exact\n",
    )
    out = tmp_path / "tonight.yaml"
    code = main([
        "showcontext", "import",
        str(DATA / "ingest-fixture.xlsx"),
        "--map", str(DATA / "ingest-fixture-map.yaml"), "-o", str(out),
    ])
    assert code == 0
    err = capsys.readouterr().err
    lines = err.splitlines()
    warning_lines = [i for i, line in enumerate(lines) if line.startswith("warning:")]
    summary_lines = [i for i, line in enumerate(lines) if line.startswith("wrote ")]
    assert warning_lines, err
    assert "bad term" in err and "unknown kind" in err
    assert summary_lines, err
    assert warning_lines[0] < summary_lines[0]


def test_the_vocabulary_is_read_once_not_once_per_performer_fragment(
    tmp_path, monkeypatch
):
    """classifier/resolve.py:31-40 measured this exact hazard: re-reading
    and re-parsing classifier.yaml through a ruamel round-trip on every
    call costs 3.4 s for 50 per-name lookups against 65 ms for one load --
    and the cuesheet domain grows one entry per term ever seen.

    Task 3 wired build.py to `vocabulary.Vocabulary` instead of a raw
    cache dict: the disk read now happens inside `Vocabulary.load()`
    (called once by `showcontext_import`), and every per-fragment call is
    `.effective()` working off the already-parsed, in-memory term list --
    no further disk I/O.

    Counts `cache._read` -- the function that actually touches disk --
    rather than the thinner `cache.read_raw` wrapper (fix round 1,
    controller ruling R4): `cache.load()` also calls `_read()` directly,
    bypassing `read_raw` entirely, so counting only `read_raw` would miss
    a regression that read classifier.yaml through THAT path instead.
    Counting `_read` itself is the only way to catch any real disk read
    on this path, whichever wrapper triggers it -- the original intent
    behind this test's name."""
    from wing_parser.classifier import cache

    reads: list[object] = []
    real_read = cache._read

    def counted(directory=None):
        reads.append(directory)
        return real_read(directory)

    monkeypatch.setattr(cache, "_read", counted)

    out = tmp_path / "tonight.yaml"
    assert main([
        "showcontext", "import",
        str(DATA / "ingest-fixture.xlsx"),
        "--map", str(DATA / "ingest-fixture-map.yaml"), "-o", str(out),
    ]) == 0
    assert len(reads) == 1


def test_a_column_with_a_blank_header_can_be_mapped_by_its_letter(
    tmp_path, capsys
):
    """An unlabelled notes column is common, and headers: cannot name it."""
    from openpyxl import Workbook

    book = Workbook()
    page = book.active
    page.append(["STT", "Tên tiết mục", None])
    page.append(["1", "Đón khách", "chú thích"])
    sheet = tmp_path / "blank-header.xlsx"
    book.save(sheet)

    mapping = tmp_path / "map.yaml"
    mapping.write_text(
        "header_row: 1\ncolumns:\n  title: B\n  note: C\n", encoding="utf-8"
    )
    assert main(["showcontext", "import", str(sheet), "--map", str(mapping)]) == 0
    assert "chú thích" in capsys.readouterr().out


def test_the_map_flow_folds_unmapped_columns_too(tmp_path, capsys):
    """Same pipeline as the wizard: an unmapped technical column must
    become a visible `[header] cell` comment, never dropped silently.
    Mirrors test_ingest_build's fold test at the CLI level."""
    from openpyxl import Workbook

    book = Workbook()
    page = book.active
    page.append(["STT", "Tên tiết mục", "Âm thanh"])
    page.append(["1", "Đón khách", "nhạc nền từ USB"])
    sheet = tmp_path / "unmapped.xlsx"
    book.save(sheet)

    mapping = tmp_path / "map.yaml"
    mapping.write_text(
        "header_row: 1\ncolumns:\n  id: A\n  title: B\n", encoding="utf-8"
    )
    out = tmp_path / "out.yaml"
    assert main([
        "showcontext", "import", str(sheet),
        "--map", str(mapping), "-o", str(out),
    ]) == 0
    text = out.read_text(encoding="utf-8")
    assert "[Âm thanh]" in text and "nhạc nền từ USB" in text


def test_a_letter_past_the_end_of_the_sheet_is_still_refused(tmp_path, capsys):
    from openpyxl import Workbook

    book = Workbook()
    page = book.active
    page.append(["STT", "Tên tiết mục"])
    page.append(["1", "Đón khách"])
    sheet = tmp_path / "narrow.xlsx"
    book.save(sheet)

    mapping = tmp_path / "map.yaml"
    mapping.write_text(
        "header_row: 1\ncolumns:\n  title: B\n  note: Z\n", encoding="utf-8"
    )
    assert main(["showcontext", "import", str(sheet), "--map", str(mapping)]) == 1
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert "Z" in err
