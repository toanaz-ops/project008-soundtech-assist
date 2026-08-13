"""Parse the `tags` membership string.

Membership is stored on the member ("I am in DCA 8"), not on the group,
so building the reverse index is the query layer's job. This module only
turns one string into structured membership.
"""

from __future__ import annotations

from dataclasses import dataclass

from wing_parser.descriptors import registry


@dataclass(frozen=True)
class Membership:
    dcas: tuple[int, ...] = ()
    mute_groups: tuple[int, ...] = ()
    unknown: tuple[str, ...] = ()


def parse(tags_raw: str) -> Membership:
    doc = registry.load("tags")
    separator = doc["separator"]
    prefixes = doc["prefixes"]

    dcas: set[int] = set()
    mute_groups: set[int] = set()
    unknown: list[str] = []

    for token in (tags_raw or "").split(separator):
        token = token.strip()
        if not token:
            continue
        spec = next(((p, prefixes[p]) for p in prefixes if token.startswith(p)), None)
        if spec is None:
            unknown.append(token)
            continue
        prefix, rules = spec
        try:
            index = int(token[len(prefix):])
        except ValueError:
            unknown.append(token)
            continue
        if not 1 <= index <= rules["max"]:
            unknown.append(token)
            continue
        (dcas if rules["kind"] == "dca" else mute_groups).add(index)

    return Membership(
        dcas=tuple(sorted(dcas)),
        mute_groups=tuple(sorted(mute_groups)),
        unknown=tuple(unknown),
    )
