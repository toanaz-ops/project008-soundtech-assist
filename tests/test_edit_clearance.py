"""Every descriptor must clear the finding it claims to repair.

The check is deliberately not "the finding is gone" on its own: a
repair that cleared its own finding while lighting up two others would
pass that. Asserting the total dropped by exactly one catches it, and
the failure message names what was gained and lost so the cause is
visible without a debugger.

This is the test that keeps "a finding's target is nearly the raw JSON
path" from quietly becoming an assumption.
"""

import json

import pytest

from wing_parser.core.loader import parse_raw
from wing_parser.edit import repairs, writer
from wing_parser.edit.journal import EditJournal
from wing_parser.query.scene import WingScene


def findings_of(document, path):
    return WingScene(parse_raw(document, path)).advisory.run()


@pytest.mark.parametrize("rule_id", sorted(repairs.load_repairs()))
def test_each_repair_clears_its_own_finding(vu_path, rule_id, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    document = json.loads(vu_path.read_text(encoding="utf-8"))

    before = findings_of(document, vu_path)
    target = next((f for f in before if f.rule_id == rule_id), None)
    assert target is not None, (
        f"{rule_id} has a descriptor but does not fire on the sample file, "
        "so this test cannot prove the descriptor works. Either remove the "
        "descriptor or add a fixture that makes the rule fire."
    )

    journal = EditJournal()
    journal.append(repairs.patch_for(target, document))
    after = findings_of(writer.applied(document, journal), vu_path)

    ids_before = {(f.rule_id, f.target) for f in before}
    ids_after = {(f.rule_id, f.target) for f in after}

    assert (target.rule_id, target.target) not in ids_after
    assert len(after) == len(before) - 1, (
        f"repairing {rule_id} moved the finding count by "
        f"{len(before) - len(after)}, not 1: "
        f"gained {sorted(ids_after - ids_before)}, "
        f"lost {sorted(ids_before - ids_after)}"
    )


def test_the_unprofiled_real_file_still_yields_22_findings(vu_path, monkeypatch):
    """The contract this whole cycle must not move. No rules were added."""
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    document = json.loads(vu_path.read_text(encoding="utf-8"))
    assert len(findings_of(document, vu_path)) == 22


def test_pb1_would_also_pass_with_a_set_descriptor_on_this_file(vu_path, monkeypatch):
    """Records what the sample file cannot prove, so it is not "simplified".

    Channel 16's source resolves to no SourceData, so its polarity is
    False and PB1 fires with `inv` False. Writing True and flipping
    False both produce True here, so this file cannot distinguish
    `toggle` from `set: true`. The argument for `toggle` rests on
    query/channel.py:63 -- effective polarity is an XOR, so on a
    channel whose source *is* inverted the rule fires with `inv`
    already True and a `set: true` repair would change nothing while
    reporting success. Do not replace the toggle because this suite
    stays green either way.
    """
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    document = json.loads(vu_path.read_text(encoding="utf-8"))
    assert document["ae_data"]["ch"]["16"]["in"]["set"]["inv"] is False
    assert WingScene(parse_raw(document, vu_path)).channel(16).source is None
