"""Spec §3.2-3.3: defaults + his edits + tombstones + nested sets.

Every fixture uses an isolated `directory` (tmp_path) so no test reads
or writes the real knowledge/ directory -- see conftest.py's session
autouse fixture, which already isolates config.knowledge_dir() but NOT
an explicit directory= argument, so tests here pass one explicitly.
"""
from __future__ import annotations

import pytest

from wing_parser.classifier import cache, vocabulary as vocab


@pytest.fixture
def directory(tmp_path):
    return tmp_path


# -- defaults load with no user file at all ---------------------------------


def test_the_shipped_defaults_load_with_an_empty_classifier_yaml(directory):
    v = vocab.Vocabulary.load(directory)
    keys = {s.key for s in v.sets()}
    assert "drum kit" in keys and "band" in keys
    terms = {t.key: t for t in v.terms()}
    assert terms["mc"].kinds == ("speech.mc",)
    assert terms["mc"].origin == "default"
    assert terms["mc"].match == "word"


def test_every_shipped_default_kind_is_one_patterns_yaml_can_produce(directory):
    from wing_parser.classifier.matcher import known_kinds

    known = set(known_kinds("channels"))
    v = vocab.Vocabulary.load(directory)
    for term in v.effective():
        for kind in term.kinds:
            assert kind in known, f"{term.key!r} names unknown kind {kind!r}"


# -- nested sets (F13) --------------------------------------------------------


def test_band_expands_to_its_own_kinds_plus_drum_kits_nested_ones(directory):
    v = vocab.Vocabulary.load(directory)
    expanded = v.expand_set("band")
    for kind in ("drums.kick.in", "drums.tom", "speech.vocal", "instrument.guitar"):
        assert kind in expanded


def test_editing_drum_kit_changes_what_band_expands_to(directory):
    v = vocab.Vocabulary.load(directory)
    v.put_set("drum kit", label="Drum kit", kinds=("drums.pad",))
    reloaded = vocab.Vocabulary.load(directory)
    assert reloaded.expand_set("band") == ("drums.pad", "speech.vocal",
                                           "instrument.guitar", "instrument.bass",
                                           "instrument.keys")


def test_a_cycle_is_refused_at_write_naming_the_path(directory):
    v = vocab.Vocabulary.load(directory)
    v.put_set("loop a", label="Loop A", sets=("band",))
    with pytest.raises(vocab.CycleError) as exc:
        v.put_set("band", label="Band", sets=("drum kit", "loop a"))
    assert "band" in str(exc.value) and "loop a" in str(exc.value)
    assert exc.value.path == ("band", "loop a", "band")


def test_a_cycle_already_on_disk_expands_once_and_does_not_loop(directory):
    """Reached only by hand-editing classifier.yaml -- the loader must
    tolerate it, not crash every fragment behind it (design spec S3.2)."""
    doc = cache.read_raw(directory)
    doc.setdefault("cuesheet_sets", {})
    doc["cuesheet_sets"]["loop a"] = {"label": "Loop A", "sets": ["loop b"], "origin": "manual"}
    doc["cuesheet_sets"]["loop b"] = {"label": "Loop B", "sets": ["loop a"], "kinds": ["speech.mc"],
                                      "origin": "manual"}
    cache.write_raw(doc, directory)

    v = vocab.Vocabulary.load(directory)
    assert v.expand_set("loop a") == ("speech.mc",)  # terminates, no RecursionError


def test_a_term_pointing_at_a_deleted_set_resolves_to_its_remaining_kinds(directory):
    v = vocab.Vocabulary.load(directory)
    v.put_term("solo term", kinds=("speech.lectern",), sets=("band",), match="word")
    v.delete_set("band")
    reloaded = vocab.Vocabulary.load(directory)
    effective = {t.key: t for t in reloaded.effective()}
    assert effective["solo term"].kinds == ("speech.lectern",)  # band's kinds are gone, not an error


# -- overrides and tombstones (S3.2) -----------------------------------------


