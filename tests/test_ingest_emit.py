import yaml

from wing_parser.showcontext.ingest import emit
from wing_parser.showcontext.ingest.build import BuildResult, BuiltSegment
from wing_parser.showcontext.models import Segment


def _result(**overrides):
    base = dict(
        segments=(
            BuiltSegment(
                segment=Segment(id="S1", title="Đón khách",
                                expects=("instrument.keys",)),
                comments=("row 5: time '19:00'",),
            ),
        ),
        loose_comments=("row 9: no title, kept as a comment -- note='x'",),
        data_rows=2,
        comment_rows=1,
        blank_rows=1,
    )
    base.update(overrides)
    return BuildResult(**base)


def test_the_output_is_valid_yaml_and_round_trips():
    text = emit.render("Test show", _result())
    doc = yaml.safe_load(text)
    assert doc["show"] == "Test show"
    assert doc["segments"][0]["id"] == "S1"
    assert doc["segments"][0]["expects"] == ["instrument.keys"]


def test_every_segment_carries_an_empty_cues_list():
    """It is true, the loader reads it, and it anchors the --scene comment."""
    doc = yaml.safe_load(emit.render("t", _result()))
    assert doc["segments"][0]["cues"] == []


def test_a_row_comment_survives_into_the_text():
    text = emit.render("t", _result())
    assert "row 5: time '19:00'" in text


def test_a_loose_comment_survives_into_the_text():
    """The whole point: an unreadable row must not vanish."""
    text = emit.render("t", _result())
    assert "row 9: no title" in text


def test_the_reconciliation_line_states_the_counts():
    text = emit.render("t", _result())
    assert "2 data row" in text
    assert "1 segment" in text
    assert "1 row" in text and "comment" in text


def test_a_title_with_yaml_punctuation_survives():
    """A colon, a hash and a quote in one Vietnamese title."""
    nasty = 'Tiết mục: "Nắng" #1'
    result = _result(segments=(
        BuiltSegment(segment=Segment(id="S1", title=nasty), comments=()),
    ))
    doc = yaml.safe_load(emit.render("t", result))
    assert doc["segments"][0]["title"] == nasty


def test_a_scene_proposal_appears_above_the_cues_key():
    result = _result()
    text = emit.render("t", result, proposals={"S1": ("ch 13 \"GTR\" is keys",)})
    lines = [line.strip() for line in text.splitlines()]
    proposal_at = next(i for i, line in enumerate(lines) if "ch 13" in line)
    cues_at = next(i for i, line in enumerate(lines) if line.startswith("cues:"))
    assert proposal_at < cues_at


def test_a_multiline_loose_comment_cannot_break_out_of_the_comment_block():
    """The trailer hand-assembles '#' prefixes (unlike the row-comment path,
    which goes through ruamel and re-prefixes every physical line). A loose
    comment carrying a real newline must not let its second line escape the
    comment block and become live YAML content -- emit.py must not rely on
    its caller having already escaped that newline away."""
    injected = "row 9: no title, note='x\ny_injected: PWNED'"
    result = _result(loose_comments=(injected,))
    text = emit.render("t", result)

    marker = "# rows kept as comments, not imported:"
    assert marker in text
    trailer = text[text.index(marker):]
    for line in trailer.splitlines():
        stripped = line.strip()
        if stripped:
            assert stripped.startswith("#"), (
                f"trailer line escaped the comment block: {line!r}"
            )

    doc = yaml.safe_load(text)
    assert set(doc.keys()) == {"show", "segments"}


def test_a_sheet_that_repeats_an_id_still_writes_a_loadable_file(tmp_path):
    """build + emit + loader in one test, because no single one saw this.

    loader.py:104 refuses a case-insensitive duplicate segment id, so a
    two-row sheet repeating S1 used to import with exit 0 and then fail
    every later `doctor --show` run against the file it wrote.
    """
    from wing_parser.showcontext import load_show_context
    from wing_parser.showcontext.ingest import build as builder
    from wing_parser.showcontext.ingest.mapping import SheetMapping
    from wing_parser.showcontext.ingest.sheet import RawRow

    mapping = SheetMapping(source="t", fields={"id": "A", "title": "C"})
    rows = [RawRow(number=number, cells={"A": "S1", "C": title})
            for number, title in ((5, "Một"), (6, "Hai"))]
    result = builder.build(rows, mapping, lambda term: None)

    path = tmp_path / "out.yaml"
    path.write_text(emit.render("t", result), encoding="utf-8")
    context = load_show_context(path)
    assert [segment.id for segment in context.segments] == ["S1", "S1-2"]
    assert "S1-2" in path.read_text(encoding="utf-8")


