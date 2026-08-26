import json
import os
from pathlib import Path

import pytest

from wing_parser import WingScene, config

REPO_ROOT = Path(__file__).resolve().parents[1]
USER_FILES = REPO_ROOT / "user-files"


def _mutated_scene(vu_path, tmp_path, mutate, name="mutated.snap"):
    """Load the sample scene with a caller-supplied mutation applied to its
    raw `ae_data`, without ever writing directly to the checked-in fixture.

    `mutate` receives `doc["ae_data"]` and edits it in place (e.g. flip a
    send's `on` flag, drop a dyn block). Later tasks that need a synthetic
    real-file variant import this rather than repeating the read/mutate/
    write dance each test in this suite already does by hand.
    """
    doc = json.loads(vu_path.read_text(encoding="utf-8"))
    mutate(doc["ae_data"])
    out = tmp_path / name
    out.write_text(json.dumps(doc), encoding="utf-8")
    return WingScene.load(out)


@pytest.fixture(scope="session")
def factory_path() -> Path:
    return USER_FILES / "factory-scene.snap"


@pytest.fixture(scope="session")
def vu_path() -> Path:
    return USER_FILES / "example-Vu.snap"


@pytest.fixture(scope="session")
def qt_app():
    """One QApplication for the whole run; Qt permits only one.

    `importorskip` rather than a hard import: PySide6 is the optional
    `ui` extra, and the engine and CLI must stay testable on a machine
    with no GUI installed at all.
    """
    widgets = pytest.importorskip("PySide6.QtWidgets")
    return widgets.QApplication.instance() or widgets.QApplication([])


@pytest.fixture(scope="session", autouse=True)
def _isolated_knowledge_dir(tmp_path_factory):
    """Point every test at a throwaway knowledge directory by default.

    Without this, the suite reads `config.knowledge_dir()`'s real default
    -- the in-repo `knowledge/toanaz/`. The README's own "Add a
    show-specific override" section tells a user to drop a `.yaml` file
    into `knowledge/toanaz/shows/`; doing that on a real checkout used to
    turn tests red, because tests that never pass an explicit
    `directory=` were silently reading whatever a user had actually put
    there. `knowledge/toanaz/classifier.yaml` ships with `channels: {}`,
    `buses: {}`, and `cuesheet: {}`, and the shipped `principles.yaml`
    holds `principles: []` -- no standing principle has been needed yet
    -- so an empty tmp directory (nothing on disk at all) resolves
    identically to the shipped default: both `layers._principles` calls
    yield `[]`. This costs no coverage. A test that deliberately needs
    the real in-repo directory opts in explicitly with
    `monkeypatch.delenv(config.ENV_VAR, ...)` or by constructing its own
    `directory=` fixture, the way `test_classifier_cache.py` and
    `test_advisory_resolver.py` already do.

    A plain `monkeypatch` fixture is function-scoped and cannot be
    requested from a session-scoped fixture, so the environment variable
    is set and restored by hand instead.
    """
    directory = tmp_path_factory.mktemp("knowledge")
    previous = os.environ.get(config.ENV_VAR)
    os.environ[config.ENV_VAR] = str(directory)
    yield directory
    if previous is None:
        os.environ.pop(config.ENV_VAR, None)
    else:
        os.environ[config.ENV_VAR] = previous


@pytest.fixture
def settle(qt_app):
    """Pump Qt events until predicate() holds; queued signals need this.

    Worker results arrive across a thread boundary and are only
    delivered while the event loop runs -- tests pump instead of sleep.
    """
    import time

    def _settle(predicate, limit_s=2.0):
        deadline = time.monotonic() + limit_s
        while time.monotonic() < deadline:
            if predicate():
                return True
            qt_app.processEvents()
            time.sleep(0.005)
        return False

    return _settle
