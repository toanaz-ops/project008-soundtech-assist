"""Static export: one self-contained index.html (data, CSS and JS inline)
plus the PNG diagrams under media/<id>/. Read-only; opens from file://.

Artifact mode (`artifact=True`) writes ONE page fragment, library.html: no
<html>/<head>/<body>, PNGs inlined as data: URIs (the host wraps the page).
"""

from __future__ import annotations

import base64
import datetime as dt
import json
import re
import shutil
from importlib import resources
from pathlib import Path

from wing_parser.library import schema
from wing_parser.library.store import LibraryStore
from wing_parser.library.validate import unsafe_media_path
from wing_parser.library.web import render

_CSS_TAG = '<link rel="stylesheet" href="static/app.css">'
_JS_TAG = '<script src="static/app.js"></script>'
_DATA_MARK = "<!--LIBRARY_DATA-->"
_BODY = re.compile(r"<body[^>]*>(.*)</body>", re.S)
_BOOTSTRAP = re.compile(r'<script id="prefs-bootstrap">.*?</script>', re.S)
ARTIFACT_LIMIT = 16 * 1024 * 1024


def static_text(name: str) -> str:
    return (resources.files("wing_parser.library.web") / "static" / name).read_text(encoding="utf-8")


def static_bytes(name: str) -> bytes:
    return (resources.files("wing_parser.library.web") / "static" / name).read_bytes()


_FONT_URL = re.compile(r"url\(fonts/([\w.-]+\.woff2)\)")


def _font_names() -> list[str]:
    return sorted(set(_FONT_URL.findall(static_text("app.css"))))


def _css(inline_fonts: bool) -> str:
    """app.css for embedding: font files become data: URIs (artifact, ~106 KB) or static/fonts/ paths (full export)."""
    css = static_text("app.css")
    if inline_fonts:
        return _FONT_URL.sub(lambda m: "url(data:font/woff2;base64,"
                             + base64.b64encode(static_bytes("fonts/" + m.group(1))).decode("ascii") + ")", css)
    return _FONT_URL.sub(lambda m: f"url(static/fonts/{m.group(1)})", css)


def script_json(payload: dict) -> str:
    """JSON safe to embed in a <script> element."""
    text = json.dumps(payload, ensure_ascii=False, default=str)
    return (text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
                .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def _fill(page: str, payload: dict, inline_fonts: bool = False) -> str:
    for needle in (_CSS_TAG, _JS_TAG, _DATA_MARK):
        if needle not in page:
            raise RuntimeError(f"static/index.html lost its marker {needle!r}")
    data = f'<script type="application/json" id="library-data">{script_json(payload)}</script>'
    js = static_text("app.js").replace("</script", "<\\/script")
    css = f"<style>\n{_css(inline_fonts)}\n</style>"
    return (page.replace(_CSS_TAG, css)
                .replace(_DATA_MARK, data)
                .replace(_JS_TAG, f"<script>\n{js}\n</script>"))


def build_page(payload: dict) -> str:
    return _fill(static_text("index.html"), payload)


def build_fragment(payload: dict) -> str:
    """Page fragment for the artifact host: title, viewport meta, style, content, scripts."""
    match = _BODY.search(static_text("index.html"))
    if match is None:
        raise RuntimeError("static/index.html has no <body>")
    boot = _BOOTSTRAP.search(static_text("index.html"))
    if boot is None:
        raise RuntimeError("static/index.html lost its prefs-bootstrap script")
    # The fragment has no <head>: the bootstrap goes first so it still runs before the app markup paints.
    inner = _fill(boot.group(0) + "\n" + _CSS_TAG + "\n" + match.group(1).strip(), payload, inline_fonts=True)
    return ('<title>Thư viện Mix</title>\n'
            '<meta name="claude:viewport-fit-sides" content="cover">\n' + inner + "\n")


def _inline_png(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def export_web(store: LibraryStore, out_dir: Path, *, artifact: bool = False) -> dict:
    """Write the export. Returns entries / media / missing_media / bytes / path."""
    render.markdown_module()  # fail early with a clear message
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    views, media_count, missing = [], 0, []
    media_out = out / "media"
    if not artifact and media_out.exists():
        shutil.rmtree(media_out)  # the export owns this folder; avoids stale diagrams
    for loaded in store.entries(include_retired=True):
        view = render.detail(loaded, media_prefix="media/", raw=False)
        for item in view["media"]:
            if item.get("kind") != "diagram":
                continue
            rel = str(item.get("path", ""))
            src = None
            if rel.lower().endswith(".png") and not unsafe_media_path(rel):
                try:
                    src = store.media_file(loaded.id, rel)
                except (ValueError, OSError):
                    src = None
            if src is None or not src.is_file():
                item.pop("src", None)
                missing.append(f"{loaded.id}/{rel}")
                continue
            if artifact:
                item["src"] = _inline_png(src)
            else:
                dest = media_out / loaded.id / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dest)
            media_count += 1
        views.append(view)
    topics = schema.load_topics(store.taxonomy_root)
    payload = {"mode": "export", "topics": render.topic_list(topics),
               "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
               "schema": render.schema_info(), "entries": views}
    if artifact:
        page = build_fragment(payload)
        size = len(page.encode("utf-8"))
        if size >= ARTIFACT_LIMIT:
            raise RuntimeError(f"artifact is {size} bytes, over the 16 MB limit")
        target = out / "library.html"
    else:
        page = build_page(payload)
        target = out / "index.html"
        fonts_out = out / "static" / "fonts"
        fonts_out.mkdir(parents=True, exist_ok=True)
        for name in _font_names():
            (fonts_out / name).write_bytes(static_bytes("fonts/" + name))
        size = len(page.encode("utf-8")) + sum(p.stat().st_size for d in (media_out, fonts_out) for p in d.rglob("*") if p.is_file())
    target.write_text(page, encoding="utf-8", newline="\n")
    return {"entries": len(views), "media": media_count, "missing_media": missing, "bytes": size, "path": target}
