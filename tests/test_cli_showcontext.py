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
