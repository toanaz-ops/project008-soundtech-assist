"""The public entry point: load a .snap file and query it."""

from __future__ import annotations

from pathlib import Path

from wing_parser.core.loader import RawScene, load_raw
from wing_parser.core.models import Anomaly, DcaData, MuteGroupData, SourceData, SourceRef
from wing_parser.core.validator import validate
from wing_parser.descriptors import safes as safes_descriptor
from wing_parser.query.build_channel import build as build_channel
from wing_parser.query.build_io import build_dcas, build_mute_groups, build_sources
from wing_parser.query.channel import Channel


class WingScene:
    def __init__(self, raw: RawScene) -> None:
        self._raw = raw
        self.path: Path = raw.path
        self.version = raw.version

        anomalies: list[Anomaly] = list(validate(raw))

        self._channels: dict[int, Channel] = {}
        for key, entry in raw.ae.get("ch", {}).items():
            number = int(key)
            data, found = build_channel(number, entry)
            anomalies.extend(found)
            self._channels[number] = Channel(data, self)

        self.sources: dict[tuple[str, int], SourceData] = build_sources(
            raw.ae.get("io", {}).get("in", {})
        )
        self.dcas: dict[int, DcaData] = build_dcas(raw.ae.get("dca", {}))
        self.mute_groups: dict[int, MuteGroupData] = build_mute_groups(
            raw.ae.get("mgrp", {})
        )
        self.safes: dict[str, tuple[bool, ...]] = safes_descriptor.decode_scene(
            raw.ce.get("safes", {})
        )
        self.anomalies: tuple[Anomaly, ...] = tuple(anomalies)

    @classmethod
    def load(cls, path: str | Path) -> "WingScene":
        return cls(load_raw(path))

    @property
    def raw(self) -> RawScene:
        return self._raw

    def channel(self, number: int) -> Channel:
        if number not in self._channels:
            raise KeyError(f"no channel {number} in {self.path.name}")
        return self._channels[number]

    def channels(self) -> tuple[Channel, ...]:
        return tuple(self._channels[n] for n in sorted(self._channels))

    def source_for(self, ref: SourceRef) -> SourceData | None:
        if ref.is_off:
            return None
        return self.sources.get((ref.group, ref.index))

    def __repr__(self) -> str:
        return f"<WingScene {self.path.name} {self.version.type_id}>"
