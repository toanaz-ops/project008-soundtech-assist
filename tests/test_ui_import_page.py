"""The Import page wizard: pick, mapping, terms, preview and save."""

import threading

import pytest
import yaml

pytest.importorskip("PySide6.QtWidgets")

BIDV = "tests/data/BIDV TPHCM - KỊCH BẢN SK YEP 2025..xlsx"


def hold_gate(gate):
    """A never-returning provider stub the test controls via the gate."""
    gate.wait(timeout=5.0)
    return None


@pytest.fixture
def page(qt_app, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui import import_page

    return import_page.ImportPage()


@pytest.fixture
def bidv_terms(page, monkeypatch, settle):
    """The real BIDV sheet walked from pick to a built terms step."""
    from wing_parser.ui import import_page

    monkeypatch.setattr(import_page.ic, "unresolved", lambda result: ())
    page.pick_file(BIDV)
    assert settle(lambda: page.step_area.currentIndex() == 1)
    for field, letter in (("id", "A"), ("time", "B"), ("title", "E")):
        page.letter_edit(field).setText(letter)
    page.header_edit("performers").setText("Thực hiện")
    page.sheet_edit.setText("KB 8.1")
    page.header_row_spin.setValue(5)
    page.next_button.click()
    return page


def test_set_session_is_accepted_but_unused(page):
    page.set_session(None)


def test_pick_step_advances_to_mapping(page, settle):
    page.pick_file(BIDV)                     # public seam, no dialog
    assert settle(lambda: page.step_area.currentIndex() == 1)
    assert page.step_area.currentIndex() == 1


def test_pick_samples_the_workbook_into_the_preview_pane(page):
    page.pick_file(BIDV)
    assert page.sample_pane.toPlainText() != ""


def test_pick_of_a_non_xlsx_degrades_to_status_label(page, tmp_path):
    bad = tmp_path / "bad.xlsx"
    bad.write_bytes(b"not a zip")
    page.pick_file(str(bad))                 # must not raise
    assert page.status.text() != ""
    assert page.step_area.currentIndex() == 0


def test_error_message_reads_as_a_sentence_naming_a_next_action(page,
                                                                tmp_path):
    bad = tmp_path / "bad.xlsx"
    bad.write_bytes(b"not a zip")
    page.pick_file(str(bad))

    message = page.status.text()
    assert "Could not read that sheet" in message
    assert str(bad) not in message           # the raw exception is not shown
    assert "header row" in message


def test_save_dialog_offers_a_yaml_filter_not_xlsx(page, monkeypatch):
    seen = {}

    def fake_get_save_file_name(parent, title, directory, filt):
        seen["filter"] = filt
        return "", ""

    from wing_parser.ui import import_page

    monkeypatch.setattr(import_page.QFileDialog, "getSaveFileName",
                        fake_get_save_file_name)
    page.save_step.save_button.click()
    assert seen["filter"] == "YAML (*.yaml);;All files (*)"


def test_without_proposal_the_grid_starts_empty(page, settle):
    page.pick_file(BIDV)
    assert settle(lambda: page.step_area.currentIndex() == 1)
    assert page.letter_edit("title").text() == ""
    assert page.manual_hint.isVisibleTo(page)


def test_proposal_prefills_grid_and_shows_unverified_problems(page,
                                                               monkeypatch,
                                                               settle):
    from wing_parser.showcontext.ingest.suggest import MappingProposal
    from wing_parser.ui import import_page
    from wing_parser.ui.texts import text

    proposal = MappingProposal(
        sheet="KB 8.1", header_row=5,
        columns={"id": "A", "time": "B", "title": "E"},
        headers={"performers": "Thực hiện"},
        problems=("column note:C has no text on the header row.",),
    )
    monkeypatch.setattr(import_page.ic, "proposal_for",
                        lambda xlsx, factory: proposal)
    page.pick_file(BIDV)
    assert settle(lambda: page.sheet_edit.text() == "KB 8.1")
    assert page.header_row_spin.value() == 5
    assert page.letter_edit("title").text() == "E"
    assert page.header_edit("performers").text() == "Thực hiện"
    assert page.badge.text() == text("import.unverified")
    assert "note" in page.problems_label.text()


def test_clean_proposal_shows_the_verified_badge(page, monkeypatch, settle):
    from wing_parser.showcontext.ingest.suggest import MappingProposal
    from wing_parser.ui import import_page
    from wing_parser.ui.texts import text

    proposal = MappingProposal(
        sheet="KB 8.1", header_row=5,
        columns={"id": "A", "time": "B", "title": "E"},
        headers={"performers": "Thực hiện"}, problems=(),
    )
    monkeypatch.setattr(import_page.ic, "proposal_for",
                        lambda xlsx, factory: proposal)
    page.pick_file(BIDV)
    assert settle(lambda: page.badge.text() != "")
    assert page.badge.text() == text("import.verified")
    assert page.problems_label.text() == ""


def test_bad_mapping_lands_in_status_label_never_crash(page, settle):
    page.pick_file(BIDV)
    assert settle(lambda: page.step_area.currentIndex() == 1)
    page.sheet_edit.setText("sheet that does not exist")
    page.letter_edit("title").setText("A")
    page.next_button.click()                 # must not raise
    assert page.status.text() != ""
    assert page.step_area.currentIndex() == 1


def test_valid_mapping_advances_to_the_terms_step(bidv_terms, monkeypatch):
    from wing_parser.ui import import_page

    monkeypatch.setattr(import_page.ic, "unresolved",
                        lambda result: ("ca trống",))
    bidv_terms.show_terms_step(bidv_terms.result)
    assert bidv_terms.step_area.currentIndex() == 2
    assert bidv_terms.term_row_state("ca trống") == "pending"


def test_skip_marks_the_row_without_writing(page, tmp_path, monkeypatch):
    from wing_parser.ui import import_page

    class FakeResult:
        segments = [type("S", (), {"comments": [
            "row 1: could not read performer 'múa rối'"]})()]

    monkeypatch.setattr(import_page.ic, "unresolved", lambda result: ("múa rối",))
    page.set_output_directory(tmp_path)
    page.show_terms_step(FakeResult())
    page.skip_button_for("múa rối").click()
    assert page.term_row_state("múa rối") == "skipped"
    assert not (tmp_path / "classifier.yaml").exists()


def test_record_writes_the_picked_kinds_through_vocabulary_put_term(page, tmp_path, monkeypatch):
    from PySide6.QtCore import Qt
    from wing_parser.ui import import_page

    class FakeResult:
        segments = [type("S", (), {"comments": [
            "row 1: could not read performer 'ca trống'"]})()]

    monkeypatch.setattr(import_page.ic, "unresolved", lambda result: ("ca trống",))
    page.set_output_directory(tmp_path)
    page.show_terms_step(FakeResult())
    vocab = tmp_path / "classifier.yaml"

    assert page.term_row_state("ca trống") == "pending"
    assert not vocab.exists()

    row = page.terms_step._rows["ca trống"]
    hit = row.kinds_list.findItems("speech.mc", Qt.MatchFlag.MatchExactly)[0]
    hit.setSelected(True)
    page.record_button_for("ca trống").click()

    assert page.term_row_state("ca trống") == "recorded"
    assert vocab.exists()
    doc = yaml.safe_load(vocab.read_text(encoding="utf-8"))
    assert doc["cuesheet"]["ca trống"]["kinds"] == ["speech.mc"]


def test_ignore_remember_writes_ignore_true(page, tmp_path, monkeypatch):
    from wing_parser.ui import import_page

    class FakeResult:
        segments = [type("S", (), {"comments": [
            "row 1: could not read performer 'hoa tươi'"]})()]

    monkeypatch.setattr(import_page.ic, "unresolved", lambda result: ("hoa tươi",))
    page.set_output_directory(tmp_path)
    page.show_terms_step(FakeResult())

    page.terms_step._rows["hoa tươi"].ignore_button.click()
    assert page.term_row_state("hoa tươi") == "recorded"
    doc = yaml.safe_load((tmp_path / "classifier.yaml").read_text(encoding="utf-8"))
    assert doc["cuesheet"]["hoa tươi"]["ignore"] is True


def test_recording_one_term_re_resolves_a_pending_sibling(page, tmp_path, monkeypatch):
    from PySide6.QtCore import Qt
    from wing_parser.ui import import_page

    class FakeResult:
        segments = [type("S", (), {"comments": [
            "row 1: could not read performer 'trống'",
            "row 2: could not read performer 'dàn trống'",
        ]})()]

    monkeypatch.setattr(import_page.ic, "unresolved",
                        lambda result: ("trống", "dàn trống"))
    page.set_output_directory(tmp_path)
    page.show_terms_step(FakeResult())

    row = page.terms_step._rows["trống"]
    row.word_match_check.setChecked(True)   # "trống" alone equals the fragment; tick by hand
    hit = row.kinds_list.findItems("drums.kick", Qt.MatchFlag.MatchExactly)[0]
    hit.setSelected(True)
    page.record_button_for("trống").click()

    assert page.term_row_state("trống") == "recorded"
    assert page.term_row_state("dàn trống") == "resolved"


def test_a_shortened_key_auto_ticks_match_inside_a_sentence(page, tmp_path, monkeypatch):
    from wing_parser.ui import import_page

    class FakeResult:
        segments = [type("S", (), {"comments": [
            "row 1: could not read performer 'Mời BLĐ lên sân khấu'"]})()]

    monkeypatch.setattr(import_page.ic, "unresolved",
                        lambda result: ("Mời BLĐ lên sân khấu",))
    page.set_output_directory(tmp_path)
    page.show_terms_step(FakeResult())

    row = page.terms_step._rows["Mời BLĐ lên sân khấu"]
    assert row.word_match_check.isChecked() is False
    row.key_edit.setText("BLĐ")
    assert row.word_match_check.isChecked() is True


def test_the_ai_propose_button_opens_the_vocabulary_window_with_pending_fragments(
        page, tmp_path, monkeypatch):
    from wing_parser.ui import import_page

    class FakeResult:
        segments = [type("S", (), {"comments": [
            "row 1: could not read performer 'tốp múa'"]})()]

    monkeypatch.setattr(import_page.ic, "unresolved", lambda result: ("tốp múa",))
    page.set_output_directory(tmp_path)
    page.show_terms_step(FakeResult())

    seen = {}

    class _NullDialog:
        def exec(self):
            return 0

    def fake_window(parent, *, directory=None, initial_fragments=()):
        seen["fragments"] = initial_fragments
        return _NullDialog()

    import wing_parser.ui.vocabulary_window as vw_module

    monkeypatch.setattr(vw_module, "VocabularyWindow", fake_window)
    page.terms_step.ai_propose_button.click()
    assert seen["fragments"] == ("tốp múa",)


def test_the_vocabulary_button_opens_the_window_over_the_steps_own_directory(
        page, tmp_path, monkeypatch):
    """Controller requirement on top of the brief: the Terms step's
    Vocabulary... button must open the window on `self.directory` (the
    knowledge dir this wizard is using), not the library default."""
    from wing_parser.ui import import_page

    class FakeResult:
        segments = [type("S", (), {"comments": [
            "row 1: could not read performer 'tốp múa'"]})()]

    monkeypatch.setattr(import_page.ic, "unresolved", lambda result: ("tốp múa",))
    page.set_output_directory(tmp_path)
    page.show_terms_step(FakeResult())

    seen = {}

    class _NullDialog:
        def exec(self):
            return 0

    def fake_window(parent, *, directory=None, initial_fragments=()):
        seen["directory"] = directory
        return _NullDialog()

    import wing_parser.ui.vocabulary_window as vw_module

    monkeypatch.setattr(vw_module, "VocabularyWindow", fake_window)
    page.terms_step.vocabulary_button.click()
    assert seen["directory"] == tmp_path


def test_a_term_added_in_the_vocabulary_window_re_resolves_a_matching_row(
        page, tmp_path, monkeypatch):
    """Spec §8.1: closing the Vocabulary window must re-read the effective
    vocabulary and re-resolve the remaining rows, so a term taught there
    clears a matching row here without a separate reload step."""
    from wing_parser.ui import import_page

    class FakeResult:
        segments = [type("S", (), {"comments": [
            "row 1: could not read performer 'ca trống'"]})()]

    monkeypatch.setattr(import_page.ic, "unresolved", lambda result: ("ca trống",))
    page.set_output_directory(tmp_path)
    page.show_terms_step(FakeResult())

    seen = {}

    class _WritingVocabularyWindow:
        def __init__(self, parent, *, directory=None, initial_fragments=()):
            seen["directory"] = directory

        def exec(self):
            from wing_parser.classifier import vocabulary as vocab_module

            vocab_module.Vocabulary.load(seen["directory"]).put_term(
                "ca trống", kinds=("speech.mc",), match="exact")
            return 1

    import wing_parser.ui.vocabulary_window as vw_module

    monkeypatch.setattr(vw_module, "VocabularyWindow", _WritingVocabularyWindow)
    page.terms_step.vocabulary_button.click()

    assert seen["directory"] == tmp_path
    assert page.term_row_state("ca trống") == "resolved"


def test_recording_with_no_kinds_or_sets_reports_the_problem_and_keeps_the_row(
        page, tmp_path, monkeypatch):
    """Controller requirement: a Record that fails validation (put_term's
    own "needs kinds and/or sets, or ignore: true") is shown to the
    operator naming the problem; the row keeps its input and does not
    crash or silently advance."""
    from PySide6.QtWidgets import QMessageBox
    from wing_parser.ui import import_page

    class FakeResult:
        segments = [type("S", (), {"comments": [
            "row 1: could not read performer 'ca trống'"]})()]

    monkeypatch.setattr(import_page.ic, "unresolved", lambda result: ("ca trống",))
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning",
                        lambda *a, **k: warnings.append(a[-1]))
    page.set_output_directory(tmp_path)
    page.show_terms_step(FakeResult())

    page.record_button_for("ca trống").click()   # no kind/set picked

    assert warnings and "ca trống" in warnings[0]
    assert page.term_row_state("ca trống") == "pending"
    assert page.terms_step._rows["ca trống"].key_edit.text() == "ca trống"
    assert not (tmp_path / "classifier.yaml").exists()


