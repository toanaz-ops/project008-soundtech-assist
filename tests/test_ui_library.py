"""The Library page (ninth): browse, search, view, edit with sources, history."""

from __future__ import annotations

import pytest
import yaml

pytest.importorskip("PySide6.QtWidgets")

from wing_parser.library import LibraryStore, dump_entry  # noqa: E402
from wing_parser.ui import library_edit_dialog, library_history_dialog, library_page  # noqa: E402
from wing_parser.ui.texts import set_language, text  # noqa: E402

SOURCE = {"title": "Compressor basics", "publisher": "Sound On Sound", "kind": "article",
          "url": "https://example.org/comp", "accessed": "2026-11-01"}


def _entry(entry_id, title, topic="dynamics", sources=True, **extra):
    data = {
        "id": entry_id, "title": title, "topic": topic,
        "tags": {"instrument": ["vocal"], "genre": ["pop"], "technique": []},
        "summary": f"About {title}.", "body": f"Body of {title}.\n",
        "sources": [dict(SOURCE)] if sources is True else (sources or []),
        "confidence": "common-practice", "status": "reviewed", "revision": 1,
        "updated_at": "2026-11-01T10:00:00+07:00", "updated_by": "tester",
    }
    data.update(extra)
    return data


def _write(root, data):
    path = root / "entries" / f"{data['id']}.yaml"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(dump_entry(data), encoding="utf-8", newline="\n")


@pytest.fixture
def lib(tmp_path):
    shipped, user = tmp_path / "shipped", tmp_path / "user"
    shipped.mkdir()
    (shipped / "topics.yaml").write_text(yaml.safe_dump({"topics": [
        {"id": "dynamics", "en": "Dynamics", "vi": "Xu ly dong"},
        {"id": "eq", "en": "EQ", "vi": "EQ"}]}), encoding="utf-8")
    (shipped / "sources.yaml").write_text(
        yaml.safe_dump({"publishers": [{"name": "Sound On Sound"}]}), encoding="utf-8")
    _write(shipped, _entry("comp-basics", "Compressor basics"))
    _write(shipped, _entry("eq-cuts", "Subtractive EQ", topic="eq",
                           tags={"instrument": ["guitar"], "genre": ["rock"], "technique": []}))
    store = LibraryStore(user, shipped)
    store.save(_entry("my-vocal-note", "My vocal note"), author="tester", note="first")
    _write(user, _entry("hand-written", "Hand written", sources=False))
    return store


@pytest.fixture
def page(qt_app, lib, tmp_path):
    widget = library_page.LibraryPage(lib, state_dir=tmp_path / "state")
    widget.refresh()
    yield widget
    widget.close()


def _ids(page):
    from wing_parser.ui.library_tree import ID_ROLE
    ids = []
    for i in range(page.tree.topLevelItemCount()):
        group = page.tree.topLevelItem(i)
        ids += [group.child(r).data(0, ID_ROLE) for r in range(group.childCount())]
    return ids


def test_the_page_builds_and_lists_both_layers(page):
    assert set(_ids(page)) == {"comp-basics", "eq-cuts", "my-vocal-note", "hand-written"}
    assert page.selected() is not None  # first entry selected on load


def test_search_filters_the_tree(page):
    page.search_box.setText("subtractive")
    assert _ids(page) == ["eq-cuts"]
    page.search_box.setText("")
    assert len(_ids(page)) == 4


def test_group_by_switches_the_groups(page):
    def groups():
        return [page.tree.topLevelItem(i).text(0) for i in range(page.tree.topLevelItemCount())]
    assert any(g.startswith("Dynamics") for g in groups())
    page.group_box.setCurrentIndex(page.group_box.findData("genre"))
    assert any(g.startswith("rock") for g in groups())
    page.group_box.setCurrentIndex(page.group_box.findData("publisher"))
    assert any(g.startswith("Sound On Sound (") for g in groups())


def test_the_entry_view_lists_sources_and_flags_unsourced(page):
    page.tree.select_entry("comp-basics")
    markdown = page.view.browser.toMarkdown()
    assert "Sources" in markdown and "Compressor basics" in markdown
    assert "https://example.org/comp" in markdown
    assert "unsourced" not in page.view.badge_keys
    page.tree.select_entry("hand-written")
    assert "unsourced" in page.view.badge_keys


