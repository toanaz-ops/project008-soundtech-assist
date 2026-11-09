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


def _check(proposal, document, kb):
    bounds = Bounds(kb.bounds)
    for change in proposal.changes:
        assert pointer.read(document, change.path) == change.before, change.path
        assert bounds.violation(change.path, change.after) is None, change.path
        assert change.after != change.before, change.path


@pytest.mark.skipif(not SCENES, reason="no scenes in user-files/")
def test_half_strength_headroom_uses_interpolated_faders():
    path = SCENES[0]
    document = json.loads(path.read_text(encoding="utf-8"))
    scene, kb = WingScene(parse_raw(document, path)), knowledge.load()
    nominal, ceiling = kb.balance["headroom"]["nominal_dbfs"], kb.balance["headroom"]["ceiling_dbfs"]
    before_sum = main_sum_db(document, nominal)
    for strength in (0.0, 0.5):
        proposal = propose(scene, document, AutomixOptions("pop", strength=strength))
        _check(proposal, document, kb)
        journal = EditJournal()
        for patch in to_patches(proposal):
            journal.append(patch)
        patched = writer.applied(document, journal)
        assert main_sum_db(patched, nominal) <= max(ceiling, before_sum) + 1e-6
        if strength == 0.0:
            assert not [c for c in proposal.changes if c.stage == "fader"]


@pytest.mark.skipif(not SCENES, reason="no scenes in user-files/")
def test_speech_genre_with_its_default_stages_on_a_live_scene():
    stages = frozenset(knowledge.load().genres["genres"]["speech"]["stages"])
    for path in SCENES:
        document = json.loads(path.read_text(encoding="utf-8"))
        scene = WingScene(parse_raw(document, path))
        proposal = propose(scene, document, AutomixOptions("speech", stages=stages))
        _check(proposal, document, knowledge.load())
        assert {c.stage for c in proposal.changes} <= stages
        assert not [c for c in proposal.changes if c.stage in ("gate", "fx", "sends")]


def _int_bools(node):
    if isinstance(node, bool):
        return int(node)
    if isinstance(node, dict):
        return {k: _int_bools(v) for k, v in node.items()}
    return node


@pytest.mark.skipif(not SCENES, reason="no scenes in user-files/")
def test_int_encoded_bool_document_matches_the_file_document():
    """A console-pulled document carries 0/1 for switches (net/export.py)."""
    path = SCENES[0]
    document = json.loads(path.read_text(encoding="utf-8"))
    ints = _int_bools(document)
    kb = knowledge.load()
    for genre in ("pop", "speech"):
        file_run = propose(WingScene(parse_raw(document, path)), document, AutomixOptions(genre))
        int_run = propose(WingScene(parse_raw(ints, path)), ints, AutomixOptions(genre))
        _check(int_run, ints, kb)
        assert [c.path for c in int_run.changes] == [c.path for c in file_run.changes], genre
        for ints_change, file_change in zip(int_run.changes, file_run.changes):
            assert ints_change.after == file_change.after, ints_change.path  # True == 1, same numbers
            if isinstance(file_change.after, bool):
                assert type(ints_change.after) is int, ints_change.path  # written in the document's own type
        journal = EditJournal()
        for patch in to_patches(int_run):
            journal.append(patch)
        writer.applied(ints, journal)
