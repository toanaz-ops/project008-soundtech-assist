"""Argument wiring only. Behaviour lives in commands.py, text in render.py."""

from __future__ import annotations

import argparse
import sys

from wing_parser import __version__
from wing_parser.advisory.feedback import VERDICTS
from wing_parser.cli import commands


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
        node.add_argument("file")
        node.set_defaults(handler=getattr(commands, name))

    node = sub.add_parser("channel", help="full detail for one channel")
    node.add_argument("file")
    node.add_argument("number", type=int)
    node.set_defaults(handler=commands.channel)

    node = sub.add_parser("doctor", help="advisory findings only")
    node.add_argument("file")
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
    node.add_argument("before")
    node.add_argument("after")
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

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
