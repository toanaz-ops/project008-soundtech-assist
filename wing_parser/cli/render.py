"""Turn objects into text. No I/O, no argument parsing."""

from __future__ import annotations

import math
import re
from typing import Any, Iterable

BULLET = "  - "


def level(db: float) -> str:
    return "-inf" if math.isinf(db) else f"{db:.1f} dB"


def _natural(target: str) -> tuple[object, ...]:
    """Sort key that orders ch.2 before ch.10 rather than after it."""
    return tuple(int(part) if part.isdigit() else part
                 for part in re.split(r"(\d+)", target))


def scene_overview(scene) -> str:
    lines = [
        f"{scene.path.name}  [{scene.version.type_id} / {scene.version.label}]",
        f"  {len(scene.channels())} channels, {len(scene.buses())} buses, "
        f"{len(scene.mains())} mains, {len(scene.matrices())} matrices",
    ]
    live = scene.routing.summary().live_channel_count
    lines.append(f"  {live} live channels (unmuted, fader above -inf)")

    named = [ch for ch in scene.channels() if ch.name.strip()]
    lines.append(f"  {len(named)} named channels:")
    for ch in named:
        lines.append(
            f"{BULLET}{ch.number:>2}  {ch.name:<20} {level(ch.fader_dB):>9}  "
            f"{ch.source_type.kind}"
        )

    if scene.anomalies:
        lines.append(f"  {len(scene.anomalies)} anomalies:")
        for anomaly in scene.anomalies:
            lines.append(f"{BULLET}{anomaly.code}: {anomaly.where} — {anomaly.detail}")
    return "\n".join(lines)


def channel_detail(channel) -> str:
    source = channel.source
    lines = [
        f"Channel {channel.number}: {channel.name!r}",
        f"  type        {channel.source_type.kind} "
        f"(confidence {channel.source_type.confidence:.2f}, {channel.source_type.origin})",
        f"  fader       {level(channel.fader_dB)}    muted={channel.muted}",
        f"  chain       {' -> '.join(channel.proc_chain) or '(none)'}",
        f"  tap point   {channel.tap_point}",
        f"  scene safe  {channel.scene_safe}",
        f"  DCAs        {channel.dcas or '(none)'}    mute groups {channel.mute_groups or '(none)'}",
    ]
    if source is None:
        lines.append("  source      not patched")
    else:
        lines.append(
            f"  source      {source.group}:{source.index}  gain {source.gain_dB:.1f} dB  "
            f"phantom={source.phantom}  polarity={source.polarity}"
        )
    lines.append(f"  polarity    effective={channel.effective_polarity}")

    filt = channel.filter
    lines.append(
        f"  HPF         {'on' if filt.low_cut_on else 'off'} "
        f"{filt.low_cut_hz:.0f} Hz  {filt.low_cut_slope} dB/oct"
    )

    if channel.eq.bands is None:
        lines.append(f"  EQ          {channel.eq.model} (no descriptor — bands unparsed)")
    else:
        lines.append(f"  EQ          {channel.eq.model}")
        for band in channel.eq.bands:
            lines.append(
                f"{BULLET}band {band.name:<4} {band.gain:>6.1f} dB  "
                f"{band.freq:>8.1f} Hz  Q {band.q:.2f}"
            )

    live = [s for s in channel.sends if s.on]
    lines.append(f"  sends       {len(live)} active")
    for send in live:
        lines.append(f"{BULLET}-> bus {send.dest:<3} {level(send.level_dB):>9}  {send.mode}")
    return "\n".join(lines)


def findings(items: Iterable[Any], suppressed: dict[str, str] | None = None,
             off_event: dict[str, str] | None = None,
             declared_event: str | None = None) -> str:
    items = list(items)
    if not items:
        return "No findings."

    order = {"error": 0, "warning": 1, "info": 2}
    lines: list[str] = [f"{len(items)} findings:"]
    for finding in sorted(items, key=lambda f: (order.get(f.severity, 9), _natural(f.target))):
        confidence = "" if finding.confidence >= 1.0 else f"  (confidence {finding.confidence:.2f})"
        lines.append(
            f"  [{finding.severity:<7}] {finding.rule_id:<6} {finding.target:<18} "
            f"via {finding.layer}{confidence}"
        )
        lines.append(f"      {' '.join(finding.message.split())}")

    for rule_id, by in (suppressed or {}).items():
        lines.append(f"  [suppressed] {rule_id} switched off by {by}")

    for rule_id, rule_event in (off_event or {}).items():
        lines.append(
            f"  [off-event] {rule_id} is {rule_event}-only; "
            f"profile declares event {declared_event}"
        )
    return "\n".join(lines)


def routing(summary, unclassified: Iterable[Any]) -> str:
    lines = [
        f"{summary.live_channel_count} live channels",
        f"  orphans (live, feeding nothing): {summary.orphan_channels or '(none)'}",
        f"  alt-sourced channels:            {summary.alt_sourced_channels or '(none)'}",
        f"  unpatched channels:              {summary.unpatched_channels or '(none)'}",
        f"  live but unnamed:                {summary.unnamed_but_live or '(none)'}",
    ]
    unclassified = list(unclassified)
    if unclassified:
        lines.append(f"  {len(unclassified)} could not be classified — name them more")
        lines.append("  descriptively, or declare them in knowledge/toanaz/classifier.yaml:")
        for view in unclassified:
            lines.append(f"{BULLET}{view.name!r}")
    return "\n".join(lines)


def changes(items: Iterable[Any], limit: int = 50) -> str:
    items = sorted(items, key=lambda change: _natural(change.path))
    if not items:
        return "No differences."

    lines = [f"{len(items)} differences:"]
    for change in items[:limit]:
        magnitude = f"  (delta {change.magnitude:.2f})" if change.magnitude else ""
        lines.append(f"  {change.path}: {change.before!r} -> {change.after!r}{magnitude}")
    if len(items) > limit:
        lines.append(f"  ... {len(items) - limit} more (raise --limit to see them)")
    return "\n".join(lines)
