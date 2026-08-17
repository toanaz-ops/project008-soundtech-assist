"""The parse/load split that lets a scene be rebuilt from memory.

The desktop app re-derives the whole scene after every edit, from a
patched copy of the document it holds. Without this split it would have
to write a temporary file to do so.
"""

import json

import pytest

from wing_parser.core.loader import load_raw, parse_raw


def test_parse_raw_accepts_an_in_memory_document(vu_path):
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    from_memory = parse_raw(doc, vu_path)
    from_file = load_raw(vu_path)

    assert from_memory.ae == from_file.ae
    assert from_memory.ce == from_file.ce
    assert from_memory.meta == from_file.meta
    assert from_memory.version == from_file.version
    assert from_memory.path == vu_path


def test_parse_raw_refuses_a_document_that_is_not_a_snapshot(tmp_path):
    with pytest.raises(ValueError, match="not a WING snapshot"):
        parse_raw({"nothing": "here"}, tmp_path / "x.snap")


def test_parse_raw_refuses_a_non_mapping(tmp_path):
    with pytest.raises(ValueError, match="not a WING snapshot"):
        parse_raw([1, 2, 3], tmp_path / "x.snap")


def test_load_raw_still_reads_from_disk(vu_path):
    # The split must not change the public entry point's behaviour.
    raw = load_raw(vu_path)
    assert raw.path == vu_path
    assert "ch" in raw.ae
