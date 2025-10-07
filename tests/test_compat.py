from __future__ import annotations

import sys

import pytest


@pytest.fixture(autouse=True)
def _cleanup_imp_module():
    sys.modules.pop("imp", None)
    yield
    sys.modules.pop("imp", None)


def test_ensure_imp_module_provides_shim():
    from saftao._compat import ensure_modules

    ensure_modules(["imp"])

    import imp  # type: ignore

    assert hasattr(imp, "new_module")
