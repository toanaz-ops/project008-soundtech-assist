"""The edit journal: an ordered record of edits, held instead of applied."""

import dataclasses

import pytest

from wing_parser.edit.journal import EditJournal, Patch


def a_patch(path="ae_data.ch.1.mute", after=True):
    return Patch(path=path, before=False, after=after,
                 because="G8:ch.1.send.8", label="Mute channel 1")


def test_a_new_journal_is_empty():
    journal = EditJournal()
    assert len(journal) == 0
    assert not journal
    assert journal.patches() == ()


def test_append_then_undo_returns_the_patch_and_empties_the_journal():
    journal = EditJournal()
    patch = a_patch()
    journal.append(patch)

    assert bool(journal) is True
    assert journal.patches() == (patch,)
    assert journal.undo() is patch
    assert journal.patches() == ()


def test_undo_on_an_empty_journal_returns_none_rather_than_raising():
    # The Undo menu item is always present; an empty journal is a
    # normal state, not an error.
    assert EditJournal().undo() is None


def test_patches_come_back_in_the_order_they_were_made():
    journal = EditJournal()
    first, second = a_patch(), a_patch(path="ae_data.ch.2.mute")
    journal.append(first)
    journal.append(second)
    assert journal.patches() == (first, second)


def test_undo_removes_only_the_last_patch():
    journal = EditJournal()
    first, second = a_patch(), a_patch(path="ae_data.ch.2.mute")
    journal.append(first)
    journal.append(second)

    assert journal.undo() is second
    assert journal.patches() == (first,)


def test_patches_returns_a_snapshot_the_caller_cannot_use_to_mutate():
    journal = EditJournal()
    journal.append(a_patch())
    taken = journal.patches()
    journal.append(a_patch(path="ae_data.ch.2.mute"))
    assert len(taken) == 1


def test_a_patch_is_frozen():
    with pytest.raises(dataclasses.FrozenInstanceError):
        a_patch().after = False
