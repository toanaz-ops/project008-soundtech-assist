"""Join an imported `expects:` against a scene, as a commented-out cue.

Nothing is ever written outside a comment. This is a join between two
things already computed -- the kinds build.py resolved and the
classifications the scene already carries -- so it adds no new
name-guessing layer, and this project has exactly one of those on
purpose.

The proposal is a whole cue rather than a channel list because `channels`
is a Cue field, not a Segment field. Applying it does more than fill in
a number: it brings Q1, Q2 and Q6 to life for that segment, and Q3 once
a DCA is named (Q7 ships disabled and no cue can revive it).

Stripping every `#` and leaving `cues: []` in place does not work: the
loader reads a segment's cues with `entry.get("cues")`
(`wing_parser/showcontext/loader.py:123`) and ignores any other key, so
an empty `cues: []` left standing beside the new lines is what it
finds -- silently, since an unrecognised key is not an error. The
rendered comment says outright which lines to delete and that the rest
replaces `cues: []`, not sits beside it.

The returned dict is keyed by segment id, which is safe only because
`build.build` makes those ids unique (`build.py:_unique`, folded the way
`showcontext/loader.py:104` folds them). Without that invariant a
repeated id would be last-write-wins here and `emit.render` would print
the survivor's channels above every segment sharing the id -- a claim
the sheet never made.
"""

from __future__ import annotations

from wing_parser.showcontext.view import channels_of


def for_segments(result, scene) -> dict[str, tuple[str, ...]]:
    proposals: dict[str, tuple[str, ...]] = {}

    for built in result.segments:
        numbers: list[int] = []
        found: list[str] = []
        for kind in built.segment.expects:
            matches = channels_of(scene, kind)
            if not matches:
                continue
            for channel in matches:
                numbers.append(channel.data.number)
                found.append(
                    f"--scene: ch {channel.data.number} "
                    f"{channel.data.name!r} is {kind}"
                )

        if not numbers:
            continue

        listed = ", ".join(str(number) for number in sorted(set(numbers)))
        proposals[built.segment.id] = tuple(found) + (
            "delete this and the line(s) above; replace \"cues: []\" below with:",
            "cues:",
            f"  - id: \"{built.segment.id} cue 1\"",
            "    action: open",
            f"    channels: [{listed}]",
        )

    return proposals
