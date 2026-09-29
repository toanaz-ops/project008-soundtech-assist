"""Local CI runner for wing-parser -- one command, one exit code, answers
"is this branch fit to push or merge" without waiting on GitHub Actions.

Built per docs/git-workflow.md's "Luật CI: làm theo PROJECT004" entry
(memory/MEMORY.md, 2026-09-25): failures from a CI-only environment gap are
never silently skipped, they print `BOQUA (ci): <nodeid> — <reason>` and are
checked against a named registry (EXPECTED_SKIPS below); a real failure is
never skipped at all. Modelled on PROJECT004's scripts/dry_run_all.py.

Five checks, in order:
  1. Editable-install sanity -- refuses to run against the wrong checkout
     (the shared-.venv trap, memory/MEMORY.md 2026-08-24 / 2026-09-18).
     FATAL: nothing else runs if this fails.
  2. CI extras importable (pyproject's [ui,ingest,llm,llm-openai,dev]),
     and `mcp` confirmed ABSENT, matching .github/workflows/ci.yml exactly.
  3. Same QT_QPA_PLATFORM as CI, same relative configfile path.
  4. python -m pytest --junitxml=dist-reports/ci-local.xml.
  5. The XML's skip list against EXPECTED_SKIPS -- an unregistered skip
     fails, and a registry entry that no longer skips fails too (a stale
     entry means the registry is rotting exactly like PROJECT004's
     BO_CAN_SECRET warns about).

Usage: python scripts/ci_local.py   (run from the checkout root; the pinned
venv's python must already be the one on PATH -- see memory/MEMORY.md
"PITFALL: venv phải cài đủ extras trước khi build exe" for what to install).
"""
from __future__ import annotations

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

# Make the sibling module importable both when this file is run directly
# (`python scripts/ci_local.py`, where sys.path[0] is scripts/ already) and
# when it is imported as `scripts.ci_local` (tests/test_ci_local.py, where
# sys.path[0] is the checkout root and "scripts" is a namespace package).
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ci_local_lib import (
    JunitTally,
    SkipDiff,
    dep_spec_to_dist_name,
    diff_skips,
    dist_name_to_import_name,
    is_same_checkout,
    parse_junit_tally,
    parse_optional_dependencies,
)

ROOT = Path(__file__).resolve().parent.parent
PY = sys.executable

# Exactly ci.yml's install line (.github/workflows/ci.yml), so the pip
# command this script prints is copy-pasteable and gets the same result CI
# gets. `mcp` is deliberately never in this list -- see check_extras().
CI_EXTRAS = ("dev", "ui", "ingest", "llm", "llm-openai")

QT_QPA_PLATFORM = "offscreen:configfile=.github/ci-offscreen-screen.json"
JUNIT_PATH = ROOT / "dist-reports" / "ci-local.xml"

# The skips of the CI environment (no `mcp`, checked below), measured on a
# real run after the shared venv was cleaned 2026-09-29.
EXPECTED_SKIPS = {
    "tests/test_mcp.py::test_server_builds_when_the_mcp_package_is_installed":
        "the mcp extra is deliberately absent, as in GitHub CI; "
        "test_main_names_the_fix_when_the_mcp_extra_is_missing runs instead.",
    "tests/test_ui_keyboard.py::test_tab_order_stays_inside_each_page[overview]":
        "Overview page exposes fewer than two focus stops today (house "
        "style task 1b-18/1b-21, memory/MEMORY.md 2026-08-26).",
    "tests/test_ui_keyboard.py::test_tab_order_stays_inside_each_page[channels]":
        "Channels page exposes fewer than two focus stops today (same as "
        "overview above).",
}


def check_editable_install() -> tuple[bool, str]:
    proc = subprocess.run(
        [PY, "-c", "import wing_parser; print(wing_parser.__file__)"],
        cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8",
    )
    if proc.returncode != 0:
        return False, f"import wing_parser failed:\n{proc.stderr.strip()}"
    resolved = proc.stdout.strip()
    if is_same_checkout(resolved, ROOT):
        return True, f"OK   wing_parser imports from this checkout: {resolved}"
    fix = f'"{PY}" -m pip install -e "{ROOT}"'
    return False, (
        f"HONG -- wing_parser imports from a DIFFERENT checkout:\n"
        f"    {resolved}\n"
        f"  expected under: {ROOT / 'wing_parser'}\n"
        f"  This venv's editable install still points at another worktree "
        f"or the main checkout. Fix:\n    {fix}"
    )


