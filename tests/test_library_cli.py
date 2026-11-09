"""`wing library ...`: exit codes and output."""

import json

import pytest
import yaml

from tests.library_support import SOURCE, entry, make_root
from wing_parser.cli.__main__ import main


@pytest.fixture
def lib(tmp_path, monkeypatch):
    root = make_root(tmp_path / "lib")
    monkeypatch.setenv("WING_LIBRARY_DIR", str(root))
    monkeypatch.setattr("wing_parser.config.shipped_library_dir", lambda: root)
    return root


def entry_file(tmp_path, data, name="e.yaml"):
    path = tmp_path / name
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return str(path)


def test_add_list_show_search_history(lib, tmp_path, capsys):
    path = entry_file(tmp_path, entry())
    assert main(["library", "add", path, "--author", "agent:test", "--note", "first"]) == 0
    assert main(["library", "list"]) == 0
    assert "hpf-basics" in capsys.readouterr().out
    assert main(["library", "search", "loc thong"]) == 0
    assert "hpf-basics" in capsys.readouterr().out
    assert main(["library", "history", "hpf-basics"]) == 0
    assert "agent:test" in capsys.readouterr().out


def test_show_json_is_valid_json(lib, tmp_path, capsys):
    main(["library", "add", entry_file(tmp_path, entry()), "--author", "a"])
    capsys.readouterr()
    assert main(["library", "show", "hpf-basics", "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["id"] == "hpf-basics" and data["revision"] == 1 and data["layer"] == "user"


def test_show_unknown_id_fails(lib):
    assert main(["library", "show", "nope"]) == 1


def test_add_unsourced_exits_1_and_writes_nothing(lib, tmp_path, capsys):
    path = entry_file(tmp_path, entry(sources=[]))
    assert main(["library", "add", path, "--author", "a"]) == 1
    assert "unsourced" in capsys.readouterr().err
    assert not (lib / "entries" / "hpf-basics.yaml").exists()


def test_add_existing_id_fails(lib, tmp_path):
    path = entry_file(tmp_path, entry())
    assert main(["library", "add", path, "--author", "a"]) == 0
    assert main(["library", "add", path, "--author", "a"]) == 1


def test_edit_requires_note_and_checks_revision(lib, tmp_path):
    path = entry_file(tmp_path, entry())
    main(["library", "add", path, "--author", "a"])
    edited = entry_file(tmp_path, entry(summary="New."), "edit.yaml")
    assert main(["library", "edit", "hpf-basics", edited, "--author", "a"]) == 1  # no note
    assert main(["library", "edit", "hpf-basics", edited, "--author", "a", "--note", "n"]) == 0
    stale = entry_file(tmp_path, entry(summary="Stale.", revision=1), "stale.yaml")
    assert main(["library", "edit", "hpf-basics", stale, "--author", "a", "--note", "n"]) == 1


def test_history_diff(lib, tmp_path, capsys):
    main(["library", "add", entry_file(tmp_path, entry()), "--author", "a"])
    main(["library", "edit", "hpf-basics", entry_file(tmp_path, entry(summary="New."), "b.yaml"),
          "--author", "a", "--note", "n"])
    capsys.readouterr()
    assert main(["library", "history", "hpf-basics", "--diff", "2"]) == 0
    assert "+summary: New." in capsys.readouterr().out
    assert main(["library", "history", "hpf-basics", "--diff", "1"]) == 1


def test_validate_exit_codes(lib, tmp_path, capsys):
    assert main(["library", "validate"]) == 0
    main(["library", "add", entry_file(tmp_path, entry(sources=[dict(SOURCE, publisher="Blog")])),
          "--author", "a"])
    capsys.readouterr()
    assert main(["library", "validate"]) == 0  # warning only
    assert main(["library", "validate", "--strict"]) == 1
    assert "hpf-basics: warning unvetted-source sources[0].publisher:" in capsys.readouterr().out
    bad = lib / "entries" / "bad.yaml"
    bad.write_text(yaml.safe_dump({**entry("bad", sources=[]), "revision": 1,
                                   "updated_at": "2026-11-09T10:00:00+07:00",
                                   "updated_by": "x"}), encoding="utf-8")
    assert main(["library", "validate"]) == 1
    assert "bad: error unsourced sources:" in capsys.readouterr().out
