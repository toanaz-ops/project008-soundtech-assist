"""Wizard decisions are Enter-to-accept; --one-shot writes and stops."""
from pathlib import Path

from wing_parser.classifier.provider import ProviderError
from wing_parser.cli.__main__ import main
from wing_parser.showcontext.ingest.wizard import run_wizard

DATA = Path(__file__).resolve().parent / "data"
VIVO = str(DATA / "05102022_vivo_ Event Rundown.xlsx")
MAP_NAME = "05102022_vivo_ Event Rundown.map.yaml"


class VivoProvider:
    """The proposal Task 9's suite already proved clean end-to-end."""

    def complete_json(self, system, user, schema):
        return {
            "sheet": "Rundown",
            "header_row": 4,
            "columns": '{"id": "B", "time": "C", "title": "F"}',
            "headers": '{"performers": "On stage", "note": "CHUẨN BỊ"}',
        }


class DeadProvider:
    def complete_json(self, system, user, schema):
        raise ProviderError("key missing")


def _fake_provider(monkeypatch, provider):
    """The wizard builds its own provider offline; swap the factory."""
    monkeypatch.setattr(
        "wing_parser.classifier.provider.make_provider", lambda config: provider
    )
    monkeypatch.delenv("WING_PROVIDER_CONFIG", raising=False)


def test_all_enter_accepts_proposal_and_imports(tmp_path, capsys, monkeypatch):
    _fake_provider(monkeypatch, VivoProvider())
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "vivo.yaml"
    code = run_wizard(
        VIVO,
        input_fn=lambda *a, **k: "",
        print_fn=lambda *a, **k: None,
        output=str(out),
        force=False,
        scene=None,
        one_shot=False,
    )
    assert code == 0
    assert out.exists()
    assert "segments:" in out.read_text(encoding="utf-8")
    assert (tmp_path / MAP_NAME).exists()

    from wing_parser.showcontext import load_show_context

    context = load_show_context(out)
    assert len(context.segments) > 0


def test_one_shot_writes_only_the_map(tmp_path, capsys, monkeypatch):
    _fake_provider(monkeypatch, VivoProvider())
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "vivo.yaml"
    code = run_wizard(
        VIVO,
        input_fn=lambda *a, **k: "",
        print_fn=lambda *a, **k: print(*a),
        output=str(out),
        force=False,
        scene=None,
        one_shot=True,
    )
    assert code == 0
    maps = list(tmp_path.glob("*.map.yaml"))
    assert len(maps) == 1
    assert maps[0].name == MAP_NAME
    assert not out.exists()
    assert ".map.yaml" in capsys.readouterr().out


def test_provider_failure_prints_one_line_and_walks_manual_questions(
    tmp_path, capsys, monkeypatch
):
    _fake_provider(monkeypatch, DeadProvider())
    monkeypatch.chdir(tmp_path)
    answers = iter([
        "Rundown",       # sheet, typed by hand -- nothing to accept
        "4",             # header row
        "B", "C", "F",   # id, time, title by letter
        "On stage",      # performers by header text
        "CHUẨN BỊ",      # note
        "", "", "", "",  # sound, lighting, led left unmapped
    ])
    out = tmp_path / "vivo.yaml"
    code = run_wizard(
        VIVO,
        input_fn=lambda *a, **k: next(answers),
        print_fn=lambda *a, **k: print(*a),
        output=str(out),
        force=False,
        scene=None,
        one_shot=False,
    )
    assert code == 0
    lines = [
        line
        for line in capsys.readouterr().out.splitlines()
        if "no model assist" in line
    ]
    assert len(lines) == 1
    assert out.exists()
    assert "segments:" in out.read_text(encoding="utf-8")


def test_cli_one_shot_flag_reaches_the_wizard(tmp_path, capsys, monkeypatch):
    """Wiring check: the flag travels into run_wizard. The wizard body
    itself (Enter-to-accept, one map file) is proven directly above --
    driving it through main() would read stdin under capsys."""
    seen = {}

    def fake_wizard(xlsx, **kwargs):
        seen.update(kwargs, xlsx=xlsx)
        return 0

    monkeypatch.setattr(
        "wing_parser.showcontext.ingest.wizard.run_wizard", fake_wizard
    )
    code = main(["showcontext", "import", VIVO, "--one-shot"])
    assert code == 0
    assert seen["xlsx"] == VIVO
    assert seen["one_shot"] is True


def test_no_assist_without_a_mapping_is_refused(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("WING_PROVIDER_CONFIG", raising=False)
    code = main(["showcontext", "import", VIVO, "--no-assist"])
    assert code != 0
    assert "--no-assist" in capsys.readouterr().err


def test_wizard_refuses_to_overwrite_output_without_force(tmp_path, monkeypatch):
    _fake_provider(monkeypatch, VivoProvider())
    monkeypatch.chdir(tmp_path)
    out = tmp_path / "vivo.yaml"
    out.write_text("keep me\n", encoding="utf-8")
    asked = []
    code = run_wizard(
        VIVO,
        input_fn=lambda prompt: (asked.append(prompt), "")[1],
        print_fn=lambda *a, **k: None,
        output=str(out),
        force=False,
        scene=None,
        one_shot=False,
    )
    assert code == 1
    assert out.read_text(encoding="utf-8") == "keep me\n"
    assert not asked  # refused before a single question was asked
