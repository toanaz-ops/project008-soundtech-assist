"""One function per command. Each returns a process exit code."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

from wing_parser import WingScene
from wing_parser.advisory import feedback as feedback_log
from wing_parser.cli import render


def _load(path: str) -> WingScene | None:
    try:
        return WingScene.load(path)
    except FileNotFoundError:
        print(f"error: cannot open {path}", file=sys.stderr)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
    return None


def analyze(args) -> int:
    scene = _load(args.file)
    if scene is None:
        return 1
    print(render.scene_overview(scene))
    return 0


def channel(args) -> int:
    scene = _load(args.file)
    if scene is None:
        return 1
    try:
        view = scene.channel(args.number)
    except KeyError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(render.channel_detail(view))
    return 0


def doctor(args) -> int:
    scene = _load(args.file)
    if scene is None:
        return 1
    found = scene.advisory.run()
    if getattr(args, "json", False):
        print(json.dumps([asdict(f) for f in found], indent=2, ensure_ascii=False))
    else:
        print(render.findings(found, scene.advisory.suppressed()))
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
    return 0


def feedback(args) -> int:
    scene = _load(args.scene)
    if scene is None:
        return 1

    match = next(
        (f for f in scene.advisory.run() if feedback_log.finding_id(f) == args.finding_id),
        None,
    )
    if match is None:
        print(
            f"error: no finding {args.finding_id!r} in {Path(args.scene).name}; "
            "run `wing doctor` to list current findings",
            file=sys.stderr,
        )
        return 1

    entry = feedback_log.record(
        match, args.verdict, note=args.note, scene=Path(args.scene).name
    )
    print(f"recorded {entry.verdict} for {entry.finding_id}")
    return 0
