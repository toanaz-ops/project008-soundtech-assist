"""Scene facts shaped for tables. No Qt here.

The CLI renders the same facts as text (render.scene_overview /
render.channel_detail / render.routing); these functions are the
structured half so the desktop app never shells out to the CLI.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from wing_parser.cli.render import level


@dataclass(frozen=True)
class ChannelRow:
    number: int
    name: str
    kind: str
    confidence: float
    fader_dB: float
    muted: bool


def summarize(scene) -> dict:
    counts = {
        "channels": len(scene.channels()),
        "buses": len(scene.buses()),
        "mains": len(scene.mains()),
        "matrices": len(scene.matrices()),
    }
    return {
        "source": str(scene.source),
        "version": f"{scene.version.type_id} / {scene.version.label}",
        "counts": counts,
        "live": scene.routing.summary().live_channel_count,
        "named": len([ch for ch in scene.channels() if ch.name.strip()]),
        "anomalies": len(scene.anomalies),
    }


def channel_rows(scene) -> tuple[ChannelRow, ...]:
    return tuple(
        ChannelRow(
            number=ch.number,
            name=ch.name,
            kind=ch.source_type.kind,
            confidence=ch.source_type.confidence,
            fader_dB=ch.fader_dB,
            muted=ch.muted,
        )
        for ch in sorted(scene.channels(), key=lambda c: c.number)
    )


def channel_detail_rows(channel) -> list[tuple[str, str]]:
    """Label/value pairs mirroring render.channel_detail, line for line.

    Keep in sync with render.channel_detail — the duplication is
    deliberate: the CLI needs one text block, the desktop app needs the
    same facts as widget rows, and neither should shell out to the other.
    """
    st = channel.source_type
    rows = [
        ("Name", repr(channel.name)),
        ("Type", f"{st.kind} (confidence {st.confidence:.2f}, {st.origin})"),
        ("Fader", level(channel.fader_dB)),
        ("Muted", str(channel.muted)),
        ("Chain", " -> ".join(channel.proc_chain) or "(none)"),
        ("Tap point", str(channel.tap_point)),
        ("Scene safe", str(channel.scene_safe)),
        ("DCAs", str(channel.dcas or "(none)")),
        ("Mute groups", str(channel.mute_groups or "(none)")),
        ("Polarity (effective)", str(channel.effective_polarity)),
        ("HPF", f"{'on' if channel.filter.low_cut_on else 'off'} "
                f"{channel.filter.low_cut_hz:.0f} Hz "
                f"{channel.filter.low_cut_slope} dB/oct"),
    ]
    source = channel.source
    rows.append(
        ("Source", "not patched" if source is None else
         f"{source.group}:{source.index}  gain {source.gain_dB:.1f} dB  "
         f"phantom={source.phantom}  polarity={source.polarity}")
    )
    eq = channel.eq
    if eq.bands is None:
        rows.append(("EQ", f"{eq.model} (no descriptor — bands unparsed)"))
    else:
        rows.append(("EQ", eq.model))
        for band in eq.bands:
            rows.append((
                f"EQ band {band.name}",
                f"{band.gain:.1f} dB  {band.freq:.1f} Hz  Q {band.q:.2f}",
            ))
    live_sends = [s for s in channel.sends if s.on]
    rows.append(("Sends", f"{len(live_sends)} active"))
    for send in live_sends:
        rows.append((f"Send -> {send.dest_kind} {send.dest}",
                     f"{level(send.level_dB)}  {send.mode}"))
    return rows


def routing_view(scene) -> tuple[list[tuple[str, str]], list[str]]:
    """Summary pairs plus unclassified names, mirroring render.routing."""
    summary = scene.routing.summary()
    raw = asdict(summary)
    pairs = [(k.replace("_", " ").capitalize(), v) for k, v in raw.items()]
    # Rename live_channel_count to the stable label the table pins on.
    pairs = [(label, value) for label, value in pairs if label != "Live channel count"]
    pairs.insert(0, ("Live channels", summary.live_channel_count))
    unclassified = [view.name for view in scene.unclassified()]
    return pairs, unclassified
