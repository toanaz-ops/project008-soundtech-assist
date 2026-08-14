from wing_parser.query.build_blocks import build_sends, parse_send_key


def test_parse_send_key():
    assert parse_send_key("8") == ("bus", 8)
    assert parse_send_key("16") == ("bus", 16)
    assert parse_send_key("MX1") == ("matrix", 1)
    assert parse_send_key("MX8") == ("matrix", 8)


def test_parse_send_key_returns_none_for_a_key_of_neither_form():
    assert parse_send_key("") is None
    assert parse_send_key("MXfoo") is None
    assert parse_send_key("bus7") is None


def test_malformed_send_key_is_reported_not_raised():
    sends, anomalies = build_sends({"8": {"on": True}, "MXfoo": {"on": True}})
    assert [(s.dest_kind, s.dest) for s in sends] == [("bus", 8)]
    assert len(anomalies) == 1
    assert anomalies[0].code == "malformed_send_key"
    assert "MXfoo" in anomalies[0].where
