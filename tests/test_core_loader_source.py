"""A scene knows where it came from, whether or not that is a file.

`WingScene` is built from a `RawScene`, never from a path, which is what
lets a console-read scene run the whole query and advisory stack unchanged.
The one thing that assumed a file was the display name, so `source` carries
it and `path` is allowed to be absent.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from wing_parser.core.loader import RawScene, load_raw
from wing_parser.query.scene import WingScene


def test_a_file_scene_derives_its_source_from_the_filename(vu_path):
    raw = load_raw(vu_path)
    assert raw.source == Path(vu_path).name
    assert raw.path is not None


def test_a_console_scene_has_no_path_but_still_has_a_source(vu_path):
    version = load_raw(vu_path).version
    raw = RawScene(version=version, ae={}, ce={}, meta={}, source="wing://192.168.128.28")
    assert raw.path is None
    assert raw.source == "wing://192.168.128.28"


def test_an_explicit_source_is_not_overwritten_by_the_filename(vu_path):
    raw = RawScene(
        version=load_raw(vu_path).version,
        ae={}, ce={}, meta={},
        path=Path("somewhere/else.snap"),
        source="wing://10.0.0.1",
    )
    assert raw.source == "wing://10.0.0.1"


def test_a_scene_with_neither_still_prints_something(vu_path):
    """A caller that forgets both must not produce an AttributeError deep in
    a rendering path; it gets a visible placeholder instead."""
    raw = RawScene(version=load_raw(vu_path).version, ae={}, ce={}, meta={})
    assert raw.source == "<unknown>"


def test_the_scene_surfaces_source_in_errors_and_repr(vu_path):
    raw = load_raw(vu_path)
    scene = WingScene(raw)
    assert scene.source == raw.source
    assert raw.source in repr(scene)
    with pytest.raises(KeyError) as caught:
        scene.channel(999)
    assert raw.source in str(caught.value)