def test_an_oserror_on_record_is_reported_and_keeps_the_row(page, tmp_path, monkeypatch):
    """Controller requirement: an OSError on write (disk trouble) is
    shown naming the problem, not raised."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QMessageBox
    from wing_parser.ui import import_page

    class FakeResult:
        segments = [type("S", (), {"comments": [
            "row 1: could not read performer 'ca trống'"]})()]

    monkeypatch.setattr(import_page.ic, "unresolved", lambda result: ("ca trống",))
    warnings = []
    monkeypatch.setattr(QMessageBox, "warning",
                        lambda *a, **k: warnings.append(a[-1]))
    page.set_output_directory(tmp_path)
    page.show_terms_step(FakeResult())

    row = page.terms_step._rows["ca trống"]
    hit = row.kinds_list.findItems("speech.mc", Qt.MatchFlag.MatchExactly)[0]
    hit.setSelected(True)

    def _boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(row._vocabulary, "put_term", _boom)
    page.record_button_for("ca trống").click()

    assert warnings and "disk full" in warnings[0]
    assert page.term_row_state("ca trống") == "pending"


def test_preview_renders_and_save_writes_utf8(bidv_terms, tmp_path):
    bidv_terms.preview_button.click()
    assert bidv_terms.step_area.currentIndex() == 3
    rendered = bidv_terms.preview_pane.toPlainText()
    assert rendered != ""
    out = tmp_path / "out.yaml"
    assert bidv_terms.save_as(str(out))      # public seam, no dialog
    assert out.read_text(encoding="utf-8") == rendered


# -- the step rail and the honest empty states (task 1b-19c) --------------


def test_the_wizard_has_a_step_rail_starting_at_pick(page):
    assert page.step_rail.step == 0
    assert page.step_rail.names == ("pick", "mapping", "vocabulary", "save")
    assert page.step_rail.labels[0].isEnabled()
    assert not page.step_rail.labels[-1].isEnabled()


def test_the_rail_follows_the_wizard(page, settle):
    page.pick_file(BIDV)
    assert settle(lambda: page.step_rail.step == 1)


def test_the_workbook_pane_says_something_at_rest(page):
    assert page.pick_step.sample_pane.toPlainText().strip() != ""


def test_a_missing_key_names_itself_and_offers_settings(qt_app, monkeypatch,
                                                        tmp_path):
    from wing_parser import config
    from wing_parser.classifier import provider

    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    monkeypatch.setenv(config.ENV_VAR, str(tmp_path / "knowledge"))
    monkeypatch.delenv(provider.ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)   # away from the repo's own ./provider.yaml
    for env in ("ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY"):
        monkeypatch.delenv(env, raising=False)   # the machine's real keys
    from wing_parser.ui.import_page import ImportPage

    page = ImportPage()
    assert page.key_status.text() != ""

    requested = []
    page.key_status.open_settings_requested.connect(lambda: requested.append(1))
    page.key_status.linkActivated.emit("settings")   # the click, offscreen
    assert requested == [1]


def test_a_present_key_keeps_the_line_empty(qt_app, monkeypatch, tmp_path):
    from wing_parser import config
    from wing_parser.classifier import provider

    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "provider.yaml").write_text("api_key: sk-test\n",
                                             encoding="utf-8")
    monkeypatch.setenv(config.ENV_VAR, str(knowledge))
    monkeypatch.delenv(provider.ENV_VAR, raising=False)
    from wing_parser.ui.import_page import ImportPage

    page = ImportPage()
    assert page.key_status.text() == ""


def test_the_key_hint_and_the_model_call_read_the_same_config(
        qt_app, monkeypatch, tmp_path):
    """The refutation that reopened D-30, pinned.

    A keyless knowledge-dir provider.yaml (Settings saved with the key
    field left empty) used to stop the key line's search while the model
    call walked on to ./provider.yaml and found a real key. The line said
    "no model key configured" about a machine that was configured.
    """
    from wing_parser import config
    from wing_parser.classifier import provider

    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "provider.yaml").write_text(
        'provider: openai-compat\napi_key: ""\napi_key_env: ""\n',
        encoding="utf-8",
    )
    (tmp_path / "provider.yaml").write_text(
        'provider: openai-compat\napi_key: "sk-real-9f3a"\n', encoding="utf-8"
    )
    monkeypatch.setenv(config.ENV_VAR, str(knowledge))
    monkeypatch.delenv(provider.ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)
    for env in ("ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY"):
        monkeypatch.delenv(env, raising=False)
    from wing_parser.ui.import_page import ImportPage

    page = ImportPage()
    # What a real call would authenticate with, built without any SDK.
    assert page._provider_factory().api_key == "sk-real-9f3a"
    assert page.key_status.text() == ""


def test_a_placeholder_key_still_reads_as_missing(qt_app, monkeypatch,
                                                  tmp_path):
    """docs/tech-debt.md#d-30: a `PASTE_KEY...` marker is not a key.

    Untracked, not shipped -- it is what the operator's own provider.yaml
    carries before they paste a real key over it. Counting it as
    configured hid this warning and the assisted path then died on the
    first model call instead of here.
    """
    from wing_parser import config
    from wing_parser.classifier import provider

    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "provider.yaml").write_text(
        "provider: openai-compat\napi_key: PASTE_KEY_DEEPSEEK_VAO_DAY\n",
        encoding="utf-8",
    )
    monkeypatch.setenv(config.ENV_VAR, str(knowledge))
    monkeypatch.delenv(provider.ENV_VAR, raising=False)
    monkeypatch.chdir(tmp_path)   # away from the repo's own ./provider.yaml
    for env in ("ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY"):
        monkeypatch.delenv(env, raising=False)
    from wing_parser.ui.import_page import ImportPage

    page = ImportPage()
    assert page.key_status.text() != ""


def test_the_key_line_rechecks_when_the_page_is_shown(qt_app, monkeypatch,
                                                      tmp_path):
    from wing_parser import config
    from wing_parser.classifier import provider

    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    knowledge = tmp_path / "knowledge"
    knowledge.mkdir()
    (knowledge / "provider.yaml").write_text("api_key: sk-test\n",
                                             encoding="utf-8")
    monkeypatch.setenv(config.ENV_VAR, str(knowledge))
    monkeypatch.delenv(provider.ENV_VAR, raising=False)
    from wing_parser.ui.import_page import ImportPage

    page = ImportPage()
    assert page.key_status.text() == ""

    # The named-config branch beats the knowledge-dir fallback, so a
    # vanished WING_PROVIDER_CONFIG flips the line without touching disk.
    monkeypatch.setenv(provider.ENV_VAR, str(tmp_path / "missing.yaml"))
    page.show()                              # the re-check trigger
    assert page.key_status.text() != ""


# -- the concurrency law on this page (task C, ruled 2026-08-26) ----------


def test_the_window_still_pumps_events_while_a_model_call_runs(
        page, monkeypatch, qt_app, settle):
    from PySide6.QtCore import QTimer

    from wing_parser.ui import import_page

    gate = threading.Event()
    monkeypatch.setattr(import_page.ic, "proposal_for",
                        lambda xlsx, factory: hold_gate(gate))
    page.pick_file(BIDV)
    ticks = []
    timer = QTimer()
    timer.setInterval(10)
    timer.timeout.connect(lambda: ticks.append(1))
    timer.start()
    try:
        assert settle(lambda: len(ticks) >= 5), "the GUI thread froze"
        assert not page.pick_step.choose_button.isEnabled()
        assert page.cancel_button.isVisibleTo(page)
    finally:
        gate.set()
        timer.stop()
    assert settle(lambda: page.step_area.currentIndex() == 1)


def test_cancel_discards_a_stuck_proposal_and_the_page_retries(
        page, monkeypatch, settle):
    from wing_parser.ui import import_page
    from wing_parser.ui.texts import text

    gate = threading.Event()
    monkeypatch.setattr(import_page.ic, "proposal_for",
                        lambda xlsx, factory: hold_gate(gate))
    page.pick_file(BIDV)
    try:
        page.cancel_button.click()
    finally:
        gate.set()
    assert page.status.text() == text("import.cancelled")
    assert page.pick_step.choose_button.isEnabled()
    assert not page.cancel_button.isVisibleTo(page)
    assert page.step_area.currentIndex() == 0

    # Retry immediately with a fast provider -- the page is usable.
    monkeypatch.setattr(import_page.ic, "proposal_for",
                        lambda xlsx, factory: None)
    page.pick_file(BIDV)
    assert settle(lambda: page.step_area.currentIndex() == 1)


def test_a_slow_proposal_times_out_with_a_message_naming_seconds(
        page, monkeypatch, settle):
    from wing_parser.ui import import_page, workers

    gate = threading.Event()
    monkeypatch.setattr(import_page.ic, "proposal_for",
                        lambda xlsx, factory: hold_gate(gate))
    monkeypatch.setitem(workers.TIMEOUTS, "proposal", 0)
    try:
        page.pick_file(BIDV)
        assert settle(lambda: "0 s" in page.status.text())
    finally:
        gate.set()
    assert page.pick_step.choose_button.isEnabled()


def test_starting_a_second_call_while_one_runs_is_queue_rejected(
        page, monkeypatch, settle):
    from wing_parser.ui import import_page

    gate = threading.Event()
    monkeypatch.setattr(import_page.ic, "proposal_for",
                        lambda xlsx, factory: hold_gate(gate))
    try:
        page.pick_file(BIDV)
        page.pick_file(BIDV)                 # a second concurrent call
        assert "already running" in page.status.text()
        assert page.step_area.currentIndex() == 0
    finally:
        gate.set()
