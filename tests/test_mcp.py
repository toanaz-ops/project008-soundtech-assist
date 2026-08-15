import inspect
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
    # "live" alone also appears in scene_overview's "N live channels
    # (unmuted, ...)" line, so a miswired tool calling the wrong renderer
    # would still pass that check. Assert text only routing() produces.
    out = tools.routing(str(vu_path))
    assert "3 live channels" in out
    assert "unpatched channels" in out


def test_diff_returns_changes(vu_path, tmp_path):
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    doc["ae_data"]["ch"]["8"]["fdr"] = -3.0
    other = tmp_path / "other.snap"
    other.write_text(json.dumps(doc), encoding="utf-8")

    assert "ch.8.fader_dB" in tools.diff(str(vu_path), str(other))


def test_diff_names_the_second_file_when_it_is_the_one_missing(vu_path):
    # _guard's OSError handler used to fall back to `exc.filename or
    # args[0]`. That fallback is dead code -- Path.read_text always sets
    # .filename -- but it would have named the wrong file for diff(before,
    # after) if it had ever fired: args[0] is `before`, not whichever path
    # actually failed to open. Assert on the argument that would have
    # exposed that bug: the *second* (missing) path, not the first.
    out = tools.diff(str(vu_path), "no-such-second-file.snap")
    assert "no-such-second-file.snap" in out
    assert out.lower().startswith("error")


def test_a_missing_file_returns_a_message_not_an_exception():
    out = tools.analyze("no-such-file.snap")
    assert "no-such-file.snap" in out
    assert out.lower().startswith("error")


def test_an_unknown_channel_returns_a_message(vu_path):
    out = tools.channel(str(vu_path), 99)
    assert "99" in out
    assert out.lower().startswith("error")


def test_a_directory_returns_a_message_not_an_exception(tmp_path):
    # analyze() opens a directory path, which raises PermissionError (an
    # OSError subclass) rather than FileNotFoundError — Task 22's own
    # loader guard covers this one layer up in cli/commands.py, and the
    # MCP tools need the same net so nothing crosses the MCP boundary.
    out = tools.analyze(str(tmp_path))
    assert out.lower().startswith("error")


def test_every_tool_keeps_the_signature_fastmcp_introspects():
    """FastMCP builds each tool's input schema from the signature, so a
    *args/**kwargs wrapper would register five tools with no parameters."""
    assert list(inspect.signature(tools.channel).parameters) == ["path", "number"]
    assert list(inspect.signature(tools.diff).parameters) == ["before", "after"]
    for name, function in tools.TOOLS.items():
        parameters = inspect.signature(function).parameters
        assert parameters, f"{name} exposes no parameters"
        assert "args" not in parameters and "kwargs" not in parameters, name


def test_server_builds_when_the_mcp_package_is_installed():
    pytest.importorskip("mcp")
    from wing_parser.mcp.server import build

    assert build() is not None


def test_main_names_the_fix_when_the_mcp_extra_is_missing(capsys):
    # A bare ImportError from `wing-mcp` (the console script) points at
    # nothing actionable. This only exercises the failure path when `mcp`
    # is genuinely absent -- which it deliberately is in this suite's
    # environment (see the one skip in test_server_builds_when_...).
    try:
        import mcp  # noqa: F401
    except ImportError:
        pass
    else:
        pytest.skip("mcp is installed in this environment")

    from wing_parser.mcp.server import main

    with pytest.raises(SystemExit) as excinfo:
        main()
    assert excinfo.value.code == 1
    assert "wing-parser[mcp]" in capsys.readouterr().err
