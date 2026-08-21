import pytest

from tests.fake_wing import FakeWing
from wing_parser.net.identity import IdentityError, parse_identity, query_identity

# The recorded WING? reply (design doc sec 2.1 / tests/data/wing_osc_fixtures.json
# "identity"). Not the lab console's real IP/name/serial for their own sake --
# just the fixed string this whole test file parses and re-parses.
_RAW_REPLY = (
    b"WING,192.168.128.28,WING-GIAQUY,wing-rack,"
    b"01009Y90604AAE,3.1-0-g9f314617:release"
)


def test_parse_identity_fills_all_five_fields_exactly():
    identity = parse_identity(_RAW_REPLY)

    assert identity.ip == "192.168.128.28"
    assert identity.name == "WING-GIAQUY"
    assert identity.model == "wing-rack"
    assert identity.serial == "01009Y90604AAE"
    assert identity.firmware == "3.1-0-g9f314617:release"


def test_query_identity_against_the_fake_matches_the_recorded_fixture():
    with FakeWing() as fake:
        host, port = fake.identity_address
        identity = query_identity(host, port=port, timeout=1.0)

    assert identity.ip == "192.168.128.28"
    assert identity.name == "WING-GIAQUY"
    assert identity.model == "wing-rack"
    assert identity.serial == "01009Y90604AAE"
    assert identity.firmware == "3.1-0-g9f314617:release"


@pytest.mark.parametrize(
    "raw",
    [
        pytest.param(b"NOPE,192.168.128.28,WING-GIAQUY,wing-rack,x,y", id="wrong-prefix"),
        pytest.param(b"WING,192.168.128.28,WING-GIAQUY", id="too-few-fields"),
        pytest.param(b"WING,", id="prefix-only-empty-field"),
    ],
)
def test_parse_identity_rejects_malformed_replies_instead_of_guessing(raw):
    # A half-filled WingIdentity would be worse than an exception here --
    # sec 6.2 makes this parse the write-safety identity echo, so a wrong
    # partial parse could let a write land on the wrong console silently.
    with pytest.raises(IdentityError):
        parse_identity(raw)


def test_query_identity_rejects_a_malformed_reply_end_to_end():
    with FakeWing() as fake:
        fake.register_identity(b"WING?", b"NOT,EVEN,CLOSE")
        host, port = fake.identity_address
        with pytest.raises(IdentityError):
            query_identity(host, port=port, timeout=1.0)


def test_query_identity_times_out_clearly_when_the_console_stays_silent():
    with FakeWing() as fake:
        # Overrides the default reply with silence -- same shape as sec
        # 2.4(b)'s "no reply at all" cases, just triggered on demand.
        fake.register_identity(b"WING?", None)
        host, port = fake.identity_address

        with pytest.raises(TimeoutError):
            query_identity(host, port=port, timeout=0.2)


def test_a_timeout_does_not_hang_the_test_suite():
    # Belt and suspenders on the above: an explicit short timeout plus
    # an assertion that we actually got here proves this is a fast
    # error path, not a slow one that happens to finish before pytest's
    # own default timeout (there isn't one).
    with FakeWing() as fake:
        fake.register_identity(b"WING?", None)
        host, port = fake.identity_address

        with pytest.raises(TimeoutError, match=str(port)):
            query_identity(host, port=port, timeout=0.1)
