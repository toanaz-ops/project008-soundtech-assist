"""Who feeds what, and which channels look stranded."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from wing_parser.core.normalizer import is_silent

if TYPE_CHECKING:
    from wing_parser.query.scene import WingScene

# Which collection to read, and which dest_kind within it. Buses and
# matrices share the `sends` tuple and are told apart by dest_kind; mains
# live in their own `main_sends` tuple, which carries no kind.
SEND_SECTION: dict[str, tuple[str, str | None]] = {
    "bus": ("sends", "bus"),
    "matrix": ("sends", "matrix"),
    "main": ("main_sends", None),
}


@dataclass(frozen=True)
class Feed:
    kind: str
    number: int
    name: str
    level_dB: float
    mode: str
    on: bool


@dataclass(frozen=True)
class RoutingSummary:
    orphan_channels: tuple[int, ...]
    alt_sourced_channels: tuple[int, ...]
    unpatched_channels: tuple[int, ...]
    unnamed_but_live: tuple[int, ...]
    live_channel_count: int


def _is_live(view) -> bool:
    return not view.muted and not is_silent(view.fader_dB)


def _feeds_anything(view) -> bool:
    return any(s.on for s in view.sends) or any(m.on for m in view.main_sends)


def feeds_into(scene: "WingScene", kind: str, number: int) -> tuple[Feed, ...]:
    """Every enabled send from any channel or bus into the named destination."""
    if kind not in SEND_SECTION:
        raise ValueError(
            f"unrecognised destination kind {kind!r}; expected one of "
            f"{sorted(SEND_SECTION)}"
        )
    attribute, dest_kind = SEND_SECTION[kind]
    found: list[Feed] = []

    sources = [("channel", ch) for ch in scene.channels()]
    sources += [(entry.kind, entry) for entry in scene.bus_family()]

    for source_kind, view in sources:
        if source_kind == kind and view.number == number:
            continue                      # a bus cannot feed itself
        for send in getattr(view, attribute, ()):
            if dest_kind is not None and send.dest_kind != dest_kind:
                continue                  # bus 3 and MX3 share a number
            if send.dest == number and send.on:
                found.append(
                    Feed(
                        kind=source_kind,
                        number=view.number,
                        name=view.name,
                        level_dB=send.level_dB,
                        mode=getattr(send, "mode", "MAIN"),
                        on=send.on,
                    )
                )
    return tuple(found)


def summarise(scene: "WingScene") -> RoutingSummary:
    orphans: list[int] = []
    alt_sourced: list[int] = []
    unpatched: list[int] = []
    unnamed_live: list[int] = []
    live = 0

    for ch in scene.channels():
        if not ch.data.alt_source_ref.is_off:
            alt_sourced.append(ch.number)
        if ch.data.source_ref.is_off:
            unpatched.append(ch.number)
        if _is_live(ch):
            live += 1
            if not ch.name.strip():
                unnamed_live.append(ch.number)
            if not _feeds_anything(ch):
                orphans.append(ch.number)

    return RoutingSummary(
        orphan_channels=tuple(orphans),
        alt_sourced_channels=tuple(alt_sourced),
        unpatched_channels=tuple(unpatched),
        unnamed_but_live=tuple(unnamed_live),
        live_channel_count=live,
    )


class RoutingFacade:
    """Thin binding so callers can write scene.routing.summary()."""

    def __init__(self, scene: "WingScene") -> None:
        self._scene = scene

    def summary(self) -> RoutingSummary:
        return summarise(self._scene)

    def feeds_into(self, kind: str, number: int) -> tuple[Feed, ...]:
        return feeds_into(self._scene, kind, number)
