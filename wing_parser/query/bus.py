"""A navigable view over one BusData record.

Buses, auxes, mains and matrices share this class; `kind` distinguishes
them. Same delegation pattern as Channel.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wing_parser.classifier.matcher import HIGH, Classification, is_confident
from wing_parser.core.models import BusData, Send
from wing_parser.descriptors import safes, tags

if TYPE_CHECKING:
    from wing_parser.query.scene import WingScene

SAFES_SECTION = {"bus": "bus", "aux": "aux", "main": "main", "matrix": "mtx"}


class Bus:
    def __init__(self, data: BusData, scene: "WingScene") -> None:
        self.data = data
        self._scene = scene

    def __getattr__(self, item: str) -> Any:
        """Same guarded delegation as Channel — see the note there.

        A private or dunder name would recurse on the copy and pickle
        paths; a name defined on the class means a property raised
        internally and must not be reported as missing.
        """
        if item.startswith("_") or hasattr(type(self), item):
            raise AttributeError(
                f"{type(self).__name__}.{item} is not resolvable on this instance"
            )
        try:
            return getattr(object.__getattribute__(self, "data"), item)
        except AttributeError as exc:
            raise AttributeError(
                f"{type(self).__name__!r} has no attribute {item!r}"
            ) from exc

    def __repr__(self) -> str:
        return f"<Bus {self.data.kind}.{self.data.number} {self.data.name!r}>"

    @property
    def dcas(self) -> tuple[int, ...]:
        return tags.parse(self.data.tags_raw).dcas

    @property
    def mute_groups(self) -> tuple[int, ...]:
        return tags.parse(self.data.tags_raw).mute_groups

    @property
    def scene_safe(self) -> bool:
        section = SAFES_SECTION.get(self.data.kind, self.data.kind)
        return safes.is_safe(self._scene.safes.get(section, ()), self.data.number)

    def send_to(self, dest: int, kind: str = "bus") -> Send | None:
        return next(
            (s for s in self.data.sends if s.dest == dest and s.dest_kind == kind),
            None,
        )

    @property
    def role(self) -> Classification:
        return self._scene.classifier.resolve(self.data.name, "buses")

    @property
    def is_monitor(self) -> bool:
        found = self.role
        is_monitor_kind = found.kind == "monitor" or found.kind.startswith("monitor.")
        return is_monitor_kind and is_confident(found)

    @property
    def notch_count(self) -> int:
        """Bands narrow and deep enough that all three knowledge-base
        sources would call them feedback notches: q >= 8, cut >= 6 dB.
        Shelves (shape SHV) are tonal moves, not notches, and are skipped."""
        bands = self.data.eq.bands or ()
        return sum(
            1 for band in bands
            if band.shape != "SHV" and band.gain <= -6.0 and band.q >= 8.0
        )

    @property
    def max_boost_above_8k(self) -> float | None:
        bands = self.data.eq.bands or ()
        boosts = [b.gain for b in bands if b.freq > 8000.0 and b.gain > 0.0]
        return max(boosts) if boosts else None

    def _fed_by(self, channel) -> bool:
        if self.data.kind == "main":
            return any(m.on and m.dest == self.data.number for m in channel.main_sends)
        if self.data.kind in ("bus", "matrix"):
            return any(
                s.on and s.dest == self.data.number and s.dest_kind == self.data.kind
                for s in channel.sends
            )
        return False   # aux inputs are not channel-send destinations

    @property
    def receives_any(self) -> bool:
        return any(self._fed_by(ch) for ch in self._scene.channels())

    @property
    def receives_ambient(self) -> bool:
        return any(
            self._fed_by(ch)
            for ch in self._scene.channels()
            if ch.source_type.kind == "utility.ambient"
            and ch.source_type.confidence >= HIGH
        )
