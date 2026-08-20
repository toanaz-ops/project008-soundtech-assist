"""Tests for wing_parser.net.write, driven only against tests/fake_wing.py
-- no test here touches a real socket to a real console (design doc sec 7).

fake_wing's request/reply table is static (last registration for a given
tx wins), so most scenarios here register their own tx/rx pairs with
`fake.register` rather than leaning on the ambient state left by the full
wing_write_fixtures.json replay -- that keeps each test's expected
readback unambiguous instead of depending on load order.
"""

from __future__ import annotations

import pytest

from tests.fake_wing import FakeWing
from wing_parser.net import write
from wing_parser.net.codec import encode

_FAST = dict(timeout=0.5)
# The console FakeWing impersonates by default (tests/data/wing_osc_fixtures.json
# "identity"): serial 01009Y90604AAE.
_REAL_SERIAL = "01009Y90604AAE"


def _addrs(fake):
    host, osc_port = fake.osc_address
    _, identity_port = fake.identity_address
    return host, osc_port, identity_port


def _sff(address, display, native):
    return encode(address, "sff", (display, 0.0, native))


def _sfi(address, display, native):
    return encode(address, "sfi", (display, 0.0, native))


def _s(address, text):
    return encode(address, "s", (text,))


# -- sec 6.1: dry-run is the default, and sends nothing ---------------------


def test_dry_run_sends_zero_packets_from_any_entry_point(monkeypatch):
    monkeypatch.delenv("WING_WRITE_ALLOW_SERIAL", raising=False)
    with FakeWing() as fake:
        host, osc_port, identity_port = _addrs(fake)
        osc_before = fake.osc_packets_received
        id_before = fake.identity_packets_received

        set_result = write.set(host, "/ch/40/fdr", -6.0, osc_port=osc_port,
                                identity_port=identity_port, **_FAST)
        toggle_result = write.toggle(host, "/ch/40/mute", osc_port=osc_port,
                                      identity_port=identity_port, **_FAST)
        node_result = write.node_write(host, "/ch/40", {"fdr": -6.0}, osc_port=osc_port,
                                        identity_port=identity_port, **_FAST)
        push_result = write.push(host, {"/ch/40/fdr": -6.0}, osc_port=osc_port,
                                  identity_port=identity_port, **_FAST)

        osc_after = fake.osc_packets_received
        id_after = fake.identity_packets_received

    # Not one datagram, on either port -- sec 6.1 is "touches no socket",
    # not merely "doesn't write", so the identity echo itself must not
    # fire either when confirm=False.
    assert osc_after == osc_before
    assert id_after == id_before
    assert set_result.dry_run and toggle_result.dry_run
    assert node_result.dry_run and push_result.dry_run
    assert set_result.matched is None
    assert push_result.landed == () and push_result.mismatched == {} and push_result.absent == ()


# -- set(): display-domain string by default, plain decimal, -oo -----------


def test_set_default_typetag_is_display_domain_string_plain_decimal():
    result = write.set("127.0.0.1", "/ch/40/fdr", -6.0, confirm=False)
    assert result.sent == "-6.0"


def test_set_formats_a_tiny_float_without_scientific_notation():
    # design doc sec 2.6: fx.N.thr_3 = 1.490116119e-07 was 5 of the 21344
    # write failures because WING's parser rejects an exponent.
    result = write.set("127.0.0.1", "/fx/1/thr_3", 1.490116119e-07, confirm=False)
    assert "e" not in result.sent and "E" not in result.sent
    assert float(result.sent) == pytest.approx(1.490116119e-07, abs=1e-9)


@pytest.mark.parametrize("value", [-144.0, -999.0, float("-inf")])
def test_set_formats_silence_as_the_oo_token(value):
    result = write.set("127.0.0.1", "/ch/40/fdr", value, confirm=False)
    assert result.sent == "-oo"


def test_set_formats_a_schema_index_int_bare_not_as_a_float():
    # design doc sec 2.6: ch.N.dyn.ratio holds the int 3 in the file, meant
    # as the *value* 3.0 via ",s 3" -- never re-expressed as "3.0".
    result = write.set("127.0.0.1", "/ch/1/dyn/ratio", 3, confirm=False)
    assert result.sent == "3"