def test_technical_fields_written_only_when_present():
    """One segment carries sound, one carries none; exactly one `sound:` line
    appears, and the empty segment keeps its pre-change shape."""
    result = _result(segments=(
        BuiltSegment(
            segment=Segment(id="S1", title="Band",
                            expects=("instrument.keys",),
                            sound="DCA 3 trống"),
            comments=(),
        ),
        BuiltSegment(segment=Segment(id="S2", title="MC welcome",
                                     expects=("speech.mc",)),
                     comments=()),
    ), loose_comments=(), data_rows=2, comment_rows=0, blank_rows=0)
    text = emit.render("t", result)
    assert text.count("sound:") == 1
    assert "lighting:" not in text
    assert "led:" not in text


def test_a_segment_with_no_technical_fields_is_byte_identical_to_before():
    """The pinned contract: an all-empty segment renders exactly as the
    pre-G2b renderer did -- captured from the old code path before this
    change landed."""
    result = _result(segments=(
        BuiltSegment(segment=Segment(id="S1", title="Band",
                                     expects=("instrument.keys",)),
                     comments=()),
    ), loose_comments=(), data_rows=1, comment_rows=0, blank_rows=0)
    expected = (
        "# Generated by `wing showcontext import`. Read it before you use it.\n"
        "\n"
        "# Times and notes from the sheet are comments, not fields: nothing in this\n"
        "# tool reads a segment time, and a sheet's wall-clock time is not the\n"
        "# show-relative form `time:` accepts.\n"
        "\n"
        "# Only Q4 and Q5 fire on a file with no cues. Stripping the `#` from a\n"
        "# proposed cue does not make one: `cues: []` is still sitting below it and\n"
        "# the loader reads that. Each proposal says which lines to delete and what\n"
        "# the rest replaces -- follow it literally, and Q1, Q2 and Q6 come to life\n"
        "# for that segment, and Q3 once a DCA is named. Q7 ships disabled\n"
        "# (base_rules/showcontext.yaml) and stays off regardless of cues.\n"
        "show: t\n"
        "segments:\n"
        "  - id: S1\n"
        "    title: Band\n"
        "    expects: [instrument.keys]\n"
        "    cues: []\n"
        "\n"
        "# imported 1 data row(s) -> 1 segment(s) carrying 1 expectation(s), "
        "0 row(s) and 0 performer fragment(s) kept as comments, "
        "0 blank row(s) skipped\n"
    )
    assert emit.render("t", result) == expected


def test_technical_fields_round_trip_through_the_loader(tmp_path):
    """What emit writes for sound/lighting/led, load_show_context reads back."""
    from wing_parser.showcontext import load_show_context

    result = _result(segments=(
        BuiltSegment(
            segment=Segment(id="S1", title="Band", expects=("instrument.keys",),
                            sound="DCA 3 trống", lighting="full wash", led="warm"),
            comments=(),
        ),
    ), loose_comments=(), data_rows=1, comment_rows=0, blank_rows=0)

    path = tmp_path / "out.yaml"
    path.write_text(emit.render("t", result), encoding="utf-8")
    context = load_show_context(path)
    assert len(context.segments) == 1
    segment = context.segments[0]
    assert segment.sound == "DCA 3 trống"
    assert segment.lighting == "full wash"
    assert segment.led == "warm"


def test_the_document_loads_through_the_show_context_loader(tmp_path):
    """The real contract: what this writes, load_show_context must read."""
    from wing_parser.showcontext import load_show_context

    path = tmp_path / "out.yaml"
    path.write_text(emit.render("Test show", _result()), encoding="utf-8")
    context = load_show_context(path)
    assert context.show == "Test show"
    assert len(context.segments) == 1
    assert context.segments[0].expects == ("instrument.keys",)
    assert context.anomalies == ()
