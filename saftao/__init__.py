"""Compatibility package to expose the project modules without installation."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_pkg_dir = Path(__file__).resolve().parent.parent / "src" / "saftao"
_spec = importlib.util.spec_from_file_location(
    __name__,
    _pkg_dir / "__init__.py",
    submodule_search_locations=[str(_pkg_dir)],
)
_module = importlib.util.module_from_spec(_spec)
sys.modules[__name__] = _module
assert _spec.loader is not None
_spec.loader.exec_module(_module)
