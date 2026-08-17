# tests/test_cli_showcontext.py
import json

import yaml

from wing_parser.cli.__main__ import main


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
