import os
import shutil
import tempfile
from pathlib import Path
import pytest

# 1. Immediate isolation at conftest import time:
# Pytest loads conftest.py BEFORE discovering or importing any test modules (such as test_main.py).
# Initializing the test database here guarantees that no test file or FastAPI TestClient can ever
# connect to or mutate data/nonpartisan.duckdb.
_TEST_TEMP_DIR = tempfile.TemporaryDirectory(prefix="duckdb_test_")
_TEST_DB_FILE = Path(_TEST_TEMP_DIR.name) / "test_nonpartisan.duckdb"

_PROD_DB = Path(__file__).resolve().parent.parent / "data" / "nonpartisan.duckdb"
if _PROD_DB.exists():
    shutil.copyfile(_PROD_DB, _TEST_DB_FILE)

os.environ["TESTING"] = "1"
os.environ["DUCKDB_PATH"] = str(_TEST_DB_FILE)

import database
database.initialize()


def pytest_unconfigure(config):
    """Clean up test environment after the test session ends."""
    if "DUCKDB_PATH" in os.environ:
        del os.environ["DUCKDB_PATH"]
    if "TESTING" in os.environ:
        del os.environ["TESTING"]
    try:
        _TEST_TEMP_DIR.cleanup()
    except Exception:
        # Handles Windows file lock cleanup silently on process exit
        pass


@pytest.fixture(scope="session", autouse=True)
def isolated_test_db():
    """Ensure the session uses the isolated temporary database."""
    yield _TEST_DB_FILE
