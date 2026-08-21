"""Tests for wing_parser.net.nodetext, driven by the `dump/*` exchanges the
console actually sent (tests/data/wing_osc_fixtures.json), plus two DUMP
captures in tests/data/wing_write_fixtures.json -- `/dca` and `/mgrp` --
taken during the write probe while `/dca/16/name` and `/mgrp/8/name` were
still set to `A,B=C`. Design doc S2.7 documents that quoting rule, but the
read-only capture that produced wing_osc_fixtures.json ran after those names
were restored, so the quoted form only survives in the write fixtures.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from wing_parser.net.codec import decode
from wing_parser.net.nodetext import NodeTextError, parse_node_text

REPO_ROOT = Path(__file__).resolve().parents[1]
OSC_FIXTURES = json.loads(
    (REPO_ROOT / "tests" / "data" / "wing_osc_fixtures.json").read_text(encoding="utf-8")
)
EXCHANGES = OSC_FIXTURES["exchanges"]

# wing_write_fixtures.json is a *list* of {"label", "tx", "rx", "parsed"}
# entries, not the {"exchanges": {...}} mapping wing_osc_fixtures.json uses.
WRITE_FIXTURES = json.loads(
    (REPO_ROOT / "tests" / "data" / "wing_write_fixtures.json").read_text(encoding="utf-8")
)
WRITE_FIXTURES_BY_LABEL = {entry["label"]: entry for entry in WRITE_FIXTURES}

# Every `dump/*` exchange whose rx is not null (rx: null means the console
# sent no reply at all -- S2.4a's oversized-dump hazard, out of scope here).
DUMP_KEYS = sorted(
    k for k, v in EXCHANGES.items() if k.startswith("dump/") and v["rx"] is not None
)


def node_text_of(key: str) -> str:
    """Decode one fixture's rx hex down to the node-text body via codec.decode."""
    message = decode(bytes.fromhex(EXCHANGES[key]["rx"]))
    assert message.typetag == "s"
    return message.args[0]


def node_text_of_write(label: str) -> str:
    """Same as node_text_of, but for a labelled entry in the write fixtures."""
    message = decode(bytes.fromhex(WRITE_FIXTURES_BY_LABEL[label]["rx"]))
    assert message.typetag == "s"
    return message.args[0]


# --- the grammar's four moves, each on a real captured dump ----------------


def test_leading_key_with_a_dot_descends_and_a_plain_key_stays():
    # design doc S3's own worked example: `set.srcauto=0,altsrc=0,...`
    # -- altsrc has no dot, so it must land inside `set`, not at the root.
    tree = parse_node_text(node_text_of("dump/ch/1/in"))

    assert tree["set"]["srcauto"] == "0"
    assert tree["set"]["altsrc"] == "0"
    assert "altsrc" not in tree


def test_a_single_leading_dot_pops_one_level_before_descending():
    # same fixture, second half: `.conn.grp=LCL,in=1,...` -- the leading
    # dot must pop out of `set` first, so `conn` is a sibling of `set`,
    # not a child of it, and `in` stays inside `conn`.
    tree = parse_node_text(node_text_of("dump/ch/1/in"))

    assert "conn" not in tree["set"]
    assert tree["conn"]["grp"] == "LCL"
    assert tree["conn"]["in"] == "1"
    assert tree["conn"]["altgrp"] == "OFF"


def test_two_leading_dots_pop_two_levels():
    # design doc S3's `/mtx/1` example: `in.set.inv=0,trim=0.0,bal=0.0,
    # ..dir.on=0,...` -- `..dir` must land as a sibling of `in`, not
    # inside `in.set` (which one leading dot would give) or `in` (zero).
    tree = parse_node_text(node_text_of("dump/mtx/1"))

    assert tree["in"] == {"set": {"inv": "0", "trim": "0.0", "bal": "0.0"}}
    assert "dir" not in tree["in"]
    assert "dir" not in tree["in"]["set"]
    assert tree["dir"]["on"] == "0"
    assert tree["dir"]["in"] == "OFF"


def test_numeric_child_nodes_descend_like_named_ones():
    # `/ch/1/main`: `1.on=1,lvl=0.0,pre=0,.2.on=0,...` -- "1" and "2" are
    # child node names (fader-group indices), not something special.
    tree = parse_node_text(node_text_of("dump/ch/1/main"))

    assert tree["1"] == {"on": "1", "lvl": "0.0", "pre": "0"}
    assert tree["2"] == {"on": "0", "lvl": "0.0", "pre": "0"}
    assert tree["3"]["on"] == "0"
    assert tree["4"]["on"] == "0"


# --- quoting (S2.7) ---------------------------------------------------------


