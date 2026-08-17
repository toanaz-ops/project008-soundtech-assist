from wing_parser.cli.__main__ import main

GOOD = """\
show: Tiec cuoi nam
segments:
  # the band set
  - id: S2
    expects: [instrument.kyes]
    cues:
      - id: SQ 2
        action: open
        channels: [29]
"""


def test_lint_reports_repairs_without_touching_the_file(tmp_path, capsys):
    path = tmp_path / "tonight.yaml"
    path.write_text(GOOD, encoding="utf-8")
    before = path.read_text(encoding="utf-8")
    assert main(["showcontext", "lint", str(path)]) == 0
    assert "instrument.keys" in capsys.readouterr().out
    assert path.read_text(encoding="utf-8") == before


def test_fix_rewrites_the_file_and_keeps_comments(tmp_path, capsys):
    path = tmp_path / "tonight.yaml"
    path.write_text(GOOD, encoding="utf-8")
    assert main(["showcontext", "lint", str(path), "--fix"]) == 0
    after = path.read_text(encoding="utf-8")
    assert "instrument.keys" in after
    assert "instrument.kyes" not in after
    assert "# the band set" in after


def test_lint_exits_one_on_an_unrepairable_file(tmp_path, capsys):
    path = tmp_path / "bad.yaml"
    path.write_text("show: x\nsegments:\n  - id: S1\n    expects: [trombone]\n",
                    encoding="utf-8")
    assert main(["showcontext", "lint", str(path)]) == 1
    assert "trombone" in capsys.readouterr().err
