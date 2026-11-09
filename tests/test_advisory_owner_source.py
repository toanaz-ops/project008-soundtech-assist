"""toanaz and show layers claim to be the owner's own judgement, so their
rules must carry a `source:` starting with "ToanAZ" and an ISO date.
Base rules are not affected."""

from __future__ import annotations

from pathlib import Path

import pytest

from wing_parser.advisory import layers
from wing_parser.advisory.loader import load_rules

GOOD = "ToanAZ, field practice, 2026-08-16"


def _principles_dir(tmp_path: Path, source_line: str) -> Path:
    (tmp_path / "principles.yaml").write_text(
        "principles:\n  - id: p.test\n    severity: info\n" + source_line,
        encoding="utf-8",
    )
    return tmp_path


def _show_dir(tmp_path: Path, source_line: str) -> Path:
    shows = tmp_path / "shows"
    shows.mkdir()
    (shows / "t.yaml").write_text(
        "rules:\n  - id: show.t.r\n    title: t\n    severity: info\n"
        + source_line
        + "    rationale: r\n    supersedes: [G8]\n",
        encoding="utf-8",
    )
    return tmp_path


def test_toanaz_rule_without_source_is_rejected(tmp_path):
    d = _principles_dir(tmp_path, "")
    with pytest.raises(ValueError, match=r"principles\.yaml.*p\.test.*ToanAZ"):
        layers._principles(d)


def test_toanaz_rule_with_foreign_source_is_rejected(tmp_path):
    d = _principles_dir(tmp_path, '    source: "from a textbook"\n')
    with pytest.raises(ValueError, match=r"p\.test"):
        layers._principles(d)


def test_toanaz_rule_without_date_is_rejected(tmp_path):
    d = _principles_dir(tmp_path, '    source: "ToanAZ said so"\n')
    with pytest.raises(ValueError, match=r"p\.test"):
        layers._principles(d)


def test_toanaz_rule_with_owner_source_and_date_loads(tmp_path):
    d = _principles_dir(tmp_path, f'    source: "{GOOD}"\n')
    assert [r.id for r in layers._principles(d)] == ["p.test"]


def test_show_rule_with_foreign_source_is_rejected(tmp_path):
    d = _show_dir(tmp_path, '    source: "from a textbook"\n')
    with pytest.raises(ValueError, match=r"t\.yaml.*show\.t\.r"):
        layers._show_rules(d, "t")


def test_show_rule_with_owner_source_and_date_loads(tmp_path):
    d = _show_dir(tmp_path, f'    source: "{GOOD}"\n')
    assert [r.id for r in layers._show_rules(d, "t")] == ["show.t.r"]


def test_base_layer_is_not_affected(tmp_path):
    p = tmp_path / "b.yaml"
    p.write_text(
        "rules:\n  - id: B1\n    title: t\n    severity: info\n"
        '    source: "from a textbook"\n    rationale: r\n    supersedes: []\n',
        encoding="utf-8",
    )
    assert [r.id for r in load_rules(p, layer="base")] == ["B1"]


def test_shipped_small_profile_still_loads():
    repo_knowledge = Path(__file__).resolve().parents[1] / "knowledge" / "toanaz"
    rules = layers._show_rules(repo_knowledge, "small")
    assert len(rules) == 2