def test_dca_quoted_name_does_not_swallow_the_assignments_after_it():
    # Captured from the console (tests/data/wing_write_fixtures.json,
    # label "DUMP /dca ,s *"), taken while /dca/16/name was set to
    # A,B=C during the write probe. This is the sharpest version of the
    # "does the embedded comma end the token early" risk: the quoted
    # value sits in the MIDDLE of node 16, with six more assignments
    # after it, including a non-default fdr=-5.0.
    tree = parse_node_text(node_text_of_write("DUMP /dca ,s *"))

    assert tree["16"]["name"] == "A,B=C"
    assert tree["16"]["col"] == "1"
    assert tree["16"]["icon"] == "0"
    assert tree["16"]["led"] == "0"
    assert tree["16"]["mute"] == "0"
    assert tree["16"]["fdr"] == "-5.0"  # would read wrong if the comma split the token
    assert tree["16"]["mon"] == "A"

    # the sibling entry right before the quoted one must be unaffected
    assert tree["15"] == {
        "name": "", "col": "1", "icon": "0", "led": "0", "mute": "0",
        "fdr": "-oo", "mon": "A",
    }


def test_mgrp_quoted_name_as_the_last_entry_before_the_trailing_dot():
    # Same probe, label "DUMP /mgrp ,s *" -- here the quoted value is the
    # LAST node before the body's closing ".", so this covers the quote
    # interacting with end-of-body rather than a mid-line assignment.
    tree = parse_node_text(node_text_of_write("DUMP /mgrp ,s *"))

    assert tree["8"]["name"] == "A,B=C"
    assert tree["8"]["mute"] == "0"

    # the sibling entry right before the quoted one must be unaffected
    assert tree["7"] == {"name": "MGRP.7", "mute": "0"}


def test_a_captured_dump_with_quoted_values_parses_the_quotes_away():
    # `/$ctl/safes` quotes every value (S2.7 also covers plain-space
    # strings, not just ones containing `,`/`='). Spot-check one field
    # rather than the whole 700+ char body.
    tree = parse_node_text(node_text_of("dump/$ctl/safes"))

    assert tree["dca"] == " " * 16
    assert tree["source"]["LCL"] == " " * 8


# --- trailing "." (most dumps have one) -------------------------------------


@pytest.mark.parametrize("key", DUMP_KEYS)
def test_every_captured_dump_parses_without_raising(key):
    parse_node_text(node_text_of(key))


def test_trailing_dot_pops_without_adding_a_phantom_key():
    # `/ch/1/main` ends `...,pre=0,.` -- the trailing "." must not become
    # a key named "" or "." anywhere in the tree.
    tree = parse_node_text(node_text_of("dump/ch/1/main"))

    assert "" not in tree
    assert "." not in tree
    for child in tree.values():
        assert "" not in child
        assert "." not in child


def test_ch_1_eq_leaf_names_match_the_fixture_text_independently():
    # Cross-check against the fixture text itself, not against the parser's
    # own logic: split the raw body on top-level commas and take the part
    # before "=" for each token -- /ch/1/eq is flat (no nested nodes), so
    # this must equal the parsed key set exactly.
    text = node_text_of("dump/ch/1/eq")
    expected_keys = {token.split("=", 1)[0] for token in text.split(",") if token}

    tree = parse_node_text(text)

    assert set(tree.keys()) == expected_keys
    assert expected_keys == {
        "on", "mdl", "mix", "lg", "lf", "lq", "leq",
        "1g", "1f", "1q", "2g", "2f", "2q", "3g", "3f", "3q", "4g", "4f", "4q",
        "hg", "hf", "hq", "heq",
    }


# --- malformed bodies raise instead of returning a half-built dict --------


@pytest.mark.parametrize(
    "body",
    [
        pytest.param("a=1,,b=2", id="empty-token-mid-body"),
        pytest.param("a=1,..b=2", id="pops-past-the-root"),
        pytest.param("nokeyvalue", id="no-equals-sign"),
        pytest.param("a='unterminated,b=2", id="unterminated-quote"),
        pytest.param("a..b=1", id="empty-path-segment"),
    ],
)
def test_malformed_body_raises_instead_of_returning_a_partial_dict(body):
    with pytest.raises(NodeTextError):
        parse_node_text(body)


def test_raw_tokens_are_never_coerced_off_the_wire_text():
    # The module's whole reason to exist (design doc S2.3/S4): a node dump
    # is lossy display text, so nothing here may turn "-oo" into a float
    # sentinel or "10k02" into a number -- that would dress up a display
    # string as an exact value. Assert the literal strings survive.
    tree = parse_node_text(node_text_of("dump/ch/1/send"))
    assert tree["1"]["lvl"] == "-oo"
    assert isinstance(tree["1"]["lvl"], str)

    tree = parse_node_text(node_text_of("dump/ch/1/flt"))
    assert tree["hcf"] == "10k02"
