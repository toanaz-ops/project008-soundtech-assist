"""Unit tests for the pure parts of scripts/ci_local.py -- junit XML parsing,
the skip-registry diff, and the editable-install path check. None of these
spawn pytest or touch the venv; that's the point (scripts/ci_local.py itself
is exercised for real by running it, not by this suite recursively).
"""
from pathlib import Path

from scripts import ci_local_lib as lib

JUNIT_TEMPLATE = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
  <testsuite name="pytest" errors="{errors}" failures="{failures}"
             skipped="{skipped}" tests="{tests}" time="1.0">
{cases}
  </testsuite>
</testsuites>
"""


def _case(classname, name, skip_reason=None):
    if skip_reason is None:
        return f'    <testcase classname="{classname}" name="{name}" time="0.01"/>'
    return (
        f'    <testcase classname="{classname}" name="{name}" time="0.01">\n'
        f'      <skipped type="pytest.skip" message="{skip_reason}">skipped</skipped>\n'
        f'    </testcase>'
    )


# --- parse_junit_tally --------------------------------------------------


def test_parse_junit_tally_reads_the_summary_counts():
    xml = JUNIT_TEMPLATE.format(
        errors=0, failures=0, skipped=1, tests=3,
        cases="\n".join([
            _case("tests.test_a", "test_one"),
            _case("tests.test_a", "test_two"),
            _case("tests.test_b", "test_three", "needs mcp"),
        ]),
    )
    tally = lib.parse_junit_tally(xml)
    assert (tally.tests, tally.failures, tally.errors, tally.skipped) == (3, 0, 0, 1)


def test_parse_junit_tally_collects_skip_nodeids_and_reasons():
    xml = JUNIT_TEMPLATE.format(
        errors=0, failures=0, skipped=2, tests=2,
        cases="\n".join([
            _case("tests.test_mcp", "test_a", "mcp is installed in this environment"),
            _case("tests.test_ui_keyboard",
                  "test_tab_order_stays_inside_each_page[overview]",
                  "overview exposes fewer than two focus stops"),
        ]),
    )
    tally = lib.parse_junit_tally(xml)
    assert tally.skips == {
        "tests/test_mcp.py::test_a": "mcp is installed in this environment",
        "tests/test_ui_keyboard.py::test_tab_order_stays_inside_each_page[overview]":
            "overview exposes fewer than two focus stops",
    }


def test_parse_junit_tally_counts_failures_and_errors_separately():
    xml = JUNIT_TEMPLATE.format(errors=1, failures=2, skipped=0, tests=5, cases="")
    tally = lib.parse_junit_tally(xml)
    assert (tally.failures, tally.errors) == (2, 1)


# --- diff_skips -----------------------------------------------------------


def test_diff_skips_exact_match_is_ok():
    actual = {"tests/test_a.py::test_x": "reason A"}
    registry = {"tests/test_a.py::test_x": "documented reason, wording may differ"}
    diff = lib.diff_skips(actual, registry)
    assert diff.ok
    assert diff.unexpected == []
    assert diff.stale == []
    assert diff.matched == ["tests/test_a.py::test_x"]


def test_diff_skips_unexpected_skip_fails():
    actual = {"tests/test_a.py::test_x": "reason A",
              "tests/test_b.py::test_new_skip": "surprise"}
    registry = {"tests/test_a.py::test_x": "reason A"}
    diff = lib.diff_skips(actual, registry)
    assert not diff.ok
    assert diff.unexpected == ["tests/test_b.py::test_new_skip"]
    assert diff.stale == []


def test_diff_skips_stale_registry_entry_fails():
    actual = {"tests/test_a.py::test_x": "reason A"}
    registry = {"tests/test_a.py::test_x": "reason A",
                "tests/test_gone.py::test_removed": "no longer exists"}
    diff = lib.diff_skips(actual, registry)
    assert not diff.ok
    assert diff.unexpected == []
    assert diff.stale == ["tests/test_gone.py::test_removed"]


def test_diff_skips_handles_both_unexpected_and_stale_at_once():
    actual = {"tests/test_new.py::test_a": "new"}
    registry = {"tests/test_old.py::test_b": "old"}
    diff = lib.diff_skips(actual, registry)
    assert diff.unexpected == ["tests/test_new.py::test_a"]
    assert diff.stale == ["tests/test_old.py::test_b"]
    assert not diff.ok


# --- is_same_checkout -------------------------------------------------------


def test_is_same_checkout_true_for_the_expected_init_file(tmp_path):
    root = tmp_path / "checkout"
    (root / "wing_parser").mkdir(parents=True)
    init_file = root / "wing_parser" / "__init__.py"
    init_file.write_text("", encoding="utf-8")
    assert lib.is_same_checkout(str(init_file), root)


def test_is_same_checkout_false_for_a_different_checkout(tmp_path):
    root = tmp_path / "worktree"
    other = tmp_path / "main-checkout"
    (root / "wing_parser").mkdir(parents=True)
    (other / "wing_parser").mkdir(parents=True)
    other_init = other / "wing_parser" / "__init__.py"
    other_init.write_text("", encoding="utf-8")
    assert not lib.is_same_checkout(str(other_init), root)


def test_is_same_checkout_normalises_relative_and_dotted_paths(tmp_path):
    root = tmp_path / "checkout"
    (root / "wing_parser").mkdir(parents=True)
    init_file = root / "wing_parser" / "__init__.py"
    init_file.write_text("", encoding="utf-8")
    # Same file, spelled with a redundant "./wing_parser/../wing_parser" hop.
    messy = str(root / "wing_parser" / ".." / "wing_parser" / "__init__.py")
    assert lib.is_same_checkout(messy, root)


# --- pyproject extras parsing (small, but easy and pure) --------------------


def test_dep_spec_to_dist_name_strips_version_specifiers():
    assert lib.dep_spec_to_dist_name("PySide6>=6.11") == "PySide6"
    assert lib.dep_spec_to_dist_name("mcp>=1.2,<2") == "mcp"


def test_dist_name_to_import_name_overrides_known_mismatches():
    assert lib.dist_name_to_import_name("PyYAML") == "yaml"
    assert lib.dist_name_to_import_name("pytest-cov") == "pytest_cov"
    assert lib.dist_name_to_import_name("openpyxl") == "openpyxl"


def test_parse_optional_dependencies_reads_the_real_pyproject():
    root = Path(__file__).resolve().parents[1]
    text = (root / "pyproject.toml").read_text(encoding="utf-8")
    optional = lib.parse_optional_dependencies(text)
    assert "ui" in optional and "mcp" in optional
    assert any("PySide6" in spec for spec in optional["ui"])
