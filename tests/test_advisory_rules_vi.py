"""Vietnamese rule text (wave 11): data parity, loading, evaluation."""

import string
from types import SimpleNamespace

import pytest

from wing_parser.advisory import layers
from wing_parser.advisory.evaluator import evaluate
from wing_parser.advisory.loader import load_base_rules, load_rules
from wing_parser.advisory.models import Finding, Rule


def _fields(text: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


def test_every_base_rule_has_vietnamese_text_with_the_same_placeholders():
    rules = load_base_rules()
    assert len(rules) >= 39
    for rule in rules:
        assert rule.title_vi.strip(), rule.id
        assert rule.message_vi.strip(), rule.id
        assert _fields(rule.message_vi) == _fields(rule.message), rule.id


def test_findings_default_to_no_vietnamese():
    assert Finding("X", "base", "info", "t", "m").message_vi == ""
    rule = Rule("X", "t", "info", "s", "r", "none", {}, "m", "base")
    assert (rule.title_vi, rule.message_vi) == ("", "")


def _write(path, body):
    path.write_text(body, encoding="utf-8")
    return path


_RULE = """rules:
  - id: T1
    title: "T"
    severity: info
    source: s
    rationale: r
    when: {for_each: channel, where: {}}
    message: "Channel {channel.number}"
    %s
"""


def test_blank_vietnamese_keys_load_as_empty(tmp_path):
    path = _write(tmp_path / "r.yaml", _RULE % "message_vi:\n    title_vi:")
    (rule,) = load_rules(path, layer="base")
    assert (rule.title_vi, rule.message_vi) == ("", "")


def test_the_toanaz_layer_reads_vietnamese_keys(tmp_path):
    path = _write(
        tmp_path / "p.yaml",
        "principles:\n  - id: P1\n    title: T\n    message: m\n"
        "    title_vi: Tựa\n    message_vi: Tin\n"
        "  - id: P2\n    title: T\n    message_vi:\n",
    )
    p1, p2 = layers._as_rules(path, layer="toanaz", key="principles",
                              owner_source=False)
    assert (p1.title_vi, p1.message_vi) == ("Tựa", "Tin")
    assert p2.message_vi == ""


def _scene_with_unnamed_channel():
    ch = SimpleNamespace(number=3, name="")
    return ch


def test_evaluator_renders_vietnamese_with_the_same_context(monkeypatch):
    from wing_parser.advisory import evaluator

    target = SimpleNamespace(
        name="ch3", context={"channel": {"number": 3}}, confidence=1.0)
    monkeypatch.setattr(evaluator, "targets_for", lambda s, f: [target])
    base = dict(id="T1", title="t", severity="info", source="s",
                rationale="r", for_each="channel", where={}, layer="base")
    with_vi = Rule(message="Ch {channel.number}",
                   message_vi="Kênh {channel.number}", **base)
    without = Rule(message="Ch {channel.number}", **base)
    (f1,) = evaluate(None, with_vi)
    (f2,) = evaluate(None, without)
    assert (f1.message, f1.message_vi) == ("Ch 3", "Kênh 3")
    assert f2.message_vi == ""
