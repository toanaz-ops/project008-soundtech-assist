"""Tests for wing_parser.net.export.to_snap_json (design doc S5).

Offline: driven from the two committed reference files (via the
session-scoped `vu_path`/`factory_path` fixtures in tests/conftest.py)
and small handwritten RawScene fixtures. No test here touches a console.
"""

from __future__ import annotations

import collections
import json
import re

from wing_parser.core.loader import RawScene, load_raw
from wing_parser.core.versions import load_registry, resolve
from wing_parser.net.export import to_snap_json
from wing_parser.net.identity import WingIdentity

_INTEGRAL_FLOAT_LITERAL = re.compile(r':\s*-?\d+\.0\b')


def _leaf_types(node, parts, out):
    """Flatten a nested ae_data/ce_data tree to {shape-path-tuple: type name}."""
    if isinstance(node, dict):
        for key, value in node.items():
            _leaf_types(value, parts + [key], out)
    else:
        out[tuple(parts)] = type(node).__name__


def _shape(parts):
    return "/".join("*" if p.isdigit() else p for p in parts)


def _known_mixed_shapes(vu_path, factory_path):
    """Shapes written as `int` in one reference file and `bool` in the
    other -- recomputed here from *both* files together, the same way
    examples/generate_jsontypes.py builds the oracle, rather than
    hardcoded, so this stays correct if the reference files ever change.
    A shape's kind set has to be pooled across both files: within either
    file alone every leaf of a given shape already agrees with itself, so
    the disagreement only shows up by comparing the two.

    Design doc S5: these are the 18 send-`plink` shapes WING itself is
    not consistent about. `to_snap_json` always resolves them to `bool`
    (net/export.py's docstring explains why), so a round-trip test must
    treat them as a named, expected exception rather than a failure.
    """
    kinds = collections.defaultdict(set)
    for path in (vu_path, factory_path):
        doc = json.loads(path.read_text(encoding="utf-8"))
        types: dict[tuple, str] = {}
        _leaf_types(doc.get("ae_data") or {}, [], types)
        _leaf_types(doc.get("ce_data") or {}, ["$ctl"], types)
        for parts, kind in types.items():
            kinds[_shape(list(parts))].add(kind)
    return {shape for shape, seen in kinds.items() if seen == {"bool", "int"}}


def _round_trip_type_check(path, vu_path, factory_path):
    raw = load_raw(path)
    mixed = _known_mixed_shapes(vu_path, factory_path)

    original: dict[tuple, str] = {}
    _leaf_types(raw.ae, [], original)
    _leaf_types(raw.ce, ["$ctl"], original)

    rendered = json.loads(to_snap_json(raw))
    rebuilt: dict[tuple, str] = {}
    _leaf_types(rendered["ae_data"], [], rebuilt)
    _leaf_types(rendered["ce_data"], ["$ctl"], rebuilt)

    assert original.keys() == rebuilt.keys()
    mismatches = []
    for parts, before in original.items():
        after = rebuilt[parts]
        if before == after:
            continue
        if _shape(list(parts)) in mixed and before == "int" and after == "bool":
            continue  # the accepted S5 exception -- see _known_mixed_shapes
        mismatches.append((parts, before, after))
    assert mismatches == []


def test_round_trip_preserves_json_types_for_example_vu(vu_path, factory_path):
    _round_trip_type_check(vu_path, vu_path, factory_path)


def test_round_trip_preserves_json_types_for_factory_scene(vu_path, factory_path):
    # factory-scene.snap has zero int/bool disagreement within itself
    # (every plink leaf there is already bool), so this file's round trip
    # has no exceptions at all -- the strongest form of the check.
    _round_trip_type_check(factory_path, vu_path, factory_path)


def test_no_trailing_dot_zero_appears_for_an_integral_float(vu_path):
    raw = load_raw(vu_path)
    text = to_snap_json(raw)
    # design doc S5: WING's own convention, measured against both
    # reference files -- neither contains a single ":N.0".
    assert _INTEGRAL_FLOAT_LITERAL.search(text) is None


