"""The dev diagram renderer: maths sanity, SVG output, error handling."""

import importlib.util
import math
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
