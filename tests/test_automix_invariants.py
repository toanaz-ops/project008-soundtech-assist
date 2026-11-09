"""Invariants every automix proposal must keep (wave 12, spec section 9 item 2).

Over every genre and every scene in user-files/: each change reads back
from the original document, stays off the forbidden leaves and inside the
safety bounds, applies cleanly as a journal, never makes the main-sum
estimate worse than the headroom ceiling, and raises no Doctor finding the
scene did not already have.
"""

import json
from pathlib import Path

import pytest

from wing_parser import WingScene
from wing_parser.automix import GENRES, AutomixOptions, knowledge, propose, to_patches
from wing_parser.automix.bounds import Bounds
from wing_parser.automix.stages_balance import main_sum_db
from wing_parser.core.loader import parse_raw
from wing_parser.edit import pointer, writer
from wing_parser.edit.journal import EditJournal

SCENES = sorted((Path(__file__).resolve().parents[1] / "user-files").glob("*.snap"))


def _findings(document, path):
    return {(f.rule_id, f.target) for f in WingScene(parse_raw(document, path)).advisory.run(None)}


@pytest.mark.parametrize("path", SCENES, ids=[p.stem for p in SCENES])
def test_invariants(path):
    document = json.loads(path.read_text(encoding="utf-8"))
    scene = WingScene(parse_raw(document, path))
    kb = knowledge.load()
    bounds, nominal = Bounds(kb.bounds), kb.balance["headroom"]["nominal_dbfs"]
    ceiling = kb.balance["headroom"]["ceiling_dbfs"]
    original, before_sum = _findings(document, path), main_sum_db(document, nominal)
    for genre in GENRES:
        proposal = propose(scene, document, AutomixOptions(genre))
        journal = EditJournal()
        for patch in to_patches(proposal):
            journal.append(patch)
        for change in proposal.changes:
            where = f"{path.name} {genre} {change.path}"
            assert pointer.read(document, change.path) == change.before, where
            assert bounds.violation(change.path, change.after) is None, where
            assert change.after != change.before, where
        patched = writer.applied(document, journal)  # raises KeyError on a leaf that does not exist
        if any(c.stage == "fader" for c in proposal.changes):
            assert main_sum_db(patched, nominal) <= max(ceiling, before_sum) + 1e-6, f"{path.name} {genre}"
        extra = _findings(patched, path) - original
        assert not extra, f"{path.name} {genre} adds Doctor findings {sorted(extra)}"
