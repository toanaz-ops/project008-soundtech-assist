"""`ui_steps` diagram: a schematic console panel with numbered callouts.

Drawing toolkit (Svg, colours, wrap) is passed in by library_diagrams so the
two modules never import each other at load time.
"""

from __future__ import annotations

from types import SimpleNamespace

PANEL = (30, 64, 930, 372)  # left, top, right, bottom
STYLES = ("button", "display", "fader", "knob", "grid")
CELLS = ("tick", "x", "blank")
MAX_STEPS = 6
LEGEND_TOP, LEGEND_BOTTOM = 394, 512
NOTE = "Schematic - not a screenshot"


def _kit(kit):
    if kit is not None:
        return kit
    import library_diagrams as ld
    return SimpleNamespace(Svg=ld.Svg, C=ld._C, wrap=ld._wrap)


REGION_KEYS = ("id", "x", "y", "w", "h", "style")
GRID_KEYS = ("rows", "cols", "cells")
STEP_KEYS = ("n", "region", "text")


def _need(obj: dict, keys, what: str) -> None:
    missing = [k for k in keys if k not in obj]
    if missing:
        raise ValueError(f"{what}: missing key(s) {', '.join(missing)}")


def _validate(item: dict) -> None:
    _need(item, ("regions", "steps"), "ui_steps item")
    regions, steps = item["regions"], item["steps"]
    if not 1 <= len(steps) <= MAX_STEPS:
        raise ValueError(f"steps must have 1..{MAX_STEPS} items, got {len(steps)}")
    ids = set()
    for r in regions:
        _need(r, REGION_KEYS, f"region {r.get('id', '?')}")
        for key in ("x", "y", "w", "h"):
            if not 0 <= r[key] <= 100:
                raise ValueError(f"region {r['id']}: {key} outside 0..100")
        if r["x"] + r["w"] > 100 or r["y"] + r["h"] > 100:
            raise ValueError(f"region {r['id']}: extends past the panel (x+w or y+h > 100)")
        if r["style"] not in STYLES:
            raise ValueError(f"region {r['id']}: unknown style {r['style']!r}")
        if r["style"] == "grid":
            _need(r, GRID_KEYS, f"grid region {r['id']}")
            rows, cols, cells = r["rows"], r["cols"], r["cells"]
            if len(cells) != len(rows) or any(len(c) != len(cols) for c in cells):
                raise ValueError(f"region {r['id']}: cells shape must match rows x cols")
            if any(v not in CELLS for row in cells for v in row):
                raise ValueError(f"region {r['id']}: cell values must be tick, x or blank")
        ids.add(r["id"])
    seen = set()
    for s in steps:
        _need(s, STEP_KEYS, f"step {s.get('n', '?')}")
        if s["n"] in seen:
            raise ValueError(f"duplicate step number {s['n']}")
        seen.add(s["n"])
        if s["region"] not in ids:
            raise ValueError(f"step {s['n']}: unknown region {s['region']!r}")


def _box(r):
    left, top, right, bottom = PANEL
    pw, ph = right - left, bottom - top
    return (left + r["x"] / 100 * pw, top + r["y"] / 100 * ph,
            r["w"] / 100 * pw, r["h"] / 100 * ph)


def _rect(svg, x, y, w, h, fill, stroke, rx=4):
    svg.add(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
            f'fill="{fill}" stroke="{stroke}"/>')


def _button(svg, c, r, x, y, w, h):
    lit = r.get("lit")
    _rect(svg, x, y, w, h, c["accent"] if lit else c["raise_"],
          c["accent"] if lit else c["border"], rx=6)
    svg.text(x + w / 2, y + h / 2 + 5, r["label"], size=13,
             fill=c["background"] if lit else c["text"], anchor="middle", weight="bold")


def _display(svg, c, r, x, y, w, h):
    _rect(svg, x, y, w, h, c["well"], c["border"])
    svg.text(x + 8, y + 17, r["label"], size=12, fill=c["dim"], weight="bold")
    for i, line in enumerate(r.get("lines", [])):
        ly = y + 38 + i * 18
        if ly > y + h - 4:
            break
        svg.add(f'<text x="{x + 8:.1f}" y="{ly:.1f}" font-size="13" font-family="monospace" '
                f'fill="{c["text"]}">{_esc(line)}</text>')


def _fader(svg, c, r, x, y, w, h):
    _rect(svg, x, y, w, h, c["panel"], c["border"])
    n = max(int(r.get("count", 8)), 1)
    top, bottom = y + 22, y + h - 8
    slot = w / n
    for i in range(n):
        cx = x + slot * (i + 0.5)
        svg.line(cx, top, cx, bottom, c["border"], 3)
        cap_y = top + (bottom - top) * (0.25 + 0.1 * (i % 3))
        _rect(svg, cx - min(slot * 0.32, 9), cap_y - 5, min(slot * 0.64, 18), 10,
              c["raise_"], c["dim"], rx=2)
    svg.text(x + 6, y + 15, r["label"], size=12, fill=c["dim"], weight="bold")


