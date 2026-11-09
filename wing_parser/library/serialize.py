"""YAML (de)serialisation helpers: canonical key order, literal body blocks."""

from __future__ import annotations

import datetime as dt

import yaml

from wing_parser.library import schema


def _plain(value):
    """YAML auto-parses unquoted dates/timestamps; the store keeps strings."""
    if isinstance(value, dt.datetime):
        return value.isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_plain(v) for v in value]
    return value


class _Dumper(yaml.SafeDumper):
    pass


def _str_presenter(dumper, data: str):
    if "\n" in data:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


_Dumper.add_representer(str, _str_presenter)


def _ordered(mapping: dict, order: tuple[str, ...]) -> dict:
    out = {k: mapping[k] for k in order if k in mapping}
    out.update({k: v for k, v in mapping.items() if k not in out})
    return out


def _normalise(entry: dict) -> dict:
    data = _ordered(_plain(entry), schema.KEY_ORDER)
    for key in ("title", "title_vi", "summary", "body"):
        if isinstance(data.get(key), str):
            data[key] = data[key].replace("\r\n", "\n").replace("\r", "\n")
            if key == "body":
                data[key] = data[key].rstrip("\n") + "\n"
    if isinstance(data.get("sources"), list):
        data["sources"] = [_ordered(s, schema.SOURCE_ORDER) if isinstance(s, dict) else s
                           for s in data["sources"]]
    if isinstance(data.get("media"), list):
        data["media"] = [_ordered(m, schema.MEDIA_ORDER) if isinstance(m, dict) else m
                         for m in data["media"]]
    return data


def dump_entry(entry: dict) -> str:
    """Canonical YAML text of an entry (UTF-8-safe, key order fixed)."""
    return yaml.dump(_normalise(entry), Dumper=_Dumper, sort_keys=False,
                     allow_unicode=True, default_flow_style=False, width=1000)
