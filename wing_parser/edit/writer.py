"""Apply a journal to a document and write it out as a .snap.

Patching a copy of the original document, rather than re-serialising
the parsed model, is what makes the write lossless. Verified 2026-08-18
against both sample files, which carry different top-level key sets:
`factory-scene.snap` additionally has `ae_globals`, `ce_globals`,
`created`, `creator_fw`, `creator_sn` and `creator_version`. A writer
built from the model would have dropped all six without a word, and
would have looked correct on `example-Vu.snap`.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

from wing_parser.edit import pointer
from wing_parser.edit.journal import EditJournal


def applied(document: dict, journal: EditJournal) -> dict:
    """A deep copy with every patch applied, in order. The input is not
    touched -- the original is the one thing the session must be able to
    trust for the whole of its life."""
    patched = copy.deepcopy(document)
    for patch in journal.patches():
        pointer.write(patched, patch.path, patch.after)
    return patched


def write_snap(document: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(document), encoding="utf-8")
