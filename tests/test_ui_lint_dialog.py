"""Spec §6: lint reads exactly what `wing showcontext lint` reads; each
anomaly is marked auto-fixable or manual-only, Fix is enabled only when
at least one is fixable, and Fix writes a .bak before apply_repairs
(W2), then re-lints."""
from __future__ import annotations

import stat

import pytest

pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture
def dialog(qt_app):
    from wing_parser.ui.lint_dialog import LintDialog

    return LintDialog()


def _fixable_yaml() -> str:
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


def _unfixable_yaml() -> str:
    """A segment `time:` loader.py cannot parse -- an anomaly, but one
    `apply_repairs` never touches (rewrite.py only re-resolves `expects`
    and cue `action`)."""
    return (
        "show: t\n"
        "segments:\n"
        "  - id: S1\n"
        "    title: A\n"
        "    time: bogus\n"
        "    expects: []\n"
    )


def _mixed_yaml() -> str:
    """One fixable (`expects`) anomaly and one unfixable (`time:`) one on
    the same segment."""
    return (
        "show: t\n"
        "segments:\n"
        "  - id: S1\n"
        "    title: A\n"
        "    time: bogus\n"
        "    expects: [instrument.gutiar]\n"
    )


def test_a_clean_file_says_nothing_to_repair(dialog, tmp_path):
    path = tmp_path / "clean.yaml"
    path.write_text("show: t\nsegments:\n  - id: S1\n    title: A\n    expects: []\n",
                    encoding="utf-8")
    dialog.open_path(str(path))
    assert "nothing to repair" in dialog.output.toPlainText()
    assert not dialog.fix_button.isEnabled()


def test_a_file_with_anomalies_lists_them_marked_and_enables_fix(dialog, tmp_path):
    path = tmp_path / "messy.yaml"
    path.write_text(_fixable_yaml(), encoding="utf-8")
    dialog.open_path(str(path))
    output = dialog.output.toPlainText()
    assert "[auto-fixable]" in output
    assert "'instrument.gutiar' read as 'instrument.guitar'" in output
    assert "'colse' read as 'close'" in output
    assert dialog.fix_button.isEnabled()


def test_only_unfixable_anomalies_leave_fix_disabled_and_each_line_marked(dialog, tmp_path):
    path = tmp_path / "unfixable.yaml"
    path.write_text(_unfixable_yaml(), encoding="utf-8")
    dialog.open_path(str(path))
    output = dialog.output.toPlainText()
    assert "[manual only]" in output
    assert "'bogus'" in output
    assert "[auto-fixable]" not in output
    assert not dialog.fix_button.isEnabled()


def test_a_mixed_file_marks_each_line_and_fix_only_clears_the_fixable_one(
        dialog, tmp_path, monkeypatch):
    """The bug this fix round closes: an unfixable anomaly used to leave
    Fix enabled forever -- clicking it wrote a .bak, ran apply_repairs
    (which touched nothing), reported "fixed 0", and re-lit the
    identical anomaly list. After this fix, Fix clears the fixable
    anomaly and then correctly disables itself, because only the
    unfixable one is left."""
    from PySide6.QtWidgets import QMessageBox

    path = tmp_path / "mixed.yaml"
    path.write_text(_mixed_yaml(), encoding="utf-8")
    dialog.open_path(str(path))
    output = dialog.output.toPlainText()
    assert "[auto-fixable]" in output and "[manual only]" in output
    assert dialog.fix_button.isEnabled()

    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    dialog.fix_button.click()

    after = dialog.output.toPlainText()
    assert "[auto-fixable]" not in after
    assert "[manual only]" in after and "'bogus'" in after
    assert not dialog.fix_button.isEnabled()   # the loop really ends


def test_a_malformed_file_shows_the_message_not_a_crash(dialog, tmp_path):
    path = tmp_path / "broken.yaml"
    path.write_text("not: [valid, show, context", encoding="utf-8")
    dialog.open_path(str(path))    # must not raise
    assert dialog.output.toPlainText() != ""
    assert not dialog.fix_button.isEnabled()


def test_fix_writes_a_bak_then_re_lints(dialog, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    path = tmp_path / "messy.yaml"
    original = _fixable_yaml()
    path.write_text(original, encoding="utf-8")
    dialog.open_path(str(path))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))

    dialog.fix_button.click()

    backup = tmp_path / "messy.yaml.bak"
    assert backup.exists()
    assert backup.read_text(encoding="utf-8") == original
    assert "fixed" in dialog.output.toPlainText().lower()
    assert not dialog.fix_button.isEnabled()   # re-lint found nothing left to fix


def test_an_older_bak_is_overwritten_not_appended_to(dialog, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    path = tmp_path / "messy.yaml"
    path.write_text(_fixable_yaml(), encoding="utf-8")
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
    path.write_text(_fixable_yaml(), encoding="utf-8")
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


def test_a_read_only_source_reports_the_apply_repairs_failure_and_keeps_the_bak(
        dialog, tmp_path, monkeypatch):
    """Fix round 1, item 2: the .bak write (a copy) succeeds against a
    read-only source, but apply_repairs's own `open(path, "w")` then
    raises PermissionError -- caught and reported, never left to escape
    this Qt slot (silent in the console=False release exe), and the
    .bak this dialog already wrote stays on disk."""
    from PySide6.QtWidgets import QMessageBox

    path = tmp_path / "messy.yaml"
    path.write_text(_fixable_yaml(), encoding="utf-8")
    dialog.open_path(str(path))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))

    path.chmod(stat.S_IREAD)
    try:
        dialog.fix_button.click()
        assert (tmp_path / "messy.yaml.bak").exists()
        assert "Could not write repairs" in dialog.output.toPlainText()
    finally:
        path.chmod(stat.S_IWRITE | stat.S_IREAD)


def test_an_unreadable_file_reports_the_failure_not_a_crash(dialog, tmp_path, monkeypatch):
    """Fix round 2, minor 2: load_show_context's own read_text can raise
    OSError (a locked/permission-denied file), not only the ValueError
    it raises itself for a missing file or bad YAML -- _lint must catch
    that too instead of letting it escape the Qt slot."""
    from wing_parser.ui import lint_dialog

    path = tmp_path / "locked.yaml"
    path.write_text(_fixable_yaml(), encoding="utf-8")

    def _boom(_path):
        raise PermissionError("Permission denied")

    monkeypatch.setattr(lint_dialog, "load_show_context", _boom)
    dialog.open_path(str(path))    # must not raise
    assert "Could not read" in dialog.output.toPlainText()
    assert "Permission denied" in dialog.output.toPlainText()
    assert not dialog.fix_button.isEnabled()
