import json
import re

import pytest
import yaml

from wing_parser.classifier.resolve import Classifier
from wing_parser.cli.__main__ import main
from wing_parser.cli.render import changes, level
from wing_parser.query.diff import Change


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
    assert "14 findings" in out
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
        "bus.7",
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


def test_changes_orders_numbered_sends_naturally_not_lexicographically():
    # render.findings() already got a _natural sort key to fix this same
    # class of bug; render.changes() kept sorting its diff paths
    # lexicographically, so send 16 printed before send 2. Reuse the same
    # key here too.
    items = [
        Change(path="ch.1.send.16", before=0.0, after=-3.0, magnitude=3.0),
        Change(path="ch.1.send.2", before=0.0, after=-3.0, magnitude=3.0),
        Change(path="ch.1.send.1", before=0.0, after=-3.0, magnitude=3.0),
    ]
    out = changes(items)
    assert [line.split(":", 1)[0].strip() for line in out.splitlines()[1:]] == [
        "ch.1.send.1", "ch.1.send.2", "ch.1.send.16",
    ]


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


def test_doctor_reports_a_typo_d_supersedes_id_without_a_traceback(
    vu_path, tmp_path, capsys, monkeypatch
):
    # scene.advisory.run() sits outside every CLI handler's try/except;
    # a hand-edited principles.yaml with a typo'd `supersedes` id used to
    # reach the user as a traceback instead of `error: ...` on stderr.
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    (tmp_path / "principles.yaml").write_text(
        "principles:\n"
        "  - id: toanaz.typo\n"
        "    principle: typo'd rule id\n"
        "    hardness: hard\n"
        "    supersedes: [G88]\n"
        "    rationale: field practice\n"
        "    source: ToanAZ\n"
        "    enabled: true\n",
        encoding="utf-8",
    )
    assert main(["doctor", str(vu_path)]) == 1
    assert "G88" in capsys.readouterr().err


def test_feedback_reports_a_yaml_syntax_error_without_a_traceback(
    vu_path, tmp_path, capsys, monkeypatch
):
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    (tmp_path / "principles.yaml").write_text(
        "principles:\n  - id: [unterminated\n", encoding="utf-8"
    )
    assert main(
        ["feedback", "G8:ch.8.send.8", "--verdict", "correct", "--scene", str(vu_path)]
    ) == 1
    assert "principles.yaml" in capsys.readouterr().err


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


def _write_small_profile(directory):
    shows = directory / "shows"
    shows.mkdir(parents=True, exist_ok=True)
    (shows / "small.yaml").write_text(
        yaml.safe_dump(
            {"rules": [{"id": "show.small", "title": "Small show",
                        "severity": "info", "source": "s", "rationale": "r",
                        "supersedes": ["G8"]}]}
        ),
        encoding="utf-8",
    )


def test_doctor_without_a_profile_is_unchanged(vu_path, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    _write_small_profile(tmp_path)
    assert main(["doctor", str(vu_path)]) == 0
    assert "G8" in capsys.readouterr().out


def test_doctor_with_a_profile_suppresses_the_superseded_rule(
    vu_path, tmp_path, capsys, monkeypatch
):
    # render.findings() also prints a transparency line naming every
    # switched-off rule id ("[suppressed] G8 switched off by show.small"),
    # by design (see suppressed_ids() and its tests in
    # test_advisory_resolver.py) -- so a bare "G8" not in out would fail
    # even when suppression worked correctly. Use --json, which reports
    # only the active findings, to test what this test actually means:
    # G8 is no longer an active rule_id, and G7 still is.
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    _write_small_profile(tmp_path)
    assert main(["doctor", str(vu_path), "--profile", "small", "--json"]) == 0
    rule_ids = {f["rule_id"] for f in json.loads(capsys.readouterr().out)}
    assert "G8" not in rule_ids
    assert "G7" in rule_ids


def test_an_unknown_profile_exits_cleanly(vu_path, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    _write_small_profile(tmp_path)
    assert main(["doctor", str(vu_path), "--profile", "smal"]) == 1
    err = capsys.readouterr().err
    assert "smal" in err
    assert "small" in err


def test_feedback_sees_the_same_findings_doctor_printed(
    vu_path, tmp_path, capsys, monkeypatch
):
    """An id doctor prints under a profile must resolve under the same
    profile, or the two surfaces have diverged."""
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    _write_small_profile(tmp_path)
    assert main(["doctor", str(vu_path), "--profile", "small", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    target_id = f"{payload[0]['rule_id']}:{payload[0]['target']}"

    assert main(["feedback", target_id, "--verdict", "correct",
                 "--scene", str(vu_path), "--profile", "small"]) == 0


def test_feedback_with_the_profile_cannot_find_a_finding_the_profile_suppressed(
    vu_path, tmp_path, capsys, monkeypatch
):
    # G8:ch.8.send.8 only exists as a finding when no profile suppresses
    # G8. Passing --profile small here makes feedback run the advisory
    # under the same profile doctor would, G8 is superseded, and the id
    # is not among that run's findings -- so it correctly fails to
    # resolve, the same way a typo'd id would.
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    _write_small_profile(tmp_path)
    assert main(["feedback", "G8:ch.8.send.8", "--verdict", "correct",
                 "--scene", str(vu_path), "--profile", "small"]) == 1
