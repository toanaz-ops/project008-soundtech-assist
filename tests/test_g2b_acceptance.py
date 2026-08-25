# tests/test_g2b_acceptance.py
"""Spec §11 success criteria, minus criterion 3's live-key path (offline).

These pin the deterministic halves of J1 against the REAL sheets ToanAZ
dropped on 2026-08-24. Model-dependent behaviour is exercised through
scripted providers; the network is never touched (global constraint).
"""
from pathlib import Path

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