def test_an_unvetted_publisher_is_flagged(page, lib):
    _write(lib.root, _entry("odd-pub", "Odd publisher",
                            sources=[dict(SOURCE, publisher="Nobody Inc")]))
    page.refresh()
    page.tree.select_entry("odd-pub")
    assert "unvetted" in page.view.badge_keys


def _complete_form(dialog):
    form = dialog.form
    form.id_edit.setText("new-note")
    form.title_edit.setText("New note")
    form.summary_edit.setPlainText("A summary.")
    form.body_edit.setPlainText("A body.")
    form.tag_edits["instrument"].setText("vocal, drums")


def test_save_is_disabled_until_a_complete_source_exists(qt_app, lib, tmp_path):
    dialog = library_edit_dialog.EditDialog(lib, None, state_dir=tmp_path / "state")
    _complete_form(dialog)
    assert not dialog.save_button.isEnabled()  # no source
    row = dialog.form.sources.add_row()
    assert not dialog.save_button.isEnabled()  # blank source row
    for name, value in (("title", "Gain staging"), ("publisher", "Sound On Sound"),
                        ("url", "https://example.org/g")):
        dialog.form.sources.set_cell(row, name, value)
    assert dialog.save_button.isEnabled()


def test_saving_a_new_entry_bumps_the_revision_and_writes_history(qt_app, lib, tmp_path):
    dialog = library_edit_dialog.EditDialog(lib, None, state_dir=tmp_path / "state")
    _complete_form(dialog)
    row = dialog.form.sources.add_row()
    for name, value in (("title", "Gain staging"), ("publisher", "Sound On Sound"),
                        ("url", "https://example.org/g")):
        dialog.form.sources.set_cell(row, name, value)
    dialog.author_edit.setText("Toan")
    dialog.save()
    assert dialog.saved_id == "new-note"
    saved = lib.get("new-note").entry
    assert saved["revision"] == 1 and saved["updated_by"] == "Toan"
    assert saved["tags"]["instrument"] == ["vocal", "drums"]
    assert [r.rev for r in lib.history("new-note")] == [1]


def test_editing_needs_a_note_and_bumps_the_revision(qt_app, lib, tmp_path):
    loaded = lib.get("my-vocal-note")
    dialog = library_edit_dialog.EditDialog(lib, loaded, state_dir=tmp_path / "state")
    assert not dialog.form.id_edit.isEnabled()
    assert not dialog.save_button.isEnabled()  # note required
    dialog.note_edit.setText("tighten summary")
    dialog.form.summary_edit.setPlainText("Tighter.")
    assert dialog.save_button.isEnabled()
    dialog.save()
    after = lib.get("my-vocal-note")
    assert after.entry["revision"] == 2 and after.entry["summary"] == "Tighter."
    assert [r.rev for r in lib.history("my-vocal-note")] == [1, 2]


