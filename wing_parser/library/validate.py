"""Entry validation. Pure functions: no file writes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from wing_parser.library import schema


@dataclass(frozen=True)
class Issue:
    level: str  # "error" | "warning"
    code: str
    field: str
    message: str

    def format(self, entry_id: str = "") -> str:
        return f"{entry_id}: {self.level} {self.code} {self.field}: {self.message}"


def _err(code: str, field: str, msg: str) -> Issue:
    return Issue("error", code, field, msg)


def _blank(value) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _check_tags(tags, issues: list[Issue]) -> None:
    if not isinstance(tags, dict):
        issues.append(_err("bad-tags", "tags", "tags must be a mapping"))
        return
    for key, values in tags.items():
        if key not in schema.TAG_KEYS:
            issues.append(_err("bad-tags", f"tags.{key}", f"unknown tag group {key!r}"))
            continue
        if not isinstance(values, list):
            issues.append(_err("bad-tags", f"tags.{key}", "must be a list"))
            continue
        for value in values:
            if not isinstance(value, str) or not schema.ID_RE.match(value):
                issues.append(_err("bad-tags", f"tags.{key}", f"{value!r} is not kebab-case"))


def _check_source(index: int, src, vetted: set[str], issues: list[Issue]) -> None:
    field = f"sources[{index}]"
    if not isinstance(src, dict):
        issues.append(_err("bad-source", field, "must be a mapping"))
        return
    for key in ("title", "publisher", "kind", "accessed"):
        if _blank(src.get(key)):
            issues.append(_err("bad-source", f"{field}.{key}", f"{key} is required"))
    kind = src.get("kind")
    if not _blank(kind) and kind not in schema.SOURCE_KINDS:
        issues.append(_err("bad-source", f"{field}.kind", f"unknown kind {kind!r}"))
    url = src.get("url")
    if _blank(url):
        if kind != "book":
            issues.append(_err("bad-source", f"{field}.url", "url is required unless kind is book"))
    elif not str(url).startswith(("http://", "https://")):
        issues.append(_err("bad-source", f"{field}.url", "url must be http or https"))
    accessed = src.get("accessed")
    if not _blank(accessed) and not schema.DATE_RE.match(str(accessed)):
        issues.append(_err("bad-source", f"{field}.accessed", "use YYYY-MM-DD"))
    publisher = src.get("publisher")
    if not _blank(publisher) and str(publisher).casefold() not in vetted:
        issues.append(Issue("warning", "unvetted-source", f"{field}.publisher",
                            f"publisher {publisher!r} is not in sources.yaml"))


def _check_media(index: int, item, entry_id: str, media_roots: list[Path],
                 issues: list[Issue]) -> None:
    field = f"media[{index}]"
    if not isinstance(item, dict):
        issues.append(_err("bad-media", field, "must be a mapping"))
        return
    kind = item.get("kind")
    if kind not in schema.MEDIA_KINDS:
        issues.append(_err("bad-media", f"{field}.kind", f"unknown kind {kind!r}"))
        return
    if kind == "diagram":
        for key in ("path", "caption", "license", "attribution", "generated_by"):
            if _blank(item.get(key)):
                issues.append(_err("bad-media", f"{field}.{key}", f"{key} is required"))
        rel = item.get("path")
        if not _blank(rel) and media_roots:
            if not any((root / entry_id / str(rel)).is_file() for root in media_roots):
                issues.append(_err("missing-media-file", f"{field}.path",
                                   f"media/{entry_id}/{rel} does not exist"))
    elif kind == "image":
        for key in ("url", "caption", "license", "attribution"):
            if _blank(item.get(key)):
                issues.append(_err("bad-media", f"{field}.{key}", f"{key} is required"))
        lic = item.get("license")
        if not _blank(lic) and lic not in schema.IMAGE_LICENSES:
            issues.append(_err("bad-media", f"{field}.license", f"unknown licence {lic!r}"))
    else:
        for key in ("url", "title", "channel"):
            if _blank(item.get(key)):
                issues.append(_err("bad-media", f"{field}.{key}", f"{key} is required"))
    url = item.get("url")
    if kind in ("image", "video") and not _blank(url) and \
            not str(url).startswith(("http://", "https://")):
        issues.append(_err("bad-media", f"{field}.url", "url must be http or https"))
    stamp = item.get("timestamp")
    if not _blank(stamp) and not schema.TIMESTAMP_RE.match(str(stamp)):
        issues.append(_err("bad-media", f"{field}.timestamp", "use mm:ss"))


def validate(entry: dict, *, topics: dict, publishers: list[dict],
             media_root: Path | list[Path] | None = None) -> list[Issue]:
    """All problems with `entry`. An empty list (or warnings only) means valid.

    `media_root` may be one directory or several (user layer, shipped layer).
    """
    if media_root is None:
        media_roots: list[Path] = []
    elif isinstance(media_root, (list, tuple)):
        media_roots = [Path(r) for r in media_root]
    else:
        media_roots = [Path(media_root)]
    issues: list[Issue] = []
    for key in schema.REQUIRED:
        value = entry.get(key)
        if key == "tags":
            missing = value is None
        else:
            missing = _blank(value)
        if missing and key != "sources":
            issues.append(_err("missing-field", key, f"{key} is required"))
    entry_id = entry.get("id")
    if not _blank(entry_id) and not schema.ID_RE.match(str(entry_id)):
        issues.append(_err("bad-id", "id", f"{entry_id!r} is not kebab-case"))
    topic = entry.get("topic")
    if not _blank(topic) and topic not in topics:
        issues.append(_err("bad-topic", "topic", f"unknown topic {topic!r}"))
    for key, allowed in (("confidence", schema.CONFIDENCE), ("status", schema.STATUS)):
        value = entry.get(key)
        if not _blank(value) and value not in allowed:
            issues.append(_err("bad-enum", key, f"{value!r} not in {', '.join(allowed)}"))
    revision = entry.get("revision")
    if revision is not None and (not isinstance(revision, int)
                                 or isinstance(revision, bool) or revision < 1):
        issues.append(_err("bad-enum", "revision", "revision must be an integer >= 1"))
    if entry.get("tags") is not None:
        _check_tags(entry["tags"], issues)

    sources = entry.get("sources")
    if isinstance(sources, list) and sources:
        vetted = schema.publisher_names(publishers)
        for index, src in enumerate(sources):
            _check_source(index, src, vetted, issues)
    elif sources and not isinstance(sources, list):
        issues.append(_err("bad-source", "sources", "sources must be a list"))
    else:
        issues.append(_err("unsourced", "sources", "at least one source is required"))

    media = entry.get("media") or []
    if not isinstance(media, list):
        issues.append(_err("bad-media", "media", "media must be a list"))
    else:
        for index, item in enumerate(media):
            _check_media(index, item, str(entry_id), media_roots, issues)
    return issues


def errors(issues: list[Issue]) -> list[Issue]:
    return [i for i in issues if i.level == "error"]