def check_extras() -> tuple[bool, list[str]]:
    lines: list[str] = []
    ok = True
    optional = parse_optional_dependencies((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    for extra in CI_EXTRAS:
        missing, names = [], []
        for spec in optional.get(extra, []):
            module = dist_name_to_import_name(dep_spec_to_dist_name(spec))
            names.append(module)
            if importlib.util.find_spec(module) is None:
                missing.append(module)
        if missing:
            ok = False
            lines.append(f"FAIL extra '{extra}': not importable -- {', '.join(missing)}")
        else:
            lines.append(f"OK   extra '{extra}': {', '.join(names)}")

    mcp_present = importlib.util.find_spec("mcp") is not None
    if mcp_present:
        ok = False
        lines.append(
            "FAIL mcp: PRESENT -- CI never installs this extra "
            "(tests/test_mcp.py depends on its absence; see EXPECTED_SKIPS above)"
        )
    else:
        lines.append("OK   mcp: absent, exactly as in CI")

    if not ok:
        lines.append(f'fix: "{PY}" -m pip install -e "{ROOT}"[{",".join(CI_EXTRAS)}]')
        if mcp_present:
            lines.append(f'fix: "{PY}" -m pip uninstall -y mcp')
    return ok, lines


def run_pytest() -> JunitTally:
    JUNIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    env = {**os.environ, "QT_QPA_PLATFORM": QT_QPA_PLATFORM}
    print(f"$ QT_QPA_PLATFORM={QT_QPA_PLATFORM} {PY} -m pytest -p no:faulthandler "
          f"--junitxml={JUNIT_PATH.relative_to(ROOT)}")
    proc = subprocess.run(
        [PY, "-m", "pytest", "-p", "no:faulthandler", f"--junitxml={JUNIT_PATH}"],
        cwd=str(ROOT), env=env,
    )
    print(f"(pytest exit code {proc.returncode} -- informational only; the "
          f"verdict below is computed from the JUnit XML, not this code or "
          f"the terminal summary, because Qt teardown can eat the summary)")
    if not JUNIT_PATH.exists():
        sys.exit(f"CI-LOCAL: HONG -- {JUNIT_PATH} was not written; pytest did not "
                  f"reach the point of producing a report")
    return parse_junit_tally(JUNIT_PATH.read_text(encoding="utf-8"))


def report_skips(tally: JunitTally) -> SkipDiff:
    for nodeid, reason in sorted(tally.skips.items()):
        print(f"BOQUA (ci): {nodeid} — {reason}")
    diff = diff_skips(tally.skips, EXPECTED_SKIPS)
    for nodeid in diff.unexpected:
        print(f"HONG -- skipped but not in the registry: {nodeid}")
    for nodeid in diff.stale:
        print(f"HONG -- registry entry did not skip this run (stale): {nodeid} "
              f"— {EXPECTED_SKIPS[nodeid]}")
    return diff


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    print("== 1. Editable install (shared-.venv trap) ==")
    editable_ok, msg = check_editable_install()
    print(msg)
    if not editable_ok:
        print("\nCI-LOCAL: HONG -- refusing to run the suite against the wrong checkout")
        return 1

    print("\n== 2. CI extras ==")
    extras_ok, extras_lines = check_extras()
    print("\n".join(extras_lines))

    print(f"\n== 3. Qt platform ==\nQT_QPA_PLATFORM={QT_QPA_PLATFORM}")

    print("\n== 4. pytest ==")
    tally = run_pytest()
    print(f"tests={tally.tests} failures={tally.failures} errors={tally.errors} "
          f"skipped={tally.skipped}")

    print("\n== 5. Skip registry ==")
    diff = report_skips(tally)

    fail_count = tally.failures + tally.errors
    overall_ok = extras_ok and fail_count == 0 and diff.ok

    print()
    if overall_ok:
        print(f"CI-LOCAL: DAT {tally.tests} tests, {fail_count} fail, "
              f"{tally.skipped} skip (registry khớp)")
        return 0

    reasons = []
    if not extras_ok:
        reasons.append("extras/mcp check failed")
    if fail_count:
        reasons.append(f"{fail_count} test failure(s)/error(s)")
    if not diff.ok:
        reasons.append(f"{len(diff.unexpected)} unexpected skip(s), "
                        f"{len(diff.stale)} stale registry entr(y/ies)")
    print(f"CI-LOCAL: HONG -- {'; '.join(reasons)}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
