"""Assemble a BusData record for a bus, main, matrix or aux entry.

All four sections share a field layout, so one builder covers them; the
`kind` argument records which section the entry came from.
"""

from __future__ import annotations

from typing import Any

from wing_parser.core.models import Anomaly, BusData
from wing_parser.core.normalizer import to_db
from wing_parser.descriptors import eq_models
from wing_parser.query.build_blocks import build_dyn, build_main_sends, build_sends


def _delay_ms(raw: Any) -> float:
    """Buses store delay as a nested block; matrices sometimes as a bare number."""
    if isinstance(raw, dict):
        return float(raw.get("dly", 0.0))
    return float(raw or 0.0)


def build(kind: str, number: int, entry: dict[str, Any]) -> tuple[BusData, list[Anomaly]]:
    eq, found = eq_models.build(entry.get("eq", {}))
    sends, send_found = build_sends(entry.get("send"))
    main_sends, main_found = build_main_sends(entry.get("main"))
    anomalies = [
        Anomaly(a.code, f"{kind}.{number}.{a.where}", a.detail)
        for a in (*found, *send_found, *main_found)
    ]

    data = BusData(
        number=number,
        kind=kind,
        name=entry.get("name", ""),
        color=int(entry.get("col", 0)),
        muted=bool(entry.get("mute", False)),
        fader_dB=to_db(entry.get("fdr")),
        tags_raw=entry.get("tags", ""),
        eq=eq,
        dyn=build_dyn(entry.get("dyn")),
        delay_ms=_delay_ms(entry.get("dly")),
        sends=sends,
        main_sends=main_sends,
    )
    return data, anomalies
