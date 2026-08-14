"""Reverse index for DCA and mute-group membership.

The file records membership on the member ("I am in DCA 8"), so
answering "who is in DCA 8" means walking every channel, aux, bus, main
and matrix once and inverting.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from wing_parser.core.models import DcaData, MuteGroupData

if TYPE_CHECKING:
    from wing_parser.query.scene import WingScene


@dataclass(frozen=True)
class GroupMember:
    kind: str
    number: int
    name: str


Index = dict[int, tuple[GroupMember, ...]]


def build_index(scene: "WingScene") -> tuple[Index, Index]:
    dca_members: dict[int, list[GroupMember]] = {}
    mute_members: dict[int, list[GroupMember]] = {}

    entries = [("channel", ch) for ch in scene.channels()]
    entries += [(entry.kind, entry) for entry in scene.bus_family()]

    for kind, view in entries:
        member = GroupMember(kind=kind, number=view.number, name=view.name)
        for number in view.dcas:
            dca_members.setdefault(number, []).append(member)
        for number in view.mute_groups:
            mute_members.setdefault(number, []).append(member)

    freeze = lambda index: {n: tuple(v) for n, v in index.items()}  # noqa: E731
    return freeze(dca_members), freeze(mute_members)


class Dca:
    def __init__(self, data: DcaData, members: tuple[GroupMember, ...]) -> None:
        self.number = data.number
        self.name = data.name
        self.muted = data.muted
        self.fader_dB = data.fader_dB
        self.members = members

    def __repr__(self) -> str:
        return f"<Dca {self.number} {self.name!r} members={len(self.members)}>"


class MuteGroup:
    def __init__(self, data: MuteGroupData, members: tuple[GroupMember, ...]) -> None:
        self.number = data.number
        self.name = data.name
        self.muted = data.muted
        self.members = members

    def __repr__(self) -> str:
        return f"<MuteGroup {self.number} {self.name!r} members={len(self.members)}>"
