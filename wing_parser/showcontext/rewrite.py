"""Write repairs back into a show-context file.

ruamel round-trip, not PyYAML dump: the file is hand-written and carries
the author's comments and ordering, and a tool that silently reformats
the document it was asked to spell-check has taken something away.

Only a genuine repair (`Resolution.repaired`) is written back. A token
that is already valid but differently cased or separated (`Open` for
`open`) resolves without `repaired` being set -- `loader.py` does not
surface that as an anomaly either, and this module keeps the same line:
lint should not silently relabel a spelling the vocabulary already
accepts.
"""

from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML

from wing_parser.classifier.matcher import known_kinds
from wing_parser.showcontext import vocabulary


def apply_repairs(path: str | Path) -> tuple[str, ...]:
    where_from = Path(path)
    yaml = YAML()
    yaml.preserve_quotes = True
    with where_from.open(encoding="utf-8") as handle:
        doc = yaml.load(handle) or {}

    kinds = known_kinds("channels")
    repairs: list[str] = []

    for segment in doc.get("segments") or []:
        expects = segment.get("expects")
        if expects is not None:
            for index, written in enumerate(expects):
                resolved = vocabulary.resolve(str(written), kinds, what="kind")
                if resolved.repaired:
                    repairs.append(f"{written!r} -> {resolved.value!r}")
                    expects[index] = resolved.value
        for cue in segment.get("cues") or []:
            written = cue.get("action")
            if written is None:
                continue
            resolved = vocabulary.resolve(
                str(written), vocabulary.KNOWN_ACTIONS, what="action"
            )
            if resolved.repaired:
                repairs.append(f"{written!r} -> {resolved.value!r}")
                cue["action"] = resolved.value

    if repairs:
        with where_from.open("w", encoding="utf-8") as handle:
            yaml.dump(doc, handle)
    return tuple(repairs)
