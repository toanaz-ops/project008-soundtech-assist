"""Draft-rule dry-run: pure half (wave 8)."""

from __future__ import annotations

from pathlib import Path

import pytest

from wing_parser import WingScene
from wing_parser.advisory import draft_dry_run as dd
from wing_parser.advisory.resolver import active_rules, run

GOOD = "ToanAZ, voice note, 2026-11-09"
GATE_RULE = """
principles:
  - id: draft.gate_on
    severity: info
    source: "{source}"
    when:
      for_each: channel
      where:
        channel.gate.on: true
    message: "Gate on channel {{channel.number}}"
"""


@pytest.fixture(scope="module")
def vu(vu_path):
    return WingScene.load(vu_path)


def _draft(tmp_path: Path, body: str, name: str = "d.yaml") -> Path:
    folder = tmp_path / "drafts"
    folder.mkdir(exist_ok=True)
    path = folder / name
    path.write_text(body, encoding="utf-8")
    return path


def _gate(source: str = GOOD) -> str:
    return GATE_RULE.format(source=source)


def test_draft_adds_findings(tmp_path, vu):
    load = dd.load_draft(_draft(tmp_path, _gate()), tmp_path)
    assert load.error is None and load.promotable
    delta = dd.dry_run(vu, load.rules, tmp_path)
    assert delta.added and not delta.removed
    assert {f.rule_id for f in delta.added} == {"draft.gate_on"}
    assert delta.after == delta.before + len(delta.added)


def test_draft_supersedes_base_rule(tmp_path, vu):
    body = f"""
principles:
  - id: draft.off_g8
    source: "{GOOD}"
    supersedes: [G8]
"""
    load = dd.load_draft(_draft(tmp_path, body), tmp_path)
    assert load.error is None
    delta = dd.dry_run(vu, load.rules, tmp_path)
    assert not delta.added
    assert delta.removed and {f.rule_id for f in delta.removed} == {"G8"}
    assert delta.suppressed == {"G8": "draft.off_g8"}
    assert delta.after == delta.before - len(delta.removed)


def test_flexible_non_matching_applies_when_changes_nothing(tmp_path, vu):
    body = _gate() + "    hardness: flexible\n    applies_when:\n        channel_count: 99999\n"
    load = dd.load_draft(_draft(tmp_path, body), tmp_path)
    assert load.error is None
    delta = dd.dry_run(vu, load.rules, tmp_path)
    assert delta.added == () and delta.removed == ()
    assert delta.before == delta.after


def test_source_without_date_runs_but_not_promotable(tmp_path, vu):
    load = dd.load_draft(_draft(tmp_path, _gate("ToanAZ voice note")), tmp_path)
    assert load.error is None
    assert not load.promotable
    assert load.promote_blockers and "draft.gate_on" in load.promote_blockers[0]
    assert dd.dry_run(vu, load.rules, tmp_path).added


def test_id_collides_with_base_id(tmp_path):
    body = _gate().replace("draft.gate_on", "G8")
    load = dd.load_draft(_draft(tmp_path, body), tmp_path)
    assert load.error and "G8" in load.error and not load.rules
    assert not load.promotable


def test_id_collides_with_principles_id(tmp_path):
    (tmp_path / "principles.yaml").write_text(_gate(), encoding="utf-8")
    load = dd.load_draft(_draft(tmp_path, _gate()), tmp_path)
    assert load.error and "principles.yaml" in load.error


def test_duplicate_ids_inside_draft(tmp_path):
    body = _gate() + _gate().replace("principles:\n", "")
    load = dd.load_draft(_draft(tmp_path, body), tmp_path)
    assert load.error and "more than once" in load.error


def test_supersedes_unknown_id(tmp_path):
    body = _gate() + "    supersedes: [NOPE99]\n"
    load = dd.load_draft(_draft(tmp_path, body), tmp_path)
    assert load.error and "NOPE99" in load.error


def test_supersedes_principle_id(tmp_path):
    (tmp_path / "principles.yaml").write_text(
        _gate().replace("draft.gate_on", "p.real"), encoding="utf-8")
    body = f'principles:\n  - id: draft.x\n    source: "{GOOD}"\n    supersedes: [p.real]\n'
    load = dd.load_draft(_draft(tmp_path, body), tmp_path)
    assert load.error and "p.real" in load.error


def test_broken_yaml_is_an_error(tmp_path):
    load = dd.load_draft(_draft(tmp_path, "principles: [unclosed\n  - : :"), tmp_path)
    assert load.error and not load.rules and not load.promotable


def test_empty_draft_is_an_error(tmp_path):
    load = dd.load_draft(_draft(tmp_path, "principles: []\n"), tmp_path)
    assert load.error


def test_active_rules_without_extra_rules_is_unchanged(vu):
    assert ([r.id for r in active_rules(vu)]
            == [r.id for r in active_rules(vu, extra_rules=())])
    assert run(vu) == __import__("wing_parser.advisory.evaluator",
                                 fromlist=["x"]).evaluate_all(
        vu, active_rules(vu, extra_rules=()))


def test_list_drafts_filters_and_sorts(tmp_path):
    assert dd.list_drafts(tmp_path) == []  # missing dir
    _draft(tmp_path, "x", "b.yml")
    _draft(tmp_path, "x", "a.yaml")
    _draft(tmp_path, "x", "notes.txt")
    assert [p.name for p in dd.list_drafts(tmp_path)] == ["a.yaml", "b.yml"]


def test_resolver_never_reads_drafts(tmp_path, vu):
    baseline = run(vu, tmp_path)
    _draft(tmp_path, _gate())
    assert run(vu, tmp_path) == baseline
    assert "draft.gate_on" not in {r.id for r in active_rules(vu, tmp_path)}


def test_dry_run_files_real_scene_and_missing_file(tmp_path, vu_path):
    load = dd.load_draft(_draft(tmp_path, _gate()), tmp_path)
    missing = tmp_path / "nope.snap"
    results = dd.dry_run_files([vu_path, missing], load.rules, tmp_path)
    assert results[0].error is None and results[0].delta.added
    assert results[1].delta is None and results[1].error
    assert results[1].path == missing