def test_his_entry_replaces_a_default_with_the_same_folded_key(directory):
    v = vocab.Vocabulary.load(directory)
    v.put_term("MC", kinds=("speech.lectern",), match="word")  # overrides the default "mc"
    reloaded = vocab.Vocabulary.load(directory)
    terms = {t.key: t for t in reloaded.terms()}
    assert terms["mc"].kinds == ("speech.lectern",)
    assert terms["mc"].display_origin == "default, edited"


def test_deleting_a_default_term_tombstones_it_rather_than_reviving_on_update(directory):
    v = vocab.Vocabulary.load(directory)
    v.delete_term("hoa tươi")
    reloaded = vocab.Vocabulary.load(directory)
    assert "hoa tươi" not in {t.key for t in reloaded.terms()}
    doc = cache.read_raw(directory)
    assert doc["cuesheet"]["hoa tươi"]["deleted"] is True


def test_reset_removes_the_tombstone_and_the_default_shows_through_again(directory):
    v = vocab.Vocabulary.load(directory)
    v.delete_term("hoa tươi")
    v.reset_term("hoa tươi")
    reloaded = vocab.Vocabulary.load(directory)
    terms = {t.key: t for t in reloaded.terms()}
    assert terms["hoa tươi"].ignore is True
    assert terms["hoa tươi"].origin == "default"


def test_deleting_a_manual_term_that_has_no_default_removes_it_outright(directory):
    v = vocab.Vocabulary.load(directory)
    v.put_term("cajon", kinds=("drums.pad",), match="word")
    v.delete_term("cajon")
    doc = cache.read_raw(directory)
    assert "cajon" not in doc["cuesheet"]


# -- fix round 1 (I1): reaching a tombstoned default for Reset --------------


def test_deleted_terms_lists_a_tombstoned_default_term(directory):
    v = vocab.Vocabulary.load(directory)
    assert "hoa tươi" not in {t.key for t in v.deleted_terms()}
    v.delete_term("hoa tươi")
    deleted = {t.key for t in v.deleted_terms()}
    assert "hoa tươi" in deleted
    assert "hoa tươi" not in {t.key for t in v.terms()}


def test_deleted_sets_lists_a_tombstoned_default_set(directory):
    v = vocab.Vocabulary.load(directory)
    v.delete_set("drum kit")
    assert "drum kit" in {s.key for s in v.deleted_sets()}
    assert "drum kit" not in {s.key for s in v.sets()}


def test_deleting_a_manual_only_term_never_shows_up_as_deleted(directory):
    """A manual-only delete drops the raw entry outright (fix round 1's
    docstring on deleted_terms): there is no default underneath for
    Reset to bring back, so it must not appear as a "greyed, resettable"
    row either."""
    v = vocab.Vocabulary.load(directory)
    v.put_term("cajon", kinds=("drums.pad",), match="word")
    v.delete_term("cajon")
    assert "cajon" not in {t.key for t in v.deleted_terms()}


def test_has_default_term_is_true_for_a_default_and_false_for_manual_only(directory):
    v = vocab.Vocabulary.load(directory)
    v.put_term("cajon", kinds=("drums.pad",), match="word")
    assert v.has_default_term("hoa tươi") is True
    assert v.has_default_term("cajon") is False


def test_has_default_set_is_true_for_a_default_and_false_for_manual_only(directory):
    v = vocab.Vocabulary.load(directory)
    v.put_set("cajon kit", label="Cajon kit", kinds=("drums.pad",))
    assert v.has_default_set("drum kit") is True
    assert v.has_default_set("cajon kit") is False


# -- validation ---------------------------------------------------------------


def test_put_term_refuses_an_unknown_kind_naming_it(directory):
    v = vocab.Vocabulary.load(directory)
    with pytest.raises(vocab.UnknownKindError, match="nonsense.kind"):
        v.put_term("x", kinds=("nonsense.kind",), match="word")


def test_put_term_refuses_an_unknown_set_naming_it(directory):
    v = vocab.Vocabulary.load(directory)
    with pytest.raises(vocab.UnknownSetError, match="no such set"):
        v.put_term("x", sets=("no such set",), match="word")


