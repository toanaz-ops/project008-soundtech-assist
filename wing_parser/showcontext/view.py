"""What the show context means once a scene is loaded beside it.

Derivations are exposed as counts, never as collections. The predicate
language has no emptiness operator, so a tuple-returning property would
have to be written `{not: []}` in a rule -- which is always true in
Python, since `() != []`. The rule would sit silent forever and no test
against a stub would catch it. Counts match with `gt: 0`, the shape
`Bus.notch_count` already uses.

Each count has a `*_text` twin so a finding can name the actual channel
numbers instead of reporting "3".
"""

from __future__ import annotations

from wing_parser.classifier.matcher import HIGH
from wing_parser.showcontext.loader import _parse_time
from wing_parser.showcontext.models import Cue, Segment, ShowContext

# Only these two move the open/closed book. A level move on a closed
# channel is not a contradiction, and what a recall does to any given
# channel is not knowable from a cue sheet (spec section 3).
STATE_ACTIONS = {"open": True, "close": False}


def _listed(numbers: tuple[int, ...]) -> str:
    return ", ".join(str(n) for n in numbers)


class CueView:
    def __init__(self, cue: Cue, segment_id: str, scene,
                 contradictions: tuple[int, ...], gap: float | None) -> None:
        self._cue = cue
        self._scene = scene
        self.segment_id = segment_id
        self._contradictions = contradictions
        self._gap = gap

    @property
    def id(self) -> str:
        return self._cue.id

    @property
    def action(self) -> str:
        return self._cue.action

    @property
    def target_name(self) -> str:
        return f"cue.{self.segment_id}.{''.join(self._cue.id.split())}"

    @property
    def _present(self) -> dict[int, object]:
        return self._scene.channel_map()

    # Private from here down: these tuples exist only to back a count and
    # a text property, never to be read on their own -- the module's
    # contract is counts. That naming buys nothing at the predicate layer:
    # advisory/predicates.py's resolve_path() walks a dotted path with a
    # plain getattr() and does not distinguish public from private, so a
    # rule that named e.g. `cue._missing_channels` would still resolve it
    # and still hit the `{not: []}` always-true trap. This is documentation
    # of a known limit, not a guard against it.
    @property
    def _missing_channels(self) -> tuple[int, ...]:
        present = self._present
        return tuple(n for n in self._cue.channels if n not in present)

    @property
    def missing_channel_count(self) -> int:
        return len(self._missing_channels)

    @property
    def missing_channels_text(self) -> str:
        return _listed(self._missing_channels)

    @property
    def _unnamed_channels(self) -> tuple[int, ...]:
        present = self._present
        return tuple(
            n for n in self._cue.channels
            if n in present and not present[n].name.strip()
        )

    @property
    def unnamed_channel_count(self) -> int:
        return len(self._unnamed_channels)

    @property
    def unnamed_channels_text(self) -> str:
        return _listed(self._unnamed_channels)

    @property
    def _missing_dcas(self) -> tuple[int, ...]:
        return tuple(n for n in self._cue.dcas if n not in self._scene.dcas)

    @property
    def missing_dca_count(self) -> int:
        return len(self._missing_dcas)

    @property
    def missing_dcas_text(self) -> str:
        return _listed(self._missing_dcas)

    @property
    def contradiction_count(self) -> int:
        return len(self._contradictions)

    @property
    def contradictions_text(self) -> str:
        return _listed(self._contradictions)

    @property
    def seconds_after_previous(self) -> float | None:
        return self._gap


class SegmentView:
    def __init__(self, segment: Segment, scene, cues: tuple[CueView, ...]) -> None:
        self._segment = segment
        self._scene = scene
        self.cues = cues

    @property
    def id(self) -> str:
        return self._segment.id

    @property
    def title(self) -> str:
        return self._segment.title

    @property
    def target_name(self) -> str:
        return f"segment.{self._segment.id}"

    def _channels_of(self, kind: str) -> tuple:
        """Only confidently-classified channels count.

        Same threshold Bus.receives_ambient uses: a weak guess must not
        satisfy an expectation, or the rule silently stops firing on the
        thing it exists to catch.
        """
        return tuple(
            channel for channel in self._scene.channels()
            if channel.source_type.kind == kind
            and channel.source_type.confidence >= HIGH
        )

    @property
    def _unmet_expects(self) -> tuple[str, ...]:
        return tuple(k for k in self._segment.expects if not self._channels_of(k))

    @property
    def unmet_expect_count(self) -> int:
        return len(self._unmet_expects)

    @property
    def unmet_expects_text(self) -> str:
        return ", ".join(self._unmet_expects)

    @property
    def _dark_expects(self) -> tuple[str, ...]:
        found = []
        for kind in self._segment.expects:
            channels = self._channels_of(kind)
            if channels and not any(channel.in_use for channel in channels):
                found.append(kind)
        return tuple(found)

    @property
    def dark_expect_count(self) -> int:
        return len(self._dark_expects)

    @property
    def dark_expects_text(self) -> str:
        return ", ".join(self._dark_expects)


def build(context: ShowContext, scene) -> tuple[SegmentView, ...]:
    """Walk every cue in file order, keeping the open/closed book."""
    state: dict[int, bool] = {}
    previous_seconds: int | None = None
    segments: list[SegmentView] = []

    for segment in context.segments:
        cues: list[CueView] = []
        for cue in segment.cues:
            wanted = STATE_ACTIONS.get(cue.action)
            contradictions: list[int] = []
            if wanted is not None:
                for number in cue.channels:
                    if state.get(number) == wanted:
                        contradictions.append(number)
                    state[number] = wanted

            seconds = _parse_time(cue.time) if cue.time else None
            gap = (
                float(seconds - previous_seconds)
                if seconds is not None and previous_seconds is not None
                else None
            )
            if seconds is not None:
                previous_seconds = seconds

            cues.append(CueView(cue, segment.id, scene, tuple(contradictions), gap))
        segments.append(SegmentView(segment, scene, tuple(cues)))

    return tuple(segments)
