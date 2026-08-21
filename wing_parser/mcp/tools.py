"""Tool bodies, as plain functions.

Kept out of server.py so they are testable without a running server.
Each returns a string and swallows its own failures: an exception
crossing the MCP boundary is far less useful to Claude than a sentence
saying what went wrong.

Docstrings here are the tool descriptions Claude reads to decide which
tool to call, so they say when to use each one, not just what it does.
"""

from __future__ import annotations

import contextlib
import functools
import io
from typing import Callable

from wing_parser import WingScene
from wing_parser.cli import render
from wing_parser.cli.commands import _load


def _guard(function):
    @functools.wraps(function)
    def wrapper(*args, **kwargs) -> str:
        try:
            return function(*args, **kwargs)
        except OSError as exc:
            # exc.filename is always set: every OSError caught here comes
            # from Path.read_text (via WingScene.load), which sets it on
            # every failure mode. args[0] would be wrong for diff(before,
            # after) if it were ever needed, since the failing path is not
            # necessarily the first argument -- correct even though the
            # fallback cannot fire today.
            return f"error: cannot open {exc.filename}"
        except (KeyError, ValueError) as exc:
            return f"error: {exc}"

    return wrapper


def _scene(path: str | None, show: str | None = None, live: str | None = None):
    """One loader for every tool, so MCP cannot drift from the CLI on
    what a scene is or where it may come from.

    `_load` reports a failure by printing to stderr and returning
    `None` -- fine for the CLI, where stderr reaches the terminal, but
    an MCP session only ever sees this function's return value, so that
    message would otherwise be lost. Capture it (still never touching
    stdout, the MCP protocol channel) so a bad path or an unreachable
    console still names itself instead of falling back to one generic
    sentence for every failure.
    """
    captured = io.StringIO()
    with contextlib.redirect_stderr(captured):
        scene = _load(path, show, live)
    if scene is None:
        message = captured.getvalue().strip()
        if message.startswith("error: "):
            message = message[len("error: "):]
        raise ValueError(
            message or "could not read a scene: pass either a .snap path or live=<ip>"
        )
    return scene


@_guard
def analyze(path: str | None = None, live: str | None = None) -> str:
    """Overview of a scene: channels, buses, names, levels, inferred
    source types, firmware version and parser anomalies.

    Pass `live` with a console's IP to read a running desk instead of a
    file.
    """
    scene = _scene(path, live=live)
    out = render.scene_overview(scene)
    scene.classifier.flush()
    return out


@_guard
def channel(path: str | None = None, number: int = 1, live: str | None = None) -> str:
    """Full detail for one input channel, 1 to 40.

    Use when a question is about a specific channel: its EQ curve, gate
    and dynamics settings, high-pass filter, preamp gain, phantom power,
    polarity, tap point, DCA and mute-group membership, or which buses
    it feeds.
    """
    scene = _scene(path, live=live)
    out = render.channel_detail(scene.channel(number))
    scene.classifier.flush()
    return out


@_guard
def diff(before: str, after: str) -> str:
    """Field-by-field comparison of two scene files.

    Use when asked what changed between two scenes, for example a
    factory default and a show file, or last night's file and tonight's.
    Paths read in decoded terms such as ch.8.fader_dB, and level changes
    carry a magnitude in dB.
    """
    before_scene = WingScene.load(before)
    after_scene = WingScene.load(after)
    out = render.changes(before_scene.diff(after_scene))
    # compare() walks raw dataclasses today and never resolves a name, so
    # these flushes are inert — but the CLI's diff command flushes both
    # scenes (and is spy-tested for it), and the day diff output gains a
    # classified field this keeps the two surfaces from silently diverging.
    before_scene.classifier.flush()
    after_scene.classifier.flush()
    return out


@_guard
def routing(path: str | None = None, live: str | None = None) -> str:
    """Routing map: orphans, ALT-sourced channels and anything the
    classifier could not identify.

    Pass `live` with a console's IP to read a running desk instead of a
    file.
    """
    scene = _scene(path, live=live)
    out = render.routing(scene.routing.summary(), scene.unclassified())
    scene.classifier.flush()
    return out


@_guard
def doctor(
    path: str | None = None,
    profile: str | None = None,
    show: str | None = None,
    live: str | None = None,
) -> str:
    """Run the advisory rules and report likely misconfigurations.

    Use when asked to check, review, or find problems in a scene. Each
    finding names the rule, the target, and which rule layer decided it
    (base for generic industry practice, toanaz for personal principles,
    show for one-off overrides). Rules switched off by a higher layer are
    listed too.

    Pass `profile` to apply one show profile from the knowledge
    directory. Pass `show` with a show-context YAML to also report where
    the cue sheet and the console disagree (rules Q1-Q7). Pass `live`
    with a console's IP to read a running desk instead of a file.
    """
    scene = _scene(path, show=show, live=live)
    found = scene.advisory.run(profile)
    text = render.findings(found, scene.advisory.suppressed(profile))
    scene.classifier.flush()
    return text


TOOLS: dict[str, Callable[..., str]] = {
    "wing_analyze": analyze,
    "wing_channel": channel,
    "wing_diff": diff,
    "wing_routing": routing,
    "wing_doctor": doctor,
}
