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

import re
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


#: Anchored to the exact two message shapes `loader.py` emits for a
#: repairable entry (`parse_show_context`, lines 117 and 141-143):
#: "...: expects <original> read as <value>" and
#: "..., cue <id>: action <original> read as <value>". Fix round 2,
#: minor 3: a bare `" read as " in anomaly` substring check would also
#: match a `time:`/path VALUE that happens to contain that phrase
#: (`repr()` of an operator-typed string is not sanitised against it),
#: wrongly marking an anomaly `apply_repairs` will never touch as
#: fixable. Anchoring on the literal `": expects "` / `", cue ...:
#: action "` prefix immediately before it, and `\Z` (the true end of
#: the string, not just before a trailing newline) after it, means the
#: phrase can only match in the one place `loader.py` itself ever
#: writes it -- never inside an arbitrary time or id value.
_FIXABLE_PATTERN = re.compile(r": expects .+ read as .+\Z|, cue [^:]+: action .+ read as .+\Z")


def is_fixable_anomaly(anomaly: str) -> bool:
    """True when `apply_repairs` (above) would touch the entry this
    anomaly names -- so a caller (the lint dialog) can mark each
    anomaly line and gate its own Fix action without a second lint
    pass: this reads the same anomaly STRING lint already produced, it
    never re-derives one.

    `apply_repairs` re-resolves exactly two things: a segment's
    `expects` entries and a cue's `action`. `loader.py`'s own message
    for each of those two repairs reads "... read as ..."
    (`parse_show_context`'s `resolved.repaired`/`action.repaired`
    branches). Every other anomaly `loader.py` raises -- an unreadable
    `time:` value, at either the segment or the cue level -- is left
    completely alone by `apply_repairs`, and that message says "was
    ignored" instead, never "read as".
    """
    return _FIXABLE_PATTERN.search(anomaly) is not None