def test_confirmed_set_sends_the_display_string_and_verifies_readback():
    address = "/ch/40/fdr"
    with FakeWing() as fake:
        fake.register(encode(address, "s", ("-6.0",)), None)  # sec 2.1: no echo
        fake.register(encode(address), _sff(address, "-6.0", -6.0))
        host, osc_port, identity_port = _addrs(fake)
        before = fake.osc_packets_received

        result = write.set(host, address, -6.0, osc_port=osc_port,
                            identity_port=identity_port, confirm=True, **_FAST)

        after = fake.osc_packets_received

    assert after - before == 2  # one SET, one read-back GET
    assert result.dry_run is False
    assert result.sent == "-6.0"
    assert result.readback == -6.0
    assert result.matched is True


def test_confirmed_set_honours_an_explicit_typetag_override():
    # design doc sec 2.6: /ch/40/fdr ,f -6.0 is one of the three confirmed
    # working wire forms.
    address = "/ch/40/fdr"
    with FakeWing() as fake:
        fake.register(encode(address, "f", (-6.0,)), None)
        fake.register(encode(address), _sff(address, "-6.0", -6.0))
        host, osc_port, identity_port = _addrs(fake)

        result = write.set(host, address, -6.0, typetag="f", osc_port=osc_port,
                            identity_port=identity_port, confirm=True, **_FAST)

    assert result.matched is True


def test_read_back_mismatch_is_reported_not_swallowed():
    # design doc sec 2.6: the console clamps silently and still answers a
    # per-leaf set -- the read-back is what must catch it.
    address = "/ch/40/fdr"
    with FakeWing() as fake:
        fake.register(encode(address, "s", ("999",)), None)
        fake.register(encode(address), _sff(address, "10.0", 10.0))  # clamped
        host, osc_port, identity_port = _addrs(fake)

        result = write.set(host, address, 999, osc_port=osc_port,
                            identity_port=identity_port, confirm=True, **_FAST)

    assert result.readback == 10.0
    assert result.matched is False


# -- toggle(): ,i -1, no target value to match -------------------------------


def test_toggle_dry_run_sent_text_is_minus_one():
    assert write.toggle("127.0.0.1", "/ch/40/mute", confirm=False).sent == "-1"


def test_confirmed_toggle_sends_i_minus_one_and_reads_back():
    address = "/ch/40/mute"
    with FakeWing() as fake:
        fake.register(encode(address, "i", (-1,)), None)
        fake.register(encode(address), _sfi(address, "0", 0))
        host, osc_port, identity_port = _addrs(fake)

        result = write.toggle(host, address, osc_port=osc_port,
                               identity_port=identity_port, confirm=True, **_FAST)

    assert result.sent == "-1"
    assert result.readback == 0
    assert result.matched is True  # a live reply is toggle's whole verification


# -- node_write(): /* OK, error payloads, unrecognised is still an error ----


def test_node_write_success_is_recognised_from_the_slash_star_ok_payload():
    node, params = "/ch/40", {"fdr": -3.0, "mute": 1}
    with FakeWing() as fake:
        payload = "fdr=-3.0,mute=1"
        fake.register(encode(node, "s", (payload,)), _s("/*", "OK"))
        fake.register(encode(f"{node}/fdr"), _sff(f"{node}/fdr", "-3.0", -3.0))
        fake.register(encode(f"{node}/mute"), _sfi(f"{node}/mute", "1", 1))
        host, osc_port, identity_port = _addrs(fake)

        result = write.node_write(host, node, params, osc_port=osc_port,
                                   identity_port=identity_port, confirm=True, **_FAST)

    assert result.payload == payload
    assert result.ok is True
    assert result.error is None
    assert result.verified == {"fdr": True, "mute": True}


@pytest.mark.parametrize(
    "error_text",
    ["NODE NOT FOUND", "VALUE ERROR", "NODE IS NOT PAR",  # sec 2.6: observed
     "BUFFER OVERFLOW", "SOMETHING THIS MODULE HAS NEVER SEEN"],  # not observed
)
def test_node_write_any_non_ok_payload_is_an_error(error_text):
    node, params = "/ch/40", {"proc": "NOPE"}
    with FakeWing() as fake:
        fake.register(encode(node, "s", ("proc=NOPE",)), _s("/*", error_text))
        host, osc_port, identity_port = _addrs(fake)

        result = write.node_write(host, node, params, osc_port=osc_port,
                                   identity_port=identity_port, confirm=True, **_FAST)

    assert result.ok is False
    assert result.error == error_text
    assert result.verified == {}


