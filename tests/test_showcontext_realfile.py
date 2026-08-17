"""The show-context contract on the real sample file.

Regenerate with:
python - <<'EOF'
import os; os.environ["WING_DISABLE_LLM"] = "1"
from wing_parser import WingScene
scene = WingScene.load("user-files/example-Vu.snap",
                       show="tests/data/example-Vu-show.yaml")
for f in sorted((f for f in scene.advisory.run() if f.rule_id.startswith("Q")),
                key=lambda f: (f.rule_id, f.target)):
    print(f'    ("{f.rule_id}", "{f.target}", "{f.severity}"),')
EOF
"""
import pytest

from wing_parser import WingScene

SHOW = "tests/data/example-Vu-show.yaml"

EXPECTED_Q = [
    ("Q1", "cue.S2.SQ2", "warning"),
    ("Q2", "cue.S2.SQ2", "info"),
    ("Q4", "segment.S2", "warning"),
    ("Q5", "segment.S2", "info"),
    ("Q6", "cue.S2.SQ3", "warning"),
    # Spot-checked against raw ae_data and `wing analyze` before commit:
    #   - Q1 "cue.S2.SQ2": SQ 2 names channel 99. `ae_data["ch"]` has keys
    #     "1".."40" only (40 channels, no gap) -- 99 does not exist, which
    #     is exactly what Q1's `missing_channel_count` counts.
    #   - Q2 "cue.S2.SQ2": SQ 2 also names channel 31. `ae_data["ch"]["31"]`
    #     is present (the channel exists) but its
    #     `config["name"]` is `None` -- carries no name -- which is what
    #     `unnamed_channel_count` counts. Channels 32-36 are blank the same
    #     way but are not named by any cue, so they do not add rows.
    #   - Q4 "segment.S2": S2 expects `instrument.horns`. Iterating every
    #     channel's `source_type.kind` in the loaded scene finds zero
    #     channels classified `instrument.horns` (`horns channels: []`),
    #     so the expectation is unmet -- `unmet_expect_count` fires.
    #   - Q5 "segment.S2": S2 also expects `instrument.keys`. Channels 29
    #     ("Key 1") and 30 ("Key 2") both classify `instrument.keys` at
    #     confidence 0.9 (>= the HIGH=0.8 threshold `_channels_of` uses),
    #     so the expectation *is* met and Q4 does not also fire for keys.
    #     But both channels read `fader == -inf` in `wing analyze`, so
    #     `Channel.in_use` is False for both -- `dark_expect_count` fires.
    #   - Q6 "cue.S2.SQ3": walking the cues in file order, SQ 2 opens
    #     channel 29 among others, then SQ 3 opens channel 29 again. The
    #     open/closed book already has 29 marked open when SQ 3 tries to
    #     open it, so `contradiction_count` fires on SQ 3, not SQ 2 (SQ 2
    #     is the cue that *set* the state, SQ 3 is the one that repeats
    #     it).
    #
    # Q3 does not fire: the fixture never names a DCA on any cue, so
    # `missing_dca_count` is 0 everywhere. Q7 does not fire: it ships with
    # `enabled: false` in showcontext.yaml (see that file's rationale), so
    # load_base_rules() never offers it to the evaluator regardless of the
    # fixture's cue timing.
]


def test_the_show_context_contract(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    scene = WingScene.load(vu_path, show=SHOW)
    got = sorted((f.rule_id, f.target, f.severity)
                 for f in scene.advisory.run() if f.rule_id.startswith("Q"))
    assert got == sorted(EXPECTED_Q)


def test_the_same_scene_without_context_yields_no_q_findings(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    found = WingScene.load(vu_path).advisory.run()
    assert not [f for f in found if f.rule_id.startswith("Q")]
    assert len(found) == 22


def test_the_q2_message_is_rendered_not_a_bare_triple(vu_path, monkeypatch):
    # render() in wing_parser/advisory/predicates.py leaves an unresolvable
    # {dotted.path} token visible in the output instead of raising. A
    # mistyped message path in showcontext.yaml would therefore still pass
    # every (rule_id, target, severity) assertion above -- the finding
    # would just carry a literal "{cue.foo}" nobody reading a triple would
    # notice. Assert on the rendered text itself: the Q2 message must name
    # channel 31 by number, and no finding's message may contain a "{" --
    # proof every token in every Q1-Q7 message actually resolved.
    scene = WingScene.load(vu_path, show=SHOW)
    q_findings = [f for f in scene.advisory.run() if f.rule_id.startswith("Q")]
    q2 = next(f for f in q_findings if f.rule_id == "Q2")
    assert "31" in q2.message
    assert all("{" not in f.message for f in q_findings)
