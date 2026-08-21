"""The CLI surface for `wing net watch`.

The last two cycles each shipped a bug where a non-JSON line reached
stdout in --json mode, because the flag and the print lived in different
files. These tests hold both halves.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from wing_parser.cli import net_commands
from wing_parser.cli.__main__ import build_parser
from wing_parser.net.watch.events import Change
from wing_parser.net.watch.list import WatchList


def _args(**overrides) -> SimpleNamespace:
    fields = dict(host="10.0.0.1", json=False, interval=0.25, until=1.0)
    fields.update(overrides)
    return SimpleNamespace(**fields)


def _change() -> Change:
    return Change(
        address="/ch/8/$fdr",
        strip="/ch/8",
        key="$fdr",
        label="M8 MC",
        before=-144.0,
        after=-7.9,
        elapsed=1.5,
    )


@pytest.fixture
def stubbed(monkeypatch):
    """Replace the network entirely: a fixed watch-list and one change."""
    state = {"list": WatchList(("/ch/8/$fdr",), (), {"ch": 40}), "changes": [_change()]}

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *exc_info):
            return False

    monkeypatch.setattr(net_commands, "WingClient", FakeClient)
    monkeypatch.setattr(
        net_commands, "build_watch_list", lambda *a, **k: state["list"]
    )
    monkeypatch.setattr(
        net_commands, "watch", lambda *a, **k: iter(state["changes"])
    )
    return state


def test_the_parser_accepts_net_watch_with_an_ip():
    args = build_parser().parse_args(["net", "watch", "10.0.0.1"])
    assert args.host == "10.0.0.1"
    assert args.handler is net_commands.net_watch


def test_text_mode_prints_the_change_with_its_name(stubbed, capsys):
    assert net_commands.net_watch(_args()) == 0
    out = capsys.readouterr().out
    assert "M8 MC" in out
    assert "$fdr" in out


def test_json_mode_emits_only_json_on_stdout(stubbed, capsys):
    """Every stdout line must parse. This is the exact defect that
    shipped twice before."""
    assert net_commands.net_watch(_args(json=True)) == 0
    out = capsys.readouterr().out
    lines = [line for line in out.splitlines() if line.strip()]
    assert lines
    for line in lines:
        json.loads(line)


def test_an_unresolved_node_is_reported_on_stderr_in_text_mode(stubbed, capsys):
    stubbed["list"] = WatchList(("/ch/8/$fdr",), ("/main/1",), {"ch": 40})
    net_commands.net_watch(_args())
    captured = capsys.readouterr()
    assert "/main/1" in captured.err
    assert "/main/1" not in captured.out


def test_an_unresolved_node_travels_in_the_json_header(stubbed, capsys):
    stubbed["list"] = WatchList(("/ch/8/$fdr",), ("/main/1",), {"ch": 40})
    net_commands.net_watch(_args(json=True))
    out = capsys.readouterr().out
    header = json.loads(out.splitlines()[0])
    assert header["unresolved"] == ["/main/1"]


def test_a_network_failure_reports_and_returns_one(monkeypatch, capsys):
    class Boom:
        def __init__(self, *args, **kwargs):
            raise OSError("no route to host")

    monkeypatch.setattr(net_commands, "WingClient", Boom)
    assert net_commands.net_watch(_args()) == 1
    assert "no route to host" in capsys.readouterr().err
