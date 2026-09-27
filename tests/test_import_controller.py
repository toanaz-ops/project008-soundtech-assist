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


def test_build_result_reads_the_vocabulary_from_the_given_directory(tmp_path):
    """Fix round 1, controller ruling R1: a caller that already knows
    which knowledge dir it is teaching into (the Terms step) can rebuild
    against that SAME vocabulary, not whatever config.knowledge_dir()
    resolves to process-wide."""
    from wing_parser.classifier import vocabulary as vocab_module

    vocab_module.Vocabulary.load(tmp_path).put_term(
        "ca trống", kinds=("speech.mc",), match="exact")
    read, resolved = ic.read_with(BIDV, "KB 8.1", 5, _BIDV_COLUMNS, _BIDV_HEADERS)
    result = ic.build_result(read, resolved, tmp_path)
    assert "ca trống" not in ic.unresolved(result)
