"""Spec §3.4-3.5: diacritic-folded whole-word matching, no I/O.

fold() is the ONE place this wave strips a Vietnamese tone mark -- every
other module that needs a folded key calls this, never reimplements it
(Global Constraints). match() is steps 1-2 of the lookup order (S3.3):
whole-fragment equality for match="exact" terms, then whole-word
substring scanning for match="word" terms, with longest-wins containment
and ignore-only-when-nothing-else-matched (S3.5).
"""
from __future__ import annotations

from wing_parser.showcontext.ingest.keywords import Resolution, Term, fold, match

# -- fold -----------------------------------------------------------------


def test_fold_casefolds_and_collapses_whitespace():
    assert fold("  Ca Sĩ   Nữ  ") == "ca si nu"


def test_fold_strips_tone_marks_but_keeps_the_base_letter():
    assert fold("phát biểu") == "phat bieu"


def test_fold_turns_d_stroke_into_a_plain_d_after_casefold():
    assert fold("BLĐ") == fold("Bld") == fold("bld") == "bld"


def test_fold_turns_punctuation_into_a_single_space():
    assert fold("check-in, mời!") == "check in moi"


def test_fold_of_empty_or_none_is_empty():
    assert fold("") == ""
    assert fold(None) == ""


# -- match: exact ----------------------------------------------------------


def test_an_exact_term_must_equal_the_whole_fragment():
    terms = (Term(key="MC", kinds=("speech.mc",), ignored=False, match="exact"),)
    assert match("MC", terms) == Resolution(("speech.mc",), False)
    assert match("Mời MC", terms) == Resolution((), False)


# -- match: word, single hit -------------------------------------------------


def test_a_word_term_matches_as_a_whole_word_inside_a_longer_fragment():
    terms = (Term(key="trống", kinds=("drums.kick",), ignored=False, match="word"),)
    assert match("Mời trống lên sân khấu", terms) == Resolution(("drums.kick",), False)


def test_a_word_term_does_not_match_inside_a_longer_word():
    terms = (Term(key="band", kinds=("instrument.guitar",), ignored=False, match="word"),)
    assert match("bandana", terms) == Resolution((), False)


def test_a_multi_word_phrase_key_matches_as_one_bounded_phrase():
    terms = (Term(key="lên sân khấu", kinds=("utility.playback",), ignored=False,
                  match="word"),)
    assert match("Mời BLĐ lên sân khấu quay số", terms) == Resolution(
        ("utility.playback",), False)


# -- match: word, several hits in one cell (S3.5) ---------------------------


def test_several_word_terms_in_one_fragment_union_their_kinds_first_seen():
    terms = (
        Term(key="BLĐ", kinds=("speech.handheld",), ignored=False, match="word"),
        Term(key="lên sân khấu", kinds=("utility.playback",), ignored=False, match="word"),
        Term(key="quay số", kinds=("speech.mc", "utility.playback"), ignored=False,
             match="word"),
    )
    result = match("Mời BLĐ lên sân khấu quay số", terms)
    assert result.kinds == ("speech.handheld", "utility.playback", "speech.mc")
    assert result.ignored is False


def test_a_shorter_hit_wholly_inside_a_longer_hit_is_dropped():
    """'trống' loses to 'dàn trống' when both match the same fragment."""
    terms = (
        Term(key="trống", kinds=("drums.kick",), ignored=False, match="word"),
        Term(key="dàn trống", kinds=("drums.overhead",), ignored=False, match="word"),
    )
    assert match("dàn trống điện tử", terms) == Resolution(("drums.overhead",), False)


# -- ignore (F5, S3.5) -------------------------------------------------------


def test_ignore_wins_only_when_nothing_else_matched():
    terms = (Term(key="hoa tươi", kinds=(), ignored=True, match="word"),)
    assert match("tặng hoa tươi", terms) == Resolution((), True)


def test_a_non_ignore_hit_beats_an_ignore_hit_in_the_same_fragment():
    terms = (
        Term(key="hoa tươi", kinds=(), ignored=True, match="word"),
        Term(key="trao giải", kinds=("speech.mc",), ignored=False, match="word"),
    )
    result = match("trao giải và tặng hoa tươi", terms)
    assert result.kinds == ("speech.mc",) and result.ignored is False


def test_no_term_matches_at_all_is_an_empty_non_ignored_resolution():
    assert match("tốp múa", ()) == Resolution((), False)


def test_an_empty_fragment_matches_nothing():
    assert match("   ", (Term(key="x", kinds=("a",), ignored=False, match="word"),)
                 ) == Resolution((), False)


# -- fix round, I3: an exact hit with no kinds must not cut matching short --


def test_a_weak_exact_entry_over_the_whole_fragment_does_not_block_word_terms():
    """A pre-wave-4 cache entry below matcher.HIGH becomes an exact term
    with kinds=() (vocabulary_store.py term_from_user). Keyed to the WHOLE
    fragment, it used to return Resolution((), False) immediately, hiding
    default word terms that also match inside that same fragment."""
    terms = (
        Term(key="Mời BLĐ lên sân khấu quay số", kinds=(), ignored=False, match="exact"),
        Term(key="blđ", kinds=("speech.handheld",), ignored=False, match="word"),
        Term(key="quay số", kinds=("speech.mc", "utility.playback"), ignored=False,
             match="word"),
    )
    result = match("Mời BLĐ lên sân khấu quay số", terms)
    assert "speech.handheld" in result.kinds
    assert "speech.mc" in result.kinds


def test_a_weak_exact_entry_sharing_a_defaults_own_key_still_lets_it_resolve():
    """A weak entry whose folded key equals another term's key must not
    replace it with nothing -- fall through to the word stage."""
    terms = (
        Term(key="quay số", kinds=(), ignored=False, match="exact"),
        Term(key="quay số", kinds=("speech.mc",), ignored=False, match="word"),
    )
    result = match("Mời BLĐ lên sân khấu quay số", terms)
    assert result.kinds == ("speech.mc",)


def test_an_exact_term_with_no_kinds_and_not_ignored_resolves_to_nothing():
    """An exact term whose sets were all deleted expands to no kinds
    (vocabulary.py's effective()) -- it must fall through rather than
    stop the fragment from ever reaching the word stage."""
    terms = (Term(key="ca trống", kinds=(), ignored=False, match="exact"),)
    assert match("ca trống", terms) == Resolution((), False)


def test_an_exact_ignore_entry_still_returns_immediately():
    """Ignored is still a real hit -- the fix must not touch this branch."""
    terms = (Term(key="ca trống", kinds=(), ignored=True, match="exact"),)
    assert match("ca trống", terms) == Resolution((), True)


def test_a_word_hit_with_no_kinds_does_not_block_an_ignore_hit():
    """Same rule as the exact stage, but in the word stage: a non-ignore
    hit contributing no kinds must count as no hit at all, or it wrongly
    blocks 'ignore wins only when nothing else matched' (S3.5)."""
    terms = (
        Term(key="trống", kinds=(), ignored=False, match="word"),
        Term(key="hoa tươi", kinds=(), ignored=True, match="word"),
    )
    assert match("tặng hoa tươi và trống", terms) == Resolution((), True)
