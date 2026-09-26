"""Validate and apply an AI-proposed vocabulary change (design spec §8.2).

Two ways in share this module: the Vocabulary window's instruction box
and the Terms step's "AI: propose for unread rows" button (Task 7). Both
call `propose_changes`, both hand every returned Change to `validate`
before showing it, and only `apply` (called per ticked change, from
Apply, never automatically -- F11) writes anything.

The prompt lives here, not in a widget, so it is reviewed and tuned in
one place. `provider.py`'s `complete_json` dialect is flat
strings/numbers only (read that module's own docstring) -- a list of
change objects cannot be expressed in it, so the model is asked for one
string field, `changes_json`, holding a JSON-encoded array; this module
decodes it with `json.loads`, not a second schema layer.

Batch validation: `validate` checks one change against the vocabulary
AS IT STANDS RIGHT NOW -- it does not simulate applying the other ticked
changes in the same batch first (that would mean re-running validate for
every remaining row on every tick, and a fabricated in-memory Vocabulary
to validate against without writing). The window's own Apply covers the
gap this leaves (a change valid alone but not after an earlier one in
the same batch lands, e.g. two edits that only cycle together): it calls
straight into `vocabulary.put_set`/`put_term` per ticked change, which
re-validate for real immediately before writing and raise if the
vocabulary has moved out from under an earlier-computed `Validated`, and
the UI reports that failure without aborting the rest of the batch. See
`vocabulary_assistant.py`'s `_apply`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from wing_parser.classifier.provider import ProviderError
from wing_parser.showcontext.ingest import keywords

VALID_OPS = ("add", "edit", "delete")
VALID_TARGETS = ("set", "term")
VALID_MATCH = ("exact", "word")


class MalformedReplyError(ProviderError, ValueError):
    """The model's `changes_json` reply couldn't be read as a JSON list of
    changes -- fix round 1 (e). Also a `ProviderError`, so
    `provider_errors.classify` puts it in the same BAD_REPLY bucket as any
    other malformed model reply instead of the generic OTHER a plain
    `ValueError` would get; also a `ValueError` so the existing
    `pytest.raises(ValueError, ...)` caller (and any bare `except
    ValueError` elsewhere) keeps working unchanged."""

SYSTEM_PROMPT = (
    "You edit a cue-sheet vocabulary that maps terms and sets to "
    "console-strip kinds for a live-sound tool. Reply with one field, "
    "changes_json: a JSON-encoded string containing a list of objects, "
    'each shaped {"op": "add"|"edit"|"delete", "target": "set"|"term", '
    '"key": str, "before": object|null, "after": object|null, '
    '"reason": str}. For a set, "after" is {"label": str, "kinds": '
    '[str], "sets": [str]}; for a term it is {"kinds": [str], "sets": '
    '[str], "ignore": bool, "match": "exact"|"word"}. Only name a kind '
    "already in the known-kinds list given to you -- never invent one. "
    "You propose; a human approves every change before anything is "
    "written."
)

CHANGES_SCHEMA = {
    "type": "object",
    "properties": {"changes_json": {"type": "string"}},
    "required": ["changes_json"],
}


@dataclass(frozen=True)
class Change:
    op: str
    target: str
    key: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    reason: str


@dataclass(frozen=True)
class Validated:
    change: Change
    problems: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.problems


def parse(raw: dict) -> Change:
    missing = [field for field in ("op", "target", "key", "reason") if field not in raw]
    if missing:
        raise ValueError(f"missing field(s): {', '.join(missing)}")
    return Change(
        op=str(raw["op"]), target=str(raw["target"]), key=str(raw["key"]),
        before=raw.get("before"), after=raw.get("after"), reason=str(raw["reason"]),
    )


def current_before(change: Change, vocabulary):
    """The real stored entry for `change.key`/`change.target`, matched by
    folded identity (W3: display keys aren't folded, but identity is) --
    fix round 1, I3. Used for the UI's Before column (never the model's
    own `before` claim, which is untrusted and can say anything) AND by
    `validate` to decide add-of-existing/edit-of-missing. Returns a
    `SetEntry`/`TermEntry` when one exists (default or manual -- deleted
    ones are already excluded by `.sets()`/`.terms()`), else `None`."""
    if vocabulary is None or not isinstance(change.key, str):
        return None
    pool = vocabulary.sets() if change.target == "set" else vocabulary.terms()
    folded = keywords.fold(change.key)
    for entry in pool:
        if keywords.fold(entry.key) == folded:
            return entry
    return None


def _string_list_problem(value: Any, name: str) -> str | None:
    """None when `value` is a list/tuple of strings; otherwise a problem
    naming what's wrong -- fix round 1, I2. A bare string here used to
    silently split into single-character "kinds"/"sets" (the same trap
    `vocabulary_store.py`'s own `MalformedEntryError` guards against for
    a hand-edited `classifier.yaml`); an AI-proposed change gets the same
    protection instead of a misleading "unknown set(s) ['b','a','n','d']"."""
    if not isinstance(value, (list, tuple)):
        return f"{name} must be a list, got {type(value).__name__}"
    if not all(isinstance(item, str) for item in value):
        return f"{name} must be a list of strings"
    return None


def validate(change: Change, vocabulary) -> Validated:
    """Every problem `apply(change, vocabulary)` would hit, without
    writing -- total against untrusted model output (fix round 1, I2:
    `_show_proposal` must never crash on a malformed proposal, only show
    it greyed with why). Delegates the kind/set/cycle rules to
    `Vocabulary.dry_run_set`/`dry_run_term` (same rules `put_set`/
    `put_term` enforce) so this module carries no rule of its own to
    drift out of sync with them."""
    problems: list[str] = []
    if change.op not in VALID_OPS:
        problems.append(f"unknown op {change.op!r}")
    if change.target not in VALID_TARGETS:
        problems.append(f"unknown target {change.target!r}")
    if not isinstance(change.key, str) or not change.key.strip():
        problems.append("key must be a non-empty string")
    if problems:
        return Validated(change, tuple(problems))

    current = current_before(change, vocabulary)
    if change.op == "delete":
        if current is None:
            problems.append(f"no such {change.target} {change.key!r} to delete")
        return Validated(change, tuple(problems))
    if change.op == "add" and current is not None:
        problems.append(f"{change.target} {change.key!r} already exists -- use edit")
        return Validated(change, tuple(problems))
    if change.op == "edit" and current is None:
        problems.append(f"no such {change.target} {change.key!r} to edit")
        return Validated(change, tuple(problems))

    after = change.after
    if not isinstance(after, dict):
        return Validated(change, (f"after must be an object, got {type(after).__name__}",))

    kinds_problem = _string_list_problem(after.get("kinds", ()), "kinds")
    if kinds_problem:
        problems.append(kinds_problem)
    sets_problem = _string_list_problem(after.get("sets", ()), "sets")
    if sets_problem:
        problems.append(sets_problem)
    if change.target == "term":
        ignore_raw = after.get("ignore", False)
        if not isinstance(ignore_raw, bool):
            problems.append(f"ignore must be true or false, got {ignore_raw!r}")
        match_raw = after.get("match", "exact")
        if match_raw not in VALID_MATCH:
            problems.append(f"match must be one of {VALID_MATCH}, got {match_raw!r}")
    if problems:
        return Validated(change, tuple(problems))

    kinds = tuple(after.get("kinds", ()))
    sets_ = tuple(after.get("sets", ()))
    if change.target == "set":
        problems.extend(vocabulary.dry_run_set(change.key, kinds=kinds, sets=sets_))
    else:
        ignore = bool(after.get("ignore", False))
        problems.extend(vocabulary.dry_run_term(change.key, kinds=kinds, sets=sets_, ignore=ignore))
    return Validated(change, tuple(problems))


def apply(change: Change, vocabulary, *, origin: str = "ai-approved") -> None:
    """Write one already-validated change. Callers check `.valid` first;
    `vocabulary.py`'s own `put_set`/`put_term` validate again right
    before writing (they always do, for every caller, not just this
    one) and raise if the vocabulary moved out from under an
    earlier-computed `Validated` -- this function adds no re-check of
    its own on top of that."""
    if change.op == "delete":
        (vocabulary.delete_set if change.target == "set" else vocabulary.delete_term)(change.key)
        return
    after = change.after or {}
    if change.target == "set":
        vocabulary.put_set(
            change.key, label=str(after.get("label", change.key)),
            kinds=tuple(after.get("kinds", ())), sets=tuple(after.get("sets", ())),
            origin=origin,
        )
    else:
        vocabulary.put_term(
            change.key, kinds=tuple(after.get("kinds", ())),
            sets=tuple(after.get("sets", ())), ignore=bool(after.get("ignore", False)),
            match=str(after.get("match", "exact")), origin=origin,
        )


def build_user_prompt(instruction: str, fragments: tuple[str, ...], vocabulary,
                      known_kinds: tuple[str, ...]) -> str:
    """`vocabulary` may be `None` -- `propose_changes` must be able to
    fail on a malformed model reply before it ever needs a real
    Vocabulary (see that function's docstring), and building the prompt
    happens before the reply exists, so this guards the same way."""
    parts = ["Known kinds: " + ", ".join(known_kinds)]
    if vocabulary is not None:
        parts.append("Current sets: " + ", ".join(s.key for s in vocabulary.sets()))
        parts.append("Current terms: " + ", ".join(t.key for t in vocabulary.terms()))
    if instruction:
        parts.append(f"Instruction: {instruction}")
    if fragments:
        parts.append("Unresolved fragments: " + "; ".join(fragments))
    return "\n".join(parts)


def propose_changes(provider, *, instruction: str = "", fragments: tuple[str, ...] = (),
                    vocabulary, known_kinds: tuple[str, ...]) -> list[Change]:
    """Ask the model for changes_json, decode it, parse every entry.

    Order matters: the JSON-string decode failure must surface before
    anything here would need a real `vocabulary` (a caller with no
    vocabulary yet -- or a broken one -- should still learn its reply
    was garbage, not crash on an unrelated attribute lookup first).
    `build_user_prompt` above tolerates `vocabulary=None` for exactly
    this reason.
    """
    from wing_parser.classifier.provider import complete_json

    user = build_user_prompt(instruction, fragments, vocabulary, known_kinds)
    reply = complete_json(provider, SYSTEM_PROMPT, user, CHANGES_SCHEMA)
    try:
        raw_changes = json.loads(reply["changes_json"])
    except (TypeError, ValueError) as exc:
        raise MalformedReplyError(f"changes_json did not parse as JSON: {exc}") from exc
    if not isinstance(raw_changes, list):
        raise MalformedReplyError("changes_json must decode to a JSON list")

    changes: list[Change] = []
    for item in raw_changes:
        try:
            changes.append(parse(item))
        except (ValueError, TypeError) as exc:
            # One unparseable item must not cost every OTHER item in the
            # same reply (fix round 1, I2): `op`/`target` left empty are
            # deliberately outside VALID_OPS/VALID_TARGETS, so `validate`
            # reports this the same way it reports any other malformed
            # proposal -- greyed, with `exc`'s own text as the reason.
            key = item.get("key", "?") if isinstance(item, dict) else "?"
            changes.append(Change(op="", target="", key=str(key), before=None,
                                  after=None, reason=str(exc)))
    return changes
