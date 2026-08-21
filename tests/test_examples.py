import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
EXAMPLES = REPO / "examples"


@pytest.mark.parametrize(
    "script", ["analyze_vu.py", "diff_factory_vs_vu.py", "advisory_check.py"]
)
def test_example_runs_cleanly(script, tmp_path, monkeypatch):
    env = {
        **dict(__import__("os").environ),
        "WING_DISABLE_LLM": "1",
        "WING_KNOWLEDGE_DIR": str(tmp_path),
        "PYTHONPATH": str(REPO),
    }
    result = subprocess.run(
        [sys.executable, str(EXAMPLES / script)],
        capture_output=True, text=True, env=env, cwd=REPO,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip()


def test_every_skill_has_front_matter_and_a_command():
    for skill_dir in sorted((REPO / "skills").iterdir()):
        body = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
        assert body.startswith("---"), skill_dir.name
        assert "description:" in body, skill_dir.name
        assert "python -m wing_parser.cli" in body, skill_dir.name


def test_the_shipped_skills_are_exactly_the_documented_set():
    """Named rather than counted, so adding a skill without documenting it
    fails with the missing name instead of an arithmetic mismatch. The
    README's `## Claude Skills` section lists the same set."""
    assert {d.name for d in (REPO / "skills").iterdir()} == {
        "wing-analyze",
        "wing-channel",
        "wing-diff",
        "wing-doctor",
        "wing-net",
        "wing-routing",
    }
