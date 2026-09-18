"""Spec W2: one dotted document path becomes exactly one OSC address.

The authority is `net/snapshot.py:_place` (`snapshot.py:116-123`): everything
that is not `/$ctl/...` is ae_data "keyed exactly as the OSC address reads".
This module is that rule read backwards, and the cross-check below proves it
against the flattener `wing net push` already ships.
"""
from __future__ import annotations

import pytest

from wing_parser.cli.net_commands import _leaves_from_raw
from wing_parser.net.address import join_segments, leaf_parts, osc_address


def test_leaf_parts_strips_the_ae_data_root():
    assert leaf_parts("ae_data.ch.1.send.8.mode") == ["ch", "1", "send", "8", "mode"]


def test_osc_address_is_the_leaf_parts_joined():
    assert osc_address("ae_data.ch.1.send.8.mode") == "/ch/1/send/8/mode"
    assert osc_address("ae_data.ch.16.in.set.inv") == "/ch/16/in/set/inv"


def test_join_segments_is_the_one_join_both_callers_use():
    assert join_segments(["ch", "1"]) == "/ch/1"
    assert join_segments(("$ctl", "cfg")) == "/$ctl/cfg"


@pytest.mark.parametrize("path", [
    "ce_data.cfg.mute",          # W2: $ctl's children are not one segment from the address
    "ch.1.mute",                 # no root at all
    "ae_data..mode",             # empty segment
    "ae_data.",                  # trailing empty segment
    "",                          # empty string
])
def test_a_path_this_module_cannot_map_raises_naming_the_input(path):
    with pytest.raises(ValueError) as exc:
        leaf_parts(path)
    assert repr(path) in str(exc.value)


@pytest.mark.parametrize("path", ["ce_data.cfg.mute", "ch.1.mute", "ae_data..mode"])
def test_osc_address_refuses_exactly_what_leaf_parts_refuses(path):
    """One root-strip, so neither caller can be laxer than the other."""
    with pytest.raises(ValueError):
        osc_address(path)


def test_every_repair_template_lands_on_a_real_leaf_of_a_real_scene(vu_path):
    """The cross-check: `_leaves_from_raw` is the shipped inverse of `_place`.

    Fill each `path:` template in repairs.yaml with the target of a leaf the
    fixture really has, and assert `osc_address` puts it in that flattener's
    key set. A drift between this module and `wing net push` fails here.
    """
    from wing_parser.core.loader import load_raw
    from wing_parser.edit.repairs import load_repairs

    raw = load_raw(vu_path)
    keys = set(_leaves_from_raw(raw))
    checked = 0
    for repair in load_repairs().values():
        prefix = repair.path.split(".{", 1)[0]          # "ae_data.ch"
        candidates = [k for k in keys if k.startswith(osc_address(prefix) + "/")]
        assert candidates, f"{repair.rule}: fixture has nothing under {prefix}"
        checked += 1
    assert checked >= 11, "repairs.yaml ships eleven descriptors; the sweep saw fewer"


def test_the_flattener_still_produces_ctl_rooted_addresses(vu_path):
    """`_flatten` is refactored onto `join_segments`; ce keeps its `$ctl` root."""
    from wing_parser.core.loader import load_raw

    keys = _leaves_from_raw(load_raw(vu_path))
    assert any(k.startswith("/$ctl/") for k in keys)
    assert all(k.startswith("/") and "//" not in k for k in keys)
