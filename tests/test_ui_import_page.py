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


def test_record_writes_vocabulary_only_on_click(page, tmp_path, monkeypatch,
                                                settle):
    """The G2b invariant: nothing writes without the explicit click."""
    from wing_parser.classifier.matcher import Classification
    from wing_parser.ui import import_page

    class FakeResult:
        segments = [type("S", (), {"comments": [
            "row 1: could not read performer 'ca trống'"]})()]

    monkeypatch.setattr(import_page.ic, "unresolved",
                        lambda result: ("ca trống",))
    monkeypatch.setattr(import_page.ic, "guesses_for",
                        lambda terms, ctx, factory: [
                            ("ca trống", Classification(
                                kind="music.traditional", confidence=0.9,
                                origin="g2b-assisted"))])
    page.set_output_directory(tmp_path)      # where record_term writes
    page.show_terms_step(FakeResult())       # builds step 3 UI
    vocab = tmp_path / "classifier.yaml"

    assert page.term_row_state("ca trống") == "pending"
    page.load_guesses_button.click()         # prefill, not a write
    assert settle(lambda: page.kind_editor_for("ca trống").text() != "")
    assert page.kind_editor_for("ca trống").text() == "music.traditional"
    assert not vocab.exists()                # NO click -> nothing written

    page.record_button_for("ca trống").click()
    assert page.term_row_state("ca trống") == "recorded"
    assert vocab.exists()                    # after click -> the term is there
    doc = yaml.safe_load(vocab.read_text(encoding="utf-8"))
    assert doc["cuesheet"]["ca trống"]["kind"] == "music.traditional"


def test_skip_marks_the_row_without_writing(page, tmp_path, monkeypatch):
    from wing_parser.ui import import_page

    class FakeResult:
        segments = [type("S", (), {"comments": [
            "row 1: could not read performer 'múa rối'"]})()]

    monkeypatch.setattr(import_page.ic, "unresolved",
                        lambda result: ("múa rối",))
    monkeypatch.setattr(import_page.ic, "guesses_for",
                        lambda terms, ctx, factory: [])
    page.set_output_directory(tmp_path)
    page.show_terms_step(FakeResult())
    page.skip_button_for("múa rối").click()
    assert page.term_row_state("múa rối") == "skipped"
    assert not (tmp_path / "classifier.yaml").exists()


def test_raising_provider_factory_degrades_to_status_label(page, monkeypatch,
                                                           settle):
    from wing_parser.ui import import_page

    class FakeResult:
        segments = [type("S", (), {"comments": [
            "row 1: could not read performer 'ca trống'"]})()]

    def boom(*args):
        raise RuntimeError("offline")

    monkeypatch.setattr(import_page.ic, "unresolved",
                        lambda result: ("ca trống",))
    monkeypatch.setattr(import_page.ic, "guesses_for", boom)
    page.show_terms_step(FakeResult())
    page.load_guesses_button.click()         # must not raise
    assert settle(lambda: page.status.text() != "")
    assert page.status.text() != ""
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
    """docs/tech-debt.md#d-30: the shipped `PASTE_KEY...` is not a key.

    Counting it as configured hid this warning and the assisted path
    then died on the first model call instead of here.
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


def test_guesses_cancel_leaves_the_terms_step_retriable(
        page, monkeypatch, settle):
    from wing_parser.classifier.matcher import Classification
    from wing_parser.ui import import_page

    class FakeResult:
        segments = [type("S", (), {"comments": [
            "row 1: could not read performer 'ca trống'"]})()]

    monkeypatch.setattr(import_page.ic, "unresolved",
                        lambda result: ("ca trống",))
    gate = threading.Event()

    def stuck(terms, ctx, factory):
        return hold_gate(gate)

    monkeypatch.setattr(import_page.ic, "guesses_for", stuck)
    page.show_terms_step(FakeResult())
    page.load_guesses_button.click()
    try:
        page.terms_step.cancel_button.click()
    finally:
        gate.set()
    assert page.status.text() != ""
    assert page.load_guesses_button.isEnabled()

    monkeypatch.setattr(import_page.ic, "guesses_for",
                        lambda terms, ctx, factory: [
                            ("ca trống", Classification(
                                kind="music.traditional", confidence=0.9,
                                origin="g2b-assisted"))])
    page.load_guesses_button.click()
    assert settle(lambda: page.kind_editor_for("ca trống").text() != "")


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
