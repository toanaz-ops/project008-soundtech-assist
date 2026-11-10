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


def test_artifact_export_is_a_single_fragment(store, tmp_path, monkeypatch, capsys):
    video = {"kind": "video", "url": "https://youtu.be/abc123XYZ_-", "title": "Talk", "channel": "Ch", "timestamp": "1:05"}
    store.save(entry("with-video", media=[video]), author="t", note="n")
    out = tmp_path / "art"
    result = export_web(store, out, artifact=True)
    page = (out / "library.html").read_text(encoding="utf-8")
    assert [p.name for p in out.iterdir()] == ["library.html"]
    assert result["path"] == out / "library.html" and result["media"] == 1
    assert page.startswith("<title>Thư viện Mix</title>\n<meta name=\"claude:viewport-fit-sides\" content=\"cover\">")
    assert not re.search(r"<(html|head|body)[\s>]", page) and "<!doctype" not in page.lower()
    assert "youtube.com/watch?v=" in page  # video link cards, no embeds
    assert "data:image/png;base64," in page and "media/with-diagram/curve.png" not in page
    assert '"#" + kind + "-"' in page and "<iframe" not in page
    assert "#/e/" in page  # legacy form stays readable
    assert "<style>" in page and "<script>" in page


def test_artifact_cli_flag(store, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(library_commands, "_store", lambda: store)
    args = type("A", (), {"out_dir": str(tmp_path / "c"), "artifact": True})()
    assert library_commands.export_web(args) == 0
    assert (tmp_path / "c" / "library.html").is_file() and not (tmp_path / "c" / "index.html").exists()
    assert "library.html" in capsys.readouterr().out


def test_shell_keeps_full_document_for_server_mode():
    from wing_parser.library.web.export import static_text
    shell = static_text("index.html")
    assert "<!doctype html>" in shell.lower() and "<body>" in shell
    css = static_text("app.css")
    assert "100vh" not in css
    assert "prefers-color-scheme" not in css and "data-theme" not in css
    for skin in ("dark", "sodium", "tet"):
        assert f':root[data-skin="{skin}"]' in css
    # before-paint bootstrap shares PRJ012's storage keys and defaults to light
    head = shell.split("</head>")[0]
    assert 'id="prefs-bootstrap"' in head and "az.prefs.v1" in head and "az.language" in head and "data-skin" in head
    assert "prefers-color-scheme" not in shell and "data-theme" not in shell and 'name="color-scheme"' not in shell
    assert 's="light",n="compact",f="condensed",l="vi"' in head and 'p.font==="default"' in head and 'data-font' in head
    assert ':root[data-font="default"]' in css
    # original look: system condensed face first, self-hosted OFL fallback last, no per-skin type indirection
    assert '"Bahnschrift", "DIN Condensed", "Arial Narrow", "Saira Condensed"' in css
    assert "--head-track" not in css and "--head-case" not in css


def test_shell_has_the_original_header_controls():
    from wing_parser.library.web.export import static_text
    shell = static_text("index.html")
    for ident in ("menu-btn", "new-btn", "lang-btn", "display-btn"):
        assert f'id="{ident}"' in shell
    assert 'class="brand"' in shell


def test_artifact_inlines_fonts_and_full_export_ships_them(store, tmp_path):
    frag = export_web(store, tmp_path / "frag", artifact=True)["path"].read_text(encoding="utf-8")
    assert "data:font/woff2;base64," in frag and "url(fonts/" not in frag
    res = export_web(store, tmp_path / "full")
    page = res["path"].read_text(encoding="utf-8")
    fonts = list((tmp_path / "full" / "static" / "fonts").glob("*.woff2"))
    assert len(fonts) == 6 and "url(static/fonts/" in page and "data:font" not in page


def test_exports_keep_the_prefs_bootstrap(store, tmp_path):
    full = export_web(store, tmp_path / "full")["path"].read_text(encoding="utf-8")
    frag = export_web(store, tmp_path / "frag", artifact=True)["path"].read_text(encoding="utf-8")
    for page in (full, frag):
        assert "az.prefs.v1" in page and "az.language" in page and "data-skin" in page
        assert 'id="display-btn"' in page and "prefers-color-scheme" not in page
    # in the fragment the bootstrap precedes all app markup so it still runs before first paint
    assert frag.index("az.prefs.v1") < frag.index('id="app"')


def test_one_bad_media_path_does_not_stop_the_export(store, tmp_path):
    from wing_parser.library.web.export import export_web
    path = store.root / "entries" / "with-diagram.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("curve.png", "../../x.png"), encoding="utf-8")
    result = export_web(store, tmp_path / "out")
    assert any("x.png" in m for m in result["missing_media"])
    assert (tmp_path / "out" / "index.html").is_file()


def test_vietnamese_fields_reach_the_export_and_artifact(store, tmp_path):
    media = [{"kind": "video", "url": "https://youtu.be/abc123XYZ_-", "title": "T", "channel": "C",
              "caption": "Cap", "caption_vi": "Chú thích"}]
    store.save(entry("vi-entry", summary_vi="Tóm tắt VI", body_vi="Nội dung **đậm**\n", media=media),
               author="t", note="n")
    for artifact, name in ((False, "index.html"), (True, "library.html")):
        out = tmp_path / ("a" if artifact else "e")
        export_web(store, out, artifact=artifact)
        view = next(e for e in _data((out / name).read_text(encoding="utf-8"))["entries"]
                    if e["id"] == "vi-entry")
        assert view["summary_vi"] == "Tóm tắt VI"
        assert "<strong>đậm</strong>" in view["body_vi_html"]
        assert view["media"][0]["caption_vi"] == "Chú thích"
        assert "body_vi" not in view and "Tóm tắt VI" in (out / name).read_text(encoding="utf-8")
    plain = next(e for e in _data((tmp_path / "e" / "index.html").read_text(encoding="utf-8"))["entries"]
                 if e["id"] == "hpf-basics")
    assert plain["body_vi_html"] == "" and plain["summary_vi"] == ""
    loaded = store.get("vi-entry")
    assert render.detail(loaded, media_prefix="m/", raw=True)["body_vi"].startswith("Nội dung")
    assert "noi dung dam" in render._search_text(loaded.entry)
    page = (tmp_path / "e" / "index.html").read_text(encoding="utf-8")
    assert "summary_vi" in page and "caption_vi" in page and "noVi" in page
