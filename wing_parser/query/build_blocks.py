"""Blocks shared by every addressable strip.

Channels, auxes, buses, mains and matrices all carry a dynamics block and
the same two send collections. These builders live here rather than in
build_channel.py so the bus builder does not have to depend on the
channel builder to reach them.
"""

from __future__ import annotations

from typing import Any

from wing_parser.core.models import Anomaly, Dyn, MainSend, Send
from wing_parser.core.normalizer import to_db

MATRIX_PREFIX = "MX"


def _ratio(value: Any) -> float | None:
    """A dynamics ratio is a number for compressor-family models and the
    string "1:3" for gate-family ones.

    Neither sample file exercises the string form -- both carry only CMB and
    COMP -- so `float()` alone read correctly for as long as those two files
    were the only input. A live console defaults its buses to GATE, and a
    scene saved from one therefore contains a ratio `float()` cannot parse.
    Returning None rather than a guess keeps the sibling convention set by
    `Gate`, which models no ratio at all.
    """
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_dyn(raw: dict[str, Any] | None) -> Dyn:
    """Public: build_bus.py builds the same block from bus entries."""
    raw = raw or {}
    return Dyn(
        on=bool(raw.get("on", False)),
        model=raw.get("mdl", "NONE"),
        threshold_dB=float(raw.get("thr", 0.0)),
        ratio=_ratio(raw.get("ratio", 1.0)),
        attack_ms=float(raw.get("att", 0.0)),
        release_ms=float(raw.get("rel", 0.0)),
    )


def parse_send_key(key: str) -> tuple[str, int] | None:
    """Split a send-block key into its destination kind and number.

    Both real files store 16 numeric bus keys and 8 "MX<n>" matrix keys in
    the same dict — and a main's send block holds *only* matrix keys, so
    discarding the non-numeric ones would leave every main with no sends
    at all.

    Returns None for a key that is neither form. Every sibling in this
    codebase reports malformed input rather than raising, so a corrupt
    key must not abort the whole channel build.
    """
    if key.startswith(MATRIX_PREFIX):
        rest, kind = key[len(MATRIX_PREFIX):], "matrix"
    else:
        rest, kind = key, "bus"
    try:
        return kind, int(rest)
    except ValueError:
        return None


def build_sends(
    raw: dict[str, Any] | None,
) -> tuple[tuple[Send, ...], list[Anomaly]]:
    """Public: shared with build_bus.py."""
    sends: list[Send] = []
    anomalies: list[Anomaly] = []

    for key, value in (raw or {}).items():
        parsed = parse_send_key(key)
        if parsed is None:
            anomalies.append(
                Anomaly(
                    code="malformed_send_key",
                    where=f"send.{key}",
                    detail="neither a bus number nor MX<n>; send skipped",
                )
            )
            continue
        dest_kind, dest = parsed
        sends.append(
            Send(
                dest_kind=dest_kind,
                dest=dest,
                on=bool(value.get("on", False)),
                level_dB=to_db(value.get("lvl")),
                mode=value.get("mode", "GRP"),
                pre_on=bool(value.get("pon", False)),
                pan=float(value.get("pan", 0.0)),
            )
        )

    # Buses first, then matrices, each ascending — a stable order the diff
    # and the rule engine can both rely on.
    return tuple(sorted(sends, key=lambda s: (s.dest_kind, s.dest))), anomalies


def build_main_sends(
    raw: dict[str, Any] | None,
) -> tuple[tuple[MainSend, ...], list[Anomaly]]:
    """Public: shared with build_bus.py. Main keys are always numeric."""
    sends: list[MainSend] = []
    anomalies: list[Anomaly] = []

    for key, value in (raw or {}).items():
        try:
            dest = int(key)
        except ValueError:
            anomalies.append(
                Anomaly(
                    code="malformed_send_key",
                    where=f"main.{key}",
                    detail="not a main number; send skipped",
                )
            )
            continue
        sends.append(
            MainSend(
                dest=dest,
                on=bool(value.get("on", False)),
                level_dB=to_db(value.get("lvl")),
                pre=bool(value.get("pre", False)),
            )
        )

    return tuple(sorted(sends, key=lambda s: s.dest)), anomalies
