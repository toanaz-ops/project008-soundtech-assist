import inspect
import json

import pytest
import yaml

from wing_parser.core.loader import RawScene
from wing_parser.core.versions import load_registry, resolve
from wing_parser.mcp import tools
from wing_parser.net.snapshot import SnapshotResult


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
    # G7 is silent on this file since the 2026-08-16 monitor split (all
    # IEM matrices have dyn.on True); its old sole finding moved to G9.
    out = tools.doctor(str(vu_path))
    assert "G8" in out and "G9" in out


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
    assert list(inspect.signature(tools.channel).parameters) == ["path", "number", "live"]
    assert list(inspect.signature(tools.diff).parameters) == ["before", "after"]
    for name, function in tools.TOOLS.items():
        parameters = inspect.signature(function).parameters
        assert parameters, f"{name} exposes no parameters"
        assert "args" not in parameters and "kwargs" not in parameters, name


def test_server_builds_when_the_mcp_package_is_installed():
    pytest.importorskip("mcp")
    from wing_parser.mcp.server import build

    assert build() is not None


def test_doctor_accepts_a_profile(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    shows = tmp_path / "shows"
    shows.mkdir(parents=True, exist_ok=True)
    (shows / "small.yaml").write_text(
        yaml.safe_dump(
            {"rules": [{"id": "show.small", "title": "Small show",
                        "severity": "info", "source": "s", "rationale": "r",
                        "supersedes": ["G8"]}]}
        ),
        encoding="utf-8",
    )
    # render.findings() names every switched-off rule id in a transparency
    # line ("[suppressed] G8 switched off by show.small"), so a bare "G8"
    # not in out would fail even on correct suppression -- the MCP tool
    # has no --json escape hatch, so assert the *only* remaining "G8" is
    # that transparency line, not an active finding.
    with_profile = tools.doctor(str(vu_path), profile="small")
    assert with_profile.count("G8") == 1
    assert "G8 switched off by show.small" in with_profile
    assert "G8" in tools.doctor(str(vu_path))


def test_doctor_with_an_unknown_profile_returns_a_message(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_KNOWLEDGE_DIR", str(tmp_path))
    out = tools.doctor(str(vu_path), profile="nope")
    assert out.lower().startswith("error")
    assert "nope" in out


def test_the_doctor_tool_still_exposes_its_parameters():
    assert list(inspect.signature(tools.doctor).parameters) == [
        "path", "profile", "show", "live"
    ]


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


def test_doctor_accepts_a_show_context_and_reports_its_findings(vu_path):
    """Spec S6.1: without this, a Claude session on MCP cannot see
    Q1-Q7 at all."""
    from wing_parser.mcp import tools

    plain = tools.doctor(str(vu_path))
    with_show = tools.doctor(
        str(vu_path), show="tests/data/example-Vu-show.yaml"
    )
    assert "Q1" not in plain
    assert "Q1" in with_show


def test_every_tool_that_reads_a_scene_now_offers_live():
    import inspect

    from wing_parser.mcp import tools

    for name in ("analyze", "routing", "channel", "doctor"):
        signature = inspect.signature(getattr(tools, name))
        assert "live" in signature.parameters, f"{name} has no live parameter"


def test_doctor_still_reports_the_pinned_count_for_the_real_file(vu_path):
    from wing_parser.mcp import tools

    assert tools.doctor(str(vu_path)).startswith("22 findings")


def test_doctor_show_reports_show_anomalies_too(vu_path, tmp_path):
    """F3: the CLI prints render.show_anomalies(scene.show.anomalies)
    ahead of the findings (commands.py doctor); the MCP tool did not.
    Spec S6.1 says the MCP surface mirrors the CLI, which is the
    authority -- model this on test_cli_showcontext.py's
    test_show_anomalies_are_printed, which uses the same typo'd
    `instrument.kyes` to trigger one."""
    path = tmp_path / "typo.yaml"
    path.write_text(
        yaml.safe_dump({"show": "t", "segments": [
            {"id": "S1", "expects": ["instrument.kyes"]}
        ]}),
        encoding="utf-8",
    )
    out = tools.doctor(str(vu_path), show=str(path))
    assert "instrument.kyes" in out and "instrument.keys" in out


# --- F1: a partial live read must not read as a complete one on MCP ---
#
# Modeled on tests/test_cli_live_unreachable.py, which already covers the
# CLI side of the same `_load` behaviour. `_scene` (wing_parser/mcp/tools.py)
# used to consult its captured stderr only when `_load` returned None --
# a partial-but-usable read (a scene plus a stderr warning) fell through
# that check and reached an MCP session with no trace at all.

DEAD_ROOTS = (
    "/cfg", "/io", "/ch", "/aux", "/bus", "/main", "/mtx",
    "/dca", "/mgrp", "/fx", "/cards", "/play", "/$ctl",
)


def _raw(ae: dict, ce: dict) -> RawScene:
    return RawScene(
        version=resolve("snapshot.11", load_registry()),
        ae=ae,
        ce=ce,
        meta={},
        path=None,
        source="wing://10.0.0.1",
    )


def _stub_partial(monkeypatch, factory_path) -> None:
    import json as _json

    real = _json.loads(factory_path.read_text(encoding="utf-8"))
    monkeypatch.setattr(
        "wing_parser.net.snapshot.take_snapshot",
        lambda *a, **k: SnapshotResult(
            raw=_raw(real["ae_data"], real["ce_data"]),
            unresolved_nodes=("/fx/1",),
            unresolved_leaves=("/ch/1/fdr", "/ch/2/fdr"),
        ),
    )


def _stub_complete(monkeypatch, factory_path) -> None:
    import json as _json

    real = _json.loads(factory_path.read_text(encoding="utf-8"))
    monkeypatch.setattr(
        "wing_parser.net.snapshot.take_snapshot",
        lambda *a, **k: SnapshotResult(
            raw=_raw(real["ae_data"], real["ce_data"]),
            unresolved_nodes=(),
            unresolved_leaves=(),
        ),
    )


def test_analyze_carries_the_partial_read_warning(monkeypatch, factory_path):
    _stub_partial(monkeypatch, factory_path)
    out = tools.analyze(live="10.0.0.1")
    assert "warning" in out.lower() and "10.0.0.1" in out


def test_channel_carries_the_partial_read_warning(monkeypatch, factory_path):
    _stub_partial(monkeypatch, factory_path)
    out = tools.channel(number=1, live="10.0.0.1")
    assert "warning" in out.lower() and "10.0.0.1" in out


def test_routing_carries_the_partial_read_warning(monkeypatch, factory_path):
    _stub_partial(monkeypatch, factory_path)
    out = tools.routing(live="10.0.0.1")
    assert "warning" in out.lower() and "10.0.0.1" in out


def test_doctor_carries_the_partial_read_warning(monkeypatch, factory_path):
    _stub_partial(monkeypatch, factory_path)
    out = tools.doctor(live="10.0.0.1")
    assert "warning" in out.lower() and "10.0.0.1" in out


def test_analyze_on_a_complete_live_read_has_no_warning_prefix(monkeypatch, factory_path):
    """Silence on a clean read is deliberate -- assert it holds on MCP too."""
    _stub_complete(monkeypatch, factory_path)
    out = tools.analyze(live="10.0.0.1")
    assert "warning" not in out.lower()


def test_doctor_on_a_complete_live_read_has_no_warning_prefix(monkeypatch, factory_path):
    _stub_complete(monkeypatch, factory_path)
    out = tools.doctor(live="10.0.0.1")
    assert "warning" not in out.lower()