def test_a_term_cannot_be_both_ignore_and_kinds(directory):
    v = vocab.Vocabulary.load(directory)
    with pytest.raises(ValueError, match="ignore"):
        v.put_term("x", kinds=("speech.mc",), ignore=True, match="word")


# -- the old single-kind shape still loads (S3.2) ----------------------------


def test_an_old_shape_cache_remember_entry_loads_as_a_match_exact_term(directory):
    from wing_parser.classifier.matcher import Classification

    cache.remember("guitar solo", "cuesheet",
                   Classification(kind="instrument.guitar", confidence=1.0, origin="manual"),
                   directory=directory)
    v = vocab.Vocabulary.load(directory)
    terms = {t.key: t for t in v.terms()}
    assert terms["guitar solo"].kinds == ("instrument.guitar",)
    assert terms["guitar solo"].match == "exact"


# -- fix round 1, controller ruling R1: an old entry keeps its meaning -------
# Before Task 3 wired build.py through Vocabulary, resolve_fragment only
# trusted a remembered Classification when matcher.is_confident() (confidence
# >= matcher.HIGH) -- a weak model guess stayed a comment, never `expects:`.
# term_from_user must preserve that for the same pre-wave-4 shape it now
# also has to parse.


def test_an_old_shape_entry_below_matcher_high_does_not_resolve(directory):
    from wing_parser.classifier.matcher import HIGH, Classification
    from wing_parser.showcontext.ingest import build
    from wing_parser.showcontext.ingest.mapping import SheetMapping
    from wing_parser.showcontext.ingest.sheet import RawRow

    assert HIGH - 0.3 < HIGH  # sanity: 0.5 really is below matcher.HIGH (0.8)
    cache.remember("flooble", "cuesheet",
                   Classification(kind="speech.mc", confidence=0.5, origin="manual"),
                   directory=directory)
    v = vocab.Vocabulary.load(directory)

    # The term itself must carry no kind (not be dropped outright): it
    # still identity-matches at match="exact" -- correctly shadowing a
    # same-key default, if one existed -- it just resolves to nothing.
    terms = {t.key: t for t in v.terms()}
    assert terms["flooble"].kinds == ()
    assert terms["flooble"].match == "exact"

    mapping = SheetMapping(source="t", fields={"title": "C", "performers": "D"})
    row = RawRow(number=5, cells={"C": "x", "D": "flooble"})
    result = build.build([row], mapping, v)
    assert result.segments[0].segment.expects == ()
    assert result.unreadable_performers == 1


def test_an_old_shape_entry_at_or_above_matcher_high_resolves(directory):
    from wing_parser.classifier.matcher import HIGH, Classification
    from wing_parser.showcontext.ingest import build
    from wing_parser.showcontext.ingest.mapping import SheetMapping
    from wing_parser.showcontext.ingest.sheet import RawRow

    cache.remember("flooble", "cuesheet",
                   Classification(kind="speech.mc", confidence=1.0, origin="manual"),
                   directory=directory)
    v = vocab.Vocabulary.load(directory)
    terms = {t.key: t for t in v.terms()}
    assert terms["flooble"].kinds == ("speech.mc",)

    mapping = SheetMapping(source="t", fields={"title": "C", "performers": "D"})
    row = RawRow(number=5, cells={"C": "x", "D": "flooble"})
    result = build.build([row], mapping, v)
    assert result.segments[0].segment.expects == ("speech.mc",)
    assert result.unreadable_performers == 0
    assert HIGH == 0.8  # documents the exact threshold this test straddles


# -- effective() feeds keywords.match directly -------------------------------


def test_effective_terms_are_ready_for_keywords_match(directory):
    from wing_parser.showcontext.ingest import keywords

    v = vocab.Vocabulary.load(directory)
    result = keywords.match("Mời MC lên sân khấu", v.effective())
    assert "speech.mc" in result.kinds and "utility.playback" in result.kinds


# -- I3 regression: deleting a set must not turn its terms into "ignored" ---


