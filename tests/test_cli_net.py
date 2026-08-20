"""Tests for `wing net` and the `--live` flag, driven only against
tests/fake_wing.py -- no test here touches a real socket to a real
console (design doc S7). `net_commands.py` binds `OSC_PORT`/`IDENTITY_PORT`
as bare module globals rather than argparse defaults specifically so a
test can retarget every command at the fake's ephemeral loopback ports
via `monkeypatch.setattr(net_commands, "OSC_PORT", ...)`.
"""

from __future__ import annotations

import json
import types

import pytest

from tests.fake_wing import FakeWing
from wing_parser import WingScene
from wing_parser.cli import net_commands
from wing_parser.cli.__main__ import main
from wing_parser.core.loader import RawScene, load_raw
from wing_parser.core.versions import load_registry, resolve
from wing_parser.net import snapshot as snapshot_module
from wing_parser.net.codec import encode
from wing_parser.net.snapshot import SnapshotResult


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")


def _sff(address, display, native):
    return encode(address, "sff", (display, 0.0, native))


def _sfi(address, display, native):
    return encode(address, "sfi", (display, 0.0, native))


def _s(address, text):
    return encode(address, "s", (text,))


# -- net identity -------------------------------------------------------


def test_net_identity_prints_the_parsed_fields(capsys, monkeypatch):
    with FakeWing() as fake:
        host, port = fake.identity_address
        monkeypatch.setattr(net_commands, "IDENTITY_PORT", port)
        assert main(["net", "identity", host]) == 0

    out = capsys.readouterr().out
    assert "WING-GIAQUY" in out
    assert "wing-rack" in out
    assert "01009Y90604AAE" in out


