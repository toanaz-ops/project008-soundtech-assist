"""Spec §9.1: the write seam, against `FakeDesk`. No socket anywhere.

The load-bearing test here is the normalisation pair. Eight of the eleven
repair descriptors set a JSON bool (`repairs.yaml` lines 55, 68, 80, 93,
102, 130, 142, 156), a `,sfi` leaf reads back as a Python `int`
(`codec.py:126-128`), and an unnormalised read would hand the countdown
`0` against a journal `before` of `False` -- shown to an operator at 2 a.m.
as the nonsense "the desk holds 0, the scene file expected False".
"""
from __future__ import annotations

import pytest

from tests.fake_desk import FakeDesk
from wing_parser.net.codec import OscMessage
from wing_parser.net.identity import WingIdentity
from wing_parser.ui import live_write

HOST = "192.168.128.28"
BOOL_PATH = "ae_data.ch.1.in.set.inv"          # a boolean shape in wing_jsontypes.yaml
BOOL_OSC = "/ch/1/in/set/inv"


def _identity():
    return WingIdentity(ip=HOST, name="WING-GIAQUY", model="wing-rack",
                        serial="01009Y90604AAE", firmware="3.1-0-g9f314617:release")


def _desk(**kwargs):
    return FakeDesk(identity=_identity(), **kwargs)


def _sfi(address, display, native):
    return OscMessage(address, "sfi", (display, 0.0, native))


def _sff(address, display, native):
    return OscMessage(address, "sff", (display, 0.0, native))


def _confirmation(desk, path, after, desk_before=None):
    from wing_parser.net.address import osc_address
    return live_write.WriteConfirmation(
        host=HOST, address=osc_address(path), after=after,
        identity=_identity(), desk_before=desk_before)


# -- preflight ----------------------------------------------------------


def test_preflight_returns_the_identity_and_the_desks_current_value():
    desk = _desk(leaves={BOOL_OSC: _sfi(BOOL_OSC, "1", 1)})
    identity, current = live_write.preflight(HOST, BOOL_PATH, desk.write_transport())
    assert identity.name == "WING-GIAQUY"
    assert current is True


def test_a_timeout_from_identity_propagates_untranslated():
    desk = FakeDesk(identity=TimeoutError("no reply from 192.168.128.28"))
    with pytest.raises(TimeoutError):
        live_write.preflight(HOST, BOOL_PATH, desk.write_transport())


# -- normalisation, one test per JSON type (§4) -------------------------


@pytest.mark.parametrize("native,expected", [(1, True), (0, False)])
def test_a_boolean_shape_reads_back_as_a_bool_not_an_int(native, expected):
    desk = _desk(leaves={BOOL_OSC: _sfi(BOOL_OSC, str(native), native)})
    _identity_, current = live_write.preflight(HOST, BOOL_PATH, desk.write_transport())
    assert current is expected
    assert current == expected, "a journal `before` of True/False must compare equal"
    assert not isinstance(current, int) or isinstance(current, bool)


def test_a_non_boolean_sfi_leaf_stays_an_int():
    path, osc = "ae_data.ch.1.dyn.ratio", "/ch/1/dyn/ratio"
    desk = _desk(leaves={osc: _sfi(osc, "3", 2)})
    _i, current = live_write.preflight(HOST, path, desk.write_transport())
    assert current == 3 and isinstance(current, int) and not isinstance(current, bool)


def test_an_sff_leaf_stays_a_float():
    path, osc = "ae_data.ch.1.fdr", "/ch/1/fdr"
    desk = _desk(leaves={osc: _sff(osc, "-6.0", -6.0)})
    _i, current = live_write.preflight(HOST, path, desk.write_transport())
    assert current == pytest.approx(-6.0) and isinstance(current, float)


def test_an_s_leaf_stays_a_str():
    path, osc = "ae_data.ch.1.send.8.mode", "/ch/1/send/8/mode"
    desk = _desk(leaves={osc: OscMessage(osc, "s", ("POST",))})
    _i, current = live_write.preflight(HOST, path, desk.write_transport())
    assert current == "POST" and isinstance(current, str)


# -- scene_value, one test per JSON type (F8) ---------------------------


@pytest.mark.parametrize("readback,expected", [(1, True), (0, False)])
def test_scene_value_coerces_a_boolean_shape(readback, expected):
    assert live_write.scene_value(["ch", "1", "in", "set", "inv"], readback) is expected


