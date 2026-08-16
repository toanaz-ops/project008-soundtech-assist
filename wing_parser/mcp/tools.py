"""Tool bodies, as plain functions.

Kept out of server.py so they are testable without a running server.
Each returns a string and swallows its own failures: an exception
crossing the MCP boundary is far less useful to Claude than a sentence
saying what went wrong.

Docstrings here are the tool descriptions Claude reads to decide which
tool to call, so they say when to use each one, not just what it does.
"""

from __future__ import annotations

import functools
from typing import Callable

from wing_parser import WingScene
from wing_parser.cli import render


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


@_guard
def analyze(path: str) -> str:
    """Overview of a WING .snap scene file.

    Use this first when asked anything general about a scene: how many
    channels are in use, what they are named, what the file's firmware
    version is, and whether the parser found anomalies. Returns a
    channel list with levels and inferred source types.
    """
    scene = WingScene.load(path)
    out = render.scene_overview(scene)
    scene.classifier.flush()
    return out


@_guard
def channel(path: str, number: int) -> str:
    """Full detail for one input channel, 1 to 40.

    Use when a question is about a specific channel: its EQ curve, gate
    and dynamics settings, high-pass filter, preamp gain, phantom power,
    polarity, tap point, DCA and mute-group membership, or which buses
    it feeds.
    """
    scene = WingScene.load(path)
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
def routing(path: str) -> str:
    """Routing summary for a scene.

    Use when asked how signal flows: which live channels feed nothing,
    which use an ALT input, which are unpatched or unnamed. Also lists
    channels and buses whose source type could not be inferred from
    their names.
    """
    scene = WingScene.load(path)
    out = render.routing(scene.routing.summary(), scene.unclassified())
    scene.classifier.flush()
    return out


@_guard
def doctor(path: str, profile: str | None = None) -> str:
    """Run the advisory rules and report likely misconfigurations.

    Use when asked to check, review, or find problems in a scene. Each
    finding names the rule, the target, and which rule layer decided it
    (base for generic industry practice, toanaz for personal principles,
    show for one-off overrides). Rules switched off by a higher layer are
    listed too. Pass `profile` to apply one show profile from the
    knowledge directory, which can switch base rules off for a show whose
    author is deviating from them on purpose.
    """
    scene = WingScene.load(path)
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