def test_a_revision_conflict_reloads_instead_of_overwriting(qt_app, lib, tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(library_edit_dialog, "warn", lambda *a: seen.append(a))
    dialog = library_edit_dialog.EditDialog(lib, lib.get("my-vocal-note"), state_dir=tmp_path / "state")
    lib.save(dict(lib.get("my-vocal-note").entry, summary="Changed elsewhere."),
             author="other", note="x")
    dialog.note_edit.setText("mine")
    dialog.save()
    assert seen and dialog.saved_id == ""
    assert dialog.form.summary_edit.toPlainText() == "Changed elsewhere."


def test_history_shows_the_diff_and_restore_makes_a_new_revision(qt_app, lib, tmp_path, monkeypatch):
    lib.save(dict(lib.get("my-vocal-note").entry, summary="Second."), author="t", note="two")
    monkeypatch.setattr(library_history_dialog, "confirm", lambda *a: True)
    dialog = library_history_dialog.HistoryDialog(lib, "my-vocal-note", state_dir=tmp_path / "state")
    assert dialog.table.rowCount() == 2
    assert "Second." in dialog.diff_view.toPlainText()
    assert not dialog.restore_button.isEnabled()  # latest selected
    dialog.table.selectRow(1)
    assert dialog.restore_button.isEnabled()
    dialog.restore_selected()
    revisions = lib.history("my-vocal-note")
    assert [r.rev for r in revisions] == [1, 2, 3] and revisions[-1].action == "restore"
    assert lib.get("my-vocal-note").entry["summary"] == "About My vocal note."


def test_retire_hides_the_entry_until_show_retired(page, monkeypatch):
    monkeypatch.setattr(library_page, "confirm_retire", lambda *a: True)
    page.tree.select_entry("my-vocal-note")
    page.retire_entry()
    assert "my-vocal-note" not in _ids(page)
    page.retired_check.setChecked(True)
    assert "my-vocal-note" in _ids(page)


def test_the_page_renders_in_vietnamese(qt_app, lib):
    set_language("vi")
    try:
        widget = library_page.LibraryPage(lib)
        widget.refresh()
        assert widget.new_button.text() == text("library.new") != "New entry"
    finally:
        set_language("en")


def test_media_renders_as_links_and_sources_are_numbered(lib):
    from wing_parser.ui.library_markdown import entry_markdown
    entry = _entry("with-media", "With media", media=[
        {"kind": "video", "url": "https://example.org/v", "title": "Clip", "channel": "Chan",
         "timestamp": "1:23"},
        {"kind": "image", "url": "https://example.org/i", "caption": "A photo",
         "license": "CC0-1.0", "attribution": "Someone"}])
    _write(lib.root, entry)
    markdown = entry_markdown(lib.get("with-media"), lib, {})
    assert "[Clip · Chan · 1:23](<https://example.org/v>)" in markdown
    assert "Licence: CC0-1.0" in markdown and "1. **Compressor basics**" in markdown


def test_retiring_a_broken_entry_works_and_a_conflict_warns(page, lib, monkeypatch):
    monkeypatch.setattr(library_page, "confirm_retire", lambda *a: True)
    shown = []
    monkeypatch.setattr(library_page, "warn", lambda *a: shown.append(a))
    page.tree.select_entry("hand-written")
    assert lib.get("hand-written").has_errors
    page.retire_entry()
    assert lib.get("hand-written").entry["status"] == "retired" and not shown
    page.tree.select_entry("my-vocal-note")
    lib.save(_entry("my-vocal-note", "Moved on"), author="x", note="n", expected_revision=1)
    page.retire_entry()
    assert len(shown) == 1 and lib.get("my-vocal-note").entry["status"] != "retired"


def test_a_new_entry_never_overwrites_an_existing_hand_written_file(qt_app, lib, tmp_path, monkeypatch):
    shown = []
    monkeypatch.setattr(library_edit_dialog, "warn", lambda *a: shown.append(a))
    dialog = library_edit_dialog.EditDialog(lib, None, None, tmp_path / "state")
    dialog.form.to_entry = lambda: _entry("hand-written", "Overwrite")
    path = lib.root / "entries" / "hand-written.yaml"
    before = path.read_text(encoding="utf-8")
    dialog.save()
    assert shown and path.read_text(encoding="utf-8") == before


def test_vietnamese_view_shows_vi_text_and_falls_back_with_a_note(lib):
    from wing_parser.ui.library_markdown import entry_markdown
    media = [{"kind": "image", "url": "https://example.org/i", "caption": "A photo",
              "caption_vi": "Ảnh minh hoạ", "license": "CC0-1.0", "attribution": "S"}]
    _write(lib.root, _entry("has-vi", "Has VI", title_vi="Có VI", media=media,
                            summary_vi="Tóm tắt VI", body_vi="Nội dung VI"))
    _write(lib.root, _entry("no-vi", "No VI"))
    set_language("vi")
    try:
        md = entry_markdown(lib.get("has-vi"), lib, {})
        assert md.startswith("# Có VI") and "Nội dung VI" in md and "Ảnh minh hoạ" in md
        assert text("library.view.no_vi") not in md
        fallback = entry_markdown(lib.get("no-vi"), lib, {})
        assert text("library.view.no_vi") in fallback and "Compressor" in fallback
    finally:
        set_language("en")
    english = entry_markdown(lib.get("has-vi"), lib, {})
    assert english.startswith("# Has VI") and "Nội dung VI" not in english
    assert "A photo" in english and "Ảnh minh hoạ" not in english


def test_edit_form_round_trips_vietnamese_fields_and_omits_empty(qt_app, lib):
    from wing_parser.ui.library_edit_form import EntryForm
    form = EntryForm({"dynamics": {"id": "dynamics", "en": "Dynamics", "vi": "Động"}}, True)
    form.load(_entry("x", "X", summary_vi="Tóm tắt", body_vi="Nội dung"))
    out = form.to_entry()
    assert out["summary_vi"] == "Tóm tắt" and out["body_vi"] == "Nội dung"
    form.summary_vi_edit.setPlainText("")
    form.body_vi_edit.setPlainText("  \n")
    out = form.to_entry()
    assert "summary_vi" not in out and "body_vi" not in out
