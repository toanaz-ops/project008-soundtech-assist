# tests/test_g2b_acceptance.py
"""Spec §11 success criteria, minus criterion 3's live-key path (offline).

These pin the deterministic halves of J1 against the REAL sheets ToanAZ
dropped on 2026-08-24. Model-dependent behaviour is exercised through
scripted providers; the network is never touched (global constraint).
"""
import re
from pathlib import Path

from wing_parser.classifier import vocabulary as vocab_module
from wing_parser.showcontext.ingest import build, sheet
from wing_parser.showcontext.ingest import mapping as mapping_mod
from wing_parser.showcontext.ingest.guess import unresolved_terms
from wing_parser.showcontext.ingest.mapping import FIELDS
from wing_parser.showcontext.ingest.suggest import check_proposal
from wing_parser.showcontext.models import Segment

VIVO = Path("tests/data/05102022_vivo_ Event Rundown.xlsx")
BIDV = Path("tests/data/BIDV TPHCM - KỊCH BẢN SK YEP 2025..xlsx")


def test_spec_criterion_1_bidv_header_row_five_accepted():
    proposal = {"sheet": "KB 8.1", "header_row": 5,
                "columns": {"id": "A", "time": "B", "title": "E"},
                "headers": {"performers": "Thực hiện"}}
    assert check_proposal(proposal, BIDV) == ()


def test_spec_criterion_2_vivo_survives_blank_column_a():
    proposal = {"sheet": "Rundown", "header_row": 4,
                "columns": {"id": "B", "time": "C", "title": "F"},
                "headers": {"performers": "On stage"}}
    assert check_proposal(proposal, VIVO) == ()


def test_segment_carries_structured_fields():
    seg = Segment(id="1", title="t", sound="nhạc", lighting="đèn", led="video")
    assert (seg.sound, seg.lighting, seg.led) == ("nhạc", "đèn", "video")


def test_fields_extended_per_spec_section_7():
    assert set(FIELDS) >= {"sound", "lighting", "led"}


# Mirrors build.py's own `_SPLIT`: not imported from there (a private
# name) so this file's fragment count cannot silently start reading a
# different split than the one build.build itself used to produce
# unreadable_performers/ignored_performers -- both sides of the "N of
# fragment_total resolved" arithmetic below must agree independently.
_SPLIT = re.compile(r"[,/;\n]+")


def _built(path, sheet_name, header_row, columns, performers_header, tmp_path):
    """The real pipeline: read the sheet, resolve columns, build segments
    against the shipped defaults (an empty tmp_path knowledge dir, so
    nothing but the defaults is in play). Returns (result, fragment_total)
    so a test can say "N of fragment_total resolved" explicitly (fix
    round 1, IMPORTANT 2) instead of only the negative space (0 unread,
    0 ignored)."""
    read = sheet.read_sheet(path, sheet_name, header_row)
    raw = mapping_mod.RawMapping(
        source=path.stem, sheet=sheet_name, header_row=header_row,
        columns=columns, headers={"performers": performers_header},
    )
    resolved = mapping_mod.resolve_columns(raw, read.headers, read.last_column)
    vocabulary = vocab_module.Vocabulary.load(tmp_path)
    result = build.build(read.rows, resolved, vocabulary, blank_rows=read.blank_rows,
                         headers=read.headers)

    letter = resolved.fields.get("performers")
    fragment_total = 0
    if letter is not None:
        for row in read.rows:
            for fragment in _SPLIT.split(row.cells.get(letter, "")):
                if fragment.strip():
                    fragment_total += 1
    return result, fragment_total


def test_vivo_resolves_every_performer_fragment_with_the_shipped_defaults(tmp_path):
    """Spec §9: with the shipped defaults, every VIVO fragment resolves.
    Measured 2026-09-26 against keywords.fold/match + Task 2's defaults:
    9 fragments total, 9 resolved, 0 ignored, 0 left unread -- 9 of 9."""
    result, total = _built(VIVO, "Rundown", 4,
                    {"id": "B", "time": "C", "title": "F"}, "On stage", tmp_path)
    assert total == 9
    resolved = total - result.unreadable_performers - result.ignored_performers
    assert resolved == 9  # 9 of 9
    assert result.unreadable_performers == 0
    assert result.ignored_performers == 0


def test_bidv_resolves_or_ignores_all_but_four_deliberately_unread_fragments(tmp_path):
    """Measured 2026-09-26: 31 fragments total, 19 resolved, 8 ignored, 4
    left unread. The four are 'Đội' and 'nhóm' (bare group nouns), 'mời
    lên SK' (a stage-direction verb phrase) and the BIDV Youth Union's
    full organisation name -- none of them name an instrument or a mic
    role, so there is genuinely nothing to classify. If this count
    changes, a real default changed underneath it; re-measure, do not
    adjust the number to make the test pass."""
    result, total = _built(BIDV, "KB 8.1", 5,
                    {"id": "A", "time": "B", "title": "E"}, "Thực hiện", tmp_path)
    assert total == 31
    resolved = total - result.unreadable_performers - result.ignored_performers
    assert resolved == 19  # 19 of 31
    assert result.ignored_performers == 8
    assert result.unreadable_performers == 4
    assert sorted(unresolved_terms(result)) == sorted([
        "Đội", "nhóm", "mời lên SK",
        "Đoàn thanh niên BIDV TP. Hồ Chí Minh",
    ])
