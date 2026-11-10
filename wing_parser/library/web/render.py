"""Markdown -> sanitised HTML, and the JSON views the web app consumes.

Raw HTML in a body is never passed through: the Markdown block/inline HTML
handlers are removed (so `<script>` is shown as text) and every link scheme
other than http/https/mailto is neutralised.
"""

from __future__ import annotations

import html
import re

from wing_parser.library import schema
from wing_parser.library.store import LoadedEntry
from wing_parser.showcontext.ingest.keywords import fold

INSTALL_HINT = 'the "markdown" package is missing: pip install "wing-parser[library-web]"'
_SCHEME = re.compile(r"^([a-z][a-z0-9+.-]*):")
_SAFE_SCHEMES = {"http", "https", "mailto"}
MANAGED_KEYS = ("revision", "updated_at", "updated_by")
EDITABLE_KEYS = tuple(k for k in schema.KEY_ORDER if k not in MANAGED_KEYS)


class MissingDependency(RuntimeError):
    """An optional package of the `library-web` extra is not installed."""


def markdown_module():
    try:
        import markdown
    except ImportError as exc:
        raise MissingDependency(INSTALL_HINT) from exc
    return markdown


def render_markdown(text: str) -> str:
    """Body Markdown -> HTML with raw HTML escaped and unsafe links removed."""
    markdown = markdown_module()
    from markdown.treeprocessors import Treeprocessor

    class _Safe(Treeprocessor):
        def run(self, root):
            for node in root.iter("a"):
                href = node.get("href", "")
                flat = re.sub(r"[\x00-\x20]", "", html.unescape(href)).lower()
                match = _SCHEME.match(flat)
                if match and match.group(1) not in _SAFE_SCHEMES:
                    node.set("href", "#")
                elif match:
                    node.set("target", "_blank")
                    node.set("rel", "noopener noreferrer")

    md = markdown.Markdown(extensions=["tables", "fenced_code", "sane_lists"])
    md.preprocessors.deregister("html_block")
    for name in ("html", "image_link", "image_reference", "short_image_ref"):
        md.inlinePatterns.deregister(name)
    md.treeprocessors.register(_Safe(md), "safe_links", 5)
    return md.convert(text or "")


def _codes(loaded: LoadedEntry) -> set[str]:
    return {i.code for i in loaded.issues}


def _publishers(entry: dict) -> list[str]:
    return sorted({str(s.get("publisher", "")) for s in entry.get("sources") or []
                   if isinstance(s, dict) and s.get("publisher")})


def _search_text(entry: dict) -> str:
    tags = entry.get("tags") if isinstance(entry.get("tags"), dict) else {}
    parts = [entry.get("title"), entry.get("title_vi"), entry.get("summary"),
             entry.get("summary_vi"), entry.get("body"), entry.get("body_vi")]
    for values in tags.values():
        parts.extend(values if isinstance(values, list) else [])
    for src in entry.get("sources") or []:
        if isinstance(src, dict):
            parts.extend((src.get("title"), src.get("publisher")))
    return fold(" ".join(str(p) for p in parts if p))


def list_item(loaded: LoadedEntry) -> dict:
    """Light view for the sidebar: no body, plus pre-folded search text."""
    e = loaded.entry
    return {
        "id": loaded.id, "title": e.get("title", ""), "title_vi": e.get("title_vi", ""),
        "topic": e.get("topic", ""), "tags": e.get("tags") or {}, "summary": e.get("summary", ""),
        "summary_vi": e.get("summary_vi", ""),
        "confidence": e.get("confidence", ""), "status": e.get("status", ""),
        "revision": e.get("revision"), "layer": loaded.layer,
        "unsourced": "unsourced" in _codes(loaded),
        "unvetted": "unvetted-source" in _codes(loaded),
        "publishers": _publishers(e),
        "folded_title": fold(f"{e.get('title', '')} {e.get('title_vi', '')}"),
        "folded_text": _search_text(e),
    }


def detail(loaded: LoadedEntry, *, media_prefix: str, raw: bool) -> dict:
    """Full view. `media_prefix` is joined to `<id>/<file>` for diagram sources;
    `raw` adds the Markdown body and rule for the edit form (server mode)."""
    e = loaded.entry
    out = list_item(loaded)
    media = []
    for item in e.get("media") or []:
        if not isinstance(item, dict):
            continue
        item = dict(item)
        if item.get("kind") == "diagram" and item.get("path"):
            item["src"] = f"{media_prefix}{loaded.id}/{item['path']}"
        media.append(item)
    out.update({
        "body_html": render_markdown(str(e.get("body", ""))),
        "body_vi_html": render_markdown(str(e["body_vi"])) if e.get("body_vi") else "",
        "sources": e.get("sources") or [], "media": media,
        "updated_at": e.get("updated_at", ""), "updated_by": e.get("updated_by", ""),
        "issues": [i.__dict__ for i in loaded.issues],
    })
    if raw:
        out["body"] = e.get("body", "")
        out["body_vi"] = e.get("body_vi", "")
        out["rule"] = e.get("rule")
    return out


def topic_list(topics: dict[str, dict]) -> list[dict]:
    return [{"id": t["id"], "en": t.get("en", t["id"]), "vi": t.get("vi", t.get("en", t["id"]))}
            for t in topics.values()]


def schema_info() -> dict:
    return {"confidence": list(schema.CONFIDENCE), "status": list(schema.STATUS),
            "source_kinds": list(schema.SOURCE_KINDS), "media_kinds": list(schema.MEDIA_KINDS),
            "image_licenses": list(schema.IMAGE_LICENSES), "tag_keys": list(schema.TAG_KEYS)}
