"""Doctor findings follow the UI language (wave 11, V3)."""

import pytest

pytest.importorskip("PySide6.QtWidgets")

from PySide6.QtCore import Qt

from wing_parser.advisory.models import Finding, Rule
from wing_parser.ui import texts
from wing_parser.ui.detail_panel import DetailPanel
from wing_parser.ui.findings_model import COLUMNS, FindingsModel

_BASE = dict(severity="info", source="s", rationale="r", for_each="none",
             where={}, layer="base")
_RULES = {
    "A": Rule(id="A", title="Eng A", message="eng a",
              title_vi="Tựa A", message_vi="tin a", **_BASE),
    "B": Rule(id="B", title="Eng B", message="eng b", **_BASE),
}


class _Session:
    def rule(self, rule_id):
        return _RULES.get(rule_id)


def _finding(rule_id):
    r = _RULES[rule_id]
    return Finding(rule_id, "base", "info", "t", r.message,
                   message_vi=r.message_vi)


def _cell(model, row):
    return model.index(row, COLUMNS.index("message")).data(
        Qt.ItemDataRole.DisplayRole)


def _model():
    model = FindingsModel()
    model.set_findings([_finding("A"), _finding("B")])
    return model


def test_the_table_shows_vietnamese_when_available(qt_app):
    texts.set_language("vi")
    model = _model()
    assert [_cell(model, 0), _cell(model, 1)] == ["tin a", "eng b"]


def test_the_table_stays_english_in_english(qt_app):
    texts.set_language("en")
    model = _model()
    assert [_cell(model, 0), _cell(model, 1)] == ["eng a", "eng b"]


def test_the_detail_panel_follows_the_language(qt_app):
    panel = DetailPanel()
    session = _Session()
    texts.set_language("vi")
    panel.show_finding(_finding("A"), session)
    assert panel.message_label.text() == "tin a"
    assert "Tựa A" in panel.title_label.text()
    panel.show_finding(_finding("B"), session)
    assert panel.message_label.text() == "eng b"
    assert "Eng B" in panel.title_label.text()
    texts.set_language("en")
    panel.show_finding(_finding("A"), session)
    assert panel.message_label.text() == "eng a"
    assert "Eng A" in panel.title_label.text()
