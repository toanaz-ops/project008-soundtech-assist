"""Validation, save, history, restore, retire and the shipped/user overlay."""

import pytest

from tests.library_support import SOURCE, entry, make_root, write_raw
from wing_parser.library import (
    LibraryStore,
    EntryExists,
    RevisionConflict,
    ValidationFailed,
    default_author,
    load_publishers,
    load_topics,
    validate,
)


@pytest.fixture
def root(tmp_path):
    return make_root(tmp_path / "lib")


@pytest.fixture
def store(root):
    return LibraryStore(root)


def codes(root, data, media_root=None):
    issues = validate(data, topics=load_topics(root), publishers=load_publishers(root),
                      media_root=media_root)
    return {(i.level, i.code) for i in issues}


def full(**overrides):
    return entry(revision=1, updated_at="2026-11-09T10:00:00+07:00", updated_by="t", **overrides)


def test_valid_entry_has_no_issues(root):
    assert codes(root, full()) == set()


def test_missing_field(root):
    data = full()
    del data["summary"]
    assert ("error", "missing-field") in codes(root, data)


def test_bad_id(root):
    assert ("error", "bad-id") in codes(root, full(id="Bad_ID"))


def test_bad_topic(root):
    assert ("error", "bad-topic") in codes(root, full(topic="nope"))


def test_unsourced(root):
    assert ("error", "unsourced") in codes(root, full(sources=[]))


def test_bad_source(root):
    bad = dict(SOURCE, url="ftp://x", accessed="yesterday")
    assert ("error", "bad-source") in codes(root, full(sources=[bad]))
    no_url = {k: v for k, v in SOURCE.items() if k != "url"}
    assert ("error", "bad-source") in codes(root, full(sources=[no_url]))
    assert ("error", "bad-source") not in codes(root, full(sources=[dict(no_url, kind="book")]))


def test_unvetted_source_is_only_a_warning(root):
    result = codes(root, full(sources=[dict(SOURCE, publisher="Some Blog")]))
    assert result == {("warning", "unvetted-source")}
    assert codes(root, full(sources=[dict(SOURCE, publisher="sos")])) == set()  # alias, any case


def test_bad_media_and_missing_media_file(root):
    assert ("error", "bad-media") in codes(root, full(media=[{"kind": "gif"}]))
    diagram = {"kind": "diagram", "path": "a.png", "caption": "c", "license": "CC0-1.0",
               "attribution": "x", "generated_by": "s"}
    result = codes(root, full(media=[diagram]), media_root=root / "media")
    assert ("error", "missing-media-file") in result
    (root / "media" / "hpf-basics").mkdir(parents=True)
    (root / "media" / "hpf-basics" / "a.png").write_bytes(b"x")
    assert codes(root, full(media=[diagram]), media_root=root / "media") == set()


def test_bad_enum_and_bad_tags(root):
    assert ("error", "bad-enum") in codes(root, full(confidence="sure"))
    assert ("error", "bad-enum") in codes(root, full(status="done"))
    assert ("error", "bad-tags") in codes(root, full(tags={"instrument": ["Not Kebab"]}))
    assert ("error", "bad-tags") in codes(root, full(tags={"mood": []}))


def test_unsourced_save_is_blocked_and_nothing_written(store, root):
    with pytest.raises(ValidationFailed) as caught:
        store.save(entry(sources=[]), author="t", note="n")
    assert any(i.code == "unsourced" for i in caught.value.issues)
    assert not (root / "entries" / "hpf-basics.yaml").exists()
    assert not (root / "history").exists()


def test_unvetted_source_saves_with_warning(store):
    saved = store.save(entry(sources=[dict(SOURCE, publisher="Some Blog")]), author="t")
    assert saved["revision"] == 1
    assert [i.code for i in store.get("hpf-basics").issues] == ["unvetted-source"]


