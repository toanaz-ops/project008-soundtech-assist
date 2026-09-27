"""Pure helpers for scripts/ci_local.py -- kept import-light and side-effect
free so tests/test_ci_local.py can exercise them without spawning pytest or
touching the venv. Anything that needs a subprocess or importlib.util.find_spec
lives in ci_local.py itself; this module only parses text and compares data.
"""
from __future__ import annotations

import re
import tomllib
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

# --- editable-install check ------------------------------------------------


def is_same_checkout(resolved_file: str, root: Path, package: str = "wing_parser") -> bool:
    """True when `resolved_file` (a module's __file__, as a string) is the
    __init__.py inside `root`'s own copy of `package`.

    This is the shared-.venv editable-install trap (memory/MEMORY.md,
    2026-08-24 and 2026-09-18): a `pip install -e` run from a sibling
    worktree or the main checkout leaves this venv's editable pointer aimed
    at THAT checkout, so `import wing_parser` here silently returns someone
    else's code instead of raising.
    """
    resolved = Path(resolved_file).resolve()
    expected = (root / package / "__init__.py").resolve()
    return resolved == expected


# --- pyproject extras -------------------------------------------------------

# Distribution name -> import module name, for the handful of cases where
# they differ. Everything else falls back to replacing "-" with "_".
IMPORT_NAME_OVERRIDES = {
    "PyYAML": "yaml",
    "pytest-cov": "pytest_cov",
}

_DIST_NAME_RE = re.compile(r"[A-Za-z0-9_.\-]+")


def dep_spec_to_dist_name(spec: str) -> str:
    """'PySide6>=6.11' -> 'PySide6'; 'ruamel.yaml>=0.18' -> 'ruamel.yaml'."""
    match = _DIST_NAME_RE.match(spec.strip())
    return match.group(0) if match else spec.strip()


def dist_name_to_import_name(dist_name: str) -> str:
    return IMPORT_NAME_OVERRIDES.get(dist_name, dist_name.replace("-", "_"))


def parse_optional_dependencies(pyproject_text: str) -> dict[str, list[str]]:
    data = tomllib.loads(pyproject_text)
    return data["project"]["optional-dependencies"]


# --- junit XML tally ---------------------------------------------------------


@dataclass
class JunitTally:
    tests: int
    failures: int
    errors: int
    skipped: int
    skips: dict[str, str] = field(default_factory=dict)  # nodeid -> reason


def _nodeid(classname: str, name: str) -> str:
    """'tests.test_mcp' + 'test_x[a]' -> 'tests/test_mcp.py::test_x[a]'."""
    return f"{classname.replace('.', '/')}.py::{name}"


def parse_junit_tally(xml_text: str) -> JunitTally:
    """Read the tally from a pytest --junitxml report.

    Deliberately does not look at the terminal summary: Qt's teardown can
    kill the process after pytest already wrote the report, eating the
    printed summary line but leaving the XML intact.
    """
    root = ET.fromstring(xml_text)
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    if suite is None:
        raise ValueError("no <testsuite> element in junit XML")
    skips: dict[str, str] = {}
    for testcase in suite.iter("testcase"):
        skipped = testcase.find("skipped")
        if skipped is not None:
            nodeid = _nodeid(testcase.get("classname", ""), testcase.get("name", ""))
            skips[nodeid] = skipped.get("message", "")
    return JunitTally(
        tests=int(suite.get("tests", 0)),
        failures=int(suite.get("failures", 0)),
        errors=int(suite.get("errors", 0)),
        skipped=int(suite.get("skipped", 0)),
        skips=skips,
    )


# --- skip registry vs reality ------------------------------------------------


@dataclass
class SkipDiff:
    unexpected: list[str]  # skipped now, not in the registry -- FAIL
    stale: list[str]       # in the registry, did not skip this run -- FAIL
    matched: list[str]     # in both -- fine

    @property
    def ok(self) -> bool:
        return not self.unexpected and not self.stale


def diff_skips(actual: dict[str, str], registry: dict[str, str]) -> SkipDiff:
    """Compare this run's skipped nodeids against the allowed registry.

    Matching is by nodeid only (not by reason text): the registry records
    WHY a skip is allowed, the XML records why pytest actually skipped it,
    and the two are free to be worded differently.
    """
    actual_ids = set(actual)
    registry_ids = set(registry)
    return SkipDiff(
        unexpected=sorted(actual_ids - registry_ids),
        stale=sorted(registry_ids - actual_ids),
        matched=sorted(actual_ids & registry_ids),
    )
