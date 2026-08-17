"""Applying a journal and writing a .snap back out."""

import json
import subprocess
import sys

import pytest

from wing_parser.edit import writer
from wing_parser.edit.journal import EditJournal, Patch


@pytest.mark.parametrize("fixture_name", ["vu_path", "factory_path"])
def test_an_empty_journal_round_trips_both_sample_files(tmp_path, fixture_name, request):
    """The writer must preserve what this project does not understand.

    Both files are used deliberately. `factory-scene.snap` carries
    `ae_globals`, `ce_globals`, `created`, `creator_fw`, `creator_sn`
    and `creator_version`, none of which `example-Vu.snap` has. A
    writer that rebuilt the file from the parsed model rather than
    patching the original document would drop all six -- and would
    pass this test on `example-Vu.snap` alone.
    """
    source = request.getfixturevalue(fixture_name)
    original = json.loads(source.read_text(encoding="utf-8"))

    out = tmp_path / source.name
    writer.write_snap(writer.applied(original, EditJournal()), out)

    assert json.loads(out.read_text(encoding="utf-8")) == original


def test_applied_does_not_touch_the_document_it_was_given(vu_path):
    original = json.loads(vu_path.read_text(encoding="utf-8"))
    journal = EditJournal()
    journal.append(Patch("ae_data.ch.1.mute", False, True, "manual", "Mute ch 1"))

    result = writer.applied(original, journal)

    assert result["ae_data"]["ch"]["1"]["mute"] is True
    assert original["ae_data"]["ch"]["1"]["mute"] is False


def test_patches_apply_in_order(vu_path):
    original = json.loads(vu_path.read_text(encoding="utf-8"))
    journal = EditJournal()
    journal.append(Patch("ae_data.ch.1.mute", False, True, "manual", "on"))
    journal.append(Patch("ae_data.ch.1.mute", True, False, "manual", "off"))

    assert writer.applied(original, journal)["ae_data"]["ch"]["1"]["mute"] is False


def test_write_snap_creates_a_file_the_loader_reads_back(vu_path, tmp_path):
    from wing_parser.query.scene import WingScene

    original = json.loads(vu_path.read_text(encoding="utf-8"))
    journal = EditJournal()
    journal.append(Patch("ae_data.ch.1.send.8.mode", "POST", "PRE", "manual", "PRE"))

    out = tmp_path / "edited.snap"
    writer.write_snap(writer.applied(original, journal), out)

    assert WingScene.load(out).channel(1).send_to(8).mode == "PRE"


def test_the_edit_package_never_imports_qt():
    """The engine and CLI must keep working with no GUI installed.

    Run in a subprocess with a clean module table. Asserting against
    this process's `sys.modules` would pass trivially whenever no other
    test had imported Qt first, which is exactly when the guard is
    least useful.
    """
    code = (
        "import sys; "
        "import wing_parser.edit.writer, wing_parser.edit.journal, "
        "wing_parser.edit.pointer, wing_parser.edit.repairs; "
        "print([m for m in sys.modules if 'PySide' in m or 'shiboken' in m])"
    )
    result = subprocess.run([sys.executable, "-c", code],
                            capture_output=True, text=True, check=True)
    assert result.stdout.strip() == "[]"
