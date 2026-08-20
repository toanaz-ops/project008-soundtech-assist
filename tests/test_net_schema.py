"""Tests for wing_parser.net.schema, driven only against tests/fake_wing.py
-- no test here touches a real socket to a real console (design doc S7).

The 74 recorded exchanges in wing_osc_fixtures.json cover several real
`,s ?` replies (schema/ch/1 and its children) but no fixture was ever
recorded for `,s ?` on a *container* address like /ch itself -- the real
console was never probed at that exact node during capture. Tests here
register that one missing link at runtime via `fake.register()` (exactly
what its docstring says it is for), then let the walk reach real recorded
text for everything below it.
"""

from __future__ import annotations

from tests.fake_wing import FakeWing
from wing_parser.net.codec import encode
from wing_parser.net.schema import walk_schema

# Short idle gaps so the several roots this module always seeds but a test
# never registers (S2.2's other ae roots) time out in milliseconds, not
# the console-sized 0.2s default.
FAST = dict(batch_size=200, retry_rounds=1, idle_timeout=0.03)


def _schema_tx(address: str) -> bytes:
    return encode(address, "s", ("?",))


def _schema_rx(address: str, body: str) -> bytes:
    return encode(address, "s", (body,))


def test_walk_finds_children_and_leaves_and_skips_dollar_names_but_descends_ctl():
    with FakeWing() as fake:
        fake.register(_schema_tx("/ch"), _schema_rx("/ch", "  1              (node)\n"))
        fake.register(
            _schema_tx("/ch/1"),
            _schema_rx(
                "/ch/1",
                "  fdr            fader [-oo .. 10.0 dB], 1024 steps\n"
                "  flt            (node)\n"
                "  $col           int [1 .. 18]\n",
            ),
        )
        fake.register(
            _schema_tx("/ch/1/flt"),
            _schema_rx("/ch/1/flt", "  lcf            log [20.0 .. 2k00 Hz], 641 steps\n"),
        )
        # /$ctl itself must be descended into despite the "$" -- the one
        # named exception in S2.2 -- but its OWN $-prefixed child ($stat)
        # must still be skipped even though its line says "(node)".
        fake.register(
            _schema_tx("/$ctl"),
            _schema_rx("/$ctl", "  cfg            (node)\n  $stat          (node)\n"),
        )
        fake.register(
            _schema_tx("/$ctl/cfg"), _schema_rx("/$ctl/cfg", "  on             int [0 .. 1]\n")
        )

        host, port = fake.osc_address
        result = walk_schema(host, port, **FAST)

    # A subset check, not equality: this module seeds every ae root, and a
    # root this test never registers falls through to the `,s *` recovery,
    # which the fixture file DOES answer for several of them. That recovery
    # is the intended behaviour (see the dump-fallback test below), so the
    # assertion pins what the walk must find rather than what it must not.
    assert result.leaves["/ch/1/fdr"] == "fader [-oo .. 10.0 dB], 1024 steps"
    assert result.leaves["/ch/1/flt/lcf"] == "log [20.0 .. 2k00 Hz], 641 steps"
    assert result.leaves["/$ctl/cfg/on"] == "int [0 .. 1]"
    # $col is a read-only shadow of col (S2.2) and must never surface as a leaf.
    assert not any(addr.startswith("/ch/1/$col") for addr in result.leaves)
    # $stat is skipped even though its own line says "(node)" -- /$ctl is
    # the *only* exception to the $-skip rule, not a license for its children.
    assert not any(addr.startswith("/$ctl/$stat") for addr in result.leaves)
    assert "/$ctl/$stat" not in result.unresolved_nodes  # never queried at all


