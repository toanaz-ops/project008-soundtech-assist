"""Read hand-edited YAML into Rule records for the toanaz and show layers.

Base rules ship in the package and are validated on load by
`loader.load_rules`. The toanaz principles file and per-show exception
files are the two layers a human edits by hand, and a hand-edited file is
exactly where a slip is most likely and a silent default is most
dangerous -- so this module applies the same validation `load_rules`
already gives the base layer.
"""

from __future__ import annotations

from pathlib import Path

from wing_parser import config
from wing_parser.advisory.loader import _load_yaml, load_rules
from wing_parser.advisory.models import SEVERITIES, Rule
from wing_parser.advisory.validation import _optional, _validate_any_of, _validate_where

PRINCIPLES_FILE = "principles.yaml"
SHOWS_DIR = "shows"


def _principles(directory: Path | None) -> list[Rule]:
    path = config.knowledge_dir(directory) / PRINCIPLES_FILE
    if not path.exists():
        return []
    return _as_rules(path, layer="toanaz", key="principles")


def _show_rules(directory: Path | None, profile: str | None = None) -> list[Rule]:
    """Load exactly the named show file, or none at all.

    This used to glob every `*.yaml` and `*.yml` under `shows/` and apply
    all of them, which meant two show files were both active for ever --
    last week's overrides still in force tonight, with nothing to say so.
    Nothing caught it because the directory ships empty.

    A profile is selected by name and nothing is loaded without one. An
    unrecognised name raises rather than degrading to "no profile": a
    mistyped `--profile smal` would otherwise run with the base rule still
    active while its author believes it is switched off, which is the
    worst shape this failure can take.
    """
    if profile is None:
        return []

    shows = config.knowledge_dir(directory) / SHOWS_DIR
    for suffix in (".yaml", ".yml"):
        path = shows / f"{profile}{suffix}"
        if path.is_file():
            return load_rules(path, layer="show")

    available = sorted(
        {p.stem for p in list(shows.glob("*.yaml")) + list(shows.glob("*.yml"))}
    ) if shows.is_dir() else []
    raise ValueError(
        f"no profile named {profile!r} in {shows}; "
        f"available: {', '.join(available) if available else '(none)'}"
    )


def _as_rules(path: Path, layer: str, key: str) -> list[Rule]:
    """principles.yaml uses `principles:` and may omit the `when` block.

    A principle whose only job is to switch a base rule off needs no
    target of its own, so a missing `when` becomes a rule that uses the
    `none` iterator -- which yields no targets -- and exists purely for
    its `supersedes` list. An explicit
    `when` block with no `for_each` is a different, invalid case and is
    rejected the same way `loader.load_rules` rejects it, rather than
    left to raise a bare `KeyError` a few lines down.

    Every optional field -- `severity`, `source`, `rationale`,
    `requires_classifier`, `enabled`, `hardness` -- routes through
    `loader._optional`, not `.get(key, default)`. `.get` only supplies
    its default when the key is absent entirely; a hand-edited
    principles file can leave a key present but blank, which YAML
    parses as null. A blank `hardness:` would resolve to `None` under
    `.get`, `_is_active` would not recognise it as `"flexible"`, and
    the principle would fall through to unconditionally active --
    silently switching a base rule off on every show from a
    one-character slip. A blank `source:` would resolve to `None`
    instead of the documented `"ToanAZ"` default, the same hazard on a
    field that exists purely for traceability. This is also why this
    layer validates `severity` against `SEVERITIES`: `load_rules`
    already rejects a bad severity for the base layer, and toanaz is
    the one hand-maintained layer, so leaving it unvalidated here would
    make the only human-edited layer the only unchecked one.

    Three more slips a hand-edited file invites, all turned into the
    same `ValueError(f"{path}: ...")` shape `loader._rule_from` already
    uses rather than left to raise a bare `KeyError` or `AttributeError`
    a few lines down: an entry that is not a mapping at all (a bare
    string dropped into the `principles:` list), an entry missing `id:`
    entirely, and a `when:` block that is present but not a mapping
    (a scalar like `"for_each channel"`, or a YAML list) -- `when.get(...)`
    a few lines down would otherwise raise a bare `AttributeError`.
    """
    doc = _load_yaml(path)
    rules: list[Rule] = []
    for entry in doc.get(key) or []:
        if not isinstance(entry, dict):
            raise ValueError(
                f"{path}: each entry under {key!r} must be a mapping, not "
                f"{type(entry).__name__} ({entry!r})"
            )
        if not entry.get("id"):
            raise ValueError(f"{path}: rule is missing required field 'id'")

        severity = _optional(entry, "severity", "info")
        if severity not in SEVERITIES:
            raise ValueError(
                f"{path}: rule {entry['id']} has severity {severity!r}; "
                f"expected one of {SEVERITIES}"
            )
        # Twin of the loader.py hazard: `entry.get("when")` returns None
        # both when the key is absent (supersede-only) and when it is
        # present but left blank. Testing key membership instead of the
        # resolved value keeps a blank `when:` from silently becoming a
        # match-nothing supersede-only rule -- it falls through to the
        # `isinstance(when, dict)` guard below and raises instead.
        if "when" in entry:
            when = entry["when"]
            if not isinstance(when, dict):
                raise ValueError(
                    f"{path}: rule {entry['id']} has a when: block that must "
                    f"be a mapping, not {type(when).__name__} ({when!r})"
                )
            if not when.get("for_each"):
                raise ValueError(f"{path}: rule {entry['id']} has no when.for_each")
        else:
            when = {"for_each": "none", "where": {}}

        where = dict(when.get("where") or {})
        _validate_where(where, path, entry["id"])
        any_of = (
            _validate_any_of(when["any_of"], path, entry["id"])
            if "any_of" in when
            else ()
        )

        rules.append(
            Rule(
                id=entry["id"],
                title=entry.get("principle") or entry.get("title", entry["id"]),
                severity=severity,
                source=_optional(entry, "source", "ToanAZ"),
                rationale=_optional(entry, "rationale", ""),
                for_each=when["for_each"],
                where=where,
                message=entry.get("message", entry.get("principle", entry["id"])),
                layer=layer,
                requires_classifier=bool(_optional(entry, "requires_classifier", False)),
                enabled=bool(_optional(entry, "enabled", True)),
                hardness=_optional(entry, "hardness", "hard"),
                applies_when=dict(entry.get("applies_when") or {}),
                any_of=any_of,
                supersedes=tuple(entry.get("supersedes") or ()),
            )
        )
    return rules
