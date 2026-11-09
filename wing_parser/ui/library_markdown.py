"""An entry as Markdown, for the entry view (no widgets).

Own words and structure only: the title, the summary, the body, the media
and a numbered Sources list. Badges are not Markdown -- they are labels in
the view, so they can carry theme colours.
"""

from __future__ import annotations

from PySide6.QtCore import QUrl

from wing_parser.library.store import LibraryStore, LoadedEntry
from wing_parser.ui.library_support import topic_label
from wing_parser.ui.texts import text


def _esc(value) -> str:
    """Keep a title from opening a link or an emphasis by accident."""
    out = str(value)
    for char in ("\\", "[", "]", "*", "_", "`"):
        out = out.replace(char, "\\" + char)
    return out


def _link(label: str, url: str) -> str:
    return f"[{_esc(label)}](<{url}>)"


def _tag_line(entry: dict) -> str:
    tags = entry.get("tags") or {}
    parts = []
    for group in ("instrument", "genre", "technique", "event"):
        values = tags.get(group) or []
        if values:
            parts.append(f"{group}: {', '.join(str(v) for v in values)}")
    return " | ".join(parts)


def _media_lines(loaded: LoadedEntry, store: LibraryStore) -> list[str]:
    entry, lines = loaded.entry, []
    for item in entry.get("media") or []:
        if not isinstance(item, dict):
            continue
        kind, caption = item.get("kind"), str(item.get("caption", "") or "")
        credit = " - ".join(
            f"{text('library.view.' + key)}: {item[key]}"
            for key in ("license", "attribution") if item.get(key))
        if kind == "diagram":
            try:
                path = store.media_file(loaded.id, str(item.get("path", "")))
            except ValueError:
                path = None
            if path is not None and path.is_file():
                url = QUrl.fromLocalFile(str(path)).toString(QUrl.ComponentFormattingOption.FullyEncoded)
                lines.append(f"![{_esc(caption)}](<{url}>)")
            else:
                lines.append(f"*{_esc(caption)} {text('library.view.missing_file')}*")
        elif kind == "video":
            label = " · ".join(str(item[k]) for k in ("title", "channel", "timestamp") if item.get(k))
            lines.append(_link(label or str(item.get("url", "")), str(item.get("url", ""))))
        else:
            lines.append(_link(caption or str(item.get("url", "")), str(item.get("url", ""))))
        lines.append("")
        if kind != "video" and caption:
            lines += [f"*{_esc(caption)}*", ""]
        if credit:
            lines += [f"*{_esc(credit)}*", ""]
    return lines


def _source_lines(entry: dict) -> list[str]:
    sources = [s for s in entry.get("sources") or [] if isinstance(s, dict)]
    if not sources:
        return [f"*{text('library.view.no_sources')}*"]
    lines = []
    for number, src in enumerate(sources, start=1):
        meta = ", ".join(str(src[k]) for k in ("publisher", "author", "year", "locator") if src.get(k))
        if src.get("accessed"):
            meta += f" ({text('library.view.accessed')} {src['accessed']})"
        line = f"{number}. **{_esc(src.get('title', ''))}** - {_esc(meta)}"
        if src.get("url"):
            line += f" - {_link(str(src['url']), str(src['url']))}"
        lines.append(line)
    return lines


def entry_markdown(loaded: LoadedEntry, store: LibraryStore, topics: dict) -> str:
    entry = loaded.entry
    out = [f"# {_esc(entry.get('title', loaded.id))}"]
    if entry.get("title_vi"):
        out += ["", f"*{_esc(entry['title_vi'])}*"]
    meta = [f"{text('library.view.topic')}: {_esc(topic_label(topics, entry.get('topic', '')))}"]
    if _tag_line(entry):
        meta.append(_esc(_tag_line(entry)))
    meta.append(text("library.view.revision").format(
        rev=entry.get("revision", "?"), when=entry.get("updated_at", ""),
        who=_esc(entry.get("updated_by", ""))))
    out += ["", "  \n".join(meta), "", str(entry.get("summary", "") or "").strip(), "",
            str(entry.get("body", "") or "").strip(), ""]
    media = _media_lines(loaded, store)
    if media:
        out += [f"## {text('library.view.media')}", "", *media]
    out += [f"## {text('library.view.sources')}", "", *_source_lines(entry)]
    return "\n".join(out)
