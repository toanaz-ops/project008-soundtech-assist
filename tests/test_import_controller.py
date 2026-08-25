"""The GUI's import brain -- every decision testable without Qt."""

from pathlib import Path

from wing_parser.showcontext.ingest.sheet import RawRow
from wing_parser.ui import import_controller as ic

BIDV = Path("tests/data/BIDV TPHCM - KỊCH BẢN SK YEP 2025..xlsx")

# Pinned identically in tests/test_g2b_acceptance.py (criterion 1): the
# proposal the checker accepts clean against the real BIDV sheet.
_BIDV_COLUMNS = {"id": "A", "time": "B", "title": "E"}
_BIDV_HEADERS = {"performers": "Thực hiện"}


def test_proposal_none_when_kill_switch_on(monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    assert ic.proposal_for(BIDV, None) is None


def test_read_with_resolves_the_real_bidv_sheet():
    read, resolved = ic.read_with(
        BIDV, "KB 8.1", 5, _BIDV_COLUMNS, _BIDV_HEADERS,
    )
    assert resolved.fields["title"] == "E"
    assert resolved.fields["performers"]
    assert read.rows


def test_unresolved_terms_parse_from_comments(monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    read, resolved = ic.read_with(
        BIDV, "KB 8.1", 5, _BIDV_COLUMNS, _BIDV_HEADERS,
    )
    result = ic.build_result(read, resolved)
    terms = ic.unresolved(result)
    assert all(isinstance(term, str) and term for term in terms)


def test_preview_text_is_a_render_under_the_workbook_stem():
    read, resolved = ic.read_with(
        BIDV, "KB 8.1", 5, _BIDV_COLUMNS, _BIDV_HEADERS,
    )
    result = ic.build_result(read, resolved)
    text = ic.preview_text(BIDV, result)
    assert isinstance(text, str)
    assert "segments:" in text


def test_context_for_collects_up_to_two_rows_per_term():
    rows = (
        RawRow(number=2, cells={"A": "1", "B": "đón khách"}),
        RawRow(number=3, cells={"A": "2", "B": "ca trống"}),
        RawRow(number=4, cells={"A": "3", "B": "mở màn ca trống"}),
        RawRow(number=5, cells={"A": "4", "B": "tốp múa"}),
    )
    context = ic.context_for(("ca trống",), rows)
    hits = context["ca trống"]
    assert len(hits) == 2
    assert hits[0].startswith("row 3:")
    assert hits[1].startswith("row 4:")


def test_guesses_swallow_errors_per_term():
    class DeadProvider:
        def complete_json(self, system, user, schema):
            raise RuntimeError("offline")

    guesses = ic.guesses_for(
        ("ca trống",),
        {"ca trống": ["row 1: ca trống"]},
        lambda: DeadProvider(),
    )
    assert guesses == [("ca trống", None)]


def test_guesses_respect_the_kill_switch(monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")

    def forbidden():
        raise AssertionError("provider must not be constructed")

    assert ic.guesses_for(("ca trống",), {}, forbidden) == []


def test_record_term_writes_through_cache(tmp_path):
    from wing_parser.classifier import cache
    from wing_parser.classifier.matcher import Classification

    entry = Classification(kind="music.traditional", confidence=0.9,
                           origin="g2b-assisted")
    ic.record_term("ca trống", entry, directory=tmp_path)

    stored = cache.load(directory=tmp_path)["cuesheet"]["ca trống"]
    assert stored.kind == "music.traditional"
