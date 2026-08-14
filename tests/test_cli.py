import json
import re

import pytest

from wing_parser.classifier.resolve import Classifier
from wing_parser.cli.__main__ import main
from wing_parser.cli.render import level


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")


def test_level_formats_silence_and_real_values():
    assert level(float("-inf")) == "-inf"
    assert level(-7.9) == "-7.9 dB"
    assert level(0.0) == "0.0 dB"


def test_analyze_prints_an_overview(vu_path, capsys):
    assert main(["analyze", str(vu_path)]) == 0
    out = capsys.readouterr().out
    assert "snapshot.11" in out
    assert "M8 MC" in out
    assert "40 channels" in out


def test_analyze_reports_a_directory_without_a_traceback(tmp_path, capsys):
    assert main(["analyze", str(tmp_path)]) == 1
    assert str(tmp_path) in capsys.readouterr().err


def test_analyze_reports_a_non_object_top_level_without_a_traceback(tmp_path, capsys):
    bad = tmp_path / "bad.snap"
    bad.write_text("[1, 2]", encoding="utf-8")
    assert main(["analyze", str(bad)]) == 1
    assert str(bad) in capsys.readouterr().err


def test_channel_prints_detail(vu_path, capsys):
    assert main(["channel", str(vu_path), "8"]) == 0
    out = capsys.readouterr().out
    assert "M8 MC" in out
    assert "-7.9 dB" in out
    assert "POST_FDR" in out
    assert "speech.mc" in out


def test_channel_reports_an_unknown_number_without_a_traceback(vu_path, capsys):
    assert main(["channel", str(vu_path), "99"]) == 1
    assert "99" in capsys.readouterr().err


def test_doctor_lists_the_findings(vu_path, capsys):
    assert main(["doctor", str(vu_path)]) == 0
    out = capsys.readouterr().out
    assert "17 findings" in out
    assert "G8" in out
    assert "G7" in out
    assert "MON VOX" in out


def test_doctor_shows_the_deciding_layer(vu_path, capsys):
    main(["doctor", str(vu_path)])
    assert "base" in capsys.readouterr().out


def test_doctor_orders_findings_naturally_not_lexicographically(vu_path, capsys):
    main(["doctor", str(vu_path)])
    out = capsys.readouterr().out
    targets = re.findall(r"^\s*\[\S+\s*\]\s+\S+\s+(\S+)\s+via base", out, re.MULTILINE)
    assert targets == [
        "bus.7", "bus.8", "bus.9", "bus.10",
        "ch.1.send.8", "ch.2.send.8", "ch.3.send.8",
        "ch.4.send.7", "ch.4.send.8", "ch.5.send.8",
        "ch.7.send.7", "ch.7.send.8", "ch.8.send.7", "ch.8.send.8",
        "ch.10.send.8", "ch.11", "ch.12.send.8",
    ]


def test_routing_prints_the_summary(vu_path, capsys):
    assert main(["routing", str(vu_path)]) == 0
    out = capsys.readouterr().out
    assert "3 live channels" in out
    unpatched_line = next(line for line in out.splitlines() if "unpatched channels" in line)
    assert len(re.findall(r"\d+", unpatched_line)) == 23


def test_routing_lists_unclassified_channels(vu_path, capsys):
    main(["routing", str(vu_path)])
    assert "My Lap" in capsys.readouterr().out


def test_diff_reports_a_changed_fader(vu_path, tmp_path, capsys):
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"]["8"]["fdr"] = -3.0
    other = tmp_path / "other.snap"
    other.write_text(json.dumps(doc), encoding="utf-8")

    assert main(["diff", str(vu_path), str(other)]) == 0
    assert "ch.8.fader_dB" in capsys.readouterr().out


def test_json_output_is_machine_readable(vu_path, capsys):
    assert main(["doctor", str(vu_path), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert isinstance(payload, list)
    assert {"rule_id", "layer", "severity", "target", "message"} <= set(payload[0])


def test_feedback_appends_a_verdict(vu_path, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    code = main([
        "feedback", "G8:ch.8.send.8",
        "--verdict", "false-positive",
        "--note", "shared IEM rig",
        "--scene", str(vu_path),
    ])
    assert code == 0
    assert (tmp_path / "feedback.jsonl").exists()
    assert "false-positive" in (tmp_path / "feedback.jsonl").read_text(encoding="utf-8")


def test_feedback_rejects_an_unknown_finding_id(vu_path, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    assert main(["feedback", "ZZ:ch.1", "--verdict", "correct", "--scene", str(vu_path)]) == 1
    assert "ZZ:ch.1" in capsys.readouterr().err


def test_missing_file_reports_cleanly(capsys):
    assert main(["analyze", "no-such-file.snap"]) == 1
    assert "no-such-file.snap" in capsys.readouterr().err


FLUSH_CASES = [
    pytest.param("analyze", lambda vu, tmp: ["analyze", str(vu)], 1, id="analyze"),
    pytest.param("channel", lambda vu, tmp: ["channel", str(vu), "8"], 1, id="channel"),
    pytest.param("doctor", lambda vu, tmp: ["doctor", str(vu)], 1, id="doctor"),
    pytest.param("routing", lambda vu, tmp: ["routing", str(vu)], 1, id="routing"),
    pytest.param(
        "feedback",
        lambda vu, tmp: [
            "feedback", "G8:ch.8.send.8", "--verdict", "correct", "--scene", str(vu),
        ],
        1,
        id="feedback",
    ),
    pytest.param("diff", lambda vu, tmp: ["diff", str(vu), str(vu)], 2, id="diff"),
]


@pytest.mark.parametrize("name, build_argv, expected", FLUSH_CASES)
def test_flush_is_called_by_every_command_that_resolves_names(
    name, build_argv, expected, vu_path, tmp_path, capsys, monkeypatch
):
    # A spy on Classifier.flush, not on what it writes (Task 15 covers that
    # already) — the point is to catch a future edit that silently deletes
    # one of the five call sites in commands.py.
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    calls: list[Classifier] = []
    monkeypatch.setattr(Classifier, "flush", lambda self: calls.append(self))

    assert main(build_argv(vu_path, tmp_path)) == 0
    assert len(calls) == expected, (
        f"{name}: expected {expected} flush() call(s), got {len(calls)}"
    )
