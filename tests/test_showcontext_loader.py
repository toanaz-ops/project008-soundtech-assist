import pytest
import yaml

from wing_parser.showcontext import load_show_context

GOOD = {
    "show": "Tiec cuoi nam",
    "date": "2026-09-14",
    "segments": [
        {
            "id": "S1",
            "title": "MC welcome",
            "expects": ["speech.mc"],
            "cues": [{"id": "SQ 1", "action": "open", "channels": [8]}],
        },
        {
            "id": "S2",
            "title": "Band set",
            "expects": ["instrument.kyes"],
            "cues": [
                {"id": "SQ 2", "action": "Open", "channels": [29], "dcas": [2],
                 "time": "T+00:18:04"},
                {"id": "SQ 3", "action": "close", "channels": [29]},
            ],
        },
    ],
}


def _write(tmp_path, doc, name="show.yaml"):
    path = tmp_path / name
    path.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")
    return path


def test_a_good_file_loads_into_records(tmp_path):
    context = load_show_context(_write(tmp_path, GOOD))
    assert context.show == "Tiec cuoi nam"
    assert [s.id for s in context.segments] == ["S1", "S2"]
    assert context.segments[1].cues[0].channels == (29,)
    assert context.segments[1].cues[0].dcas == (2,)
    assert context.segments[1].cues[0].action == "open"      # 'Open' normalised
    assert context.segments[0].cues[0].time is None


def test_a_repaired_kind_is_applied_and_reported(tmp_path):
    context = load_show_context(_write(tmp_path, GOOD))
    assert context.segments[1].expects == ("instrument.keys",)
    assert any("instrument.kyes" in note and "instrument.keys" in note
               for note in context.anomalies)


def test_an_unresolvable_kind_raises_naming_the_file(tmp_path):
    doc = {"show": "x", "segments": [{"id": "S1", "expects": ["trombone"]}]}
    path = _write(tmp_path, doc)
    with pytest.raises(ValueError) as caught:
        load_show_context(path)
    assert path.name in str(caught.value)
    assert "S1" in str(caught.value)


def test_an_unresolvable_action_raises_naming_the_file_and_cue(tmp_path):
    doc = {"show": "x", "segments": [{"id": "S1", "cues": [
        {"id": "SQ 1", "action": "frobnicate"}]}]}
    path = _write(tmp_path, doc)
    with pytest.raises(ValueError) as caught:
        load_show_context(path)
    assert path.name in str(caught.value)
    assert "S1" in str(caught.value)
    assert "SQ 1" in str(caught.value)


def test_a_duplicate_segment_id_raises(tmp_path):
    doc = {"show": "x", "segments": [{"id": "S1"}, {"id": "s1"}]}
    with pytest.raises(ValueError, match="duplicate segment id"):
        load_show_context(_write(tmp_path, doc))


def test_duplicate_cue_ids_within_a_segment_raise_even_across_whitespace(tmp_path):
    doc = {"show": "x", "segments": [{"id": "S1", "cues": [
        {"id": "SQ 1", "action": "open"}, {"id": "SQ1", "action": "close"}]}]}
    with pytest.raises(ValueError, match="duplicate cue id"):
        load_show_context(_write(tmp_path, doc))


def test_a_malformed_time_is_an_anomaly_not_an_exception(tmp_path):
    doc = {"show": "x", "segments": [{"id": "S1", "cues": [
        {"id": "SQ 1", "action": "open", "time": "quarter past"}]}]}
    context = load_show_context(_write(tmp_path, doc))
    assert context.segments[0].cues[0].time is None
    assert any("quarter past" in note for note in context.anomalies)


def test_a_missing_file_raises_naming_the_path(tmp_path):
    with pytest.raises(ValueError, match="nope.yaml"):
        load_show_context(tmp_path / "nope.yaml")


def test_a_scalar_segments_field_raises_naming_the_file_and_field(tmp_path):
    # `segments: 5` is truthy, so `doc.get("segments") or []` lets it
    # through to a bare `for` loop, which used to raise `TypeError: 'int'
    # object is not iterable` -- a traceback with no file name in it.
    doc = {"show": "x", "segments": 5}
    path = _write(tmp_path, doc)
    with pytest.raises(ValueError) as caught:
        load_show_context(path)
    assert path.name in str(caught.value)
    assert "segments" in str(caught.value)


def test_a_scalar_cues_field_raises_naming_the_file_and_field(tmp_path):
    doc = {"show": "x", "segments": [{"id": "S1", "cues": 3}]}
    path = _write(tmp_path, doc)
    with pytest.raises(ValueError) as caught:
        load_show_context(path)
    assert path.name in str(caught.value)
    assert "cues" in str(caught.value)


def test_expects_without_brackets_raises_naming_the_file_and_field(tmp_path):
    # The single most likely YAML slip in this format: leaving off the
    # `[ ]` around a one-item `expects` list. A bare string is truthy and
    # iterable, so the old `entry.get("expects") or []` guard would iterate
    # its characters one at a time instead of raising here.
    doc = {"show": "x", "segments": [{"id": "S1", "expects": "instrument.keys"}]}
    path = _write(tmp_path, doc)
    with pytest.raises(ValueError) as caught:
        load_show_context(path)
    assert path.name in str(caught.value)
    assert "expects" in str(caught.value)