def test_deleting_the_drum_kit_set_leaves_trong_unreadable_not_ignored(directory):
    """End to end, the real path the coordinator's re-review named:
    'trống'/'drum'/'dàn trống' resolve through `sets: [drum kit]`
    (cuesheet_defaults.yaml); deleting that set expands them to kinds=()
    via `effective()`, but they are STILL genuine word hits, not ignored.
    A performer cell containing 'trống' must stay a 'could not read'
    comment (unreadable_performers +1, a visible warning), never silently
    swallowed as if the operator had asked to ignore it (F5)."""
    from wing_parser.showcontext.ingest import build
    from wing_parser.showcontext.ingest.mapping import SheetMapping
    from wing_parser.showcontext.ingest.sheet import RawRow

    v = vocab.Vocabulary.load(directory)
    v.delete_set("drum kit")
    v = vocab.Vocabulary.load(directory)  # fresh load, same as a real re-open

    terms = {t.key: t for t in v.terms()}
    assert terms["trống"].kinds == ()  # the set it named no longer exists

    # "cây trống to" -- deliberately avoids every OTHER shipped default
    # word (e.g. "tiết mục" is itself ignore: true) so the only thing this
    # fragment can hit is "trống" itself.
    mapping = SheetMapping(source="t", fields={"title": "C", "performers": "D"})
    row = RawRow(number=7, cells={"C": "x", "D": "cây trống to"})
    result = build.build([row], mapping, v)

    assert result.segments[0].segment.expects == ()
    assert result.unreadable_performers == 1
    assert any(
        "could not read performer" in c
        for seg in result.segments for c in seg.comments
    )


# -- fix round 1 (review of 748b51a..912f125): identity bugs -----------------
# CRITICAL 1: put/delete/reset must find an existing raw entry by FOLDED
# identity, not by the exact string passed -- a raw key on disk keeps
# whatever the person typed (W3), so a caller using a different
# spelling/case/diacritics for the SAME logical entry must still find it.


def test_delete_finds_a_user_term_saved_under_different_diacritics_or_case(directory):
    from wing_parser.showcontext.ingest import keywords

    v = vocab.Vocabulary.load(directory)
    v.put_term("Cá Nhân", kinds=("speech.lectern",), match="word")  # no default shadows this
    v.delete_term("ca nhan")  # same folded identity, different spelling
    doc = cache.read_raw(directory)
    assert not any(keywords.fold(k) == "ca nhan" for k in doc["cuesheet"])
    reloaded = vocab.Vocabulary.load(directory)
    assert not any(keywords.fold(t.key) == "ca nhan" for t in reloaded.terms())


def test_reset_finds_an_override_saved_under_a_different_spelling_than_the_default(directory):
    v = vocab.Vocabulary.load(directory)
    v.put_term("MC", kinds=("speech.lectern",), match="word")  # overrides default "mc"
    v.reset_term("Mc")  # different case than what was typed, same folded identity
    reloaded = vocab.Vocabulary.load(directory)
    terms = {t.key: t for t in reloaded.terms()}
    assert terms["mc"].kinds == ("speech.mc",)
    assert terms["mc"].origin == "default"


def test_put_term_again_under_a_different_spelling_replaces_not_duplicates(directory):
    from wing_parser.showcontext.ingest import keywords

    v = vocab.Vocabulary.load(directory)
    v.put_term("Cajon", kinds=("drums.pad",), match="word")
    v.put_term("cajon", kinds=("drums.pad", "drums.tom"), match="word")
    doc = cache.read_raw(directory)
    matching = [k for k in doc["cuesheet"] if keywords.fold(k) == "cajon"]
    assert len(matching) == 1


# IMPORTANT 1: _check_cycle must tolerate a pre-existing disk cycle it is not
# joining, not RecursionError.


def test_put_set_tolerates_a_pre_existing_disk_cycle_it_does_not_join(directory):
    doc = cache.read_raw(directory)
    doc.setdefault("cuesheet_sets", {})
    doc["cuesheet_sets"]["loop a"] = {"label": "Loop A", "sets": ["loop b"], "origin": "manual"}
    doc["cuesheet_sets"]["loop b"] = {"label": "Loop B", "sets": ["loop a"], "kinds": ["speech.mc"],
                                      "origin": "manual"}
    cache.write_raw(doc, directory)

    v = vocab.Vocabulary.load(directory)
    v.put_set("x", label="X", sets=("loop a",))  # must not raise / RecursionError
    reloaded = vocab.Vocabulary.load(directory)
    assert reloaded.expand_set("x") == ("speech.mc",)


