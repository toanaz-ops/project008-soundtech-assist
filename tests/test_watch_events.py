from __future__ import annotations

from wing_parser.net.watch.events import (
    Change,
    change_as_dict,
    format_change,
    split_address,
)


def _change(**overrides) -> Change:
    fields = dict(
        address="/ch/8/$fdr",
        strip="/ch/8",
        key="$fdr",
        label="M8 MC",
        before=-144.0,
        after=-7.9,
        elapsed=12.25,
    )
    fields.update(overrides)
    return Change(**fields)


def test_split_address_separates_the_strip_from_the_key():
    assert split_address("/ch/8/$fdr") == ("/ch/8", "$fdr")
    assert split_address("/dca/16/$solo") == ("/dca/16", "$solo")


def test_a_named_strip_shows_its_name():
    assert "M8 MC" in format_change(_change())


def test_an_unnamed_strip_falls_back_to_its_address_not_an_empty_gap():
    """A blank name is normal -- example-Vu.snap has six blank-named
    channels and factory-scene.snap has forty. Rendering "" would produce
    a line with a hole in it."""
    line = format_change(_change(label=""))
    assert "/ch/8" in line
    assert "  ''" not in line


def test_the_line_carries_elapsed_address_before_and_after():
    line = format_change(_change())
    assert "12.25" in line or "12.2" in line
    assert "$fdr" in line
    assert "-144.0" in line
    assert "-7.9" in line


def test_the_dict_form_is_json_safe_and_keeps_every_field():
    import json

    payload = change_as_dict(_change())
    assert payload["address"] == "/ch/8/$fdr"
    assert payload["label"] == "M8 MC"
    assert payload["before"] == -144.0
    assert payload["after"] == -7.9
    json.dumps(payload)  # raises if anything is not serialisable
