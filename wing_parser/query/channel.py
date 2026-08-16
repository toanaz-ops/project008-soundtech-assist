"""A navigable view over one ChannelData record.

Unknown attributes fall through to the record, so `ch.name` and
`ch.eq` work without restating every field. Everything defined here
needs the scene: it is the cross-object navigation the record
deliberately does not carry.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wing_parser.classifier.matcher import HIGH, Classification
from wing_parser.core.models import ChannelData, Send, SourceData
from wing_parser.descriptors import safes, tags

if TYPE_CHECKING:
    from wing_parser.query.scene import WingScene


class Channel:
    def __init__(self, data: ChannelData, scene: "WingScene") -> None:
        self.data = data
        self._scene = scene

    def __getattr__(self, item: str) -> Any:
        """Delegate unknown attributes to the wrapped record.

        Two lookups must be refused rather than delegated:

        A private or dunder name. `copy.copy` and `pickle` probe for
        `__setstate__` and friends on a shell built by `__new__`, whose
        `__dict__` is still empty — delegating would re-enter this method
        looking for `data`, which is also absent, and recurse forever.

        A name already defined on the class. Reaching here for one means a
        property raised `AttributeError` internally; answering "no such
        attribute" would bury the real bug.
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

    @property
    def source_type(self) -> Classification:
        return self._scene.classifier.resolve(self.data.name, "channels")

    @property
    def iem_send_count(self) -> int:
        """How many active sends on this channel land on a confident IEM bus.

        `dest_kind` disambiguates bus vs. matrix numbering (bus 3 and MX3
        share a number), so the destination lookup goes through the
        matching family before the role is read.
        """
        families = {"bus": self._scene.family("bus"), "matrix": self._scene.family("matrix")}
        count = 0
        for send in self.data.sends:
            if not send.on:
                continue
            destination = families.get(send.dest_kind, {}).get(send.dest)
            if destination is None:
                continue
            role = destination.role
            if role.confidence >= HIGH and (
                role.kind == "monitor.iem" or role.kind.startswith("monitor.iem.")
            ):
                count += 1
        return count

    @property
    def eq_has_lowmid_cut(self) -> bool:
        """Any band in 200-500 Hz (inclusive) pulled down -- a typical mud cut."""
        bands = self.data.eq.bands or ()
        return any(200.0 <= b.freq <= 500.0 and b.gain < 0.0 for b in bands)

    @property
    def eq_has_presence_lift(self) -> bool:
        """Any band in 2-4 kHz (inclusive) pushed up -- a typical presence lift."""
        bands = self.data.eq.bands or ()
        return any(2000.0 <= b.freq <= 4000.0 and b.gain > 0.0 for b in bands)

    @property
    def in_use(self) -> bool:
        """Patched, unmuted, routed, and with the fader actually up.

        The -90 dB floor is the discriminator that keeps a factory-default
        scene (every channel fader at the -144 sentinel, per the probe in
        the 2026-08-16 rule-set-growth spec's task-6 brief step 2) from
        reading as in use -- the acceptance constraint the spec's §4 (N1)
        demands.
        """
        if self.data.source_ref.is_off or self.data.muted:
            return False
        if self.data.fader_dB <= -90.0:
            return False
        return any(s.on for s in self.data.sends) or any(
            m.on for m in self.data.main_sends
        )
