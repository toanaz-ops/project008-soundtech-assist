"""One function per command. Each returns a process exit code."""

from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

from wing_parser import WingScene
from wing_parser.advisory import feedback as feedback_log
from wing_parser.cli import render
from wing_parser.showcontext import load_show_context
from wing_parser.showcontext.rewrite import apply_repairs


def _load(path: str | None, show: str | None = None, live: str | None = None) -> WingScene | None:
    """`live` is an IP rather than None when `--live` was passed
    (argparse enforces `file`/`--live` as mutually exclusive, so exactly
    one of `path`/`live` is meaningful on any call). The live branch
    supplies a different `RawScene` -- via `net.snapshot.take_snapshot` --
    and nothing else about scene-building changes (design doc S4.1).

    Kept as its own branch rather than threaded through `WingScene.load`
    because a live read can fail over the network (`OSError`, or
    `TimeoutError`/`IdentityError` from `net/identity.py`, both `OSError`
    or `ValueError` subclasses) in ways a file read never does, and the
    two failure vocabularies should not blur together.
    """
    if live is not None:
        try:
            from wing_parser.net.snapshot import take_snapshot
            context = load_show_context(show) if show is not None else None
            return WingScene(take_snapshot(live).raw, context)
        except (OSError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
        return None
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
    scene = _load(args.file, live=getattr(args, "live", None))
    if scene is None:
        return 1
    print(render.scene_overview(scene))
    scene.classifier.flush()
    return 0


def channel(args) -> int:
    scene = _load(args.file, live=getattr(args, "live", None))
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
    scene = _load(args.file, getattr(args, "show", None), getattr(args, "live", None))
    if scene is None:
        return 1
    if scene.show is not None:
        text = render.show_anomalies(scene.show.anomalies)
        if text:
            print(text, file=sys.stderr)
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
    scene = _load(args.file, live=getattr(args, "live", None))
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


def showcontext_lint(args) -> int:
    try:
        context = load_show_context(args.file)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if not context.anomalies:
        print(render.lint_clean(args.file, len(context.segments)))
        return 0

    print(render.show_anomalies(context.anomalies))
    if args.fix:
        text = render.show_repairs(apply_repairs(args.file))
        if text:
            print(text)
    else:
        print(render.lint_hint())
    return 0
