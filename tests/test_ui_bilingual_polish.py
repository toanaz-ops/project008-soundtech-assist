"""Visual-review fixes for the bilingual UI (2026-09-29): every test builds
the real widget and asserts geometry or displayed text, not pixels."""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import Qt
from PySide6.QtGui import QFontMetrics
from PySide6.QtWidgets import QApplication

from tests.fake_desk import FakeDesk
from wing_parser.net.identity import WingIdentity
from wing_parser.ui import texts

LANGS = ("en", "vi")


@pytest.fixture
def themed(qt_app):
    """The house theme (idempotent) so sizes include the real QSS padding."""
    from wing_parser.ui.theme import apply as apply_theme

    apply_theme(qt_app)
    return qt_app


@pytest.fixture
def knowledge(themed, monkeypatch, tmp_path):
    from wing_parser import config

    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    monkeypatch.setattr(config, "knowledge_dir", lambda override=None: tmp_path)
    return tmp_path


def _identity():
    return WingIdentity(ip="192.168.128.28", name="WING-GIAQUY",
                        model="wing-rack", serial="01009Y90604AAE",
                        firmware="3.1-0-g9f314617:release")


def _gate(desk):
    from wing_parser.ui.live_state import LiveState
    from wing_parser.ui.live_wiring import WriteGate

    class _Bar:
        def host(self):
            return "192.168.128.28"

    class _Page:
        state = LiveState.CONNECTED
        connect_bar = _Bar()

    return WriteGate(_Page(), transport=desk.write_transport(), timeout=2)


def _session(vu_path):
    from wing_parser.ui.session import Session

    return Session.open(vu_path, None)


# -- 1. the Arm button fits its text ------------------------------------


@pytest.mark.parametrize("shown", (True, False), ids=("shown", "rendered"))
@pytest.mark.parametrize("lang", LANGS)
def test_the_armed_button_is_as_wide_as_its_text(knowledge, vu_path, lang, shown):
    """`rendered` is the screenshot path: a fixed-size window grabbed
    without ever being shown (the layout has not been polished by a show)."""
    from PySide6.QtGui import QImage
    from wing_parser.ui.main_window import MainWindow

    texts.set_language(lang)
    window = MainWindow(_session(vu_path))
    window.setFixedSize(1280, 760)
    window.switch_to("doctor")
    if shown:
        window.show()
    doctor = window.pages["doctor"]
    window.write_gate._transport = FakeDesk(
        identity=_identity()).write_transport()
    window.write_gate.arm.arm(_identity())
    window.write_gate.changed.emit()
    QApplication.processEvents()
    if not shown:
        window.render(QImage(1280, 760, QImage.Format.Format_ARGB32_Premultiplied))

    button = doctor.arm_button
    shown = button.text()
    assert "WING-GIAQUY" in shown
    need = QFontMetrics(button.font()).horizontalAdvance(shown)
    assert button.width() >= button.sizeHint().width()
    assert button.width() >= need + 16          # text plus some padding
    # the selector gave way, but not below its own longest item
    box = doctor.level_box
    widest = max(QFontMetrics(box.font()).horizontalAdvance(box.itemText(i))
                 for i in range(box.count()))
    assert box.width() >= widest + 24
    parent = button.parentWidget()
    assert button.geometry().right() <= parent.width()   # not pushed off


# -- 2. the send-result badge is readable whole -----------------------------


def _record(readback, matched, written="PRE", desk_before="POST",
            address="/ch/1/send/8/mode", path="ae_data.ch.1.send.8.mode"):
    from wing_parser.net.write import SetResult
    from wing_parser.ui.live_write import SentWrite

    return SentWrite(address=address, path=path, desk_before=desk_before,
                     written=written,
                     result=SetResult(address, written, str(written), False,
                                      readback, matched))


def _patch(path, before, after, label):
    from wing_parser.edit.journal import Patch

    return Patch(path=path, before=before, after=after, because="x", label=label)


