"""Compatibility helpers for deprecated/removed stdlib modules."""

from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import Iterable

__all__ = ["ensure_modules"]


def ensure_modules(missing: Iterable[str]) -> None:
    """Ensure compatibility modules are importable.

    For each module name in *missing*, attempt to import it.  If it cannot be
    imported, look for a sibling module within this package with the same name
    and insert it into :mod:`sys.modules` so that downstream imports succeed.
    """

    import sys

    for name in missing:
        try:
            import_module(name)
        except ModuleNotFoundError:
            candidate = f"{__name__}.{name}"
            try:
                module = import_module(candidate)
            except ModuleNotFoundError:
                continue
            sys.modules[name] = module
