"""Guesses land in classifier.yaml only after an explicit yes.

Every recording test passes directory=tmp_path through offer_terms' own
kwarg -- nothing here may touch the real knowledge/toanaz/classifier.yaml.
"""
from wing_parser.classifier import cache
from wing_parser.showcontext.ingest import build as builder
from wing_parser.showcontext.ingest.guess import (
    offer_terms,
    propose_term,
    unresolved_terms,
)
from wing_parser.showcontext.ingest.mapping import SheetMapping
from wing_parser.showcontext.ingest.sheet import RawRow

TERM_SCHEMA_RESULT = {"kind": "speech.playback", "confidence": 0.7}

MAPPING = SheetMapping(
    source="test",
    fields={"id": "A", "time": "B", "title": "C", "performers": "D", "note": "E"},
)


class TermProvider:
    def complete_json(self, system, user, schema):
        assert "Nhạc đón khách" in user
        return dict(TERM_SCHEMA_RESULT)


class UnknownProvider:
    def complete_json(self, system, user, schema):
        return {"kind": "unknown", "confidence": 0.0}


class DeadProvider:
    def complete_json(self, system, user, schema):
        raise RuntimeError("socket closed")


def _never(term):
    return None


def row(number, **cells):
    return RawRow(
        number=number,
        cells={"A": "", "B": "", "C": "", "D": "", "E": "", **cells},
    )


def test_propose_term_returns_a_g2b_assisted_classification():
    got = propose_term("Nhạc đón khách", ["r2: Nhạc đón khách"], TermProvider())
    assert got.kind == "speech.playback"
    assert got.origin == "g2b-assisted"


def test_an_unknown_verdict_is_not_a_proposal():
    assert propose_term("???", [], UnknownProvider()) is None


def test_a_yes_records_through_the_normal_cache_path(tmp_path):
    answers = iter(["y"])
    count = offer_terms(
        ["Nhạc đón khách"], {}, provider_factory=lambda: TermProvider(),
        input_fn=lambda *a, **k: next(answers), print_fn=lambda *a, **k: None,
        directory=tmp_path,
    )
    assert count == 1
    remembered = cache.load(directory=tmp_path)["cuesheet"]["nhạc đón khách"]
    assert remembered.kind == "speech.playback"
    assert remembered.origin == "g2b-assisted"


def test_a_no_records_nothing(tmp_path):
    answers = iter(["n"])
    count = offer_terms(
        ["Nhạc đón khách"], {}, provider_factory=lambda: TermProvider(),
        input_fn=lambda *a, **k: next(answers), print_fn=lambda *a, **k: None,
        directory=tmp_path,
    )
    assert count == 0
    assert cache.load(directory=tmp_path)["cuesheet"] == {}


def test_a_dead_provider_is_one_line_and_no_question(tmp_path):
    asked = []

    def refusing_input(prompt):
        asked.append(prompt)
        return "n"

    said = []
    count = offer_terms(
        ["Nhạc đón khách"], {}, provider_factory=lambda: DeadProvider(),
        input_fn=refusing_input, print_fn=lambda *a, **k: said.append(a[0]),
        directory=tmp_path,
    )
    assert count == 0
    assert len(said) == 1 and "term guessing unavailable" in said[0]
    assert not asked
    assert cache.load(directory=tmp_path)["cuesheet"] == {}


def test_unresolved_terms_are_deduped_in_first_seen_order():
    """Built the way tests/test_ingest_build.py builds them: two rows carry
    'Nhạc đón khách', one carries 'PGs'; nothing resolves, so each lands
    in a BuiltSegment comment and the parser reads them back out."""
    rows = [
        row(5, C="Một", D="Nhạc đón khách"),
        row(6, C="Hai", D="PGs"),
        row(7, C="Ba", D="Nhạc đón khách"),
    ]
    result = builder.build(rows, MAPPING, _never)
    assert unresolved_terms(result) == ("Nhạc đón khách", "PGs")
