"""A navigable view over one BusData record.

Buses, auxes, mains and matrices share this class; `kind` distinguishes
them. Same delegation pattern as Channel.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wing_parser.classifier.matcher import Classification, is_confident
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
        return found.kind == "monitor" and is_confident(found)