def test_node_write_ok_reply_with_a_clamped_readback_is_still_a_mismatch():
    # design doc sec 2.6's own example: fdr=999 -> reply OK, but the fader
    # actually landed at the clamp, +10.0 -- OK is not proof.
    node, params = "/ch/40", {"fdr": 999}
    with FakeWing() as fake:
        fake.register(encode(node, "s", ("fdr=999",)), _s("/*", "OK"))
        fake.register(encode(f"{node}/fdr"), _sff(f"{node}/fdr", "10.0", 10.0))
        host, osc_port, identity_port = _addrs(fake)

        result = write.node_write(host, node, params, osc_port=osc_port,
                                   identity_port=identity_port, confirm=True, **_FAST)

    assert result.ok is True
    assert result.verified == {"fdr": False}


# -- push(): landed / mismatched / absent are three distinct outcomes ------


def test_push_reports_landed_mismatched_and_absent_distinctly():
    leaves = {
        "/ch/1/name": "PROBE",       # will read back matching -> landed
        "/ch/2/fdr": -6.0,           # will read back different -> mismatched
        "/ch/3/mute": 1,             # never answers -> absent (sec 2.7)
    }
    with FakeWing() as fake:
        fake.register(encode("/ch/1/name", "s", ("PROBE",)), None)
        fake.register(encode("/ch/1/name"), _s("/ch/1/name", "PROBE"))
        fake.register(encode("/ch/2/fdr", "s", ("-6.0",)), None)
        fake.register(encode("/ch/2/fdr"), _sff("/ch/2/fdr", "-3.0", -3.0))
        fake.register(encode("/ch/3/mute", "s", ("1",)), None)
        # /ch/3/mute's GET is deliberately never registered: sec 2.4(b)'s
        # "GET on a missing address is silent", sec 2.7's "genuinely absent".
        host, osc_port, identity_port = _addrs(fake)

        result = write.push(host, leaves, osc_port=osc_port,
                             identity_port=identity_port, confirm=True, **_FAST)

    assert result.landed == ("/ch/1/name",)
    assert result.mismatched == {"/ch/2/fdr": (-6.0, -3.0)}
    assert result.absent == ("/ch/3/mute",)
    assert result.dry_run is False


# -- sec 6.3: optional serial pin --------------------------------------------


def test_serial_pin_refuses_a_non_matching_console(monkeypatch):
    monkeypatch.setenv("WING_WRITE_ALLOW_SERIAL", "SOME-OTHER-SERIAL")
    address = "/ch/40/fdr"
    with FakeWing() as fake:
        fake.register(encode(address, "s", ("-6.0",)), None)
        fake.register(encode(address), _sff(address, "-6.0", -6.0))
        host, osc_port, identity_port = _addrs(fake)
        osc_before = fake.osc_packets_received

        with pytest.raises(write.SerialMismatchError):
            write.set(host, address, -6.0, osc_port=osc_port,
                      identity_port=identity_port, confirm=True, **_FAST)

        osc_after = fake.osc_packets_received

    # Refused before the SET packet -- only the identity echo went out.
    assert osc_after == osc_before


def test_serial_pin_permits_a_matching_console(monkeypatch):
    monkeypatch.setenv("WING_WRITE_ALLOW_SERIAL", _REAL_SERIAL)
    address = "/ch/40/fdr"
    with FakeWing() as fake:
        fake.register(encode(address, "s", ("-6.0",)), None)
        fake.register(encode(address), _sff(address, "-6.0", -6.0))
        host, osc_port, identity_port = _addrs(fake)

        result = write.set(host, address, -6.0, osc_port=osc_port,
                            identity_port=identity_port, confirm=True, **_FAST)

    assert result.matched is True


def test_serial_pin_is_off_by_default(monkeypatch):
    monkeypatch.delenv("WING_WRITE_ALLOW_SERIAL", raising=False)
    address = "/ch/40/fdr"
    with FakeWing() as fake:
        fake.register(encode(address, "s", ("-6.0",)), None)
        fake.register(encode(address), _sff(address, "-6.0", -6.0))
        host, osc_port, identity_port = _addrs(fake)

        result = write.set(host, address, -6.0, osc_port=osc_port,
                            identity_port=identity_port, confirm=True, **_FAST)

    assert result.matched is True
