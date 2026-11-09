"""Maths for the library diagrams: RBJ biquads, dynamics curves, polar patterns.

Pure Python, no numpy. Filters follow Robert Bristow-Johnson's Audio EQ
Cookbook; HPF/LPF slopes are Butterworth cascades. Evaluated at 48 kHz.
"""

from __future__ import annotations

import cmath
import math

FS = 48000.0

# (b0, b1, b2, a0, a1, a2)
Section = tuple[float, float, float, float, float, float]


def log_grid(lo: float = 20.0, hi: float = 20000.0, points: int = 400) -> list[float]:
    ratio = hi / lo
    return [lo * ratio ** (i / (points - 1)) for i in range(points)]


def _first_order(kind: str, f: float) -> Section:
    k = math.tan(math.pi * f / FS)
    if kind == "hpf":
        return (1.0, -1.0, 0.0, 1.0 + k, k - 1.0, 0.0)
    return (k, k, 0.0, 1.0 + k, k - 1.0, 0.0)


def _second_order(kind: str, f: float, q: float, gain_db: float = 0.0) -> Section:
    w0 = 2 * math.pi * f / FS
    cosw, sinw = math.cos(w0), math.sin(w0)
    alpha = sinw / (2 * q)
    a_lin = 10 ** (gain_db / 40)
    if kind == "hpf":
        return ((1 + cosw) / 2, -(1 + cosw), (1 + cosw) / 2, 1 + alpha, -2 * cosw, 1 - alpha)
    if kind == "lpf":
        return ((1 - cosw) / 2, 1 - cosw, (1 - cosw) / 2, 1 + alpha, -2 * cosw, 1 - alpha)
    if kind == "bell":
        return (1 + alpha * a_lin, -2 * cosw, 1 - alpha * a_lin,
                1 + alpha / a_lin, -2 * cosw, 1 - alpha / a_lin)
    if kind == "notch":
        return (1.0, -2 * cosw, 1.0, 1 + alpha, -2 * cosw, 1 - alpha)
    root = 2 * math.sqrt(a_lin) * alpha
    if kind == "low_shelf":
        return (a_lin * ((a_lin + 1) - (a_lin - 1) * cosw + root),
                2 * a_lin * ((a_lin - 1) - (a_lin + 1) * cosw),
                a_lin * ((a_lin + 1) - (a_lin - 1) * cosw - root),
                (a_lin + 1) + (a_lin - 1) * cosw + root,
                -2 * ((a_lin - 1) + (a_lin + 1) * cosw),
                (a_lin + 1) + (a_lin - 1) * cosw - root)
    if kind == "high_shelf":
        return (a_lin * ((a_lin + 1) + (a_lin - 1) * cosw + root),
                -2 * a_lin * ((a_lin - 1) + (a_lin + 1) * cosw),
                a_lin * ((a_lin + 1) + (a_lin - 1) * cosw - root),
                (a_lin + 1) - (a_lin - 1) * cosw + root,
                2 * ((a_lin - 1) - (a_lin + 1) * cosw),
                (a_lin + 1) - (a_lin - 1) * cosw - root)
    raise ValueError(f"unknown filter type {kind!r}")


def butterworth_sections(kind: str, f: float, slope: int) -> list[Section]:
    """hpf/lpf of `slope` dB/oct (6, 12, 18, 24, 48...) as biquad sections."""
    order = max(1, int(round(slope / 6)))
    sections: list[Section] = []
    for i in range(order // 2):
        q = 1.0 / (2.0 * math.sin(math.pi * (2 * i + 1) / (2 * order)))
        sections.append(_second_order(kind, f, q))
    if order % 2:
        sections.append(_first_order(kind, f))
    return sections


def filter_sections(spec: dict) -> list[Section]:
    kind = spec["type"]
    f = float(spec["f"])
    if kind in ("hpf", "lpf"):
        return butterworth_sections(kind, f, int(spec.get("slope", 12)))
    default_q = 0.707 if kind.endswith("shelf") else 1.0
    return [_second_order(kind, f, float(spec.get("q", default_q)),
                          float(spec.get("gain_db", 0.0)))]


def response_db(sections: list[Section], freqs: list[float]) -> list[float]:
    """Magnitude in dB of the cascade at each frequency."""
    out: list[float] = []
    for f in freqs:
        z1 = cmath.exp(-1j * 2 * math.pi * f / FS)
        z2 = z1 * z1
        total = 0.0
        for b0, b1, b2, a0, a1, a2 in sections:
            mag = abs((b0 + b1 * z1 + b2 * z2) / (a0 + a1 * z1 + a2 * z2))
            total += 20 * math.log10(max(mag, 1e-12))
        out.append(total)
    return out


def curve_db(filters: list[dict], freqs: list[float]) -> list[float]:
    sections = [s for spec in filters for s in filter_sections(spec)]
    return response_db(sections, freqs)


def transfer_out(curve: dict, level_db: float) -> float:
    """Output level (dB) of a compressor / expander / gate / limiter at an input level."""
    mode = curve.get("mode", "compress")
    thr = float(curve["threshold_db"])
    ratio = float(curve.get("ratio", 1.0))
    knee = float(curve.get("knee_db", 0.0))
    if mode == "limit":
        return min(level_db, thr)
    if mode == "gate":
        return level_db if level_db >= thr else level_db - float(curve.get("range_db", 80.0))
    if mode == "expand":
        return level_db if level_db >= thr else thr + (level_db - thr) * ratio
    over = level_db - thr
    if knee > 0 and abs(over) <= knee / 2:
        return level_db + (1 / ratio - 1) * (over + knee / 2) ** 2 / (2 * knee)
    return level_db if over <= 0 else thr + over / ratio


POLAR = {  # pattern -> (a, 1 - a): r = a + (1 - a) cos(theta)
    "omni": (1.0, 0.0), "subcardioid": (0.7, 0.3), "cardioid": (0.5, 0.5),
    "supercardioid": (0.37, 0.63), "hypercardioid": (0.25, 0.75), "figure8": (0.0, 1.0),
}


def polar_gain(pattern: str, theta: float) -> float:
    a, b = POLAR[pattern]
    return abs(a + b * math.cos(theta))


def envelope_sim(attack_ms: float, release_ms: float, hold_ms: float = 0.0,
                 threshold_db: float = -20.0, ratio: float = 4.0):
    """(times_ms, input_db, gain_reduction_db) for a level burst through a compressor."""
    pre, burst = 10.0, max(4 * attack_ms, 50.0)
    total = pre + burst + hold_ms + max(3 * release_ms, 100.0)
    step = total / 599
    times = [i * step for i in range(600)]
    level = [0.0 if pre <= t < pre + burst else -40.0 for t in times]
    gr, current, held = [], 0.0, 0.0
    for t, lv in zip(times, level):
        target = (1 - 1 / ratio) * max(lv - threshold_db, 0.0)
        if target > current:
            tau, held = attack_ms, 0.0
        else:
            held += step
            tau = release_ms if held > hold_ms else 1e12
        current += (target - current) * (1 - math.exp(-step / tau)) if tau < 1e11 else 0.0
        gr.append(current)
    return times, level, gr
