"""probe13_nonascii_names: parse/verdict behaviour, and proof it cannot write."""

from __future__ import annotations

import ast
import importlib.util
import unicodedata
from pathlib import Path

from tests.fake_wing import FakeWing
from wing_parser.net.codec import encode

PROBE_PATH = Path(__file__).resolve().parents[1] / "docs" / "probes" / "probe13_nonascii_names.py"
_spec = importlib.util.spec_from_file_location("probe13_nonascii_names", PROBE_PATH)
probe13 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(probe13)

VIET = "Ca sĩ Đạt"
# cp1258 lacks some precomposed letters (e.g. "ĩ"): it stores base + combining mark.


def _cp1258(text: str) -> bytes:
    out = b""
    for ch in text:
        try:
            out += ch.encode("cp1258")
        except UnicodeEncodeError:
            out += unicodedata.normalize("NFD", ch).encode("cp1258", errors="ignore")
    return out


VIET_CP = _cp1258(VIET)


def _reply(address: str, raw_name: bytes) -> bytes:
    """A ,sff reply carrying raw (undecoded) name bytes."""
    field = raw_name + b"\x00"
    field += b"\x00" * (-len(field) % 4)
    return encode(address) + b",sff\x00\x00\x00\x00" + field + b"\x00" * 8


def test_decodes_utf8_and_cp1258():
    utf8 = probe13.build_record("/ch/1/name", _reply("/ch/1/name", VIET.encode("utf-8")))
    assert utf8["non_ascii"] and utf8["decodes"]["utf-8"] == VIET
    assert utf8["decodes"]["ascii"] is None

    vi = probe13.build_record("/ch/2/name", _reply("/ch/2/name", VIET_CP))
    assert vi["non_ascii"] and vi["decodes"]["utf-8"] is None
    assert unicodedata.normalize("NFC", vi["decodes"]["cp1258"]) == VIET


def test_malformed_datagram_is_recorded_not_raised():
    for bad in (b"\xff\xfe", b"", b"/ch/1/name", encode("/ch/1/name") + b"zzzz"):
        record = probe13.build_record("/ch/3/name", bad)
        assert record["error"] and record["name_hex"] is None


def test_verdict_lines():
    plain = [probe13.build_record("/ch/1/name", _reply("/ch/1/name", b"Kick"))]
    assert probe13.verdict(plain).startswith("non-ASCII seen: no")
    utf8 = [probe13.build_record("/ch/1/name", _reply("/ch/1/name", "Đức".encode()))]
    assert "non-ASCII seen: yes" in probe13.verdict(utf8)
    assert "consistent with: utf-8" in probe13.verdict(utf8)
    cp = [probe13.build_record("/ch/1/name", _reply("/ch/1/name", _cp1258("Đức")))]
    assert "utf-8" not in probe13.verdict(cp).split("consistent with:")[1]
    assert "cp1258" in probe13.verdict(cp)


def test_parse_range():
    assert list(probe13.parse_range("1-3")) == [1, 2, 3]
    assert list(probe13.parse_range("7")) == [7]


def test_run_against_fakewing_survives_garbage_and_silence():
    channels = probe13.parse_range("1-4")
    n_requests = len(probe13.targets(channels))
    with FakeWing() as fake:
        fake.register(encode("/ch/1/name"), _reply("/ch/1/name", VIET.encode("utf-8")))
        fake.register(encode("/ch/2/name"), _reply("/ch/2/name", VIET_CP))
        fake.register(encode("/ch/3/name"), b"\xff\xfe\x00")
        host, port = fake.osc_address
        records = probe13.run(host, channels, timeout=0.05, port=port)
        assert len(records) == n_requests
        assert fake.osc_packets_received == n_requests
    by_addr = {r["address"]: r for r in records}
    assert by_addr["/ch/1/name"]["decodes"]["utf-8"] == VIET
    assert unicodedata.normalize("NFC", by_addr["/ch/2/name"]["decodes"]["cp1258"]) == VIET
    assert by_addr["/ch/3/name"]["error"]
    assert by_addr["/ch/4/name"]["error"] == "no reply (timeout)"
    assert "non-ASCII seen: yes" in probe13.verdict(records)


def test_probe_cannot_write():
    tree = ast.parse(PROBE_PATH.read_text(encoding="utf-8"))
    banned = {"write", "set", "toggle", "push", "node_write"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert "net.write" not in (node.module or "")
            assert not any(a.name in banned for a in node.names)
        elif isinstance(node, ast.Import):
            assert not any("net.write" in a.name for a in node.names)
        elif isinstance(node, ast.Call):
            func = node.func
            name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            assert name not in banned
            if name == "encode" and isinstance(func, ast.Name):
                # codec.encode is only ever the bare address GET: no typetag/args.
                assert len(node.args) == 1 and not node.keywords
