"""Shared pytest fixtures and utilities for all tests."""

import os

import pytest

from common.config import DB_PATH


def _db_exists() -> bool:
    """Check if the product database exists."""
    db_path = os.path.join(os.getcwd(), DB_PATH)
    return os.path.exists(db_path)


# Skip marker for tests requiring database
requires_db = pytest.mark.skipif(not _db_exists(), reason="Database not found - run ingestion first")
