"""Dev tool: render knowledge/library/diagrams.yaml to SVG + PNG.

    python scripts/library_diagrams.py [--manifest PATH] [--out-root PATH]
                                       [--only ENTRY] [--no-png]

Writes <out-root>/media/<entry>/<file>.svg (pure-Python SVG, colours from the
app theme tokens) and converts it to a 960x540 .png with PySide6 QtSvg.
The conversion is dev-time only; the app just shows the PNG. Output is
deterministic, so re-running is idempotent.
"""

from __future__ import annotations

import argparse
import os
import importlib.util
import math
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import yaml

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import library_diagram_dsp as dsp  # noqa: E402

W, H = 960, 540
PLOT = (90, 80, 920, 450)  # left, top, right, bottom
FREQ_TICKS = [(20, "20"), (50, "50"), (100, "100"), (200, "200"), (500, "500"),
              (1000, "1k"), (2000, "2k"), (5000, "5k"), (10000, "10k"), (20000, "20k")]


def _tokens() -> dict[str, int]:
    """COLOURS from the theme, loaded by path so Qt is not imported."""
    spec = importlib.util.spec_from_file_location(
        "_theme_tokens", ROOT / "wing_parser" / "ui" / "theme" / "tokens.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.COLOURS


_C = {k: f"#{v:06x}" for k, v in _tokens().items()}
SERIES = [_C["accent"], _C["settled"], _C["ok"], _C["danger"], _C["warn"], _C["cooling"]]


class Svg:
    def __init__(self, title: str):
        self.parts: list[str] = [
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
            f'viewBox="0 0 {W} {H}" font-family="sans-serif">',
            f'<rect width="{W}" height="{H}" fill="{_C["background"]}"/>']
        self.text(W / 2, 40, title, size=22, fill=_C["text"], anchor="middle", weight="bold")

    def add(self, markup: str) -> None:
        self.parts.append(markup)

    def line(self, x1, y1, x2, y2, stroke, width=1, dash=None) -> None:
        extra = f' stroke-dasharray="{dash}"' if dash else ""
        self.add(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
                 f'stroke="{stroke}" stroke-width="{width}"{extra}/>')

    def text(self, x, y, s, size=14, fill=None, anchor="start", weight="normal") -> None:
        self.add(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" '
                 f'fill="{fill or _C["dim"]}" text-anchor="{anchor}" '
                 f'font-weight="{weight}">{escape(str(s))}</text>')

    def poly(self, pts, stroke, width=2.5) -> None:
        data = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        self.add(f'<polyline points="{data}" fill="none" stroke="{stroke}" '
                 f'stroke-width="{width}" stroke-linejoin="round" stroke-linecap="round"/>')

    def legend(self, labels: list[str], x=None, y=None) -> None:
        x = PLOT[2] - 190 if x is None else x
        y = PLOT[1] + 14 if y is None else y
        self.add(f'<rect x="{x - 12}" y="{y - 16}" width="200" height="{len(labels) * 24 + 8}" '
                 f'rx="4" fill="{_C["panel"]}" fill-opacity="0.9" stroke="{_C["border"]}"/>')
        for i, label in enumerate(labels):
            row = y + i * 24
            self.line(x, row - 4, x + 26, row - 4, SERIES[i % len(SERIES)], 3)
            self.text(x + 34, row, label, size=14, fill=_C["text"])

    def frame(self, box=PLOT) -> None:
        left, top, right, bottom = box
        self.add(f'<rect x="{left}" y="{top}" width="{right - left}" height="{bottom - top}" '
                 f'fill="{_C["well"]}" stroke="{_C["border"]}"/>')

    def render(self) -> str:
        return "\n".join(self.parts + ["</svg>"]) + "\n"


def _lin(v, lo, hi, a, b) -> float:
    return a + (v - lo) / (hi - lo) * (b - a)


def _log_x(f: float, box=PLOT) -> float:
    return _lin(math.log10(f), math.log10(20), math.log10(20000), box[0], box[2])


def _nice_step(span: float, target: int = 6) -> float:
    raw = span / target
    mag = 10 ** math.floor(math.log10(raw))
    for mult in (1, 2, 5, 10):
        if raw <= mult * mag:
            return mult * mag
    return 10 * mag


def _ticks(lo: float, hi: float, step: float | None = None) -> list[float]:
    step = step or _nice_step(hi - lo)
    first = math.ceil(lo / step - 1e-9) * step
    out, v = [], first
    while v <= hi + 1e-9:
        out.append(round(v, 6))
        v += step
    return out


def _fmt(v: float) -> str:
    return str(int(v)) if float(v).is_integer() else f"{v:g}"


def _axes(svg: Svg, x_lo, x_hi, y_lo, y_hi, x_label="", y_label="", *, x_log=False,
          x_ticks=None, box=PLOT):
    """Draw frame, grid, ticks and labels; return (map_x, map_y)."""
    left, top, right, bottom = box
    svg.frame(box)
    if x_log:
        xs = x_ticks or FREQ_TICKS
        mx = lambda f: _lin(math.log10(f), math.log10(x_lo), math.log10(x_hi),  # noqa: E731
                            left, right)
    else:
        xs = [(v, _fmt(v)) for v in (x_ticks or _ticks(x_lo, x_hi))]
        mx = lambda v: _lin(v, x_lo, x_hi, left, right)  # noqa: E731
    my = lambda v: _lin(v, y_lo, y_hi, bottom, top)  # noqa: E731
    for value, label in xs:
        x = mx(value)
        svg.line(x, top, x, bottom, _C["grid"])
        svg.text(x, bottom + 22, label, anchor="middle")
    for value in _ticks(min(y_lo, y_hi), max(y_lo, y_hi)):
        y = my(value)
        svg.line(left, y, right, y, _C["border"] if value == 0 else _C["grid"])
        svg.text(left - 10, y + 5, _fmt(value), anchor="end")
    if x_label:
        svg.text((left + right) / 2, bottom + 50, x_label, size=15, anchor="middle")
    if y_label:
        svg.add(f'<text transform="translate(26,{(top + bottom) / 2:.1f}) rotate(-90)" '
                f'font-size="15" fill="{_C["dim"]}" text-anchor="middle">{escape(y_label)}</text>')
    return mx, my


def _clipped(svg: Svg, pts, colour, box=PLOT) -> None:
    """Polyline cut at the plot's top/bottom edges (crossings interpolated)."""
    top, bottom = box[1], box[3]
    runs: list[list[tuple[float, float]]] = []
    run: list[tuple[float, float]] = []
    prev = None
    for x, y in pts:
        inside = top <= y <= bottom
        if prev is not None and inside != (top <= prev[1] <= bottom):
            edge = top if (y < top or prev[1] < top) else bottom
            ex = prev[0] + (x - prev[0]) * (edge - prev[1]) / (y - prev[1])
            if inside:
                run = [(ex, edge)]
            else:
                run.append((ex, edge))
                runs.append(run)
                run = []
        if inside:
            run.append((x, y))
        prev = (x, y)
    if run:
        runs.append(run)
    for piece in runs:
        if len(piece) > 1:
            svg.poly(piece, colour)


def eq_curve(item: dict) -> str:
    svg = Svg(item["title"])
    lo, hi = item.get("y_range", [-24, 12])
    mx, my = _axes(svg, 20, 20000, lo, hi, "Frequency (Hz)", "Level (dB)", x_log=True)
    freqs = dsp.log_grid()
    for i, curve in enumerate(item["curves"]):
        db = dsp.curve_db(curve["filters"], freqs)
        _clipped(svg, [(mx(f), my(v)) for f, v in zip(freqs, db)], SERIES[i % len(SERIES)])
    svg.legend([c["label"] for c in item["curves"]])
    return svg.render()


def band_chart(item: dict) -> str:
    svg = Svg(item["title"])
    bands = item["bands"]
    svg.frame()
    for value, label in FREQ_TICKS:
        x = _log_x(value)
        svg.line(x, PLOT[1], x, PLOT[3], _C["grid"])
        svg.text(x, PLOT[3] + 22, label, anchor="middle")
    svg.text((PLOT[0] + PLOT[2]) / 2, PLOT[3] + 50, "Frequency (Hz)", size=15, anchor="middle")
    row = (PLOT[3] - PLOT[1]) / len(bands)
    for i, band in enumerate(bands):
        x1, x2 = _log_x(max(band["lo"], 20)), _log_x(min(band["hi"], 20000))
        y = PLOT[1] + i * row + row * 0.18
        colour = SERIES[i % len(SERIES)]
        svg.add(f'<rect x="{x1:.1f}" y="{y:.1f}" width="{x2 - x1:.1f}" height="{row * 0.64:.1f}" '
                f'rx="3" fill="{colour}" fill-opacity="0.85"/>')
        need = len(band["label"]) * 8 + 16
        inside = x2 - x1 >= need
        ty = y + row * 0.64 / 2 + 5
        if inside:
            svg.text(x1 + 8, ty, band["label"], size=14, fill=_C["background"], weight="bold")
        elif x2 + need <= W - 10:
            svg.text(x2 + 8, ty, band["label"], size=14, fill=_C["text"], weight="bold")
        else:
            svg.text(x1 - 8, ty, band["label"], size=14, fill=_C["text"], weight="bold", anchor="end")
    return svg.render()


def range_chart(item: dict) -> str:
    """Horizontal bars, one row per label, spanning lo..hi on a linear value axis."""
    svg = Svg(item["title"])
    box = (250, 80, 920, 450)
    rows = item["rows"]
    values = [v for r in rows for v in (r["lo"], r["hi"])]
    x_lo, x_hi = item.get("x_range") or [min(values), max(values)]
    unit = item.get("unit", "")
    svg.frame(box)
    for v in _ticks(x_lo, x_hi):
        x = _lin(v, x_lo, x_hi, box[0], box[2])
        svg.line(x, box[1], x, box[3], _C["border"] if v == 0 else _C["grid"])
        svg.text(x, box[3] + 22, _fmt(v), anchor="middle")
    svg.text((box[0] + box[2]) / 2, box[3] + 50, item.get("x_label", ""), size=15, anchor="middle")
    row_h = (box[3] - box[1]) / len(rows)
    for i, row in enumerate(rows):
        a, b = sorted((row["lo"], row["hi"]))
        x1 = _lin(a, x_lo, x_hi, box[0], box[2])
        x2 = max(_lin(b, x_lo, x_hi, box[0], box[2]), x1 + 3)
        y = box[1] + i * row_h + row_h * 0.2
        svg.text(box[0] - 12, y + row_h * 0.3 + 5, row["label"], anchor="end")
        svg.add(f'<rect x="{x1:.1f}" y="{y:.1f}" width="{x2 - x1:.1f}" height="{row_h * 0.6:.1f}" '
                f'rx="3" fill="{SERIES[i % len(SERIES)]}" fill-opacity="0.85"/>')
        text = _fmt(a) if a == b else f"{_fmt(a)} to {_fmt(b)}"
        label, ty = f"{text}{unit}", y + row_h * 0.3 + 5
        need = len(label) * 8 + 12
        if x2 + need <= W - 10:
            svg.text(x2 + 8, ty, label, size=13, weight="bold")
        elif x2 - x1 >= need:
            svg.text(x2 - 8, ty, label, size=13, weight="bold", anchor="end", fill=_C["background"])
        else:
            svg.text(x1 - 8, ty, label, size=13, weight="bold", anchor="end")
    return svg.render()


def transfer_curve(item: dict) -> str:
    svg = Svg(item["title"])
    box = (150, 80, 650, 450)  # square-ish plot
    mx, my = _axes(svg, -60, 0, -60, 0, "Input level (dB)", "Output level (dB)", box=box)
    svg.line(mx(-60), my(-60), mx(0), my(0), _C["faded"], 1.5, "6 4")
    levels = [-60 + i * 0.5 for i in range(121)]
    for i, curve in enumerate(item["curves"]):
        pts = [(mx(v), my(dsp.transfer_out(curve, v))) for v in levels]
        _clipped(svg, pts, SERIES[i % len(SERIES)], box)
    svg.legend([c["label"] for c in item["curves"]], x=690, y=110)
    svg.text(690, 110 + len(item["curves"]) * 24 + 24, "dashed: 1:1 (no processing)", size=13)
    return svg.render()


def envelope(item: dict) -> str:
    attack, release = float(item["attack_ms"]), float(item["release_ms"])
    hold = float(item.get("hold_ms", 0))
    thr, ratio = float(item.get("threshold_db", -20)), float(item.get("ratio", 4))
    times, level, gr = dsp.envelope_sim(attack, release, hold, thr, ratio)
    svg = Svg(item["title"])
    top_box, bot_box = (90, 80, 920, 260), (90, 300, 920, 450)
    t_end = times[-1]
    mx, my = _axes(svg, 0, t_end, -45, 5, "", "Input (dB)", box=top_box)
    svg.add(f'<line x1="{top_box[0]}" y1="{my(thr):.1f}" x2="{top_box[2]}" y2="{my(thr):.1f}" '
            f'stroke="{_C["warn"]}" stroke-dasharray="6 4"/>')
    svg.text(top_box[2] - 6, my(thr) - 6, f"threshold {_fmt(thr)} dB", anchor="end", fill=_C["warn"])
    svg.poly([(mx(t), my(v)) for t, v in zip(times, level)], SERIES[1])
    max_gr = max(max(gr) * 1.15, 1.0)
    mx2, my2 = _axes(svg, 0, t_end, max_gr, 0, "Time (ms)", "Gain reduction (dB)", box=bot_box)
    svg.poly([(mx2(t), my2(v)) for t, v in zip(times, gr)], SERIES[0])
    info = f"attack {_fmt(attack)} ms  |  release {_fmt(release)} ms  |  ratio {_fmt(ratio)}:1"
    if hold:
        info += f"  |  hold {_fmt(hold)} ms"
    svg.text(W / 2, 66, info, size=14, anchor="middle")
    return svg.render()


def polar_pattern(item: dict) -> str:
    svg = Svg(item["title"])
    cx, cy, radius = 340, 295, 195
    for frac in (0.25, 0.5, 0.75, 1.0):
        svg.add(f'<circle cx="{cx}" cy="{cy}" r="{radius * frac:.1f}" fill="none" '
                f'stroke="{_C["grid"] if frac < 1 else _C["border"]}"/>')
    for deg in range(0, 360, 30):
        a = math.radians(deg)
        svg.line(cx, cy, cx + radius * math.sin(a), cy - radius * math.cos(a), _C["grid"])
    for deg in (0, 90, 180, 270):
        a = math.radians(deg)
        svg.text(cx + (radius + 18) * math.sin(a), cy - (radius + 18) * math.cos(a) + 5,
                 f"{deg}", anchor="middle")
    for i, name in enumerate(item["patterns"]):
        pts = []
        for step in range(361):
            theta = math.radians(step)
            r = radius * dsp.polar_gain(name, theta)
            pts.append((cx + r * math.sin(theta), cy - r * math.cos(theta)))
        svg.poly(pts, SERIES[i % len(SERIES)], 2.5)
    svg.legend([p.replace("figure8", "figure-8") for p in item["patterns"]], x=640, y=140)
    svg.text(640, 140 + len(item["patterns"]) * 24 + 26, "0 deg = on-axis (front)", size=13)
    return svg.render()


def _wrap(label: str, width: int) -> list[str]:
    lines, cur = [], ""
    for word in label.split():
        if cur and len(cur) + 1 + len(word) > width:
            lines.append(cur)
            cur = word
        else:
            cur = f"{cur} {word}".strip()
    return lines + [cur] if cur else lines


def signal_flow(item: dict) -> str:
    svg = Svg(item["title"])
    nodes = item["nodes"]
    n = len(nodes)
    gap = 34
    box_w = (W - 80 - gap * (n - 1)) / n
    width_chars = max(int(box_w / 9), 6)
    y, box_h = 200, 110
    for i, node in enumerate(nodes):
        x = 40 + i * (box_w + gap)
        svg.add(f'<rect x="{x:.1f}" y="{y}" width="{box_w:.1f}" height="{box_h}" rx="8" '
                f'fill="{_C["raise_"]}" stroke="{SERIES[i % len(SERIES)]}" stroke-width="2"/>')
        lines = _wrap(node["label"], width_chars)
        top = y + box_h / 2 - (len(lines) - 1) * 10 + 5
        for j, line in enumerate(lines):
            svg.text(x + box_w / 2, top + j * 20, line, size=16, fill=_C["text"],
                     anchor="middle", weight="bold")
        for j, line in enumerate(_wrap(node.get("note", ""), max(int(box_w / 7.5), 8))):
            svg.text(x + box_w / 2, y + box_h + 28 + j * 18, line, size=13, anchor="middle")
        if i < n - 1:
            ax = x + box_w + 4
            svg.line(ax, y + box_h / 2, ax + gap - 12, y + box_h / 2, _C["dim"], 2)
            svg.add(f'<polygon points="{ax + gap - 4:.1f},{y + box_h / 2:.1f} '
                    f'{ax + gap - 14:.1f},{y + box_h / 2 - 6:.1f} '
                    f'{ax + gap - 14:.1f},{y + box_h / 2 + 6:.1f}" fill="{_C["dim"]}"/>')
    return svg.render()


def _decade_axis(lo: float, hi: float):
    """Log axis fitted to non-audio data: whole decades plus 2/5 minor ticks."""
    if lo <= 0:
        raise ValueError("x_log needs positive x values")
    d_lo, d_hi = math.floor(math.log10(lo)), math.ceil(math.log10(hi))
    if d_hi == d_lo:
        d_hi += 1
    mults = (1, 2, 5) if d_hi - d_lo <= 3 else (1,)
    ticks = [(m * 10.0 ** d, _fmt(m * 10.0 ** d)) for d in range(d_lo, d_hi) for m in mults]
    ticks.append((10.0 ** d_hi, _fmt(10.0 ** d_hi)))
    return 10.0 ** d_lo, 10.0 ** d_hi, ticks


def xy_plot(item: dict) -> str:
    svg = Svg(item["title"])
    pts_all = [p for s in item["series"] for p in s["points"]]
    xs, ys = [p[0] for p in pts_all], [p[1] for p in pts_all]
    x_log = bool(item.get("x_log"))
    if x_log and min(xs) >= 20 and max(xs) <= 20000:
        mx_axes = _axes(svg, 20, 20000, min(ys), max(ys), item.get("x_label", ""),
                        item.get("y_label", ""), x_log=True)
    elif x_log:
        x_lo, x_hi, ticks = _decade_axis(min(xs), max(xs))
        pad = (max(ys) - min(ys)) * 0.08 or 1
        mx_axes = _axes(svg, x_lo, x_hi, min(ys) - pad, max(ys) + pad, item.get("x_label", ""),
                        item.get("y_label", ""), x_log=True, x_ticks=ticks)
    else:
        x_lo, x_hi = min(xs), max(xs)
        pad = (max(ys) - min(ys)) * 0.08 or 1
        y_lo, y_hi = min(ys) - pad, max(ys) + pad
        mx_axes = _axes(svg, x_lo, x_hi, y_lo, y_hi, item.get("x_label", ""),
                        item.get("y_label", ""))
    mx, my = mx_axes
    for i, series in enumerate(item["series"]):
        _clipped(svg, [(mx(x), my(y)) for x, y in series["points"]], SERIES[i % len(SERIES)])
    svg.legend([s["label"] for s in item["series"]])
    return svg.render()


KINDS = {"eq_curve": eq_curve, "band_chart": band_chart, "transfer_curve": transfer_curve,
         "range_chart": range_chart, "envelope": envelope, "polar_pattern": polar_pattern, "signal_flow": signal_flow,
         "xy_plot": xy_plot}


def render_item(item: dict) -> str:
    kind = item.get("kind")
    if kind not in KINDS:
        raise ValueError(f"diagram {item.get('entry')}/{item.get('file')}: unknown kind {kind!r}")
    try:
        return KINDS[kind](item)
    except KeyError as exc:
        raise ValueError(f"diagram {item.get('entry')}/{item.get('file')}: "
                         f"missing key {exc} for kind {kind}") from exc


def svg_to_png(svg_path: Path, png_path: Path) -> None:
    """Rasterise with QtSvg (dev-time only)."""
    from PySide6.QtGui import QColor, QImage, QPainter
    from PySide6.QtSvg import QSvgRenderer
    from PySide6.QtWidgets import QApplication
    # QApplication, not QGuiApplication: under pytest a bare QGuiApplication
    # created here makes the later `qt_app` fixture's widget tests abort.
    app = QApplication.instance() or QApplication([])  # noqa: F841 - keeps fonts alive
    # The offscreen platform has no system fonts: load the app's vendored sans
    # and let the SVG's generic "sans-serif" resolve to it.
    from PySide6.QtGui import QFont, QFontDatabase
    font_id = QFontDatabase.addApplicationFont(
        str(ROOT / "wing_parser" / "ui" / "resources" / "fonts" / "IBMPlexSans-Regular.ttf"))
    families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
    if families:
        QFont.insertSubstitution("sans-serif", families[0])
    renderer = QSvgRenderer(str(svg_path))
    image = QImage(W, H, QImage.Format.Format_ARGB32)
    image.fill(QColor(_C["background"]))
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    image.save(str(png_path), "PNG")


def run(manifest: Path, out_root: Path, only: str | None = None, png: bool = True) -> int:
    with open(manifest, encoding="utf-8") as handle:
        items = (yaml.safe_load(handle) or {}).get("diagrams", [])
    count = 0
    for item in items:
        if only and item.get("entry") != only:
            continue
        markup = render_item(item)
        folder = out_root / "media" / item["entry"]
        folder.mkdir(parents=True, exist_ok=True)
        svg_path = folder / f"{item['file']}.svg"
        with open(svg_path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(markup)
        if png:
            svg_to_png(svg_path, folder / f"{item['file']}.png")
        count += 1
        print(f"rendered {item['entry']}/{item['file']}")
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--manifest", type=Path, default=ROOT / "knowledge/library/diagrams.yaml")
    parser.add_argument("--out-root", type=Path, default=None)
    parser.add_argument("--only", default=None, metavar="ENTRY")
    parser.add_argument("--no-png", action="store_true")
    args = parser.parse_args(argv)
    out_root = args.out_root or args.manifest.parent
    try:
        count = run(args.manifest, out_root, args.only, not args.no_png)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"{count} diagram(s)")
    return 0


if __name__ == "__main__":
    # Headless only when run as a script; inside pytest the shared
    # QApplication's platform is the test run's choice, not ours.
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    sys.exit(main())
