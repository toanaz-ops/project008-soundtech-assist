"""Scene, journal, and the re-derivation that keeps them honest.

No Qt here. The window observes this object; this object knows nothing
about widgets.

Every change re-applies the whole journal to a copy of the original
document, rebuilds the scene and re-runs the advisory. Measured
2026-08-18 on the real file at about 100 ms for the whole pipeline
(37 ms load, 104 ms advisory, three repeats at 90/103/99 ms), which is
imperceptible and buys the property that matters: the findings list is
always the truth about the current state, never a stale list with
edits pencilled on top. A repair that fails to clear its finding is
visible in the same second it is made, rather than at a console.
"""

from __future__ import annotations

import json
from pathlib import Path

from typing import Any

from wing_parser.advisory.models import Finding, Rule
from wing_parser.core.loader import parse_raw
from wing_parser.edit import pointer, repairs, writer
from wing_parser.edit.journal import EditJournal, Patch
from wing_parser.query.scene import WingScene


class Session:
    def __init__(self, document: dict, path: Path, profile: str | None = None) -> None:
        self._original = document
        self.path = Path(path)
        self.profile = profile
        self._journal = EditJournal()
        self._derive()

    @classmethod
    def open(cls, path: str | Path, profile: str | None = None) -> "Session":
        file_path = Path(path)
        return cls(
            json.loads(file_path.read_text(encoding="utf-8")), file_path, profile
        )

    def _document(self) -> dict:
        return writer.applied(self._original, self._journal)

    def _derive(self) -> None:
        self.scene = WingScene(parse_raw(self._document(), self.path))
        self._findings = self.scene.advisory.run(self.profile)
        self._rules = {r.id: r for r in self.scene.advisory.rules(self.profile)}

    def findings(self) -> list[Finding]:
        return self._findings

    def rule(self, rule_id: str) -> Rule | None:
        return self._rules.get(rule_id)

    def repair(self, finding: Finding) -> bool:
        """Apply the declared repair, or answer False if none is declared.

        `before` is read from the *currently patched* document rather
        than the original, so a second edit to the same key records
        what was actually there when the operator looked at it.
        """
        patch = repairs.patch_for(finding, self._document())
        if patch is None:
            return False
        self._journal.append(patch)
        self._derive()
        return True

    def undo(self) -> bool:
        if self._journal.undo() is None:
            return False
        self._derive()
        return True

    def reanalyse(self) -> None:
        """Re-run the whole derive pipeline against the current journal.

        The public face of the F5 accelerator: findings and rules are
        recomputed from the patched document, never carried over stale.
        """
        self._derive()

    def changes(self) -> tuple[Patch, ...]:
        return self._journal.patches()

    @property
    def dirty(self) -> bool:
        return bool(self._journal)

    def save_as(self, path: str | Path) -> None:
        """Write a new file. The journal survives: Save As is not a
        commit, and the operator may save more than one variant from
        the same set of edits."""
        writer.write_snap(self._document(), path)

    def record_value(self, path: str, value: Any, *, label: str, because: str) -> Patch:
        """Move one leaf outside the repair table, and re-derive.

        The journal is the only door into the document -- `_document()` is
        `writer.applied(original, journal)` (`:43-44`) -- so a console
        clamp (F8) and a successful revert (W13) both land here. `before`
        is read from the CURRENTLY PATCHED document, exactly as `repair`
        does (`:64`), so a second move of the same key records what was
        actually there when the operator looked at it.
        """
        patch = Patch(
            path=path,
            before=pointer.read(self._document(), path),
            after=value,
            because=because,
            label=label,
        )
        self._journal.append(patch)
        self._derive()
        return patch
