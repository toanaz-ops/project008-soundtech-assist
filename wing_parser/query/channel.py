"""A navigable view over one ChannelData record.

Unknown attributes fall through to the record, so `ch.name` and
`ch.eq` work without restating every field. Everything defined here
needs the scene: it is the cross-object navigation the record
deliberately does not carry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wing_parser.core.models import ChannelData, Send, SourceData
from wing_parser.descriptors import safes, tags

if TYPE_CHECKING:
    from wing_parser.query.scene import WingScene


class Channel:
    def __init__(self, data: ChannelData, scene: "WingScene") -> None:
        self.data = data
        self._scene = scene

    def __getattr__(self, item: str) -> Any:
        # Only reached when normal lookup fails, so no recursion risk
        # for `data` and `_scene`, which are set in __init__.
        try:
            return getattr(self.data, item)
        except AttributeError as exc:
            raise AttributeError(
                f"{type(self).__name__!r} has no attribute {item!r}"
            ) from exc

    def __repr__(self) -> str:
        return f"<Channel {self.data.number} {self.data.name!r}>"

    @property
    def source(self) -> SourceData | None:
        return self._scene.source_for(self.data.source_ref)

    @property
    def alt_source(self) -> SourceData | None:
        return self._scene.source_for(self.data.alt_source_ref)

    @property
    def effective_polarity(self) -> bool:
        """Channel inversion XOR source inversion. Inverting twice is not inverting."""
        source = self.source
        return bool(self.data.polarity_invert) ^ bool(source.polarity if source else False)

    @property
    def dcas(self) -> tuple[int, ...]:
        return tags.parse(self.data.tags_raw).dcas

    @property
    def mute_groups(self) -> tuple[int, ...]:
        return tags.parse(self.data.tags_raw).mute_groups

    @property
    def scene_safe(self) -> bool:
        return safes.is_safe(self._scene.safes.get("ch", ()), self.data.number)

    def send_to(self, dest: int, kind: str = "bus") -> Send | None:
        """A send block mixes buses and matrices, so the number alone is
        ambiguous: bus 3 and MX3 share a number. Defaults to bus."""
        return next(
            (s for s in self.data.sends if s.dest == dest and s.dest_kind == kind),
            None,
        )
