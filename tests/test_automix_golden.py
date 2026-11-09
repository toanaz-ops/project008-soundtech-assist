"""Golden snapshots of automix proposals (wave 12, spec section 9 item 1).

One parametrised test. Each case stores every (path, after) pair plus the
suggestion / skipped counts. To accept an intended change, regenerate with
AUTOMIX_REGEN_GOLDEN=1 and review the JSON diff before committing it.
"""

import json
import os
from pathlib import Path

import pytest

from wing_parser import WingScene
from wing_parser.automix import AutomixOptions, propose
from wing_parser.core.loader import parse_raw

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = Path(__file__).parent / "data" / "automix_golden"

CASES = (
    [(g, s) for g in ("pop", "rock", "ballad", "jazz") for s in ("LIVE", "OCHESTRA")]
    + [(g, s) for g in ("speech", "jazz", "edm") for s in ("GIAQUY_WING", "CAI LUONG")]
    + [(g, "example-Vu") for g in ("pop", "rock", "speech")]
)


def _slug(genre: str, scene: str) -> str:
    return f"{genre}-{scene.lower().replace(' ', '_')}.json"


@pytest.mark.parametrize("genre,scene", CASES, ids=[_slug(g, s)[:-5] for g, s in CASES])
def test_golden(genre, scene):
    path = ROOT / "user-files" / f"{scene}.snap"
    document = json.loads(path.read_text(encoding="utf-8"))
    proposal = propose(WingScene(parse_raw(document, path)), document, AutomixOptions(genre))
    snapshot = {
        "changes": [[c.path, c.after] for c in proposal.changes],
        "suggestions": len(proposal.suggestions),
        "skipped": len(proposal.skipped),
        "headroom_trim_db": proposal.headroom_trim_db,
    }
    golden = GOLDEN / _slug(genre, scene)
    if os.environ.get("AUTOMIX_REGEN_GOLDEN") == "1":
        golden.parent.mkdir(parents=True, exist_ok=True)
        golden.write_text(json.dumps(snapshot, indent=1) + "\n", encoding="utf-8")
    assert golden.is_file(), f"missing {golden.name}; run with AUTOMIX_REGEN_GOLDEN=1"
    assert snapshot == json.loads(golden.read_text(encoding="utf-8"))
