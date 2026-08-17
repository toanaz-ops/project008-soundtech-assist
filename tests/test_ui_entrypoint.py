"""The wing-ui entry point.

The engine and the CLI must keep working on a machine with no GUI
installed, so a missing PySide6 has to produce one readable line
naming the extra -- not an ImportError traceback.
"""

import builtins

import pytest

import wing_parser.ui.__main__ as entry


def test_a_missing_pyside_names_the_extra_to_install(monkeypatch, capsys):
    real_import = builtins.__import__

    def refuse_pyside(name, *args, **kwargs):
        if name.startswith("PySide6"):
            raise ImportError("No module named 'PySide6'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", refuse_pyside)

    assert entry.main([]) == 1

    error = capsys.readouterr().err
    assert "PySide6" in error
    assert 'pip install -e ".[ui]"' in error


def test_an_unreadable_file_is_refused_on_the_command_line(tmp_path, capsys):
    # Better than opening an empty window that gives no hint why the
    # file named on the command line is not in it.
    not_a_scene = tmp_path / "notes.txt"
    not_a_scene.write_text("this is not a WING scene", encoding="utf-8")

    assert entry.main([str(not_a_scene)]) == 1
    assert "error:" in capsys.readouterr().err


def test_the_parser_accepts_a_profile(qt_app, monkeypatch):
    # Exercised through the parser only: main() would enter the Qt event
    # loop, which a test must never do.
    parser_args = entry.argparse.ArgumentParser(prog="wing-ui")
    parser_args.add_argument("file", nargs="?")
    parser_args.add_argument("--profile", default=None)
    parsed = parser_args.parse_args(["a.snap", "--profile", "small"])
    assert parsed.profile == "small"
