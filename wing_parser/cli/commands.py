"""One function per command. Each returns a process exit code."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

from wing_parser import WingScene
from wing_parser.advisory import feedback as feedback_log
from wing_parser.cli import render


def _load(path: str, show: str | None = None) -> WingScene | None:
    try:
        return WingScene.load(path, show=show)
    except OSError:
        print(f"error: cannot open {path}", file=sys.stderr)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
    return None


def _run_advisory(scene: WingScene, profile: str | None = None) -> list | None:
    """Run the advisory rules, turning a hand-edited rule file's error
    into the same `error: <message>` shape `_load` already gives a bad
    scene file, instead of a traceback. `scene.advisory.run()` reads and
    validates `principles.yaml` and every show file on every call, so a
    typo'd `supersedes` id, a rule missing `id:`, a bare-string list
    entry, an unknown predicate operator, an unknown `for_each`, an
    unknown profile name, or a YAML syntax error can all still surface
    here — this is the CLI's copy of the same guard the MCP `_guard`
    decorator already gives those tools.
    """
    try:
        return scene.advisory.run(profile)
    except (KeyError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return None


def analyze(args) -> int:
    scene = _load(args.file)
    if scene is None:
        return 1
    print(render.scene_overview(scene))
    scene.classifier.flush()
    return 0


def channel(args) -> int:
    scene = _load(args.file)
    if scene is None:
        return 1
    try:
        view = scene.channel(args.number)
    except KeyError as exc:
        print(f"error: {exc.args[0]}", file=sys.stderr)
        return 1
    print(render.channel_detail(view))
    scene.classifier.flush()
    return 0


def doctor(args) -> int:
    scene = _load(args.file, getattr(args, "show", None))
    if scene is None:
        return 1
    if scene.show is not None:
        for note in scene.show.anomalies:
            print(f"show context: {note}")
    profile = getattr(args, "profile", None)
    found = _run_advisory(scene, profile)
    if found is None:
        return 1
    if getattr(args, "json", False):
        print(json.dumps([asdict(f) for f in found], indent=2, ensure_ascii=False))
    else:
        print(render.findings(
            found,
            scene.advisory.suppressed(profile),
            off_event=scene.advisory.off_event(profile),
            declared_event=scene.advisory.declared_event(profile),
        ))
    scene.classifier.flush()
    return 0


def routing(args) -> int:
    scene = _load(args.file)
    if scene is None:
        return 1
    print(render.routing(scene.routing.summary(), scene.unclassified()))
    scene.classifier.flush()
    return 0


def diff(args) -> int:
    before, after = _load(args.before), _load(args.after)
    if before is None or after is None:
        return 1
    print(render.changes(before.diff(after), limit=args.limit))
    before.classifier.flush()
    after.classifier.flush()
    return 0


def feedback(args) -> int:
    scene = _load(args.scene, getattr(args, "show", None))
    if scene is None:
        return 1

    findings = _run_advisory(scene, getattr(args, "profile", None))
    if findings is None:
        return 1

    match = next(
        (f for f in findings if feedback_log.finding_id(f) == args.finding_id),
        None,
    )
    if match is None:
        print(
            f"error: no finding {args.finding_id!r} in {Path(args.scene).name}; "
            "run `wing doctor` to list current findings",
            file=sys.stderr,
        )
        scene.classifier.flush()
        return 1

    entry = feedback_log.record(
        match, args.verdict, note=args.note, scene=Path(args.scene).name
    )
    print(f"recorded {entry.verdict} for {entry.finding_id}")
    scene.classifier.flush()
    return 0