def test_a_known_boolean_shape_serialises_as_true_false():
    version = resolve("snapshot.11", load_registry())
    raw = RawScene(version=version, ae={"ch": {"1": {"eq": {"on": 1}}}}, ce={}, meta={})
    doc = json.loads(to_snap_json(raw))
    assert doc["ae_data"]["ch"]["1"]["eq"]["on"] is True


def test_a_known_non_boolean_int_shape_stays_an_int():
    version = resolve("snapshot.11", load_registry())
    # ch/*/col: a colour index, plain int, never boolean (S2.3's own
    # example of a ,sfi leaf whose native/display split matters).
    raw = RawScene(version=version, ae={"ch": {"1": {"col": 5}}}, ce={}, meta={})
    doc = json.loads(to_snap_json(raw))
    assert doc["ae_data"]["ch"]["1"]["col"] == 5
    assert doc["ae_data"]["ch"]["1"]["col"] is not True
    assert doc["ae_data"]["ch"]["1"]["col"] is not False


def test_output_is_valid_json_with_the_expected_top_level_keys():
    version = resolve("snapshot.11", load_registry())
    raw = RawScene(version=version, ae={"ch": {}}, ce={}, meta={})
    doc = json.loads(to_snap_json(raw))
    assert "ae_data" in doc
    assert "ce_data" in doc
    assert "type" in doc
    assert doc["type"] == "snapshot.11"


def test_no_identity_produces_an_honest_placeholder_not_a_fabricated_console():
    version = resolve("snapshot.11", load_registry())
    raw = RawScene(version=version, ae={}, ce={}, meta={}, source="wing://10.0.0.1")
    doc = json.loads(to_snap_json(raw))  # must not raise -- valid output with no identity
    for field in ("creator_model", "creator_name"):
        assert doc[field], f"{field} must not be blank"
        # Never a plausible-looking real console name -- the whole point
        # is that this process never measured one.
        assert doc[field] != "WING-GIAQUY"
        assert "unknown" in doc[field].lower()


def test_identity_fills_creator_model_and_name_when_given():
    version = resolve("snapshot.11", load_registry())
    identity = WingIdentity(
        ip="192.168.128.28",
        name="WING-GIAQUY",
        model="wing-rack",
        serial="01009Y90604AAE",
        firmware="3.1-0-g9f314617:release",
    )
    raw = RawScene(version=version, ae={}, ce={}, meta={}, source="wing://192.168.128.28")
    doc = json.loads(to_snap_json(raw, identity=identity))
    assert doc["creator_model"] == "wing-rack"
    assert doc["creator_name"] == "WING-GIAQUY"
    # Not invented: WingIdentity carries no editing-software name/version,
    # so those two fields still name this tool rather than guessing one.
    assert doc["creator"] == "wing-parser"


def test_the_declared_type_id_matches_the_envelope_actually_emitted():
    """`snapshot.11` is a claim about this exporter's output format, not a
    guess about the console. A console never writes a .snap at all --
    WING-Edit does, and the type id tracks ITS version: 3.0 writes
    snapshot.9, 3.2.1 snapshot.10, 3.3.3 snapshot.11, with genuinely
    different envelopes. So the id has to be checked against what we emit,
    or it silently becomes a lie the moment the envelope changes.
    """
    import json

    from wing_parser.core.loader import RawScene
    from wing_parser.core.versions import load_registry, resolve
    from wing_parser.net.export import to_snap_json
    from wing_parser.net.snapshot import SNAPSHOT_TYPE_ID

    registry = load_registry()
    raw = RawScene(
        version=resolve(SNAPSHOT_TYPE_ID, registry),
        ae={"cards": {"wlive": {}, "wmadi": {}}},
        ce={},
        meta={},
        source="wing://test",
    )
    doc = json.loads(to_snap_json(raw))

    declared = registry[SNAPSHOT_TYPE_ID]
    emitted = {k for k in doc if k not in ("ae_data", "ce_data")} - {"type"}
    assert emitted == set(declared.meta_keys)
    assert declared.has_globals is False
    assert not [k for k in doc if k.endswith("_globals")]
    assert set(doc["ae_data"]["cards"]) == set(declared.cards)