def test_a_node_that_never_answers_is_reported_not_silently_dropped():
    with FakeWing() as fake:
        fake.register(
            _schema_tx("/ch"), _schema_rx("/ch", "  1              (node)\n  2              (node)\n")
        )
        fake.register(
            _schema_tx("/ch/1"), _schema_rx("/ch/1", "  fdr            fader [-oo .. 10.0 dB], 1024 steps\n")
        )
        # /ch/2 is deliberately never registered -- a silent node, S2.4(b)'s
        # "GET on an address that does not exist is harmless" case.
        host, port = fake.osc_address
        result = walk_schema(host, port, **FAST)

    # /ch/2 answers neither `,s ?` nor the `,s *` recovery, so it stays
    # unresolved -- which is the distinction that matters: a node the
    # console cannot describe at all must remain visible to the caller.
    assert "/ch/2" in result.unresolved_nodes
    assert result.leaves["/ch/1/fdr"] == "fader [-oo .. 10.0 dB], 1024 steps"
    assert not any(addr.startswith("/ch/2/") for addr in result.leaves)


def test_walk_reaches_a_real_recorded_multi_level_subtree():
    # schema/ch/1, schema/ch/1/in and schema/ch/1/in/conn are real replies
    # captured from the lab console (design doc S2.3); only the /ch ->
    # /ch/1 link at the very top was never recorded, so it is the one
    # thing this test supplies itself.
    with FakeWing() as fake:
        fake.register(_schema_tx("/ch"), _schema_rx("/ch", "  1              (node)\n"))
        host, port = fake.osc_address
        result = walk_schema(host, port, **FAST)

    # /ch/1/in/conn/in is exactly the leaf design doc S2.3 flags as the
    # recorded ,sfi disagreement fixture (get/ch/1/in/conn/in) -- proving
    # the schema walk reaches the very address the value-conversion test
    # depends on, via nothing but real recorded ,s ? text.
    assert result.leaves["/ch/1/in/conn/in"] == "int [1 .. 64]"
    assert result.leaves["/ch/1/flt/lcf"] == "log [20.0 .. 2k00 Hz], 641 steps"
    assert result.leaves["/ch/1/fdr"] == "fader [-oo .. 10.0 dB], 1024 steps"
    # $-prefixed children of /ch/1 (schema/ch/1's own $col, $name, ...)
    # must never surface, on a real reply just as much as a synthetic one.
    assert not any(addr.startswith("/ch/1/$") for addr in result.leaves)


def test_a_node_whose_schema_overflows_is_recovered_from_its_dump():
    """S2.4's ceiling bites hardest on a loaded effect slot: measured on the
    console, `/fx/1` holding a VSS3 reverb could not answer `,s ?` at all,
    while its `,s *` dump came back in 338 characters listing all 34
    parameters. Falling back to the dump for the key NAMES is what takes a
    live walk from 27 unresolved nodes to none.

    Only names are taken. A dump's values are lossy display text (S2.3) and
    every value still comes from a per-leaf read, so the recovered leaves
    carry an empty declared type rather than a fabricated one.
    """
    with FakeWing() as fake:
        fake.register(_schema_tx("/fx"), _schema_rx("/fx", "  1              (node)\n"))
        fake.register(_schema_tx("/fx/1"), None)  # oversized: no reply at all
        fake.register(
            encode("/fx/1", "s", ("*",)),
            encode("/fx/1", "s", ("mdl=VSS3,fxmix=100,dcy=2.5,",)),
        )
        host, port = fake.osc_address
        result = walk_schema(host, port, **FAST)

    assert "/fx/1" not in result.unresolved_nodes
    assert result.leaves["/fx/1/mdl"] == ""
    assert result.leaves["/fx/1/fxmix"] == ""
    assert result.leaves["/fx/1/dcy"] == ""


def test_a_node_answering_neither_schema_nor_dump_stays_unresolved():
    with FakeWing() as fake:
        fake.register(_schema_tx("/fx"), _schema_rx("/fx", "  9              (node)\n"))
        fake.register(_schema_tx("/fx/9"), None)
        fake.register(encode("/fx/9", "s", ("*",)), None)
        host, port = fake.osc_address
        result = walk_schema(host, port, **FAST)

    assert "/fx/9" in result.unresolved_nodes
    assert not any(addr.startswith("/fx/9/") for addr in result.leaves)
