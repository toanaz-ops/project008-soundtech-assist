"""HPF and EQ stages. EQ is written only on the STD model (AM-10)."""

from __future__ import annotations

import math

from wing_parser.automix.interp import MISSING, Ctx, geo_mid, weakest

OCTAVE_GAP = 0.33  # a masking cut closer than this (octaves) to an own cut is redundant


def _window(kb, strip):
    windows = kb.eq["doctor_windows"]
    rec = windows.get(strip.raw) or windows.get(strip.fam)
    return (tuple(rec["hz"]), rec) if rec else (None, None)


def hpf(ctx: Ctx, kb, strips) -> list:
    out = []
    default = kb.eq["defaults"]["hpf"]
    for s in strips:
        rec = kb.eq["kinds"].get(s.eq_kind, {}).get("hpf")
        if not rec:
            continue
        window, wrec = _window(kb, s)
        src = tuple(rec["src"]) + tuple(default["src"]) + (tuple(wrec["src"]) if wrec else ())
        conf = weakest(rec["confidence"], default["confidence"])
        why = f"{s.eq_kind}: high-pass near {rec['hz']:g} Hz removes rumble and bleed"
        if wrec:
            why += f" (kept inside the Doctor {wrec['rule']} window)"
        base, kw = f"ch.{s.number}.flt.", dict(stage="hpf", who=s.target, why=why, src=src, conf=conf)
        out += filter(None, (
            ctx.change(base + "lc", True, label="HPF on", mode="switch", **kw),
            ctx.change(base + "lcf", rec["hz"], label="HPF corner", mode="geo", window=window, **kw),
            ctx.change(base + "lcs", default["slope"], label="HPF slope", mode="switch", optional=True, **kw),
        ))
    return out


def _plan(kb, strip, present, tilt) -> tuple:
    """(bands, shelf): bands is [(band_no, hz, db, q, why, src, conf)]."""
    d, rec = kb.eq["defaults"], kb.eq["kinds"][strip.eq_kind]
    scale, presence = tilt.get("boost_scale", 1.0), tilt.get("presence_db", 0.0)
    cuts = [(r, "cut") for r in rec.get("cuts", [])[:2]]
    for pair in kb.masking["pairs"]:
        if pair["yield"] == strip.eq_kind and pair["owner"] in present and len(cuts) < 2:
            hz = geo_mid(pair["hz"])
            if all(abs(math.log2(hz / geo_mid(r["hz"]))) > OCTAVE_GAP for r, _ in cuts):
                cuts.append((pair, "mask"))
    boosts = [(r, "boost") for r in rec.get("boosts", [])[:2]]
    bands = []
    for group, first in ((cuts, 1), (boosts, 3)):
        for index, (r, kind) in enumerate(group):
            dflt = d["boost" if kind == "boost" else "cut"]
            db, q = r.get("db", dflt["db"]), r.get("q", dflt["q"])
            if kind == "boost":
                lifted = geo_mid(r["hz"]) >= tilt.get("presence_from_hz", 1e9)
                db = db * scale + (presence if lifted else 0.0)
            conf = r["confidence"] if "db" in r else weakest(r["confidence"], dflt["confidence"])
            verb = "boost" if kind == "boost" else "cut"
            bands.append((first + index, geo_mid(r["hz"]), db, q,
                          f"{strip.eq_kind}: {r['why']} ({verb})", tuple(r["src"]), conf))
    shelf = rec.get("shelf")
    return bands, shelf


def eq(ctx: Ctx, kb, strips, genre: str) -> list:
    out, present = [], {s.eq_kind for s in strips}
    tilt = kb.genres["genres"][genre]["eq_tilt"]
    for s in strips:
        if s.bottom or s.eq_kind not in kb.eq["kinds"]:
            continue
        rec = kb.eq["kinds"][s.eq_kind]
        if not (rec.get("cuts") or rec.get("boosts") or rec.get("shelf")):
            continue
        model = ctx.read(f"ch.{s.number}.eq.mdl")
        if model != "STD":
            ctx.skip(s.target, "EQ model MISSING" if model is MISSING else f"EQ model {model} is not STD")
            continue
        bands, shelf = _plan(kb, s, present, tilt)
        base, changes, gains = f"ch.{s.number}.eq.", [], []
        for number, hz, db, q, why, src, conf in bands:
            kw = dict(stage="eq", who=s.target, why=why, src=src, conf=conf)
            gains.append(db)
            changes += [ctx.change(f"{base}{number}g", db, label=f"EQ band {number} gain", **kw),
                        ctx.change(f"{base}{number}f", hz, label=f"EQ band {number} frequency", mode="geo", **kw),
                        ctx.change(f"{base}{number}q", q, label=f"EQ band {number} Q", digits=2, **kw)]
        if shelf and ctx.read(base + "heq") == "SHV":
            dflt = kb.eq["defaults"]["shelf"]
            db = shelf.get("db", dflt["db"]) * tilt.get("boost_scale", 1.0)
            conf = shelf["confidence"] if "db" in shelf else weakest(shelf["confidence"], dflt["confidence"])
            kw = dict(stage="eq", who=s.target, src=tuple(shelf["src"]), conf=conf,
                      why=f"{s.eq_kind}: {shelf['why']} (high shelf)")
            gains.append(db)
            changes += [ctx.change(base + "hg", db, label="EQ high shelf gain", **kw),
                        ctx.change(base + "hf", geo_mid(shelf["hz"]), label="EQ high shelf frequency", mode="geo", **kw),
                        ctx.change(base + "hq", shelf.get("q", dflt["q"]), label="EQ high shelf Q", digits=2, **kw)]
        if any(g != 0 for g in gains):
            changes.append(ctx.change(base + "on", True, stage="eq", who=s.target, label="EQ on", mode="switch",
                                      why=f"{s.eq_kind}: the proposed bands need the EQ switched on",
                                      src=(), conf="eng_default"))
        out += [c for c in changes if c]
    return out
