"""A pulled scene as a `Session`, plus the suggested filename for one.

Split out of `live_controller.py` for headroom (D-41 needed room for the
schema-cache wiring); re-exported from there
(`from .live_session_build import session_from_snapshot, suggested_name`),
so every existing `from wing_parser.ui.live_controller import ...` keeps
working unchanged.
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from wing_parser.net.export import to_snap_json
from wing_parser.net.identity import WingIdentity
from wing_parser.net.snapshot import SnapshotResult
from wing_parser.ui.session import Session

# `wing://<host>` is the prefix `net/snapshot.py:106` stamps onto every
# scene read off a console, and `RawScene.source` is the only record a
# `SnapshotResult` keeps of which desk it came from -- so it is the one
# place `session_from_snapshot` can recover the host its filename needs.
_LIVE_SOURCE = "wing://"


def suggested_name(identity: WingIdentity | None, host: str) -> str:
    """What to call a pulled scene: `WING-GIAQUY-20260915-1432.snap`.

    A **bare filename, no directory** (D4): a `path` naming a real file
    would let a plain Save overwrite something nobody chose. Sanitised
    at the source (D-43) because `menus.save_as` proposes from this same
    path (`menus.py:87-89`) and `WingIdentity.name` is whatever somebody
    typed into the desk -- "FOH/Monitors" would otherwise arrive as a
    directory. Dot and dash survive: the fallback stays an address.
    """
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    stem = identity.name if identity is not None else f"wing-{host}"
    who = re.sub(r"[^\w.\-]", "_", stem)
    return f"{who}-{stamp}.snap"


def session_from_snapshot(
    result: SnapshotResult,
    identity: WingIdentity | None,
    profile: str | None = None,
) -> tuple[Session, str]:
    """A pulled scene as an ordinary `Session`, plus the pull-time text.

    The scene goes through `net/export.py`'s serialiser and straight back
    through `json.loads`, so what the `Session` holds is the same
    document an opened `.snap` would give it -- which is why Doctor,
    Overview, Channels, Routing and Diff need to know nothing about
    consoles.

    The text is returned as well, and it is the *pull-time original*
    (D3): export must go through `Session.save_as`, which writes the
    patched document (`session.py:92-96` -> `_document()` at `:43-44`),
    so writing this string instead would silently drop every repair made
    after the pull. Only the tests keep it, to prove that difference.
    """
    text = to_snap_json(result.raw, identity)
    host = result.raw.source.removeprefix(_LIVE_SOURCE)
    session = Session(
        json.loads(text), Path(suggested_name(identity, host)), profile
    )
    return session, text
