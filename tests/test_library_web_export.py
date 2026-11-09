"""Static export: embedded data, copied PNGs, escaped raw HTML, CLI messages."""

import json
import re

import pytest

pytest.importorskip("markdown")

from tests.library_support import entry, make_root  # noqa: E402
from wing_parser.cli import library_commands  # noqa: E402
from wing_parser.library import LibraryStore  # noqa: E402
from wing_parser.library.web import render  # noqa: E402
from wing_parser.library.web.export import export_web  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 16
DATA_RE = re.compile(r'<script type="application/json" id="library-data">(.*?)</script>', re.S)


@pytest.fixture
def store(tmp_path):
    root = make_root(tmp_path / "lib")
    s = LibraryStore(root)
    s.save(entry("hpf-basics", body="Plain **bold** text.\n"), author="t", note="n")
    diagram = {"kind": "diagram", "path": "curve.png", "caption": "Curve", "license": "CC0-1.0",
               "attribution": "Generated for wing-parser", "generated_by": "scripts/library_diagrams.py:x"}
    folder = root / "media" / "with-diagram"
    folder.mkdir(parents=True)
    (folder / "curve.png").write_bytes(PNG)
    (folder / "curve.svg").write_text("<svg/>", encoding="utf-8")
    s.save(entry("with-diagram", media=[diagram]), author="t", note="n")
    return s


def _data(page: str) -> dict:
    return json.loads(DATA_RE.search(page).group(1))


def test_export_embeds_data_and_copies_png(store, tmp_path):
    out = tmp_path / "out"
    result = export_web(store, out)
    page = (out / "index.html").read_text(encoding="utf-8")
    data = _data(page)
    assert data["mode"] == "export" and {e["id"] for e in data["entries"]} == {"hpf-basics", "with-diagram"}
    assert result["entries"] == 2 and result["media"] == 1
    assert (out / "media" / "with-diagram" / "curve.png").read_bytes() == PNG
    assert not list(out.rglob("*.svg"))
    diagram = next(e for e in data["entries"] if e["id"] == "with-diagram")["media"][0]
    assert diagram["src"] == "media/with-diagram/curve.png"
    # self-contained: the shell files are inlined, nothing is fetched
    assert 'src="static/app.js"' not in page and 'href="static/app.css"' not in page
    assert "<style>" in page


def test_export_leaves_raw_fields_out(store, tmp_path):
    export_web(store, tmp_path / "o")
    data = _data((tmp_path / "o" / "index.html").read_text(encoding="utf-8"))
    assert all("body" not in e and "rule" not in e for e in data["entries"])  # server-only


def test_markdown_raw_html_is_escaped():
    out = render.render_markdown(
        "<script>alert(1)</script>\n\n<img src=x onerror=alert(1)>\n\n"
        "[a](javascript:alert(1)) [b](JaVa&#115;cript:alert(2)) [ok](https://example.org)\n\n"
        "![i](http://x/y.png)")
    assert "<script" not in out and "<img" not in out
    assert "&lt;script&gt;" in out
    assert 'href="javascript' not in out.lower() and 'href="#"' in out
    assert 'href="https://example.org"' in out and 'rel="noopener noreferrer"' in out


def test_script_json_cannot_close_the_script_tag(store, tmp_path):
    store.save(entry("evil", title="</script><b>x"), author="t", note="n")
    export_web(store, tmp_path / "o")
    page = (tmp_path / "o" / "index.html").read_text(encoding="utf-8")
    assert "</script><b>" not in page
    assert any(e["title"] == "</script><b>x" for e in _data(page)["entries"])


def test_missing_markdown_is_a_clear_error_not_a_traceback(store, tmp_path, monkeypatch, capsys):
    def boom():
        raise render.MissingDependency(render.INSTALL_HINT)

    monkeypatch.setattr(render, "markdown_module", boom)
    monkeypatch.setattr(library_commands, "_store", lambda: store)
    args = type("A", (), {"out_dir": str(tmp_path / "o")})()
    assert library_commands.export_web(args) == 1
    assert "library-web" in capsys.readouterr().err


def test_cli_export_web_writes_index(store, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(library_commands, "_store", lambda: store)
    args = type("A", (), {"out_dir": str(tmp_path / "cli")})()
    assert library_commands.export_web(args) == 0
    assert (tmp_path / "cli" / "index.html").is_file()
    assert "exported 2 entries" in capsys.readouterr().out
