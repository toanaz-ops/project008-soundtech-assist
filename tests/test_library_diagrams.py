"""The dev diagram renderer: maths sanity, SVG output, error handling."""

import importlib.util
import math
import re
import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"


@pytest.fixture(scope="module")
def tool():
    sys.path.insert(0, str(SCRIPTS))
    spec = importlib.util.spec_from_file_location("library_diagrams", SCRIPTS / "library_diagrams.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def manifest(tmp_path, items):
    path = tmp_path / "diagrams.yaml"
    path.write_text(yaml.safe_dump({"diagrams": items}), encoding="utf-8")
    return path


EQ = {"entry": "eq-test", "file": "hpf", "kind": "eq_curve", "title": "HPF", "y_range": [-36, 6],
      "curves": [{"label": "12", "filters": [{"type": "hpf", "f": 100, "slope": 12}]}]}


def test_eq_curve_renders_svg_to_the_media_folder(tool, tmp_path):
    out = tmp_path / "out"
    assert tool.run(manifest(tmp_path, [EQ]), out, png=False) == 1
    text = (out / "media" / "eq-test" / "hpf.svg").read_text(encoding="utf-8")
    assert text.startswith("<svg") and "<polyline" in text and "HPF" in text


def test_rendering_is_idempotent(tool, tmp_path):
    out = tmp_path / "out"
    tool.run(manifest(tmp_path, [EQ]), out, png=False)
    first = (out / "media" / "eq-test" / "hpf.svg").read_bytes()
    tool.run(manifest(tmp_path, [EQ]), out, png=False)
    assert (out / "media" / "eq-test" / "hpf.svg").read_bytes() == first


def test_only_filters_by_entry(tool, tmp_path):
    other = dict(EQ, entry="other")
    assert tool.run(manifest(tmp_path, [EQ, other]), tmp_path / "o", only="other", png=False) == 1


def test_unknown_kind_names_the_item(tool, tmp_path, capsys):
    bad = {"entry": "x", "file": "y", "kind": "pie_chart", "title": "t"}
    assert tool.main(["--manifest", str(manifest(tmp_path, [bad])), "--no-png"]) == 1
    assert "x/y" in capsys.readouterr().err


def test_butterworth_hpf_is_minus_3_db_at_cutoff(tool):
    dsp = tool.dsp
    for slope in (12, 18, 24):
        db = dsp.curve_db([{"type": "hpf", "f": 1000, "slope": slope}], [1000.0])[0]
        assert db == pytest.approx(-3.01, abs=0.1)
    assert dsp.curve_db([{"type": "hpf", "f": 1000, "slope": 24}], [100.0])[0] < -70


def test_bell_peak_gain_and_filter_sums(tool):
    dsp = tool.dsp
    bell = {"type": "bell", "f": 1000, "gain_db": 6, "q": 1.4}
    assert dsp.curve_db([bell], [1000.0])[0] == pytest.approx(6.0, abs=0.05)
    assert dsp.curve_db([bell, bell], [1000.0])[0] == pytest.approx(12.0, abs=0.1)
    shelf = {"type": "low_shelf", "f": 200, "gain_db": -6}
    assert dsp.curve_db([shelf], [20.0])[0] == pytest.approx(-6.0, abs=0.1)


def test_transfer_and_polar_maths(tool):
    dsp = tool.dsp
    assert dsp.transfer_out({"threshold_db": -20, "ratio": 4}, -10) == pytest.approx(-17.5)
    assert dsp.transfer_out({"threshold_db": -20, "ratio": 4}, -30) == -30
    assert dsp.polar_gain("cardioid", math.pi) == pytest.approx(0.0, abs=1e-9)
    assert dsp.polar_gain("figure8", math.pi / 2) == pytest.approx(0.0, abs=1e-9)


@pytest.mark.parametrize("item", [
    {"kind": "band_chart", "title": "b", "bands": [{"label": "Low", "lo": 20, "hi": 250}]},
    {"kind": "transfer_curve", "title": "t",
     "curves": [{"label": "g", "mode": "gate", "threshold_db": -40, "range_db": 20}]},
    {"kind": "envelope", "title": "e", "attack_ms": 10, "release_ms": 100, "ratio": 4},
    {"kind": "polar_pattern", "title": "p", "patterns": ["cardioid"]},
    {"kind": "signal_flow", "title": "s", "nodes": [{"label": "Mic", "note": "XLR"}, {"label": "Pre"}]},
    {"kind": "xy_plot", "title": "x", "x_label": "a", "y_label": "b",
     "series": [{"label": "s", "points": [[0, 0], [1, 2]]}]},
], ids=lambda i: i["kind"])
def test_every_kind_renders(tool, item):
    markup = tool.render_item(dict(item, entry="e", file="f"))
    assert markup.startswith("<svg") and markup.rstrip().endswith("</svg>")


def test_png_conversion(tool, tmp_path):
    pytest.importorskip("PySide6.QtSvg")
    out = tmp_path / "out"
    tool.run(manifest(tmp_path, [EQ]), out, png=True)
    png = out / "media" / "eq-test" / "hpf.png"
    assert png.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def _xy(tool, x_values):
    pts = [[x, math.log10(x)] for x in x_values]
    return tool.xy_plot({"title": "t", "x_label": "x", "y_label": "y", "x_log": True,
                         "series": [{"label": "s", "points": pts}]})


def test_xy_log_axis_fits_non_frequency_data_with_decade_ticks(tool):
    svg = _xy(tool, [1, 2, 4, 8, 16])
    assert ">1<" in svg and ">10<" in svg and ">100<" in svg
    assert ">20k<" not in svg and ">200<" not in svg


def test_xy_log_axis_keeps_audio_ticks_inside_20_to_20k(tool):
    svg = _xy(tool, [50, 500, 5000])
    assert ">20k<" in svg and ">1k<" in svg


def test_range_chart_draws_one_bar_per_row(tool):
    svg = tool.range_chart({"title": "r", "x_label": "s", "unit": " s",
                            "rows": [{"label": "a", "lo": 0.8, "hi": 1.8},
                                     {"label": "b", "lo": 0.0, "hi": 0.6}]})
    assert svg.count("<rect") >= 2 and "0.8 to 1.8 s" in svg


def _ui(**over):
    item = {"entry": "e", "file": "f", "kind": "ui_steps", "title": "How to", "panel": "SD10",
            "regions": [
                {"id": "scope", "label": "Scope", "x": 5, "y": 10, "w": 40, "h": 50, "style": "grid",
                 "rows": ["In", "Aux"], "cols": ["Gain", "EQ"], "cells": [["x", "tick"], ["blank", "tick"]]},
                {"id": "fire", "label": "FIRE", "x": 60, "y": 70, "w": 10, "h": 12,
                 "style": "button", "lit": True}],
            "steps": [{"n": 1, "region": "scope", "text": "Open <Scope>"},
                      {"n": 2, "region": "fire", "text": "Press FIRE"}]}
    item.update(over)
    return item


def test_ui_steps_renders_markers_note_and_grid_colours(tool):
    svg = tool.render_item(_ui())
    assert svg.startswith("<svg") and "Schematic - not a screenshot" in svg
    assert "&lt;Scope&gt;" in svg
    for n in (1, 2):
        # one marker in the panel and one in the legend
        assert svg.count(f">{n}<") == 2
    assert tool._C["ok"] in svg and tool._C["danger"] in svg


@pytest.mark.parametrize("over", [
    {"steps": [{"n": 1, "region": "nope", "text": "t"}]},
    {"steps": [{"n": i, "region": "fire", "text": "t"} for i in range(1, 8)]},
    {"steps": [{"n": 1, "region": "fire", "text": "a"}, {"n": 1, "region": "fire", "text": "b"}]},
    {"regions": [{"id": "r", "label": "r", "x": -1, "y": 0, "w": 10, "h": 10, "style": "button"}],
     "steps": []},
    {"regions": [{"id": "r", "label": "r", "x": 95, "y": 0, "w": 10, "h": 10, "style": "button"}],
     "steps": []},
    {"regions": [{"id": "r", "label": "r", "x": 0, "y": 0, "w": 10, "h": 10, "style": "slider"}],
     "steps": []},
    {"regions": [{"id": "r", "label": "r", "x": 0, "y": 0, "w": 50, "h": 50, "style": "grid",
                  "rows": ["a"], "cols": ["b", "c"], "cells": [["tick"]]}], "steps": []},
    {"regions": [{"id": "r", "label": "r", "x": 0, "y": 0, "w": 50, "h": 50, "style": "grid",
                  "rows": ["a"], "cols": ["b"], "cells": [["maybe"]]}], "steps": []},
    {"steps": [{"n": i, "region": "fire", "text": "word " * 80} for i in range(1, 7)]},
    {"steps": []},
    {"regions": [{"id": "r", "label": "r", "x": 0, "y": 0, "w": 10, "style": "button"}], "steps": []},
    {"regions": [{"id": "r", "label": "r", "x": 0, "y": 0, "w": 50, "h": 50, "style": "grid",
                  "rows": ["a"], "cols": ["b"]}], "steps": []},
    {"steps": [{"n": 1, "region": "fire"}]},
], ids=["unknown-region", "too-many-steps", "duplicate-n", "negative-coord", "overflow-coord",
        "unknown-style", "grid-shape", "grid-cell-value", "legend-overflow", "empty-steps",
        "region-missing-key", "grid-missing-key", "step-missing-key"])
def test_ui_steps_validation_errors(tool, over):
    with pytest.raises(ValueError):
        tool.render_item(_ui(**over))


def test_markers_sharing_a_region_read_left_to_right(tool):
    item = _ui(steps=[{"n": 1, "region": "fire", "text": "a"}, {"n": 2, "region": "fire", "text": "b"},
                      {"n": 3, "region": "fire", "text": "c"}])
    svg = tool.render_item(item)
    xs = [float(m) for m in re.findall(r'<text x="([\d.]+)"[^>]*>[123]</text>', svg)]
    panel = xs[:3]  # panel markers come before the legend entries
    assert panel == sorted(panel)
