"""Spec §6: lint reads exactly what `wing showcontext lint` reads; Fix
writes a .bak before apply_repairs (W2), then re-lints."""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")

CLEAN = "tests/data/ingest-fixture.xlsx"   # any real file stands in below; see fixtures written per test


@pytest.fixture
def dialog(qt_app):
    from wing_parser.ui.lint_dialog import LintDialog

    return LintDialog()


def _show_context_yaml() -> str:
    """Two genuinely repairable typos -- edit-distance-1 from a real kind
    and a real action (design spec's radius-1 rule, showcontext/vocabulary.py):
    'gutiar' is a transposition of 'guitar', 'colse' of 'close'. A pure
    case difference like 'Speech.MC' would NOT anomaly here -- normalise()
    lowercases it silently (vocabulary.py:31-42) with repaired=False, so
    it must not be used as this fixture's "auto-fixable" example. Verified
    2026-09-26 against the real loader/rewrite pipeline: both repair, and
    a second lint after apply_repairs shows zero anomalies."""
    return (
        "show: t\n"
        "segments:\n"
        "  - id: S1\n"
        "    title: A\n"
        "    expects: [instrument.gutiar]\n"
        "    cues:\n"
        "      - {id: c1, action: colse}\n"
    )


def test_a_clean_file_says_nothing_to_repair(dialog, tmp_path):
    path = tmp_path / "clean.yaml"
    path.write_text("show: t\nsegments:\n  - id: S1\n    title: A\n    expects: []\n",
                    encoding="utf-8")
    dialog.open_path(str(path))
    assert "nothing to repair" in dialog.output.toPlainText()
    assert not dialog.fix_button.isEnabled()


def test_a_file_with_anomalies_lists_them_and_enables_fix(dialog, tmp_path):
    path = tmp_path / "messy.yaml"
    path.write_text(_show_context_yaml(), encoding="utf-8")
    dialog.open_path(str(path))
    assert dialog.output.toPlainText() != ""
    assert dialog.fix_button.isEnabled()


def test_a_malformed_file_shows_the_message_not_a_crash(dialog, tmp_path):
    path = tmp_path / "broken.yaml"
    path.write_text("not: [valid, show, context", encoding="utf-8")
    dialog.open_path(str(path))    # must not raise
    assert dialog.output.toPlainText() != ""
    assert not dialog.fix_button.isEnabled()


def test_fix_writes_a_bak_then_re_lints(dialog, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    path = tmp_path / "messy.yaml"
    original = _show_context_yaml()
    path.write_text(original, encoding="utf-8")
    dialog.open_path(str(path))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))

    dialog.fix_button.click()

    backup = tmp_path / "messy.yaml.bak"
    assert backup.exists()
    assert backup.read_text(encoding="utf-8") == original
    assert "fixed" in dialog.output.toPlainText().lower() or "Speech.MC" in dialog.output.toPlainText()
    assert not dialog.fix_button.isEnabled()   # re-lint found nothing left to fix


def test_an_older_bak_is_overwritten_not_appended_to(dialog, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    path = tmp_path / "messy.yaml"
    path.write_text(_show_context_yaml(), encoding="utf-8")
    (tmp_path / "messy.yaml.bak").write_text("stale backup", encoding="utf-8")
    dialog.open_path(str(path))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    dialog.fix_button.click()
    assert "stale backup" not in (tmp_path / "messy.yaml.bak").read_text(encoding="utf-8")


def test_a_failed_backup_write_stops_before_apply_repairs(dialog, tmp_path, monkeypatch):
    """Controller requirement: a .bak write failure (OSError) must report
    and stop -- apply_repairs must never run against an un-backed-up file."""
    from PySide6.QtWidgets import QMessageBox

    from wing_parser.ui import lint_dialog

    path = tmp_path / "messy.yaml"
    path.write_text(_show_context_yaml(), encoding="utf-8")
    dialog.open_path(str(path))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))

    called = []
    monkeypatch.setattr(lint_dialog, "apply_repairs", lambda p: called.append(p) or ())

    def _boom(*_a, **_k):
        raise OSError("disk full")

    monkeypatch.setattr(lint_dialog.shutil, "copyfile", _boom)

    dialog.fix_button.click()

    assert called == []
    assert "disk full" in dialog.output.toPlainText()
