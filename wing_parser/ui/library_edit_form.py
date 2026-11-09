"""The entry editor's tabs: every schema field, no validation, no saving.

`to_entry()` rebuilds the entry dict from the widgets, starting from the
copy it was loaded with so keys this form does not know survive an edit.
"""

from __future__ import annotations

import yaml
from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox, QFormLayout, QLineEdit, QPlainTextEdit, QTabWidget, QTextBrowser,
    QWidget,
)

from wing_parser.library import schema
from wing_parser.ui.library_edit_tables import DictTable
from wing_parser.ui.library_support import today, topic_label
from wing_parser.ui.texts import text

SOURCE_COLUMNS = ("title", "publisher", "kind", "url", "author", "year", "accessed",
                  "locator", "doi", "isbn")
MEDIA_COLUMNS = ("kind", "path", "url", "title", "channel", "timestamp", "caption",
                 "license", "attribution", "generated_by")


def _combo(values) -> QComboBox:
    box = QComboBox()
    box.addItems(list(values))
    return box


class EntryForm(QTabWidget):
    changed = Signal()

    def __init__(self, topics: dict, editing: bool) -> None:
        super().__init__()
        self.base: dict = {}
        self.rule_error = ""
        self.id_edit, self.title_edit, self.title_vi_edit = QLineEdit(), QLineEdit(), QLineEdit()
        self.id_edit.setEnabled(not editing)
        self.topic_box = QComboBox()
        for topic_id in topics:
            self.topic_box.addItem(topic_label(topics, topic_id), topic_id)
        self.confidence_box, self.status_box = _combo(schema.CONFIDENCE), _combo(schema.STATUS)
        self.tag_edits = {key: QLineEdit() for key in schema.TAG_KEYS}
        self.summary_edit, self.rule_edit = QPlainTextEdit(), QPlainTextEdit()
        self.summary_edit.setFixedHeight(76)
        self.body_edit = QPlainTextEdit()
        self.preview = QTextBrowser()
        self.sources = DictTable(SOURCE_COLUMNS, {"kind": schema.SOURCE_KINDS},
                                 {"kind": "article", "accessed": today()})
        self.media = DictTable(MEDIA_COLUMNS, {"kind": schema.MEDIA_KINDS}, {"kind": "video"})

        details = QWidget()
        form = QFormLayout(details)
        for key, widget in (("id", self.id_edit), ("title", self.title_edit),
                            ("title_vi", self.title_vi_edit), ("topic", self.topic_box),
                            ("confidence", self.confidence_box), ("status", self.status_box)):
            form.addRow(text(f"library.field.{key}"), widget)
        for key, edit in self.tag_edits.items():
            edit.setPlaceholderText(text("library.tags_hint"))
            form.addRow(text(f"library.field.tag.{key}"), edit)
        form.addRow(text("library.field.summary"), self.summary_edit)
        form.addRow(text("library.field.rule"), self.rule_edit)
        self.addTab(details, text("library.tab.details"))
        self.addTab(self.body_edit, text("library.tab.body"))
        self.addTab(self.preview, text("library.tab.preview"))
        self.addTab(self.sources, text("library.tab.sources"))
        self.addTab(self.media, text("library.tab.media"))
        self.currentChanged.connect(lambda _i: self.preview.setMarkdown(self.body_edit.toPlainText()))
        for line in (self.id_edit, self.title_edit, self.title_vi_edit, *self.tag_edits.values()):
            line.textChanged.connect(self.changed)
        for box in (self.topic_box, self.confidence_box, self.status_box):
            box.currentIndexChanged.connect(self.changed)
        for edit in (self.summary_edit, self.rule_edit, self.body_edit):
            edit.textChanged.connect(self.changed)
        self.sources.changed.connect(self.changed)
        self.media.changed.connect(self.changed)

    def load(self, entry: dict) -> None:
        self.base = dict(entry)
        self.id_edit.setText(str(entry.get("id", "")))
        self.title_edit.setText(str(entry.get("title", "")))
        self.title_vi_edit.setText(str(entry.get("title_vi", "") or ""))
        index = self.topic_box.findData(entry.get("topic"))
        if index < 0 and entry.get("topic"):
            self.topic_box.addItem(str(entry["topic"]), entry["topic"])
            index = self.topic_box.count() - 1
        self.topic_box.setCurrentIndex(max(index, 0))
        self.confidence_box.setCurrentText(str(entry.get("confidence", schema.CONFIDENCE[1])))
        self.status_box.setCurrentText(str(entry.get("status", "draft")))
        tags = entry.get("tags") or {}
        for key, edit in self.tag_edits.items():
            edit.setText(", ".join(str(v) for v in tags.get(key) or []))
        self.summary_edit.setPlainText(str(entry.get("summary", "")))
        rule = entry.get("rule")
        self.rule_edit.setPlainText(
            yaml.safe_dump(rule, sort_keys=False, allow_unicode=True) if rule else "")
        self.body_edit.setPlainText(str(entry.get("body", "")))
        self.sources.set_rows(list(entry.get("sources") or []))
        self.media.set_rows(list(entry.get("media") or []))

    def _tags(self) -> dict:
        out = {}
        had = self.base.get("tags") or {}
        for key, edit in self.tag_edits.items():
            values = [part.strip() for part in edit.text().split(",") if part.strip()]
            if values or key in had:
                out[key] = values
        return out

    def _rule(self) -> dict | None:
        self.rule_error = ""
        raw = self.rule_edit.toPlainText().strip()
        if not raw:
            return None
        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            self.rule_error = str(exc).splitlines()[0]
            return None
        if not isinstance(data, dict):
            self.rule_error = "not a mapping"
            return None
        return data

    def to_entry(self) -> dict:
        entry = dict(self.base)
        entry.update(
            id=self.id_edit.text().strip(), title=self.title_edit.text().strip(),
            topic=self.topic_box.currentData() or "", tags=self._tags(),
            summary=self.summary_edit.toPlainText().strip(), body=self.body_edit.toPlainText(),
            confidence=self.confidence_box.currentText(), status=self.status_box.currentText(),
            sources=self.sources.rows())
        for key, value in (("title_vi", self.title_vi_edit.text().strip()),
                           ("rule", self._rule()), ("media", self.media.rows())):
            if value:
                entry[key] = value
            else:
                entry.pop(key, None)
        return entry