def test_round_trip_save_edit_history_diff_restore(store, root):
    first = store.save(entry(), author="alice", note="create")
    assert first["revision"] == 1 and first["updated_by"] == "alice"
    assert first["updated_at"][-6] in "+-"  # local tz offset

    changed = entry(summary="A changed summary.")
    second = store.save(changed, author="bob", note="reword", expected_revision=1)
    assert second["revision"] == 2

    rows = store.history("hpf-basics")
    assert [(r.rev, r.author, r.action) for r in rows] == [(1, "alice", "create"), (2, "bob", "edit")]
    diff = store.diff("hpf-basics", 1, 2)
    assert "-summary: Why and where" in diff and "+summary: A changed summary." in diff

    third = store.restore("hpf-basics", 1, author="carol", note="undo")
    assert third["revision"] == 3
    assert third["summary"] == first["summary"]
    assert store.history("hpf-basics")[-1].action == "restore"
    assert len(store.history("hpf-basics")) == 3  # history only grows


def test_file_format(store, root):
    store.save(entry(), author="t")
    text = (root / "entries" / "hpf-basics.yaml").read_bytes().decode("utf-8")
    assert "\r" not in text and "Lọc thông cao" in text
    assert "body: |\n" in text
    keys = [line.split(":")[0] for line in text.splitlines() if line and line[0].isalpha()]
    assert keys == ["id", "title", "title_vi", "topic", "tags", "summary", "body", "sources",
                    "confidence", "status", "revision", "updated_at", "updated_by"]


def test_revision_conflict(store):
    store.save(entry(), author="a")
    store.save(entry(), author="b", expected_revision=1)
    with pytest.raises(RevisionConflict):
        store.save(entry(), author="c", expected_revision=1)
    assert store.get("hpf-basics").entry["revision"] == 2


def test_retire_hides_from_default_listing(store):
    store.save(entry(), author="a")
    store.retire("hpf-basics", author="a", note="obsolete")
    assert store.entries() == []
    assert [e.id for e in store.entries(include_retired=True)] == ["hpf-basics"]
    assert store.get("hpf-basics").entry["status"] == "retired"
    assert store.history("hpf-basics")[-1].action == "retire"


def test_hand_written_files_are_loaded_and_flagged(store, root):
    write_raw(root, entry("hand-made", sources=[]))
    (root / "entries" / "broken.yaml").write_text("id: [unclosed", encoding="utf-8")
    loaded = {e.id: e for e in store.entries()}
    assert {i.code for i in loaded["hand-made"].issues} == {"unsourced"}
    assert [i.code for i in loaded["broken"].issues] == ["bad-yaml"]


def test_editing_a_hand_written_entry_logs_a_baseline(store, root):
    write_raw(root, entry("hand-made"))
    store.save(entry("hand-made", summary="Changed."), author="a", note="n", expected_revision=1)
    assert [r.rev for r in store.history("hand-made")] == [1, 2]
    assert "summary" in store.diff("hand-made", 1, 2)


def test_media_file_blocks_path_traversal(store):
    with pytest.raises(ValueError):
        store.media_file("hpf-basics", "../../secret.txt")


def test_default_author_is_a_nonempty_string():
    assert isinstance(default_author(), str) and default_author()


# -- overlay: shipped layer under the user layer -------------------------------
@pytest.fixture
def layers(tmp_path):
    shipped = make_root(tmp_path / "shipped")
    user = make_root(tmp_path / "user")
    return shipped, user, LibraryStore(user, shipped)


