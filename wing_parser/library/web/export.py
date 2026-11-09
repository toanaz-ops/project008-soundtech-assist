"""Static export: one self-contained index.html (data, CSS and JS inline)
plus the PNG diagrams under media/<id>/. Read-only; opens from file://."""

from __future__ import annotations

import datetime as dt
import json
import shutil
from importlib import resources
from pathlib import Path

from wing_parser.library import schema
from wing_parser.library.store import LibraryStore
from wing_parser.library.web import render

_CSS_TAG = '<link rel="stylesheet" href="static/app.css">'
_JS_TAG = '<script src="static/app.js"></script>'
_DATA_MARK = "<!--LIBRARY_DATA-->"


def static_text(name: str) -> str:
    return (resources.files("wing_parser.library.web") / "static" / name).read_text(encoding="utf-8")


def script_json(payload: dict) -> str:
    """JSON safe to embed in a <script> element."""
    text = json.dumps(payload, ensure_ascii=False, default=str)
    return (text.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
                .replace("\u2028", "\\u2028").replace("\u2029", "\\u2029"))


def build_page(payload: dict) -> str:
    page = static_text("index.html")
    for needle in (_CSS_TAG, _JS_TAG, _DATA_MARK):
        if needle not in page:
            raise RuntimeError(f"static/index.html lost its marker {needle!r}")
    data = f'<script type="application/json" id="library-data">{script_json(payload)}</script>'
    js = static_text("app.js").replace("</script", "<\\/script")
    return (page.replace(_CSS_TAG, f"<style>\n{static_text('app.css')}\n</style>")
                .replace(_DATA_MARK, data)
                .replace(_JS_TAG, f"<script>\n{js}\n</script>"))


def export_web(store: LibraryStore, out_dir: Path) -> dict:
    """Write the export. Returns entries / media / missing_media / bytes."""
    render.markdown_module()  # fail early with a clear message
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    views, media_count, missing = [], 0, []
    media_out = out / "media"
    if media_out.exists():
        shutil.rmtree(media_out)  # the export owns this folder; avoids stale diagrams
    for loaded in store.entries(include_retired=True):
        view = render.detail(loaded, media_prefix="media/", raw=False)
        for item in view["media"]:
            if item.get("kind") != "diagram":
                continue
            rel = str(item.get("path", ""))
            src = store.media_file(loaded.id, rel) if rel.lower().endswith(".png") else None
            if src is None or not src.is_file():
                item.pop("src", None)
                missing.append(f"{loaded.id}/{rel}")
                continue
            dest = media_out / loaded.id / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, dest)
            media_count += 1
        views.append(view)
    topics = schema.load_topics(store._taxonomy_root())
    payload = {"mode": "export", "topics": render.topic_list(topics),
               "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
               "schema": render.schema_info(), "entries": views}
    page = build_page(payload)
    (out / "index.html").write_text(page, encoding="utf-8", newline="\n")
    size = len(page.encode("utf-8")) + sum(p.stat().st_size for p in media_out.rglob("*") if p.is_file())
    return {"entries": len(views), "media": media_count, "missing_media": missing, "bytes": size}