@pytest.mark.parametrize("width", (760, 480))
@pytest.mark.parametrize("lang", LANGS)
def test_every_badge_is_fully_visible_and_wrapped(knowledge, lang, width):
    from wing_parser.ui.changes_panel import ChangesPanel

    texts.set_language(lang)
    desk = FakeDesk(identity=_identity())
    panel = ChangesPanel()
    panel.attach_gate(_gate(desk))
    panel.attach_window(None)
    patches = (
        _patch("ae_data.ch.1.send.8.mode", "POST", "PRE", "Set the send to PRE"),
        _patch("ae_data.ch.2.fdr", -6.0, 12.0, "Set the fader to +12.0 dB"),
        _patch("ae_data.ch.3.in.set.inv", True, False, "Clear the polarity"),
    )
    panel.set_changes(patches)
    records = (
        _record("PRE", True),
        _record(10.0, False, written=12.0, address="/ch/2/fdr",
                path="ae_data.ch.2.fdr"),
        _record(None, False, written=False, address="/ch/3/in/set/inv",
                path="ae_data.ch.3.in.set.inv"),
    )
    for patch, record in zip(patches, records):
        panel._badge(patch, record)
    panel.resize(width, 460)
    panel.show()
    QApplication.processEvents()

    for index in range(3):
        item = panel.list.item(index)
        row = panel.list.itemWidget(item)
        badge = row.badge
        shown = badge.text()
        assert shown and badge.isVisible()
        assert badge.wordWrap() is True
        assert badge.toolTip() == shown          # the whole conclusion
        metrics = QFontMetrics(badge.font())
        needed = metrics.boundingRect(
            0, 0, badge.width(), 10_000,
            int(Qt.TextFlag.TextWordWrap), shown).height()
        assert badge.height() >= needed          # no line is cut off
        # the list item is as tall as the row wants to be at this width
        assert item.sizeHint().height() >= row.layout().totalHeightForWidth(
            panel.list.viewport().width())
        # and the badge sits below the label, not squeezed beside it
        assert badge.geometry().top() >= row.label.geometry().bottom()


# -- 3. the step rail separates its steps ----------------------------------


@pytest.mark.parametrize("lang", LANGS)
def test_step_rail_gaps_are_wider_than_a_word_gap(themed, lang):
    from wing_parser.ui.import_page import STEPS
    from wing_parser.ui.step_rail import StepRail

    texts.set_language(lang)
    steps = tuple((s, texts.text(f"import.step.{s}")) for s in STEPS)
    rail = StepRail(steps)
    rail.resize(900, 30)
    rail.show()
    QApplication.processEvents()

    assert len(rail.separators) == len(steps) - 1
    word_gap = QFontMetrics(rail.labels[0].font()).horizontalAdvance(" ")
    for left, right in zip(rail.labels, rail.labels[1:]):
        gap = right.geometry().left() - left.geometry().right()
        assert gap >= 3 * word_gap, (gap, word_gap)
    for separator, left, right in zip(rail.separators, rail.labels,
                                      rail.labels[1:]):
        assert left.geometry().right() < separator.geometry().left()
        assert separator.geometry().right() < right.geometry().left()


# -- 4. Doctor filters and findings: translated display, raw data ----------


def _expected(kind, token):
    return texts.text(f"token.{kind}.{token}")


@pytest.mark.parametrize("lang", LANGS)
def test_filter_combos_show_translated_names_but_keep_raw_tokens(
        themed, lang):
    from wing_parser.advisory.models import LAYERS, SEVERITIES
    from wing_parser.ui.findings_view import ALL, FindingsView

    texts.set_language(lang)
    view = FindingsView()
    for box, kind, tokens in ((view._severity, "severity", SEVERITIES),
                              (view._layer, "layer", LAYERS)):
        assert box.count() == len(tokens) + 1
        assert box.itemData(0) == ALL
        assert box.itemText(0) == texts.text("token.all")
        for i, token in enumerate(tokens, start=1):
            assert box.itemData(i) == token
            assert box.itemText(i) == _expected(kind, token)
    if lang == "vi":
        assert view._severity.itemText(0) != "all"
        assert view._severity.itemText(2) == "cảnh báo"


def test_filtering_compares_the_token_never_the_display_text(
        themed, vu_path):
    from wing_parser.ui.findings_view import FindingsView

    texts.set_language("vi")
    view = FindingsView()
    findings = _session(vu_path).findings()
    view.set_findings(findings)
    warned = [f for f in findings if f.severity == "warning"]
    assert warned and len(warned) < len(findings)
    index = view._severity.findData("warning")
    view._severity.setItemText(index, "zzz-not-a-token")   # display is free
    view._severity.setCurrentIndex(index)
    assert view.visible_findings() == warned
    view._layer.setCurrentIndex(view._layer.findData("show"))
    assert view.visible_findings() == []


def test_the_findings_cells_and_detail_title_use_display_names(
        themed, vu_path):
    from wing_parser.ui.detail_panel import DetailPanel
    from wing_parser.ui.findings_model import FindingsModel

    texts.set_language("vi")
    session = _session(vu_path)
    model = FindingsModel()
    model.set_findings(session.findings())
    first = model.finding_at(0)
    assert model.index(0, 0).data() == _expected("severity", first.severity)
    assert model.index(0, 4).data() == _expected("layer", first.layer)
    assert first.severity != model.index(0, 0).data()      # really translated
    panel = DetailPanel()
    panel.show_finding(first, session)
    title = panel.title_label.text()
    assert _expected("severity", first.severity) in title
    assert _expected("layer", first.layer) in title