# IMPORTANT 2: deciding "had a default" from the currently-merged entry is
# wrong once that entry IS the tombstone -- must decide from the shipped
# defaults' own (static) key set instead.


def test_deleting_an_already_deleted_default_stays_deleted(directory):
    v = vocab.Vocabulary.load(directory)
    v.delete_term("hoa tươi")
    v.delete_term("hoa tươi")  # deleting again must not resurrect it
    reloaded = vocab.Vocabulary.load(directory)
    assert "hoa tươi" not in {t.key for t in reloaded.terms()}
    doc = cache.read_raw(directory)
    assert doc["cuesheet"]["hoa tươi"]["deleted"] is True


# IMPORTANT 3: _check_sets must compare against the folded identity of
# visible sets, not their (possibly unfolded) display key.


def test_check_sets_finds_a_set_by_folded_identity_not_its_display_key(directory):
    v = vocab.Vocabulary.load(directory)
    v.put_set("Loop A", label="Loop A", kinds=("speech.mc",))  # display key keeps the case
    v.put_term("y", sets=("loop a",), match="word")  # different case, same folded identity
    reloaded = vocab.Vocabulary.load(directory)
    effective = {t.key: t for t in reloaded.effective()}
    assert effective["y"].kinds == ("speech.mc",)


# -- spec gaps (spec governs over the brief's own draft) ---------------------


def test_missing_match_on_a_hand_edited_entry_defaults_to_exact(directory):
    doc = cache.read_raw(directory)
    doc["cuesheet"]["newword"] = {"kinds": ["speech.mc"], "origin": "manual"}  # no match:
    cache.write_raw(doc, directory)
    v = vocab.Vocabulary.load(directory)
    terms = {t.key: t for t in v.terms()}
    assert terms["newword"].match == "exact"


def test_put_term_without_a_match_argument_defaults_to_exact(directory):
    v = vocab.Vocabulary.load(directory)
    v.put_term("newterm2", kinds=("speech.mc",))  # match not given
    doc = cache.read_raw(directory)
    assert doc["cuesheet"]["newterm2"]["match"] == "exact"


def test_put_term_refuses_an_entry_with_neither_kinds_sets_nor_ignore(directory):
    v = vocab.Vocabulary.load(directory)
    with pytest.raises(ValueError, match="kinds"):
        v.put_term("empty term")


def test_problems_reports_an_unknown_kind_on_a_hand_edited_term_and_excludes_it(directory):
    doc = cache.read_raw(directory)
    doc["cuesheet"]["broken term"] = {"kinds": ["nonsense.kind"], "match": "word", "origin": "manual"}
    cache.write_raw(doc, directory)
    v = vocab.Vocabulary.load(directory)
    assert any("broken term" in p and "nonsense.kind" in p for p in v.problems)
    assert "broken term" not in {t.key for t in v.effective()}


def test_problems_reports_a_set_cycle_found_on_disk(directory):
    doc = cache.read_raw(directory)
    doc.setdefault("cuesheet_sets", {})
    doc["cuesheet_sets"]["loop a"] = {"label": "Loop A", "sets": ["loop b"], "origin": "manual"}
    doc["cuesheet_sets"]["loop b"] = {"label": "Loop B", "sets": ["loop a"], "kinds": ["speech.mc"],
                                      "origin": "manual"}
    cache.write_raw(doc, directory)
    v = vocab.Vocabulary.load(directory)
    assert any("cycle" in p and "loop a" in p and "loop b" in p for p in v.problems)


def test_a_term_naming_a_now_missing_set_is_also_listed_in_problems(directory):
    v = vocab.Vocabulary.load(directory)
    v.put_term("solo term2", sets=("band",), match="word")
    v.delete_set("band")
    reloaded = vocab.Vocabulary.load(directory)
    assert any("solo term2" in p for p in reloaded.problems)


