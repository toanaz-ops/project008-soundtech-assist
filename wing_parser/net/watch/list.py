"""Build the concrete address list a watch session polls.

The derivation is indirect on purpose. `schema._expand` drops every "$"
child (S2.2: read-only keys are absent from .snap), and the "$" keys are
exactly what a watch session wants -- S2.2 again: $fdr and $mute are the
EFFECTIVE values, already folding in DCA and mute-override. So the walk
supplies the strip SET, and the keys come from watchlist.yaml.

The alternative -- probe /ch/1, /ch/2, ... and stop at the first silence
-- is what S2.7 measured and rejected: it lost a whole family once and
then reproduced correctly 30 times out of 30. Rare and silent is the
dangerous combination, and `walk_schema` is the path that reports what it
could not resolve instead of folding it into "absent".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

from wing_parser.net.client import OSC_PORT, WingClient
from wing_parser.net.schema import walk_schema

_DATA = Path(__file__).resolve().parent / "data" / "watchlist.yaml"

# The families a strip address can name. Kept explicit rather than
# inferred so a typo in watchlist.yaml is refused (see build_watch_list)
# rather than silently contributing nothing.
FAMILIES = ("ch", "bus", "main", "mtx", "dca")

_STRIP_RE = re.compile(rf"^/({'|'.join(FAMILIES)})/(\d+)/")


@dataclass(frozen=True)
class WatchList:
    """`unresolved` is a field rather than an omission for the same reason
    `SchemaResult.unresolved_nodes` is: a node that never answered must
    stay visible to the caller."""

    addresses: tuple[str, ...]
    unresolved: tuple[str, ...]
    strips: dict[str, int]


@lru_cache(maxsize=1)
def _load_yaml() -> dict[str, tuple[str, ...]]:
    document = yaml.safe_load(_DATA.read_text(encoding="utf-8")) or {}
    families = document.get("families") or {}
    return {name: tuple(keys) for name, keys in families.items()}


def load_watch_keys(path: Path | None = None) -> dict[str, tuple[str, ...]]:
    """The shipped config, or one read from `path` for a caller that
    wants to watch something else."""
    if path is None:
        return dict(_load_yaml())
    document = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    families = document.get("families") or {}
    return {name: tuple(keys) for name, keys in families.items()}


def build_watch_list(
    host: str,
    *,
    port: int = OSC_PORT,
    client: WingClient | None = None,
    keys: dict[str, tuple[str, ...]] | None = None,
    **walk_kwargs,
) -> WatchList:
    """Walk the console, then emit one address per (strip, key) pair.

    Fresh every call, like `walk_schema` itself: the tree's shape depends
    on live values, so a cached list would miss what a loaded desk holds.
    """
    wanted = load_watch_keys() if keys is None else keys

    unknown = sorted(set(wanted) - set(FAMILIES))
    if unknown:
        raise ValueError(
            f"watch config names {', '.join(unknown)}, which is not a strip "
            f"family; expected one of {', '.join(FAMILIES)}"
        )

    schema = walk_schema(host, port=port, client=client, **walk_kwargs)

    present: dict[str, set[int]] = {}
    for address in schema.leaves:
        match = _STRIP_RE.match(address)
        if match:
            present.setdefault(match.group(1), set()).add(int(match.group(2)))

    addresses: list[str] = []
    strips: dict[str, int] = {}
    for family in FAMILIES:
        if family not in wanted or family not in present:
            continue
        numbers = sorted(present[family])
        strips[family] = len(numbers)
        for number in numbers:
            addresses.extend(f"/{family}/{number}/{key}" for key in wanted[family])

    return WatchList(
        addresses=tuple(addresses),
        unresolved=schema.unresolved_nodes,
        strips=strips,
    )
