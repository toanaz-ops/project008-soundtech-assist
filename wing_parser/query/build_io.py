"""Assemble sources, DCAs and mute groups.

Phantom power, preamp gain and source polarity live on the source, not
the channel. A channel points here via ch.in.conn.{grp,in}.
"""

from __future__ import annotations

from typing import Any

from wing_parser.core.models import DcaData, MuteGroupData, SourceData
from wing_parser.core.normalizer import int_keyed, to_db


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
        number: DcaData(
            number=number,
            name=entry.get("name", ""),
            muted=bool(entry.get("mute", False)),
            fader_dB=to_db(entry.get("fdr")),
        )
        for number, entry in int_keyed(section or {}).items()
    }


def build_mute_groups(section: dict[str, Any]) -> dict[int, MuteGroupData]:
    return {
        number: MuteGroupData(
            number=number,
            name=entry.get("name", ""),
            muted=bool(entry.get("mute", False)),
        )
        for number, entry in int_keyed(section or {}).items()
    }
