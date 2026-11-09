"""FX slot parameters and the channel sends that feed the FX buses.

Only keys that already exist are patched: loading a model into an empty
slot cannot be a Patch (the pointer never creates keys), so a missing
role becomes a Suggestion (AM-14).
"""

from __future__ import annotations

from wing_parser.automix.interp import MISSING, Ctx, mid, weakest
from wing_parser.automix.options import Suggestion

OFF_DB = -144.0
_PICK = {"lo": lambda r: r[0], "mid": mid, "hi": lambda r: r[1]}


def fx(ctx: Ctx, kb, buses, options) -> tuple:
    genre, table = options.genre, kb.fx
    changes, hints = [], []
    have = {b.role for b in buses}
    models = {}
    for mdl, role in table["model_roles"].items():
        models.setdefault(role, mdl)
    for role in kb.genres["genres"][genre]["fx_roles"]:
        if role not in have:
            hints.append(Suggestion(
                "fx", "fx", f"Load a {models[role]} into an empty FX slot 1-8, insert it on a free bus "
                f"and run automix again to tune it (genre {genre} wants a {role.replace('_', ' ')}).",
                tuple(table["bus_assign"][role]["src"])))
    reverb, delay = table["reverb"].get(genre), table["delay"].get(genre)
    done = set()
    for b in buses:
        if b.slot in done:
            continue
        done.add(b.slot)
        base, who = f"fx.{b.slot}.", f"fx.{b.slot}"
        if b.role == "delay" and delay:
            ms = delay["slap_ms"] if "slap_ms" in delay else 60000.0 / options.bpm * delay["beats"]
            leaves = [("time", ms, "Delay time", 1), ("feed", delay["feed_pct"], "Delay feedback", 1),
                      ("lc", delay["locut_hz"], "Delay low cut", 1), ("hc", delay["hicut_hz"], "Delay high cut", 1)]
            rec, why = delay, f"{genre} delay {'slapback' if 'slap_ms' in delay else 'at ' + format(options.bpm, 'g') + ' BPM'}"
        elif b.role != "delay" and reverb:
            how = _PICK[table["role_pick"][b.role]]
            leaves = [("dcy", how(reverb["decay_s"]), "Reverb decay", 2),
                      ("pdel", how(reverb["predelay_ms"]), "Reverb pre-delay", 1),
                      ("lc", reverb["locut_hz"], "Reverb low cut", 1), ("hc", reverb["hicut_hz"], "Reverb high cut", 1)]
            rec, why = reverb, f"{genre} {b.role.replace('_', ' ')} ({b.mdl})"
        else:
            continue
        conf = weakest(rec["confidence"], table["role_pick"]["confidence"] if "dcy" == leaves[0][0] else "high")
        for leaf, value, label, digits in leaves:
            changes.append(ctx.change(base + leaf, value, stage="fx", who=who, label=label, digits=digits,
                                      why=why, src=tuple(rec["src"]), conf=conf))
    return [c for c in changes if c], hints


def sends(ctx: Ctx, kb, strips, buses, genre: str) -> list:
    wet, out = kb.fx["wetness"][genre], []
    for b in buses:
        assign = kb.fx["bus_assign"][b.role]
        for s in strips:
            row, shift = kb.fx["send_levels"].get(s.fam), assign["kinds"].get(s.fam)
            if s.bottom or row is None or shift is None:
                continue
            base = f"ch.{s.number}.send.{b.bus}."
            if ctx.read(base + "lvl") is MISSING:
                ctx.skip(s.target, f"leaf {base}lvl is missing from the scene")
                continue
            level = row[assign["level"]]
            off = wet.get("dry") or level == "off"
            target = OFF_DB if off else min(mid(level) + shift + wet[assign["level"]], 0.0)
            conf = weakest(row["confidence"], assign["confidence"], wet["confidence"])
            kw = dict(stage="sends", who=s.target, src=tuple(row["src"]) + tuple(assign["src"]), conf=conf,
                      why=f"{s.fam} to the {b.role.replace('_', ' ')} bus: "
                          + ("dry" if off else f"{target:g} dB post-fader"))
            out.append(ctx.change(base + "lvl", target, label=f"Send {b.bus} level",
                                  mode="switch" if off else "lin", **kw))
            if not off:
                out.append(ctx.change(base + "on", True, label=f"Send {b.bus} on", mode="switch", **kw))
                if ctx.read(base + "mode") == "PRE":
                    out.append(ctx.change(base + "mode", "POST", label=f"Send {b.bus} mode", mode="switch",
                                          **dict(kw, why=f"{s.fam}: FX sends are post-fader so the effect follows the fader")))
    return [c for c in out if c]
