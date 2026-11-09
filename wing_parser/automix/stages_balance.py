"""Fader balance with a headroom guard, and the WING automix group insert."""

from __future__ import annotations

import math

from wing_parser.automix.interp import MISSING, Ctx, is_number, is_on, lerp, weakest
from wing_parser.automix.options import Suggestion

INF_FLOOR = -90.0  # at or below this a fader is treated as -inf (the sentinel is -144)
MAX_TRIM_DB = 24.0


def _main_on(channel: dict) -> bool:
    return any(isinstance(m, dict) and is_on(m.get("on")) for m in (channel.get("main") or {}).values())


def main_sum_db(document: dict, nominal_dbfs: float) -> float:
    """Estimated sum of every channel that feeds a main, each at nominal level
    plus its fader, as dBFS. -inf when nothing feeds a main."""
    total = 0.0
    for channel in document.get("ae_data", {}).get("ch", {}).values():
        fader = channel.get("fdr")
        if is_number(fader) and fader > INF_FLOOR and _main_on(channel):
            total += 10 ** ((nominal_dbfs + fader) / 10)
    return 10 * math.log10(total) if total > 0 else float("-inf")


def _anchor(ctx: Ctx, kb, strips) -> float:
    rule = kb.balance["anchor"]
    lead = next((s for s in strips if s.lead), None)
    value = ctx.read(f"ch.{lead.number}.fdr") if lead else MISSING
    if is_number(value) and value > INF_FLOOR:
        return min(max(value, rule["lead_clamp_db"][0]), rule["lead_clamp_db"][1])
    return rule["default_db"]


def _trim(ctx: Ctx, kb, values: dict) -> float:
    """Uniform dB to take off every proposed fader so the main sum stays under the ceiling.

    `values` are the already strength-interpolated fader targets. The guard
    never asks for less headroom than the scene had to begin with (so strength
    0 moves nothing), and never more than the ceiling (AM-35)."""
    rule = kb.balance["headroom"]
    nominal = rule["nominal_dbfs"]
    fixed = proposed = current = 0.0
    for key, channel in ctx.document.get("ae_data", {}).get("ch", {}).items():
        if not _main_on(channel):
            continue
        number = int(key)
        now = channel.get("fdr")
        if is_number(now) and now > INF_FLOOR:
            current += 10 ** ((nominal + now) / 10)
        if number in values:
            proposed += 10 ** ((nominal + values[number]) / 10)
        elif is_number(now) and now > INF_FLOOR:
            fixed += 10 ** ((nominal + now) / 10)
    limit = max(10 ** (rule["ceiling_dbfs"] / 10), current)
    if proposed == 0 or fixed + proposed <= limit:
        return 0.0
    room = limit - fixed
    needed = MAX_TRIM_DB if room <= 0 else 10 * math.log10(proposed / room)
    return min(math.ceil(needed * 10) / 10 + 0.1, MAX_TRIM_DB)  # +0.1: fader rounding margin


def fader(ctx: Ctx, kb, strips, options) -> tuple:
    genre = kb.balance["genres"][options.genre]
    venue = kb.balance["venue"].get(options.venue)
    anchor, values, picked = _anchor(ctx, kb, strips), {}, []
    for s in strips:
        offset = genre["offsets"].get(s.fam)
        if offset is None:
            continue
        before = ctx.read(f"ch.{s.number}.fdr")
        if before is MISSING:
            ctx.skip(s.target, f"leaf ch.{s.number}.fdr is missing from the scene")
        elif not is_number(before) or before <= INF_FLOOR:
            ctx.skip(s.target, "fader is at -inf: left alone")
        else:
            shift = venue["delta_db"] if venue and s.fam in venue["kinds"] else 0.0
            target = ctx.bounds.clamp(f"ch.{s.number}.fdr", anchor + offset + shift, lead=s.lead)
            values[s.number] = lerp(before, target, ctx.strength)  # interpolate first, trim after
            picked.append((s, offset, shift))
    trim = _trim(ctx, kb, values)
    out = []
    for s, offset, shift in picked:
        why = f"{s.fam}: {offset:+g} dB against the lead-vocal anchor of {anchor:g} dB"
        why += f", {shift:+g} dB small-room stage volume" if shift else ""
        why += f", {-trim:g} dB headroom trim" if trim else ""
        conf = weakest(genre["confidence"], kb.balance["anchor"]["confidence"], venue["confidence"] if shift else "high",
                       kb.balance["headroom"]["ceiling_confidence"] if trim else "high")
        src = tuple(genre["src"]) + tuple(kb.balance["anchor"]["src"])
        out.append(ctx.change(f"ch.{s.number}.fdr", values[s.number] - trim, stage="fader", who=s.target,
                              label="Fader", why=why, src=src, conf=conf, lead=s.lead, strength=1.0))
    return [c for c in out if c], trim


def inserts(ctx: Ctx, kb, strips, genre: str) -> tuple:
    if genre != "speech":
        return [], []
    rule, out = kb.balance["inserts"], []
    for s in strips:
        if not s.raw.startswith("speech."):
            continue
        n = s.number
        if ctx.read(f"ch.{n}.postins.ins") != "NONE":
            continue
        if is_on(ctx.read(f"ch.{n}.gate.on")):
            ctx.skip(s.target, "gate is on; a gate and automix on one channel conflict (Doctor E6)")
            continue
        weight = rule["weight_db"].get(s.raw, rule["weight_db"]["default"])
        kw = dict(stage="inserts", who=s.target, src=tuple(rule["src"]), conf=rule["confidence"],
                  why=f"{s.raw}: join WING automix group X so open microphones share gain")
        base = f"ch.{n}.postins."
        out += filter(None, (
            ctx.change(base + "mode", rule["mode"], label="Insert mode", mode="switch", **kw),
            ctx.change(base + "on", True, label="Insert on", mode="switch", **kw),
            ctx.change(base + "w", weight, label="Automix weight", **kw),
        ))
    hints = []
    if out and ctx.read("cfg.amix.x") is not MISSING and not is_on(ctx.read("cfg.amix.x")):
        hints.append(Suggestion("inserts", "cfg.amix.x", "Automix group X is off in the scene "
                                "configuration; switch it on at the desk so AUTO_X takes effect.",
                                tuple(rule["src"])))
    return out, hints
