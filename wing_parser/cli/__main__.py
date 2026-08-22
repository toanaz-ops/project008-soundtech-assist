"""Argument wiring only. Behaviour lives in commands.py, text in render.py."""

from __future__ import annotations

import argparse
import sys

from wing_parser import __version__
from wing_parser.advisory.feedback import VERDICTS
from wing_parser.cli import commands, net_commands


def _add_file_or_live(parser: argparse.ArgumentParser) -> None:
    """`file` and `--live IP` supply the same thing -- a scene to read --
    from two different places, so exactly one must be given. A
    mutually-exclusive group makes argparse reject both together (or
    neither) up front, rather than each command checking by hand."""
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("file", nargs="?", help="a .snap file")
    group.add_argument("--live", metavar="IP", help="read this console live instead of a file")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wing", description="Read and analyse Behringer WING .snap scene files"
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("analyze", "overview of a scene"),
        ("routing", "routing map, orphans and unclassified channels"),
    ):
        node = sub.add_parser(name, help=help_text)
        _add_file_or_live(node)
        node.set_defaults(handler=getattr(commands, name))

    node = sub.add_parser("channel", help="full detail for one channel")
    _add_file_or_live(node)
    node.add_argument("number", type=int)
    node.set_defaults(handler=commands.channel)

    node = sub.add_parser("doctor", help="advisory findings only")
    _add_file_or_live(node)
    node.add_argument("--json", action="store_true", help="machine-readable output")
    node.add_argument(
        "--profile",
        default=None,
        help="apply one show profile from knowledge/toanaz/shows/<name>.yaml",
    )
    node.add_argument(
        "--show",
        default=None,
        help="a show-context YAML file: segments, expected sources and cues",
    )
    node.set_defaults(handler=commands.doctor)

    node = sub.add_parser("diff", help="compare two scenes")
    # One file LIST, not two positionals. Two positionals -- each in a
    # mutually-exclusive group with its own --live-* flag -- is the
    # obvious shape and argparse rejects it: positionals fill left to
    # right, so `diff --live-before IP saved.snap` puts saved.snap into
    # `before`, the side the flag already supplied, and the group
    # conflict fires. Measured 2026-08-21. Arity is checked in
    # commands._diff_sides instead, which can also say what was wrong.
    node.add_argument(
        "files",
        nargs="*",
        metavar="FILE",
        help="one or two .snap files; one per side not supplied by --live-*",
    )
    node.add_argument(
        "--live-before", metavar="IP", help="read this console as the BEFORE side"
    )
    node.add_argument(
        "--live-after", metavar="IP", help="read this console as the AFTER side"
    )
    node.add_argument("--limit", type=int, default=50)
    node.set_defaults(handler=commands.diff)

    node = sub.add_parser("feedback", help="record a verdict on a finding")
    node.add_argument("finding_id", help="for example G8:ch.8.send.8")
    node.add_argument("--verdict", required=True, choices=VERDICTS)
    node.add_argument("--scene", required=True, help="the .snap the finding came from")
    node.add_argument("--note", default="")
    node.add_argument(
        "--profile",
        default=None,
        help="apply one show profile from knowledge/toanaz/shows/<name>.yaml",
    )
    node.add_argument(
        "--show",
        default=None,
        help="a show-context YAML file: segments, expected sources and cues",
    )
    node.set_defaults(handler=commands.feedback)

    node = sub.add_parser("showcontext", help="work with a show-context file")
    inner = node.add_subparsers(dest="showcontext_command", required=True)
    lint = inner.add_parser("lint", help="check a show-context file on its own")
    lint.add_argument("file")
    lint.add_argument("--fix", action="store_true",
                      help="write the repairs back into the file")
    lint.set_defaults(handler=commands.showcontext_lint)

    importer = inner.add_parser(
        "import", help="build a show-context file from a producer's spreadsheet"
    )
    importer.add_argument("sheet", help="the .xlsx file")
    importer.add_argument(
        "--map", dest="mapping", required=True,
        help="the mapping file for this producer's template",
    )
    importer.add_argument("-o", "--output", default=None,
                          help="write here instead of printing")
    importer.add_argument("--scene", default=None,
                          help="propose cues from this scene, as comments")
    importer.add_argument("--force", action="store_true",
                          help="overwrite an existing output file")
    importer.set_defaults(handler=commands.showcontext_import)

    node = sub.add_parser("net", help="talk to a live console over OSC")
    net_sub = node.add_subparsers(dest="net_command", required=True)

    identity = net_sub.add_parser("identity", help="print name, model, serial, firmware")
    identity.add_argument("ip")
    identity.set_defaults(handler=net_commands.net_identity)

    snapshot = net_sub.add_parser("snapshot", help="read the whole console")
    snapshot.add_argument("ip")
    snapshot.add_argument(
        "-o", "--output", default=None,
        help="write a .snap file here instead of printing a summary",
    )
    snapshot.set_defaults(handler=net_commands.net_snapshot)

    get = net_sub.add_parser("get", help="read one leaf")
    get.add_argument("ip")
    get.add_argument("address")
    get.set_defaults(handler=net_commands.net_get)

    set_ = net_sub.add_parser("set", help="write one leaf (dry-run unless --confirm)")
    set_.add_argument("ip")
    set_.add_argument("address")
    set_.add_argument("value")
    set_.add_argument(
        "--confirm", action="store_true",
        help="actually send the write; without it, nothing is sent",
    )
    set_.set_defaults(handler=net_commands.net_set)

    toggle = net_sub.add_parser("toggle", help="flip a 0/1 leaf (dry-run unless --confirm)")
    toggle.add_argument("ip")
    toggle.add_argument("address")
    toggle.add_argument(
        "--confirm", action="store_true",
        help="actually send the write; without it, nothing is sent",
    )
    toggle.set_defaults(handler=net_commands.net_toggle)

    push = net_sub.add_parser("push", help="push a scene file (dry-run unless --confirm)")
    push.add_argument("ip")
    push.add_argument("file")
    push.add_argument(
        "--confirm", action="store_true",
        help="actually send the writes; without it, nothing is sent",
    )
    push.set_defaults(handler=net_commands.net_push)

    watch = net_sub.add_parser("watch", help="report changes on a running console")
    watch.add_argument("host", metavar="IP")
    watch.add_argument("--json", action="store_true", help="machine-readable output")
    watch.add_argument(
        "--interval",
        type=float,
        default=0.25,
        help="seconds between rounds (default 0.25; a 120-leaf round measured 0.022s)",
    )
    watch.add_argument(
        "--until",
        type=float,
        default=None,
        metavar="SECONDS",
        help="stop after this long; without it, runs until interrupted",
    )
    watch.set_defaults(handler=net_commands.net_watch)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
