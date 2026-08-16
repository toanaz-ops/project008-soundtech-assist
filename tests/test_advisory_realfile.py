"""The full advisory contract on the two shipped sample files.

Any rule change that shifts real-file behaviour must edit this table in
the same commit, with the probe evidence in the diff. Generated from a
live run on 2026-08-17 -- regenerate with:
python - <<'EOF'
import os; os.environ["WING_DISABLE_LLM"] = "1"
from wing_parser import WingScene
for f in sorted(WingScene.load("user-files/example-Vu.snap").advisory.run(),
                key=lambda f: (f.rule_id, f.target)):
    print(f'    ("{f.rule_id}", "{f.target}", "{f.severity}"),')
EOF
"""
import pytest

from wing_parser import WingScene

EXPECTED_VU = [
    ("E6", "ch.11", "warning"),
    ("G10", "matrix.5", "info"),
    ("G10", "matrix.6", "info"),
    ("G10", "matrix.7", "info"),
    ("G10", "matrix.8", "info"),
    ("G8", "ch.1.send.8", "warning"),
    ("G8", "ch.10.send.8", "warning"),
    ("G8", "ch.12.send.8", "warning"),
    ("G8", "ch.2.send.8", "warning"),
    ("G8", "ch.3.send.8", "warning"),
    ("G8", "ch.4.send.7", "warning"),
    ("G8", "ch.4.send.8", "warning"),
    ("G8", "ch.5.send.8", "warning"),
    ("G8", "ch.7.send.7", "warning"),
    ("G8", "ch.7.send.8", "warning"),
    ("G8", "ch.8.send.7", "warning"),
    ("G8", "ch.8.send.8", "warning"),
    ("G9", "bus.7", "warning"),
    ("PB1", "ch.16", "info"),
    ("PB2", "ch.21", "info"),
    ("PB4", "ch.22", "info"),
    ("PB5", "ch.13", "info"),
    # Spot-checked against raw ae_data before commit:
    #   - G9 "bus.7": ae_data["bus"]["7"] has name "SIDEFILL" and
    #     dyn.on == False -- the only monitor-role output in the file
    #     reading dyn.on False, so this is the one G9 target.
    #   - G8 "ch.8.send.8": ae_data["ch"]["8"]["send"]["8"] reads
    #     {"on": True, "mode": "POST", ...} -- a live POST send into a
    #     monitor-role bus, which is exactly what G8 flags.
    #   - PB1 "ch.16": ae_data["ch"]["16"]["in"]["set"]["inv"] is False
    #     and ae_data["ch"]["16"]["in"]["conn"]["grp"] is "OFF" (no
    #     SourceData resolves), so effective_polarity is False --
    #     "Snare Bot" (drums.snare.bottom) fires PB1.
    #   - G10 "matrix.5"/"matrix.6"/"matrix.7"/"matrix.8": no channel
    #     name anywhere in ae_data["ch"] contains "amb" (case-
    #     insensitive) -- there is no utility.ambient-classified
    #     channel in this file at all, so bus.receives_ambient is False
    #     for every monitor.iem matrix (5 "IEM MC", 6 "IEM CA SI 1",
    #     7 "IEM CA SI 2", 8 "IEM3 BAKUP"), and all four fire at info.
]


def test_the_real_file_advisory_contract(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    scene = WingScene.load(vu_path)
    got = sorted((f.rule_id, f.target, f.severity) for f in scene.advisory.run())
    assert got == sorted(EXPECTED_VU)


def test_the_factory_scene_stays_silent(factory_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    assert WingScene.load(factory_path).advisory.run() == []


def test_the_small_profile_still_suppresses_g8(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    # Uses the real in-repo knowledge dir: shows/small.yaml supersedes G8.
    from wing_parser import config
    monkeypatch.delenv(config.ENV_VAR, raising=False)
    scene = WingScene.load(vu_path)
    found = scene.advisory.run("small")
    assert not any(f.rule_id == "G8" for f in found)
    assert scene.advisory.suppressed("small") == {"G8": "show.small.post-monitors-are-deliberate"}