def test_scene_value_leaves_a_non_boolean_int_alone():
    assert live_write.scene_value(["ch", "1", "dyn", "ratio"], 3) == 3


def test_scene_value_leaves_a_float_and_a_string_alone():
    assert live_write.scene_value(["ch", "1", "fdr"], -6.0) == pytest.approx(-6.0)
    assert live_write.scene_value(["ch", "1", "send", "8", "mode"], "PRE") == "PRE"


def test_scene_value_passes_a_missing_readback_through_as_none():
    assert live_write.scene_value(["ch", "1", "in", "set", "inv"], None) is None


# -- send ---------------------------------------------------------------


def test_send_transmits_confirm_true_the_mapped_address_and_one_value():
    desk = _desk(leaves={"/ch/1/send/8/mode": OscMessage("/ch/1/send/8/mode", "s", ("PRE",))},
                 readbacks={"/ch/1/send/8/mode": "PRE"})
    result = live_write.send(
        _confirmation(desk, "ae_data.ch.1.send.8.mode", "PRE"), desk.write_transport())
    assert desk.sets == [("/ch/1/send/8/mode", "PRE", True)]
    assert result.matched is True


@pytest.mark.parametrize("bad", [None, "not a confirmation", {"address": "/ch/1/fdr"}])
def test_send_refuses_anything_but_a_write_confirmation(bad):
    desk = _desk()
    with pytest.raises(TypeError):
        live_write.send(bad, desk.write_transport())
    assert desk.sets == []


def test_send_refuses_when_the_desk_serial_changed_since_preflight():
    """Gate 4's second half: the confirmation names a desk, and `send`
    proves the desk still answering is that one before it transmits.

    Without it the operator confirms against WING-GIAQUY, a DHCP lease or
    a swapped cable puts another console on that address, and the packet
    lands on a stranger's mix -- `write.set`'s own `_authorize` cannot
    catch it, because `WING_WRITE_ALLOW_SERIAL` is unset in this app.
    """
    import dataclasses

    desk = _desk(leaves={BOOL_OSC: _sfi(BOOL_OSC, "1", 1)})
    transport = desk.write_transport()
    identity, _current = live_write.preflight(HOST, BOOL_PATH, transport)

    desk.identity = dataclasses.replace(
        identity, name="WING-OTHER", serial="02FEEDFACE0000")

    confirmation = live_write.WriteConfirmation(
        host=HOST, address=BOOL_OSC, after=False,
        identity=identity, desk_before=True)
    with pytest.raises(live_write.DeskChanged) as exc:
        live_write.send(confirmation, transport)
    assert "01009Y90604AAE" in str(exc.value), "the serial confirmed against"
    assert "02FEEDFACE0000" in str(exc.value), "the serial answering now"
    assert desk.sets == [], "nothing may reach the wire once the desk changed"


def test_send_transmits_when_the_desk_is_still_the_confirmed_one():
    desk = _desk(readbacks={BOOL_OSC: 1})
    live_write.send(_confirmation(desk, BOOL_PATH, True), desk.write_transport())
    assert desk.sets == [(BOOL_OSC, True, True)]


def test_a_serial_mismatch_reaches_the_caller_with_its_own_text():
    from wing_parser.net.write import SerialMismatchError

    desk = _desk()
    transport = desk.write_transport()

    def refusing(host, osc, value, *, confirm=False, **kw):
        raise SerialMismatchError("refusing to write to 'WING-GIAQUY' (serial 'X')")

    import dataclasses
    transport = dataclasses.replace(transport, set=refusing)
    with pytest.raises(SerialMismatchError) as exc:
        live_write.send(_confirmation(desk, BOOL_PATH, True), transport)
    assert "refusing to write to 'WING-GIAQUY'" in str(exc.value)


# -- the seam itself ----------------------------------------------------


def test_real_transport_names_the_read_only_entry_points_and_write_set():
    # Imported HERE, never at module scope: this assertion is the one place
    # a test needs the real write module, and `set` is the only verb it may
    # be wired to (W4). `tests/` is outside the AST scan either way.
    from wing_parser.net import write
    from wing_parser.net.identity import query_identity

    assert live_write.REAL.identity is query_identity
    assert live_write.REAL.set is write.set
    assert callable(live_write.REAL.read)
