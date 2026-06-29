"""
Minimal smoke tests.

Purpose:
- Verify all project modules import correctly.
- Catch missing dependencies, syntax errors, and broken imports.

This is intentionally lightweight for the MVP.
"""


import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

def test_pipeline_imports():
    from pipeline import deid
    from pipeline import deid_check
    from pipeline import ner
    from pipeline import ner_check

    assert deid is not None
    assert deid_check is not None
    assert ner is not None
    assert ner_check is not None


def test_utils_imports():
    from utils import config
    from utils import logging

    assert config is not None
    assert logging is not None


def test_main_import():
    import main

    assert main is not None