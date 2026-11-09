"""Gate and compressor stages. Written only on the GATE / COMP models (AM-10)."""

from __future__ import annotations

from wing_parser.automix.interp import MISSING, Ctx, mid, nearest, weakest

SPEECH_RATIO_CAP = 4.0  # Doctor PC5 flags speech compression above 4:1


def _model_ok(ctx: Ctx, strip, leaf: str, wanted: str) -> bool:
    model = ctx.read(f"ch.{strip.number}.{leaf}.mdl")
    if model == wanted:
        return True
    ctx.skip(strip.target, f"{leaf} model {'missing' if model is MISSING else model} is not {wanted}")
    return False


def gate(ctx: Ctx, kb, strips, genre: str) -> list:
    if not kb.genres["genres"][genre]["gates"]:
        return []
    out, rows, fixed = [], kb.dynamics["gate"]["kinds"], kb.dynamics["gate"]["assumptions"]
    for s in strips:
        rec = rows.get(s.fam)
        if rec is None or s.bottom or not _model_ok(ctx, s, "gate", "GATE"):
            continue
        base = f"ch.{s.number}.gate."
        kw = dict(stage="gate", who=s.target, src=tuple(rec["src"]), conf=rec["confidence"],
                  why=f"{s.fam}: gate timing and range from {', '.join(rec['src'])}")
        thr_kw = dict(kw, src=tuple(fixed["src"]), conf=fixed["confidence"],
                      why=f"{s.fam}: threshold assumed {fixed['thr']} dB (no meters offline)")
        out += filter(None, (
            ctx.change(base + "on", True, label="Gate on", mode="switch", **kw),
            ctx.change(base + "thr", fixed["thr"], label="Gate threshold", **thr_kw),
            ctx.change(base + "range", mid(rec["range"]), label="Gate range", **kw),
            ctx.change(base + "att", int(mid(rec["att"]) + 0.5), label="Gate attack", digits=0, **kw),  # 1 ms step (AM-36)
            ctx.change(base + "hld", mid(rec["hld"]), label="Gate hold", **kw),
            ctx.change(base + "rel", mid(rec["rel"]), label="Gate release", **kw),
        ))
    return out


def _comp_target(kb, strip, genre: str) -> tuple:
    """(ratio, gain_reduction_db, confidence, sources) for one strip."""
    rec = kb.dynamics["comp"]["kinds"][strip.fam]
    ratio, gr, conf, src = mid(rec["ratio"]), mid(rec["gr"]), rec["confidence"], tuple(rec["src"])
    delta = kb.dynamics["genre_deltas"].get(genre)
    if delta and (not delta.get("kinds") or strip.fam in delta["kinds"]):
        gr = mid(delta["gr_range"]) if "gr_range" in delta else gr
        gr += delta.get("gr_add", 0)
        ratio = mid(delta["ratio_range"]) if "ratio_range" in delta else ratio
        ratio = min(max(ratio, delta.get("ratio_min", 0)), delta.get("ratio_max", 1e9))
        conf = weakest(conf, delta["confidence"])
    if strip.raw.startswith("speech."):
        ratio = min(ratio, SPEECH_RATIO_CAP)
    return nearest(kb.bounds["wing"]["ratio_list"], ratio), max(gr, 0.5), conf, src


def comp(ctx: Ctx, kb, strips, genre: str) -> list:
    out, rules = [], kb.dynamics["comp"]
    fixed, bounds = rules["assumptions"], kb.bounds["comp"]
    for s in strips:
        if s.bottom or s.fam not in rules["kinds"] or not _model_ok(ctx, s, "dyn", "COMP"):
            continue
        rec = rules["kinds"][s.fam]
        ratio, gr, conf, src = _comp_target(kb, s, genre)
        thr = fixed["peak_est_dbfs"] - gr * ratio / (ratio - 1)
        thr = min(max(thr, bounds["thr_db"][0]), bounds["thr_db"][1])
        base = f"ch.{s.number}.dyn."
        kw = dict(stage="comp", who=s.target, src=src, conf=conf,
                  why=f"{s.fam}: about {gr:g} dB gain reduction at {ratio:g}:1 ({genre})")
        fix = dict(kw, src=tuple(fixed["src"]), conf=weakest(conf, fixed["confidence"]),
                   why=f"{s.fam}: threshold derived from an assumed {fixed['peak_est_dbfs']} dBFS peak (no meters offline)")
        out += filter(None, (
            ctx.change(base + "on", True, label="Compressor on", mode="switch", **kw),
            ctx.change(base + "thr", thr, label="Compressor threshold", **fix),
            ctx.change(base + "ratio", ratio, label="Compressor ratio", mode="switch", **kw),
            ctx.change(base + "knee", fixed["knee"], label="Compressor knee", mode="switch", digits=0, **fix),
            ctx.change(base + "att", mid(rec["att"]), label="Compressor attack", **kw),
            ctx.change(base + "rel", mid(rec["rel"]), label="Compressor release", **kw),
            ctx.change(base + "gain", min(max(gr / 2, bounds["gain_db"][0]), bounds["gain_db"][1]),
                       label="Compressor makeup gain", **fix),
        ))
    return out
