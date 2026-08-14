"""Assemble sources, DCAs and mute groups.

Phantom power, preamp gain and source polarity live on the source, not
the channel. A channel points here via ch.in.conn.{grp,in}.
"""

from __future__ import annotations

from typing import Any

from wing_parser.core.models import DcaData, MuteGroupData, SourceData
from wing_parser.core.normalizer import to_db


def build_sources(io_in: dict[str, Any]) -> dict[tuple[str, int], SourceData]:
    sources: dict[tuple[str, int], SourceData] = {}
    for group, entries in (io_in or {}).items():
        if not isinstance(entries, dict):
            continue
        for key, entry in entries.items():
            try:
                index = int(key)
            except (TypeError, ValueError):
                continue
            sources[(group, index)] = SourceData(
                group=group,
                index=index,
                name=entry.get("name", ""),
                gain_dB=float(entry.get("g", 0.0)),
                phantom=bool(entry.get("vph", False)),
                polarity=bool(entry.get("pol", False)),
                mode=entry.get("mode", "M"),
            )
    return sources


def build_dcas(section: dict[str, Any]) -> dict[int, DcaData]:
    return {
        int(key): DcaData(
            number=int(key),
            name=entry.get("name", ""),
            muted=bool(entry.get("mute", False)),
            fader_dB=to_db(entry.get("fdr")),
        )
        for key, entry in (section or {}).items()
    }


def build_mute_groups(section: dict[str, Any]) -> dict[int, MuteGroupData]:
    return {
        int(key): MuteGroupData(
            number=int(key),
            name=entry.get("name", ""),
            muted=bool(entry.get("mute", False)),
        )
        for key, entry in (section or {}).items()
    }
