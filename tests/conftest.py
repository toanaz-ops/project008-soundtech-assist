from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
USER_FILES = REPO_ROOT / "user-files"


@pytest.fixture(scope="session")
def factory_path() -> Path:
    return USER_FILES / "factory-scene.snap"


@pytest.fixture(scope="session")
def vu_path() -> Path:
    return USER_FILES / "example-Vu.snap"
