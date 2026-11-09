"""Search with Vietnamese folding, filters, ranking and facets."""

from tests.library_support import SOURCE, entry, make_root
from wing_parser.library import LibraryStore, facets, search


def build(tmp_path):
    store = LibraryStore(make_root(tmp_path / "lib"))
    store.save(entry("hpf-basics"), author="t")
    store.save(entry("vocal-comp", title="Vocal compression", title_vi="Nén giọng hát",
                     topic="vocals", summary="Taming a lead vocal.",
                     body="Use a slow attack on the vocal.\n",
                     tags={"instrument": ["vocal"], "genre": ["pop"], "technique": ["compression"],
                           "event": []},
                     sources=[dict(SOURCE, publisher="Some Blog")]), author="t")
    return store.entries()


def ids(rows):
    return [r.id for r in rows]


def test_empty_query_returns_everything_in_title_order(tmp_path):
    rows = search(build(tmp_path))
    assert ids(rows) == ["hpf-basics", "vocal-comp"]


def test_vietnamese_folding_matches_without_tone_marks(tmp_path):
    entries = build(tmp_path)
    assert ids(search(entries, "nen giong hat")) == ["vocal-comp"]
    assert ids(search(entries, "NÉN GIỌNG")) == ["vocal-comp"]
    assert ids(search(entries, "loc thong cao")) == ["hpf-basics"]


def test_all_tokens_must_match(tmp_path):
    entries = build(tmp_path)
    assert ids(search(entries, "vocal slow")) == ["vocal-comp"]
    assert search(entries, "vocal nonexistentword") == []


def test_title_hits_rank_first(tmp_path):
    rows = search(build(tmp_path), "vocal")
    assert ids(rows)[0] == "vocal-comp"  # title hit outranks the tag-only hit in hpf-basics
    assert set(ids(rows)) == {"vocal-comp", "hpf-basics"}


def test_source_text_is_searched(tmp_path):
    assert ids(search(build(tmp_path), "blog")) == ["vocal-comp"]


def test_filters(tmp_path):
    entries = build(tmp_path)
    assert ids(search(entries, topic="vocals")) == ["vocal-comp"]
    assert ids(search(entries, instrument="vocal")) == ["hpf-basics", "vocal-comp"]
    assert ids(search(entries, genre="pop")) == ["vocal-comp"]
    assert ids(search(entries, technique="hpf")) == ["hpf-basics"]
    assert ids(search(entries, publisher="sound on sound")) == ["hpf-basics"]
    assert search(entries, topic="vocals", genre="rock") == []


def test_facets(tmp_path):
    counts = facets(build(tmp_path))
    assert counts["topic"] == {"eq": 1, "vocals": 1}
    assert counts["instrument"]["vocal"] == 2
    assert counts["genre"] == {"pop": 1}
    assert counts["publisher"]["Some Blog"] == 1
