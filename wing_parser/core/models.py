"""Frozen data records for a decoded scene.

These are plain values with no back-references. Cross-object navigation
(channel -> source, DCA -> members) lives in the query layer, so this
module stays free of construction-order problems.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

OFF_GROUP = "OFF"


@dataclass(frozen=True)
class Anomaly:
    code: str
    where: str
    detail: str


@dataclass(frozen=True)
class SourceRef:
    group: str
    index: int

    @property
    def is_off(self) -> bool:
        return self.group == OFF_GROUP


@dataclass(frozen=True)
class SourceData:
    group: str
    index: int
    name: str
    gain_dB: float
    phantom: bool
    polarity: bool
    mode: str


@dataclass(frozen=True)
class EqBand:
    name: str
    freq: float
    gain: float
    q: float
    shape: str | None = None


@dataclass(frozen=True)
class Eq:
    on: bool
    model: str
    bands: tuple[EqBand, ...] | None
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Filter:
    low_cut_on: bool
    low_cut_hz: float
    low_cut_slope: int
    high_cut_on: bool
    high_cut_hz: float
    high_cut_slope: int


@dataclass(frozen=True)
class Gate:
    on: bool
    model: str
    threshold_dB: float
    range_dB: float
    attack_ms: float
    hold_ms: float
    release_ms: float


@dataclass(frozen=True)
class Dyn:
    on: bool
    model: str
    threshold_dB: float
    # None when the console stores the ratio in its "1:3" form, which every
    # gate-family model does. Sibling `Gate` omits a ratio field entirely for
    # the same reason: the a:b token is not a number and inventing one would
    # put a fabricated value in front of a mix decision.
    ratio: float | None
    attack_ms: float
    release_ms: float


@dataclass(frozen=True)
class Insert:
    on: bool
    slot: str
    automix_group: str | None
    automix_weight: float | None


@dataclass(frozen=True)
class Send:
    """One send from a channel, aux, bus, main or matrix.

    A send block mixes two destination families under one dict: numeric
    keys ("1".."16") address buses, and "MX1".."MX8" address matrices.
    Bus 3 and MX3 are different destinations, so the number alone cannot
    identify one — dest_kind is what keeps them apart.
    """

    dest_kind: str        # "bus" | "matrix"
    dest: int
    on: bool
    level_dB: float
    mode: str
    pre_on: bool
    pan: float


@dataclass(frozen=True)
class MainSend:
    dest: int
    on: bool
    level_dB: float
    pre: bool


@dataclass(frozen=True)
class ChannelData:
    number: int
    name: str
    icon: int
    color: int
    muted: bool
    fader_dB: float
    pan: float
    width: float
    solo_safe: bool
    proc_raw: str
    proc_chain: tuple[str, ...]
    tap_point: str
    tags_raw: str
    trim_dB: float
    polarity_invert: bool
    delay_ms: float
    delay_on: bool
    source_ref: SourceRef
    alt_source_ref: SourceRef
    filter: Filter
    eq: Eq
    gate: Gate
    dyn: Dyn
    pre_insert: Insert
    post_insert: Insert
    sends: tuple[Send, ...]
    main_sends: tuple[MainSend, ...]


@dataclass(frozen=True)
class BusData:
    number: int
    kind: str            # "bus" | "main" | "matrix" | "aux"
    name: str
    color: int
    muted: bool
    fader_dB: float
    tags_raw: str
    eq: Eq
    dyn: Dyn
    delay_ms: float
    sends: tuple[Send, ...]
    main_sends: tuple[MainSend, ...]


@dataclass(frozen=True)
class DcaData:
    number: int
    name: str
    muted: bool
    fader_dB: float


@dataclass(frozen=True)
class MuteGroupData:
    number: int
    name: str
    muted: bool