def snapshot_files(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def test_shipped_entry_appears_when_user_layer_lacks_it(layers):
    shipped, _user, store = layers
    write_raw(shipped, entry("shipped-one"))
    found = store.entries()
    assert [(e.id, e.layer) for e in found] == [("shipped-one", "shipped")]
    assert store.get("shipped-one").layer == "shipped"


def test_user_entry_overrides_shipped_by_id(layers):
    shipped, user, store = layers
    write_raw(shipped, entry("same", title="Shipped title"))
    write_raw(user, entry("same", title="User title"))
    found = store.entries()
    assert [(e.id, e.layer, e.entry["title"]) for e in found] == [("same", "user", "User title")]


def test_saving_a_shipped_entry_writes_only_to_the_user_layer(layers):
    shipped, user, store = layers
    write_raw(shipped, entry("shipped-one"))
    before = snapshot_files(shipped)
    saved = store.save(entry("shipped-one", summary="Mine."), author="me", note="tweak",
                       expected_revision=1)
    assert saved["revision"] == 2
    assert snapshot_files(shipped) == before
    assert (user / "entries" / "shipped-one.yaml").is_file()
    assert store.get("shipped-one").layer == "user"
    rows = store.history("shipped-one")
    assert [(r.rev, r.action) for r in rows] == [(1, "shipped"), (2, "edit")]
    assert "summary" in store.diff("shipped-one", 1, 2)


def test_conflict_is_checked_against_the_shipped_revision(layers):
    shipped, _user, store = layers
    write_raw(shipped, entry("shipped-one"))
    with pytest.raises(RevisionConflict):
        store.save(entry("shipped-one"), author="me", expected_revision=5)


def test_taxonomy_falls_back_to_shipped(tmp_path):
    shipped = make_root(tmp_path / "shipped")
    user = tmp_path / "user"
    (user / "entries").mkdir(parents=True)
    store = LibraryStore(user, shipped)
    saved = store.save(entry(), author="me")  # topic "eq" only known to shipped topics.yaml
    assert saved["revision"] == 1


def test_media_lookup_tries_user_then_shipped(layers):
    shipped, user, store = layers
    (shipped / "media" / "e").mkdir(parents=True)
    (shipped / "media" / "e" / "a.png").write_bytes(b"s")
    assert store.media_file("e", "a.png") == (shipped / "media" / "e" / "a.png").resolve()
    (user / "media" / "e").mkdir(parents=True)
    (user / "media" / "e" / "a.png").write_bytes(b"u")
    assert store.media_file("e", "a.png") == (user / "media" / "e" / "a.png").resolve()


def test_single_layer_when_shipped_root_equals_root(root):
    store = LibraryStore(root, root)
    assert store.shipped_root is None


def test_retire_works_on_an_entry_with_validation_errors(store, root):
    write_raw(root, entry("hand-made", sources=[]))
    assert store.get("hand-made").has_errors
    written = store.retire("hand-made", author="a", note="drop it", expected_revision=1)
    assert written["status"] == "retired" and written["revision"] == 2
    assert store.history("hand-made")[-1].action == "retire"


def test_retire_still_checks_the_revision(store):
    store.save(entry("hpf-basics"), author="a", note="n")
    with pytest.raises(RevisionConflict):
        store.retire("hpf-basics", author="a", expected_revision=9)
    # ordinary saves still validate
    with pytest.raises(ValidationFailed):
        store.save(entry("hpf-basics", sources=[]), author="a", note="n", expected_revision=1)


def test_create_refuses_an_existing_hand_written_file(store, root):
    path = write_raw(root, entry("hand-made"))
    before = path.read_text(encoding="utf-8")
    with pytest.raises(EntryExists):
        store.save(entry("hand-made", summary="Overwrite."), author="a", note="n", create=True)
    assert path.read_text(encoding="utf-8") == before


def test_create_refuses_an_id_in_the_shipped_layer(tmp_path):
    shipped = make_root(tmp_path / "shipped")
    LibraryStore(shipped).save(entry("hpf-basics"), author="a", note="n")
    user = make_root(tmp_path / "user")
    with pytest.raises(EntryExists):
        LibraryStore(user, shipped).save(entry("hpf-basics"), author="a", note="n", create=True)


def test_history_skips_a_truncated_line(store, root):
    store.save(entry("hpf-basics"), author="a", note="one")
    store.save(entry("hpf-basics", summary="Two."), author="a", note="two", expected_revision=1)
    path = root / "history" / "hpf-basics.jsonl"
    with open(path, "a", encoding="utf-8", newline="\n") as handle:
        handle.write('{"rev": 3, "at": "x", "auth')
    revisions, skipped = store.history_report("hpf-basics")
    assert [r.rev for r in revisions] == [1, 2] and skipped == 1
    store.save(entry("hpf-basics", summary="Three."), author="a", note="three", expected_revision=2)


def test_load_errors_name_the_file_not_the_server_path(store, root):
    (root / "entries" / "broken.yaml").write_text("id: [unclosed", encoding="utf-8")
    message = store.get("broken").issues[0].message
    assert "broken.yaml" in message and str(root) not in message


def test_diagram_path_must_be_a_plain_file_name(root):
    for bad in ("../x.png", "a/b.png", "a" + chr(92) + "b.png", "/abs.png", "C:/x.png"):
        diagram = {"kind": "diagram", "path": bad, "caption": "c", "license": "CC0-1.0",
                   "attribution": "a", "generated_by": "g"}
        assert ("error", "bad-media") in codes(root, full(media=[diagram])), bad