@pytest.mark.parametrize("lang", LANGS)
def test_no_fixed_findings_column_elides_its_widest_cell(
        themed, vu_path, lang):
    from wing_parser.ui.findings_view import FindingsView
    from wing_parser.ui.theme import tokens

    texts.set_language(lang)
    view = FindingsView()
    view.resize(900, 500)
    view.set_findings(_session(vu_path).findings())
    view.show()
    QApplication.processEvents()
    model, table = view._model, view._table
    metrics = QFontMetrics(table.font())
    pad = tokens.METRICS["unit"] * 2
    for column in (0, 1, 2, 4):
        widest = max(metrics.horizontalAdvance(str(model.index(r, column).data()))
                     for r in range(model.rowCount()))
        # `MonoDelegate` paints in `width - pad`; Qt's own item margin
        # takes a few more pixels, so demand a little room on top of it.
        assert table.columnWidth(column) >= widest + pad + 6, column


def test_an_unknown_token_is_shown_raw(themed):
    from wing_parser.ui import token_labels

    texts.set_language("vi")
    assert token_labels.label("severity", "catastrophic") == "catastrophic"
    assert token_labels.label("layer", "future-layer") == "future-layer"


# -- 5. Channels: Mute column ----------------------------------------------


@pytest.mark.parametrize("lang", LANGS)
def test_the_muted_column_says_yes_or_no_not_true_or_false(
        themed, vu_path, lang):
    from wing_parser.ui.channels_page import COLUMNS, ChannelsPage

    texts.set_language(lang)
    page = ChannelsPage()
    page.set_session(_session(vu_path))
    column = COLUMNS.index("muted")
    assert page.rows
    yes, no = texts.text("token.muted.yes"), texts.text("token.muted.no")
    for i, row in enumerate(page.rows):
        cell = page.channels_model.item(i, column).text()
        assert cell == (yes if row.muted else no)
        assert cell not in ("True", "False")
    if lang == "vi":
        assert (yes, no) == ("Có", "Không")


# -- 6. Vocabulary tables: source / match display ---------------------------


@pytest.mark.parametrize("lang", LANGS)
def test_vocabulary_source_and_match_cells_are_translated(
        themed, tmp_path, lang):
    from wing_parser.ui.vocabulary_window import VocabularyWindow

    texts.set_language(lang)
    window = VocabularyWindow(directory=tmp_path)
    window.vocabulary.put_term("cajon", kinds=("drums.pad",), match="word")
    window._reload()
    terms = window.terms_tab.table
    origin_col = terms.columnCount() - 1
    match_col = terms.columnCount() - 2
    cells = {(terms.item(r, match_col).text(), terms.item(r, origin_col).text())
             for r in range(terms.rowCount())}
    assert (texts.text("token.match.word"),
            texts.text("token.origin.manual")) in cells
    assert any(o == texts.text("token.origin.default") for _, o in cells)
    sets = window.sets_tab.table
    origins = {sets.item(r, sets.columnCount() - 1).text()
               for r in range(sets.rowCount())}
    assert texts.text("token.origin.default") in origins
    if lang == "vi":
        assert "mặc định" in origins and "default" not in origins
        assert "word" not in {c[0] for c in cells}
    # the data itself is untouched
    assert {t.origin for t in window.vocabulary.terms()} <= {"default", "manual"}


# -- 7. VI verdict wording ------------------------------------------------


def test_verdict_none_yet_reads_naturally_in_vietnamese():
    assert texts.VI["verdict.none_yet"] == "{rule}: chưa có nhận định nào"


# -- 8. Settings: the API-key placeholder fits -----------------------------


@pytest.mark.parametrize("lang", LANGS)
def test_the_api_key_placeholder_fits_the_field_at_default_size(
        knowledge, lang):
    from wing_parser.ui.settings_dialog import SettingsDialog

    texts.set_language(lang)
    dialog = SettingsDialog(None)
    dialog.resize(dialog.sizeHint())
    dialog.show()
    QApplication.processEvents()
    edit = dialog.key_edit
    placeholder = edit.placeholderText()
    assert placeholder == texts.text("settings.key_placeholder")
    need = QFontMetrics(edit.font()).horizontalAdvance(placeholder)
    assert need + 24 <= edit.width(), (need, edit.width())
    # what the short line drops is still one hover away
    assert edit.toolTip() == texts.text("settings.key_tooltip")
    assert "provider.yaml" in edit.toolTip()