# -- fix round 2 (re-review): unknown kinds must not reach the matcher,
# and the loader must never raise on a malformed hand-edit -------------------


def test_a_term_naming_a_set_with_one_unknown_and_one_known_kind_resolves_to_the_known_one(directory):
    doc = cache.read_raw(directory)
    doc.setdefault("cuesheet_sets", {})
    doc["cuesheet_sets"]["broken set"] = {
        "label": "Broken Set", "kinds": ["nonsense.kind", "speech.mc"], "origin": "manual",
    }
    doc["cuesheet"]["uses broken set"] = {"sets": ["broken set"], "match": "word", "origin": "manual"}
    cache.write_raw(doc, directory)

    v = vocab.Vocabulary.load(directory)
    assert v.expand_set("broken set") == ("speech.mc",)  # nonsense.kind dropped, not passed through
    effective = {t.key: t for t in v.effective()}
    assert effective["uses broken set"].kinds == ("speech.mc",)
    assert any("broken set" in p and "nonsense.kind" in p for p in v.problems)


def test_a_non_dict_hand_edited_entry_is_skipped_and_reported_not_raised(directory):
    doc = cache.read_raw(directory)
    doc["cuesheet"]["weird"] = "not a mapping"
    cache.write_raw(doc, directory)

    v = vocab.Vocabulary.load(directory)  # must not raise
    assert "weird" not in {t.key for t in v.terms()}
    assert any("weird" in p for p in v.problems)


def test_an_old_shape_entry_missing_kind_is_skipped_and_reported_not_raised(directory):
    doc = cache.read_raw(directory)
    doc["cuesheet"]["half old shape"] = {"confidence": 0.9, "origin": "manual"}
    cache.write_raw(doc, directory)

    v = vocab.Vocabulary.load(directory)  # must not raise KeyError
    assert "half old shape" not in {t.key for t in v.terms()}
    assert any("half old shape" in p for p in v.problems)


def test_a_string_kinds_value_is_skipped_and_reported_not_split_into_characters(directory):
    doc = cache.read_raw(directory)
    doc["cuesheet"]["string kinds"] = {"kinds": "speech.mc", "match": "word", "origin": "manual"}
    cache.write_raw(doc, directory)

    v = vocab.Vocabulary.load(directory)  # must not raise, must not split into 's','p','e',...
    assert "string kinds" not in {t.key for t in v.terms()}
    assert any("string kinds" in p for p in v.problems)


# -- dry_run_set / dry_run_term: every problem put_set/put_term would raise,
# without writing (vocab_changes.validate calls these) ----------------------


def test_dry_run_set_reports_an_unknown_kind_without_writing(directory):
    v = vocab.Vocabulary.load(directory)
    problems = v.dry_run_set("x", kinds=("nonsense.kind",))
    assert problems and "nonsense.kind" in problems[0]
    assert "x" not in {s.key for s in vocab.Vocabulary.load(directory).sets()}


def test_dry_run_set_reports_a_cycle_without_writing(directory):
    v = vocab.Vocabulary.load(directory)
    v.put_set("loop a", label="Loop A", sets=("band",))
    problems = v.dry_run_set("band", kinds=(), sets=("drum kit", "loop a"))
    assert problems and "loop a" in problems[0]


def test_dry_run_set_is_empty_for_a_writable_set(directory):
    v = vocab.Vocabulary.load(directory)
    assert v.dry_run_set("new one", kinds=("speech.mc",)) == ()


def test_dry_run_term_reports_ignore_with_kinds_as_one_problem(directory):
    v = vocab.Vocabulary.load(directory)
    problems = v.dry_run_term("x", kinds=("speech.mc",), ignore=True)
    assert len(problems) == 1 and "ignore" in problems[0]


def test_dry_run_term_reports_an_empty_term_as_one_problem(directory):
    v = vocab.Vocabulary.load(directory)
    problems = v.dry_run_term("x")
    assert len(problems) == 1 and "kinds" in problems[0]


def test_dry_run_term_is_empty_for_a_writable_term(directory):
    v = vocab.Vocabulary.load(directory)
    assert v.dry_run_term("cajon", kinds=("drums.pad",)) == ()
