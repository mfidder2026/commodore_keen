"""Run all tests: converter tests, py65 unit tests and headless VICE scenarios.

Usage: python tools/test.py [pytest args]
Set UPDATE_GOLDEN=1 to (re)write reference screenshots in tests/golden/ on purpose.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent

if __name__ == "__main__":
    sys.exit(pytest.main([str(ROOT / "tests"), "-v", *sys.argv[1:]]))
