import json

import pytest

from wing_parser.mcp import tools


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")


def test_five_tools_are_registered():
    assert set(tools.TOOLS) == {
        "wing_analyze", "wing_channel", "wing_diff", "wing_routing", "wing_doctor"
    }


def test_every_tool_has_a_docstring_claude_can_read():
    for name, function in tools.TOOLS.items():
        assert function.__doc__, f"{name} has no docstring"
        assert len(function.__doc__.strip()) > 60, f"{name} docstring is too thin"


def test_analyze_returns_text(vu_path):
    out = tools.analyze(str(vu_path))
    assert "snapshot.11" in out


def test_channel_returns_detail(vu_path):
    out = tools.channel(str(vu_path), 8)
    assert "M8 MC" in out
    assert "speech.mc" in out


def test_doctor_returns_the_findings(vu_path):
    out = tools.doctor(str(vu_path))
    assert "G8" in out and "G7" in out


def test_routing_returns_the_summary(vu_path):
    assert "live" in tools.routing(str(vu_path)).lower()


def test_diff_returns_changes(vu_path, tmp_path):
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"]["8"]["fdr"] = -3.0
    other = tmp_path / "other.snap"
    other.write_text(json.dumps(doc), encoding="utf-8")

    assert "ch.8.fader_dB" in tools.diff(str(vu_path), str(other))


def test_a_missing_file_returns_a_message_not_an_exception():
    out = tools.analyze("no-such-file.snap")
    assert "no-such-file.snap" in out
    assert out.lower().startswith("error")


def test_an_unknown_channel_returns_a_message(vu_path):
    out = tools.channel(str(vu_path), 99)
    assert "99" in out
    assert out.lower().startswith("error")


def test_server_builds_when_the_mcp_package_is_installed():
    pytest.importorskip("mcp")
    from wing_parser.mcp.server import build

    assert build() is not None