def _knob(svg, c, r, x, y, w, h):
    rad = max(min(w, h - 16) / 2, 4)
    cx, cy = x + w / 2, y + rad
    svg.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rad:.1f}" fill="{c["raise_"]}" '
            f'stroke="{c["border"]}" stroke-width="2"/>')
    svg.line(cx, cy, cx + rad * 0.55, cy - rad * 0.55, c["text"], 3)
    svg.text(cx, y + 2 * rad + 14, r["label"], size=12, fill=c["dim"], anchor="middle")


def _grid(svg, c, r, x, y, w, h):
    _rect(svg, x, y, w, h, c["well"], c["border"])
    svg.text(x + 8, y + 17, r["label"], size=12, fill=c["dim"], weight="bold")
    rows, cols, cells = r["rows"], r["cols"], r["cells"]
    label_w = min(max(max((len(s) for s in rows), default=4) * 7.5 + 12, 40), w * 0.4)
    gx, gy = x + label_w, y + 26
    cw = (w - label_w) / max(len(cols), 1)
    rh = (h - 30) / (len(rows) + 1)
    for j, col in enumerate(cols):
        svg.text(gx + cw * (j + 0.5), gy + rh * 0.65, col, size=12, fill=c["dim"], anchor="middle")
    for i, row in enumerate(rows):
        ry = gy + rh * (i + 1)
        svg.line(x + 4, ry, x + w - 4, ry, c["grid"])
        svg.text(x + 8, ry + rh * 0.65, row, size=12, fill=c["text"])
        for j, val in enumerate(cells[i]):
            cx, cy = gx + cw * (j + 0.5), ry + rh / 2
            if val == "tick":
                svg.poly([(cx - 7, cy), (cx - 2, cy + 6), (cx + 8, cy - 6)], c["ok"], 3)
            elif val == "x":
                svg.line(cx - 6, cy - 6, cx + 6, cy + 6, c["danger"], 3)
                svg.line(cx - 6, cy + 6, cx + 6, cy - 6, c["danger"], 3)


def _esc(s):
    from xml.sax.saxutils import escape
    return escape(str(s))


DRAW = {"button": _button, "display": _display, "fader": _fader, "knob": _knob, "grid": _grid}


def _legend(svg, c, steps, wrap):
    cols = 2 if len(steps) > 3 else 1
    col_w = 450 if cols == 2 else 900
    width = int((col_w - 40) / 7.2)
    per_col = -(-len(steps) // cols)
    for k in range(cols):
        y = LEGEND_TOP + 8
        for s in steps[k * per_col:(k + 1) * per_col]:
            x = 30 + k * col_w
            lines = wrap(s["text"], width)
            svg.add(f'<circle cx="{x + 11}" cy="{y + 2}" r="11" fill="{c["accent"]}"/>')
            svg.text(x + 11, y + 7, s["n"], size=13, fill=c["background"], anchor="middle",
                     weight="bold")
            for j, line in enumerate(lines):
                svg.text(x + 32, y + 7 + j * 17, line, size=14, fill=c["text"])
            y += max(len(lines), 1) * 17 + 12
        if y - 12 > LEGEND_BOTTOM:
            raise ValueError("step text too long: legend would overflow the diagram")


def ui_steps(item: dict, kit=None) -> str:
    kit = _kit(kit)
    c = kit.C
    _validate(item)
    svg = kit.Svg(item["title"])
    left, top, right, bottom = PANEL
    _rect(svg, left, top, right - left, bottom - top, c["panel"], c["border"], rx=10)
    if item.get("panel"):
        svg.text(left + 12, top + 18, item["panel"], size=12, fill=c["faded"], weight="bold")
    boxes = {}
    for r in item["regions"]:
        boxes[r["id"]] = _box(r)
        DRAW[r["style"]](svg, c, r, *boxes[r["id"]])
    ordered = sorted(item["steps"], key=lambda s: s["n"])
    total: dict[str, int] = {}
    for s in ordered:
        total[s["region"]] = total.get(s["region"], 0) + 1
    used: dict[str, int] = {}
    for s in ordered:
        x, y, w, _h = boxes[s["region"]]
        k = used.get(s["region"], 0)
        used[s["region"]] = k + 1
        # ascending n reads left to right: the highest n sits at the right edge
        cx, cy = x + w - 4 - (total[s["region"]] - 1 - k) * 26, y + 2
        svg.add(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="11" fill="{c["accent"]}" '
                f'stroke="{c["background"]}" stroke-width="2"/>')
        svg.text(cx, cy + 5, s["n"], size=13, fill=c["background"], anchor="middle", weight="bold")
    _legend(svg, c, ordered, kit.wrap)
    svg.text(930, 530, NOTE, size=11, fill=c["faded"], anchor="end")
    return svg.render()
