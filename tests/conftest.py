import os
from pathlib import Path

import pytest

from wing_parser import config

REPO_ROOT = Path(__file__).resolve().parents[1]
USER_FILES = REPO_ROOT / "user-files"


@pytest.fixture(scope="session")
def factory_path() -> Path:
    return USER_FILES / "factory-scene.snap"


@pytest.fixture(scope="session")
def vu_path() -> Path:
    return USER_FILES / "example-Vu.snap"


@pytest.fixture(scope="session", autouse=True)
def _isolated_knowledge_dir(tmp_path_factory):
    """Point every test at a throwaway knowledge directory by default.

    Without this, the suite reads `config.knowledge_dir()`'s real default
    -- the in-repo `knowledge/toanaz/`. The README's own "Add a
    show-specific override" section tells a user to drop a `.yaml` file
    into `knowledge/toanaz/shows/`; doing that on a real checkout used to
    turn tests red, because tests that never pass an explicit
    `directory=` were silently reading whatever a user had actually put
    there. `knowledge/toanaz/classifier.yaml` ships with `channels: {}`
    and `buses: {}`, and the shipped `principles.yaml` holds `principles:
    []` -- no standing principle has been needed yet -- so an empty tmp
    directory (nothing on disk at all) resolves identically to the
    shipped default: both `layers._principles` calls yield `[]`. This
    costs no coverage. A test that deliberately needs the real in-repo directory
    opts in explicitly with `monkeypatch.delenv(config.ENV_VAR, ...)` or
    by constructing its own `directory=` fixture, the way
    `test_classifier_cache.py` and `test_advisory_resolver.py` already
    do.

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
