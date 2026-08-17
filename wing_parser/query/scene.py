"""The public entry point: load a .snap file and query it."""

from __future__ import annotations

from pathlib import Path

from wing_parser.advisory.resolver import AdvisoryFacade
from wing_parser.classifier.resolve import Classifier
from wing_parser.core.loader import RawScene, load_raw
from wing_parser.core.models import Anomaly, DcaData, MuteGroupData, SourceData, SourceRef
from wing_parser.core.validator import validate
from wing_parser.descriptors import safes as safes_descriptor
from wing_parser.query.build_bus import build as build_bus
from wing_parser.query.build_channel import build as build_channel
from wing_parser.query.build_io import build_dcas, build_mute_groups, build_sources
from wing_parser.query.bus import Bus
from wing_parser.query.channel import Channel
from wing_parser.query.diff import Change, compare
from wing_parser.query.groups import Dca, MuteGroup, build_index
from wing_parser.query.routing import RoutingFacade
from wing_parser.showcontext import ShowContext, load_show_context
from wing_parser.showcontext import view as show_view


class WingScene:
    def __init__(self, raw: RawScene, show: ShowContext | None = None) -> None:
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

        self._bus_family: dict[str, dict[int, Bus]] = {}
        for kind, section in (
            ("bus", "bus"),
            ("aux", "aux"),
            ("main", "main"),
            ("matrix", "mtx"),
        ):
            built: dict[int, Bus] = {}
            for key, entry in raw.ae.get(section, {}).items():
                number = int(key)
                data, found = build_bus(kind, number, entry)
                anomalies.extend(found)
                built[number] = Bus(data, self)
            self._bus_family[kind] = built

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
        self._dca_index, self._mute_index = build_index(self)
        self.classifier = Classifier()
        self.show: ShowContext | None = show
        self._show_segments: tuple | None = None
        self._show_expectations: tuple | None = None

    @classmethod
    def load(cls, path: str | Path, show: str | Path | None = None) -> "WingScene":
        """`show` names a show-context YAML file; without one, the cue and
        segment iterators yield nothing and behaviour is unchanged."""
        context = load_show_context(show) if show is not None else None
        return cls(load_raw(path), context)

    def show_segments(self) -> tuple:
        """Segment views, built once. Empty when no context is loaded."""
        if self.show is None:
            return ()
        if self._show_segments is None:
            self._show_segments = show_view.build(self.show, self)
        return self._show_segments

    def show_expectations(self) -> tuple:
        """Expectation views, built once. Empty when no context is loaded."""
        if self.show is None:
            return ()
        if self._show_expectations is None:
            self._show_expectations = show_view.build_expectations(self.show, self)
        return self._show_expectations

    @property
    def raw(self) -> RawScene:
        return self._raw

    def channel(self, number: int) -> Channel:
        if number not in self._channels:
            raise KeyError(f"no channel {number} in {self.path.name}")
        return self._channels[number]

    def channels(self) -> tuple[Channel, ...]:
        return tuple(self._channels[n] for n in sorted(self._channels))

    def channel_map(self) -> dict[int, Channel]:
        return dict(self._channels)

    def source_for(self, ref: SourceRef) -> SourceData | None:
        if ref.is_off:
            return None
        return self.sources.get((ref.group, ref.index))

    def _family(self, kind: str, number: int) -> Bus:
        section = self._bus_family[kind]
        if number not in section:
            raise KeyError(f"no {kind} {number} in {self.path.name}")
        return section[number]

    def bus(self, number: int) -> Bus:
        return self._family("bus", number)

    def aux(self, number: int) -> Bus:
        return self._family("aux", number)

    def main(self, number: int) -> Bus:
        return self._family("main", number)

    def matrix(self, number: int) -> Bus:
        return self._family("matrix", number)

    def buses(self) -> tuple[Bus, ...]:
        return self._sorted("bus")

    def auxes(self) -> tuple[Bus, ...]:
        return self._sorted("aux")

    def mains(self) -> tuple[Bus, ...]:
        return self._sorted("main")

    def matrices(self) -> tuple[Bus, ...]:
        return self._sorted("matrix")

    def _sorted(self, kind: str) -> tuple[Bus, ...]:
        section = self._bus_family[kind]
        return tuple(section[n] for n in sorted(section))

    def family(self, kind: str) -> dict[int, Bus]:
        return dict(self._bus_family[kind])

    def bus_family(self) -> tuple[Bus, ...]:
        return self.buses() + self.auxes() + self.mains() + self.matrices()

    def unclassified(self) -> tuple:
        """Named channels and buses whose type could not be determined."""
        found = []
        for view in self.channels():
            if view.name.strip() and view.source_type.confidence == 0.0:
                found.append(view)
        for view in self.bus_family():
            if view.name.strip() and view.role.confidence == 0.0:
                found.append(view)
        return tuple(found)

    def dca(self, number: int) -> Dca:
        return Dca(self.dcas[number], self._dca_index.get(number, ()))

    def mute_group(self, number: int) -> MuteGroup:
        return MuteGroup(self.mute_groups[number], self._mute_index.get(number, ()))

    @property
    def routing(self) -> RoutingFacade:
        return RoutingFacade(self)

    @property
    def advisory(self) -> AdvisoryFacade:
        return AdvisoryFacade(self)

    def diff(self, other: "WingScene") -> tuple[Change, ...]:
        return compare(self, other)

    def __repr__(self) -> str:
        return f"<WingScene {self.path.name} {self.version.type_id}>"
