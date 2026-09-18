"""The session: scene, journal, and the re-derivation that keeps them honest.

No Qt is imported here, deliberately -- every decision the application
makes lives in this object, so all of it is testable without a display.
"""

import json

import pytest

from wing_parser.ui.session import Session


@pytest.fixture
def session(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    return Session.open(vu_path)


def a_g8(session):
    return next(f for f in session.findings() if f.rule_id == "G8")


def test_a_fresh_session_reports_the_pinned_finding_count(session):
    assert len(session.findings()) == 22
    assert session.dirty is False
    assert session.changes() == ()


def test_repairing_a_finding_removes_it_and_marks_the_session_dirty(session):
    target = a_g8(session)

    assert session.repair(target) is True
    assert session.dirty is True
    assert len(session.changes()) == 1
    assert len(session.findings()) == 21
    assert not [f for f in session.findings()
                if (f.rule_id, f.target) == (target.rule_id, target.target)]


def test_undo_restores_the_previous_finding_set(session):
    before = [(f.rule_id, f.target) for f in session.findings()]
    session.repair(a_g8(session))

    assert session.undo() is True
    assert [(f.rule_id, f.target) for f in session.findings()] == before
    assert session.dirty is False


def test_undo_on_a_clean_session_is_false_rather_than_an_error(session):
    assert session.undo() is False


def test_a_rule_without_a_descriptor_cannot_be_repaired(session):
    target = next(f for f in session.findings() if f.rule_id == "G10")
    assert session.repair(target) is False
    assert session.dirty is False


def test_a_second_edit_to_one_key_records_what_was_actually_there(session):
    """`before` must come from the patched document, not the original.

    Otherwise a second edit to the same key would claim the original
    value was still in place, and the changes list would read as a lie.
    """
    target = a_g8(session)
    session.repair(target)
    session.undo()
    session.repair(target)
    assert session.changes()[0].before == "POST"


def test_save_as_writes_the_repair_and_leaves_the_original_alone(session, tmp_path):
    original_bytes = session.path.read_bytes()
    session.repair(a_g8(session))

    out = tmp_path / "edited.snap"
    session.save_as(out)

    assert session.path.read_bytes() == original_bytes

    saved = json.loads(out.read_text(encoding="utf-8"))
    patch = session.changes()[0]
    node = saved
    for segment in patch.path.split("."):
        node = node[segment]
    assert node == "PRE"


def test_saving_does_not_clear_the_journal(session, tmp_path):
    # Save As is not "commit". The operator may save two variants from
    # the same set of edits, and losing the changes list on the first
    # save would make the second impossible to review.
    session.repair(a_g8(session))
    session.save_as(tmp_path / "one.snap")
    assert session.dirty is True
    assert len(session.changes()) == 1


def test_rule_returns_the_rule_behind_a_finding(session):
    rule = session.rule("G8")
    assert rule is not None
    assert rule.rationale.strip()
    assert rule.source.strip()


def test_rule_is_none_for_an_id_that_is_not_active(session):
    assert session.rule("NOSUCHRULE") is None


def test_the_session_never_imports_qt():
    import subprocess
    import sys

    code = ("import sys; import wing_parser.ui.session; "
            "print([m for m in sys.modules if 'PySide' in m])")
    result = subprocess.run([sys.executable, "-c", code],
                            capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "[]"


def test_record_value_appends_a_patch_and_re_derives(vu_path):
    """F8's clamp path and W13's revert both move a leaf outside `repair`."""
    from wing_parser.ui.session import Session

    session = Session.open(vu_path)
    path = "ae_data.ch.1.send.8.mode"
    before = session._document()["ae_data"]["ch"]["1"]["send"]["8"]["mode"]

    patch = session.record_value(path, "PRE", label="Console clamped", because="G8")

    assert patch.before == before and patch.after == "PRE"
    assert session.changes()[-1] is patch
    assert session._document()["ae_data"]["ch"]["1"]["send"]["8"]["mode"] == "PRE"
    assert session.dirty


def test_record_value_is_undone_like_any_other_patch(vu_path):
    from wing_parser.ui.session import Session

    session = Session.open(vu_path)
    before = session._document()["ae_data"]["ch"]["1"]["send"]["8"]["mode"]
    session.record_value("ae_data.ch.1.send.8.mode", "PRE", label="x", because="G8")
    assert session.undo()
    assert session._document()["ae_data"]["ch"]["1"]["send"]["8"]["mode"] == before
