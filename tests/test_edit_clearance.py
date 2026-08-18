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

# --------------------------------------------------------------------
# Conditions that make a rule fire on a document derived from the real
# file. A descriptor may only ship if this test can exercise it, and
# nine of the eleven rules carrying a repair are silent on the untouched
# scene -- correctly, because ToanAZ's file does not contain those
# mistakes. Each mutation below is taken from the fixture the rule's own
# test already uses, in tests/test_advisory_rules_routing.py and
# tests/test_advisory_rules_presets.py, so the two suites cannot drift
# on what "this rule fires" means.
#
# Channel 20 is the standard donor: named, parked, and carrying no
# finding of its own on the untouched file.
# --------------------------------------------------------------------


def _silence_all_routing(ae, channel="20"):
    for send in ae["ch"][channel]["send"].values():
        send["on"] = False
    for main in ae["ch"][channel]["main"].values():
        main["on"] = False


def _click_into_the_foh_main(ae):
    ae["ch"]["20"]["name"] = "CLICK"
    _silence_all_routing(ae)
    ae["ch"]["20"]["main"]["1"]["on"] = True          # main 1 = MAIN FOH


def _talkback_into_the_foh_main(ae):
    ae["ch"]["20"]["name"] = "TB"
    _silence_all_routing(ae)
    ae["ch"]["20"]["main"]["1"]["on"] = True


def _timecode_into_a_bus(ae):
    ae["ch"]["20"]["name"] = "LTC"
    _silence_all_routing(ae)
    ae["ch"]["20"]["send"]["9"]["on"] = True


def _timecode_into_a_main(ae):
    ae["ch"]["20"]["name"] = "LTC"
    _silence_all_routing(ae)
    ae["ch"]["20"]["main"]["2"]["on"] = True


def _post_fader_send_to_a_record_bus(ae):
    ae["bus"]["12"]["name"] = "RECORD"
    ae["ch"]["1"]["send"]["12"]["on"] = True
    ae["ch"]["1"]["send"]["12"]["mode"] = "POST"


def _post_fader_main_send_to_a_record_main(ae):
    # main 3 is RECODING on the real file -- a typo that stays
    # unclassified by design. ch.1 already has main 3 on with pre False.
    ae["main"]["3"]["name"] = "RECORD"


def _caller_into_its_own_mix_minus(ae):
    ae["ch"]["20"]["name"] = "ZOOM"
    ae["bus"]["12"]["name"] = "MIX MINUS"
    ae["ch"]["20"]["send"]["12"]["on"] = True


def _speech_channel_with_the_hpf_off(ae):
    ae["ch"]["20"]["name"] = "LECTERN"
    ae["ch"]["20"]["flt"]["lc"] = False


def _an_unmuted_qa_mic(ae):
    ae["ch"]["20"]["name"] = "Q&A 1"
    ae["ch"]["20"]["mute"] = False


INDUCERS = {
    "R1": _click_into_the_foh_main,
    "R2": _talkback_into_the_foh_main,
    "R3": _timecode_into_a_bus,
    "R3M": _timecode_into_a_main,
    "R4": _post_fader_send_to_a_record_bus,
    "R5": _post_fader_main_send_to_a_record_main,
    "R6": _caller_into_its_own_mix_minus,
    "S1": _speech_channel_with_the_hpf_off,
    "PC8": _an_unmuted_qa_mic,
}


def findings_of(document, path):
    return WingScene(parse_raw(document, path)).advisory.run()


def _document_where_the_rule_fires(vu_path, rule_id):
    """The real file, mutated only if the rule needs it to fire."""
    document = json.loads(vu_path.read_text(encoding="utf-8"))
    if any(f.rule_id == rule_id for f in findings_of(document, vu_path)):
        return document

    inducer = INDUCERS.get(rule_id)
    assert inducer is not None, (
        f"{rule_id} has a repair descriptor but does not fire on the sample "
        "file and has no entry in INDUCERS, so nothing here can prove the "
        "descriptor works. Add an inducer or remove the descriptor."
    )
    inducer(document["ae_data"])
    assert any(f.rule_id == rule_id for f in findings_of(document, vu_path)), (
        f"the inducer for {rule_id} did not make it fire; the fixture is "
        "stale, so the descriptor below it is unproven"
    )
    return document


@pytest.mark.parametrize("rule_id", sorted(repairs.load_repairs()))
def test_each_repair_clears_its_own_finding(vu_path, rule_id, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    document = _document_where_the_rule_fires(vu_path, rule_id)

    before = findings_of(document, vu_path)
    target = next(f for f in before if f.rule_id == rule_id)

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


def test_every_inducer_belongs_to_a_shipped_descriptor():
    """A stale inducer is dead weight that reads as coverage."""
    assert set(INDUCERS) <= set(repairs.load_repairs())


def test_a_matrix_send_target_repairs_the_matrix_send(vu_path, monkeypatch):
    """The MX branch, which no rule exercises on the untouched file.

    `_channel_sends` in the evaluator names a matrix send target
    `ch.N.send.MX5`, keeping the raw file's own prefix -- and the raw
    document really does hold `ae_data.ch.N.send.MX5` beside
    `ae_data.ch.N.send.5`, two different destinations. So the declared
    path template resolves correctly for both by construction, and
    nothing tested that until here: ToanAZ's IEM matrix sends are all
    already PRE, which is correct practice and why G8 stays silent on
    them.

    Without this test a template that assumed a bare number would look
    perfect on the sample file and would write to the wrong destination
    the first time an IEM send was left post-fader.
    """
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    document = json.loads(vu_path.read_text(encoding="utf-8"))
    # Matrix 5 is "IEM MC", classified monitor.iem at 0.95, so a POST
    # send into it is exactly what G8 exists to catch.
    document["ae_data"]["ch"]["4"]["send"]["MX5"]["mode"] = "POST"

    target = next(f for f in findings_of(document, vu_path)
                  if f.rule_id == "G8" and f.target == "ch.4.send.MX5")

    patch = repairs.patch_for(target, document)
    assert patch.path == "ae_data.ch.4.send.MX5.mode"
    assert patch.before == "POST"

    journal = EditJournal()
    journal.append(patch)
    patched = writer.applied(document, journal)

    assert patched["ae_data"]["ch"]["4"]["send"]["MX5"]["mode"] == "PRE"
    # Bus 5 is a different destination and must not have been touched.
    assert (patched["ae_data"]["ch"]["4"]["send"]["5"]
            == document["ae_data"]["ch"]["4"]["send"]["5"])
    assert not [f for f in findings_of(patched, vu_path)
                if f.target == "ch.4.send.MX5"]


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
    query/channel.py:63 -- effective polarity is an XOR, so on a channel
    whose source *is* inverted the rule fires with `inv` already True
    and a `set: true` repair would change nothing while reporting
    success. Do not replace the toggle because this suite stays green
    either way.
    """
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    document = json.loads(vu_path.read_text(encoding="utf-8"))
    assert document["ae_data"]["ch"]["16"]["in"]["set"]["inv"] is False
    assert WingScene(parse_raw(document, vu_path)).channel(16).source is None
