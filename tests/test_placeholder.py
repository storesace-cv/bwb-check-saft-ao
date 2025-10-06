"""Placeholder tests ensuring the package can be imported."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))


def test_import_package() -> None:
    module = importlib.import_module("saftao")
    assert hasattr(module, "__all__")
