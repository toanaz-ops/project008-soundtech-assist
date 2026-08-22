import pytest

from wing_parser.classifier.matcher import Classification
from wing_parser.showcontext.ingest import build as builder
from wing_parser.showcontext.ingest.mapping import SheetMapping
from wing_parser.showcontext.ingest.sheet import RawRow

MAPPING = SheetMapping(
    source="test",
    fields={"id": "A", "time": "B", "title": "C", "performers": "D", "note": "E"},
)

VOCABULARY = {"ca sĩ nữ": "speech.vocal", "trống": "drums.kick"}


def lookup(term):
    kind = VOCABULARY.get(term)
    if kind is None:
        return None
    return Classification(kind=kind, confidence=0.95, origin="manual")


def row(number, **cells):
    return RawRow(number=number, cells={"A": "", "B": "", "C": "", "D": "", "E": "",
                                        **cells})


def test_a_row_becomes_one_segment():
    result = builder.build([row(5, A="1", C="Đón khách")], MAPPING, lookup)
    assert len(result.segments) == 1
    assert result.segments[0].segment.id == "1"
    assert result.segments[0].segment.title == "Đón khách"


def test_an_absent_id_is_generated_in_file_order():
    rows = [row(5, C="Một"), row(6, C="Hai")]
    mapping = SheetMapping(source="t", fields={"title": "C"})
    result = builder.build(rows, mapping, lookup)
    assert [b.segment.id for b in result.segments] == ["S1", "S2"]


def test_the_vocabulary_is_consulted_before_the_pattern_matcher():
    result = builder.build([row(5, C="x", D="ca sĩ nữ")], MAPPING, lookup)
    assert result.segments[0].segment.expects == ("speech.vocal",)


def test_a_loanword_falls_through_to_the_pattern_matcher():
    """guitar is in patterns.yaml, not in the cuesheet vocabulary."""
    result = builder.build([row(5, C="x", D="guitar")], MAPPING, lookup)
    assert result.segments[0].segment.expects == ("instrument.guitar",)


def test_performers_split_on_commas_slashes_semicolons_and_newlines():
    result = builder.build(
        [row(5, C="x", D="guitar, ca sĩ nữ; trống\nbass")], MAPPING, lookup
    )
    assert set(result.segments[0].segment.expects) == {
        "instrument.guitar", "speech.vocal", "drums.kick", "instrument.bass",
    }


def test_expects_is_deduplicated_and_keeps_first_seen_order():
    result = builder.build([row(5, C="x", D="guitar, gtr, bass")], MAPPING, lookup)
    assert result.segments[0].segment.expects == ("instrument.guitar",
                                                  "instrument.bass")


def test_an_unresolvable_fragment_becomes_a_verbatim_comment():
    result = builder.build([row(5, C="x", D="tốp múa")], MAPPING, lookup)
    assert result.segments[0].segment.expects == ()
    assert any("tốp múa" in note for note in result.segments[0].comments)


def test_a_weak_pattern_hit_does_not_satisfy_an_expectation():
    """A weak guess in expects would make Q4 stop catching what it exists for.

    'spd' is confidence 0.75 in patterns.yaml, below the confident band.
    """
    result = builder.build([row(5, C="x", D="spd")], MAPPING, lookup)
    assert result.segments[0].segment.expects == ()
    assert any("spd" in note for note in result.segments[0].comments)


def test_note_and_time_become_comments_not_fields():
    result = builder.build(
        [row(5, C="x", B="19:45", E="Chuẩn bị backline")], MAPPING, lookup
    )
    built = result.segments[0]
    assert built.segment.time is None
    assert any("19:45" in note for note in built.comments)
    assert any("Chuẩn bị backline" in note for note in built.comments)


def test_a_row_without_a_title_becomes_a_loose_comment_not_a_segment():
    result = builder.build([row(5, C="", D="trống", E="thiếu tên")], MAPPING, lookup)
    assert result.segments == ()
    assert result.comment_rows == 1
    assert any("trống" in note for note in result.loose_comments)
    assert any("5" in note for note in result.loose_comments)


def test_an_untitled_rows_id_cell_is_not_dropped():
    result = builder.build([row(7, A="7", C="", D="trống")], MAPPING, lookup)
    assert any("7" in note and "id" in note for note in result.loose_comments)


def test_the_counts_reconcile():
    rows = [row(5, C="Một"), row(6, C=""), row(7, C="Ba")]
    result = builder.build(rows, MAPPING, lookup, blank_rows=2)
    assert result.data_rows == 3
    assert len(result.segments) + result.comment_rows == result.data_rows
    assert result.blank_rows == 2


def test_every_comment_names_its_source_row():
    result = builder.build([row(9, C="x", D="tốp múa")], MAPPING, lookup)
    assert all("row 9" in note for note in result.segments[0].comments)