def test_net_identity_reports_an_unreachable_console_without_a_traceback(capsys, monkeypatch):
    def _raise(host, port):
        raise TimeoutError(f"no WING? reply from {host}:{port} within 2.0s")

    monkeypatch.setattr(net_commands, "query_identity", _raise)
    assert main(["net", "identity", "10.255.255.1"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("error:")
    assert "Traceback" not in err


# -- net snapshot ---------------------------------------------------------


def test_net_snapshot_prints_a_summary_with_unresolved_counts(capsys, monkeypatch):
    raw = RawScene(
        version=resolve("snapshot.11", load_registry()),
        ae={"ch": {"1": {"fdr": -6.0}}}, ce={}, meta={}, path=None,
        source="wing://10.0.0.1",
    )
    result = SnapshotResult(
        raw=raw, unresolved_nodes=("/fx/1",), unresolved_leaves=("/cfg/mon/1/lvl",)
    )
    monkeypatch.setattr(net_commands, "take_snapshot", lambda host, port: result)

    assert main(["net", "snapshot", "10.0.0.1"]) == 0
    out = capsys.readouterr().out
    assert "1 leaves read" in out
    assert "unresolved node" in out and "/fx/1" in out
    assert "unresolved leaf" in out and "/cfg/mon/1/lvl" in out


def test_net_snapshot_o_writes_a_file_wingscene_can_reload(vu_path, tmp_path, monkeypatch):
    # net/export.py is being written concurrently (design doc S4.1) and
    # may not exist yet; stub it in sys.modules to test the CLI's side of
    # the contract (`to_snap_json(raw) -> str`) without depending on
    # whether the real module has landed.
    raw = load_raw(vu_path)
    monkeypatch.setattr(
        net_commands, "take_snapshot",
        lambda host, port: SnapshotResult(raw=raw, unresolved_nodes=(), unresolved_leaves=()),
    )

    def _to_snap_json(raw, identity=None):
        return json.dumps({"type": raw.version.type_id, "ae_data": raw.ae, "ce_data": raw.ce})

    fake_export = types.ModuleType("wing_parser.net.export")
    fake_export.to_snap_json = _to_snap_json
    monkeypatch.setitem(__import__("sys").modules, "wing_parser.net.export", fake_export)

    out_path = tmp_path / "live.snap"
    assert main(["net", "snapshot", "192.168.128.28", "-o", str(out_path)]) == 0

    reloaded = WingScene.load(out_path)
    original = WingScene.load(vu_path)
    assert len(reloaded.channels()) == len(original.channels())


# -- net get ----------------------------------------------------------------


def test_net_get_prints_the_leaf_value(capsys, monkeypatch):
    with FakeWing() as fake:
        host, port = fake.osc_address
        monkeypatch.setattr(net_commands, "OSC_PORT", port)
        assert main(["net", "get", host, "/ch/1/fdr"]) == 0

    assert "-42.3" in capsys.readouterr().out


def test_net_get_reports_a_silent_address_without_a_traceback(capsys, monkeypatch):
    # /ch/99/fdr is one of wing_osc_fixtures.json's three deliberate
    # no-reply cases (design doc S2.4(b) -- a GET on a missing address).
    with FakeWing() as fake:
        host, port = fake.osc_address
        monkeypatch.setattr(net_commands, "OSC_PORT", port)
        assert main(["net", "get", host, "/ch/99/fdr"]) == 1

    err = capsys.readouterr().err
    assert err.startswith("error:")
    assert "Traceback" not in err


# -- net set: dry-run default is the important guarantee --------------------


def test_net_set_without_confirm_sends_zero_osc_packets(capsys, monkeypatch):
    with FakeWing() as fake:
        host, port = fake.osc_address
        monkeypatch.setattr(net_commands, "OSC_PORT", port)
        before = fake.osc_packets_received
        code = main(["net", "set", host, "/ch/40/fdr", "-6.0"])
        after = fake.osc_packets_received

    assert code == 0
    assert after == before, "dry-run (no --confirm) must not send a single packet"
    assert "dry run" in capsys.readouterr().out.lower()


def test_net_set_with_confirm_echoes_identity_and_verifies_the_readback(capsys, monkeypatch):
    address = "/ch/40/fdr"
    with FakeWing() as fake:
        fake.register(encode(address, "s", ("-6.0",)), None)  # no echo (S2.1)
        fake.register(encode(address), _sff(address, "-6.0", -6.0))
        host, osc_port = fake.osc_address
        _, identity_port = fake.identity_address
        monkeypatch.setattr(net_commands, "OSC_PORT", osc_port)
        monkeypatch.setattr(net_commands, "IDENTITY_PORT", identity_port)

        code = main(["net", "set", host, address, "-6.0", "--confirm"])

    assert code == 0
    out = capsys.readouterr().out
    assert "WING-GIAQUY" in out  # S6 guard 2: identity echoed before the write
    assert "[OK]" in out


def test_net_set_confirm_reports_a_mismatch_as_failure(capsys, monkeypatch):
    # design doc S2.6: an out-of-range value is silently clamped and still
    # answers OK -- the read-back is what must catch it, never swallowed.
    address = "/ch/40/fdr"
    with FakeWing() as fake:
        fake.register(encode(address, "s", ("999",)), None)
        fake.register(encode(address), _sff(address, "10.0", 10.0))  # clamped
        host, osc_port = fake.osc_address
        _, identity_port = fake.identity_address
        monkeypatch.setattr(net_commands, "OSC_PORT", osc_port)
        monkeypatch.setattr(net_commands, "IDENTITY_PORT", identity_port)

        code = main(["net", "set", host, address, "999", "--confirm"])

    assert code == 1
    assert "MISMATCH" in capsys.readouterr().out


def test_net_set_confirm_with_serial_mismatch_is_a_clean_error(capsys, monkeypatch):
    monkeypatch.setenv("WING_WRITE_ALLOW_SERIAL", "SOME-OTHER-SERIAL")
    address = "/ch/40/fdr"
    with FakeWing() as fake:
        fake.register(encode(address, "s", ("-6.0",)), None)
        fake.register(encode(address), _sff(address, "-6.0", -6.0))
        host, osc_port = fake.osc_address
        _, identity_port = fake.identity_address
        monkeypatch.setattr(net_commands, "OSC_PORT", osc_port)
        monkeypatch.setattr(net_commands, "IDENTITY_PORT", identity_port)

        code = main(["net", "set", host, address, "-6.0", "--confirm"])

    assert code == 1
    err = capsys.readouterr().err
    assert err.startswith("error:")
    assert "Traceback" not in err


# -- net toggle ---------------------------------------------------------------


def test_net_toggle_without_confirm_sends_zero_osc_packets(capsys, monkeypatch):
    with FakeWing() as fake:
        host, port = fake.osc_address
        monkeypatch.setattr(net_commands, "OSC_PORT", port)
        before = fake.osc_packets_received
        code = main(["net", "toggle", host, "/ch/40/mute"])
        after = fake.osc_packets_received

    assert code == 0
    assert after == before
    assert "dry run" in capsys.readouterr().out.lower()


def test_net_toggle_with_confirm_sends_and_verifies(capsys, monkeypatch):
    address = "/ch/40/mute"
    with FakeWing() as fake:
        fake.register(encode(address, "i", (-1,)), None)
        fake.register(encode(address), _sfi(address, "0", 0))
        host, osc_port = fake.osc_address
        _, identity_port = fake.identity_address
        monkeypatch.setattr(net_commands, "OSC_PORT", osc_port)
        monkeypatch.setattr(net_commands, "IDENTITY_PORT", identity_port)

        code = main(["net", "toggle", host, address, "--confirm"])

    assert code == 0
    assert "[OK]" in capsys.readouterr().out


# -- net push: landed / mismatched / absent are three distinct outcomes -----


def _push_file(tmp_path):
    doc = {
        "type": "snapshot.11",
        "ae_data": {
            "ch": {
                "1": {"name": "PROBE"},
                "2": {"fdr": -6.0},
                "3": {"mute": 1},
            }
        },
    }
    path = tmp_path / "push.snap"
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def test_net_push_without_confirm_sends_zero_osc_packets(tmp_path, capsys):
    push_file = _push_file(tmp_path)
    with FakeWing() as fake:
        host = fake.osc_address[0]
        before = fake.osc_packets_received
        code = main(["net", "push", host, str(push_file)])
        after = fake.osc_packets_received

    assert code == 0
    assert after == before
    assert "dry run" in capsys.readouterr().out.lower()


def test_net_push_reports_landed_mismatched_and_absent_distinctly(tmp_path, capsys, monkeypatch):
    push_file = _push_file(tmp_path)
    with FakeWing() as fake:
        fake.register(encode("/ch/1/name", "s", ("PROBE",)), None)
        fake.register(encode("/ch/1/name"), _s("/ch/1/name", "PROBE"))
        fake.register(encode("/ch/2/fdr", "s", ("-6.0",)), None)
        fake.register(encode("/ch/2/fdr"), _sff("/ch/2/fdr", "-3.0", -3.0))
        fake.register(encode("/ch/3/mute", "s", ("1",)), None)
        # /ch/3/mute's GET is deliberately never registered -- S2.7's
        # "genuinely absent on this console" (129 such leaves measured).
        host, osc_port = fake.osc_address
        _, identity_port = fake.identity_address
        monkeypatch.setattr(net_commands, "OSC_PORT", osc_port)
        monkeypatch.setattr(net_commands, "IDENTITY_PORT", identity_port)

        code = main(["net", "push", host, str(push_file), "--confirm"])

    assert code == 1  # a real mismatch is a failure
    out = capsys.readouterr().out
    assert "landed=1" in out
    assert "mismatched=1" in out
    assert "absent=1" in out
    assert "not a failure" in out  # absent must read as hardware, not defect


# -- --live: doctor/analyze/routing/channel read a console instead of a file --


def test_doctor_live_matches_the_file_flag_finding_count(vu_path, capsys, monkeypatch):
    raw = load_raw(vu_path)
    monkeypatch.setattr(
        snapshot_module, "take_snapshot",
        lambda host: SnapshotResult(raw=raw, unresolved_nodes=(), unresolved_leaves=()),
    )

    assert main(["doctor", "--live", "192.168.128.28"]) == 0
    assert "22 findings" in capsys.readouterr().out


def test_live_and_file_are_mutually_exclusive(capsys):
    with pytest.raises(SystemExit):
        main(["doctor", "some.snap", "--live", "10.0.0.1"])
    assert "not allowed" in capsys.readouterr().err


def test_live_reports_a_network_failure_without_a_traceback(capsys, monkeypatch):
    def _raise(host):
        raise TimeoutError(f"no reply from {host}")

    monkeypatch.setattr(snapshot_module, "take_snapshot", _raise)
    assert main(["doctor", "--live", "10.255.255.1"]) == 1
    err = capsys.readouterr().err
    assert err.startswith("error:")
    assert "Traceback" not in err
