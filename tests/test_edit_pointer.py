"""Reading and writing one leaf of a .snap document by dotted path.

Every path asserted here was read out of `user-files/example-Vu.snap`
on 2026-08-18, not assumed from the schema.
"""

import json

import pytest

from wing_parser.edit import pointer


@pytest.fixture
def doc(vu_path):
    return json.loads(vu_path.read_text(encoding="utf-8"))


def test_read_walks_a_real_path(doc):
    assert pointer.read(doc, "ae_data.ch.16.in.set.inv") is False
    assert pointer.read(doc, "ae_data.ch.1.send.8.mode") == "POST"


def test_write_replaces_a_leaf_in_place(doc):
    pointer.write(doc, "ae_data.ch.16.in.set.inv", True)
    assert doc["ae_data"]["ch"]["16"]["in"]["set"]["inv"] is True


def test_read_names_the_whole_path_it_got_as_far_as(doc):
    with pytest.raises(KeyError, match="ae_data.ch.999"):
        pointer.read(doc, "ae_data.ch.999.mute")


def test_write_refuses_to_create_a_missing_key(doc):
    # A scene saved by different firmware may legitimately lack a key.
    # Inventing it writes a structure the console never had.
    with pytest.raises(KeyError, match="ae_data.ch.1.invented"):
        pointer.write(doc, "ae_data.ch.1.invented.deeper", 1)
    assert "invented" not in doc["ae_data"]["ch"]["1"]


def test_write_refuses_a_missing_leaf_without_creating_it(doc):
    with pytest.raises(KeyError, match="ae_data.ch.1.nosuchleaf"):
        pointer.write(doc, "ae_data.ch.1.nosuchleaf", 1)
    assert "nosuchleaf" not in doc["ae_data"]["ch"]["1"]


def test_read_refuses_to_walk_through_a_non_mapping(doc):
    # `name` is a string. Asking for a key inside it must raise KeyError
    # naming the path, not a TypeError from somewhere deeper.
    with pytest.raises(KeyError, match="ae_data.ch.1.name"):
        pointer.read(doc, "ae_data.ch.1.name.oops")


def test_a_single_segment_path_reads_a_top_level_key(doc):
    assert pointer.read(doc, "type") == doc["type"]
