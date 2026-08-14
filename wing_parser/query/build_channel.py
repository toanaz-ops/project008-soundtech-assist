"""Assemble a ChannelData record from one raw ch entry."""

from __future__ import annotations

from typing import Any

from wing_parser.core.models import (
    Anomaly,
    ChannelData,
    Filter,
    Gate,
    Insert,
    SourceRef,
)
from wing_parser.core.normalizer import to_db
from wing_parser.descriptors import eq_models, proc_chain
from wing_parser.query.build_blocks import (
    build_dyn,
    build_main_sends,
    build_sends,
)

AUTOMIX_PREFIX = "AUTO_"


def _filter(raw: dict[str, Any]) -> Filter:
    return Filter(
        low_cut_on=bool(raw.get("lc", False)),
        low_cut_hz=float(raw.get("lcf", 0.0)),
        low_cut_slope=int(raw.get("lcs", 12)),
        high_cut_on=bool(raw.get("hc", False)),
        high_cut_hz=float(raw.get("hcf", 0.0)),
        high_cut_slope=int(raw.get("hcs", 12)),
    )


def _gate(raw: dict[str, Any]) -> Gate:
    return Gate(
        on=bool(raw.get("on", False)),
        model=raw.get("mdl", "UNKNOWN"),
        threshold_dB=float(raw.get("thr", 0.0)),
        range_dB=float(raw.get("range", 0.0)),
        attack_ms=float(raw.get("att", 0.0)),
        hold_ms=float(raw.get("hld", 0.0)),
        release_ms=float(raw.get("rel", 0.0)),
    )


def _insert(raw: dict[str, Any] | None) -> Insert:
    """preins carries {on, ins}; postins adds {mode, w} for automix."""
    raw = raw or {}
    mode = raw.get("mode")
    group = mode[len(AUTOMIX_PREFIX):] if isinstance(mode, str) and mode.startswith(AUTOMIX_PREFIX) else None
    weight = float(raw["w"]) if group is not None and "w" in raw else None
    return Insert(
        on=bool(raw.get("on", False)),
        slot=raw.get("ins", "NONE"),
        automix_group=group,
        automix_weight=weight,
    )


def build(number: int, entry: dict[str, Any]) -> tuple[ChannelData, list[Anomaly]]:
    eq, found = eq_models.build(entry.get("eq", {}))
    sends, send_found = build_sends(entry.get("send"))
    main_sends, main_found = build_main_sends(entry.get("main"))
    anomalies = [
        Anomaly(a.code, f"ch.{number}.{a.where}", a.detail)
        for a in (*found, *send_found, *main_found)
    ]

    conn = entry.get("in", {}).get("conn", {})
    settings = entry.get("in", {}).get("set", {})

    data = ChannelData(
        number=number,
        name=entry.get("name", ""),
        icon=int(entry.get("icon", 0)),
        color=int(entry.get("col", 0)),
        muted=bool(entry.get("mute", False)),
        fader_dB=to_db(entry.get("fdr")),
        pan=float(entry.get("pan", 0.0)),
        width=float(entry.get("wid", 100.0)),
        solo_safe=bool(entry.get("solosafe", False)),
        proc_raw=entry.get("proc", ""),
        proc_chain=proc_chain.decode(entry.get("proc", "")),
        tap_point=proc_chain.tap_point(entry.get("ptap", "")),
        tags_raw=entry.get("tags", ""),
        trim_dB=float(settings.get("trim", 0.0)),
        polarity_invert=bool(settings.get("inv", False)),
        delay_ms=float(settings.get("dly", 0.0)),
        delay_on=bool(settings.get("dlyon", False)),
        source_ref=SourceRef(conn.get("grp", "OFF"), int(conn.get("in", 0))),
        alt_source_ref=SourceRef(conn.get("altgrp", "OFF"), int(conn.get("altin", 0))),
        filter=_filter(entry.get("flt", {})),
        eq=eq,
        gate=_gate(entry.get("gate", {})),
        dyn=build_dyn(entry.get("dyn")),
        pre_insert=_insert(entry.get("preins")),
        post_insert=_insert(entry.get("postins")),
        sends=sends,
        main_sends=main_sends,
    )
    return data, anomalies
